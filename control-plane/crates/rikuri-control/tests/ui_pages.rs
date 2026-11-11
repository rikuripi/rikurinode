//! The setup pages (5c.3a): the certificate screen in the clear, the secure
//! page over TLS, both from the files embedded in the binary.
//! Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md

#![allow(clippy::unwrap_used, clippy::expect_used)]

mod common;

use common::{Node, Reply, Req, https, plain};

/// The pages' Content-Security-Policy, written out here so that a weakened
/// policy in the code fails this test.
const CSP: &str = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; \
                   font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; \
                   frame-ancestors 'none'";
const IMMUTABLE: &str = "public, max-age=31536000, immutable";

fn assert_page(reply: &Reply, page: &str) {
    assert_eq!(reply.status, 200, "{}", reply.body);
    assert_eq!(reply.header("content-type"), Some("text/html; charset=utf-8"));
    assert_eq!(reply.header("content-security-policy"), Some(CSP));
    assert_eq!(reply.header("x-content-type-options"), Some("nosniff"));
    assert_eq!(reply.header("referrer-policy"), Some("no-referrer"));
    assert_eq!(reply.header("x-frame-options"), Some("DENY"));
    assert_eq!(reply.header("cache-control"), Some("no-cache"));
    let marker = format!("<meta name=\"rikuri-page\" content=\"{page}\">");
    assert!(reply.body.contains(&marker), "no {marker} in {}", reply.body);
    // Every script is a file the CSP allows: no inline script, no inline style.
    for (i, _) in reply.body.match_indices("<script") {
        let tag = &reply.body[i..i + reply.body[i..].find('>').unwrap()];
        assert!(tag.contains(" src=\"/assets/"), "an inline or outside script: {tag}");
    }
    assert!(!reply.body.contains("<style"), "an inline style block");
    assert!(!reply.body.contains(" style=\""), "an inline style attribute");
}

/// The `/assets/` paths a page names (its scripts and its stylesheets).
fn assets(body: &str) -> Vec<String> {
    let mut found = Vec::new();
    for attr in ["src=\"", "href=\""] {
        for (i, _) in body.match_indices(attr) {
            let rest = &body[i + attr.len()..];
            let value = &rest[..rest.find('"').unwrap()];
            if value.starts_with("/assets/") {
                found.push(value.to_owned());
            }
        }
    }
    assert!(
        found.iter().any(|a| a.ends_with(".js")),
        "the page names no script: {body}"
    );
    found
}

fn assert_asset(reply: &Reply, path: &str) {
    assert_eq!(reply.status, 200, "{path}: {}", reply.body);
    let expected = if path.ends_with(".js") {
        "text/javascript; charset=utf-8"
    } else if path.ends_with(".css") {
        "text/css; charset=utf-8"
    } else if path.ends_with(".woff2") {
        "font/woff2"
    } else {
        panic!("an asset of an unexpected type: {path}")
    };
    assert_eq!(reply.header("content-type"), Some(expected), "{path}");
    assert_eq!(reply.header("cache-control"), Some(IMMUTABLE), "{path}");
    assert_eq!(reply.header("x-content-type-options"), Some("nosniff"), "{path}");
    assert!(!reply.body.is_empty(), "{path} is empty");
}

#[tokio::test]
async fn the_plain_root_is_the_certificate_screen() {
    let node = Node::start().await;
    let page = plain(&node, Req::get("/")).await;
    assert_page(&page, "certificate");
    for path in assets(&page.body) {
        assert_asset(&plain(&node, Req::get(&path)).await, &path);
    }
    node.stop().await;
}

#[tokio::test]
async fn the_secure_page_is_served_only_over_tls() {
    let node = Node::start().await;
    for path in ["/", "/setup"] {
        let page = https(&node, Req::get(path)).await.unwrap();
        assert_page(&page, "secure");
        for asset in assets(&page.body) {
            assert_asset(&https(&node, Req::get(&asset)).await.unwrap(), &asset);
        }
    }
    // In the clear, the secure page's paths go to HTTPS; nothing serves it.
    let port = node.https.port();
    for path in ["/setup", "/index.html", "/secure.html"] {
        let reply = plain(&node, Req::get(path)).await;
        assert_eq!(reply.status, 308, "{path}: {}", reply.body);
        assert_eq!(
            reply.header("location"),
            Some(format!("https://localhost:{port}{path}").as_str())
        );
    }
    node.stop().await;
}

#[tokio::test]
async fn the_certificate_screen_is_not_the_secure_page_and_the_api_stays_json() {
    let node = Node::start().await;
    let page = https(&node, Req::get("/")).await.unwrap();
    assert!(!page.body.contains("content=\"certificate\""));
    let setup = https(&node, Req::get("/api/setup")).await.unwrap();
    assert_eq!(setup.status, 200, "{}", setup.body);
    assert_eq!(setup.header("cache-control"), Some("no-store"));
    assert_eq!(setup.json()["claimed"], false);
    node.stop().await;
}

#[tokio::test]
async fn only_the_embedded_files_are_served_never_a_path_on_disk() {
    let node = Node::start().await;
    for path in [
        "/assets/missing.js",
        "/assets/../../../etc/passwd",
        "/assets/%2e%2e/%2e%2e/etc/passwd",
        "/assets/",
        "/assets",
        "/cert.html",
        "/favicon.ico",
    ] {
        let tls = https(&node, Req::get(path)).await.unwrap();
        assert_eq!(tls.status, 404, "{path} over TLS: {}", tls.body);
        assert!(!tls.body.contains("root:"), "{path}");
    }
    for path in ["/assets/missing.js", "/assets/../../../etc/passwd"] {
        let clear = plain(&node, Req::get(path)).await;
        assert_eq!(clear.status, 404, "{path} in the clear: {}", clear.body);
    }
    node.stop().await;
}

#[tokio::test]
async fn the_pages_are_read_only() {
    let node = Node::start().await;
    let post = https(&node, Req::post("/", serde_json::json!({})))
        .await
        .unwrap();
    assert_eq!(post.status, 405, "{}", post.body);
    let clear = plain(&node, Req::post("/", serde_json::json!({}))).await;
    assert_eq!(clear.status, 405, "{}", clear.body);
    node.stop().await;
}

#[tokio::test]
async fn the_shipped_fonts_carry_their_licence() {
    let node = Node::start().await;
    let notice = https(&node, Req::get("/licenses.txt")).await.unwrap();
    assert_eq!(notice.status, 200, "{}", notice.body);
    assert_eq!(notice.header("content-type"), Some("text/plain; charset=utf-8"));
    for needed in ["SIL OPEN FONT LICENSE Version 1.1", "Fredoka", "Inter", "Svelte"] {
        assert!(notice.body.contains(needed), "no {needed:?} in the notice");
    }
    node.stop().await;
}
