//! The node's UUID (5c.4a): the identity setup gives the node when it is
//! claimed (platform plan, stage 1), shown to its owner, and kept for the
//! node's life. A random version-4 UUID, from the one RNG (`random.rs`), in
//! a file of its own: B0.2's `node.json` holds the sessions' issuer, which
//! stays internal and is never rewritten for this.
//!
//! Made once and never replaced: a file that cannot be read, or that does not
//! hold a UUID, is an error the caller reports, never a reason to mint a new
//! identity quietly (lessons register EVID-02; AGENTS.md, "Nothing important
//! fails silently").
//! Record: docs/build-records/2026-11-11-5c4a-uuid-and-setup-hub.md

use std::fmt;

use serde::{Deserialize, Serialize};

use crate::random::RandomError;
use crate::state::{StateDir, StateError};

pub const FILE: &str = "node-uuid.json";

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct NodeUuidFile {
    pub uuid: String,
    pub created_unix: u64,
}

#[derive(Debug)]
pub enum NodeIdError {
    State(StateError),
    Random(RandomError),
    /// The file holds something that is not a version-4 UUID.
    Malformed,
}

impl fmt::Display for NodeIdError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            NodeIdError::State(e) => write!(f, "{e}"),
            NodeIdError::Random(e) => write!(f, "{e}"),
            NodeIdError::Malformed => write!(f, "{FILE} does not hold a version-4 UUID"),
        }
    }
}

impl std::error::Error for NodeIdError {}

/// RFC 9562's version-4 form of 16 random bytes: version 4, variant 10,
/// lowercase, `8-4-4-4-12`.
pub fn format_v4(_bytes: [u8; 16]) -> String {
    String::new() // red: 5c.4a
}

/// Whether `text` is exactly what [`format_v4`] writes.
pub fn is_v4(_text: &str) -> bool {
    false // red: 5c.4a
}

/// The node's UUID, if it has one.
pub fn load(_dir: &StateDir) -> Result<Option<String>, NodeIdError> {
    Ok(None) // red: 5c.4a
}

/// The node's UUID, made now if it has none; never replaced.
pub fn ensure(_dir: &StateDir, _now_unix: u64) -> Result<String, NodeIdError> {
    Err(NodeIdError::Malformed) // red: 5c.4a
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::testing::Scratch;

    const NOW: u64 = 1_800_000_000;

    #[test]
    fn the_form_is_rfc_9562_version_4() {
        assert_eq!(format_v4([0; 16]), "00000000-0000-4000-8000-000000000000");
        assert_eq!(
            format_v4([0xff; 16]),
            "ffffffff-ffff-4fff-bfff-ffffffffffff"
        );
        let bytes = [
            0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc, 0xde, 0xf0, 0x0f, 0xed, 0xcb, 0xa9, 0x87, 0x65,
            0x43, 0x21,
        ];
        assert_eq!(format_v4(bytes), "12345678-9abc-4ef0-8fed-cba987654321");
        for text in [
            "00000000-0000-4000-8000-000000000000",
            "12345678-9abc-4ef0-8fed-cba987654321",
        ] {
            assert!(is_v4(text), "{text}");
        }
        for text in [
            "",
            "12345678-9abc-1ef0-8fed-cba987654321", // version 1
            "12345678-9abc-4ef0-cfed-cba987654321", // variant 110
            "12345678-9ABC-4EF0-8FED-CBA987654321", // upper case
            "123456789abc4ef08fedcba987654321",     // no hyphens
            "12345678-9abc-4ef0-8fed-cba98765432",  // short
            "12345678-9abc-4ef0-8fed-cba9876543210",
            "{12345678-9abc-4ef0-8fed-cba987654321}",
            "12345678-9abc-4ef0-8fed-cba98765432g",
        ] {
            assert!(!is_v4(text), "{text}");
        }
    }

    #[test]
    fn it_is_made_once_and_kept() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        assert!(load(&dir).unwrap().is_none());
        let first = ensure(&dir, NOW).unwrap();
        assert!(is_v4(&first), "{first}");
        assert_eq!(load(&dir).unwrap().as_deref(), Some(first.as_str()));
        assert_eq!(ensure(&dir, NOW + 60).unwrap(), first);
        let file: NodeUuidFile = dir.read_json(FILE).unwrap().unwrap();
        assert_eq!(
            file,
            NodeUuidFile {
                uuid: first.clone(),
                created_unix: NOW
            }
        );
        let other = Scratch::new();
        let other = StateDir::open(&other.0).unwrap();
        assert_ne!(ensure(&other, NOW).unwrap(), first, "each node its own");
    }

    #[test]
    fn a_file_that_is_not_a_uuid_is_refused_and_never_replaced() {
        for written in [
            br#"{"uuid":"not a uuid","created_unix":1}"#.as_slice(),
            br#"{"uuid":"12345678-9abc-1ef0-8fed-cba987654321","created_unix":1}"#,
            b"{not json",
            b"",
        ] {
            let scratch = Scratch::new();
            let dir = StateDir::open(&scratch.0).unwrap();
            dir.write(FILE, written).unwrap();
            assert!(
                load(&dir).is_err(),
                "{:?}",
                String::from_utf8_lossy(written)
            );
            assert!(
                ensure(&dir, NOW).is_err(),
                "{:?}",
                String::from_utf8_lossy(written)
            );
            assert_eq!(
                dir.read(FILE).unwrap().unwrap(),
                written,
                "the file is left as it was"
            );
        }
    }
}
