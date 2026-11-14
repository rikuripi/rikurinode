//! The node's name, and the one call that changes it (5c.4b-1).
//!
//! The name is one DNS label (lower-case letters, digits and inner hyphens);
//! the node answers as `<name>.local`. It is the static hostname that
//! systemd-hostnamed keeps in `/etc/hostname`, read again rather than
//! remembered, so a rename by any route ends with the same names.
//!
//! The control plane never runs another program (ADR 0005, ADR 0014), so it
//! asks hostnamed over the system bus itself: a minimal D-Bus client that
//! authenticates with SASL EXTERNAL (the socket's own credentials), sends
//! `Hello` and one fixed call, `org.freedesktop.hostname1.SetStaticHostname(s,
//! b)` with `interactive = false`, and reads back only a method return or an
//! error, within a time limit and a size limit. Polkit lets only the control
//! plane's user make that call (the image's rule); a refusal comes back as an
//! error, never as a prompt. Little-endian only: hostnamed and the bus run on
//! the node itself (x86-64 and arm64).
//! Record: docs/build-records/2026-11-13-5c4b1-rename-engine.md
//!
//! 5c.4b-2: one more fixed call, to systemd-resolved, `ResolveHostname` over
//! mDNS only: whether something on the network answers a name. It needs no
//! polkit rule and no socket of the control plane's own on the network.
//! Record: docs/build-records/2026-11-13-5c4b2-naming-page.md

use std::fmt;
use std::io;
use std::os::unix::fs::MetadataExt;
use std::path::Path;
use std::time::Duration;

use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::UnixStream;

/// The system bus.
pub const BUS_SOCKET: &str = "/run/dbus/system_bus_socket";
/// How long a rename may take, the bus's answer included.
pub const BUS_TIMEOUT: Duration = Duration::from_secs(10);
/// No message from the bus is larger than this, and nothing larger is read.
pub const MAX_MESSAGE: usize = 64 * 1024;
/// All the bytes one rename may read from the bus.
pub const MAX_READ: usize = 4 * MAX_MESSAGE;
/// The longest line the bus may send while authenticating.
const MAX_AUTH_LINE: usize = 512;

/// The serials of the two calls a rename sends.
pub const HELLO_SERIAL: u32 = 1;
pub const CALL_SERIAL: u32 = 2;

/// A name the node can be given: one lower-case DNS label, never `localhost`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NodeName(String);

/// Not a name the node can be given.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NotAName;

impl fmt::Display for NotAName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(
            "not a name for the node: 1 to 63 letters, digits or inner hyphens, and not localhost",
        )
    }
}

impl std::error::Error for NotAName {}

impl NodeName {
    /// `raw`, lower-cased, if it is one label of letters, digits and inner
    /// hyphens, 1 to 63 characters, and not `localhost`. Nothing is trimmed.
    pub fn parse(raw: &str) -> Result<Self, NotAName> {
        let lower = raw.to_ascii_lowercase();
        let label_ok = !lower.is_empty()
            && lower.len() <= 63
            && !lower.starts_with('-')
            && !lower.ends_with('-')
            && lower
                .bytes()
                .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-');
        if label_ok && lower != "localhost" {
            Ok(Self(lower))
        } else {
            Err(NotAName)
        }
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// The name the node answers to on the LAN.
    pub fn local(&self) -> String {
        format!("{}.local", self.0)
    }
}

impl fmt::Display for NodeName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// The name line of a hostname file: its first line that is neither blank nor
/// a comment, trimmed (hostname(5)).
pub fn first_line(text: &str) -> Option<&str> {
    text.lines()
        .map(str::trim)
        .find(|line| !line.is_empty() && !line.starts_with('#'))
}

/// The node's name in a hostname file's text, if its name line is one.
pub fn name_in(text: &str) -> Option<NodeName> {
    first_line(text).and_then(|line| NodeName::parse(line).ok())
}

/// This process's user id, as the bus will see it on the socket: the owner
/// of `/proc/self`, so no `unsafe` call is needed.
pub fn own_uid() -> io::Result<u32> {
    std::fs::metadata("/proc/self").map(|m| m.uid())
}

// ---- the wire ---------------------------------------------------------------

/// What came back from the bus.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Kind {
    Call,
    Return,
    Error,
    Signal,
}

/// The parts of a message a rename looks at.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Message {
    pub kind: Kind,
    pub serial: u32,
    pub reply_serial: Option<u32>,
    pub error_name: Option<String>,
}

#[derive(Debug)]
pub enum BusError {
    /// The bus's socket could not be reached.
    Unreachable(io::Error),
    /// The connection failed after it was made.
    Io(io::Error),
    /// The bus did not accept the authentication; what it said.
    Auth(String),
    /// Polkit, or the bus, refused the call: the error's name.
    Denied(String),
    /// Hostnamed, or the bus, answered with another error: its name.
    Refused(String),
    /// The bus answered `Hello` with an error: its name (5c.4b-2, repair 2:
    /// the bus's own error, never the call's, so never resolved's "not found").
    Hello(String),
    /// Something the bus sent that this client does not read.
    Protocol(&'static str),
    /// No answer within the limit.
    TimedOut,
}

impl fmt::Display for BusError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            BusError::Unreachable(e) => write!(f, "the system bus could not be reached: {e}"),
            BusError::Io(e) => write!(f, "the connection to the system bus failed: {e}"),
            BusError::Auth(line) => write!(f, "the system bus refused to authenticate: {line:?}"),
            BusError::Denied(name) => write!(f, "renaming the node was not allowed: {name}"),
            BusError::Refused(name) => write!(f, "hostnamed refused the name: {name}"),
            BusError::Hello(name) => write!(f, "the system bus refused Hello: {name}"),
            BusError::Protocol(what) => write!(f, "the system bus sent {what}"),
            BusError::TimedOut => write!(f, "the system bus did not answer in time"),
        }
    }
}

impl std::error::Error for BusError {}

/// The error names that mean "not allowed".
const DENIED: [&str; 2] = [
    "org.freedesktop.DBus.Error.AccessDenied",
    "org.freedesktop.DBus.Error.InteractiveAuthorizationRequired",
];

/// SASL EXTERNAL with the user id as the bus expects it: its decimal digits,
/// each as two hex digits, after the protocol's leading NUL byte.
pub fn auth_line(uid: u32) -> Vec<u8> {
    let hex: String = uid
        .to_string()
        .bytes()
        .map(|b| format!("{b:02x}"))
        .collect();
    let mut line = b"\0AUTH EXTERNAL ".to_vec();
    line.extend_from_slice(hex.as_bytes());
    line.extend_from_slice(b"\r\n");
    line
}

/// The bus's own first call, which every connection must make.
pub fn hello(serial: u32) -> Vec<u8> {
    method_call(
        serial,
        "/org/freedesktop/DBus",
        "org.freedesktop.DBus",
        "org.freedesktop.DBus",
        "Hello",
        None,
    )
}

/// `SetStaticHostname(name, false)`: never interactive, so polkit answers yes
/// or no and never asks anyone.
pub fn set_static_hostname_call(name: &NodeName, serial: u32) -> Vec<u8> {
    let mut body = Wire::default();
    body.string(name.as_str());
    body.align(4);
    body.u32(0);
    method_call(
        serial,
        "/org/freedesktop/hostname1",
        "org.freedesktop.hostname1",
        "org.freedesktop.hostname1",
        "SetStaticHostname",
        Some(("sb", body.0)),
    )
}

// ---- is a name in use? (5c.4b-2) -------------------------------------------

/// systemd-resolved's flags (org.freedesktop.resolve1(5)): ask mDNS only,
/// over IPv4 and IPv6, never a synthesized answer and never the cache, so
/// the answer is the network's now. Resolved never looks the node's own
/// name up over mDNS (the drill saw "No appropriate name servers"), so that
/// name is `Unknown`, never free; setup's name, `rikurisetup`, is never a
/// candidate (repair 2, verifier nit 3).
pub const MDNS_IPV4: u64 = 1 << 3;
pub const MDNS_IPV6: u64 = 1 << 4;
pub const NO_SYNTHESIZE: u64 = 1 << 11;
pub const NO_CACHE: u64 = 1 << 12;
// Repair 1: written out, as `|` of bits that do not overlap is `^` too, which
// no test can tell apart; the test checks it is the named flags'.
pub const LOOKUP_FLAGS: u64 = 0x1818;
/// How long a suggestion may take in all: a page waits for it.
pub const SUGGEST_LIMIT: Duration = Duration::from_secs(30);

/// The errors from resolved that mean "nothing answers that name". Any other
/// error, or none in time, is [`Lookup::Unknown`], never free.
pub const FREE: [&str; 2] = [
    "org.freedesktop.resolve1.DnsError.NXDOMAIN",
    "org.freedesktop.DBus.Error.Timeout",
];

/// Whether something on the network answers a name.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Lookup {
    /// It answers: the name is in use.
    Taken,
    /// Resolved says nothing answers it.
    Free,
    /// Resolved could not say; why.
    Unknown(String),
}

/// `ResolveHostname(0, "<name>.local", AF_UNSPEC, LOOKUP_FLAGS)`: any
/// interface, either address family.
pub fn resolve_hostname_call(name: &NodeName, serial: u32) -> Vec<u8> {
    let mut body = Wire::default();
    body.u32(0);
    body.string(&name.local());
    body.u32(0);
    body.u64(LOOKUP_FLAGS);
    method_call(
        serial,
        "/org/freedesktop/resolve1",
        "org.freedesktop.resolve1",
        "org.freedesktop.resolve1.Manager",
        "ResolveHostname",
        Some(("isit", body.0)),
    )
}

/// A lookup's outcome from the bus's answer: a return is an answer, only
/// resolved's own "not found" is free, and anything else is unknown.
pub fn lookup(answer: Result<(), BusError>) -> Lookup {
    match answer {
        Ok(()) => Lookup::Taken,
        Err(BusError::Refused(name)) if FREE.contains(&name.as_str()) => Lookup::Free,
        Err(e) => Lookup::Unknown(e.to_string()),
    }
}

/// Asks resolved, through the bus at `socket`, whether `name.local` answers.
pub async fn name_answers(socket: &Path, uid: u32, name: &NodeName, limit: Duration) -> Lookup {
    lookup(call(socket, uid, resolve_hostname_call(name, CALL_SERIAL), limit).await)
}

/// The names the suggestion tries, in order.
pub fn candidates() -> impl Iterator<Item = NodeName> {
    (1..=99).filter_map(|n| NodeName::parse(&format!("rikuri{n:02}")).ok())
}

/// The first of [`candidates`] that `look` finds free, one at a time, all
/// within `limit`: `Ok(None)` when every one is taken or the limit runs out;
/// `Err` as soon as one is [`Lookup::Unknown`], never a guess.
pub async fn suggest<F, Fut>(mut look: F, limit: Duration) -> Result<Option<NodeName>, String>
where
    F: FnMut(NodeName) -> Fut,
    Fut: std::future::Future<Output = Lookup>,
{
    let first_free = async {
        for name in candidates() {
            match look(name.clone()).await {
                Lookup::Free => return Ok(Some(name)),
                Lookup::Taken => {}
                Lookup::Unknown(why) => return Err(format!("{}: {why}", name.local())),
            }
        }
        Ok(None)
    };
    tokio::time::timeout(limit, first_free)
        .await
        .unwrap_or(Ok(None))
}

/// A method call, little-endian, expecting a reply, with no flags: the
/// fixed header, then the header fields (each aligned to 8 from the
/// message's start: path, destination, interface, member, and the body's
/// signature if any), padding to 8, and the body.
fn method_call(
    serial: u32,
    path: &str,
    destination: &str,
    interface: &str,
    member: &str,
    body: Option<(&str, Vec<u8>)>,
) -> Vec<u8> {
    let mut m = Wire::default();
    m.bytes(&[b'l', 1, 0, 1]);
    let body_len = body.as_ref().map_or(0, |(_, b)| b.len());
    m.u32(u32::try_from(body_len).unwrap_or(u32::MAX));
    m.u32(serial);
    m.u32(0); // the fields' length, written below
    let start = m.0.len();
    m.field(1, b'o', path);
    m.field(6, b's', destination);
    m.field(2, b's', interface);
    m.field(3, b's', member);
    if let Some((signature, _)) = &body {
        m.field(8, b'g', signature);
    }
    let fields_len = u32::try_from(m.0.len() - start).unwrap_or(u32::MAX);
    m.0[12..16].copy_from_slice(&fields_len.to_le_bytes());
    m.align(8);
    if let Some((_, bytes)) = body {
        m.bytes(&bytes);
    }
    m.0
}

/// The writer: offsets are the message's own, so alignment is absolute.
#[derive(Default)]
struct Wire(Vec<u8>);

impl Wire {
    fn align(&mut self, n: usize) {
        while !self.0.len().is_multiple_of(n) {
            self.0.push(0);
        }
    }
    fn bytes(&mut self, b: &[u8]) {
        self.0.extend_from_slice(b);
    }
    fn u32(&mut self, v: u32) {
        self.align(4);
        self.0.extend_from_slice(&v.to_le_bytes());
    }
    fn u64(&mut self, v: u64) {
        self.align(8);
        self.0.extend_from_slice(&v.to_le_bytes());
    }
    fn string(&mut self, s: &str) {
        self.u32(u32::try_from(s.len()).unwrap_or(u32::MAX));
        self.bytes(s.as_bytes());
        self.0.push(0);
    }
    fn signature(&mut self, s: &str) {
        self.0.push(u8::try_from(s.len()).unwrap_or(u8::MAX));
        self.bytes(s.as_bytes());
        self.0.push(0);
    }
    /// One header field: its code, its one-character type, its value.
    fn field(&mut self, code: u8, kind: u8, value: &str) {
        self.align(8);
        self.bytes(&[code, 1, kind, 0]);
        if kind == b'g' {
            self.signature(value);
        } else {
            self.string(value);
        }
    }
}

fn align(n: usize, to: usize) -> Option<usize> {
    n.checked_add(to - 1).map(|v| v / to * to)
}

fn u32_at(buf: &[u8], at: usize) -> Result<u32, BusError> {
    buf.get(at..at + 4)
        .and_then(|b| b.try_into().ok())
        .map(u32::from_le_bytes)
        .ok_or(BusError::Protocol("a header field cut short"))
}

/// The first message in `buf`, and how many bytes it took; `None` while it is
/// still incomplete. Refuses at once a message that is not little-endian
/// D-Bus 1, is of no known type, would be larger than [`MAX_MESSAGE`], or has
/// a header field this client cannot read.
pub fn parse_message(buf: &[u8]) -> Result<Option<(Message, usize)>, BusError> {
    const SHORT: BusError = BusError::Protocol("a header field cut short");
    if buf.len() < 16 {
        return Ok(None);
    }
    if buf[0] != b'l' {
        return Err(BusError::Protocol("a message that is not little-endian"));
    }
    let kind = match buf[1] {
        1 => Kind::Call,
        2 => Kind::Return,
        3 => Kind::Error,
        4 => Kind::Signal,
        _ => return Err(BusError::Protocol("a message of no known type")),
    };
    if buf[3] != 1 {
        return Err(BusError::Protocol("a message of another protocol version"));
    }
    let body_len = u32_at(buf, 4)? as usize;
    let serial = u32_at(buf, 8)?;
    let fields_end = 16usize
        .checked_add(u32_at(buf, 12)? as usize)
        .ok_or(BusError::Protocol("a message over the size limit"))?;
    let total = align(fields_end, 8)
        .and_then(|at| at.checked_add(body_len))
        .filter(|&total| total <= MAX_MESSAGE)
        .ok_or(BusError::Protocol("a message over the size limit"))?;
    if buf.len() < total {
        return Ok(None);
    }
    let mut reply_serial = None;
    let mut error_name = None;
    let mut pos = 16;
    while pos < fields_end {
        pos = align(pos, 8).ok_or(SHORT)?;
        let head = buf.get(pos..pos + 4).ok_or(SHORT)?;
        let (code, sig_len, kind_byte, nul) = (head[0], head[1], head[2], head[3]);
        if sig_len != 1 || nul != 0 {
            return Err(BusError::Protocol(
                "a header field of a type this client does not read",
            ));
        }
        pos += 4;
        let text = match kind_byte {
            b'u' => {
                pos = align(pos, 4).ok_or(SHORT)?;
                let value = u32_at(buf, pos)?;
                pos += 4;
                match code {
                    5 => reply_serial = Some(value),
                    4 => return Err(BusError::Protocol("an error name of the wrong type")),
                    _ => {}
                }
                None
            }
            b's' | b'o' => {
                pos = align(pos, 4).ok_or(SHORT)?;
                let len = u32_at(buf, pos)? as usize;
                pos += 4;
                let end = pos.checked_add(len).ok_or(SHORT)?;
                let bytes = buf.get(pos..end).ok_or(SHORT)?;
                if buf.get(end) != Some(&0) {
                    return Err(SHORT);
                }
                pos = end + 1;
                Some(bytes)
            }
            b'g' => {
                let len = *buf.get(pos).ok_or(SHORT)? as usize;
                pos += 1;
                let end = pos.checked_add(len).ok_or(SHORT)?;
                let bytes = buf.get(pos..end).ok_or(SHORT)?;
                if buf.get(end) != Some(&0) {
                    return Err(SHORT);
                }
                pos = end + 1;
                Some(bytes)
            }
            _ => {
                return Err(BusError::Protocol(
                    "a header field of a type this client does not read",
                ));
            }
        };
        match (code, text) {
            (5, Some(_)) => return Err(BusError::Protocol("a reply serial of the wrong type")),
            (4, Some(bytes)) => {
                error_name = Some(
                    String::from_utf8(bytes.to_vec())
                        .map_err(|_| BusError::Protocol("an error name that is not UTF-8"))?,
                );
            }
            _ => {}
        }
        if pos > fields_end {
            return Err(SHORT);
        }
    }
    Ok(Some((
        Message {
            kind,
            serial,
            reply_serial,
            error_name,
        },
        total,
    )))
}

// ---- the call ---------------------------------------------------------------

/// Asks hostnamed, through the bus at `socket`, to make `name` the node's
/// static hostname, as the user `uid` (the bus checks it on the socket).
/// `Ok` only on hostnamed's method return to that call, after the bus's
/// return to `Hello`; anything else within `limit` is an error.
pub async fn set_static_hostname(
    socket: &Path,
    uid: u32,
    name: &NodeName,
    limit: Duration,
) -> Result<(), BusError> {
    call(
        socket,
        uid,
        set_static_hostname_call(name, CALL_SERIAL),
        limit,
    )
    .await
}

/// One fixed call, made as [`CALL_SERIAL`] after `Hello`, within `limit`.
async fn call(socket: &Path, uid: u32, call: Vec<u8>, limit: Duration) -> Result<(), BusError> {
    tokio::time::timeout(limit, exchange(socket, uid, call))
        .await
        .map_err(|_| BusError::TimedOut)?
}

async fn exchange(socket: &Path, uid: u32, call: Vec<u8>) -> Result<(), BusError> {
    let mut bus = UnixStream::connect(socket)
        .await
        .map_err(BusError::Unreachable)?;
    bus.write_all(&auth_line(uid)).await.map_err(BusError::Io)?;
    let line = auth_answer(&mut bus).await?;
    if !line.starts_with(b"OK ") {
        return Err(BusError::Auth(String::from_utf8_lossy(&line).into_owned()));
    }
    let mut out = b"BEGIN\r\n".to_vec();
    out.extend_from_slice(&hello(HELLO_SERIAL));
    out.extend_from_slice(&call);
    bus.write_all(&out).await.map_err(BusError::Io)?;

    let mut buf = Vec::new();
    let mut read = 0;
    let mut hello_answered = false;
    loop {
        while let Some((message, used)) = parse_message(&buf)? {
            buf.drain(..used);
            match (message.kind, message.reply_serial) {
                (Kind::Return, Some(HELLO_SERIAL)) => hello_answered = true,
                (Kind::Error, Some(HELLO_SERIAL)) => {
                    return Err(BusError::Hello(error_name(message)));
                }
                (Kind::Return, Some(CALL_SERIAL)) if hello_answered => return Ok(()),
                (Kind::Error, Some(CALL_SERIAL)) => {
                    let name = error_name(message);
                    return Err(if DENIED.contains(&name.as_str()) {
                        BusError::Denied(name)
                    } else {
                        BusError::Refused(name)
                    });
                }
                (_, Some(CALL_SERIAL)) => {
                    return Err(BusError::Protocol("an answer to the call before Hello's"));
                }
                // Signals (NameAcquired), and replies to nothing this sent.
                _ => {}
            }
        }
        let mut chunk = [0u8; 4096];
        let n = bus.read(&mut chunk).await.map_err(BusError::Io)?;
        if n == 0 {
            return Err(BusError::Protocol(
                "the end of the connection, and no answer",
            ));
        }
        read += n;
        if read > MAX_READ {
            return Err(BusError::Protocol("more than a rename's answer"));
        }
        buf.extend_from_slice(&chunk[..n]);
    }
}

fn error_name(message: Message) -> String {
    message
        .error_name
        .unwrap_or_else(|| "(an error with no name)".to_owned())
}

/// The bus's one line in answer to the authentication, without its `\r\n`.
/// The bus sends nothing more until `BEGIN`, so it is read a byte at a time,
/// and anything past the line is refused.
async fn auth_answer(bus: &mut UnixStream) -> Result<Vec<u8>, BusError> {
    let mut line = Vec::new();
    loop {
        let mut byte = [0u8; 1];
        if bus.read(&mut byte).await.map_err(BusError::Io)? == 0 {
            return Err(BusError::Protocol(
                "the end of the connection while authenticating",
            ));
        }
        line.push(byte[0]);
        if line.ends_with(b"\r\n") {
            line.truncate(line.len() - 2);
            return Ok(line);
        }
        if line.len() > MAX_AUTH_LINE {
            return Err(BusError::Protocol("an authentication line over the limit"));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::MetadataExt;

    fn le(n: u32) -> [u8; 4] {
        n.to_le_bytes()
    }

    fn cat(parts: &[&[u8]]) -> Vec<u8> {
        parts.concat()
    }

    #[test]
    fn a_name_is_one_label_lower_cased() {
        let long = "a".repeat(63);
        for good in ["rikuri01", "a", "node-2", "0rikuri", "123", long.as_str()] {
            assert_eq!(NodeName::parse(good).unwrap().as_str(), good);
        }
        assert_eq!(NodeName::parse("RikuRi01").unwrap().as_str(), "rikuri01");
        assert_eq!(
            NodeName::parse("rikuri01").unwrap().local(),
            "rikuri01.local"
        );
    }

    #[test]
    fn anything_else_is_not_a_name() {
        let long = "a".repeat(64);
        for bad in [
            "",
            " rikuri01",
            "rikuri01 ",
            "rikuri01\n",
            "rikuri.local",
            "rikuri01.",
            "-rikuri",
            "rikuri-",
            "-",
            "riku_ri",
            "ríkuri",
            "rikuri01:443",
            "a/b",
            "localhost",
            "LocalHost",
            long.as_str(),
        ] {
            assert_eq!(NodeName::parse(bad), Err(NotAName), "{bad:?}");
        }
    }

    #[test]
    fn the_files_name_is_its_first_line_neither_blank_nor_a_comment() {
        assert_eq!(
            first_line("# a comment\n\n  rikuri02  \nother\n"),
            Some("rikuri02")
        );
        assert_eq!(first_line("\n# only a comment\n"), None);
        assert_eq!(first_line(""), None);
        assert_eq!(
            name_in("rikurisetup\n"),
            Some(NodeName::parse("rikurisetup").unwrap())
        );
        assert_eq!(name_in("Rikuri03\n").unwrap().as_str(), "rikuri03");
        assert_eq!(name_in("not a name\n"), None);
        assert_eq!(name_in("rikuri.example.org\n"), None);
    }

    #[test]
    fn the_auth_line_is_external_with_the_uids_digits_in_hex() {
        assert_eq!(auth_line(1000), b"\0AUTH EXTERNAL 31303030\r\n");
        assert_eq!(auth_line(0), b"\0AUTH EXTERNAL 30\r\n");
        assert_eq!(auth_line(978), b"\0AUTH EXTERNAL 393738\r\n");
    }

    #[test]
    fn hello_is_byte_for_byte_the_buses_own_call() {
        let want = cat(&[
            b"l\x01\x00\x01",
            &le(0),
            &le(1),
            &le(110),
            // 16: the path
            b"\x01\x01o\x00",
            &le(21),
            b"/org/freedesktop/DBus\0",
            &[0; 2],
            // 48: the destination
            b"\x06\x01s\x00",
            &le(20),
            b"org.freedesktop.DBus\0",
            &[0; 3],
            // 80: the interface
            b"\x02\x01s\x00",
            &le(20),
            b"org.freedesktop.DBus\0",
            &[0; 3],
            // 112: the member, then padding to 128 and no body
            b"\x03\x01s\x00",
            &le(5),
            b"Hello\0",
            &[0; 2],
        ]);
        assert_eq!(want.len(), 128);
        assert_eq!(hello(1), want);
    }

    #[test]
    fn set_static_hostname_is_byte_for_byte_and_never_interactive() {
        let name = NodeName::parse("rikuri01").unwrap();
        let want = cat(&[
            b"l\x01\x00\x01",
            &le(20),
            &le(2),
            &le(160),
            // 16: the path
            b"\x01\x01o\x00",
            &le(26),
            b"/org/freedesktop/hostname1\0",
            &[0; 5],
            // 56: the destination
            b"\x06\x01s\x00",
            &le(25),
            b"org.freedesktop.hostname1\0",
            &[0; 6],
            // 96: the interface
            b"\x02\x01s\x00",
            &le(25),
            b"org.freedesktop.hostname1\0",
            &[0; 6],
            // 136: the member
            b"\x03\x01s\x00",
            &le(17),
            b"SetStaticHostname\0",
            &[0; 6],
            // 168: the body's signature, ending at 176, already aligned
            b"\x08\x01g\x00",
            b"\x02sb\0",
            // 176: the body: the name, padding to 4, and false
            &le(8),
            b"rikuri01\0",
            &[0; 3],
            &le(0),
        ]);
        assert_eq!(want.len(), 196);
        assert_eq!(set_static_hostname_call(&name, 2), want);
    }

    #[test]
    fn the_bodys_padding_follows_the_names_length() {
        let call = set_static_hostname_call(&NodeName::parse("a").unwrap(), 7);
        assert_eq!(&call[4..8], &le(12), "a 1-byte name: 4 + 2 + 2 + 4");
        assert_eq!(&call[8..12], &le(7), "the serial");
        assert_eq!(call.len(), 176 + 12);
        assert_eq!(&call[176..], cat(&[&le(1), b"a\0", &[0; 2], &le(0)]));
    }

    /// A method return to serial 2, as the bus sends it: reply serial,
    /// destination and sender; no body.
    fn a_return() -> Vec<u8> {
        cat(&[
            b"l\x02\x01\x01",
            &le(0),
            &le(7),
            &le(37),
            b"\x05\x01u\x00",
            &le(2),
            b"\x06\x01s\x00",
            &le(5),
            b":1.42\0",
            &[0; 2],
            b"\x07\x01s\x00",
            &le(4),
            b":1.3\0",
            &[0; 3],
        ])
    }

    /// An error to serial 2: reply serial, error name, signature, and the
    /// message in the body.
    fn an_error() -> Vec<u8> {
        cat(&[
            b"l\x03\x01\x01",
            &le(22),
            &le(9),
            &le(63),
            b"\x05\x01u\x00",
            &le(2),
            b"\x04\x01s\x00",
            &le(39),
            b"org.freedesktop.DBus.Error.AccessDenied\0",
            b"\x08\x01g\x00",
            b"\x01s\0",
            &[0; 1],
            &le(17),
            b"Permission denied\0",
        ])
    }

    #[test]
    fn a_return_and_an_error_are_read() {
        let ret = a_return();
        assert_eq!(ret.len(), 56);
        assert_eq!(
            parse_message(&ret).unwrap(),
            Some((
                Message {
                    kind: Kind::Return,
                    serial: 7,
                    reply_serial: Some(2),
                    error_name: None
                },
                56
            ))
        );
        let err = an_error();
        assert_eq!(err.len(), 102);
        assert_eq!(
            parse_message(&err).unwrap(),
            Some((
                Message {
                    kind: Kind::Error,
                    serial: 9,
                    reply_serial: Some(2),
                    error_name: Some("org.freedesktop.DBus.Error.AccessDenied".to_owned())
                },
                102
            ))
        );
        let both = cat(&[&ret, &err]);
        let (_, used) = parse_message(&both).unwrap().unwrap();
        assert_eq!(used, 56);
        assert_eq!(
            parse_message(&both[used..]).unwrap().unwrap().0.kind,
            Kind::Error
        );
    }

    #[test]
    fn an_incomplete_message_waits_for_more() {
        let err = an_error();
        for cut in 0..err.len() {
            assert!(
                matches!(parse_message(&err[..cut]), Ok(None)),
                "cut at {cut}"
            );
        }
    }

    #[test]
    fn what_this_client_does_not_read_is_refused() {
        let ret = a_return();
        let with = |at: usize, byte: u8| {
            let mut m = ret.clone();
            m[at] = byte;
            m
        };
        let refused = |m: &[u8]| matches!(parse_message(m), Err(BusError::Protocol(_)));
        assert!(refused(&with(0, b'B')), "big-endian");
        assert!(refused(&with(1, 0)), "no type");
        assert!(refused(&with(1, 5)), "an unknown type");
        assert!(refused(&with(3, 2)), "another protocol version");
        assert!(
            refused(&with(18, b'x')),
            "a field of a type it does not read"
        );
        assert!(refused(&with(17, 2)), "a two-character field type");
        // A reply serial sent as a string.
        let as_string = cat(&[
            b"l\x02\x01\x01",
            &le(0),
            &le(7),
            &le(10),
            b"\x05\x01s\x00",
            &le(1),
            b"x\0",
            &[0; 6],
        ]);
        assert_eq!(as_string.len(), 32);
        assert!(refused(&as_string), "a reply serial that is not a u32");
        // The destination's length runs past the fields.
        let mut long = ret.clone();
        long[28..32].copy_from_slice(&le(200));
        assert!(refused(&long), "a string past the fields");
        // A missing NUL after a string.
        assert!(refused(&with(37, b'x')), "a string without its NUL");
        // An error name of the wrong type.
        let mut wrong = an_error();
        wrong[26] = b'u';
        assert!(refused(&wrong), "an error name that is a u32");
    }

    /// Repair 2 (verifier, Important 3): an error name sent as a u32 must
    /// reach its own refusal, not fail on later bytes by accident.
    #[test]
    fn an_error_name_that_is_a_u32_is_refused() {
        let u32_name = cat(&[
            b"l\x03\x01\x01",
            &le(0),
            &le(9),
            &le(8),
            b"\x04\x01u\x00",
            &le(5),
        ]);
        assert_eq!(u32_name.len(), 24);
        assert!(matches!(
            parse_message(&u32_name),
            Err(BusError::Protocol("an error name of the wrong type"))
        ));
    }

    /// Repair 2 (verifier, nit 1): the limits' values, not only their names.
    #[test]
    fn the_limits_are_what_the_design_says() {
        assert_eq!(MAX_MESSAGE, 65_536);
        assert_eq!(MAX_READ, 262_144);
        assert_eq!(BUS_TIMEOUT, Duration::from_secs(10));
    }

    /// Repair 3 (owner's authorization; CI's mutants job): what each error
    /// says, as the logs and an unknown lookup's reason carry it.
    #[test]
    fn each_error_says_what_happened() {
        let said = |e: BusError| e.to_string();
        let name = || "org.example.Error".to_owned();
        assert_eq!(
            said(BusError::Unreachable(io::Error::other("gone"))),
            "the system bus could not be reached: gone"
        );
        assert_eq!(
            said(BusError::Io(io::Error::other("cut"))),
            "the connection to the system bus failed: cut"
        );
        assert_eq!(
            said(BusError::Auth("REJECTED".to_owned())),
            "the system bus refused to authenticate: \"REJECTED\""
        );
        assert_eq!(
            said(BusError::Denied(name())),
            "renaming the node was not allowed: org.example.Error"
        );
        assert_eq!(
            said(BusError::Refused(name())),
            "hostnamed refused the name: org.example.Error"
        );
        assert_eq!(
            said(BusError::Hello(name())),
            "the system bus refused Hello: org.example.Error"
        );
        assert_eq!(
            said(BusError::Protocol("nonsense")),
            "the system bus sent nonsense"
        );
        assert_eq!(
            said(BusError::TimedOut),
            "the system bus did not answer in time"
        );
    }

    // ---- 5c.4b-2: is a name in use? ----

    #[test]
    fn resolve_hostname_is_byte_for_byte_and_mdns_only() {
        let name = NodeName::parse("rikuri01").unwrap();
        let want = cat(&[
            b"l\x01\x00\x01",
            &le(40),
            &le(2),
            &le(162),
            // 16: the path
            b"\x01\x01o\x00",
            &le(25),
            b"/org/freedesktop/resolve1\0",
            &[0; 6],
            // 56: the destination
            b"\x06\x01s\x00",
            &le(24),
            b"org.freedesktop.resolve1\0",
            &[0; 7],
            // 96: the interface
            b"\x02\x01s\x00",
            &le(32),
            b"org.freedesktop.resolve1.Manager\0",
            &[0; 7],
            // 144: the member, ending at 168
            b"\x03\x01s\x00",
            &le(15),
            b"ResolveHostname\0",
            // 168: the body's signature, ending at 178, then padding to 184
            b"\x08\x01g\x00",
            b"\x04isit\0",
            &[0; 6],
            // 184: any interface, the name, AF_UNSPEC, then the flags at 216
            &le(0),
            &le(14),
            b"rikuri01.local\0",
            &[0; 1],
            &le(0),
            &[0; 4],
            &0x1818_u64.to_le_bytes(),
        ]);
        assert_eq!(want.len(), 224);
        assert_eq!(resolve_hostname_call(&name, 2), want);
    }

    #[test]
    fn the_lookup_asks_mdns_only_never_synthesized_or_cached() {
        assert_eq!(LOOKUP_FLAGS, 8 | 16 | 2048 | 4096);
        assert_eq!(
            LOOKUP_FLAGS,
            MDNS_IPV4 | MDNS_IPV6 | NO_SYNTHESIZE | NO_CACHE
        );
        assert_eq!(
            [MDNS_IPV4, MDNS_IPV6, NO_SYNTHESIZE, NO_CACHE],
            [1 << 3, 1 << 4, 1 << 11, 1 << 12]
        );
        // Neither DNS (1) nor LLMNR (2, 4), and the node's own zone (8192)
        // is not turned off.
        assert_eq!(LOOKUP_FLAGS & (1 | 2 | 4 | 8192), 0);
    }

    #[test]
    fn only_resolveds_not_found_is_free_and_only_an_answer_taken() {
        let refused = |n: &str| Err(BusError::Refused(n.to_owned()));
        assert_eq!(lookup(Ok(())), Lookup::Taken);
        for free in FREE {
            assert_eq!(lookup(refused(free)), Lookup::Free, "{free}");
        }
        assert_eq!(
            FREE,
            [
                "org.freedesktop.resolve1.DnsError.NXDOMAIN",
                "org.freedesktop.DBus.Error.Timeout",
            ]
        );
        for unknown in [
            refused("org.freedesktop.resolve1.NoSuchRR"),
            refused("org.freedesktop.resolve1.NoNameServers"),
            refused("org.freedesktop.DBus.Error.ServiceUnknown"),
            Err(BusError::Denied(
                "org.freedesktop.resolve1.DnsError.NXDOMAIN".to_owned(),
            )),
            // Repair 2 (verifier, nit 1): the bus's answer to Hello.
            Err(BusError::Hello(
                "org.freedesktop.DBus.Error.Timeout".to_owned(),
            )),
            Err(BusError::TimedOut),
            Err(BusError::Protocol("x")),
            Err(BusError::Auth("REJECTED".to_owned())),
            Err(BusError::Io(io::Error::other("x"))),
            Err(BusError::Unreachable(io::Error::other("x"))),
        ] {
            let shown = format!("{unknown:?}");
            assert!(matches!(lookup(unknown), Lookup::Unknown(_)), "{shown}");
        }
    }

    #[test]
    fn the_candidates_are_rikuri01_to_rikuri99() {
        let all: Vec<String> = candidates().map(|n| n.as_str().to_owned()).collect();
        assert_eq!(all.len(), 99);
        assert_eq!(all[0], "rikuri01");
        assert_eq!(all[8], "rikuri09");
        assert_eq!(all[9], "rikuri10");
        assert_eq!(all[98], "rikuri99");
    }

    /// `suggest` with names answering as `taken` says, each lookup taking
    /// `each`; the names it asked about.
    async fn suggesting(
        taken: fn(&str) -> bool,
        unknown: Option<&'static str>,
        each: Duration,
        limit: Duration,
    ) -> (Result<Option<NodeName>, String>, Vec<String>) {
        let asked = std::sync::Arc::new(std::sync::Mutex::new(Vec::new()));
        let log = asked.clone();
        let result = suggest(
            move |name: NodeName| {
                let log = log.clone();
                async move {
                    tokio::time::sleep(each).await;
                    let n = name.as_str().to_owned();
                    log.lock().unwrap().push(n.clone());
                    if Some(n.as_str()) == unknown {
                        Lookup::Unknown("resolved could not say".to_owned())
                    } else if taken(&n) {
                        Lookup::Taken
                    } else {
                        Lookup::Free
                    }
                }
            },
            limit,
        )
        .await;
        let asked = asked.lock().unwrap().clone();
        (result, asked)
    }

    const SOON: Duration = Duration::from_millis(1);
    const LONG: Duration = Duration::from_secs(30);

    #[tokio::test]
    async fn the_suggestion_is_the_first_free_name_asked_in_order() {
        let (got, asked) =
            suggesting(|n| ["rikuri01", "rikuri02"].contains(&n), None, SOON, LONG).await;
        assert_eq!(got.unwrap().unwrap().as_str(), "rikuri03");
        assert_eq!(asked, ["rikuri01", "rikuri02", "rikuri03"], "and no more");
        let (got, asked) = suggesting(|_| false, None, SOON, LONG).await;
        assert_eq!(got.unwrap().unwrap().as_str(), "rikuri01");
        assert_eq!(asked, ["rikuri01"]);
    }

    #[tokio::test]
    async fn every_name_taken_is_no_suggestion() {
        let (got, asked) = suggesting(|_| true, None, Duration::ZERO, LONG).await;
        assert_eq!(got, Ok(None));
        assert_eq!(asked.len(), 99);
    }

    #[tokio::test]
    async fn an_unknown_answer_stops_the_suggestion() {
        let (got, asked) = suggesting(|n| n == "rikuri01", Some("rikuri02"), SOON, LONG).await;
        assert!(got.is_err(), "{got:?}");
        assert_eq!(asked, ["rikuri01", "rikuri02"]);
    }

    #[tokio::test]
    async fn the_limit_ends_the_suggestion_unchecked() {
        // Out of time is not "every name taken": the node does not know.
        let started = std::time::Instant::now();
        let (got, asked) = suggesting(
            |_| true,
            None,
            Duration::from_millis(40),
            Duration::from_millis(100),
        )
        .await;
        assert!(got.is_err(), "{got:?}");
        assert!(asked.len() < 4, "{asked:?}");
        assert!(started.elapsed() < Duration::from_secs(2));
    }

    #[test]
    fn the_suggestions_limit_is_what_the_design_says() {
        assert_eq!(SUGGEST_LIMIT, Duration::from_secs(30));
    }

    #[test]
    fn a_message_over_the_limit_is_refused_before_it_is_read() {
        let mut huge = a_return();
        huge[4..8].copy_from_slice(&le(MAX_MESSAGE as u32));
        assert!(matches!(
            parse_message(&huge[..16]),
            Err(BusError::Protocol(_))
        ));
        let mut fields = a_return();
        fields[12..16].copy_from_slice(&le(u32::MAX));
        assert!(matches!(
            parse_message(&fields[..16]),
            Err(BusError::Protocol(_))
        ));
    }

    #[test]
    fn the_uid_is_this_processes() {
        let uid = own_uid().unwrap();
        // A file this process makes is owned by its uid.
        let probe = std::env::temp_dir().join(format!("rikuri-uid-{}", std::process::id()));
        std::fs::write(&probe, b"").unwrap();
        let made = std::fs::metadata(&probe).unwrap().uid();
        let _ = std::fs::remove_file(&probe);
        assert_eq!(uid, made);
    }
}
