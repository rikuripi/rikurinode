//! Where the control plane listens. B0.1 accepted loopback only, because its
//! one route was plain HTTP with no sign-in. B0.2 puts the API behind TLS and
//! a session, so the HTTPS listener may bind any address, and so may the plain
//! listener, which serves only the CA certificate and a redirect. Host names
//! are still refused: nothing here resolves names, so what would be bound could
//! not be checked.

use std::fmt;
use std::net::SocketAddr;

/// The HTTPS listener's address.
pub const ENV: &str = "RIKURI_LISTEN";
/// Where the HTTPS listener binds when [`ENV`] is unset.
pub const DEFAULT: &str = "127.0.0.1:8443";
/// The plain HTTP listener's address; unset means no plain listener.
pub const HTTP_ENV: &str = "RIKURI_HTTP_LISTEN";

#[derive(Debug, PartialEq, Eq)]
pub enum ListenError {
    /// Not an `ip:port`.
    Unparsable { var: &'static str, spec: String },
}

impl fmt::Display for ListenError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ListenError::Unparsable { var, spec } => {
                write!(f, "{var}={spec:?} is not an ip:port such as {DEFAULT}")
            }
        }
    }
}

impl std::error::Error for ListenError {}

/// Parses `spec` as `ip:port`; `var` names the variable it came from, for the
/// message.
pub fn parse(var: &'static str, spec: &str) -> Result<SocketAddr, ListenError> {
    spec.parse().map_err(|_| ListenError::Unparsable {
        var,
        spec: spec.to_owned(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_default_is_loopback_8443() {
        let addr = parse(ENV, DEFAULT).unwrap();
        assert!(addr.ip().is_loopback());
        assert_eq!(addr.port(), 8443);
    }

    #[test]
    fn any_ip_and_port_is_accepted() {
        for spec in [
            "127.0.0.1:0",
            "[::1]:8443",
            "0.0.0.0:443",
            "192.168.1.2:80",
            "[::]:8443",
            "[fe80::1]:1",
        ] {
            let addr = parse(ENV, spec).unwrap_or_else(|e| panic!("{spec}: {e}"));
            assert_eq!(addr.to_string(), spec);
        }
    }

    #[test]
    fn names_and_fragments_are_refused_with_the_variables_name() {
        for spec in ["localhost:8080", "127.0.0.1", "8080", "", " 127.0.0.1:8080"] {
            let err = parse(HTTP_ENV, spec).unwrap_err();
            assert_eq!(
                err,
                ListenError::Unparsable {
                    var: HTTP_ENV,
                    spec: spec.to_owned()
                }
            );
            let text = err.to_string();
            assert!(text.contains(HTTP_ENV) && text.contains(DEFAULT), "{text}");
        }
    }
}
