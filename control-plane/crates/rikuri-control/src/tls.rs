//! The node's own certificate authority and the server certificate it signs
//! (D10): made at first start, kept as DER under the state folder. The CA is
//! never re-issued, so a browser that installed it keeps trusting the node;
//! the server certificate is re-issued when the node's names change or it
//! expires within 30 days. HTTPS is rustls with the `ring` provider, TLS 1.3
//! and 1.2, HTTP/1.1 only.

use std::fmt;
use std::sync::Arc;

use base64ct::{Base64, Encoding};
use rcgen::{
    BasicConstraints, CertificateParams, DistinguishedName, DnType, ExtendedKeyUsagePurpose, IsCa,
    Issuer, KeyPair, KeyUsagePurpose, PKCS_ECDSA_P256_SHA256,
};
use rustls::ServerConfig;
use rustls_pki_types::{CertificateDer, PrivateKeyDer, PrivatePkcs8KeyDer};
use serde::{Deserialize, Serialize};
use time::{Duration, OffsetDateTime};

use crate::names::Names;
use crate::random;
use crate::state::{StateDir, StateError};

pub const CA_KEY: &str = "ca.key.der";
pub const CA_CERT: &str = "ca.crt.der";
pub const SERVER_KEY: &str = "server.key.der";
pub const SERVER_CERT: &str = "server.crt.der";
pub const SERVER_META: &str = "server.json";
pub const CA_DAYS: i64 = 3650;
/// Under Apple's limit for certificates from private roots (825 days) with
/// room to spare, and re-issued 30 days before the end.
pub const SERVER_DAYS: i64 = 397;
pub const RENEW_WITHIN_DAYS: i64 = 30;
const CA_NAME: &str = "Rikuri Node CA";
const SERVER_NAME: &str = "Rikuri Node";

/// What the server certificate was issued for, kept beside it so the names and
/// the dates can be compared without parsing X.509.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ServerMeta {
    pub names: Vec<String>,
    pub not_before_unix: i64,
    pub not_after_unix: i64,
}

pub struct Identity {
    pub ca_der: Vec<u8>,
    pub ca_pem: String,
    pub ca_fingerprint: String,
    pub server_der: Vec<u8>,
    pub server_meta: ServerMeta,
    pub config: Arc<ServerConfig>,
    pub ca_created: bool,
    pub server_issued: bool,
}

impl fmt::Debug for Identity {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Identity")
            .field("ca_fingerprint", &self.ca_fingerprint)
            .field("server_meta", &self.server_meta)
            .field("ca_created", &self.ca_created)
            .field("server_issued", &self.server_issued)
            .finish_non_exhaustive()
    }
}

#[derive(Debug)]
pub enum TlsError {
    State(StateError),
    Certificate(rcgen::Error),
    Rustls(rustls::Error),
}

impl fmt::Display for TlsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TlsError::State(e) => write!(f, "TLS identity: {e}"),
            TlsError::Certificate(e) => write!(f, "TLS identity: certificate: {e}"),
            TlsError::Rustls(e) => write!(f, "TLS identity: {e}"),
        }
    }
}

impl std::error::Error for TlsError {}

impl From<StateError> for TlsError {
    fn from(e: StateError) -> Self {
        TlsError::State(e)
    }
}

impl From<rcgen::Error> for TlsError {
    fn from(e: rcgen::Error) -> Self {
        TlsError::Certificate(e)
    }
}

impl From<rustls::Error> for TlsError {
    fn from(e: rustls::Error) -> Self {
        TlsError::Rustls(e)
    }
}

/// The CA's parameters, the same at creation and whenever it signs: the
/// issuer's name and key usages come from here, not from parsing its
/// certificate.
fn ca_params() -> CertificateParams {
    let mut params = CertificateParams::default();
    let mut dn = DistinguishedName::new();
    dn.push(DnType::CommonName, CA_NAME);
    params.distinguished_name = dn;
    params.is_ca = IsCa::Ca(BasicConstraints::Unconstrained);
    params.key_usages = vec![
        KeyUsagePurpose::KeyCertSign,
        KeyUsagePurpose::CrlSign,
        KeyUsagePurpose::DigitalSignature,
    ];
    params
}

/// The names the server certificate carries: the node's names plus the
/// loopback addresses, sorted, so the same set always compares equal.
pub fn san_names(names: &Names) -> Vec<String> {
    let mut all: Vec<String> = names.iter().map(str::to_owned).collect();
    all.push("127.0.0.1".to_owned());
    all.push("::1".to_owned());
    all.sort();
    all.dedup();
    all
}

/// Loads the identity from the state folder, creating what is missing: the CA
/// once, the server certificate whenever its names or dates no longer serve.
pub fn load_or_create(
    dir: &StateDir,
    names: &Names,
    now: OffsetDateTime,
) -> Result<Identity, TlsError> {
    let (ca_key, ca_der, ca_created) = match (dir.read(CA_KEY)?, dir.read(CA_CERT)?) {
        (Some(key), Some(der)) => (
            KeyPair::from_pkcs8_der_and_sign_algo(
                &PrivatePkcs8KeyDer::from(key),
                &PKCS_ECDSA_P256_SHA256,
            )?,
            der,
            false,
        ),
        _ => {
            let key = KeyPair::generate_for(&PKCS_ECDSA_P256_SHA256)?;
            let mut params = ca_params();
            params.not_before = now - Duration::minutes(5);
            params.not_after = now + Duration::days(CA_DAYS);
            let cert = params.self_signed(&key)?;
            dir.write(CA_KEY, &key.serialize_der())?;
            dir.write(CA_CERT, cert.der().as_ref())?;
            (key, cert.der().to_vec(), true)
        }
    };

    let wanted = san_names(names);
    let meta: Option<ServerMeta> = dir.read_json(SERVER_META)?;
    let renew_at = (now + Duration::days(RENEW_WITHIN_DAYS)).unix_timestamp();
    let reuse = meta.as_ref().is_some_and(|m| {
        m.names == wanted
            && m.not_after_unix > renew_at
            && m.not_before_unix <= now.unix_timestamp()
    }) && dir.exists(SERVER_KEY)
        && dir.exists(SERVER_CERT);
    let (server_key_der, server_der, server_meta, server_issued) = match (reuse, meta) {
        (true, Some(meta)) => (
            dir.read(SERVER_KEY)?.unwrap_or_default(),
            dir.read(SERVER_CERT)?.unwrap_or_default(),
            meta,
            false,
        ),
        _ => {
            let key = KeyPair::generate_for(&PKCS_ECDSA_P256_SHA256)?;
            let mut params = CertificateParams::new(wanted.clone())?;
            let mut dn = DistinguishedName::new();
            dn.push(DnType::CommonName, SERVER_NAME);
            params.distinguished_name = dn;
            params.is_ca = IsCa::ExplicitNoCa;
            params.key_usages = vec![KeyUsagePurpose::DigitalSignature];
            params.extended_key_usages = vec![ExtendedKeyUsagePurpose::ServerAuth];
            params.use_authority_key_identifier_extension = true;
            params.not_before = now - Duration::minutes(5);
            params.not_after = now + Duration::days(SERVER_DAYS);
            let issuer = Issuer::new(ca_params(), ca_key);
            let cert = params.signed_by(&key, &issuer)?;
            let meta = ServerMeta {
                names: wanted,
                not_before_unix: params.not_before.unix_timestamp(),
                not_after_unix: params.not_after.unix_timestamp(),
            };
            dir.write(SERVER_KEY, &key.serialize_der())?;
            dir.write(SERVER_CERT, cert.der().as_ref())?;
            dir.write_json(SERVER_META, &meta)?;
            (key.serialize_der(), cert.der().to_vec(), meta, true)
        }
    };

    let mut config = ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(
            vec![CertificateDer::from(server_der.clone())],
            PrivateKeyDer::Pkcs8(PrivatePkcs8KeyDer::from(server_key_der)),
        )?;
    config.alpn_protocols = vec![b"http/1.1".to_vec()];

    Ok(Identity {
        ca_pem: pem(&ca_der),
        ca_fingerprint: random::fingerprint(&ca_der),
        ca_der,
        server_der,
        server_meta,
        config: Arc::new(config),
        ca_created,
        server_issued,
    })
}

/// A certificate in PEM: the form a browser or a phone installs.
pub fn pem(der: &[u8]) -> String {
    let mut out = String::from("-----BEGIN CERTIFICATE-----\n");
    let b64 = Base64::encode_string(der);
    for line in b64.as_bytes().chunks(64) {
        out.push_str(std::str::from_utf8(line).unwrap_or(""));
        out.push('\n');
    }
    out.push_str("-----END CERTIFICATE-----\n");
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::testing::Scratch;

    fn names() -> Names {
        Names::new(["rikuri01.local"]).unwrap()
    }

    fn now() -> OffsetDateTime {
        OffsetDateTime::now_utc()
    }

    #[test]
    fn the_first_start_makes_a_ca_and_a_server_certificate_for_the_names() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        let id = load_or_create(&dir, &names(), now()).unwrap();
        assert!(id.ca_created && id.server_issued);
        for file in [CA_KEY, CA_CERT, SERVER_KEY, SERVER_CERT, SERVER_META] {
            assert!(dir.exists(file), "{file}");
        }
        assert_eq!(
            id.server_meta.names,
            ["127.0.0.1", "::1", "localhost", "rikuri01.local"]
        );
        assert_eq!(
            id.server_meta.not_after_unix - id.server_meta.not_before_unix,
            (SERVER_DAYS * 86_400) + 300
        );
        assert_eq!(id.ca_fingerprint, random::fingerprint(&id.ca_der));
        assert_eq!(id.ca_fingerprint.len(), 95);
        assert!(
            id.ca_pem.starts_with("-----BEGIN CERTIFICATE-----\n"),
            "{}",
            id.ca_pem
        );
        assert!(
            id.ca_pem.ends_with("-----END CERTIFICATE-----\n"),
            "{}",
            id.ca_pem
        );
        assert!(id.ca_pem.lines().all(|l| l.len() <= 64), "{}", id.ca_pem);
        assert_ne!(id.ca_der, id.server_der);
        let debug = format!("{id:?}");
        assert!(debug.contains(&id.ca_fingerprint), "{debug}");
        assert!(debug.contains("server_meta"), "{debug}");
        assert!(
            !debug.contains("key"),
            "the debug form names no key material: {debug}"
        );
    }

    #[test]
    fn a_second_start_reuses_both_certificates() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        let first = load_or_create(&dir, &names(), now()).unwrap();
        let second = load_or_create(&dir, &names(), now()).unwrap();
        assert!(!second.ca_created && !second.server_issued);
        assert_eq!(first.ca_der, second.ca_der);
        assert_eq!(first.server_der, second.server_der);
        assert_eq!(first.server_meta, second.server_meta);
    }

    #[test]
    fn changed_names_re_issue_the_server_certificate_and_keep_the_ca() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        let first = load_or_create(&dir, &names(), now()).unwrap();
        let renamed = Names::new(["rikuri02.local"]).unwrap();
        let second = load_or_create(&dir, &renamed, now()).unwrap();
        assert!(!second.ca_created && second.server_issued);
        assert_eq!(first.ca_der, second.ca_der);
        assert_ne!(first.server_der, second.server_der);
        assert!(
            second
                .server_meta
                .names
                .contains(&"rikuri02.local".to_owned())
        );
    }

    #[test]
    fn a_server_certificate_near_its_end_is_re_issued() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        let first = load_or_create(&dir, &names(), now()).unwrap();
        let later = now() + Duration::days(SERVER_DAYS - RENEW_WITHIN_DAYS + 1);
        let second = load_or_create(&dir, &names(), later).unwrap();
        assert!(
            second.server_issued,
            "re-issued within {RENEW_WITHIN_DAYS} days of its end"
        );
        assert_eq!(first.ca_der, second.ca_der);
        let third = load_or_create(&dir, &names(), later).unwrap();
        assert!(!third.server_issued);
    }

    #[test]
    fn a_missing_server_file_is_re_issued_even_with_matching_metadata() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        load_or_create(&dir, &names(), now()).unwrap();
        dir.remove(SERVER_KEY).unwrap();
        let again = load_or_create(&dir, &names(), now()).unwrap();
        assert!(again.server_issued);
        assert!(dir.exists(SERVER_KEY));
    }

    #[test]
    fn pem_wraps_at_64_columns() {
        let text = pem(&[0u8; 100]);
        let body: Vec<&str> = text.lines().filter(|l| !l.starts_with("-----")).collect();
        assert_eq!(body.len(), 3, "{text}");
        assert_eq!(body[0].len(), 64);
        assert_eq!(body[2].len(), 136 - 128);
    }
}
