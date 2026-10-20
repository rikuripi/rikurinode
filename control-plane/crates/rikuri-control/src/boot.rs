//! What the daemon does before it listens, in one place so the tests can do
//! the same through the real composition: open the state folder, read or make
//! the node's instance id (the sessions' issuer), load or make the TLS
//! identity, arm a claim code at the very first start, and build the
//! application state.

use std::fmt;

use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::claim::{self, ClaimError, Code};
use crate::config::Config;
use crate::http::App;
use crate::owner;
use crate::random::{self, RandomError};
use crate::session::Store;
use crate::state::{StateDir, StateError};
use crate::status::{self, Started};
use crate::tls::{self, Identity, TlsError};

pub const NODE_FILE: &str = "node.json";

/// The node instance: made once, kept for the node's life.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct NodeFile {
    pub instance_id: String,
    pub created_unix: u64,
}

pub struct Booted {
    pub app: App,
    pub identity: Identity,
    /// The claim code, if this start armed one: the first start of an
    /// unclaimed node, and only then.
    pub armed: Option<Code>,
    pub node: NodeFile,
}

#[derive(Debug)]
pub enum BootError {
    State(StateError),
    Random(RandomError),
    Tls(TlsError),
    Claim(ClaimError),
}

impl fmt::Display for BootError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            BootError::State(e) => write!(f, "{e}"),
            BootError::Random(e) => write!(f, "{e}"),
            BootError::Tls(e) => write!(f, "{e}"),
            BootError::Claim(e) => write!(f, "{e}"),
        }
    }
}

impl std::error::Error for BootError {}

impl From<StateError> for BootError {
    fn from(e: StateError) -> Self {
        BootError::State(e)
    }
}

impl From<RandomError> for BootError {
    fn from(e: RandomError) -> Self {
        BootError::Random(e)
    }
}

impl From<TlsError> for BootError {
    fn from(e: TlsError) -> Self {
        BootError::Tls(e)
    }
}

impl From<ClaimError> for BootError {
    fn from(e: ClaimError) -> Self {
        BootError::Claim(e)
    }
}

pub fn boot(config: &Config, started: Started) -> Result<Booted, BootError> {
    let dir = StateDir::open(&config.state_dir)?;
    let now = status::unix_now().unwrap_or(0);
    let node = match dir.read_json::<NodeFile>(NODE_FILE)? {
        Some(node) => node,
        None => {
            let node = NodeFile {
                instance_id: random::token()?,
                created_unix: now,
            };
            dir.write_json(NODE_FILE, &node)?;
            node
        }
    };
    let identity = tls::load_or_create(&dir, &config.names, OffsetDateTime::now_utc())?;
    let armed = if !owner::exists(&dir) && !dir.exists(claim::FILE) {
        Some(claim::arm(&dir, now)?)
    } else {
        None
    };
    let claim_wrong_tries = claim::load(&dir)?.map_or(0, |file| file.wrong_tries);
    let sessions = Store::new(dir.clone(), node.instance_id.clone());
    let app = App::new(
        started,
        dir,
        config.names.clone(),
        sessions,
        identity.ca_pem.clone(),
        identity.ca_fingerprint.clone(),
        config.https.port(),
        claim_wrong_tries,
    );
    Ok(Booted {
        app,
        identity,
        armed,
        node,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::names::Names;
    use crate::state::testing::Scratch;

    fn config(scratch: &Scratch) -> Config {
        Config {
            https: "127.0.0.1:8443".parse().unwrap(),
            http: None,
            names: Names::new(["rikuri01.local"]).unwrap(),
            state_dir: scratch.0.clone(),
        }
    }

    #[test]
    fn the_first_start_makes_the_instance_the_identity_and_arms_a_claim() {
        let scratch = Scratch::new();
        let booted = boot(&config(&scratch), Started::now()).unwrap();
        assert_eq!(booted.node.instance_id.len(), 64);
        assert!(booted.identity.ca_created);
        assert!(
            booted.armed.is_some(),
            "an unclaimed node arms a code at its first start"
        );
        assert_eq!(booted.app.0.sessions.issuer(), booted.node.instance_id);
        assert_eq!(booted.app.0.https_port, 8443);
    }

    #[test]
    fn a_later_start_keeps_the_instance_and_arms_nothing() {
        let scratch = Scratch::new();
        let first = boot(&config(&scratch), Started::now()).unwrap();
        let second = boot(&config(&scratch), Started::now()).unwrap();
        assert_eq!(first.node.instance_id, second.node.instance_id);
        assert!(!second.identity.ca_created);
        assert!(
            second.armed.is_none(),
            "a retired or expired claim is re-armed only from the console"
        );
    }

    #[test]
    fn a_claimed_node_arms_nothing_even_without_a_claim_file() {
        let scratch = Scratch::new();
        boot(&config(&scratch), Started::now()).unwrap();
        let dir = StateDir::open(&scratch.0).unwrap();
        claim::finish(&dir).unwrap();
        owner::set_password(&dir, "a password of twelve", 1).unwrap();
        let booted = boot(&config(&scratch), Started::now()).unwrap();
        assert!(booted.armed.is_none());
    }
}
