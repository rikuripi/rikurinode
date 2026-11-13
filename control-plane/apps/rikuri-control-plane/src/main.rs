//! The control plane daemon. Serves the API over TLS (and, if configured, the
//! CA certificate and a redirect in the clear) until SIGTERM or SIGINT, and
//! offers two console subcommands: `rearm-claim`, and `claim-screen`, the
//! claim screen on `tty2` (stage 1 change 5c.1). Logs go to stderr (the
//! journal, under systemd), filtered by `RUST_LOG` (default `info`).
//!
//! Environment: `RIKURI_LISTEN` (HTTPS, default `127.0.0.1:8443`),
//! `RIKURI_HTTP_LISTEN` (plain, off unless set), `RIKURI_NAMES` (the node's
//! extra names, comma-separated; `localhost` is always one, and the node's own
//! `<hostname>.local` is read from `/etc/hostname`), `RIKURI_STATE_DIR`
//! (default `/var/lib/rikuri/control-plane`).

use std::error::Error;
use std::io::{BufRead, Write};
use std::process::ExitCode;

use rikuri_control::config::Config;
use rikuri_control::state::StateDir;
use rikuri_control::status::{self, Started};
use rikuri_control::{
    address, api_router, boot, claim, console, owner, plain_router, serve_plain, serve_tls,
};
use tokio::net::TcpListener;
use tokio::signal::unix::{SignalKind, signal};
use tracing::{error, info};
use tracing_subscriber::EnvFilter;
use tracing_subscriber::filter::LevelFilter;

const USAGE: &str = "usage: rikuri-control-plane             serve (the default)\n       rikuri-control-plane rearm-claim   arm a new claim code at the console\n       rikuri-control-plane claim-screen  the claim screen (its unit runs it on tty2)\n";

fn main() -> ExitCode {
    let mut args = std::env::args().skip(1);
    match (args.next().as_deref(), args.next()) {
        (None, _) => daemon(),
        (Some("rearm-claim"), None) => rearm_claim(),
        (Some("claim-screen"), None) => claim_screen(),
        (Some(sub @ ("rearm-claim" | "claim-screen")), Some(extra)) => {
            let _ = write!(
                std::io::stderr(),
                "{sub} takes no argument (got {extra:?})\n{USAGE}"
            );
            ExitCode::from(2)
        }
        (Some(other), _) => {
            let _ = write!(std::io::stderr(), "unknown argument {other:?}\n{USAGE}");
            ExitCode::from(2)
        }
    }
}

fn daemon() -> ExitCode {
    init_logging();
    match run() {
        Ok(()) => {
            info!("control plane stopped");
            ExitCode::SUCCESS
        }
        Err(e) => {
            error!(error = %e, "control plane cannot continue");
            ExitCode::FAILURE
        }
    }
}

fn init_logging() {
    let filter = EnvFilter::builder()
        .with_default_directive(LevelFilter::INFO.into())
        .from_env();
    let (filter, problem) = match filter {
        Ok(filter) => (filter, None),
        Err(e) => (EnvFilter::new("info"), Some(e)),
    };
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_ansi(false)
        .with_writer(std::io::stderr)
        .init();
    if let Some(e) = problem {
        error!(error = %e, "RUST_LOG is not a valid filter; logging at info");
    }
}

fn run() -> Result<(), Box<dyn Error>> {
    let config = Config::from_env()?;
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()?;
    runtime.block_on(async {
        let mut term = signal(SignalKind::terminate())?;
        let mut int = signal(SignalKind::interrupt())?;
        let booted = boot::boot(&config, Started::now(), console::lan_address())?;
        info!(
            instance = %booted.node.instance_id,
            ca_fingerprint_sha256 = %booted.identity.ca_fingerprint,
            ca_created = booted.identity.ca_created,
            server_certificate_issued = booted.identity.server_issued,
            server_certificate_names = ?booted.identity.server_meta.names,
            "node identity: compare the fingerprint with the one the browser shows"
        );
        if booted.armed.is_some() {
            // Never the code itself: the journal is kept on disk. The owner
            // gets a code to use from the claim screen at the node, which
            // replaces this one (stage 1 change 5c.1).
            info!(
                "claim code armed and not shown: press Enter on the claim screen at the node \
                 (Ctrl+Alt+F2) for a code to use; it replaces this one"
            );
        }
        let https = TcpListener::bind(config.https).await?;
        info!(bound = %https.local_addr()?, version = env!("CARGO_PKG_VERSION"), "HTTPS listener: the API");
        let plain = match config.http {
            Some(addr) => {
                let listener = TcpListener::bind(addr).await?;
                info!(bound = %listener.local_addr()?, "plain listener: the CA certificate and a redirect, nothing else");
                Some(listener)
            }
            None => None,
        };

        let (stop, stopped) = tokio::sync::watch::channel(false);
        tokio::spawn(async move {
            tokio::select! {
                _ = term.recv() => info!("SIGTERM received: stopping"),
                _ = int.recv() => info!("SIGINT received: stopping"),
            }
            let _ = stop.send(true);
        });
        let wait = |mut rx: tokio::sync::watch::Receiver<bool>| async move {
            let _ = rx.changed().await;
        };

        // The certificate follows the node's address (5c.2) and its name
        // (5c.4b-1).
        tokio::spawn(address::follow(
            booted.follower.clone(),
            console::lan_address,
            address::EVERY,
            wait(stopped.clone()),
        ));
        let api = serve_tls(https, booted.identity.config.clone(), api_router(booted.app.clone()), wait(stopped.clone()));
        match plain {
            Some(listener) => {
                let redirect = serve_plain(listener, plain_router(booted.app.clone()), wait(stopped.clone()));
                tokio::try_join!(api, redirect)?;
            }
            None => api.await?,
        }
        Ok::<(), Box<dyn Error>>(())
    })?;
    Ok(())
}

/// The console subcommand: arms a new claim code on an unclaimed node and
/// prints it. Refused once the node is claimed: the owner signs in with the
/// password, and recovery from a lost password is a later, owner-decided path.
fn rearm_claim() -> ExitCode {
    match rearm() {
        Ok(code) => {
            let mut out = std::io::stdout();
            let _ = writeln!(out, "claim code: {}", code.formatted());
            let _ = writeln!(
                out,
                "enter it on the setup page within 24 hours; twenty wrong tries retire it"
            );
            ExitCode::SUCCESS
        }
        Err(e) => {
            let _ = writeln!(std::io::stderr(), "rearm-claim: {e}");
            ExitCode::FAILURE
        }
    }
}

fn rearm() -> Result<claim::Code, Box<dyn Error>> {
    let config = Config::from_env()?;
    let dir = StateDir::open(&config.state_dir)?;
    if owner::exists(&dir) {
        return Err("the node is claimed: a claim code cannot be re-armed".into());
    }
    Ok(claim::arm(&dir, status::unix_now().unwrap_or(0))?)
}

/// Clears the console and puts the cursor at its top left.
const CLEAR: &str = "\x1b[H\x1b[2J";

/// The claim screen: draws the node's address, the CA fingerprint and the
/// claim state, then waits for a line. Enter (any line) arms a new code on an
/// unclaimed node and draws again. It ends when its input ends; its unit
/// starts it again. Never prints a code it did not arm itself.
fn claim_screen() -> ExitCode {
    let dir = match Config::from_env()
        .map_err(|e| e.to_string())
        .and_then(|config| StateDir::open(&config.state_dir).map_err(|e| e.to_string()))
    {
        Ok(dir) => dir,
        Err(e) => {
            let _ = writeln!(std::io::stderr(), "claim-screen: {e}");
            return ExitCode::FAILURE;
        }
    };
    let stdin = std::io::stdin();
    let mut shown = console::initial(&dir);
    loop {
        let screen = console::render(
            console::lan_address(),
            &console::ca_fingerprint(&dir),
            &shown,
        );
        let mut out = std::io::stdout().lock();
        if write!(out, "{CLEAR}{screen}")
            .and_then(|()| out.flush())
            .is_err()
        {
            return ExitCode::FAILURE;
        }
        drop(out);
        let mut line = String::new();
        match stdin.lock().read_line(&mut line) {
            Ok(0) => return ExitCode::SUCCESS,
            Ok(_) => shown = console::press_enter(&dir, status::unix_now().unwrap_or(0)),
            Err(e) => {
                let _ = writeln!(std::io::stderr(), "claim-screen: reading the console: {e}");
                return ExitCode::FAILURE;
            }
        }
    }
}
