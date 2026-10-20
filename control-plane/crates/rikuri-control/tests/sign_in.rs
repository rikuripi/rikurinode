//! The trust boundary through its real entry points: a TLS client against a
//! real loopback socket, from the first request on an unclaimed node to a
//! password change behind a step-up, and a restart in between.

#![allow(clippy::unwrap_used, clippy::expect_used)]

mod common;

use common::{Node, PASSWORD, Req, claim, https, ok};
use serde_json::json;

#[tokio::test]
async fn setup_is_readable_by_a_client_that_trusts_the_ca_and_by_no_other() {
    let node = Node::start().await;
    let reply = ok(&node, Req::get("/api/setup")).await;
    assert_eq!(reply.status, 200, "{}", reply.body);
    assert_eq!(reply.header("cache-control"), Some("no-store"));
    let body = reply.json();
    assert_eq!(body["claimed"], false);
    assert_eq!(body["claim"], "armed");
    assert_eq!(
        body["ca_fingerprint_sha256"],
        node.booted.identity.ca_fingerprint
    );
    assert_eq!(body["names"], json!(["localhost", "rikuri01.local"]));

    let refused = https(&node, Req::get("/api/setup").distrust_ca()).await;
    let err = refused
        .err()
        .expect("a client without the CA cannot complete the handshake");
    assert!(err.to_lowercase().contains("certificate"), "{err}");
    node.stop().await;
}

#[tokio::test]
async fn the_claim_makes_the_first_person_with_the_code_the_owner() {
    let node = Node::start().await;
    let code = node.claim_code();
    assert_eq!(code.len(), 12, "{code}");

    let wrong = ok(
        &node,
        Req::post(
            "/api/claim",
            json!({ "code": "AAAA-AAAA-AA", "password": PASSWORD }),
        ),
    )
    .await;
    assert_eq!(wrong.status, 401, "{}", wrong.body);
    assert_eq!(wrong.json()["error"], "claim refused");
    assert!(
        !wrong.body.contains(&code),
        "the code never appears in a response"
    );

    let weak = ok(
        &node,
        Req::post("/api/claim", json!({ "code": code, "password": "short" })),
    )
    .await;
    assert_eq!(weak.status, 422, "{}", weak.body);
    assert!(
        weak.json()["error"]
            .as_str()
            .unwrap()
            .contains("12 characters")
    );
    assert_eq!(
        ok(&node, Req::get("/api/setup")).await.json()["claim"],
        "armed",
        "a weak password does not spend the claim"
    );

    let typed_lower = code.to_lowercase();
    let claimed = ok(
        &node,
        Req::post(
            "/api/claim",
            json!({ "code": typed_lower, "password": PASSWORD }),
        ),
    )
    .await;
    assert_eq!(claimed.status, 201, "{}", claimed.body);
    let cookie = claimed.header("set-cookie").unwrap().to_owned();
    for flag in [
        "Path=/",
        "Max-Age=2592000",
        "HttpOnly",
        "Secure",
        "SameSite=Strict",
    ] {
        assert!(cookie.contains(flag), "{cookie}");
    }
    let session = claimed.session_cookie();
    assert_eq!(session.len(), 64);
    assert!(
        !claimed.body.contains(&session),
        "the id lives in the cookie, not the body"
    );
    let body = claimed.json();
    assert_eq!(body["csrf_token"].as_str().unwrap().len(), 64);
    let issued = body["issued_unix"].as_u64().unwrap();
    let now = rikuri_control::status::unix_now().unwrap();
    assert!(
        now.abs_diff(issued) <= 60,
        "issued at the real clock: {issued} vs {now}"
    );
    assert_eq!(
        body["expires_unix"].as_u64().unwrap(),
        issued + 30 * 24 * 60 * 60
    );

    let setup = ok(&node, Req::get("/api/setup")).await.json();
    assert_eq!(setup["claimed"], true);
    assert_eq!(setup["claim"], "done");

    let again = ok(
        &node,
        Req::post("/api/claim", json!({ "code": code, "password": PASSWORD })),
    )
    .await;
    assert_eq!(again.status, 409, "{}", again.body);

    let me = ok(&node, Req::get("/api/session").cookie(&session)).await;
    assert_eq!(me.status, 200, "{}", me.body);
    assert_eq!(me.json()["csrf_token"], body["csrf_token"]);
    node.stop().await;
}

#[tokio::test]
async fn wrong_codes_are_counted_on_disk_delayed_and_lifted_by_a_console_re_arm() {
    let node = Node::start().await;
    for n in 1..=5 {
        let r = ok(
            &node,
            Req::post(
                "/api/claim",
                json!({ "code": "AAAA-AAAA-AA", "password": PASSWORD }),
            ),
        )
        .await;
        assert_eq!(r.status, 401, "try {n}: {}", r.body);
    }
    let blocked = ok(
        &node,
        Req::post(
            "/api/claim",
            json!({ "code": node.claim_code(), "password": PASSWORD }),
        ),
    )
    .await;
    assert_eq!(blocked.status, 429, "{}", blocked.body);
    assert_eq!(blocked.header("retry-after"), Some("1"));
    assert_eq!(blocked.json()["retry_after_seconds"], 1);
    let dir = rikuri_control::state::StateDir::open(&node.scratch.0).unwrap();
    assert_eq!(
        rikuri_control::claim::load(&dir)
            .unwrap()
            .unwrap()
            .wrong_tries,
        5,
        "the count is on disk"
    );

    // The console arms a new code: the count resets, the block lifts, the new code claims.
    let fresh =
        rikuri_control::claim::arm(&dir, rikuri_control::status::unix_now().unwrap()).unwrap();
    let old = ok(
        &node,
        Req::post(
            "/api/claim",
            json!({ "code": node.claim_code(), "password": PASSWORD }),
        ),
    )
    .await;
    assert_eq!(old.status, 401, "the old code is dead: {}", old.body);
    let claimed = ok(
        &node,
        Req::post(
            "/api/claim",
            json!({ "code": fresh.formatted(), "password": PASSWORD }),
        ),
    )
    .await;
    assert_eq!(claimed.status, 201, "{}", claimed.body);
    node.stop().await;
}

#[tokio::test]
async fn sign_in_opens_a_session_and_sign_out_revokes_it_server_side() {
    let node = Node::start().await;
    claim(&node, PASSWORD).await;

    let wrong = ok(
        &node,
        Req::post("/api/session", json!({ "password": "not the password" })),
    )
    .await;
    assert_eq!(wrong.status, 401, "{}", wrong.body);
    assert_eq!(wrong.json()["error"], "sign-in refused");

    let signed_in = ok(
        &node,
        Req::post("/api/session", json!({ "password": PASSWORD })),
    )
    .await;
    assert_eq!(signed_in.status, 201, "{}", signed_in.body);
    let session = signed_in.session_cookie();
    let csrf = signed_in.json()["csrf_token"].as_str().unwrap().to_owned();

    let anonymous = ok(&node, Req::get("/api/session")).await;
    assert_eq!(anonymous.status, 401);
    let forged = ok(&node, Req::get("/api/session").cookie(&"0".repeat(64))).await;
    assert_eq!(forged.status, 401);
    let me = ok(&node, Req::get("/api/session").cookie(&session)).await;
    assert_eq!(me.status, 200, "{}", me.body);

    let no_csrf = ok(&node, Req::delete("/api/session").cookie(&session)).await;
    assert_eq!(no_csrf.status, 403, "{}", no_csrf.body);
    let wrong_csrf = ok(
        &node,
        Req::delete("/api/session").cookie(&session).csrf("nope"),
    )
    .await;
    assert_eq!(wrong_csrf.status, 403);
    let out = ok(
        &node,
        Req::delete("/api/session").cookie(&session).csrf(&csrf),
    )
    .await;
    assert_eq!(out.status, 204, "{}", out.body);
    assert!(out.header("set-cookie").unwrap().contains("Max-Age=0"));
    let dead = ok(&node, Req::get("/api/session").cookie(&session)).await;
    assert_eq!(
        dead.status, 401,
        "the same cookie is refused after sign-out"
    );
    node.stop().await;
}

#[tokio::test]
async fn wrong_passwords_are_delayed_globally() {
    let node = Node::start().await;
    claim(&node, PASSWORD).await;
    for _ in 0..5 {
        let r = ok(
            &node,
            Req::post("/api/session", json!({ "password": "wrong wrong wrong" })),
        )
        .await;
        assert_eq!(r.status, 401);
    }
    let blocked = ok(
        &node,
        Req::post("/api/session", json!({ "password": PASSWORD })),
    )
    .await;
    assert_eq!(
        blocked.status, 429,
        "even the right password waits: {}",
        blocked.body
    );
    assert_eq!(blocked.header("retry-after"), Some("1"));
    tokio::time::sleep(std::time::Duration::from_millis(1100)).await;
    let signed_in = ok(
        &node,
        Req::post("/api/session", json!({ "password": PASSWORD })),
    )
    .await;
    assert_eq!(signed_in.status, 201, "{}", signed_in.body);
    node.stop().await;
}

#[tokio::test]
async fn every_request_needs_the_nodes_host_and_every_mutation_its_origin() {
    let node = Node::start().await;
    let rebinding = ok(&node, Req::get("/api/setup").header("Host", "evil.example")).await;
    assert_eq!(rebinding.status, 421, "{}", rebinding.body);
    let by_address = ok(
        &node,
        Req::get("/api/setup").header("Host", &format!("127.0.0.1:{}", node.https.port())),
    )
    .await;
    assert_eq!(by_address.status, 200, "{}", by_address.body);
    let by_name = ok(
        &node,
        Req::get("/api/setup").header("Host", "rikuri01.local"),
    )
    .await;
    assert_eq!(by_name.status, 200);

    let code = node.claim_code();
    let no_origin = ok(
        &node,
        Req::post("/api/claim", json!({ "code": code, "password": PASSWORD })).no_origin(),
    )
    .await;
    assert_eq!(no_origin.status, 403, "{}", no_origin.body);
    let other_site = ok(
        &node,
        Req::post("/api/claim", json!({ "code": code, "password": PASSWORD }))
            .header("Origin", "https://evil.example"),
    )
    .await;
    assert_eq!(other_site.status, 403);
    let plain_scheme = ok(
        &node,
        Req::post("/api/claim", json!({ "code": code, "password": PASSWORD }))
            .header("Origin", "http://localhost"),
    )
    .await;
    assert_eq!(plain_scheme.status, 403);
    assert_eq!(
        ok(&node, Req::get("/api/setup")).await.json()["claim"],
        "armed",
        "refused mutations spend nothing"
    );
    let own_page = ok(
        &node,
        Req::post("/api/claim", json!({ "code": code, "password": PASSWORD })).header(
            "Origin",
            &format!("https://rikuri01.local:{}", node.https.port()),
        ),
    )
    .await;
    assert_eq!(own_page.status, 201, "{}", own_page.body);
    node.stop().await;
}

#[tokio::test]
async fn a_step_up_is_bound_to_one_action_and_the_password_change_needs_it() {
    let node = Node::start().await;
    let a = claim(&node, PASSWORD).await;
    let (session_a, csrf_a) = (
        a.session_cookie(),
        a.json()["csrf_token"].as_str().unwrap().to_owned(),
    );
    let b = ok(
        &node,
        Req::post("/api/session", json!({ "password": PASSWORD })),
    )
    .await;
    let session_b = b.session_cookie();
    let new_password = "a brand new password";

    let bare = ok(
        &node,
        Req::put("/api/owner/password", json!({ "password": new_password }))
            .cookie(&session_a)
            .csrf(&csrf_a),
    )
    .await;
    assert_eq!(bare.status, 403, "{}", bare.body);
    assert_eq!(bare.json()["error"], "step-up required");

    let wrong = ok(
        &node,
        Req::post(
            "/api/step-up",
            json!({ "password": "wrong", "method": "PUT", "path": "/api/owner/password" }),
        )
        .cookie(&session_a)
        .csrf(&csrf_a),
    )
    .await;
    assert_eq!(wrong.status, 401, "{}", wrong.body);

    let elsewhere = ok(
        &node,
        Req::post(
            "/api/step-up",
            json!({ "password": PASSWORD, "method": "DELETE", "path": "/api/session" }),
        )
        .cookie(&session_a)
        .csrf(&csrf_a),
    )
    .await;
    assert_eq!(elsewhere.status, 201, "{}", elsewhere.body);
    let other_token = elsewhere.json()["token"].as_str().unwrap().to_owned();
    let shopped = ok(
        &node,
        Req::put("/api/owner/password", json!({ "password": new_password }))
            .cookie(&session_a)
            .csrf(&csrf_a)
            .step_up(&other_token),
    )
    .await;
    assert_eq!(
        shopped.status, 403,
        "a token for another action is refused: {}",
        shopped.body
    );

    let granted = ok(
        &node,
        Req::post(
            "/api/step-up",
            json!({ "password": PASSWORD, "method": "put", "path": "/API/owner/password/" }),
        )
        .cookie(&session_a)
        .csrf(&csrf_a),
    )
    .await;
    assert_eq!(granted.status, 201, "{}", granted.body);
    let body = granted.json();
    assert_eq!(
        body["bound_to"],
        json!({ "method": "PUT", "path": "/api/owner/password" })
    );
    assert_eq!(body["expires_in_seconds"], 300);
    let token = body["token"].as_str().unwrap().to_owned();

    let weak = ok(
        &node,
        Req::put("/api/owner/password", json!({ "password": "short" }))
            .cookie(&session_a)
            .csrf(&csrf_a)
            .step_up(&token),
    )
    .await;
    assert_eq!(weak.status, 422, "{}", weak.body);
    let changed = ok(
        &node,
        Req::put("/api/owner/password", json!({ "password": new_password }))
            .cookie(&session_a)
            .csrf(&csrf_a)
            .step_up(&token),
    )
    .await;
    assert_eq!(
        changed.status, 204,
        "a weak password does not spend the token: {}",
        changed.body
    );
    let reused = ok(
        &node,
        Req::put("/api/owner/password", json!({ "password": new_password }))
            .cookie(&session_a)
            .csrf(&csrf_a)
            .step_up(&token),
    )
    .await;
    assert_eq!(reused.status, 403, "single-use");

    assert_eq!(
        ok(&node, Req::get("/api/session").cookie(&session_a))
            .await
            .status,
        200,
        "the changing session stays"
    );
    assert_eq!(
        ok(&node, Req::get("/api/session").cookie(&session_b))
            .await
            .status,
        401,
        "every other session is revoked"
    );
    assert_eq!(
        ok(
            &node,
            Req::post("/api/session", json!({ "password": PASSWORD }))
        )
        .await
        .status,
        401
    );
    assert_eq!(
        ok(
            &node,
            Req::post("/api/session", json!({ "password": new_password }))
        )
        .await
        .status,
        201
    );
    node.stop().await;
}

#[tokio::test]
async fn sessions_and_the_claim_survive_a_restart() {
    let node = Node::start().await;
    let claimed = claim(&node, PASSWORD).await;
    let session = claimed.session_cookie();
    let node = node.restart().await;
    assert!(node.booted.armed.is_none(), "a claimed node arms nothing");
    let setup = ok(&node, Req::get("/api/setup")).await.json();
    assert_eq!(setup["claimed"], true);
    let me = ok(&node, Req::get("/api/session").cookie(&session)).await;
    assert_eq!(me.status, 200, "{}", me.body);
    node.stop().await;
}

#[tokio::test]
async fn oversized_bodies_unknown_paths_and_wrong_methods_are_refused() {
    let node = Node::start().await;
    let big = ok(
        &node,
        Req::post(
            "/api/claim",
            json!({ "code": "x".repeat(17 * 1024), "password": PASSWORD }),
        ),
    )
    .await;
    assert_eq!(big.status, 413, "{}", big.body);
    let under = ok(
        &node,
        Req::post(
            "/api/claim",
            json!({ "code": "x".repeat(10 * 1024), "password": PASSWORD }),
        ),
    )
    .await;
    assert_eq!(
        under.status, 401,
        "a body under the limit is read and judged: {}",
        under.body
    );
    assert_eq!(ok(&node, Req::get("/api/nope")).await.status, 404);
    assert_eq!(
        ok(&node, Req::new("POST", "/api/setup").origin())
            .await
            .status,
        405
    );
    node.stop().await;
}
