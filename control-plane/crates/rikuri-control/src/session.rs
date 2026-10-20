//! Sessions: an opaque random id in a cookie the browser cannot read
//! (`HttpOnly`), sends only over TLS (`Secure`) and only to this site
//! (`SameSite=Strict`), revocable server-side, 30 days long by default so daily
//! use is one tap (the review's §3.7); a CSRF token beside it, required on
//! every mutation. The store keeps the SHA-256 of each id, so the file alone
//! opens nothing.
//!
//! Register port 46 (SEC-05), adapted from JWT `exp` and `iss` to sessions: a
//! record admits a caller only if it has not expired and its issuer is this
//! node's instance id, and both fields are required by the type, so a record
//! without them does not parse and a file that does not parse admits nobody.

use std::fmt;
use std::sync::{Arc, Mutex};

use secrecy::SecretString;
use serde::{Deserialize, Serialize};
use tracing::warn;

use crate::random::{self, RandomError};
use crate::state::{StateDir, StateError};

pub const FILE: &str = "sessions.json";
pub const COOKIE: &str = "rikuri_session";
pub const CSRF_HEADER: &str = "x-csrf-token";
/// The owner's reversible default: 30 days.
pub const LIFETIME_SECS: u64 = 30 * 24 * 60 * 60;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Record {
    /// SHA-256 of the session id, in hex.
    pub id_sha256: String,
    pub csrf: String,
    /// The node instance that opened the session.
    pub issuer: String,
    pub issued_unix: u64,
    pub expires_unix: u64,
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct SessionsFile {
    pub sessions: Vec<Record>,
}

/// The rule (port 46): this node's issuer, and not yet expired.
pub fn verify_record(record: &Record, issuer: &str, now_unix: u64) -> bool {
    record.issuer == issuer && record.expires_unix > now_unix
}

#[derive(Debug)]
pub enum SessionError {
    State(StateError),
    Random(RandomError),
}

impl fmt::Display for SessionError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SessionError::State(e) => write!(f, "sessions: {e}"),
            SessionError::Random(e) => write!(f, "sessions: {e}"),
        }
    }
}

impl std::error::Error for SessionError {}

impl From<StateError> for SessionError {
    fn from(e: StateError) -> Self {
        SessionError::State(e)
    }
}

impl From<RandomError> for SessionError {
    fn from(e: RandomError) -> Self {
        SessionError::Random(e)
    }
}

#[derive(Clone, Debug)]
pub struct Store {
    dir: StateDir,
    issuer: String,
    /// Writers go one at a time: each write is load, change, save, and two
    /// at once would let the second save the first's record away (a
    /// sign-out racing a sign-in would resurrect the revoked session).
    writing: Arc<Mutex<()>>,
}

impl Store {
    pub fn new(dir: StateDir, issuer: String) -> Self {
        Self {
            dir,
            issuer,
            writing: Arc::new(Mutex::new(())),
        }
    }

    /// The writers' turn. A poisoned lock (a writer panicked) is taken over:
    /// the file itself is always whole, by the atomic write.
    fn write_turn(&self) -> std::sync::MutexGuard<'_, ()> {
        self.writing
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
    }

    pub fn issuer(&self) -> &str {
        &self.issuer
    }

    /// The file as it is; a file that does not parse is an error, and the
    /// caller admits nobody.
    fn load(&self) -> Result<SessionsFile, SessionError> {
        Ok(self.dir.read_json(FILE)?.unwrap_or_default())
    }

    /// The file for writing: a file that does not parse is replaced by an
    /// empty one, said aloud, so the owner can sign in again.
    fn load_for_write(&self) -> Result<SessionsFile, SessionError> {
        match self.load() {
            Ok(file) => Ok(file),
            Err(SessionError::State(StateError::Json { path, source })) => {
                warn!(path = %path.display(), error = %source, "sessions file unreadable: starting over, every session revoked");
                Ok(SessionsFile::default())
            }
            Err(e) => Err(e),
        }
    }

    fn save(&self, file: &SessionsFile) -> Result<(), SessionError> {
        Ok(self.dir.write_json(FILE, file)?)
    }

    /// Opens a session at `now_unix`: the id (the cookie's value, in clear only
    /// here and in the response that sets it) and its record.
    pub fn create(&self, now_unix: u64) -> Result<(SecretString, Record), SessionError> {
        let id = random::token()?;
        let record = Record {
            id_sha256: random::sha256_hex(id.as_bytes()),
            csrf: random::token()?,
            issuer: self.issuer.clone(),
            issued_unix: now_unix,
            expires_unix: now_unix.saturating_add(LIFETIME_SECS),
        };
        let _turn = self.write_turn();
        let mut file = self.load_for_write()?;
        file.sessions
            .retain(|r| verify_record(r, &self.issuer, now_unix));
        file.sessions.push(record.clone());
        self.save(&file)?;
        Ok((SecretString::from(id), record))
    }

    /// The record of a presented id, if it admits the caller at `now_unix`.
    pub fn verify(&self, id: &str, now_unix: u64) -> Result<Option<Record>, SessionError> {
        if !well_formed(id) {
            return Ok(None);
        }
        let sha = random::sha256_hex(id.as_bytes());
        let file = self.load()?;
        Ok(file
            .sessions
            .into_iter()
            .find(|r| r.id_sha256 == sha)
            .filter(|r| verify_record(r, &self.issuer, now_unix)))
    }

    /// Revokes the session with this id; `Ok(false)` if there was none.
    pub fn revoke(&self, id: &str) -> Result<bool, SessionError> {
        let sha = random::sha256_hex(id.as_bytes());
        let _turn = self.write_turn();
        let mut file = self.load_for_write()?;
        let before = file.sessions.len();
        file.sessions.retain(|r| r.id_sha256 != sha);
        let removed = file.sessions.len() != before;
        self.save(&file)?;
        Ok(removed)
    }

    /// Revokes every session but the one whose id hash is `keep_sha256`;
    /// returns how many went.
    pub fn revoke_others(&self, keep_sha256: &str) -> Result<usize, SessionError> {
        let _turn = self.write_turn();
        let mut file = self.load_for_write()?;
        let before = file.sessions.len();
        file.sessions.retain(|r| r.id_sha256 == keep_sha256);
        self.save(&file)?;
        Ok(before - file.sessions.len())
    }

    /// How many records the file holds, live or not.
    pub fn count(&self) -> Result<usize, SessionError> {
        Ok(self.load()?.sessions.len())
    }
}

/// A session id is 64 lower-case hex characters; anything else is refused
/// before it is hashed.
fn well_formed(id: &str) -> bool {
    id.len() == 64
        && id
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

/// The session id in a `Cookie` header, if the header carries one.
pub fn cookie_value(cookie_header: &str) -> Option<&str> {
    cookie_header
        .split(';')
        .map(str::trim)
        .find_map(|pair| {
            pair.strip_prefix(COOKIE)
                .and_then(|rest| rest.strip_prefix('='))
        })
        .filter(|value| !value.is_empty())
}

/// The `Set-Cookie` value that opens a session in the browser.
pub fn set_cookie(id: &str) -> String {
    format!("{COOKIE}={id}; Path=/; Max-Age={LIFETIME_SECS}; HttpOnly; Secure; SameSite=Strict")
}

/// The `Set-Cookie` value that removes it.
pub fn clear_cookie() -> String {
    format!("{COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict")
}

#[cfg(test)]
mod tests {
    use secrecy::ExposeSecret;

    use super::*;
    use crate::state::testing::Scratch;

    const NOW: u64 = 1_800_000_000;
    const ISSUER: &str = "node-a";

    fn store() -> (Scratch, Store) {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        (scratch, Store::new(dir, ISSUER.to_owned()))
    }

    fn record(issuer: &str, expires_unix: u64) -> Record {
        Record {
            id_sha256: "x".repeat(64),
            csrf: "c".repeat(64),
            issuer: issuer.to_owned(),
            issued_unix: NOW,
            expires_unix,
        }
    }

    // Port 46: the record rule, with one thing different in each refusal.
    #[test]
    fn a_record_of_this_node_before_expiry_verifies() {
        assert!(verify_record(&record(ISSUER, NOW + 1), ISSUER, NOW));
    }

    #[test]
    fn a_record_from_another_issuer_is_refused() {
        assert!(!verify_record(
            &record("someone-else", NOW + 1),
            ISSUER,
            NOW
        ));
        assert!(!verify_record(&record("", NOW + 1), ISSUER, NOW));
    }

    #[test]
    fn an_expired_record_is_refused_at_the_second_it_expires() {
        assert!(!verify_record(&record(ISSUER, NOW), ISSUER, NOW));
        assert!(!verify_record(&record(ISSUER, NOW - 3600), ISSUER, NOW));
    }

    #[test]
    fn a_record_without_issuer_or_expiry_does_not_parse() {
        let without_issuer = r#"{"id_sha256":"a","csrf":"b","issued_unix":1,"expires_unix":2}"#;
        assert!(serde_json::from_str::<Record>(without_issuer).is_err());
        let without_expiry = r#"{"id_sha256":"a","csrf":"b","issuer":"node-a","issued_unix":1}"#;
        assert!(serde_json::from_str::<Record>(without_expiry).is_err());
        let expiry_as_text = r#"{"id_sha256":"a","csrf":"b","issuer":"node-a","issued_unix":1,"expires_unix":"9999999999"}"#;
        assert!(serde_json::from_str::<Record>(expiry_as_text).is_err());
    }

    #[test]
    fn a_session_we_opened_verifies_and_is_stored_only_as_a_hash() {
        let (_scratch, store) = store();
        let (id, record) = store.create(NOW).unwrap();
        let id = id.expose_secret().to_owned();
        assert_eq!(id.len(), 64);
        assert_eq!(record.issuer, ISSUER);
        assert_eq!(record.expires_unix, NOW + LIFETIME_SECS);
        assert_eq!(record.id_sha256, random::sha256_hex(id.as_bytes()));
        let raw = String::from_utf8(store.dir.read(FILE).unwrap().unwrap()).unwrap();
        assert!(!raw.contains(&id), "the id itself is never written");
        assert!(raw.contains(&record.csrf));
        assert_eq!(store.verify(&id, NOW + 10).unwrap(), Some(record));
    }

    #[test]
    fn verification_refuses_an_unknown_malformed_expired_or_foreign_session() {
        let (_scratch, store) = store();
        let (id, _) = store.create(NOW).unwrap();
        let id = id.expose_secret().to_owned();
        assert_eq!(store.verify(&"0".repeat(64), NOW).unwrap(), None, "unknown");
        assert_eq!(store.verify("", NOW).unwrap(), None, "empty");
        assert_eq!(store.verify(&id[..63], NOW).unwrap(), None, "short");
        assert_eq!(
            store.verify(&id.to_uppercase(), NOW).unwrap(),
            None,
            "wrong form"
        );
        assert_eq!(
            store.verify(&id, NOW + LIFETIME_SECS).unwrap(),
            None,
            "expired"
        );
        let foreign = Store::new(store.dir.clone(), "node-b".to_owned());
        assert_eq!(
            foreign.verify(&id, NOW).unwrap(),
            None,
            "another node's file"
        );
    }

    #[test]
    fn sessions_survive_a_restart_of_the_store() {
        let (_scratch, store) = store();
        let (id, record) = store.create(NOW).unwrap();
        let reopened = Store::new(store.dir.clone(), ISSUER.to_owned());
        assert_eq!(
            reopened.verify(id.expose_secret(), NOW + 1).unwrap(),
            Some(record)
        );
    }

    #[test]
    fn revocation_is_server_side_and_the_cookie_is_dead_afterwards() {
        let (_scratch, store) = store();
        let (id, _) = store.create(NOW).unwrap();
        let id = id.expose_secret().to_owned();
        assert!(store.revoke(&id).unwrap());
        assert_eq!(store.verify(&id, NOW).unwrap(), None);
        assert!(!store.revoke(&id).unwrap());
    }

    #[test]
    fn revoking_the_others_keeps_only_the_named_session() {
        let (_scratch, store) = store();
        let (a, ra) = store.create(NOW).unwrap();
        let (b, _) = store.create(NOW).unwrap();
        let (c, _) = store.create(NOW).unwrap();
        assert_eq!(store.revoke_others(&ra.id_sha256).unwrap(), 2);
        assert!(store.verify(a.expose_secret(), NOW).unwrap().is_some());
        assert!(store.verify(b.expose_secret(), NOW).unwrap().is_none());
        assert!(store.verify(c.expose_secret(), NOW).unwrap().is_none());
        assert_eq!(store.count().unwrap(), 1);
    }

    #[test]
    fn expired_sessions_are_pruned_when_a_new_one_opens() {
        let (_scratch, store) = store();
        store.create(NOW).unwrap();
        store.create(NOW).unwrap();
        assert_eq!(store.count().unwrap(), 2);
        store.create(NOW + LIFETIME_SECS).unwrap();
        assert_eq!(store.count().unwrap(), 1);
    }

    #[test]
    fn an_unreadable_file_admits_nobody_and_is_replaced_by_the_next_sign_in() {
        let (_scratch, store) = store();
        let (id, _) = store.create(NOW).unwrap();
        store.dir.write(FILE, b"{ not json").unwrap();
        assert!(
            store.verify(id.expose_secret(), NOW).is_err(),
            "fails closed"
        );
        let (fresh, _) = store.create(NOW).unwrap();
        assert!(store.verify(fresh.expose_secret(), NOW).unwrap().is_some());
        assert_eq!(
            store.verify(id.expose_secret(), NOW).unwrap(),
            None,
            "the old session is gone"
        );
        assert_eq!(store.count().unwrap(), 1);
    }

    #[test]
    fn a_session_id_is_exactly_64_lower_case_hex_characters() {
        assert!(well_formed(&"0123456789abcdef".repeat(4)));
        assert!(
            !well_formed(&"0123456789abcdef".repeat(4)[..63]),
            "too short"
        );
        assert!(
            !well_formed(&("0123456789abcdef".repeat(4) + "0")),
            "too long"
        );
        assert!(!well_formed(&"0123456789ABCDEF".repeat(4)), "upper case");
        assert!(!well_formed(&"0123456789abcdeg".repeat(4)), "not hex");
        assert!(!well_formed(""));
    }

    #[test]
    fn concurrent_writers_lose_no_revocation() {
        // Sixteen threads each open and then revoke their own session while
        // the others do the same: no revoked session may survive, and no
        // live one may be lost to another thread's save.
        let (_scratch, store) = store();
        let (keep, _) = store.create(NOW).unwrap();
        let handles: Vec<_> = (0..16)
            .map(|_| {
                let store = store.clone();
                std::thread::spawn(move || {
                    let (id, _) = store.create(NOW).unwrap();
                    assert!(store.revoke(id.expose_secret()).unwrap());
                })
            })
            .collect();
        for handle in handles {
            handle.join().unwrap();
        }
        assert_eq!(store.count().unwrap(), 1);
        assert!(store.verify(keep.expose_secret(), NOW).unwrap().is_some());
    }

    #[test]
    fn the_cookie_is_found_among_others_and_carries_every_flag() {
        assert_eq!(cookie_value("rikuri_session=abc"), Some("abc"));
        assert_eq!(
            cookie_value("theme=dark; rikuri_session=abc; other=1"),
            Some("abc")
        );
        assert_eq!(
            cookie_value("rikuri_session_old=zzz; rikuri_session=abc"),
            Some("abc")
        );
        assert_eq!(cookie_value("rikuri_session="), None);
        assert_eq!(cookie_value("theme=dark"), None);
        assert_eq!(cookie_value(""), None);
        let set = set_cookie("abc");
        for flag in [
            "rikuri_session=abc",
            "Path=/",
            "Max-Age=2592000",
            "HttpOnly",
            "Secure",
            "SameSite=Strict",
        ] {
            assert!(set.contains(flag), "{set}");
        }
        let clear = clear_cookie();
        assert!(clear.starts_with("rikuri_session=;"), "{clear}");
        assert!(clear.contains("Max-Age=0"), "{clear}");
    }
}
