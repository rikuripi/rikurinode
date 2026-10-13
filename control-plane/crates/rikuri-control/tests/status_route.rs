//! The status route through its real entry points: the router, and a real
//! loopback socket served by `serve`.

// A test crate: a failed unwrap is a failed test. clippy.toml's
// allow-unwrap-in-tests covers #[test] functions, not their helpers.
#![allow(clippy::unwrap_used)]

use axum::body::Body;
use axum::http::{Method, Request, StatusCode, header};
use http_body_util::BodyExt;
use rikuri_control::status::Started;
use rikuri_control::{router, serve};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};
use tower::ServiceExt;

async fn call(
    method: Method,
    path: &str,
) -> (StatusCode, axum::http::HeaderMap, serde_json::Value) {
    let request = Request::builder()
        .method(method)
        .uri(path)
        .body(Body::empty())
        .unwrap();
    let response = router(Started::now()).oneshot(request).await.unwrap();
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
async fn status_reports_unknown_as_unknown() {
    let (status, headers, body) = call(Method::GET, "/api/status").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers[header::CONTENT_TYPE], "application/json");
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
}

#[tokio::test]
async fn status_is_never_cached() {
    let (_, headers, _) = call(Method::GET, "/api/status").await;
    assert_eq!(headers[header::CACHE_CONTROL], "no-store");
}

#[tokio::test]
async fn an_unknown_path_is_not_found() {
    let (status, _, body) = call(Method::GET, "/api/nope").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert!(body.is_null());
}

#[tokio::test]
async fn status_answers_only_get() {
    for method in [Method::POST, Method::PUT, Method::DELETE] {
        let (status, _, _) = call(method.clone(), "/api/status").await;
        assert_eq!(status, StatusCode::METHOD_NOT_ALLOWED, "{method}");
    }
}

#[tokio::test]
async fn serves_over_a_real_loopback_socket_and_stops_on_request() {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let (stop, stopped) = tokio::sync::oneshot::channel::<()>();
    let server = tokio::spawn(serve(listener, Started::now(), async move {
        let _ = stopped.await;
    }));

    let mut stream = TcpStream::connect(addr).await.unwrap();
    stream
        .write_all(b"GET /api/status HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
        .await
        .unwrap();
    let mut raw = Vec::new();
    stream.read_to_end(&mut raw).await.unwrap();
    let response = String::from_utf8(raw).unwrap();
    assert!(response.starts_with("HTTP/1.1 200 OK\r\n"), "{response}");
    let body = response.split("\r\n\r\n").nth(1).unwrap();
    let json: serde_json::Value = serde_json::from_str(body).unwrap();
    assert_eq!(json["overall"], "unknown");

    stop.send(()).unwrap();
    server.await.unwrap().unwrap();
}
