//! The node's own names, and the two headers checked against them: `Host` on
//! every request, so a page served for another name is refused (DNS
//! rebinding: a site the owner visits resolves its name to the node's address
//! and scripts against it; the browser sends that site's name as `Host`);
//! `Origin` on every mutation, so a request a browser makes from another
//! site is refused whatever cookie it carries (the design note of 2026-10-12;
//! the review's §3.7). An IP literal is an allowed `Host`: the setup page is
//! reached by address where `.local` does not resolve (plan §8, stage 1), and
//! rebinding needs a name.
//!
//! 5c.4b-1: the names in force are [`LiveNames`]: the configured ones and the
//! node's own `<name>.local`, read again from its hostname file, so a rename
//! changes the checks and the certificate together, with no restart.

use std::collections::BTreeSet;
use std::fmt;
use std::net::{Ipv4Addr, Ipv6Addr};
use std::path::{Path, PathBuf};
use std::sync::{PoisonError, RwLock};

use tracing::{info, warn};

use crate::hostname::{self, NodeName};

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

impl Names {
    /// These names and `name`'s `.local` one.
    pub fn with(&self, name: &NodeName) -> Names {
        let mut names = self.names.clone();
        names.insert(name.local());
        Names { names }
    }
}

/// The names in force (5c.4b-1): the configured ones, and the node's own
/// `<name>.local` from its hostname file (the static name hostnamed keeps),
/// read again on each [`reload`](Self::reload). A file that cannot be read,
/// or names no node name, leaves the configured names alone: the node still
/// answers by address.
pub struct LiveNames {
    configured: Names,
    file: PathBuf,
    current: RwLock<Names>,
}

impl LiveNames {
    pub fn load(configured: Names, file: PathBuf) -> Self {
        let (current, named) = compose(&configured, &file);
        if !named {
            warn_unnamed(&file);
        }
        Self {
            configured,
            file,
            current: RwLock::new(current),
        }
    }

    /// The names now in force.
    pub fn get(&self) -> Names {
        self.current
            .read()
            .unwrap_or_else(PoisonError::into_inner)
            .clone()
    }

    pub fn host_allowed(&self, host: &str) -> bool {
        self.current
            .read()
            .unwrap_or_else(PoisonError::into_inner)
            .host_allowed(host)
    }

    pub fn origin_allowed(&self, origin: &str) -> bool {
        self.current
            .read()
            .unwrap_or_else(PoisonError::into_inner)
            .origin_allowed(origin)
    }

    /// Reads the hostname file again; the names now in force.
    pub fn reload(&self) -> Names {
        let (fresh, named) = compose(&self.configured, &self.file);
        let mut current = self.current.write().unwrap_or_else(PoisonError::into_inner);
        if *current != fresh {
            // Repair 2 (verifier, nit 5): a file that stops naming the node
            // drops its name; say so as loudly as at the start.
            if !named {
                warn_unnamed(&self.file);
            }
            info!(
                names = ?fresh.iter().collect::<Vec<_>>(),
                "the node's names changed"
            );
            *current = fresh.clone();
        }
        fresh
    }
}

/// The names in force, and whether the file named the node.
fn compose(configured: &Names, file: &Path) -> (Names, bool) {
    match std::fs::read_to_string(file)
        .ok()
        .and_then(|text| hostname::name_in(&text))
    {
        Some(name) => (configured.with(&name), true),
        None => (configured.clone(), false),
    }
}

fn warn_unnamed(file: &Path) {
    warn!(
        file = %file.display(),
        "the hostname file names no node name: the node answers by address and its configured names only"
    );
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

    fn file(name: &str, text: Option<&str>) -> PathBuf {
        let path = std::env::temp_dir().join(format!(
            "rikuri-names-{}-{name}.hostname",
            std::process::id()
        ));
        match text {
            Some(text) => std::fs::write(&path, text).unwrap(),
            None => {
                let _ = std::fs::remove_file(&path);
            }
        }
        path
    }

    fn list(names: &Names) -> Vec<&str> {
        names.iter().collect()
    }

    #[test]
    fn the_node_answers_as_its_hostnames_local_name_beside_the_configured_ones() {
        let path = file("load", Some("# hostname(5)\nRikuriSetup\n"));
        let live = LiveNames::load(Names::new(["extra.local"]).unwrap(), path.clone());
        assert_eq!(
            list(&live.get()),
            ["extra.local", "localhost", "rikurisetup.local"]
        );
        assert!(live.host_allowed("rikurisetup.local:443"));
        assert!(live.origin_allowed("https://rikurisetup.local"));
        assert!(!live.host_allowed("rikuri02.local"));
        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn a_reload_follows_the_file_and_the_old_name_leaves() {
        let path = file("reload", Some("rikurisetup\n"));
        let live = LiveNames::load(Names::new::<[&str; 0], &str>([]).unwrap(), path.clone());
        std::fs::write(&path, "rikuri02\n").unwrap();
        assert!(
            live.host_allowed("rikurisetup.local"),
            "not before a reload"
        );
        assert_eq!(list(&live.reload()), ["localhost", "rikuri02.local"]);
        assert_eq!(list(&live.get()), ["localhost", "rikuri02.local"]);
        assert!(!live.host_allowed("rikurisetup.local"));
        assert!(!live.origin_allowed("https://rikurisetup.local"));
        assert!(live.origin_allowed("https://rikuri02.local"));
        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn no_file_or_no_node_name_leaves_the_configured_names() {
        let configured = Names::new(["extra.local"]).unwrap();
        for (case, text) in [
            ("missing", None),
            ("blank", Some("\n# nothing\n")),
            ("dotted", Some("rikuri.example.org\n")),
            ("odd", Some("not a name\n")),
        ] {
            let path = file(case, text);
            let live = LiveNames::load(configured.clone(), path.clone());
            assert_eq!(live.get(), configured, "{case}");
            assert_eq!(live.reload(), configured, "{case}");
            let _ = std::fs::remove_file(path);
        }
    }
}
