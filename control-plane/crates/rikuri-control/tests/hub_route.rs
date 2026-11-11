//! 5c.4a: the node's UUID and the SetupHub through the real entry points: a
//! TLS client against a real loopback socket, the claim that gives the node
//! its UUID, and `GET /api/hub` for the signed-in owner only.
//! Record: docs/build-records/2026-11-11-5c4a-uuid-and-setup-hub.md

#![allow(clippy::unwrap_used, clippy::expect_used)]

mod common;

use common::{Node, PASSWORD, Req, claim, hostname_file, ok};
use rikuri_control::node_id;
use serde_json::json;

fn uuid_on_disk(node: &Node) -> Option<String> {
    let raw = std::fs::read(node.scratch.0.join(node_id::FILE)).ok()?;
    let file: serde_json::Value = serde_json::from_slice(&raw).unwrap();
    Some(file["uuid"].as_str().unwrap().to_owned())
}

fn set_hostname(node: &Node, name: Option<&str>) {
    let path = hostname_file(&node.scratch);
    match name {
        Some(name) => std::fs::write(path, format!("{name}\n")).unwrap(),
        None => {
            let _ = std::fs::remove_file(path);
        }
    }
}

fn states(hub: &serde_json::Value) -> Vec<(String, String)> {
    hub["steps"]
        .as_array()
        .unwrap()
        .iter()
        .map(|s| {
            (
                s["step"].as_str().unwrap().to_owned(),
                s["state"].as_str().unwrap().to_owned(),
            )
        })
        .collect()
}

fn pairs(list: &[(&str, &str)]) -> Vec<(String, String)> {
    list.iter()
        .map(|(a, b)| ((*a).to_owned(), (*b).to_owned()))
        .collect()
}

#[tokio::test]
async fn the_claim_gives_the_node_its_uuid_once() {
    let node = Node::start().await;
    assert_eq!(
        uuid_on_disk(&node),
        None,
        "an unclaimed node has no UUID yet"
    );
    let claimed = claim(&node, PASSWORD).await;
    assert_eq!(claimed.status, 201, "{}", claimed.body);
    let uuid = uuid_on_disk(&node).expect("the claim writes the UUID");
    assert!(node_id::is_v4(&uuid), "{uuid}");
    let node = node.restart().await;
    assert_eq!(
        uuid_on_disk(&node).as_deref(),
        Some(uuid.as_str()),
        "kept across a restart"
    );
    node.stop().await;
}

#[tokio::test]
async fn the_hub_is_for_the_signed_in_owner_only() {
    let node = Node::start().await;
    let before = ok(&node, Req::get("/api/hub")).await;
    assert_eq!(before.status, 401, "{}", before.body);
    assert_eq!(before.body, r#"{"error":"sign-in required"}"#);
    claim(&node, PASSWORD).await;
    let anonymous = ok(&node, Req::get("/api/hub")).await;
    assert_eq!(anonymous.status, 401, "{}", anonymous.body);
    let forged = ok(&node, Req::get("/api/hub").cookie(&"0".repeat(64))).await;
    assert_eq!(forged.status, 401, "{}", forged.body);
    let posted = ok(&node, Req::post("/api/hub", json!({}))).await;
    assert_eq!(posted.status, 405, "{}", posted.body);
    node.stop().await;
}

#[tokio::test]
async fn the_hub_lists_every_step_from_the_nodes_real_state() {
    let node = Node::start().await;
    let session = claim(&node, PASSWORD).await.session_cookie();
    let uuid = uuid_on_disk(&node).unwrap();

    set_hostname(&node, Some("rikurisetup"));
    let hub = ok(&node, Req::get("/api/hub").cookie(&session)).await;
    assert_eq!(hub.status, 200, "{}", hub.body);
    assert_eq!(hub.header("cache-control"), Some("no-store"));
    let hub = hub.json();
    assert_eq!(hub["node_id"], uuid.as_str());
    assert_eq!(
        states(&hub),
        pairs(&[
            ("connection", "done"),
            ("owner", "done"),
            ("name", "next"),
            ("bitcoin", "later"),
            ("lightning", "later"),
            ("backup", "later"),
        ])
    );

    // Read again on every request: no flag is kept.
    set_hostname(&node, Some("rikuri01"));
    let named = ok(&node, Req::get("/api/hub").cookie(&session))
        .await
        .json();
    assert_eq!(states(&named)[2], pairs(&[("name", "done")])[0]);
    set_hostname(&node, None);
    let unread = ok(&node, Req::get("/api/hub").cookie(&session))
        .await
        .json();
    assert_eq!(states(&unread)[2], pairs(&[("name", "unknown")])[0]);
    node.stop().await;
}

#[tokio::test]
async fn a_claimed_node_without_its_uuid_gets_one_on_the_next_read() {
    // A crash between the claim and the UUID's write.
    let node = Node::start().await;
    let session = claim(&node, PASSWORD).await.session_cookie();
    std::fs::remove_file(node.scratch.0.join(node_id::FILE)).unwrap();
    let hub = ok(&node, Req::get("/api/hub").cookie(&session)).await;
    assert_eq!(hub.status, 200, "{}", hub.body);
    let made = uuid_on_disk(&node).expect("made on the read");
    assert_eq!(hub.json()["node_id"], made.as_str());
    let again = ok(&node, Req::get("/api/hub").cookie(&session))
        .await
        .json();
    assert_eq!(again["node_id"], made.as_str(), "and then kept");
    node.stop().await;
}

#[tokio::test]
async fn a_uuid_file_that_cannot_be_read_is_an_error_and_is_never_replaced() {
    let node = Node::start().await;
    let session = claim(&node, PASSWORD).await.session_cookie();
    let path = node.scratch.0.join(node_id::FILE);
    std::fs::write(&path, br#"{"uuid":"not a uuid","created_unix":1}"#).unwrap();
    let hub = ok(&node, Req::get("/api/hub").cookie(&session)).await;
    assert_eq!(hub.status, 500, "{}", hub.body);
    assert_eq!(hub.body, r#"{"error":"internal error"}"#);
    assert_eq!(
        std::fs::read(&path).unwrap(),
        br#"{"uuid":"not a uuid","created_unix":1}"#,
        "the node's identity is never quietly replaced"
    );
    node.stop().await;
}
