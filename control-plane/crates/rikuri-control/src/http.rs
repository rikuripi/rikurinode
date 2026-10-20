//! The HTTP surface. Two routers: the API, served over TLS by `serve`, and the
//! plain router, which serves only the CA certificate and a redirect to HTTPS
//! (D10: the first screen, reached over plain HTTP, offers the certificate).
//! Every request's `Host` must be this node (421 otherwise); every mutation's
//! `Origin` too (403); every API response is `no-store`.
//!
//! Routes: `GET /api/setup` (public: claimed or not, the claim's state, the
//! CA's fingerprint); `POST /api/claim` (the code and the first password);
//! `POST`, `GET`, `DELETE /api/session` (sign in, read, sign out);
//! `POST /api/step-up` (the password again, for one action); `PUT
//! /api/owner/password` (needs a step-up); `GET /api/status` (open to a
//! loopback peer, a session for anyone else).

use std::net::SocketAddr;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use axum::extract::{DefaultBodyLimit, Extension, Request, State};
use axum::http::{HeaderMap, HeaderValue, Method, StatusCode, header};
use axum::middleware::{self, Next};
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post, put};
use axum::{Json, Router};
use secrecy::{ExposeSecret, SecretBox};
use serde::{Deserialize, Serialize};
use serde_json::json;
use subtle::ConstantTimeEq;
use tracing::{error, info, warn};

use crate::claim::{self, Attempt, ClaimState};
use crate::limiter::{self, Gate, Limiter};
use crate::names::Names;
use crate::owner;
use crate::password::{self, PolicyError};
use crate::session::{self, Record, Store};
use crate::state::StateDir;
use crate::status::{self, Started};
use crate::stepup::{self, Action, Grants};
use crate::trust;

/// JSON bodies above this are refused before they are read.
pub const BODY_LIMIT: usize = 16 * 1024;
/// Wrong passwords before the sign-in limiter starts delaying, and its cap.
pub const SIGNIN_DELAY_AFTER: u32 = 5;
pub const SIGNIN_DELAY_CAP: Duration = Duration::from_secs(300);

/// The peer's address, attached to every request by the accept loop.
#[derive(Clone, Copy, Debug)]
pub struct Peer(pub SocketAddr);

pub struct Inner {
    pub started: Started,
    pub dir: StateDir,
    pub names: Names,
    pub sessions: Store,
    pub ca_pem: String,
    pub ca_fingerprint: String,
    pub https_port: u16,
    /// Held for the whole of a claim attempt, so claims are judged one at a
    /// time and the limiter's count is exact.
    claim_limiter: tokio::sync::Mutex<Limiter>,
    /// The same for sign-in and step-up: every password try passes here.
    signin_limiter: tokio::sync::Mutex<Limiter>,
    grants: Mutex<Grants>,
}

#[derive(Clone)]
pub struct App(pub Arc<Inner>);

impl App {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        started: Started,
        dir: StateDir,
        names: Names,
        sessions: Store,
        ca_pem: String,
        ca_fingerprint: String,
        https_port: u16,
        claim_wrong_tries: u32,
    ) -> Self {
        let mut claim_limiter = Limiter::new(claim::DELAY_AFTER, claim::DELAY_CAP);
        claim_limiter.sync(claim_wrong_tries);
        App(Arc::new(Inner {
            started,
            dir,
            names,
            sessions,
            ca_pem,
            ca_fingerprint,
            https_port,
            claim_limiter: tokio::sync::Mutex::new(claim_limiter),
            signin_limiter: tokio::sync::Mutex::new(Limiter::new(
                SIGNIN_DELAY_AFTER,
                SIGNIN_DELAY_CAP,
            )),
            grants: Mutex::new(Grants::default()),
        }))
    }
}

/// The API, served over TLS.
pub fn api_router(app: App) -> Router {
    Router::new()
        .route("/api/setup", get(setup))
        .route("/api/claim", post(claim_handler))
        .route(
            "/api/session",
            post(sign_in).get(session_get).delete(sign_out),
        )
        .route("/api/step-up", post(step_up))
        .route("/api/owner/password", put(change_password))
        .route("/api/status", get(status_handler))
        .layer(middleware::from_fn_with_state(app.clone(), origin_check))
        .layer(middleware::from_fn_with_state(app.clone(), host_check))
        .layer(middleware::map_response(no_store))
        .layer(DefaultBodyLimit::max(BODY_LIMIT))
        .with_state(app)
}

/// The plain listener's router: the CA certificate, and a redirect for
/// everything else. No API route exists here by construction.
pub fn plain_router(app: App) -> Router {
    Router::new()
        .route("/ca.crt", get(ca_certificate))
        .fallback(redirect_to_https)
        .layer(middleware::from_fn_with_state(app.clone(), host_check))
        .with_state(app)
}

// ---- refusals ------------------------------------------------------------

enum Refusal {
    Status(StatusCode, String),
    RetryAfter(u64),
    /// Logged with its detail; the response says only that it failed.
    Internal(String),
}

fn refuse(status: StatusCode, message: &str) -> Refusal {
    Refusal::Status(status, message.to_owned())
}

fn internal(e: impl std::fmt::Display) -> Refusal {
    Refusal::Internal(e.to_string())
}

fn policy_refusal(e: PolicyError) -> Refusal {
    Refusal::Status(StatusCode::UNPROCESSABLE_ENTITY, e.to_string())
}

impl IntoResponse for Refusal {
    fn into_response(self) -> Response {
        match self {
            Refusal::Status(status, message) => {
                (status, Json(json!({ "error": message }))).into_response()
            }
            Refusal::RetryAfter(seconds) => (
                StatusCode::TOO_MANY_REQUESTS,
                [(header::RETRY_AFTER, seconds.to_string())],
                Json(json!({ "error": "too many tries", "retry_after_seconds": seconds })),
            )
                .into_response(),
            Refusal::Internal(detail) => {
                error!(error = %detail, "request failed");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    Json(json!({ "error": "internal error" })),
                )
                    .into_response()
            }
        }
    }
}

// ---- middleware ----------------------------------------------------------

fn header_str(headers: &HeaderMap, name: header::HeaderName) -> Option<&str> {
    headers.get(name).and_then(|v| v.to_str().ok())
}

fn peer_class(req: &Request) -> String {
    req.extensions().get::<Peer>().map_or_else(
        || "unknown".to_owned(),
        |Peer(addr)| trust::classify(addr.ip()).to_string(),
    )
}

async fn host_check(State(app): State<App>, req: Request, next: Next) -> Response {
    let allowed =
        header_str(req.headers(), header::HOST).is_some_and(|h| app.0.names.host_allowed(h));
    if !allowed {
        warn!(peer = %peer_class(&req), "request for a host that is not this node refused");
        return refuse(StatusCode::MISDIRECTED_REQUEST, "host is not this node").into_response();
    }
    next.run(req).await
}

async fn origin_check(State(app): State<App>, req: Request, next: Next) -> Response {
    let mutation = matches!(
        *req.method(),
        Method::POST | Method::PUT | Method::DELETE | Method::PATCH
    );
    if mutation {
        let allowed = header_str(req.headers(), header::ORIGIN)
            .is_some_and(|o| app.0.names.origin_allowed(o));
        if !allowed {
            warn!(peer = %peer_class(&req), "mutation from an origin that is not this node refused");
            return refuse(StatusCode::FORBIDDEN, "origin is not this node").into_response();
        }
    }
    next.run(req).await
}

async fn no_store(mut response: Response) -> Response {
    response
        .headers_mut()
        .insert(header::CACHE_CONTROL, HeaderValue::from_static("no-store"));
    response
}

// ---- sessions ------------------------------------------------------------

fn now_unix() -> u64 {
    status::unix_now().unwrap_or(0)
}

struct Authenticated {
    id: String,
    record: Record,
}

/// The session behind the request's cookie, or 401. A sessions file that
/// cannot be read admits nobody.
fn authenticate(app: &App, headers: &HeaderMap) -> Result<Authenticated, Refusal> {
    let id = headers
        .get_all(header::COOKIE)
        .iter()
        .filter_map(|v| v.to_str().ok())
        .find_map(session::cookie_value)
        .ok_or_else(|| refuse(StatusCode::UNAUTHORIZED, "sign-in required"))?;
    match app.0.sessions.verify(id, now_unix()) {
        Ok(Some(record)) => Ok(Authenticated {
            id: id.to_owned(),
            record,
        }),
        Ok(None) => Err(refuse(StatusCode::UNAUTHORIZED, "sign-in required")),
        Err(e) => {
            warn!(error = %e, "sessions unreadable: admitting nobody");
            Err(refuse(StatusCode::UNAUTHORIZED, "sign-in required"))
        }
    }
}

fn csrf_check(auth: &Authenticated, headers: &HeaderMap) -> Result<(), Refusal> {
    let presented = headers
        .get(session::CSRF_HEADER)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    if bool::from(presented.as_bytes().ct_eq(auth.record.csrf.as_bytes())) {
        Ok(())
    } else {
        Err(refuse(StatusCode::FORBIDDEN, "csrf token missing or wrong"))
    }
}

#[derive(Serialize)]
struct SessionOpened {
    csrf_token: String,
    issued_unix: u64,
    expires_unix: u64,
}

fn open_session(app: &App, now_unix: u64) -> Result<Response, Refusal> {
    let (id, record) = app.0.sessions.create(now_unix).map_err(internal)?;
    let cookie =
        HeaderValue::from_str(&session::set_cookie(id.expose_secret())).map_err(internal)?;
    let body = SessionOpened {
        csrf_token: record.csrf,
        issued_unix: record.issued_unix,
        expires_unix: record.expires_unix,
    };
    Ok((
        StatusCode::CREATED,
        [(header::SET_COOKIE, cookie)],
        Json(body),
    )
        .into_response())
}

async fn verify_owner_password(app: &App, password: SecretBox<String>) -> Result<bool, Refusal> {
    let dir = app.0.dir.clone();
    tokio::task::spawn_blocking(move || owner::verify_password(&dir, password.expose_secret()))
        .await
        .map_err(internal)?
        .map_err(internal)
}

// ---- handlers: setup and claim ------------------------------------------

#[derive(Serialize)]
#[serde(rename_all = "lowercase")]
enum SetupClaim {
    Done,
    Armed,
    Expired,
    Retired,
    Unarmed,
}

#[derive(Serialize)]
struct SetupReport {
    claimed: bool,
    claim: SetupClaim,
    ca_fingerprint_sha256: String,
    names: Vec<String>,
}

async fn setup(State(app): State<App>) -> Result<Json<SetupReport>, Refusal> {
    let dir = &app.0.dir;
    let claimed = owner::exists(dir);
    let claim = if claimed {
        SetupClaim::Done
    } else {
        match claim::load(dir).map_err(internal)? {
            Some(file) => match file.state(now_unix()) {
                ClaimState::Armed => SetupClaim::Armed,
                ClaimState::Expired => SetupClaim::Expired,
                ClaimState::Retired => SetupClaim::Retired,
            },
            None => SetupClaim::Unarmed,
        }
    };
    Ok(Json(SetupReport {
        claimed,
        claim,
        ca_fingerprint_sha256: app.0.ca_fingerprint.clone(),
        names: app.0.names.iter().map(str::to_owned).collect(),
    }))
}

#[derive(Deserialize)]
struct ClaimRequest {
    code: SecretBox<String>,
    password: SecretBox<String>,
}

async fn claim_handler(
    State(app): State<App>,
    peer: Option<Extension<Peer>>,
    Json(body): Json<ClaimRequest>,
) -> Result<Response, Refusal> {
    let peer = peer.map_or_else(
        || "unknown".to_owned(),
        |Extension(Peer(a))| trust::classify(a.ip()).to_string(),
    );
    let dir = app.0.dir.clone();
    if owner::exists(&dir) {
        return Err(refuse(StatusCode::CONFLICT, "already claimed"));
    }
    let mut limiter = app.0.claim_limiter.lock().await;
    let file = claim::load(&dir).map_err(internal)?;
    limiter.sync(file.as_ref().map_or(0, |f| f.wrong_tries));
    if let Gate::Blocked { retry_after } = limiter.check(Instant::now()) {
        return Err(Refusal::RetryAfter(limiter::retry_after_seconds(
            retry_after,
        )));
    }
    let now = now_unix();
    let code = body.code;
    let judged_in = dir.clone();
    let (verdict, _) =
        tokio::task::spawn_blocking(move || claim::attempt(&judged_in, code.expose_secret(), now))
            .await
            .map_err(internal)?
            .map_err(internal)?;
    match verdict {
        Attempt::Refused { counted } => {
            if counted {
                let delay = limiter.record_failure(Instant::now());
                warn!(%peer, failures = limiter.failures(), delay_seconds = delay.as_secs(), "claim refused: wrong code");
            } else {
                warn!(%peer, "claim refused: no armed claim");
            }
            Err(refuse(StatusCode::UNAUTHORIZED, "claim refused"))
        }
        Attempt::Accepted => {
            let password = body.password;
            password::check_policy(password.expose_secret()).map_err(policy_refusal)?;
            let owner_in = dir.clone();
            tokio::task::spawn_blocking(move || {
                owner::set_password(&owner_in, password.expose_secret(), now)
            })
            .await
            .map_err(internal)?
            .map_err(internal)?;
            claim::finish(&dir).map_err(internal)?;
            limiter.record_success();
            info!(%peer, "node claimed: the owner's password is set");
            open_session(&app, now)
        }
    }
}

// ---- handlers: sessions --------------------------------------------------

#[derive(Deserialize)]
struct SignInRequest {
    password: SecretBox<String>,
}

async fn sign_in(
    State(app): State<App>,
    peer: Option<Extension<Peer>>,
    Json(body): Json<SignInRequest>,
) -> Result<Response, Refusal> {
    let peer = peer.map_or_else(
        || "unknown".to_owned(),
        |Extension(Peer(a))| trust::classify(a.ip()).to_string(),
    );
    let mut limiter = app.0.signin_limiter.lock().await;
    if let Gate::Blocked { retry_after } = limiter.check(Instant::now()) {
        return Err(Refusal::RetryAfter(limiter::retry_after_seconds(
            retry_after,
        )));
    }
    if !verify_owner_password(&app, body.password).await? {
        let delay = limiter.record_failure(Instant::now());
        warn!(%peer, failures = limiter.failures(), delay_seconds = delay.as_secs(), "sign-in refused");
        return Err(refuse(StatusCode::UNAUTHORIZED, "sign-in refused"));
    }
    limiter.record_success();
    info!(%peer, "owner signed in");
    open_session(&app, now_unix())
}

#[derive(Serialize)]
struct SessionInfo {
    csrf_token: String,
    issued_unix: u64,
    expires_unix: u64,
}

async fn session_get(
    State(app): State<App>,
    headers: HeaderMap,
) -> Result<Json<SessionInfo>, Refusal> {
    let auth = authenticate(&app, &headers)?;
    Ok(Json(SessionInfo {
        csrf_token: auth.record.csrf,
        issued_unix: auth.record.issued_unix,
        expires_unix: auth.record.expires_unix,
    }))
}

async fn sign_out(State(app): State<App>, headers: HeaderMap) -> Result<Response, Refusal> {
    let auth = authenticate(&app, &headers)?;
    csrf_check(&auth, &headers)?;
    app.0.sessions.revoke(&auth.id).map_err(internal)?;
    let cookie = HeaderValue::from_str(&session::clear_cookie()).map_err(internal)?;
    info!("owner signed out");
    Ok((StatusCode::NO_CONTENT, [(header::SET_COOKIE, cookie)]).into_response())
}

// ---- handlers: step-up and the password ---------------------------------

#[derive(Deserialize)]
struct StepUpRequest {
    password: SecretBox<String>,
    method: String,
    path: String,
}

#[derive(Serialize)]
struct StepUpGranted {
    token: String,
    expires_in_seconds: u64,
    bound_to: Action,
}

async fn step_up(
    State(app): State<App>,
    headers: HeaderMap,
    Json(body): Json<StepUpRequest>,
) -> Result<(StatusCode, Json<StepUpGranted>), Refusal> {
    let auth = authenticate(&app, &headers)?;
    csrf_check(&auth, &headers)?;
    let mut limiter = app.0.signin_limiter.lock().await;
    if let Gate::Blocked { retry_after } = limiter.check(Instant::now()) {
        return Err(Refusal::RetryAfter(limiter::retry_after_seconds(
            retry_after,
        )));
    }
    if !verify_owner_password(&app, body.password).await? {
        let delay = limiter.record_failure(Instant::now());
        warn!(
            failures = limiter.failures(),
            delay_seconds = delay.as_secs(),
            "step-up refused: wrong password"
        );
        return Err(refuse(StatusCode::UNAUTHORIZED, "password refused"));
    }
    limiter.record_success();
    drop(limiter);
    let action = Action::normalize(&body.method, &body.path);
    let token = app
        .0
        .grants
        .lock()
        .map_err(|_| internal("step-up grants unavailable"))?
        .issue(action.clone(), &auth.record.id_sha256, Instant::now())
        .map_err(internal)?;
    info!(method = %action.method, path = %action.path, "step-up granted for one action");
    Ok((
        StatusCode::CREATED,
        Json(StepUpGranted {
            token,
            expires_in_seconds: stepup::LIFETIME.as_secs(),
            bound_to: action,
        }),
    ))
}

#[derive(Deserialize)]
struct PasswordChange {
    password: SecretBox<String>,
}

async fn change_password(
    State(app): State<App>,
    headers: HeaderMap,
    Json(body): Json<PasswordChange>,
) -> Result<Response, Refusal> {
    let auth = authenticate(&app, &headers)?;
    csrf_check(&auth, &headers)?;
    password::check_policy(body.password.expose_secret()).map_err(policy_refusal)?;
    let token = headers
        .get(stepup::HEADER)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    let action = Action::normalize("PUT", "/api/owner/password");
    let granted = app
        .0
        .grants
        .lock()
        .map_err(|_| internal("step-up grants unavailable"))?
        .consume(token, &action, &auth.record.id_sha256, Instant::now());
    if !granted {
        warn!("password change refused: no step-up for this action");
        return Err(refuse(StatusCode::FORBIDDEN, "step-up required"));
    }
    let dir = app.0.dir.clone();
    let now = now_unix();
    let password = body.password;
    tokio::task::spawn_blocking(move || owner::set_password(&dir, password.expose_secret(), now))
        .await
        .map_err(internal)?
        .map_err(internal)?;
    let revoked = app
        .0
        .sessions
        .revoke_others(&auth.record.id_sha256)
        .map_err(internal)?;
    info!(
        revoked,
        "owner password changed; the other sessions revoked"
    );
    Ok(StatusCode::NO_CONTENT.into_response())
}

// ---- handlers: status ----------------------------------------------------

async fn status_handler(
    State(app): State<App>,
    peer: Option<Extension<Peer>>,
    headers: HeaderMap,
) -> Result<Json<status::Report>, Refusal> {
    let loopback =
        peer.is_some_and(|Extension(Peer(addr))| trust::classify(addr.ip()).is_loopback());
    if !loopback {
        authenticate(&app, &headers)?;
    }
    Ok(Json(status::report(app.0.started)))
}

// ---- the plain router ----------------------------------------------------

async fn ca_certificate(State(app): State<App>) -> Response {
    (
        StatusCode::OK,
        [
            (header::CONTENT_TYPE, "application/x-x509-ca-cert"),
            (
                header::CONTENT_DISPOSITION,
                "attachment; filename=\"rikuri-node-ca.crt\"",
            ),
            (header::CACHE_CONTROL, "no-store"),
        ],
        app.0.ca_pem.clone(),
    )
        .into_response()
}

/// The host part of a `Host` value, without the port, as a URL authority
/// (`[::1]` keeps its brackets).
fn authority_host(host: &str) -> &str {
    let host = host.trim();
    if host.starts_with('[') {
        return host.find(']').map_or(host, |end| &host[..=end]);
    }
    match host.rsplit_once(':') {
        Some((name, _)) if !name.contains(':') => name,
        _ => host,
    }
}

async fn redirect_to_https(State(app): State<App>, req: Request) -> Response {
    let host = header_str(req.headers(), header::HOST).map_or("localhost", authority_host);
    let authority = if app.0.https_port == 443 {
        host.to_owned()
    } else {
        format!("{host}:{}", app.0.https_port)
    };
    let path = req.uri().path_and_query().map_or("/", |p| p.as_str());
    let location = format!("https://{authority}{path}");
    match HeaderValue::from_str(&location) {
        Ok(value) => (StatusCode::PERMANENT_REDIRECT, [(header::LOCATION, value)]).into_response(),
        Err(_) => StatusCode::BAD_REQUEST.into_response(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_authority_keeps_the_host_and_drops_the_port() {
        assert_eq!(authority_host("localhost:80"), "localhost");
        assert_eq!(authority_host("localhost"), "localhost");
        assert_eq!(authority_host("[::1]:80"), "[::1]");
        assert_eq!(authority_host("[::1]"), "[::1]");
        assert_eq!(authority_host("192.168.1.5:8080"), "192.168.1.5");
        assert_eq!(
            authority_host("a:b:c"),
            "a:b:c",
            "several colons: not a port"
        );
        assert_eq!(authority_host(" localhost:80 "), "localhost");
    }

    #[test]
    fn a_request_body_never_shows_its_secrets_in_debug_form() {
        let body: ClaimRequest =
            serde_json::from_str(r#"{"code":"K7QM-4XD9-TR","password":"hunter2hunter2"}"#).unwrap();
        let shown = format!("{:?} {:?}", body.code, body.password);
        assert!(
            !shown.contains("K7QM") && !shown.contains("hunter2"),
            "{shown}"
        );
        assert_eq!(body.code.expose_secret(), "K7QM-4XD9-TR");
    }
}
