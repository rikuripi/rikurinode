//! The node's certificate follows its LAN address without a restart (stage 1
//! change 5c.2): through the real TLS listener, a client trusting only the
//! node's CA reaches it by the new address, and no longer by the old one.
//! Record: docs/build-records/2026-11-10-5c2-names-and-mdns.md

#![allow(clippy::unwrap_used, clippy::expect_used)]

mod common;

use std::net::{IpAddr, Ipv4Addr};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use common::{Node, handshake_as};
use rikuri_control::address;
use rikuri_control::names::Names;
use rikuri_control::state::StateDir;

const FIRST: IpAddr = IpAddr::V4(Ipv4Addr::new(10, 0, 0, 7));
const SECOND: IpAddr = IpAddr::V4(Ipv4Addr::new(10, 0, 0, 8));

/// Waits, a bounded time, until a handshake as `name` succeeds; its certificate.
async fn reached_as(node: &Node, name: &str) -> Vec<u8> {
    for _ in 0..200 {
        if let Ok(der) = handshake_as(node, name).await {
            return der;
        }
        tokio::time::sleep(Duration::from_millis(10)).await;
    }
    panic!(
        "never reached as {name}: {:?}",
        handshake_as(node, name).await
    );
}

#[tokio::test]
async fn a_new_address_is_served_without_a_restart_and_the_old_one_leaves() {
    let node = Node::start().await;
    let at_start = handshake_as(&node, "localhost").await.unwrap();
    assert!(
        handshake_as(&node, "10.0.0.7").await.is_err(),
        "no address at boot"
    );

    let now = Arc::new(Mutex::new(Some(FIRST)));
    let probe = {
        let now = now.clone();
        move || *now.lock().unwrap()
    };
    let (stop, stopped) = tokio::sync::oneshot::channel::<()>();
    let follower = tokio::spawn(address::follow(
        StateDir::open(&node.scratch.0).unwrap(),
        Names::new(["rikuri01.local"]).unwrap(),
        node.booted.identity.current.clone(),
        probe,
        Duration::from_millis(10),
        async {
            let _ = stopped.await;
        },
    ));

    let first = reached_as(&node, "10.0.0.7").await;
    assert_ne!(first, at_start);
    assert_eq!(handshake_as(&node, "rikuri01.local").await.unwrap(), first);

    *now.lock().unwrap() = Some(SECOND);
    let second = reached_as(&node, "10.0.0.8").await;
    assert_ne!(second, first);
    assert!(
        handshake_as(&node, "10.0.0.7").await.is_err(),
        "the old address left"
    );

    stop.send(()).unwrap();
    tokio::time::timeout(Duration::from_secs(5), follower)
        .await
        .expect("follow ends when told to stop")
        .unwrap();
    node.stop().await;
}

#[tokio::test]
async fn the_same_address_issues_nothing_new() {
    let node = Node::start().await;
    let (stop, stopped) = tokio::sync::oneshot::channel::<()>();
    let follower = tokio::spawn(address::follow(
        StateDir::open(&node.scratch.0).unwrap(),
        Names::new(["rikuri01.local"]).unwrap(),
        node.booted.identity.current.clone(),
        || Some(FIRST),
        Duration::from_millis(10),
        async {
            let _ = stopped.await;
        },
    ));
    let first = reached_as(&node, "10.0.0.7").await;
    tokio::time::sleep(Duration::from_millis(100)).await;
    assert_eq!(
        handshake_as(&node, "10.0.0.7").await.unwrap(),
        first,
        "ten looks, one issue"
    );
    stop.send(()).unwrap();
    follower.await.unwrap();
    node.stop().await;
}
