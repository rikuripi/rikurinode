//! The status model: what the control plane knows about each component of
//! the node, and the rule that folds it into one overall state.
//!
//! Lessons register EVID-02: a state that could not be read is carried as
//! `unknown`, never as healthy, down, 0 or all-clear. EVID-04: a reading
//! carries the time it was taken. EVID-08: the aggregate is honest.

use std::collections::BTreeMap;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use serde::Serialize;

/// The four states a component can be in.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum State {
    Healthy,
    Degraded,
    Down,
    /// Not measured yet, or the reading failed. Never turned into one of the
    /// other three.
    Unknown,
}

/// The parts of the node the control plane reports on. A closed set: a
/// `match` over it must name every member, so adding one cannot leave a
/// report silently incomplete.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Component {
    /// The operating system image and its services (systemd, bootc).
    Os,
    Bitcoind,
    Lnd,
    Tor,
}

impl Component {
    /// Every component, in report order.
    pub const ALL: [Component; 4] = [
        Component::Os,
        Component::Bitcoind,
        Component::Lnd,
        Component::Tor,
    ];
}

/// What is known about one component right now.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ComponentStatus {
    pub state: State,
    /// When the reading behind `state` was taken, in Unix seconds; `None`
    /// until a probe has run. Never 0 for "not measured".
    pub checked_unix: Option<u64>,
    /// The finding, or why there is none, in plain words.
    pub detail: String,
}

impl ComponentStatus {
    /// The state before any probe has run, or after one could not read.
    pub fn unknown(detail: impl Into<String>) -> Self {
        Self {
            state: State::Unknown,
            checked_unix: None,
            detail: detail.into(),
        }
    }
}

/// Why every component is `unknown` in B0.1.
pub const NOT_PROBED: &str = "not probed: no interface to this component exists yet";

/// Folds component states into one. Precedence: `Down` over `Degraded` over
/// `Unknown` over `Healthy`, so a node whose state is partly unread is never
/// reported healthy. No components at all is `Unknown`: a check that could
/// not run never reads as all-clear.
pub fn overall<I: IntoIterator<Item = State>>(states: I) -> State {
    states
        .into_iter()
        .max_by_key(|state| severity(*state))
        .unwrap_or(State::Unknown)
}

fn severity(state: State) -> u8 {
    match state {
        State::Healthy => 0,
        State::Unknown => 1,
        State::Degraded => 2,
        State::Down => 3,
    }
}

/// Unix seconds now, or `None` when the clock cannot say (set before 1970).
pub fn unix_now() -> Option<u64> {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .ok()
        .map(|since| since.as_secs())
}

/// The moment the control plane started: the source of its uptime.
#[derive(Clone, Copy, Debug)]
pub struct Started {
    at: Instant,
    unix: Option<u64>,
}

impl Started {
    pub fn now() -> Self {
        Self {
            at: Instant::now(),
            unix: unix_now(),
        }
    }

    pub fn uptime(&self) -> Duration {
        self.at.elapsed()
    }
}

/// The control plane's own identity and age, beside the outcomes it reports
/// (Rikuri-PI's evidence standard: versions and ids with every outcome).
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ControlPlane {
    pub version: &'static str,
    pub pid: u32,
    pub started_unix: Option<u64>,
    pub uptime_seconds: u64,
}

/// A snapshot of what the control plane knows, with the time it was taken.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct Report {
    pub observed_unix: Option<u64>,
    pub overall: State,
    pub control_plane: ControlPlane,
    pub components: BTreeMap<Component, ComponentStatus>,
}

/// The report as of now. B0.1: no probe exists, so every component is
/// `unknown`, and the overall state with it.
pub fn report(started: Started) -> Report {
    let components: BTreeMap<_, _> = Component::ALL
        .iter()
        .map(|component| (*component, ComponentStatus::unknown(NOT_PROBED)))
        .collect();
    Report {
        observed_unix: unix_now(),
        overall: overall(components.values().map(|status| status.state)),
        control_plane: ControlPlane {
            version: env!("CARGO_PKG_VERSION"),
            pid: std::process::id(),
            started_unix: started.unix,
            uptime_seconds: started.uptime().as_secs(),
        },
        components,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use State::{Degraded, Down, Healthy, Unknown};

    #[test]
    fn no_components_is_unknown_not_healthy() {
        assert_eq!(overall([]), Unknown);
    }

    #[test]
    fn all_healthy_is_healthy() {
        assert_eq!(overall([Healthy, Healthy, Healthy]), Healthy);
    }

    #[test]
    fn one_unknown_among_healthy_is_unknown() {
        assert_eq!(overall([Healthy, Unknown, Healthy]), Unknown);
    }

    #[test]
    fn degraded_outranks_unknown_and_healthy() {
        assert_eq!(overall([Unknown, Degraded, Healthy]), Degraded);
    }

    #[test]
    fn down_outranks_everything() {
        assert_eq!(overall([Healthy, Degraded, Down, Unknown]), Down);
        assert_eq!(overall([Down]), Down);
    }

    #[test]
    fn unknown_serializes_as_the_word_with_a_null_time() {
        let status = serde_json::to_value(ComponentStatus::unknown("x")).unwrap();
        assert_eq!(status["state"], "unknown");
        assert!(status["checked_unix"].is_null(), "{status}");
        assert_eq!(status["detail"], "x");
    }

    #[test]
    fn every_state_serializes_in_lowercase() {
        for (state, word) in [
            (Healthy, "healthy"),
            (Degraded, "degraded"),
            (Down, "down"),
            (Unknown, "unknown"),
        ] {
            assert_eq!(serde_json::to_value(state).unwrap(), word);
        }
    }

    #[test]
    fn the_report_before_any_probe_is_unknown_throughout() {
        let report = report(Started::now());
        assert_eq!(report.overall, Unknown);
        assert_eq!(report.components.len(), Component::ALL.len());
        for status in report.components.values() {
            assert_eq!(status.state, Unknown);
            assert_eq!(status.checked_unix, None);
            assert_eq!(status.detail, NOT_PROBED);
        }
        assert_eq!(report.control_plane.version, env!("CARGO_PKG_VERSION"));
        assert!(report.observed_unix.is_some());
        assert!(report.control_plane.started_unix.is_some());
    }

    #[test]
    fn components_serialize_by_name() {
        let value = serde_json::to_value(report(Started::now())).unwrap();
        for name in ["os", "bitcoind", "lnd", "tor"] {
            assert_eq!(value["components"][name]["state"], "unknown", "{name}");
        }
        assert_eq!(value["components"].as_object().unwrap().len(), 4);
    }
}
