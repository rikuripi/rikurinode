//! The status route through the router: open to a loopback peer, a session
//! for any other; the report unchanged since B0.1 (every component unknown).

#![allow(clippy::unwrap_used, clippy::expect_used)]

mod common;

use axum::body::Body;
use axum::http::{Method, Request, StatusCode, header};
use common::{Scratch, boot_only};
use http_body_util::BodyExt;
use rikuri_control::{Peer, api_router};
use tower::ServiceExt;

async fn call(
    method: Method,
    path: &str,
    peer: &str,
    cookie: Option<&str>,
) -> (StatusCode, axum::http::HeaderMap, serde_json::Value) {
    call_from(method, path, peer, cookie, None).await
}

async fn call_from(
    method: Method,
    path: &str,
    peer: &str,
    cookie: Option<&str>,
    origin: Option<&str>,
) -> (StatusCode, axum::http::HeaderMap, serde_json::Value) {
    let scratch = Scratch::new();
    let booted = boot_only(&scratch);
    let mut request = Request::builder()
        .method(method)
        .uri(path)
        .header(header::HOST, "localhost");
    if let Some(cookie) = cookie {
        request = request.header(header::COOKIE, cookie);
    }
    if let Some(origin) = origin {
        request = request.header(header::ORIGIN, origin);
    }
    let mut request = request.body(Body::empty()).unwrap();
    request.extensions_mut().insert(Peer(peer.parse().unwrap()));
    let response = api_router(booted.app).oneshot(request).await.unwrap();
    let (parts, body) = response.into_parts();
    let bytes = body.collect().await.unwrap().to_bytes();
    let json = if bytes.is_empty() {
        serde_json::Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
    };
    (parts.status, parts.headers, json)
}

#[tokio::test]
async fn a_loopback_peer_reads_the_status_without_a_session() {
    let (status, headers, body) = call(Method::GET, "/api/status", "127.0.0.1:50000", None).await;
    assert_eq!(status, StatusCode::OK, "{body}");
    assert_eq!(headers[header::CONTENT_TYPE], "application/json");
    assert_eq!(headers[header::CACHE_CONTROL], "no-store");
    assert_eq!(body["overall"], "unknown");
    let components = body["components"].as_object().unwrap();
    assert_eq!(components.len(), 4, "{body}");
    for (name, component) in components {
        assert_eq!(component["state"], "unknown", "{name}");
        assert!(component["checked_unix"].is_null(), "{name}: {component}");
        assert!(
            component["detail"]
                .as_str()
                .unwrap()
                .starts_with("not probed"),
            "{name}"
        );
    }
    assert_eq!(body["control_plane"]["version"], env!("CARGO_PKG_VERSION"));
    assert!(body["control_plane"]["pid"].as_u64().unwrap() > 0);
    assert!(body["observed_unix"].as_u64().unwrap() > 0);
    let (status, _, _) = call(Method::GET, "/api/status", "[::1]:50000", None).await;
    assert_eq!(status, StatusCode::OK);
}

#[tokio::test]
async fn any_other_peer_needs_a_session() {
    for peer in ["192.168.1.9:50000", "[fe80::1]:50000", "8.8.8.8:50000"] {
        let (status, _, body) = call(Method::GET, "/api/status", peer, None).await;
        assert_eq!(status, StatusCode::UNAUTHORIZED, "{peer}: {body}");
        assert_eq!(body["error"], "sign-in required");
        let forged = format!("rikuri_session={}", "a".repeat(64));
        let (status, _, _) = call(Method::GET, "/api/status", peer, Some(&forged)).await;
        assert_eq!(status, StatusCode::UNAUTHORIZED, "{peer}");
    }
}

#[tokio::test]
async fn an_unknown_path_is_not_found_and_status_answers_only_get() {
    let (status, _, body) = call(Method::GET, "/api/nope", "127.0.0.1:1", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert!(body.is_null());
    for method in [Method::POST, Method::PUT, Method::DELETE] {
        // Without an Origin the origin check refuses first; with the node's
        // own Origin the route itself answers.
        let (status, _, _) = call(method.clone(), "/api/status", "127.0.0.1:1", None).await;
        assert_eq!(status, StatusCode::FORBIDDEN, "{method} without Origin");
        let (status, _, _) = call_from(
            method.clone(),
            "/api/status",
            "127.0.0.1:1",
            None,
            Some("https://localhost"),
        )
        .await;
        assert_eq!(
            status,
            StatusCode::METHOD_NOT_ALLOWED,
            "{method} with the node's Origin"
        );
    }
}
