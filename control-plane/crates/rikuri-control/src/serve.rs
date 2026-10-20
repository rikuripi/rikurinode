//! The accept loops: TLS for the API, plain for the certificate and the
//! redirect. Each connection is served by hyper over HTTP/1.1 with the peer's
//! address attached to its requests; a shutdown stops accepting, then lets the
//! connections in flight finish within a bound. (axum's own `serve` cannot do
//! TLS; this is the loop its TLS example shows.)

use std::future::Future;
use std::io;
use std::net::SocketAddr;
use std::pin::pin;
use std::sync::Arc;
use std::time::Duration;

use axum::Router;
use hyper::body::Incoming;
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper_util::rt::{TokioIo, TokioTimer};
use hyper_util::server::graceful::{GracefulShutdown, Watcher};
use rustls::ServerConfig;
use tokio::net::{TcpListener, TcpStream};
use tokio_rustls::TlsAcceptor;
use tower::ServiceExt;
use tracing::{debug, info, warn};

use crate::http::Peer;
use crate::trust;

/// A TLS handshake that takes longer than this is dropped.
pub const HANDSHAKE_TIMEOUT: Duration = Duration::from_secs(10);
/// A client that has not sent its request headers by then is dropped.
pub const HEADER_TIMEOUT: Duration = Duration::from_secs(10);
/// How long connections in flight get to finish after a shutdown.
pub const DRAIN_TIMEOUT: Duration = Duration::from_secs(10);

/// Serves the API over TLS on `listener` until `shutdown` completes.
pub async fn serve_tls(
    listener: TcpListener,
    tls: Arc<ServerConfig>,
    router: Router,
    shutdown: impl Future<Output = ()>,
) -> io::Result<()> {
    let acceptor = TlsAcceptor::from(tls);
    accept_loop(listener, shutdown, move |stream, peer, watcher| {
        let acceptor = acceptor.clone();
        let router = router.clone();
        async move {
            let tls = match tokio::time::timeout(HANDSHAKE_TIMEOUT, acceptor.accept(stream)).await {
                Ok(Ok(tls)) => tls,
                Ok(Err(e)) => {
                    debug!(peer = %trust::classify(peer.ip()), error = %e, "TLS handshake failed");
                    return;
                }
                Err(_) => {
                    debug!(peer = %trust::classify(peer.ip()), "TLS handshake timed out");
                    return;
                }
            };
            serve_connection(TokioIo::new(tls), peer, router, watcher).await;
        }
    })
    .await
}

/// Serves `router` in the clear on `listener` until `shutdown` completes: the
/// plain router only, which has no API route.
pub async fn serve_plain(
    listener: TcpListener,
    router: Router,
    shutdown: impl Future<Output = ()>,
) -> io::Result<()> {
    accept_loop(listener, shutdown, move |stream, peer, watcher| {
        let router = router.clone();
        async move { serve_connection(TokioIo::new(stream), peer, router, watcher).await }
    })
    .await
}

async fn accept_loop<F, Fut>(
    listener: TcpListener,
    shutdown: impl Future<Output = ()>,
    mut connect: F,
) -> io::Result<()>
where
    F: FnMut(TcpStream, SocketAddr, Watcher) -> Fut,
    Fut: Future<Output = ()> + Send + 'static,
{
    let graceful = GracefulShutdown::new();
    let mut shutdown = pin!(shutdown);
    loop {
        tokio::select! {
            accepted = listener.accept() => match accepted {
                Ok((stream, peer)) => {
                    tokio::spawn(connect(stream, peer, graceful.watcher()));
                }
                Err(e) => {
                    // Out of descriptors, or a reset before accept: say so and
                    // keep serving rather than spin.
                    warn!(error = %e, "accept failed");
                    tokio::time::sleep(Duration::from_millis(50)).await;
                }
            },
            () = &mut shutdown => break,
        }
    }
    info!("no longer accepting connections; letting those in flight finish");
    tokio::select! {
        () = graceful.shutdown() => {}
        () = tokio::time::sleep(DRAIN_TIMEOUT) => warn!("connections still open after {DRAIN_TIMEOUT:?}: closing"),
    }
    Ok(())
}

async fn serve_connection<I>(io: I, peer: SocketAddr, router: Router, watcher: Watcher)
where
    I: hyper::rt::Read + hyper::rt::Write + Unpin + Send + 'static,
{
    let service = service_fn(move |mut req: hyper::Request<Incoming>| {
        req.extensions_mut().insert(Peer(peer));
        let router = router.clone();
        async move { router.oneshot(req).await }
    });
    // A timeout needs a timer, or hyper panics on the first connection.
    let connection = http1::Builder::new()
        .timer(TokioTimer::new())
        .header_read_timeout(HEADER_TIMEOUT)
        .serve_connection(io, service);
    if let Err(e) = watcher.watch(connection).await {
        debug!(peer = %trust::classify(peer.ip()), error = %e, "connection ended with an error");
    }
}
