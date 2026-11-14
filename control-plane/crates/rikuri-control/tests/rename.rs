//! 5c.4b-1: renaming the node, through the real entry points: the D-Bus
//! client against a stand-in bus on a real Unix socket, `PUT /api/node/name`
//! over TLS on a real loopback socket, and the follower's look. After a
//! rename the node answers to the new name only, in its certificate and in
//! its `Host` and `Origin` checks, at once and after a restart.
//! Record: docs/build-records/2026-11-13-5c4b1-rename-engine.md
//!
//! 5c.4b-2: the suggested free name, and the rename's own refusals: during
//! setup only, and never to a name something on the network answers.
//! Record: docs/build-records/2026-11-13-5c4b2-naming-page.md

#![allow(clippy::unwrap_used, clippy::expect_used)]

mod common;

use std::time::Duration;

use common::bus::{Answer, Bus, Lookups, Seen};
use common::{
    Node, PASSWORD, Reply, Req, Scratch, bus_socket, claim, handshake_as, hostname_file, ok,
};
use rikuri_control::address;
use rikuri_control::hostname::{self, BusError, NodeName};
use serde_json::json;

const ACCESS_DENIED: &str = "org.freedesktop.DBus.Error.AccessDenied";
const INTERACTIVE: &str = "org.freedesktop.DBus.Error.InteractiveAuthorizationRequired";
const INVALID_ARGS: &str = "org.freedesktop.DBus.Error.InvalidArgs";

fn name(s: &str) -> NodeName {
    NodeName::parse(s).unwrap()
}

// ---- the client ---------------------------------------------------------------

/// One rename to `rikuri02` as uid 1000 through a stand-in answering
/// `answer`: the result, what the bus saw, and the hostname file after.
async fn through(answer: Answer, limit: Duration) -> (Result<(), BusError>, Seen, Option<String>) {
    let scratch = Scratch::new();
    let bus = Bus::start(bus_socket(&scratch), hostname_file(&scratch), answer);
    let result = hostname::set_static_hostname(&bus.path, 1000, &name("rikuri02"), limit).await;
    let file = std::fs::read_to_string(hostname_file(&scratch)).ok();
    (result, bus.seen(), file)
}

const LIMIT: Duration = Duration::from_secs(5);

#[tokio::test]
async fn a_rename_authenticates_says_hello_and_makes_the_one_call() {
    let (result, seen, file) = through(Answer::Renamed, LIMIT).await;
    result.unwrap();
    assert_eq!(seen.auth, [hostname::auth_line(1000)]);
    assert_eq!(
        seen.messages,
        [
            hostname::hello(hostname::HELLO_SERIAL),
            hostname::set_static_hostname_call(&name("rikuri02"), hostname::CALL_SERIAL)
        ]
    );
    assert_eq!(seen.names, ["rikuri02"]);
    assert_eq!(file.as_deref(), Some("rikuri02\n"));
}

#[tokio::test]
async fn a_refusal_is_denied_and_another_error_refused() {
    for (error, denied) in [
        (ACCESS_DENIED, true),
        (INTERACTIVE, true),
        (INVALID_ARGS, false),
    ] {
        let (result, _, file) = through(Answer::Error(error), LIMIT).await;
        match result {
            Err(BusError::Denied(name)) if denied => assert_eq!(name, error),
            Err(BusError::Refused(name)) if !denied => assert_eq!(name, error),
            other => panic!("{error}: {other:?}"),
        }
        assert_eq!(file, None, "nothing written");
    }
}

#[tokio::test]
async fn anything_but_an_answer_is_an_error() {
    let (result, seen, _) = through(Answer::Rejected, LIMIT).await;
    assert!(
        matches!(result, Err(BusError::Auth(ref line)) if line == "REJECTED EXTERNAL"),
        "{result:?}"
    );
    assert!(
        seen.messages.is_empty(),
        "nothing sent after a refused authentication"
    );
    for answer in [Answer::Hangs, Answer::Huge, Answer::CallBeforeHello] {
        let (result, _, _) = through(answer.clone(), LIMIT).await;
        assert!(
            matches!(result, Err(BusError::Protocol(_))),
            "{answer:?}: {result:?}"
        );
    }
    let started = std::time::Instant::now();
    let (result, _, _) = through(Answer::Silent, Duration::from_millis(200)).await;
    assert!(matches!(result, Err(BusError::TimedOut)), "{result:?}");
    assert!(
        started.elapsed() < Duration::from_secs(3),
        "the limit holds"
    );
    let scratch = Scratch::new();
    let result =
        hostname::set_static_hostname(&bus_socket(&scratch), 1000, &name("rikuri02"), LIMIT).await;
    assert!(
        matches!(result, Err(BusError::Unreachable(_))),
        "{result:?}"
    );
}

/// Repair 2 (verifier, Important 1 and 2): a bus that keeps talking and
/// never answers is cut off at `MAX_READ`, long before the time limit.
#[tokio::test]
async fn a_bus_that_never_stops_talking_is_cut_off() {
    let started = std::time::Instant::now();
    let (result, _, file) = through(Answer::Flood, Duration::from_secs(20)).await;
    assert!(
        matches!(
            result,
            Err(BusError::Protocol("more than a rename's answer"))
        ),
        "{result:?}"
    );
    assert!(
        started.elapsed() < Duration::from_secs(10),
        "{:?}",
        started.elapsed()
    );
    assert_eq!(file, None);
}

/// Repair 2 (verifier, Important 4): an error to `Hello` is a refusal at once.
#[tokio::test]
async fn an_error_to_hello_is_refused() {
    let started = std::time::Instant::now();
    let (result, _, file) = through(Answer::HelloError(ACCESS_DENIED), LIMIT).await;
    assert!(
        // 5c.4b-2, repair 2: its own kind, `Hello`, so a lookup never reads
        // it as resolved's answer.
        matches!(result, Err(BusError::Hello(ref name)) if name == ACCESS_DENIED),
        "{result:?}"
    );
    assert!(started.elapsed() < Duration::from_secs(3));
    assert_eq!(file, None);
}

// ---- the route ----------------------------------------------------------------

/// A node whose hostname file names `hostname`, as hostnamed would keep it.
async fn named(hostname: &str) -> Node {
    let scratch = Scratch::new();
    std::fs::write(hostname_file(&scratch), format!("{hostname}\n")).unwrap();
    Node::start_over(scratch).await
}

/// Claims the node: the session's cookie and its CSRF token.
async fn owner(node: &Node) -> (String, String) {
    let claimed = claim(node, PASSWORD).await;
    assert_eq!(claimed.status, 201, "{}", claimed.body);
    let csrf = claimed.json()["csrf_token"].as_str().unwrap().to_owned();
    (claimed.session_cookie(), csrf)
}

async fn rename(node: &Node, session: &(String, String), to: &str) -> Reply {
    ok(
        node,
        Req::put("/api/node/name", json!({ "name": to }))
            .cookie(&session.0)
            .csrf(&session.1),
    )
    .await
}

/// `GET /api/setup` with `Host: host`.
async fn setup_as_host(node: &Node, host: &str) -> Reply {
    ok(node, Req::get("/api/setup").header("Host", host)).await
}

fn on_file(node: &Node) -> String {
    std::fs::read_to_string(hostname_file(&node.scratch)).unwrap()
}

#[tokio::test]
async fn the_owner_renames_the_node_and_the_old_name_leaves_at_once() {
    let node = named("rikurisetup").await;
    let bus = Bus::start(
        bus_socket(&node.scratch),
        hostname_file(&node.scratch),
        Answer::Renamed,
    );
    handshake_as(&node, "rikurisetup.local").await.unwrap();
    assert!(handshake_as(&node, "rikuri02.local").await.is_err());
    let session = owner(&node).await;

    let renamed = rename(&node, &session, "Rikuri02").await;
    assert_eq!(renamed.status, 200, "{}", renamed.body);
    assert_eq!(
        renamed.json(),
        json!({ "name": "rikuri02", "host": "rikuri02.local" })
    );
    assert_eq!(bus.seen().names, ["rikuri02"]);
    assert_eq!(on_file(&node), "rikuri02\n");

    // The certificate, with no look by the follower in between.
    handshake_as(&node, "rikuri02.local").await.unwrap();
    assert!(
        handshake_as(&node, "rikurisetup.local").await.is_err(),
        "the old name left the certificate"
    );
    // The Host check.
    assert_eq!(setup_as_host(&node, "rikurisetup.local").await.status, 421);
    let setup = setup_as_host(&node, "rikuri02.local").await;
    assert_eq!(setup.status, 200, "{}", setup.body);
    let names = setup.json()["names"].clone();
    assert!(
        names.as_array().unwrap().contains(&json!("rikuri02.local")),
        "{names}"
    );
    assert!(
        !names
            .as_array()
            .unwrap()
            .contains(&json!("rikurisetup.local")),
        "{names}"
    );
    // The Origin check.
    let old_origin = ok(
        &node,
        Req::put("/api/node/name", json!({ "name": "rikuri03" }))
            .cookie(&session.0)
            .csrf(&session.1)
            .header("Origin", "https://rikurisetup.local"),
    )
    .await;
    assert_eq!(old_origin.status, 403, "{}", old_origin.body);
    assert_eq!(bus.seen().names, ["rikuri02"], "refused before the bus");

    // A restart reads the name from the file.
    let node = node.restart().await;
    handshake_as(&node, "rikuri02.local").await.unwrap();
    assert!(handshake_as(&node, "rikurisetup.local").await.is_err());
    assert_eq!(setup_as_host(&node, "rikurisetup.local").await.status, 421);
    assert_eq!(setup_as_host(&node, "rikuri02.local").await.status, 200);
    drop(bus);
    node.stop().await;
}

#[tokio::test]
async fn a_rename_needs_a_session_and_its_csrf_token() {
    let node = named("rikurisetup").await;
    let bus = Bus::start(
        bus_socket(&node.scratch),
        hostname_file(&node.scratch),
        Answer::Renamed,
    );
    let anonymous = ok(
        &node,
        Req::put("/api/node/name", json!({ "name": "rikuri02" })),
    )
    .await;
    assert_eq!(anonymous.status, 401, "{}", anonymous.body);
    let session = owner(&node).await;
    let forged = ok(
        &node,
        Req::put("/api/node/name", json!({ "name": "rikuri02" }))
            .cookie(&"0".repeat(64))
            .csrf(&session.1),
    )
    .await;
    assert_eq!(forged.status, 401, "{}", forged.body);
    for csrf in [None, Some("nope")] {
        let mut req = Req::put("/api/node/name", json!({ "name": "rikuri02" })).cookie(&session.0);
        if let Some(csrf) = csrf {
            req = req.csrf(csrf);
        }
        let reply = ok(&node, req).await;
        assert_eq!(reply.status, 403, "{csrf:?}: {}", reply.body);
    }
    let elsewhere = ok(
        &node,
        Req::put("/api/node/name", json!({ "name": "rikuri02" }))
            .cookie(&session.0)
            .csrf(&session.1)
            .header("Origin", "https://evil.example"),
    )
    .await;
    assert_eq!(elsewhere.status, 403, "{}", elsewhere.body);
    assert!(bus.seen().auth.is_empty(), "the bus was never asked");
    assert_eq!(on_file(&node), "rikurisetup\n");
    node.stop().await;
}

#[tokio::test]
async fn a_name_that_is_not_one_is_refused_before_the_bus_is_asked() {
    let node = named("rikurisetup").await;
    let bus = Bus::start(
        bus_socket(&node.scratch),
        hostname_file(&node.scratch),
        Answer::Renamed,
    );
    let session = owner(&node).await;
    for bad in [
        "",
        "rikuri.local",
        "-rikuri",
        "localhost",
        "a b",
        "rikuri02\n",
    ] {
        let reply = rename(&node, &session, bad).await;
        assert_eq!(reply.status, 400, "{bad:?}: {}", reply.body);
        assert_eq!(reply.json(), json!({ "error": "not a name for the node" }));
    }
    assert!(bus.seen().auth.is_empty());
    assert_eq!(on_file(&node), "rikurisetup\n");
    node.stop().await;
}

#[tokio::test]
async fn a_rename_that_fails_changes_nothing() {
    for answer in [
        Some(Answer::Error(ACCESS_DENIED)),
        Some(Answer::Error(INVALID_ARGS)),
        Some(Answer::ReturnOnly),
        None,
    ] {
        let node = named("rikurisetup").await;
        let bus = answer
            .clone()
            .map(|a| Bus::start(bus_socket(&node.scratch), hostname_file(&node.scratch), a));
        let session = owner(&node).await;
        let reply = rename(&node, &session, "rikuri02").await;
        assert_eq!(reply.status, 503, "{answer:?}: {}", reply.body);
        assert_eq!(
            reply.json(),
            json!({ "error": "the node could not be renamed" })
        );
        assert_eq!(on_file(&node), "rikurisetup\n", "{answer:?}");
        handshake_as(&node, "rikurisetup.local").await.unwrap();
        assert!(
            handshake_as(&node, "rikuri02.local").await.is_err(),
            "{answer:?}"
        );
        assert_eq!(setup_as_host(&node, "rikurisetup.local").await.status, 200);
        assert_eq!(setup_as_host(&node, "rikuri02.local").await.status, 421);
        drop(bus);
        node.stop().await;
    }
}

// ---- the follower -------------------------------------------------------------

#[tokio::test]
async fn a_rename_made_elsewhere_is_taken_on_the_next_look() {
    let node = named("rikurisetup").await;
    let (stop, stopped) = tokio::sync::oneshot::channel::<()>();
    let follower = tokio::spawn(address::follow(
        node.booted.follower.clone(),
        || None,
        Duration::from_millis(10),
        async {
            let _ = stopped.await;
        },
    ));
    std::fs::write(hostname_file(&node.scratch), "rikuri03\n").unwrap();
    let mut reached = false;
    for _ in 0..200 {
        if handshake_as(&node, "rikuri03.local").await.is_ok() {
            reached = true;
            break;
        }
        tokio::time::sleep(Duration::from_millis(10)).await;
    }
    assert!(reached, "never served as rikuri03.local");
    assert!(handshake_as(&node, "rikurisetup.local").await.is_err());
    assert_eq!(setup_as_host(&node, "rikurisetup.local").await.status, 421);
    assert_eq!(setup_as_host(&node, "rikuri03.local").await.status, 200);
    stop.send(()).unwrap();
    follower.await.unwrap();
    node.stop().await;
}

// ---- 5c.4b-2: is a name in use? ------------------------------------------------

const NO_SUCH_RR: &str = "org.freedesktop.resolve1.NoSuchRR";

#[tokio::test]
async fn a_lookup_is_the_one_call_to_resolved() {
    let scratch = Scratch::new();
    let bus = Bus::with_lookups(
        bus_socket(&scratch),
        hostname_file(&scratch),
        Answer::Renamed,
        Lookups::Taken(&["rikuri01"]),
    );
    let uid = hostname::own_uid().unwrap();
    let limit = Duration::from_secs(5);
    let socket = bus_socket(&scratch);
    assert_eq!(
        hostname::name_answers(&socket, uid, &name("rikuri01"), limit).await,
        hostname::Lookup::Taken
    );
    assert_eq!(
        hostname::name_answers(&socket, uid, &name("rikuri02"), limit).await,
        hostname::Lookup::Free
    );
    let seen = bus.seen();
    assert_eq!(seen.lookups, ["rikuri01.local", "rikuri02.local"]);
    assert_eq!(seen.messages[0], hostname::hello(1));
    assert_eq!(
        seen.messages[1],
        hostname::resolve_hostname_call(&name("rikuri01"), 2)
    );
    assert!(seen.names.is_empty(), "no rename");
    drop(bus);
    // No bus at all: unknown, never free.
    assert!(matches!(
        hostname::name_answers(&socket, uid, &name("rikuri02"), limit).await,
        hostname::Lookup::Unknown(_)
    ));
}

async fn suggestion(node: &Node, session: &(String, String)) -> Reply {
    ok(
        node,
        Req::get("/api/node/name/suggestion").cookie(&session.0),
    )
    .await
}

#[tokio::test]
async fn the_suggestion_is_the_first_name_nothing_answers() {
    let node = named("rikurisetup").await;
    let bus = Bus::with_lookups(
        bus_socket(&node.scratch),
        hostname_file(&node.scratch),
        Answer::Renamed,
        Lookups::Taken(&["rikuri01", "rikuri02"]),
    );
    let session = owner(&node).await;
    let reply = suggestion(&node, &session).await;
    assert_eq!(reply.status, 200, "{}", reply.body);
    assert_eq!(reply.json(), json!({ "name": "rikuri03" }));
    let seen = bus.seen();
    assert_eq!(
        seen.lookups,
        ["rikuri01.local", "rikuri02.local", "rikuri03.local"]
    );
    assert!(seen.names.is_empty(), "a suggestion renames nothing");
    assert_eq!(on_file(&node), "rikurisetup\n");
    drop(bus);
    node.stop().await;
}

#[tokio::test]
async fn every_name_taken_suggests_none() {
    let node = named("rikurisetup").await;
    let bus = Bus::with_lookups(
        bus_socket(&node.scratch),
        hostname_file(&node.scratch),
        Answer::Renamed,
        Lookups::All,
    );
    let session = owner(&node).await;
    let reply = suggestion(&node, &session).await;
    assert_eq!(reply.status, 200, "{}", reply.body);
    assert_eq!(reply.json(), json!({ "name": null }));
    assert_eq!(bus.seen().lookups.len(), 99);
    drop(bus);
    node.stop().await;
}

#[tokio::test]
async fn a_suggestion_resolved_cannot_give_is_refused() {
    for lookups in [Some(Lookups::Error(NO_SUCH_RR)), None] {
        let node = named("rikurisetup").await;
        let bus = lookups.map(|l| {
            Bus::with_lookups(
                bus_socket(&node.scratch),
                hostname_file(&node.scratch),
                Answer::Renamed,
                l,
            )
        });
        let session = owner(&node).await;
        let reply = suggestion(&node, &session).await;
        assert_eq!(reply.status, 503, "{lookups:?}: {}", reply.body);
        assert_eq!(
            reply.json(),
            json!({ "error": "the node could not check which names are free" })
        );
        drop(bus);
        node.stop().await;
    }
}

#[tokio::test]
async fn a_suggestion_needs_a_session() {
    let node = named("rikurisetup").await;
    let bus = Bus::start(
        bus_socket(&node.scratch),
        hostname_file(&node.scratch),
        Answer::Renamed,
    );
    let anonymous = ok(&node, Req::get("/api/node/name/suggestion")).await;
    assert_eq!(anonymous.status, 401, "{}", anonymous.body);
    let forged = ok(
        &node,
        Req::get("/api/node/name/suggestion").cookie(&"0".repeat(64)),
    )
    .await;
    assert_eq!(forged.status, 401, "{}", forged.body);
    assert!(bus.seen().auth.is_empty(), "resolved was never asked");
    node.stop().await;
}

#[tokio::test]
async fn the_rename_asks_whether_the_name_is_free_first() {
    let node = named("rikurisetup").await;
    let bus = Bus::start(
        bus_socket(&node.scratch),
        hostname_file(&node.scratch),
        Answer::Renamed,
    );
    let session = owner(&node).await;
    let renamed = rename(&node, &session, "rikuri02").await;
    assert_eq!(renamed.status, 200, "{}", renamed.body);
    let seen = bus.seen();
    assert_eq!(seen.lookups, ["rikuri02.local"]);
    assert_eq!(seen.names, ["rikuri02"]);
    // The lookup's connection, then the rename's.
    assert_eq!(
        seen.messages[1],
        hostname::resolve_hostname_call(&name("rikuri02"), 2)
    );
    assert_eq!(
        seen.messages[3],
        hostname::set_static_hostname_call(&name("rikuri02"), 2)
    );
    drop(bus);
    node.stop().await;
}

#[tokio::test]
async fn a_name_in_use_is_refused_and_hostnamed_never_asked() {
    let node = named("rikurisetup").await;
    let bus = Bus::with_lookups(
        bus_socket(&node.scratch),
        hostname_file(&node.scratch),
        Answer::Renamed,
        Lookups::Taken(&["rikuri02"]),
    );
    let session = owner(&node).await;
    let reply = rename(&node, &session, "rikuri02").await;
    assert_eq!(reply.status, 409, "{}", reply.body);
    assert_eq!(
        reply.json(),
        json!({ "error": "that name is already in use on this network" })
    );
    let seen = bus.seen();
    assert_eq!(seen.lookups, ["rikuri02.local"]);
    assert!(seen.names.is_empty(), "hostnamed was never asked");
    assert_eq!(on_file(&node), "rikurisetup\n");
    handshake_as(&node, "rikurisetup.local").await.unwrap();
    assert!(handshake_as(&node, "rikuri02.local").await.is_err());
    drop(bus);
    node.stop().await;
}

#[tokio::test]
async fn a_name_resolved_cannot_vouch_for_is_refused_and_hostnamed_never_asked() {
    let node = named("rikurisetup").await;
    let bus = Bus::with_lookups(
        bus_socket(&node.scratch),
        hostname_file(&node.scratch),
        Answer::Renamed,
        Lookups::Error(NO_SUCH_RR),
    );
    let session = owner(&node).await;
    let reply = rename(&node, &session, "rikuri02").await;
    assert_eq!(reply.status, 503, "{}", reply.body);
    assert_eq!(
        reply.json(),
        json!({ "error": "the node could not be renamed" })
    );
    let seen = bus.seen();
    assert_eq!(seen.lookups, ["rikuri02.local"]);
    assert!(seen.names.is_empty(), "hostnamed was never asked");
    assert_eq!(on_file(&node), "rikurisetup\n");
    drop(bus);
    node.stop().await;
}

#[tokio::test]
async fn a_named_node_is_not_renamed_again() {
    // Named by its owner already: refused before anything is asked.
    let node = named("rikuri05").await;
    let bus = Bus::start(
        bus_socket(&node.scratch),
        hostname_file(&node.scratch),
        Answer::Renamed,
    );
    let session = owner(&node).await;
    let reply = rename(&node, &session, "rikuri06").await;
    assert_eq!(reply.status, 409, "{}", reply.body);
    assert_eq!(
        reply.json(),
        json!({ "error": "the node already has a name" })
    );
    assert!(bus.seen().auth.is_empty(), "the bus was never asked");
    assert_eq!(on_file(&node), "rikuri05\n");
    drop(bus);
    node.stop().await;

    // Named through the page: a second rename is refused the same way.
    let node = named("rikurisetup").await;
    let bus = Bus::start(
        bus_socket(&node.scratch),
        hostname_file(&node.scratch),
        Answer::Renamed,
    );
    let session = owner(&node).await;
    assert_eq!(rename(&node, &session, "rikuri02").await.status, 200);
    let again = ok(
        &node,
        Req::put("/api/node/name", json!({ "name": "rikuri03" }))
            .cookie(&session.0)
            .csrf(&session.1),
    )
    .await;
    assert_eq!(again.status, 409, "{}", again.body);
    assert_eq!(
        again.json(),
        json!({ "error": "the node already has a name" })
    );
    assert_eq!(bus.seen().names, ["rikuri02"]);
    assert_eq!(on_file(&node), "rikuri02\n");
    drop(bus);
    node.stop().await;
}

// ---- 5c.4b-2, repair 2 (verifier, first pass) -------------------------------

/// Nit 1: an error to `Hello` is the bus's, never resolved's "not found",
/// whatever its name.
#[tokio::test]
async fn an_error_to_hello_is_never_a_free_name() {
    for name_of_error in ["org.freedesktop.DBus.Error.Timeout", common::bus::NXDOMAIN] {
        let scratch = Scratch::new();
        let bus = Bus::with_lookups(
            bus_socket(&scratch),
            hostname_file(&scratch),
            Answer::Renamed,
            Lookups::HelloError(name_of_error),
        );
        let uid = hostname::own_uid().unwrap();
        let got = hostname::name_answers(
            &bus_socket(&scratch),
            uid,
            &name("rikuri02"),
            Duration::from_secs(5),
        )
        .await;
        assert!(
            matches!(got, hostname::Lookup::Unknown(_)),
            "{name_of_error}: {got:?}"
        );
        drop(bus);
    }
}

/// Important 3: a hostname file that cannot be read is no proof the node is
/// in setup: 503, and the bus is never asked.
#[tokio::test]
async fn an_unreadable_hostname_file_is_no_rename() {
    let node = named("rikurisetup").await;
    let bus = Bus::start(
        bus_socket(&node.scratch),
        hostname_file(&node.scratch),
        Answer::Renamed,
    );
    let session = owner(&node).await;
    std::fs::remove_file(hostname_file(&node.scratch)).unwrap();
    let reply = rename(&node, &session, "rikuri02").await;
    assert_eq!(reply.status, 503, "{}", reply.body);
    assert_eq!(
        reply.json(),
        json!({ "error": "the node could not be renamed" })
    );
    let seen = bus.seen();
    assert!(seen.auth.is_empty(), "the bus was never asked: {seen:?}");
    assert!(!hostname_file(&node.scratch).exists());
    drop(bus);
    node.stop().await;
}
