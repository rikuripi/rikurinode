//! The control plane daemon. B0.1: serves the status route on loopback and
//! stops cleanly on SIGTERM or SIGINT. Logs go to stderr (the journal, under
//! systemd), filtered by `RUST_LOG` (default `info`).

use std::error::Error;
use std::process::ExitCode;

use rikuri_control::listen;
use rikuri_control::status::Started;
use tokio::net::TcpListener;
use tokio::signal::unix::{SignalKind, signal};
use tracing::{error, info};
use tracing_subscriber::EnvFilter;
use tracing_subscriber::filter::LevelFilter;

fn main() -> ExitCode {
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
    let spec = match std::env::var_os(listen::ENV) {
        None => listen::DEFAULT.to_owned(),
        Some(value) => value
            .into_string()
            .map_err(|_| format!("{} is not valid UTF-8", listen::ENV))?,
    };
    let addr = listen::parse(&spec)?;
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()?;
    runtime.block_on(async {
        let mut term = signal(SignalKind::terminate())?;
        let mut int = signal(SignalKind::interrupt())?;
        let listener = TcpListener::bind(addr).await?;
        let bound = listener.local_addr()?;
        info!(
            %bound,
            version = env!("CARGO_PKG_VERSION"),
            "control plane listening: plain HTTP on loopback until B0.2 brings TLS and sign-in"
        );
        let shutdown = async move {
            tokio::select! {
                _ = term.recv() => info!("SIGTERM received: stopping"),
                _ = int.recv() => info!("SIGINT received: stopping"),
            }
        };
        rikuri_control::serve(listener, Started::now(), shutdown).await
    })?;
    Ok(())
}
