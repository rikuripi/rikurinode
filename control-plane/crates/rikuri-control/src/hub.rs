//! The SetupHub (5c.4a): what setup still needs, each step read from the
//! node's state at the time of the request, never from a flag of our own.
//! Nothing here is kept, so
//! a refresh or a crash resumes by itself; stored wizard state comes with the
//! first step that takes input.
//!
//! The steps are a closed set: a `match` over them must name every one.
//! The hub also says why the node last restarted (D22; `restart.rs`).
//! One step, the power-return setting, is the firmware's and cannot be read
//! on the node: it is `manual`, explained and never shown as done.
//! Records: docs/build-records/2026-11-11-5c4a-uuid-and-setup-hub.md,
//! docs/build-records/2026-11-19-boot-cause-sentence.md,
//! docs/build-records/2026-11-22-power-return-step.md

use std::io;

use serde::Serialize;

use crate::restart::LastRestart;

/// The node's static hostname, as systemd-hostnamed keeps it and 5c.4b's
/// rename will write it. Repair 1 (verifier I-1; the owner, "/etc/hostname"):
/// not the kernel's `/proc/sys/kernel/hostname`, which the service's sandbox
/// hides (`ProcSubset=pid`) and whose name it freezes at its start
/// (`ProtectHostname=yes`). Reading the live name from hostnamed may come
/// with 5c.4b.
pub const HOSTNAME_FILE: &str = "/etc/hostname";
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
    // The node starts again by itself when power returns (plan §4.1): a
    // firmware setting the node cannot read.
    Power,
    Bitcoin,
    Lightning,
    Backup,
}

/// The order [`report`] lists the steps in.
pub const STEPS: [SetupStep; 7] = [
    SetupStep::Connection,
    SetupStep::Owner,
    SetupStep::Name,
    SetupStep::Power,
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
    // The node cannot read it; the owner checks it. Never shown as done.
    Manual,
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
    // Why the node last restarted; `None` when that could not be read.
    pub restart: Option<LastRestart>,
}

/// The name step, from a read of [`HOSTNAME_FILE`].
/// The name is the file's first line that is neither blank nor a comment
/// (hostname(5)); a file without one is `unknown`, never done.
pub fn name_state(hostname: &io::Result<String>) -> StepState {
    let Ok(text) = hostname else {
        return StepState::Unknown;
    };
    match text
        .lines()
        .map(str::trim)
        .find(|line| !line.is_empty() && !line.starts_with('#'))
    {
        None => StepState::Unknown,
        Some(SETUP_HOSTNAME) => StepState::Next,
        Some(_) => StepState::Done,
    }
}

/// The hub for a node whose UUID is `node_id`, whose owner exists or not,
/// whose hostname read gave `hostname`, and whose restart read gave
/// `restart`. Reached only over the node's TLS, so the connection is done by
/// the time anyone reads this.
pub fn report(
    node_id: String,
    owner: bool,
    hostname: &io::Result<String>,
    restart: Option<LastRestart>,
) -> HubReport {
    let state = |step: SetupStep| match step {
        SetupStep::Connection => StepState::Done,
        SetupStep::Owner if owner => StepState::Done,
        SetupStep::Owner => StepState::Next,
        SetupStep::Name => name_state(hostname),
        // Nothing on the node says it: the design note, option A.
        SetupStep::Power => StepState::Manual,
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
        restart,
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
        let hub = report(id.clone(), true, &read("rikurisetup\n"), None);
        assert_eq!(hub.node_id, id);
        assert_eq!(
            hub.steps.iter().map(|s| s.step).collect::<Vec<_>>(),
            STEPS.to_vec()
        );
        let states: Vec<_> = hub.steps.iter().map(|s| s.state).collect();
        use StepState::{Done, Later, Manual, Next, Unknown};
        assert_eq!(states, [Done, Done, Next, Manual, Later, Later, Later]);

        let named = report(id.clone(), true, &read("rikuri01\n"), None);
        assert_eq!(named.steps[2].state, Done);
        let unread = report(id.clone(), true, &failed(), None);
        assert_eq!(unread.steps[2].state, Unknown);
        let unowned = report(id.clone(), false, &read("rikurisetup\n"), None);
        assert_eq!(unowned.steps[1].state, Next);

        // D22: the restart is passed through as read, or None.
        assert_eq!(hub.restart, None);
        let restart = LastRestart {
            cause: crate::restart::RestartCause::Clean,
            at_unix: 2000,
            last_alive_unix: Some(1500),
        };
        let told = report(id, true, &read("rikuri01\n"), Some(restart));
        assert_eq!(told.restart, Some(restart));
    }

    #[test]
    fn the_power_step_is_manual_whatever_the_node_s_state() {
        let id = "12345678-9abc-4ef0-8fed-cba987654321";
        for owner in [false, true] {
            for hostname in [read("rikurisetup\n"), read("rikuri01\n"), failed()] {
                let hub = report(id.to_owned(), owner, &hostname, None);
                let power: Vec<_> = hub
                    .steps
                    .iter()
                    .filter(|s| s.step == SetupStep::Power)
                    .map(|s| s.state)
                    .collect();
                assert_eq!(power, [StepState::Manual], "{owner} {hostname:?}");
            }
        }
    }

    #[test]
    fn the_json_is_the_api_the_page_reads() {
        let hub = HubReport {
            node_id: "12345678-9abc-4ef0-8fed-cba987654321".to_owned(),
            steps: vec![
                HubStep {
                    step: SetupStep::Lightning,
                    state: StepState::Unknown,
                },
                HubStep {
                    step: SetupStep::Power,
                    state: StepState::Manual,
                },
            ],
            restart: None,
        };
        assert_eq!(
            serde_json::to_string(&hub).unwrap(),
            r#"{"node_id":"12345678-9abc-4ef0-8fed-cba987654321","steps":[{"step":"lightning","state":"unknown"},{"step":"power","state":"manual"}],"restart":null}"#
        );
    }
}
