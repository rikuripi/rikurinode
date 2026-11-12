//! The SetupHub (5c.4a): what setup still needs, each step read from the
//! node's real state at the time of the request, never from a stored flag
//! (AGENTS.md, "Runtime truth over declared truth"). Nothing here is kept, so
//! a refresh or a crash resumes by itself; stored wizard state comes with the
//! first step that takes input.
//!
//! The steps are a closed set: a `match` over them must name every one.
//! Record: docs/build-records/2026-11-11-5c4a-uuid-and-setup-hub.md

use std::io;

use serde::Serialize;

/// Where the running kernel says its hostname: the name the node has now,
/// not the one a file says it should have.
pub const HOSTNAME_FILE: &str = "/proc/sys/kernel/hostname";
/// The name the image gives a node until its owner names it (5c.2).
pub const SETUP_HOSTNAME: &str = "rikurisetup";

// What setup covers, in the order the owner meets it.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[cfg_attr(test, derive(ts_rs::TS))]
#[serde(rename_all = "lowercase")]
pub enum SetupStep {
    // The browser trusts the node's certificate.
    Connection,
    // The node has an owner.
    Owner,
    // The node has its own name (5c.4b).
    Name,
    Bitcoin,
    Lightning,
    Backup,
}

/// The order [`report`] lists the steps in.
pub const STEPS: [SetupStep; 6] = [
    SetupStep::Connection,
    SetupStep::Owner,
    SetupStep::Name,
    SetupStep::Bitcoin,
    SetupStep::Lightning,
    SetupStep::Backup,
];

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[cfg_attr(test, derive(ts_rs::TS))]
#[serde(rename_all = "lowercase")]
pub enum StepState {
    // The node's state shows it.
    Done,
    // What the owner can do now, or next.
    Next,
    // Comes with a later update.
    Later,
    // Could not be read. Never shown as done.
    Unknown,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[cfg_attr(test, derive(ts_rs::TS))]
pub struct HubStep {
    pub step: SetupStep,
    pub state: StepState,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[cfg_attr(test, derive(ts_rs::TS))]
pub struct HubReport {
    pub node_id: String,
    pub steps: Vec<HubStep>,
}

/// The name step, from a read of [`HOSTNAME_FILE`].
pub fn name_state(hostname: &io::Result<String>) -> StepState {
    match hostname.as_deref().map(str::trim) {
        Ok("") | Err(_) => StepState::Unknown,
        Ok(SETUP_HOSTNAME) => StepState::Next,
        Ok(_) => StepState::Done,
    }
}

/// The hub for a node whose UUID is `node_id`, whose owner exists or not,
/// and whose hostname read gave `hostname`. Reached only over the node's TLS,
/// so the connection is done by the time anyone reads this.
pub fn report(node_id: String, owner: bool, hostname: &io::Result<String>) -> HubReport {
    let state = |step: SetupStep| match step {
        SetupStep::Connection => StepState::Done,
        SetupStep::Owner if owner => StepState::Done,
        SetupStep::Owner => StepState::Next,
        SetupStep::Name => name_state(hostname),
        SetupStep::Bitcoin | SetupStep::Lightning | SetupStep::Backup => StepState::Later,
    };
    HubReport {
        node_id,
        steps: STEPS
            .iter()
            .map(|&step| HubStep {
                step,
                state: state(step),
            })
            .collect(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn read(text: &str) -> io::Result<String> {
        Ok(text.to_owned())
    }

    fn failed() -> io::Result<String> {
        Err(io::Error::new(io::ErrorKind::PermissionDenied, "denied"))
    }

    #[test]
    fn the_name_is_done_only_when_the_kernel_has_another_name() {
        assert_eq!(name_state(&read("rikurisetup\n")), StepState::Next);
        assert_eq!(name_state(&read("rikurisetup")), StepState::Next);
        assert_eq!(name_state(&read("rikuri01\n")), StepState::Done);
        assert_eq!(name_state(&read("kitchen-node\n")), StepState::Done);
        assert_eq!(name_state(&failed()), StepState::Unknown);
        for blank in ["", "\n", "  \n"] {
            assert_eq!(name_state(&read(blank)), StepState::Unknown, "{blank:?}");
        }
        // Repair 1: /etc/hostname may hold comments (hostname(5)); the name is
        // its first line that is not one.
        assert_eq!(
            name_state(&read("# set by the image\nrikurisetup\n")),
            StepState::Next
        );
        assert_eq!(
            name_state(&read("\n# named\n\nrikuri01\n")),
            StepState::Done
        );
        assert_eq!(name_state(&read("# only a comment\n")), StepState::Unknown);
    }

    #[test]
    fn every_step_in_order_with_its_state_from_the_node() {
        let id = "12345678-9abc-4ef0-8fed-cba987654321".to_owned();
        let hub = report(id.clone(), true, &read("rikurisetup\n"));
        assert_eq!(hub.node_id, id);
        assert_eq!(
            hub.steps.iter().map(|s| s.step).collect::<Vec<_>>(),
            STEPS.to_vec()
        );
        let states: Vec<_> = hub.steps.iter().map(|s| s.state).collect();
        use StepState::{Done, Later, Next, Unknown};
        assert_eq!(states, [Done, Done, Next, Later, Later, Later]);

        let named = report(id.clone(), true, &read("rikuri01\n"));
        assert_eq!(named.steps[2].state, Done);
        let unread = report(id.clone(), true, &failed());
        assert_eq!(unread.steps[2].state, Unknown);
        let unowned = report(id, false, &read("rikurisetup\n"));
        assert_eq!(unowned.steps[1].state, Next);
    }

    #[test]
    fn the_json_is_the_api_the_page_reads() {
        let hub = HubReport {
            node_id: "12345678-9abc-4ef0-8fed-cba987654321".to_owned(),
            steps: vec![HubStep {
                step: SetupStep::Lightning,
                state: StepState::Unknown,
            }],
        };
        assert_eq!(
            serde_json::to_string(&hub).unwrap(),
            r#"{"node_id":"12345678-9abc-4ef0-8fed-cba987654321","steps":[{"step":"lightning","state":"unknown"}]}"#
        );
    }
}
