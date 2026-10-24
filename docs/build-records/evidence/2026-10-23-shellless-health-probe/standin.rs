//! Stand-in service and its probe for the shell-less health experiment
//! (ADR 0013, criterion 3). Evidence, not product code.
//! Record: docs/build-records/2026-10-23-shellless-health-probe.md
//!
//! `standin serve`: after STANDIN_DELAY_S seconds (default 5), answers each
//! connection on 127.0.0.1:8080 with "ok\n", or "sick\n" if STANDIN_STATE=sick.
//! `standin probe`: exits 0 only if the answer is "ok\n", within 2 s.

use std::env;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::process::ExitCode;
use std::thread::sleep;
use std::time::Duration;

const ADDR: &str = "127.0.0.1:8080";
const LIMIT: Duration = Duration::from_secs(2);

fn answer(state: Option<&str>) -> &'static [u8] {
    if state == Some("sick") {
        b"sick\n"
    } else {
        b"ok\n"
    }
}

fn healthy(reply: &[u8]) -> bool {
    reply == b"ok\n"
}

fn serve() -> ExitCode {
    let delay = env::var("STANDIN_DELAY_S").ok().and_then(|s| s.parse().ok()).unwrap_or(5);
    eprintln!("standin: starting, ready in {delay} s");
    sleep(Duration::from_secs(delay));
    let state = env::var("STANDIN_STATE").ok();
    let reply = answer(state.as_deref());
    let listener = match TcpListener::bind(ADDR) {
        Ok(l) => l,
        Err(e) => {
            eprintln!("standin: bind {ADDR}: {e}");
            return ExitCode::FAILURE;
        }
    };
    eprintln!("standin: listening on {ADDR}, answering {:?}", String::from_utf8_lossy(reply).trim());
    for conn in listener.incoming().flatten() {
        let mut conn = conn;
        let _ = conn.write_all(reply);
    }
    ExitCode::SUCCESS
}

fn probe() -> ExitCode {
    let addr: SocketAddr = ADDR.parse().expect("fixed address");
    let mut buf = Vec::new();
    let read = TcpStream::connect_timeout(&addr, LIMIT).and_then(|s| {
        s.set_read_timeout(Some(LIMIT))?;
        s.take(16).read_to_end(&mut buf)
    });
    match read {
        Ok(_) if healthy(&buf) => ExitCode::SUCCESS,
        Ok(_) => {
            eprintln!("standin probe: unhealthy answer {:?}", String::from_utf8_lossy(&buf));
            ExitCode::FAILURE
        }
        Err(e) => {
            eprintln!("standin probe: {e}");
            ExitCode::FAILURE
        }
    }
}

fn main() -> ExitCode {
    match env::args().nth(1).as_deref() {
        Some("serve") => serve(),
        Some("probe") => probe(),
        _ => {
            eprintln!("usage: standin serve|probe");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_ok_is_healthy() {
        assert!(healthy(b"ok\n"));
        for bad in [&b""[..], b"ok", b"sick\n", b"ok\nok\n", b"OK\n"] {
            assert!(!healthy(bad), "{bad:?}");
        }
    }

    #[test]
    fn sick_state_answers_sick() {
        assert_eq!(answer(Some("sick")), b"sick\n");
        assert_eq!(answer(None), b"ok\n");
        assert!(!healthy(answer(Some("sick"))));
    }
}
