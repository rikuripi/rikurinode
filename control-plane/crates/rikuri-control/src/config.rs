//! What the daemon reads from its environment, which is what a systemd unit
//! sets (no configuration file exists yet, as in B0.1).

use std::ffi::OsString;
use std::fmt;
use std::net::SocketAddr;
use std::path::PathBuf;

use crate::listen::{self, ListenError};
use crate::names::{self, NameError, Names};
use crate::state;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Config {
    /// The HTTPS listener (`RIKURI_LISTEN`).
    pub https: SocketAddr,
    /// The plain listener for the CA certificate and the redirect
    /// (`RIKURI_HTTP_LISTEN`); none unless set.
    pub http: Option<SocketAddr>,
    /// The node's names (`RIKURI_NAMES`), `localhost` always among them.
    pub names: Names,
    /// The state folder (`RIKURI_STATE_DIR`).
    pub state_dir: PathBuf,
}

#[derive(Debug, PartialEq, Eq)]
pub enum ConfigError {
    Listen(ListenError),
    Names(NameError),
    NotUtf8(&'static str),
}

impl fmt::Display for ConfigError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ConfigError::Listen(e) => write!(f, "{e}"),
            ConfigError::Names(e) => write!(f, "{e}"),
            ConfigError::NotUtf8(var) => write!(f, "{var} is not valid UTF-8"),
        }
    }
}

impl std::error::Error for ConfigError {}

impl Config {
    pub fn from_env() -> Result<Self, ConfigError> {
        Self::from_vars(|var| std::env::var_os(var))
    }

    /// Reads the configuration through `get`, so tests need not touch the
    /// process environment.
    pub fn from_vars(get: impl Fn(&str) -> Option<OsString>) -> Result<Self, ConfigError> {
        let text = |var: &'static str| -> Result<Option<String>, ConfigError> {
            get(var)
                .map(|value| value.into_string().map_err(|_| ConfigError::NotUtf8(var)))
                .transpose()
        };
        let https = text(listen::ENV)?.unwrap_or_else(|| listen::DEFAULT.to_owned());
        let https = listen::parse(listen::ENV, &https).map_err(ConfigError::Listen)?;
        let http = text(listen::HTTP_ENV)?
            .filter(|s| !s.trim().is_empty())
            .map(|s| listen::parse(listen::HTTP_ENV, &s))
            .transpose()
            .map_err(ConfigError::Listen)?;
        let names =
            Names::from_list(&text(names::ENV)?.unwrap_or_default()).map_err(ConfigError::Names)?;
        let state_dir = get(state::ENV)
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from(state::DEFAULT));
        Ok(Self {
            https,
            http,
            names,
            state_dir,
        })
    }
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use super::*;

    fn from(pairs: &[(&str, &str)]) -> Result<Config, ConfigError> {
        let map: HashMap<&str, &str> = pairs.iter().copied().collect();
        Config::from_vars(|var| map.get(var).map(OsString::from))
    }

    #[test]
    fn the_defaults_are_loopback_https_no_plain_listener_localhost_and_var_lib() {
        let config = from(&[]).unwrap();
        assert_eq!(config.https.to_string(), listen::DEFAULT);
        assert_eq!(config.http, None);
        assert_eq!(config.names.iter().collect::<Vec<_>>(), ["localhost"]);
        assert_eq!(config.state_dir, PathBuf::from(state::DEFAULT));
    }

    #[test]
    fn every_variable_is_read() {
        let config = from(&[
            (listen::ENV, "0.0.0.0:443"),
            (listen::HTTP_ENV, "0.0.0.0:80"),
            (names::ENV, "rikuri01.local,rikurisetup.local"),
            (state::ENV, "/tmp/state"),
        ])
        .unwrap();
        assert_eq!(config.https.to_string(), "0.0.0.0:443");
        assert_eq!(
            config.http.map(|a| a.to_string()),
            Some("0.0.0.0:80".to_owned())
        );
        assert_eq!(
            config.names.iter().collect::<Vec<_>>(),
            ["localhost", "rikuri01.local", "rikurisetup.local"]
        );
        assert_eq!(config.state_dir, PathBuf::from("/tmp/state"));
    }

    #[test]
    fn a_blank_plain_listener_means_none() {
        assert_eq!(from(&[(listen::HTTP_ENV, "  ")]).unwrap().http, None);
    }

    #[test]
    fn each_bad_value_names_its_variable() {
        let err = from(&[(listen::ENV, "localhost:443")]).unwrap_err();
        assert!(err.to_string().contains(listen::ENV), "{err}");
        let err = from(&[(listen::HTTP_ENV, "80")]).unwrap_err();
        assert!(err.to_string().contains(listen::HTTP_ENV), "{err}");
        let err = from(&[(names::ENV, "a b")]).unwrap_err();
        assert!(err.to_string().contains(names::ENV), "{err}");
    }

    #[test]
    fn a_value_that_is_not_utf8_is_refused_by_name() {
        use std::os::unix::ffi::OsStringExt;
        let bad = OsString::from_vec(vec![0xff, 0xfe]);
        let err = Config::from_vars(|var| (var == listen::ENV).then(|| bad.clone())).unwrap_err();
        assert_eq!(err, ConfigError::NotUtf8(listen::ENV));
    }
}
