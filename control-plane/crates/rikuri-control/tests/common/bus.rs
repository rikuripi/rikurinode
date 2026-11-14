//! A stand-in system bus with hostnamed behind it (5c.4b-1), on a Unix socket
//! of the test's own: it takes SASL EXTERNAL, answers `Hello`, and answers the
//! rename as told, writing the hostname file as hostnamed would. It reads the
//! client's messages by their fixed header alone (lengths at fixed offsets),
//! so it does not lean on the client's own reader; the unit tests in
//! `hostname.rs` pin the client's bytes. Its replies are written out by hand.
//!
//! 5c.4b-2: it is resolved too. A call to `org.freedesktop.resolve1` is a
//! lookup, answered as its [`Lookups`] say; any other call is the rename.

use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{UnixListener, UnixStream};
use tokio::task::JoinHandle;

/// How the stand-in answers the rename.
#[derive(Clone, Debug)]
pub enum Answer {
    /// Writes the hostname file, then a method return, after a signal and a
    /// reply to nothing the client sent, which the client must skip.
    Renamed,
    /// An error of this name; the file is left alone.
    Error(&'static str),
    /// A method return, but the file is left alone.
    ReturnOnly,
    /// `REJECTED` to the authentication.
    Rejected,
    /// Reads the calls, then closes the connection with no answer. Repair 1:
    /// it closed right after `OK`, which raced the client's write of `BEGIN`
    /// and its calls (EPIPE, so `Io`) against its read (end of file, so
    /// `Protocol`); now the client always reads the end.
    Hangs,
    /// Answers the authentication, then never anything more.
    Silent,
    /// A message header announcing more than the client may read.
    Huge,
    /// The answer to the call before the answer to `Hello`.
    CallBeforeHello,
    /// Repair 2 (verifier, Important 1 and 2): answers `Hello`, then sends
    /// signals in writes of an odd size (so the client's running count does
    /// not land on the limit exactly), past `MAX_READ`, and never answers.
    Flood,
    /// Repair 2 (verifier, Important 4): `Hello` answered with an error.
    HelloError(&'static str),
}

/// How the stand-in answers lookups (5c.4b-2).
#[derive(Clone, Copy, Debug)]
pub enum Lookups {
    /// These names (without `.local`) answer; every other one is NXDOMAIN.
    Taken(&'static [&'static str]),
    /// Every name answers.
    All,
    /// Every lookup gets this error.
    Error(&'static str),
    /// Repair 2 (verifier, nit 1): `Hello` gets this error, and the lookup
    /// no answer.
    HelloError(&'static str),
    /// Every name is free (NXDOMAIN), after this long: a suggestion held open.
    Slow(std::time::Duration),
}

pub const NXDOMAIN: &str = "org.freedesktop.resolve1.DnsError.NXDOMAIN";

/// What the stand-in received.
#[derive(Clone, Debug, Default)]
pub struct Seen {
    pub auth: Vec<Vec<u8>>,
    pub messages: Vec<Vec<u8>>,
    /// The names the renames asked for.
    pub names: Vec<String>,
    /// The names the lookups asked about, with `.local`, in order.
    pub lookups: Vec<String>,
}

pub struct Bus {
    pub path: PathBuf,
    seen: Arc<Mutex<Seen>>,
    task: JoinHandle<()>,
}

impl Bus {
    /// Every lookup answers "free".
    pub fn start(path: PathBuf, hostname_file: PathBuf, answer: Answer) -> Bus {
        Bus::with_lookups(path, hostname_file, answer, Lookups::Taken(&[]))
    }

    pub fn with_lookups(
        path: PathBuf,
        hostname_file: PathBuf,
        answer: Answer,
        lookups: Lookups,
    ) -> Bus {
        let _ = std::fs::remove_file(&path);
        let listener = UnixListener::bind(&path).unwrap();
        let seen = Arc::new(Mutex::new(Seen::default()));
        let task = {
            let seen = seen.clone();
            tokio::spawn(async move {
                loop {
                    let Ok((conn, _)) = listener.accept().await else {
                        return;
                    };
                    let (seen, file, answer) =
                        (seen.clone(), hostname_file.clone(), answer.clone());
                    tokio::spawn(async move {
                        let _ = serve(conn, seen, file, answer, lookups).await;
                    });
                }
            })
        };
        Bus { path, seen, task }
    }

    pub fn seen(&self) -> Seen {
        self.seen.lock().unwrap().clone()
    }
}

impl Drop for Bus {
    fn drop(&mut self) {
        self.task.abort();
        let _ = std::fs::remove_file(&self.path);
    }
}

fn le(n: u32) -> [u8; 4] {
    n.to_le_bytes()
}

fn u32_at(b: &[u8], at: usize) -> u32 {
    u32::from_le_bytes(b[at..at + 4].try_into().unwrap())
}

fn padded(n: usize) -> usize {
    n.div_ceil(8) * 8
}

/// A method return (kind 2) or a signal (kind 4) with only a reply serial,
/// no body: 24 bytes.
fn reply(kind: u8, serial: u32, reply_serial: u32) -> Vec<u8> {
    [
        &[b'l', kind, 1, 1][..],
        &le(0),
        &le(serial),
        &le(8),
        b"\x05\x01u\x00",
        &le(reply_serial),
    ]
    .concat()
}

/// An error to `reply_serial`, named `name`, with no body.
fn error(serial: u32, reply_serial: u32, name: &str) -> Vec<u8> {
    let fields_len = 8 + 8 + name.len() + 1;
    let mut m = [
        &[b'l', 3, 1, 1][..],
        &le(0),
        &le(serial),
        &le(fields_len as u32),
        b"\x05\x01u\x00",
        &le(reply_serial),
        b"\x04\x01s\x00",
        &le(name.len() as u32),
        name.as_bytes(),
        b"\0",
    ]
    .concat();
    m.resize(padded(m.len()), 0);
    m
}

/// `NameAcquired`-like: a signal with only a path, 48 bytes.
fn signal(serial: u32) -> Vec<u8> {
    let mut m = [
        &[b'l', 4, 1, 1][..],
        &le(0),
        &le(serial),
        &le(30),
        b"\x01\x01o\x00",
        &le(21),
        b"/org/freedesktop/DBus\0",
    ]
    .concat();
    m.resize(48, 0);
    m
}

async fn read_until(conn: &mut UnixStream, end: &[u8]) -> Option<Vec<u8>> {
    let mut out = Vec::new();
    while !out.ends_with(end) {
        let mut byte = [0u8; 1];
        if conn.read(&mut byte).await.ok()? == 0 || out.len() > 1024 {
            return None;
        }
        out.push(byte[0]);
    }
    Some(out)
}

async fn read_message(conn: &mut UnixStream) -> Option<Vec<u8>> {
    let mut head = vec![0u8; 16];
    conn.read_exact(&mut head).await.ok()?;
    let total = padded(16 + u32_at(&head, 12) as usize) + u32_at(&head, 4) as usize;
    let mut rest = vec![0u8; total - 16];
    conn.read_exact(&mut rest).await.ok()?;
    head.extend_from_slice(&rest);
    Some(head)
}

/// The name in a `SetStaticHostname` call's body: its first string.
fn body_name(message: &[u8]) -> String {
    string_at(message, padded(16 + u32_at(message, 12) as usize))
}

/// The name in a `ResolveHostname` call's body: the string after the
/// interface's `i`.
fn lookup_name(message: &[u8]) -> String {
    string_at(message, padded(16 + u32_at(message, 12) as usize) + 4)
}

fn string_at(message: &[u8], at: usize) -> String {
    let len = u32_at(message, at) as usize;
    String::from_utf8(message[at + 4..at + 4 + len].to_vec()).unwrap()
}

/// Whether a call is to resolved: its destination, in its header fields.
fn to_resolved(message: &[u8]) -> bool {
    let fields = &message[16..16 + u32_at(message, 12) as usize];
    fields
        .windows(b"org.freedesktop.resolve1\0".len())
        .any(|w| w == b"org.freedesktop.resolve1\0")
}

/// A lookup's answer: a method return (an address follows in resolved's,
/// which no reader here needs) or an error.
fn lookup_answer(lookups: Lookups, name: &str, hello_serial: u32, call_serial: u32) -> Vec<u8> {
    let bare = name.strip_suffix(".local").unwrap_or(name);
    let answer = match lookups {
        Lookups::All => reply(2, 2, call_serial),
        Lookups::Taken(taken) if taken.contains(&bare) => reply(2, 2, call_serial),
        Lookups::Taken(_) => error(2, call_serial, NXDOMAIN),
        Lookups::Error(e) => error(2, call_serial, e),
        Lookups::HelloError(e) => return error(1, hello_serial, e),
        Lookups::Slow(_) => error(2, call_serial, NXDOMAIN),
    };
    [reply(2, 1, hello_serial), answer].concat()
}

async fn serve(
    mut conn: UnixStream,
    seen: Arc<Mutex<Seen>>,
    file: PathBuf,
    answer: Answer,
    lookups: Lookups,
) -> Option<()> {
    let auth = read_until(&mut conn, b"\r\n").await?;
    seen.lock().unwrap().auth.push(auth);
    if matches!(answer, Answer::Rejected) {
        conn.write_all(b"REJECTED EXTERNAL\r\n").await.ok()?;
        return None;
    }
    conn.write_all(b"OK 0123456789abcdef0123456789abcdef\r\n")
        .await
        .ok()?;
    let begin = read_until(&mut conn, b"\r\n").await?;
    assert_eq!(begin, b"BEGIN\r\n");
    let hello = read_message(&mut conn).await?;
    let call = read_message(&mut conn).await?;
    let (hello_serial, call_serial) = (u32_at(&hello, 8), u32_at(&call, 8));
    if to_resolved(&call) {
        let name = lookup_name(&call);
        {
            let mut seen = seen.lock().unwrap();
            seen.messages.push(hello.clone());
            seen.messages.push(call.clone());
            seen.lookups.push(name.clone());
        }
        if let Lookups::Slow(d) = lookups {
            tokio::time::sleep(d).await;
        }
        conn.write_all(&lookup_answer(lookups, &name, hello_serial, call_serial))
            .await
            .ok()?;
        let _ = conn.read(&mut [0u8; 1]).await;
        return Some(());
    }
    {
        let mut seen = seen.lock().unwrap();
        seen.messages.push(hello.clone());
        seen.messages.push(call.clone());
        seen.names.push(body_name(&call));
    }
    let out = match answer {
        Answer::Hangs => return None,
        Answer::Silent => {
            // Hold the connection open until the client gives up.
            let _ = conn.read(&mut [0u8; 1]).await;
            return None;
        }
        Answer::Huge => [&[b'l', 2, 1, 1][..], &le(1 << 20), &le(1), &le(8)].concat(),
        Answer::HelloError(name) => error(2, hello_serial, name),
        Answer::Flood => {
            conn.write_all(&reply(2, 1, hello_serial)).await.ok()?;
            let signals: Vec<u8> = (0..100u32).flat_map(signal).collect();
            let mut sent = 0;
            while sent < 300 * 1024 {
                for piece in signals.chunks(4093) {
                    conn.write_all(piece).await.ok()?;
                    sent += piece.len();
                }
                tokio::time::sleep(std::time::Duration::from_millis(1)).await;
            }
            let _ = conn.read(&mut [0u8; 1]).await;
            return None;
        }
        Answer::CallBeforeHello => [reply(2, 2, call_serial), reply(2, 1, hello_serial)].concat(),
        Answer::Renamed => {
            std::fs::write(&file, format!("{}\n", body_name(&call))).unwrap();
            [
                reply(2, 1, hello_serial),
                signal(2),
                reply(2, 3, 99),
                reply(2, 4, call_serial),
            ]
            .concat()
        }
        Answer::ReturnOnly => [reply(2, 1, hello_serial), reply(2, 2, call_serial)].concat(),
        Answer::Error(name) => [reply(2, 1, hello_serial), error(2, call_serial, name)].concat(),
        Answer::Rejected => unreachable!(),
    };
    conn.write_all(&out).await.ok()?;
    // Keep the connection until the client closes it.
    let _ = conn.read(&mut [0u8; 1]).await;
    Some(())
}
