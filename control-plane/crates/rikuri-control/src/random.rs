//! Random bytes, their hex form and SHA-256, from one source: ring's system
//! RNG, the crate rustls already brings, so the tree has one RNG (and one
//! `getrandom`). Every secret the control plane mints starts here: the claim
//! code, session ids, CSRF and step-up tokens, the node's instance id.

use std::fmt;

use ring::digest::{SHA256, digest};
use ring::rand::{SecureRandom, SystemRandom};

/// The operating system's random source refused: nothing can be minted. The
/// caller fails closed and says so; it never falls back to a weaker source.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RandomError;

impl fmt::Display for RandomError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("the system's random source failed")
    }
}

impl std::error::Error for RandomError {}

/// `N` random bytes.
pub fn bytes<const N: usize>() -> Result<[u8; N], RandomError> {
    let mut out = [0u8; N];
    SystemRandom::new()
        .fill(&mut out)
        .map_err(|_| RandomError)?;
    Ok(out)
}

/// 32 random bytes as 64 lower-case hex characters: a session id, a CSRF or
/// step-up token, the node's instance id.
pub fn token() -> Result<String, RandomError> {
    Ok(hex(&bytes::<32>()?))
}

/// Lower-case hex, two characters per byte.
pub fn hex(data: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(data.len() * 2);
    for byte in data {
        out.push(char::from(DIGITS[usize::from(byte >> 4)]));
        out.push(char::from(DIGITS[usize::from(byte & 0x0f)]));
    }
    out
}

/// SHA-256 of `data` in hex. Session ids are stored this way, so the store
/// alone opens nothing.
pub fn sha256_hex(data: &[u8]) -> String {
    hex(digest(&SHA256, data).as_ref())
}

/// SHA-256 of `data` as a certificate fingerprint: upper-case hex pairs joined
/// by colons, the form a browser's certificate viewer shows.
pub fn fingerprint(data: &[u8]) -> String {
    digest(&SHA256, data)
        .as_ref()
        .iter()
        .map(|byte| format!("{byte:02X}"))
        .collect::<Vec<_>>()
        .join(":")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hex_is_lower_case_and_two_characters_per_byte() {
        assert_eq!(hex(&[]), "");
        assert_eq!(hex(&[0x00, 0x0f, 0xa5, 0xff]), "000fa5ff");
    }

    #[test]
    fn sha256_matches_the_known_vector() {
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn a_fingerprint_is_colon_separated_upper_case_pairs() {
        let fp = fingerprint(b"abc");
        assert_eq!(fp.len(), 32 * 3 - 1);
        assert!(fp.starts_with("BA:78:16:BF:"), "{fp}");
        assert!(fp.split(':').all(|pair| pair.len() == 2), "{fp}");
    }

    #[test]
    fn tokens_are_64_hex_characters_and_differ() {
        let a = token().unwrap();
        let b = token().unwrap();
        assert_eq!(a.len(), 64);
        assert!(
            a.bytes()
                .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
        );
        assert_ne!(a, b);
    }

    #[test]
    fn bytes_fills_the_whole_array() {
        let a = bytes::<16>().unwrap();
        let b = bytes::<16>().unwrap();
        assert_ne!(a, b);
        assert_ne!(a, [0u8; 16]);
    }
}
