//! The HTTP surface. B0.1: one route, `GET /api/status`, served over plain
//! HTTP on loopback only (see `listen`). TLS, sign-in and the per-route
//! policy come with B0.2 and B0.3.

use axum::extract::State;
use axum::http::header;
use axum::response::{AppendHeaders, IntoResponse};
use axum::routing::get;
use axum::{Json, Router};
use tokio::net::TcpListener;

use crate::status::{self, Started};

/// The route table, with the start moment as its state.
pub fn router(started: Started) -> Router {
    Router::new()
        .route("/api/status", get(status_handler))
        .with_state(started)
}

async fn status_handler(State(started): State<Started>) -> impl IntoResponse {
    // A status is a measurement with its time: never served from a cache.
    (
        AppendHeaders([(header::CACHE_CONTROL, "no-store")]),
        Json(status::report(started)),
    )
}

/// Serves the router on `listener` until `shutdown` completes, then lets the
/// connections in flight finish.
pub async fn serve(
    listener: TcpListener,
    started: Started,
    shutdown: impl Future<Output = ()> + Send + 'static,
) -> std::io::Result<()> {
    axum::serve(listener, router(started))
        .with_graceful_shutdown(shutdown)
        .await
}
