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
//! loopback peer, a session for anyone else); `GET /api/hub` (5c.4a: the
//! node's UUID and what setup still needs, for a session only); `PUT
//! /api/node/name` (5c.4b-1: renames the node, for a session with its CSRF
//! token; the names the checks use and the certificate follow at once).

use std::net::SocketAddr;
use std::path::PathBuf;
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
use subtle::ConstantTimeEq;
use tracing::{error, info, warn};

use crate::address::Follower;
use crate::claim::{self, Attempt, ClaimState};
use crate::hostname::{self, NodeName};
use crate::hub;
use crate::limiter::{self, Gate, Limiter};
use crate::node_id;
use crate::owner;
use crate::password::{self, PolicyError};
use crate::session::{self, Record, Store};
use crate::state::StateDir;
use crate::status::{self, Started};
use crate::stepup::{self, Action, Grants};
use crate::trust;
use crate::ui;

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
    /// The names in force and the certificate, followed (5c.4b-1).
    pub follower: Arc<Follower>,
    pub sessions: Store,
    pub ca_pem: String,
    pub ca_fingerprint: String,
    pub https_port: u16,
    /// Where the node's name is read (5c.4a; `Config`).
    pub hostname_file: PathBuf,
    /// Where hostnamed is asked to rename the node (5c.4b-1; `Config`).
    pub bus_socket: PathBuf,
    /// Held for a whole rename: the bus's call, the names and the
    /// certificate, one rename at a time.
    rename_lock: tokio::sync::Mutex<()>,
    /// Held for a whole suggestion: one at a time, any other refused at once
    /// (the owner's choice), so no request waits in line.
    suggest_lock: tokio::sync::Mutex<()>,
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
        follower: Arc<Follower>,
        sessions: Store,
        ca_pem: String,
        ca_fingerprint: String,
        https_port: u16,
        claim_wrong_tries: u32,
        hostname_file: PathBuf,
        bus_socket: PathBuf,
    ) -> Self {
        let mut claim_limiter = Limiter::new(claim::DELAY_AFTER, claim::DELAY_CAP);
        claim_limiter.sync(claim_wrong_tries);
        App(Arc::new(Inner {
            started,
            dir,
            follower,
            sessions,
            ca_pem,
            ca_fingerprint,
            https_port,
            hostname_file,
            bus_socket,
            rename_lock: tokio::sync::Mutex::new(()),
            suggest_lock: tokio::sync::Mutex::new(()),
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
        .route("/api/hub", get(hub_handler))
        .route("/api/node/name", put(rename))
        .route("/api/node/name/suggestion", get(suggestion))
        .layer(middleware::from_fn_with_state(app.clone(), origin_check))
        // The secure page: read-only, so outside the origin check; a POST to
        // it is the method router's 405.
        .merge(ui::secure_routes())
        .layer(middleware::from_fn_with_state(app.clone(), host_check))
        .layer(middleware::map_response(no_store))
        .layer(DefaultBodyLimit::max(BODY_LIMIT))
        .with_state(app)
}

/// The plain listener's router: the CA certificate, the certificate screen
/// and its files, and a redirect for everything else. No API route exists
/// here by construction.
pub fn plain_router(app: App) -> Router {
    Router::new()
        .route("/ca.crt", get(ca_certificate))
        .merge(ui::plain_routes())
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

// Every refusal's body (5c.3b: the pages read it through its generated
// type). `retry_after_seconds` only on a 429, as before.
#[derive(Serialize)]
#[cfg_attr(test, derive(ts_rs::TS))]
struct ErrorReply {
    error: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    #[cfg_attr(test, ts(optional))]
    retry_after_seconds: Option<u64>,
}

impl ErrorReply {
    fn new(error: impl Into<String>) -> Json<Self> {
        Json(Self {
            error: error.into(),
            retry_after_seconds: None,
        })
    }
}

impl IntoResponse for Refusal {
    fn into_response(self) -> Response {
        match self {
            Refusal::Status(status, message) => (status, ErrorReply::new(message)).into_response(),
            Refusal::RetryAfter(seconds) => (
                StatusCode::TOO_MANY_REQUESTS,
                [(header::RETRY_AFTER, seconds.to_string())],
                Json(ErrorReply {
                    error: "too many tries".to_owned(),
                    retry_after_seconds: Some(seconds),
                }),
            )
                .into_response(),
            Refusal::Internal(detail) => {
                error!(error = %detail, "request failed");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    ErrorReply::new("internal error"),
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
    let allowed = header_str(req.headers(), header::HOST)
        .is_some_and(|h| app.0.follower.names().host_allowed(h));
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
            .is_some_and(|o| app.0.follower.names().origin_allowed(o));
        if !allowed {
            warn!(peer = %peer_class(&req), "mutation from an origin that is not this node refused");
            return refuse(StatusCode::FORBIDDEN, "origin is not this node").into_response();
        }
    }
    next.run(req).await
}

/// `no-store` on everything the TLS listener sends, refusals included,
/// unless the response set its own: only the setup pages' files do.
async fn no_store(mut response: Response) -> Response {
    response
        .headers_mut()
        .entry(header::CACHE_CONTROL)
        .or_insert(HeaderValue::from_static("no-store"));
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
#[cfg_attr(test, derive(ts_rs::TS))]
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
#[cfg_attr(test, derive(ts_rs::TS))]
#[serde(rename_all = "lowercase")]
enum SetupClaim {
    Done,
    Armed,
    Expired,
    Retired,
    Unarmed,
}

#[derive(Serialize)]
#[cfg_attr(test, derive(ts_rs::TS))]
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
        names: app
            .0
            .follower
            .names()
            .get()
            .iter()
            .map(str::to_owned)
            .collect(),
    }))
}

#[derive(Deserialize)]
#[cfg_attr(test, derive(ts_rs::TS))]
struct ClaimRequest {
    #[cfg_attr(test, ts(type = "string"))]
    code: SecretBox<String>,
    #[cfg_attr(test, ts(type = "string"))]
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
            // 5c.4a: the node's UUID, before it has an owner: a failure here
            // refuses the claim with nothing changed. Made once; a later
            // call returns the same one.
            node_id::ensure(&dir, now).map_err(internal)?;
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
#[cfg_attr(test, derive(ts_rs::TS))]
struct SignInRequest {
    #[cfg_attr(test, ts(type = "string"))]
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
#[cfg_attr(test, derive(ts_rs::TS))]
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

// ---- handlers: the node's name (5c.4b-1) ---------------------------------

#[derive(Deserialize)]
struct RenameRequest {
    name: String,
}

#[derive(Serialize)]
#[cfg_attr(test, derive(ts_rs::TS))]
struct Renamed {
    name: String,
    host: String,
}

// 5c.4b-2: the first free `rikuriNN`, or none. (A plain comment: ts-rs
// copies a doc comment into the generated type.)
#[derive(Serialize)]
#[cfg_attr(test, derive(ts_rs::TS))]
struct NameSuggestion {
    name: Option<String>,
}

/// 5c.4b-2: the first of `rikuri01` to `rikuri99` that nothing on the
/// network answers, asked of resolved one at a time. One suggestion runs at
/// a time; another gets 429 at once.
async fn suggestion(
    State(app): State<App>,
    headers: HeaderMap,
) -> Result<Json<NameSuggestion>, Refusal> {
    authenticate(&app, &headers)?;
    // After the session check: without one, nothing says a check runs.
    let Ok(_one) = app.0.suggest_lock.try_lock() else {
        return Err(refuse(
            StatusCode::TOO_MANY_REQUESTS,
            "a suggestion is already being checked",
        ));
    };
    let uid = hostname::own_uid().map_err(internal)?;
    let socket = app.0.bus_socket.clone();
    let found = hostname::suggest(
        |name| {
            let socket = socket.clone();
            async move { hostname::name_answers(&socket, uid, &name, hostname::BUS_TIMEOUT).await }
        },
        hostname::SUGGEST_LIMIT,
    )
    .await;
    match found {
        Ok(name) => Ok(Json(NameSuggestion {
            name: name.map(|n| n.as_str().to_owned()),
        })),
        Err(why) => {
            error!(why = %why, "resolved could not say which names are free");
            Err(refuse(
                StatusCode::SERVICE_UNAVAILABLE,
                "the node could not check which names are free",
            ))
        }
    }
}

/// Renames the node: hostnamed sets the static name (polkit lets only this
/// service's user ask), then the names the checks use and the certificate are
/// read again from the hostname file, as the next tick would. The answer
/// says what the node is called now; until the page moves there, the
/// connection it came in on still works.
async fn rename(
    State(app): State<App>,
    headers: HeaderMap,
    Json(body): Json<RenameRequest>,
) -> Result<Json<Renamed>, Refusal> {
    let auth = authenticate(&app, &headers)?;
    csrf_check(&auth, &headers)?;
    let name = NodeName::parse(&body.name)
        .map_err(|_| refuse(StatusCode::BAD_REQUEST, "not a name for the node"))?;
    let _one = app.0.rename_lock.lock().await;
    // 5c.4b-2: during setup only. A node its owner has named keeps its name.
    match std::fs::read_to_string(&app.0.hostname_file) {
        Ok(text) if hostname::first_line(&text) == Some(hub::SETUP_HOSTNAME) => {}
        Ok(_) => {
            return Err(refuse(StatusCode::CONFLICT, "the node already has a name"));
        }
        Err(e) => {
            error!(error = %e, "the hostname could not be read: no rename");
            return Err(refuse(
                StatusCode::SERVICE_UNAVAILABLE,
                "the node could not be renamed",
            ));
        }
    }
    let uid = hostname::own_uid().map_err(internal)?;
    // 5c.4b-2: never a name something on the network answers.
    match hostname::name_answers(&app.0.bus_socket, uid, &name, hostname::BUS_TIMEOUT).await {
        hostname::Lookup::Free => {}
        hostname::Lookup::Taken => {
            return Err(refuse(
                StatusCode::CONFLICT,
                "that name is already in use on this network",
            ));
        }
        hostname::Lookup::Unknown(why) => {
            error!(why = %why, name = %name, "resolved could not say whether the name is free: no rename");
            return Err(refuse(
                StatusCode::SERVICE_UNAVAILABLE,
                "the node could not be renamed",
            ));
        }
    }
    if let Err(e) =
        hostname::set_static_hostname(&app.0.bus_socket, uid, &name, hostname::BUS_TIMEOUT).await
    {
        error!(error = %e, name = %name, "the node could not be renamed");
        return Err(refuse(
            StatusCode::SERVICE_UNAVAILABLE,
            "the node could not be renamed",
        ));
    }
    let follower = app.0.follower.clone();
    let issued = tokio::task::spawn_blocking(move || follower.renamed())
        .await
        .map_err(internal)?;
    if !app
        .0
        .follower
        .names()
        .get()
        .iter()
        .any(|n| n == name.local())
    {
        error!(name = %name, "renamed, but the hostname file names another node name");
        return Err(refuse(
            StatusCode::SERVICE_UNAVAILABLE,
            "the node could not be renamed",
        ));
    }
    if let Err(e) = issued {
        error!(error = %e, name = %name, "renamed, but the certificate was not renewed for the new name; the next look tries again");
        return Err(refuse(
            StatusCode::SERVICE_UNAVAILABLE,
            "the node was renamed, but its certificate was not renewed",
        ));
    }
    info!(name = %name, "the node was renamed");
    Ok(Json(Renamed {
        host: name.local(),
        name: name.as_str().to_owned(),
    }))
}

/// 5c.4a: the SetupHub, read from the node's state on each request.
async fn hub_handler(
    State(app): State<App>,
    headers: HeaderMap,
) -> Result<Json<hub::HubReport>, Refusal> {
    authenticate(&app, &headers)?;
    let dir = &app.0.dir;
    // A node claimed with 5c.4a has one already. One claimed before it, or
    // whose file was lost, gets it here, and `ensure` logs that it made one.
    // A file that is not a UUID stays an error.
    let node_id = node_id::ensure(dir, now_unix()).map_err(internal)?;
    let hostname = std::fs::read_to_string(&app.0.hostname_file);
    if let Err(e) = &hostname {
        warn!(error = %e, "the hostname could not be read: the name step is unknown");
    }
    Ok(Json(hub::report(node_id, owner::exists(dir), &hostname)))
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

    /// D23: the UI's types are generated from these (ts-rs). The committed
    /// files must be exactly what ts-rs makes of them, so a renamed field
    /// fails here, and the UI's type check fails on the code that read it.
    /// This test only compares; it never writes.
    #[test]
    fn the_ui_types_are_the_rust_types() {
        use ts_rs::TS;
        // 5c.3b: the session's times are JSON numbers, so u64 is `number`
        // here (ts-rs's default is `bigint`, which the environment can also
        // set; set here, it is the same in every build).
        let cfg = ts_rs::Config::new().with_large_int("number");
        let dir = std::path::Path::new(env!("RIKURI_UI_DIR")).join("src/generated");
        for (file, ts) in [
            ("SetupClaim.ts", SetupClaim::export_to_string(&cfg).unwrap()),
            (
                "SetupReport.ts",
                SetupReport::export_to_string(&cfg).unwrap(),
            ),
            (
                "ClaimRequest.ts",
                ClaimRequest::export_to_string(&cfg).unwrap(),
            ),
            (
                "SignInRequest.ts",
                SignInRequest::export_to_string(&cfg).unwrap(),
            ),
            (
                "SessionOpened.ts",
                SessionOpened::export_to_string(&cfg).unwrap(),
            ),
            (
                "SessionInfo.ts",
                SessionInfo::export_to_string(&cfg).unwrap(),
            ),
            ("ErrorReply.ts", ErrorReply::export_to_string(&cfg).unwrap()),
            // 5c.4a: the SetupHub.
            (
                "SetupStep.ts",
                crate::hub::SetupStep::export_to_string(&cfg).unwrap(),
            ),
            (
                "StepState.ts",
                crate::hub::StepState::export_to_string(&cfg).unwrap(),
            ),
            (
                "HubStep.ts",
                crate::hub::HubStep::export_to_string(&cfg).unwrap(),
            ),
            (
                "HubReport.ts",
                crate::hub::HubReport::export_to_string(&cfg).unwrap(),
            ),
            // 5c.4b-2: naming the node.
            ("Renamed.ts", Renamed::export_to_string(&cfg).unwrap()),
            (
                "NameSuggestion.ts",
                NameSuggestion::export_to_string(&cfg).unwrap(),
            ),
        ] {
            let committed = std::fs::read_to_string(dir.join(file)).unwrap_or_default();
            assert_eq!(
                committed, ts,
                "ui/src/generated/{file} is not the Rust type; it must read exactly:\n{ts}"
            );
        }
    }

    /// 5c.3b: the pages read every refusal as `ErrorReply`; its JSON stays
    /// the API's as it was (B0.2), byte for byte, for each kind.
    #[tokio::test]
    async fn every_refusal_is_an_error_reply_as_before() {
        use http_body_util::BodyExt;
        async fn body(r: Refusal) -> (StatusCode, String) {
            let response = r.into_response();
            let status = response.status();
            let bytes = response.into_body().collect().await.unwrap().to_bytes();
            (status, String::from_utf8(bytes.to_vec()).unwrap())
        }
        assert_eq!(
            body(refuse(StatusCode::UNAUTHORIZED, "claim refused")).await,
            (
                StatusCode::UNAUTHORIZED,
                r#"{"error":"claim refused"}"#.to_owned()
            )
        );
        assert_eq!(
            body(Refusal::RetryAfter(7)).await,
            (
                StatusCode::TOO_MANY_REQUESTS,
                r#"{"error":"too many tries","retry_after_seconds":7}"#.to_owned()
            )
        );
        assert_eq!(
            body(internal("a detail that never reaches the client")).await,
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                r#"{"error":"internal error"}"#.to_owned()
            )
        );
    }

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
