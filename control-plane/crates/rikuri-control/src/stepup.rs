//! Step-up: the owner's password again, at action time, for one action
//! (register port 13, EXEC-03). The token a step-up mints is bound to the
//! exact method and path it was asked for and to the session that asked, lives
//! five minutes and is consumed on first presentation wherever that is:
//! presented at another route it is refused and burned, so a token harvested
//! from a harmless prompt cannot be shopped around for a route that accepts it
//! (the previous node's incident of 2026-08-24). Tokens live in memory only: a
//! restart forgets them, and the owner is asked again.

use std::collections::HashMap;
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};

use crate::random::{self, RandomError};

/// The request header that carries a token.
pub const HEADER: &str = "x-step-up";
pub const LIFETIME: Duration = Duration::from_secs(5 * 60);

/// One action, as the client and the server both see it.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Action {
    pub method: String,
    pub path: String,
}

impl Action {
    /// The method upper-cased; the path without query or fragment, trailing
    /// slashes removed (the root stays `/`), lower-cased.
    pub fn normalize(method: &str, path: &str) -> Self {
        let path = path.split(['?', '#']).next().unwrap_or("");
        let trimmed = path.trim_end_matches('/');
        let path = if trimmed.is_empty() { "/" } else { trimmed };
        Self {
            method: method.trim().to_ascii_uppercase(),
            path: path.to_ascii_lowercase(),
        }
    }
}

#[derive(Debug)]
struct Grant {
    action: Action,
    /// The SHA-256 of the session id that asked, never the id itself.
    session: String,
    expires: Instant,
}

#[derive(Debug, Default)]
pub struct Grants {
    tokens: HashMap<String, Grant>,
}

impl Grants {
    /// Mints a token for `action`, for the session `session` (its id's
    /// SHA-256), good until `now + LIFETIME`.
    pub fn issue(
        &mut self,
        action: Action,
        session: &str,
        now: Instant,
    ) -> Result<String, RandomError> {
        self.prune(now);
        let token = random::token()?;
        self.tokens.insert(
            token.clone(),
            Grant {
                action,
                session: session.to_owned(),
                expires: now + LIFETIME,
            },
        );
        Ok(token)
    }

    /// Consumes `token` whatever happens, and returns true only for the exact
    /// action it was minted for, from the session that minted it, before it
    /// expires.
    pub fn consume(&mut self, token: &str, action: &Action, session: &str, now: Instant) -> bool {
        self.prune(now);
        let Some(grant) = self.tokens.remove(token) else {
            return false;
        };
        grant.expires > now && grant.action == *action && grant.session == session
    }

    pub fn len(&self) -> usize {
        self.tokens.len()
    }

    pub fn is_empty(&self) -> bool {
        self.tokens.is_empty()
    }

    fn prune(&mut self, now: Instant) {
        self.tokens.retain(|_, grant| grant.expires > now);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const SESSION: &str = "session-a";

    fn act(method: &str, path: &str) -> Action {
        Action::normalize(method, path)
    }

    #[test]
    fn authorizes_the_exact_action_it_was_minted_for() {
        let mut g = Grants::default();
        let now = Instant::now();
        let t = g
            .issue(act("POST", "/api/owner/password"), SESSION, now)
            .unwrap();
        assert!(g.consume(&t, &act("POST", "/api/owner/password"), SESSION, now));
    }

    #[test]
    fn refuses_the_same_token_at_a_different_route_and_burns_it() {
        let mut g = Grants::default();
        let now = Instant::now();
        let t = g
            .issue(act("POST", "/api/node-prefs"), SESSION, now)
            .unwrap();
        assert!(!g.consume(&t, &act("POST", "/api/system/shutdown"), SESSION, now));
        // Dead for its own action too: a stolen token cannot be shopped around.
        assert!(!g.consume(&t, &act("POST", "/api/node-prefs"), SESSION, now));
        assert!(g.is_empty());
    }

    #[test]
    fn refuses_the_same_path_with_a_different_method() {
        let mut g = Grants::default();
        let now = Instant::now();
        let t = g
            .issue(act("POST", "/api/onchain/sendcoins"), SESSION, now)
            .unwrap();
        assert!(!g.consume(&t, &act("DELETE", "/api/onchain/sendcoins"), SESSION, now));
    }

    #[test]
    fn stays_single_use_for_its_own_action() {
        let mut g = Grants::default();
        let now = Instant::now();
        let t = g
            .issue(act("PUT", "/api/owner/password"), SESSION, now)
            .unwrap();
        assert!(g.consume(&t, &act("PUT", "/api/owner/password"), SESSION, now));
        assert!(!g.consume(&t, &act("PUT", "/api/owner/password"), SESSION, now));
    }

    #[test]
    fn refuses_an_unknown_or_empty_token() {
        let mut g = Grants::default();
        let now = Instant::now();
        assert!(!g.consume("", &act("POST", "/api/x"), SESSION, now));
        assert!(!g.consume("not-a-token", &act("POST", "/api/x"), SESSION, now));
    }

    #[test]
    fn refuses_another_session_and_burns_the_token() {
        let mut g = Grants::default();
        let now = Instant::now();
        let t = g
            .issue(act("PUT", "/api/owner/password"), SESSION, now)
            .unwrap();
        assert!(!g.consume(&t, &act("PUT", "/api/owner/password"), "session-b", now));
        assert!(!g.consume(&t, &act("PUT", "/api/owner/password"), SESSION, now));
    }

    #[test]
    fn expires_after_its_lifetime() {
        let mut g = Grants::default();
        let now = Instant::now();
        let t = g
            .issue(act("PUT", "/api/owner/password"), SESSION, now)
            .unwrap();
        let later = now + LIFETIME;
        assert!(!g.consume(&t, &act("PUT", "/api/owner/password"), SESSION, later));
        assert!(g.is_empty(), "expired grants are pruned");
        let t2 = g
            .issue(act("PUT", "/api/owner/password"), SESSION, now)
            .unwrap();
        assert!(g.consume(
            &t2,
            &act("PUT", "/api/owner/password"),
            SESSION,
            later - Duration::from_secs(1)
        ));
    }

    #[test]
    fn matching_ignores_case_trailing_slashes_query_and_fragment() {
        let mut g = Grants::default();
        let now = Instant::now();
        let t = g
            .issue(act("put", "/API/Owner/Password/"), SESSION, now)
            .unwrap();
        assert!(g.consume(
            &t,
            &act("PUT", "/api/owner/password?retry=1#x"),
            SESSION,
            now
        ));
    }

    #[test]
    fn normalizes_consistently() {
        assert_eq!(
            act("post", "/API/X/"),
            Action {
                method: "POST".into(),
                path: "/api/x".into()
            }
        );
        assert_eq!(act("GET", "/").path, "/");
        assert_eq!(act("GET", "").path, "/");
        assert_eq!(act("GET", "///").path, "/");
        assert_eq!(act(" get ", "/a?b=c").method, "GET");
    }

    #[test]
    fn expired_grants_are_pruned_when_a_new_one_is_issued() {
        let mut g = Grants::default();
        let now = Instant::now();
        g.issue(act("PUT", "/a"), SESSION, now).unwrap();
        g.issue(act("PUT", "/b"), SESSION, now).unwrap();
        assert_eq!(g.len(), 2);
        g.issue(act("PUT", "/c"), SESSION, now + LIFETIME).unwrap();
        assert_eq!(g.len(), 1, "the two expired grants are gone");
        g.issue(
            act("PUT", "/d"),
            SESSION,
            now + LIFETIME + Duration::from_secs(1),
        )
        .unwrap();
        assert_eq!(g.len(), 2, "a grant lives for its whole lifetime");
    }

    #[test]
    fn tokens_are_64_hex_characters_and_counted() {
        let mut g = Grants::default();
        let now = Instant::now();
        let t = g.issue(act("PUT", "/x"), SESSION, now).unwrap();
        assert_eq!(t.len(), 64);
        assert_eq!(g.len(), 1);
    }
}
