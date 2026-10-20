//! Where the control plane listens. Until TLS and sign-in exist (B0.2), only
//! a loopback address is accepted, so a configuration mistake cannot expose
//! an unauthenticated route to the network.

use std::fmt;
use std::net::SocketAddr;

/// The environment variable that overrides [`DEFAULT`].
pub const ENV: &str = "RIKURI_LISTEN";
/// Where the daemon listens when [`ENV`] is unset.
pub const DEFAULT: &str = "127.0.0.1:8080";

#[derive(Debug, PartialEq, Eq)]
pub enum ListenError {
    /// Not an `ip:port`. A host name is refused on purpose: nothing here
    /// resolves names, so what would be bound could not be checked.
    Unparsable(String),
    /// A valid address that is not on loopback.
    NotLoopback(SocketAddr),
}

impl fmt::Display for ListenError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ListenError::Unparsable(spec) => {
                write!(f, "{ENV}={spec:?} is not an ip:port such as {DEFAULT}")
            }
            ListenError::NotLoopback(addr) => write!(
                f,
                "{ENV}={addr} is not a loopback address: until TLS and sign-in exist, \
                 the control plane listens only on 127.0.0.0/8 or ::1"
            ),
        }
    }
}

impl std::error::Error for ListenError {}

/// Parses `spec` as `ip:port` and accepts it only on loopback.
pub fn parse(spec: &str) -> Result<SocketAddr, ListenError> {
    let addr: SocketAddr = spec
        .parse()
        .map_err(|_| ListenError::Unparsable(spec.to_owned()))?;
    if addr.ip().is_loopback() {
        Ok(addr)
    } else {
        Err(ListenError::NotLoopback(addr))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_default_is_loopback() {
        let addr = parse(DEFAULT).unwrap();
        assert!(addr.ip().is_loopback());
        assert_eq!(addr.port(), 8080);
    }

    #[test]
    fn loopback_addresses_are_accepted() {
        for spec in ["127.0.0.1:0", "127.1.2.3:1", "[::1]:8080"] {
            let addr = parse(spec).unwrap_or_else(|e| panic!("{spec}: {e}"));
            assert!(addr.ip().is_loopback(), "{spec}");
        }
    }

    #[test]
    fn other_addresses_are_refused() {
        for spec in ["0.0.0.0:8080", "192.168.1.2:80", "[::]:8080", "[fe80::1]:1"] {
            match parse(spec) {
                Err(ListenError::NotLoopback(addr)) => assert_eq!(addr.to_string(), spec),
                other => panic!("{spec}: {other:?}"),
            }
        }
    }

    #[test]
    fn names_and_fragments_are_refused() {
        for spec in ["localhost:8080", "127.0.0.1", "8080", "", " 127.0.0.1:8080"] {
            assert_eq!(parse(spec), Err(ListenError::Unparsable(spec.to_owned())));
        }
    }

    #[test]
    fn errors_say_what_to_fix() {
        let unparsable = parse("localhost:8080").unwrap_err().to_string();
        assert!(
            unparsable.contains(ENV) && unparsable.contains(DEFAULT),
            "{unparsable}"
        );
        let not_loopback = parse("0.0.0.0:8080").unwrap_err().to_string();
        assert!(not_loopback.contains("loopback"), "{not_loopback}");
    }
}
