//! Passwords and the claim code at rest: argon2id with the crate's defaults
//! (19 MiB, two passes, one lane: OWASP's current minimum), a fresh 16-byte
//! salt each time, the PHC string kept. Verification is the hash's own
//! constant-time comparison. Hashing is slow by design, so callers run it off
//! the request thread. The policy: at least 12 characters, at most 1,024
//! bytes, no composition rules (the review's §3.7).

use std::fmt;

use argon2::{Argon2, PasswordHasher, PasswordVerifier};

use crate::random;

pub const MIN_CHARS: usize = 12;
pub const MAX_BYTES: usize = 1024;
const SALT_LEN: usize = 16;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PolicyError {
    TooShort { chars: usize },
    TooLong { bytes: usize },
}

impl fmt::Display for PolicyError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PolicyError::TooShort { chars } => {
                write!(
                    f,
                    "a password needs at least {MIN_CHARS} characters ({chars} given)"
                )
            }
            PolicyError::TooLong { bytes } => {
                write!(
                    f,
                    "a password can have at most {MAX_BYTES} bytes ({bytes} given)"
                )
            }
        }
    }
}

impl std::error::Error for PolicyError {}

/// Length only: characters are Unicode scalar values, so a word in any script
/// counts as its letters.
pub fn check_policy(password: &str) -> Result<(), PolicyError> {
    let bytes = password.len();
    if bytes > MAX_BYTES {
        return Err(PolicyError::TooLong { bytes });
    }
    let chars = password.chars().count();
    if chars < MIN_CHARS {
        return Err(PolicyError::TooShort { chars });
    }
    Ok(())
}

/// Hashing failed (the random source, or argon2 itself); never the secret.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HashError(String);

impl fmt::Display for HashError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "cannot hash: {}", self.0)
    }
}

impl std::error::Error for HashError {}

/// The PHC string of `secret` under argon2id with a fresh salt.
pub fn hash(secret: &str) -> Result<String, HashError> {
    let salt = random::bytes::<SALT_LEN>().map_err(|e| HashError(e.to_string()))?;
    Argon2::default()
        .hash_password_with_salt(secret.as_bytes(), &salt)
        .map(|hash| hash.to_string())
        .map_err(|e| HashError(e.to_string()))
}

/// Whether `secret` is the one behind `phc`. Anything that is not a verified
/// match, a malformed string included, is `false`.
pub fn verify(secret: &str, phc: &str) -> bool {
    Argon2::default()
        .verify_password(secret.as_bytes(), phc)
        .is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_hash_is_argon2id_with_a_fresh_salt_and_verifies() {
        let a = hash("correct horse battery staple").unwrap();
        let b = hash("correct horse battery staple").unwrap();
        assert!(a.starts_with("$argon2id$v=19$m=19456,t=2,p=1$"), "{a}");
        assert_ne!(a, b, "a fresh salt each time");
        assert!(verify("correct horse battery staple", &a));
        assert!(verify("correct horse battery staple", &b));
        assert!(!verify("correct horse battery stapl", &a));
        assert!(!verify("", &a));
    }

    #[test]
    fn a_malformed_or_foreign_hash_verifies_nothing() {
        for phc in [
            "",
            "not a hash",
            "$argon2id$v=19$m=19456,t=2,p=1$",
            "$2b$12$abcdefghijklmnopqrstuu",
        ] {
            assert!(!verify("correct horse battery staple", phc), "{phc:?}");
        }
    }

    #[test]
    fn the_policy_is_length_only() {
        assert_eq!(
            check_policy("elevenchars"),
            Err(PolicyError::TooShort { chars: 11 })
        );
        assert_eq!(check_policy("twelve chars"), Ok(()));
        assert_eq!(check_policy("            "), Ok(()), "no composition rules");
        assert_eq!(
            check_policy(&"ñ".repeat(12)),
            Ok(()),
            "characters, not bytes"
        );
        assert_eq!(
            check_policy(&"ñ".repeat(11)),
            Err(PolicyError::TooShort { chars: 11 })
        );
        assert_eq!(check_policy(&"a".repeat(1024)), Ok(()));
        assert_eq!(
            check_policy(&"a".repeat(1025)),
            Err(PolicyError::TooLong { bytes: 1025 })
        );
    }

    #[test]
    fn policy_messages_say_the_rule() {
        let short = PolicyError::TooShort { chars: 3 }.to_string();
        assert!(short.contains("12") && short.contains("3 given"), "{short}");
        let long = PolicyError::TooLong { bytes: 2000 }.to_string();
        assert!(
            long.contains("1024") && long.contains("2000 given"),
            "{long}"
        );
    }
}
