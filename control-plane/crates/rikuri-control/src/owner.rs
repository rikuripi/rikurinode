//! The owner: one account, a password set on the setup page (D11, "web
//! sign-in only"). Only argon2id of the password is kept, in a 0600 file. No
//! owner file means nothing verifies: authentication fails closed (EXEC-05).

use std::fmt;

use serde::{Deserialize, Serialize};

use crate::password::{self, HashError, PolicyError};
use crate::state::{StateDir, StateError};

pub const FILE: &str = "owner.json";

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct OwnerFile {
    pub password_hash: String,
    pub set_unix: u64,
}

#[derive(Debug)]
pub enum OwnerError {
    Policy(PolicyError),
    State(StateError),
    Hash(HashError),
}

impl fmt::Display for OwnerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            OwnerError::Policy(e) => write!(f, "{e}"),
            OwnerError::State(e) => write!(f, "owner state: {e}"),
            OwnerError::Hash(e) => write!(f, "owner password: {e}"),
        }
    }
}

impl std::error::Error for OwnerError {}

impl From<PolicyError> for OwnerError {
    fn from(e: PolicyError) -> Self {
        OwnerError::Policy(e)
    }
}

impl From<StateError> for OwnerError {
    fn from(e: StateError) -> Self {
        OwnerError::State(e)
    }
}

impl From<HashError> for OwnerError {
    fn from(e: HashError) -> Self {
        OwnerError::Hash(e)
    }
}

pub fn exists(dir: &StateDir) -> bool {
    dir.exists(FILE)
}

pub fn load(dir: &StateDir) -> Result<Option<OwnerFile>, OwnerError> {
    Ok(dir.read_json(FILE)?)
}

/// Sets (or replaces) the owner's password after the policy check. Slow by
/// design (argon2id): call it off the request thread.
pub fn set_password(dir: &StateDir, password: &str, now_unix: u64) -> Result<(), OwnerError> {
    password::check_policy(password)?;
    let password_hash = password::hash(password)?;
    dir.write_json(
        FILE,
        &OwnerFile {
            password_hash,
            set_unix: now_unix,
        },
    )?;
    Ok(())
}

/// Whether `password` is the owner's. No owner, or an unreadable owner file,
/// verifies nothing. Slow by design (argon2id): call it off the request
/// thread.
pub fn verify_password(dir: &StateDir, password: &str) -> Result<bool, OwnerError> {
    match load(dir)? {
        Some(owner) => Ok(password::verify(password, &owner.password_hash)),
        None => Ok(false),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::testing::Scratch;

    const NOW: u64 = 1_800_000_000;

    #[test]
    fn no_owner_verifies_nothing() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        assert!(!exists(&dir));
        assert!(!verify_password(&dir, "correct horse battery").unwrap());
    }

    #[test]
    fn the_password_is_kept_only_as_argon2id_and_verifies() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        set_password(&dir, "correct horse battery staple", NOW).unwrap();
        assert!(exists(&dir));
        let owner = load(&dir).unwrap().unwrap();
        assert!(
            owner.password_hash.starts_with("$argon2id$"),
            "{}",
            owner.password_hash
        );
        assert!(!owner.password_hash.contains("horse"));
        assert_eq!(owner.set_unix, NOW);
        assert!(verify_password(&dir, "correct horse battery staple").unwrap());
        assert!(!verify_password(&dir, "correct horse battery stapl").unwrap());
        assert!(!verify_password(&dir, "").unwrap());
    }

    #[test]
    fn a_password_against_the_policy_is_refused_and_nothing_is_written() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        let err = set_password(&dir, "elevenchars", NOW).unwrap_err();
        assert!(matches!(err, OwnerError::Policy(_)), "{err}");
        assert!(!exists(&dir));
    }

    #[test]
    fn replacing_the_password_retires_the_old_one() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        set_password(&dir, "first password here", NOW).unwrap();
        set_password(&dir, "second password here", NOW + 1).unwrap();
        assert!(!verify_password(&dir, "first password here").unwrap());
        assert!(verify_password(&dir, "second password here").unwrap());
    }

    #[test]
    fn an_unreadable_owner_file_is_an_error_not_a_pass() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        dir.write(FILE, b"{ broken").unwrap();
        assert!(verify_password(&dir, "whatever password").is_err());
    }
}
