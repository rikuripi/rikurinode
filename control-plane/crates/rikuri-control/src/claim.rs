//! The claim code: proof that whoever becomes the owner stood at the node's
//! console (the design note of 2026-10-12; the review's §3.7). The daemon arms
//! one at its first start and logs it; the console subcommand arms another
//! after expiry or retirement. Only argon2id of the code is kept, and only here;
//! the comparison is the hash's own. A wrong try counts on disk, so a restart
//! never gives more tries; the twentieth retires the code until the console
//! says otherwise; 24 hours expire it. Every refusal looks the same to the
//! caller (wrong, expired, retired): `GET /api/setup` says the state in words
//! instead.

use std::fmt;
use std::time::Duration;

use secrecy::{ExposeSecret, SecretString};
use serde::{Deserialize, Serialize};

use crate::password::{self, HashError};
use crate::random::{self, RandomError};
use crate::state::{StateDir, StateError};

pub const FILE: &str = "claim.json";
/// Letters and digits without look-alikes: no 0/O, no 1/I/L. 31 symbols; ten
/// of them carry about 49.6 bits.
pub const ALPHABET: &[u8; 31] = b"ABCDEFGHJKMNPQRSTUVWXYZ23456789";
pub const CODE_LEN: usize = 10;
pub const LIFETIME_SECS: u64 = 24 * 60 * 60;
/// Wrong tries that retire the code.
pub const RETIRE_AT: u32 = 20;
/// Wrong tries before the limiter starts delaying.
pub const DELAY_AFTER: u32 = 5;
pub const DELAY_CAP: Duration = Duration::from_secs(300);

/// A freshly armed code: the one place it exists in clear, for the console.
pub struct Code(SecretString);

impl Code {
    /// The code as shown and typed: `XXXX-XXXX-XX`.
    pub fn formatted(&self) -> String {
        let raw = self.0.expose_secret();
        format!("{}-{}-{}", &raw[..4], &raw[4..8], &raw[8..])
    }
}

impl fmt::Debug for Code {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("Code([REDACTED])")
    }
}

/// What the file keeps: never the code.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClaimFile {
    pub hash: String,
    pub created_unix: u64,
    pub expires_unix: u64,
    pub wrong_tries: u32,
    pub retired: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum ClaimState {
    Armed,
    Expired,
    Retired,
}

impl ClaimFile {
    pub fn state(&self, now_unix: u64) -> ClaimState {
        if self.retired {
            ClaimState::Retired
        } else if now_unix >= self.expires_unix {
            ClaimState::Expired
        } else {
            ClaimState::Armed
        }
    }
}

#[derive(Debug)]
pub enum ClaimError {
    State(StateError),
    Random(RandomError),
    Hash(HashError),
}

impl fmt::Display for ClaimError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ClaimError::State(e) => write!(f, "claim state: {e}"),
            ClaimError::Random(e) => write!(f, "claim code: {e}"),
            ClaimError::Hash(e) => write!(f, "claim code: {e}"),
        }
    }
}

impl std::error::Error for ClaimError {}

impl From<StateError> for ClaimError {
    fn from(e: StateError) -> Self {
        ClaimError::State(e)
    }
}

impl From<RandomError> for ClaimError {
    fn from(e: RandomError) -> Self {
        ClaimError::Random(e)
    }
}

impl From<HashError> for ClaimError {
    fn from(e: HashError) -> Self {
        ClaimError::Hash(e)
    }
}

/// One random byte to one symbol of [`ALPHABET`], or to none: only bytes
/// below 248 (eight full rounds of 31) are used, so every symbol is drawn
/// with the same probability; the eight bytes from 248 up are thrown away.
fn symbol(byte: u8) -> Option<char> {
    (byte < 248).then(|| char::from(ALPHABET[usize::from(byte % 31)]))
}

/// Ten symbols, each from [`symbol`].
fn generate() -> Result<Code, RandomError> {
    let mut code = String::with_capacity(CODE_LEN);
    while code.len() < CODE_LEN {
        for byte in random::bytes::<32>()? {
            if code.len() == CODE_LEN {
                break;
            }
            if let Some(c) = symbol(byte) {
                code.push(c);
            }
        }
    }
    Ok(Code(SecretString::from(code)))
}

/// What a typed code becomes before it is checked: upper case, no dashes or
/// spaces, so `k7qm-4xd9-tr` and `K7QM4XD9TR` are the same code.
pub fn normalize(input: &str) -> String {
    input
        .chars()
        .filter(|c| !matches!(c, '-' | ' '))
        .flat_map(char::to_uppercase)
        .collect()
}

/// Arms a new code at `now_unix`: writes the file and returns the code, the
/// one time it is in clear.
pub fn arm(dir: &StateDir, now_unix: u64) -> Result<Code, ClaimError> {
    let code = generate()?;
    let hash = password::hash(code.0.expose_secret())?;
    dir.write_json(
        FILE,
        &ClaimFile {
            hash,
            created_unix: now_unix,
            expires_unix: now_unix.saturating_add(LIFETIME_SECS),
            wrong_tries: 0,
            retired: false,
        },
    )?;
    Ok(code)
}

pub fn load(dir: &StateDir) -> Result<Option<ClaimFile>, ClaimError> {
    Ok(dir.read_json(FILE)?)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Attempt {
    Accepted,
    /// Refused, whatever the reason; `counted` says whether it was a wrong
    /// code against an armed claim, which the limiter counts.
    Refused {
        counted: bool,
    },
}

/// Judges one typed code against the file at `now_unix`. An expired or retired
/// claim, or none at all, refuses without counting; a wrong code against an
/// armed claim counts, and the twentieth retires it. Slow by design (argon2id):
/// call it off the request thread.
pub fn attempt(
    dir: &StateDir,
    input: &str,
    now_unix: u64,
) -> Result<(Attempt, Option<ClaimFile>), ClaimError> {
    let Some(mut file) = load(dir)? else {
        return Ok((Attempt::Refused { counted: false }, None));
    };
    if file.state(now_unix) != ClaimState::Armed {
        return Ok((Attempt::Refused { counted: false }, Some(file)));
    }
    if password::verify(&normalize(input), &file.hash) {
        return Ok((Attempt::Accepted, Some(file)));
    }
    file.wrong_tries = file.wrong_tries.saturating_add(1);
    if file.wrong_tries >= RETIRE_AT {
        file.retired = true;
    }
    dir.write_json(FILE, &file)?;
    Ok((Attempt::Refused { counted: true }, Some(file)))
}

/// After a successful claim: the file goes, and with it the code for good.
pub fn finish(dir: &StateDir) -> Result<(), ClaimError> {
    dir.remove(FILE)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::testing::Scratch;

    const NOW: u64 = 1_800_000_000;

    fn open() -> (Scratch, StateDir) {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        (scratch, dir)
    }

    #[test]
    fn a_code_is_ten_symbols_of_the_alphabet_shown_in_groups() {
        let code = generate().unwrap();
        let shown = code.formatted();
        assert_eq!(shown.len(), 12, "{shown}");
        assert_eq!(shown.as_bytes()[4], b'-');
        assert_eq!(shown.as_bytes()[9], b'-');
        let raw = normalize(&shown);
        assert_eq!(raw.len(), CODE_LEN);
        assert!(raw.bytes().all(|b| ALPHABET.contains(&b)), "{shown}");
        for lookalike in ['0', 'O', '1', 'I', 'L'] {
            assert!(!raw.contains(lookalike), "{shown}");
        }
        assert_ne!(generate().unwrap().formatted(), shown);
    }

    #[test]
    fn every_byte_maps_to_one_symbol_without_bias_or_to_none() {
        // The first round of 31 and the last, and the eight bytes thrown away.
        assert_eq!(symbol(0), Some('A'));
        assert_eq!(symbol(30), Some('9'));
        assert_eq!(symbol(31), Some('A'));
        assert_eq!(symbol(217), Some('A'), "217 = 7 * 31");
        assert_eq!(symbol(247), Some('9'), "the last accepted byte");
        for byte in 248..=255u8 {
            assert_eq!(symbol(byte), None, "{byte}");
        }
        // Uniform: each symbol has exactly eight bytes.
        for want in ALPHABET {
            let count = (0..=255u8)
                .filter(|b| symbol(*b) == Some(char::from(*want)))
                .count();
            assert_eq!(count, 8, "{}", char::from(*want));
        }
    }

    #[test]
    fn every_symbol_of_the_alphabet_is_drawn() {
        // 300 codes are 3,000 draws; a symbol missing from all of them has a
        // probability below 1e-40, so this never flakes and catches a draw
        // that reaches only part of the alphabet.
        let mut seen = std::collections::BTreeSet::new();
        for _ in 0..300 {
            seen.extend(normalize(&generate().unwrap().formatted()).chars());
        }
        let alphabet: std::collections::BTreeSet<char> =
            ALPHABET.iter().map(|b| char::from(*b)).collect();
        assert_eq!(seen, alphabet);
    }

    #[test]
    fn the_debug_form_never_shows_the_code() {
        let code = generate().unwrap();
        let debug = format!("{code:?}");
        assert_eq!(debug, "Code([REDACTED])");
        assert!(!debug.contains(&normalize(&code.formatted())));
    }

    #[test]
    fn typed_forms_normalize_to_the_same_code() {
        assert_eq!(normalize("k7qm-4xd9-tr"), "K7QM4XD9TR");
        assert_eq!(normalize(" K7QM 4XD9 TR "), "K7QM4XD9TR");
        assert_eq!(normalize("K7QM4XD9TR"), "K7QM4XD9TR");
    }

    #[test]
    fn arming_writes_a_hash_and_the_right_code_is_accepted_in_any_typed_form() {
        let (_scratch, dir) = open();
        let code = arm(&dir, NOW).unwrap();
        let file = load(&dir).unwrap().unwrap();
        assert_eq!(file.state(NOW), ClaimState::Armed);
        assert_eq!(file.expires_unix, NOW + LIFETIME_SECS);
        assert_eq!(file.wrong_tries, 0);
        assert!(!file.hash.contains(&normalize(&code.formatted())));
        assert!(file.hash.starts_with("$argon2id$"), "{}", file.hash);
        let typed = code.formatted().to_lowercase();
        let (verdict, _) = attempt(&dir, &typed, NOW + 1).unwrap();
        assert_eq!(verdict, Attempt::Accepted);
        assert_eq!(
            load(&dir).unwrap().unwrap().wrong_tries,
            0,
            "a right code does not count"
        );
    }

    #[test]
    fn a_wrong_code_counts_on_disk_and_the_twentieth_retires_the_claim() {
        let (_scratch, dir) = open();
        let code = arm(&dir, NOW).unwrap();
        for n in 1..RETIRE_AT {
            let (verdict, file) = attempt(&dir, "AAAA-AAAA-AA", NOW).unwrap();
            assert_eq!(verdict, Attempt::Refused { counted: true }, "try {n}");
            let file = file.unwrap();
            assert_eq!(file.wrong_tries, n);
            assert_eq!(file.state(NOW), ClaimState::Armed, "try {n}");
        }
        let (verdict, file) = attempt(&dir, "AAAA-AAAA-AA", NOW).unwrap();
        assert_eq!(verdict, Attempt::Refused { counted: true });
        let file = file.unwrap();
        assert_eq!(file.wrong_tries, RETIRE_AT);
        assert!(file.retired);
        assert_eq!(load(&dir).unwrap().unwrap().state(NOW), ClaimState::Retired);
        // Retired: even the right code is refused, and nothing counts any more.
        let (verdict, _) = attempt(&dir, &code.formatted(), NOW).unwrap();
        assert_eq!(verdict, Attempt::Refused { counted: false });
        assert_eq!(load(&dir).unwrap().unwrap().wrong_tries, RETIRE_AT);
    }

    #[test]
    fn an_expired_claim_refuses_the_right_code_without_counting() {
        let (_scratch, dir) = open();
        let code = arm(&dir, NOW).unwrap();
        let at_expiry = NOW + LIFETIME_SECS;
        assert_eq!(
            load(&dir).unwrap().unwrap().state(at_expiry),
            ClaimState::Expired
        );
        assert_eq!(
            load(&dir).unwrap().unwrap().state(at_expiry - 1),
            ClaimState::Armed
        );
        let (verdict, _) = attempt(&dir, &code.formatted(), at_expiry).unwrap();
        assert_eq!(verdict, Attempt::Refused { counted: false });
        assert_eq!(load(&dir).unwrap().unwrap().wrong_tries, 0);
    }

    #[test]
    fn no_claim_file_refuses_without_counting_and_finish_removes_it() {
        let (_scratch, dir) = open();
        let (verdict, file) = attempt(&dir, "AAAA-AAAA-AA", NOW).unwrap();
        assert_eq!(verdict, Attempt::Refused { counted: false });
        assert_eq!(file, None);
        arm(&dir, NOW).unwrap();
        assert!(dir.exists(FILE));
        finish(&dir).unwrap();
        assert!(!dir.exists(FILE));
        finish(&dir).unwrap();
    }

    #[test]
    fn re_arming_replaces_the_code_and_resets_the_count() {
        let (_scratch, dir) = open();
        let first = arm(&dir, NOW).unwrap();
        attempt(&dir, "AAAA-AAAA-AA", NOW).unwrap();
        let second = arm(&dir, NOW + 10).unwrap();
        let file = load(&dir).unwrap().unwrap();
        assert_eq!(file.wrong_tries, 0);
        assert_eq!(file.created_unix, NOW + 10);
        let (old, _) = attempt(&dir, &first.formatted(), NOW + 11).unwrap();
        assert_eq!(old, Attempt::Refused { counted: true });
        let (new, _) = attempt(&dir, &second.formatted(), NOW + 11).unwrap();
        assert_eq!(new, Attempt::Accepted);
    }
}
