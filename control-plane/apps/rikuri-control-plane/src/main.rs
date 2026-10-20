//! The control plane daemon. Serves the API over TLS (and, if configured, the
//! CA certificate and a redirect in the clear) until SIGTERM or SIGINT, and
//! offers one console subcommand, `rearm-claim`. Logs go to stderr (the
//! journal, under systemd), filtered by `RUST_LOG` (default `info`).
//!
//! Environment: `RIKURI_LISTEN` (HTTPS, default `127.0.0.1:8443`),
//! `RIKURI_HTTP_LISTEN` (plain, off unless set), `RIKURI_NAMES` (the node's
//! names, comma-separated; `localhost` is always one), `RIKURI_STATE_DIR`
//! (default `/var/lib/rikuri/control-plane`).

use std::error::Error;
use std::io::Write;
use std::process::ExitCode;

use rikuri_control::config::Config;
use rikuri_control::state::StateDir;
use rikuri_control::status::{self, Started};
use rikuri_control::{api_router, boot, claim, owner, plain_router, serve_plain, serve_tls};
use tokio::net::TcpListener;
use tokio::signal::unix::{SignalKind, signal};
use tracing::{error, info};
use tracing_subscriber::EnvFilter;
use tracing_subscriber::filter::LevelFilter;

const USAGE: &str = "usage: rikuri-control-plane            serve (the default)\n       rikuri-control-plane rearm-claim  arm a new claim code at the console\n";

fn main() -> ExitCode {
    let mut args = std::env::args().skip(1);
    match (args.next().as_deref(), args.next()) {
        (None, _) => daemon(),
        (Some("rearm-claim"), None) => rearm_claim(),
        (Some("rearm-claim"), Some(extra)) => {
            let _ = write!(
                std::io::stderr(),
                "rearm-claim takes no argument (got {extra:?})\n{USAGE}"
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
        let booted = boot::boot(&config, Started::now())?;
        info!(
            instance = %booted.node.instance_id,
            ca_fingerprint_sha256 = %booted.identity.ca_fingerprint,
            ca_created = booted.identity.ca_created,
            server_certificate_issued = booted.identity.server_issued,
            "node identity: compare the fingerprint with the one the browser shows"
        );
        if let Some(code) = &booted.armed {
            // The one place the code is written in clear: it is how the owner
            // learns it, from the console (the journal until the banner unit
            // of stage 1 change 5 exists). Single-use, 24 hours.
            info!(
                claim_code = %code.formatted(),
                "claim code armed: enter it on the setup page within 24 hours; \
                 twenty wrong tries retire it, and only `rikuri-control-plane rearm-claim` arms another"
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
