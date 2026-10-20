//! The node's own names, and the two headers checked against them: `Host` on
//! every request, so a page served for another name is refused (DNS
//! rebinding: a site the owner visits resolves its name to the node's address
//! and scripts against it; the browser sends that site's name as `Host`);
//! `Origin` on every mutation, so a request a browser makes from another
//! site is refused whatever cookie it carries (the design note of 2026-10-12;
//! the review's §3.7). An IP literal is an allowed `Host`: the setup page is
//! reached by address where `.local` does not resolve (plan §8, stage 1), and
//! rebinding needs a name.

use std::collections::BTreeSet;
use std::fmt;
use std::net::{Ipv4Addr, Ipv6Addr};

/// The environment variable with the node's names, comma-separated.
pub const ENV: &str = "RIKURI_NAMES";
/// Always allowed: the console and the tests reach the node as `localhost`.
pub const LOCALHOST: &str = "localhost";

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Names {
    names: BTreeSet<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NameError {
    /// Not a host name: empty, a port or path attached, or a character outside
    /// letters, digits, hyphens and dots.
    Invalid(String),
}

impl fmt::Display for NameError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            NameError::Invalid(name) => write!(
                f,
                "{ENV}: {name:?} is not a host name (letters, digits, hyphens and dots; no port, no path)"
            ),
        }
    }
}

impl std::error::Error for NameError {}

impl Names {
    /// `localhost` plus `names`, lower-cased.
    pub fn new<I, S>(names: I) -> Result<Self, NameError>
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        let mut set = BTreeSet::new();
        set.insert(LOCALHOST.to_owned());
        for name in names {
            let lower = name.as_ref().trim().to_ascii_lowercase();
            if !valid_name(&lower) {
                return Err(NameError::Invalid(name.as_ref().to_owned()));
            }
            set.insert(lower);
        }
        Ok(Self { names: set })
    }

    /// The environment's form: names separated by commas; blanks ignored.
    pub fn from_list(list: &str) -> Result<Self, NameError> {
        Self::new(list.split(',').map(str::trim).filter(|s| !s.is_empty()))
    }

    /// Every allowed name, `localhost` included, in order.
    pub fn iter(&self) -> impl Iterator<Item = &str> {
        self.names.iter().map(String::as_str)
    }

    /// Whether a `Host` header value is the node: an IP literal (with or
    /// without a port), or one of the names (with or without a port).
    pub fn host_allowed(&self, host: &str) -> bool {
        match split_host(host) {
            Some(Host::Ip) => true,
            Some(Host::Name(name)) => self.names.contains(&name),
            None => false,
        }
    }

    /// Whether an `Origin` header value is the node's own page: exactly
    /// `https://` and an allowed host, nothing after it. `null` and any other
    /// scheme are refused.
    pub fn origin_allowed(&self, origin: &str) -> bool {
        let Some(host) = origin.strip_prefix("https://") else {
            return false;
        };
        !host.is_empty() && !host.contains('/') && self.host_allowed(host)
    }
}

enum Host {
    /// An IP literal; which one does not matter to the rule.
    Ip,
    Name(String),
}

/// `host[:port]` or `[v6][:port]`, as a `Host` header or the authority of an
/// `Origin` carries it. Returns the host part; refuses anything else.
fn split_host(raw: &str) -> Option<Host> {
    let raw = raw.trim();
    if raw.is_empty() {
        return None;
    }
    if let Some(rest) = raw.strip_prefix('[') {
        let end = rest.find(']')?;
        rest[..end].parse::<Ipv6Addr>().ok()?;
        let after = &rest[end + 1..];
        let port_ok = match after.strip_prefix(':') {
            None => after.is_empty(),
            Some(port) => valid_port(port),
        };
        return port_ok.then_some(Host::Ip);
    }
    let host = match raw.rsplit_once(':') {
        // A bare IPv6 address has several colons and no brackets: not a Host.
        Some((host, _)) if host.contains(':') => return None,
        Some((host, port)) => {
            if !valid_port(port) {
                return None;
            }
            host
        }
        None => raw,
    };
    if host.is_empty() {
        return None;
    }
    if host.parse::<Ipv4Addr>().is_ok() {
        return Some(Host::Ip);
    }
    let lower = host.to_ascii_lowercase();
    valid_name(&lower).then_some(Host::Name(lower))
}

fn valid_port(port: &str) -> bool {
    !port.is_empty() && port.len() <= 5 && port.bytes().all(|b| b.is_ascii_digit())
}

/// A lower-case host name: labels of letters, digits and inner hyphens.
fn valid_name(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 253
        && name.split('.').all(|label| {
            !label.is_empty()
                && label.len() <= 63
                && !label.starts_with('-')
                && !label.ends_with('-')
                && label
                    .bytes()
                    .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn names() -> Names {
        Names::new(["rikuri01.local", "RikuriSetup.local"]).unwrap()
    }

    #[test]
    fn localhost_is_always_there_and_names_are_lower_cased() {
        let n = names();
        assert_eq!(
            n.iter().collect::<Vec<_>>(),
            ["localhost", "rikuri01.local", "rikurisetup.local"]
        );
        assert_eq!(
            Names::new::<[&str; 0], &str>([])
                .unwrap()
                .iter()
                .collect::<Vec<_>>(),
            ["localhost"]
        );
    }

    #[test]
    fn the_environment_list_is_split_on_commas_and_blanks_ignored() {
        let n = Names::from_list(" rikuri01.local, ,RikuriSetup.local ").unwrap();
        assert_eq!(n, names());
        assert_eq!(
            Names::from_list("").unwrap(),
            Names::new::<[&str; 0], &str>([]).unwrap()
        );
    }

    #[test]
    fn a_name_with_a_port_a_path_a_space_or_an_odd_character_is_refused() {
        for bad in [
            "a b",
            "rikuri01.local:443",
            "rikuri01.local/x",
            "-a.b",
            "a-.b",
            "a..b",
            "ü.local",
            "",
        ] {
            let err = Names::new([bad]).unwrap_err();
            assert_eq!(err, NameError::Invalid(bad.to_owned()), "{bad:?}");
            assert!(err.to_string().contains(ENV), "{err}");
        }
    }

    #[test]
    fn hosts_that_are_the_node() {
        let n = names();
        for host in [
            "localhost",
            "LOCALHOST:8443",
            "rikuri01.local",
            "RikuriSetup.local:443",
            "127.0.0.1",
            "127.0.0.1:8443",
            "192.168.1.50",
            "[::1]",
            "[::1]:8443",
            "[fe80::1]:443",
            " localhost ",
        ] {
            assert!(n.host_allowed(host), "{host:?}");
        }
    }

    #[test]
    fn hosts_that_are_not_the_node() {
        let n = names();
        for host in [
            "evil.example",
            "rikuri01.local.evil.example",
            "evil.example:443",
            "",
            "localhost:abc",
            "localhost:",
            "localhost:123456",
            "::1",
            "[::1",
            "[::1]x",
            "[not-an-ip]",
            "localhost/x",
            "user@localhost",
            "https://localhost",
        ] {
            assert!(!n.host_allowed(host), "{host:?}");
        }
    }

    #[test]
    fn origins_that_are_the_nodes_own_page() {
        let n = names();
        for origin in [
            "https://localhost",
            "https://localhost:8443",
            "https://rikuri01.local",
            "https://192.168.1.50",
            "https://[::1]:8443",
        ] {
            assert!(n.origin_allowed(origin), "{origin:?}");
        }
    }

    #[test]
    fn origins_that_are_not() {
        let n = names();
        for origin in [
            "http://localhost:8443",
            "https://evil.example",
            "https://localhost.evil.example",
            "null",
            "",
            "https://",
            "https://localhost/",
            "https://localhost/path",
            "HTTPS://localhost",
            "localhost",
            "https://user@localhost",
        ] {
            assert!(!n.origin_allowed(origin), "{origin:?}");
        }
    }
}
