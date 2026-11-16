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
    current: RwLock<Read>,
}

impl LiveNames {
    pub fn load(configured: Names, file: PathBuf) -> Self {
        let current = compose(&configured, &file);
        if current.name.is_none() {
            warn!(
                file = %file.display(),
                "the hostname file names no node name: the node answers by address and its configured names only"
            );
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
            .names
            .clone()
    }

    pub fn host_allowed(&self, host: &str) -> bool {
        self.current
            .read()
            .unwrap_or_else(PoisonError::into_inner)
            .names
            .host_allowed(host)
    }

    pub fn origin_allowed(&self, origin: &str) -> bool {
        self.current
            .read()
            .unwrap_or_else(PoisonError::into_inner)
            .names
            .origin_allowed(origin)
    }

    /// Reads the hostname file again; the names now in force.
    pub fn reload(&self) -> Names {
        let fresh = compose(&self.configured, &self.file);
        let mut current = self.current.write().unwrap_or_else(PoisonError::into_inner);
        match change(&current, &fresh) {
            Change::Same => {}
            Change::Changed => info!(
                names = ?fresh.names.iter().collect::<Vec<_>>(),
                "the node's names changed"
            ),
            Change::Lost => warn!(
                file = %self.file.display(),
                "the hostname file no longer names a node name: the node answers by address and its configured names only"
            ),
            Change::Found => info!(
                name = ?fresh.name,
                names = ?fresh.names.iter().collect::<Vec<_>>(),
                "the hostname file names a node name again"
            ),
        }
        let names = fresh.names.clone();
        *current = fresh;
        names
    }
}

/// How a reload moved the names.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Change {
    Same,
    Changed,
    /// The node's own name left; only the configured names remain.
    Lost,
    /// The file names a node name again, after naming none.
    Found,
}

fn change(before: &Read, fresh: &Read) -> Change {
    if before.name.is_some() && fresh.name.is_none() {
        Change::Lost
    } else if before.name.is_none() && fresh.name.is_some() {
        Change::Found
    } else if before.names == fresh.names {
        Change::Same
    } else {
        Change::Changed
    }
}

/// What one read of the hostname file gave: the node name in it, if any,
/// and the names in force with it.
#[derive(Clone, Debug, PartialEq, Eq)]
struct Read {
    name: Option<NodeName>,
    names: Names,
}

fn compose(configured: &Names, file: &Path) -> Read {
    let name = std::fs::read_to_string(file)
        .ok()
        .and_then(|text| hostname::name_in(&text));
    let names = name
        .as_ref()
        .map_or_else(|| configured.clone(), |name| configured.with(name));
    Read { name, names }
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
    fn a_reload_that_loses_the_name_is_a_loss() {
        let configured = Names::new(["extra.local"]).unwrap();
        let named = |n: &str| {
            let name = hostname::name_in(n).unwrap();
            Read {
                names: configured.with(&name),
                name: Some(name),
            }
        };
        let (one, two) = (named("rikuri01"), named("rikuri02"));
        let configured = Read {
            name: None,
            names: configured,
        };
        for (case, before, fresh, want) in [
            ("renamed", &one, &two, Change::Changed),
            ("unchanged", &one, &one, Change::Same),
            ("name lost", &one, &configured, Change::Lost),
            ("still none", &configured, &configured, Change::Same),
            ("name found", &configured, &one, Change::Found),
        ] {
            assert_eq!(change(before, fresh), want, "{case}");
        }
    }

    #[test]
    fn a_configured_name_does_not_hide_the_files() {
        let configured = Names::new(["extra.local", "rikuri01.local"]).unwrap();
        let path = file("hidden", Some("rikuri01\n"));
        let fresh = compose(&configured, &path);
        assert_eq!(fresh.name, hostname::name_in("rikuri01"), "the file's name");
        assert_eq!(fresh.names, configured);
        std::fs::write(&path, "rikuri02\n").unwrap();
        let before = compose(&configured, &path);
        assert_eq!(change(&before, &fresh), Change::Changed, "renamed back");
        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn a_lost_name_is_lost_though_the_names_stay() {
        let configured = Names::new(["extra.local", "rikuri01.local"]).unwrap();
        let path = file("kept", Some("rikuri01\n"));
        let before = compose(&configured, &path);
        std::fs::write(&path, "\n").unwrap();
        let fresh = compose(&configured, &path);
        assert_eq!(before.names, fresh.names, "the names stay");
        assert!(
            before.name.is_some() && fresh.name.is_none(),
            "the file lost it"
        );
        assert_eq!(change(&before, &fresh), Change::Lost);
        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn a_name_found_again_is_found() {
        let configured = Names::new(["extra.local", "rikuri01.local"]).unwrap();
        let path = file("found", Some("\n"));
        let before = compose(&configured, &path);
        std::fs::write(&path, "rikuri01\n").unwrap();
        let fresh = compose(&configured, &path);
        assert_eq!(before.names, fresh.names, "the names stay");
        assert!(
            before.name.is_none() && fresh.name.is_some(),
            "the file names it again"
        );
        assert_eq!(change(&before, &fresh), Change::Found);
        let _ = std::fs::remove_file(path);
    }

    /// What `f` logs, without time or colour, one event per line.
    fn logged(f: impl FnOnce()) -> String {
        #[derive(Clone)]
        struct Buffer(std::sync::Arc<std::sync::Mutex<Vec<u8>>>);
        impl std::io::Write for Buffer {
            fn write(&mut self, bytes: &[u8]) -> std::io::Result<usize> {
                self.0
                    .lock()
                    .unwrap_or_else(PoisonError::into_inner)
                    .extend_from_slice(bytes);
                Ok(bytes.len())
            }
            fn flush(&mut self) -> std::io::Result<()> {
                Ok(())
            }
        }
        let buffer = Buffer(std::sync::Arc::default());
        let writer = buffer.clone();
        let subscriber = tracing_subscriber::fmt()
            .with_writer(move || writer.clone())
            .with_ansi(false)
            .without_time()
            .finish();
        tracing::subscriber::with_default(subscriber, f);
        let bytes = buffer
            .0
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .clone();
        String::from_utf8(bytes).unwrap()
    }

    /// One line at `level` with `words` in it, or nothing at all.
    fn one_line(log: &str, want: Option<(&str, &str)>, case: &str) {
        let lines: Vec<&str> = log.lines().collect();
        match want {
            None => assert!(lines.is_empty(), "{case}: {log}"),
            Some((level, words)) => {
                assert_eq!(lines.len(), 1, "{case}: {log}");
                assert!(lines[0].trim_start().starts_with(level), "{case}: {log}");
                assert!(lines[0].contains(words), "{case}: {log}");
            }
        }
    }

    #[test]
    fn a_capture_hears_a_line_another_thread_reached_first() {
        fn say() {
            tracing::warn!("a line only this test logs");
        }
        let log = logged(|| {
            std::thread::spawn(say).join().unwrap();
            say();
        });
        one_line(
            &log,
            Some(("WARN", "a line only this test logs")),
            "another thread first",
        );
    }

    #[test]
    fn the_start_warns_only_when_the_file_names_no_name() {
        let configured = Names::new(["extra.local", "rikuri01.local"]).unwrap();
        for (case, text, want) in [
            ("blank", "\n", Some(("WARN", "names no node name"))),
            ("named", "rikuri01\n", None),
        ] {
            let path = file(&format!("start-{case}"), Some(text));
            let log = logged(|| drop(LiveNames::load(configured.clone(), path.clone())));
            one_line(&log, want, case);
            let _ = std::fs::remove_file(path);
        }
    }

    #[test]
    fn a_reload_logs_what_the_file_did() {
        let plain = Names::new(["extra.local"]).unwrap();
        let holding = Names::new(["extra.local", "rikuri01.local"]).unwrap();
        for (case, configured, first, then, want) in [
            (
                "renamed",
                &plain,
                "rikuri01\n",
                "rikuri02\n",
                Some(("INFO", "the node's names changed")),
            ),
            (
                "lost",
                &plain,
                "rikuri01\n",
                "\n",
                Some(("WARN", "no longer names a node name")),
            ),
            (
                "found again",
                &holding,
                "\n",
                "rikuri01\n",
                Some(("INFO", "names a node name again")),
            ),
            ("unchanged", &plain, "rikuri01\n", "rikuri01\n", None),
        ] {
            let path = file(&format!("log-{}", case.replace(' ', "-")), Some(first));
            let live = LiveNames::load(configured.clone(), path.clone());
            std::fs::write(&path, then).unwrap();
            let log = logged(|| drop(live.reload()));
            one_line(&log, want, case);
            let _ = std::fs::remove_file(path);
        }
    }

    #[test]
    fn a_reload_that_loses_the_name_refuses_it() {
        let configured = Names::new(["extra.local"]).unwrap();
        for (case, text) in [
            ("missing", None),
            ("blank", Some("\n# nothing\n")),
            ("dotted", Some("rikuri.example.org\n")),
            ("odd", Some("not a name\n")),
        ] {
            let path = file(&format!("lost-{case}"), Some("rikuri01\n"));
            let live = LiveNames::load(configured.clone(), path.clone());
            assert!(live.host_allowed("rikuri01.local"), "{case}: named first");
            match text {
                Some(text) => std::fs::write(&path, text).unwrap(),
                None => std::fs::remove_file(&path).unwrap(),
            }
            assert_eq!(live.reload(), configured, "{case}");
            assert_eq!(live.get(), configured, "{case}");
            assert!(!live.host_allowed("rikuri01.local"), "{case}");
            assert!(!live.origin_allowed("https://rikuri01.local"), "{case}");
            assert!(live.host_allowed("extra.local"), "{case}");
            let _ = std::fs::remove_file(path);
        }
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
