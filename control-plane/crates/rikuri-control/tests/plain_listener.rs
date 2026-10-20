//! The plain listener: the CA certificate for a browser to install, and a
//! redirect for everything else. No API route exists on it.

#![allow(clippy::unwrap_used, clippy::expect_used)]

mod common;

use common::{Node, Req, plain};

#[tokio::test]
async fn the_ca_certificate_is_served_as_a_download() {
    let node = Node::start().await;
    let reply = plain(&node, Req::get("/ca.crt")).await;
    assert_eq!(reply.status, 200, "{}", reply.body);
    assert_eq!(
        reply.header("content-type"),
        Some("application/x-x509-ca-cert")
    );
    assert!(
        reply
            .header("content-disposition")
            .unwrap()
            .contains("rikuri-node-ca.crt")
    );
    assert_eq!(reply.body, node.booted.identity.ca_pem);
    assert!(reply.body.starts_with("-----BEGIN CERTIFICATE-----\n"));
    node.stop().await;
}

#[tokio::test]
async fn everything_else_is_a_redirect_to_https_never_an_api_response() {
    let node = Node::start().await;
    let port = node.https.port();
    let status = plain(&node, Req::get("/api/status")).await;
    assert_eq!(status.status, 308, "{}", status.body);
    assert_eq!(
        status.header("location"),
        Some(format!("https://localhost:{port}/api/status").as_str())
    );
    assert!(status.body.is_empty());

    let claim = plain(
        &node,
        Req::post(
            "/api/claim",
            serde_json::json!({ "code": node.claim_code(), "password": common::PASSWORD }),
        ),
    )
    .await;
    assert_eq!(
        claim.status, 308,
        "a claim over plain HTTP is never judged: {}",
        claim.body
    );
    let setup = common::ok(&node, Req::get("/api/setup")).await.json();
    assert_eq!(setup["claimed"], false);

    let with_query = plain(
        &node,
        Req::get("/setup?step=2").header("Host", "rikuri01.local:80"),
    )
    .await;
    assert_eq!(
        with_query.header("location"),
        Some(format!("https://rikuri01.local:{port}/setup?step=2").as_str())
    );
    let v6 = plain(&node, Req::get("/").header("Host", "[::1]:80")).await;
    assert_eq!(
        v6.header("location"),
        Some(format!("https://[::1]:{port}/").as_str())
    );
    node.stop().await;
}

#[tokio::test]
async fn a_host_that_is_not_this_node_is_refused_in_the_clear_too() {
    let node = Node::start().await;
    let reply = plain(&node, Req::get("/ca.crt").header("Host", "evil.example")).await;
    assert_eq!(reply.status, 421, "{}", reply.body);
    node.stop().await;
}
