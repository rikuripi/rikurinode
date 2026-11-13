//! A stand-in system bus with hostnamed behind it (5c.4b-1), on a Unix socket
//! of the test's own: it takes SASL EXTERNAL, answers `Hello`, and answers the
//! rename as told, writing the hostname file as hostnamed would. It reads the
//! client's messages by their fixed header alone (lengths at fixed offsets),
//! so it does not lean on the client's own reader; the unit tests in
//! `hostname.rs` pin the client's bytes. Its replies are written out by hand.

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
}

/// What the stand-in received.
#[derive(Clone, Debug, Default)]
pub struct Seen {
    pub auth: Vec<Vec<u8>>,
    pub messages: Vec<Vec<u8>>,
    pub names: Vec<String>,
}

pub struct Bus {
    pub path: PathBuf,
    seen: Arc<Mutex<Seen>>,
    task: JoinHandle<()>,
}

impl Bus {
    pub fn start(path: PathBuf, hostname_file: PathBuf, answer: Answer) -> Bus {
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
                        let _ = serve(conn, seen, file, answer).await;
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
    let at = padded(16 + u32_at(message, 12) as usize);
    let len = u32_at(message, at) as usize;
    String::from_utf8(message[at + 4..at + 4 + len].to_vec()).unwrap()
}

async fn serve(
    mut conn: UnixStream,
    seen: Arc<Mutex<Seen>>,
    file: PathBuf,
    answer: Answer,
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
    {
        let mut seen = seen.lock().unwrap();
        seen.messages.push(hello.clone());
        seen.messages.push(call.clone());
        seen.names.push(body_name(&call));
    }
    let (hello_serial, call_serial) = (u32_at(&hello, 8), u32_at(&call, 8));
    let out = match answer {
        Answer::Hangs => return None,
        Answer::Silent => {
            // Hold the connection open until the client gives up.
            let _ = conn.read(&mut [0u8; 1]).await;
            return None;
        }
        Answer::Huge => [&[b'l', 2, 1, 1][..], &le(1 << 20), &le(1), &le(8)].concat(),
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
