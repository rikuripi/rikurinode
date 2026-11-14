//! The setup pages (5c.3a), served from the table `build.rs` embeds: the
//! certificate screen in the clear at `/`, the secure app over TLS at `/`,
//! `/setup`, `/claim`, `/signin` and `/home` (5c.3b) and `/name` (5c.4b-2),
//! and their assets on both. A path not in the table is a 404; nothing here
//! reads the disk.
//! Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md

use axum::Router;
use axum::extract::Path;
use axum::http::{HeaderValue, StatusCode, header};
use axum::response::{IntoResponse, Response};
use axum::routing::get;

pub(crate) struct UiFile {
    pub(crate) path: &'static str,
    pub(crate) content_type: &'static str,
    pub(crate) body: &'static [u8],
}

include!(concat!(env!("OUT_DIR"), "/ui_files.rs"));

/// Only the node's own files, no inline code, no outside origin, no framing.
pub(crate) const CSP: &str = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; \
                              font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; \
                              frame-ancestors 'none'";

const CERTIFICATE_SCREEN: &str = "/cert.html";
const SECURE_PAGE: &str = "/index.html";

fn find(path: &str) -> Option<&'static UiFile> {
    FILES
        .binary_search_by(|f| f.path.cmp(path))
        .ok()
        .and_then(|i| FILES.get(i))
}

fn not_found() -> Response {
    StatusCode::NOT_FOUND.into_response()
}

fn serve(file: &'static UiFile, cache: &'static str) -> Response {
    let mut response = (StatusCode::OK, file.body).into_response();
    let headers = response.headers_mut();
    headers.insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static(file.content_type),
    );
    headers.insert(header::CACHE_CONTROL, HeaderValue::from_static(cache));
    headers.insert(
        header::X_CONTENT_TYPE_OPTIONS,
        HeaderValue::from_static("nosniff"),
    );
    response
}

fn page(path: &str) -> Response {
    let Some(file) = find(path) else {
        return not_found();
    };
    let mut response = serve(file, "no-cache");
    let headers = response.headers_mut();
    headers.insert(
        header::CONTENT_SECURITY_POLICY,
        HeaderValue::from_static(CSP),
    );
    headers.insert(
        header::REFERRER_POLICY,
        HeaderValue::from_static("no-referrer"),
    );
    headers.insert(header::X_FRAME_OPTIONS, HeaderValue::from_static("DENY"));
    response
}

async fn certificate_screen() -> Response {
    page(CERTIFICATE_SCREEN)
}

async fn secure_page() -> Response {
    page(SECURE_PAGE)
}

/// A built asset: its name carries its content's hash, so it never changes.
async fn asset(Path(rest): Path<String>) -> Response {
    match find(&format!("/assets/{rest}")) {
        Some(file) => serve(file, "public, max-age=31536000, immutable"),
        None => not_found(),
    }
}

async fn favicon() -> Response {
    find("/favicon.svg").map_or_else(not_found, |f| serve(f, "no-cache"))
}

async fn licenses() -> Response {
    find("/licenses.txt").map_or_else(not_found, |f| serve(f, "no-cache"))
}

fn shared<S: Clone + Send + Sync + 'static>(router: Router<S>) -> Router<S> {
    router
        .route("/assets/{*rest}", get(asset))
        .route("/favicon.svg", get(favicon))
        .route("/licenses.txt", get(licenses))
}

/// The plain listener's pages: the certificate screen and its files.
pub(crate) fn plain_routes<S: Clone + Send + Sync + 'static>() -> Router<S> {
    shared(Router::new().route("/", get(certificate_screen)))
}

/// The TLS listener's pages: the secure page and its files.
pub(crate) fn secure_routes<S: Clone + Send + Sync + 'static>() -> Router<S> {
    shared(
        Router::new()
            .route("/", get(secure_page))
            .route("/setup", get(secure_page))
            // 5c.3b: the owner's pages, the same app.
            .route("/claim", get(secure_page))
            .route("/signin", get(secure_page))
            .route("/home", get(secure_page))
            // 5c.4b-2: naming the node.
            .route("/name", get(secure_page)),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_table_is_sorted_and_holds_both_pages() {
        assert!(
            FILES.windows(2).all(|w| w[0].path < w[1].path),
            "binary search needs the table sorted"
        );
        for needed in [
            CERTIFICATE_SCREEN,
            SECURE_PAGE,
            "/favicon.svg",
            "/licenses.txt",
        ] {
            assert!(find(needed).is_some(), "{needed}");
        }
        assert!(find("/nope").is_none());
        assert!(find("").is_none());
    }

    #[test]
    fn every_file_has_a_type_and_a_body() {
        for f in FILES {
            assert!(f.path.starts_with('/'), "{}", f.path);
            assert!(!f.path.contains(".."), "{}", f.path);
            assert!(!f.content_type.is_empty(), "{}", f.path);
            assert!(!f.body.is_empty(), "{}", f.path);
        }
    }

    #[test]
    fn the_policy_allows_nothing_but_the_node() {
        assert!(!CSP.contains("unsafe"));
        assert!(!CSP.contains("http"));
        assert!(!CSP.contains('*'));
        assert!(!CSP.contains("data:"));
        assert!(CSP.starts_with("default-src 'none';"));
    }
}
