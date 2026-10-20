//! A node for the tests: booted through the real composition, listening on
//! real loopback sockets (TLS and plain), driven by a hand-written HTTP/1.1
//! client whose TLS trusts the node's CA, or deliberately does not.

#![allow(dead_code, clippy::unwrap_used, clippy::expect_used)]

use std::io;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicU32, Ordering};

use rikuri_control::boot::{self, Booted};
use rikuri_control::config::Config;
use rikuri_control::names::Names;
use rikuri_control::status::Started;
use rikuri_control::{api_router, plain_router, serve_plain, serve_tls};
use rustls::{ClientConfig, RootCertStore};
use rustls_pki_types::{CertificateDer, ServerName};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};
use tokio::task::JoinHandle;
use tokio_rustls::TlsConnector;

static COUNTER: AtomicU32 = AtomicU32::new(0);

pub struct Scratch(pub PathBuf);

impl Scratch {
    pub fn new() -> Self {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let path =
            std::env::temp_dir().join(format!("rikuri-control-it-{}-{n}", std::process::id()));
        let _ = std::fs::remove_dir_all(&path);
        Scratch(path)
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

pub fn config(
    scratch: &Scratch,
    https: SocketAddr,
    plain: Option<SocketAddr>,
    names: &[&str],
) -> Config {
    Config {
        https,
        http: plain,
        names: Names::new(names).unwrap(),
        state_dir: scratch.0.clone(),
    }
}

/// Boots over `scratch` without listening: for router-level tests.
pub fn boot_only(scratch: &Scratch) -> Booted {
    let config = config(
        scratch,
        "127.0.0.1:8443".parse().unwrap(),
        None,
        &["rikuri01.local"],
    );
    boot::boot(&config, Started::now()).unwrap()
}

pub struct Node {
    pub scratch: Scratch,
    pub booted: Booted,
    pub https: SocketAddr,
    pub plain: SocketAddr,
    stop: tokio::sync::watch::Sender<bool>,
    tasks: Vec<JoinHandle<io::Result<()>>>,
}

impl Node {
    pub async fn start() -> Node {
        Node::start_over(Scratch::new()).await
    }

    /// Boots over an existing state folder: a restart.
    pub async fn start_over(scratch: Scratch) -> Node {
        let https_listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let plain_listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let https = https_listener.local_addr().unwrap();
        let plain = plain_listener.local_addr().unwrap();
        let config = config(&scratch, https, Some(plain), &["rikuri01.local"]);
        let booted = boot::boot(&config, Started::now()).unwrap();
        let (stop, stopped) = tokio::sync::watch::channel(false);
        let wait = |mut rx: tokio::sync::watch::Receiver<bool>| async move {
            let _ = rx.changed().await;
        };
        let api = tokio::spawn(serve_tls(
            https_listener,
            booted.identity.config.clone(),
            api_router(booted.app.clone()),
            wait(stopped.clone()),
        ));
        let redirect = tokio::spawn(serve_plain(
            plain_listener,
            plain_router(booted.app.clone()),
            wait(stopped),
        ));
        Node {
            scratch,
            booted,
            https,
            plain,
            stop,
            tasks: vec![api, redirect],
        }
    }

    pub fn ca_der(&self) -> Vec<u8> {
        self.booted.identity.ca_der.clone()
    }

    /// The claim code this boot armed, as the console shows it.
    pub fn claim_code(&self) -> String {
        self.booted
            .armed
            .as_ref()
            .expect("the first start arms a code")
            .formatted()
    }

    pub async fn stop(self) -> Scratch {
        let _ = self.stop.send(true);
        for task in self.tasks {
            task.await.unwrap().unwrap();
        }
        self.scratch
    }

    pub async fn restart(self) -> Node {
        let scratch = self.stop().await;
        Node::start_over(scratch).await
    }
}

pub struct Reply {
    pub status: u16,
    pub headers: Vec<(String, String)>,
    pub body: String,
}

impl Reply {
    pub fn header(&self, name: &str) -> Option<&str> {
        self.headers
            .iter()
            .find(|(k, _)| k.eq_ignore_ascii_case(name))
            .map(|(_, v)| v.as_str())
    }

    pub fn json(&self) -> serde_json::Value {
        serde_json::from_str(&self.body).unwrap_or_else(|e| panic!("{e}: {:?}", self.body))
    }

    /// The session id a `Set-Cookie` opened.
    pub fn session_cookie(&self) -> String {
        let set = self.header("set-cookie").expect("a Set-Cookie header");
        set.strip_prefix("rikuri_session=")
            .and_then(|rest| rest.split(';').next())
            .unwrap()
            .to_owned()
    }
}

pub fn parse(raw: &[u8]) -> Reply {
    let text = String::from_utf8_lossy(raw);
    let (head, body) = text.split_once("\r\n\r\n").unwrap_or((&text, ""));
    let mut lines = head.lines();
    let status_line = lines.next().unwrap_or("");
    let status: u16 = status_line
        .split(' ')
        .nth(1)
        .and_then(|s| s.parse().ok())
        .unwrap_or(0);
    let headers = lines
        .filter_map(|l| l.split_once(':'))
        .map(|(k, v)| (k.trim().to_owned(), v.trim().to_owned()))
        .collect();
    Reply {
        status,
        headers,
        body: body.to_owned(),
    }
}

pub struct Req {
    pub method: &'static str,
    pub path: String,
    pub headers: Vec<(String, String)>,
    pub body: Option<String>,
    pub trust_ca: bool,
}

impl Req {
    pub fn new(method: &'static str, path: &str) -> Self {
        Req {
            method,
            path: path.to_owned(),
            headers: Vec::new(),
            body: None,
            trust_ca: true,
        }
    }

    pub fn get(path: &str) -> Self {
        Req::new("GET", path)
    }

    pub fn delete(path: &str) -> Self {
        Req::new("DELETE", path).origin()
    }

    pub fn post(path: &str, json: serde_json::Value) -> Self {
        Req::new("POST", path).origin().json(json)
    }

    pub fn put(path: &str, json: serde_json::Value) -> Self {
        Req::new("PUT", path).origin().json(json)
    }

    pub fn json(mut self, json: serde_json::Value) -> Self {
        self.body = Some(json.to_string());
        self.header("Content-Type", "application/json")
    }

    pub fn header(mut self, name: &str, value: &str) -> Self {
        self.headers.retain(|(k, _)| !k.eq_ignore_ascii_case(name));
        self.headers.push((name.to_owned(), value.to_owned()));
        self
    }

    /// The node's own origin, as a browser on the setup page sends it.
    pub fn origin(self) -> Self {
        self.header("Origin", "https://localhost")
    }

    pub fn no_origin(mut self) -> Self {
        self.headers
            .retain(|(k, _)| !k.eq_ignore_ascii_case("origin"));
        self
    }

    pub fn cookie(self, session_id: &str) -> Self {
        self.header(
            "Cookie",
            &format!("theme=dark; rikuri_session={session_id}"),
        )
    }

    pub fn csrf(self, token: &str) -> Self {
        self.header("X-CSRF-Token", token)
    }

    pub fn step_up(self, token: &str) -> Self {
        self.header("X-Step-Up", token)
    }

    pub fn distrust_ca(mut self) -> Self {
        self.trust_ca = false;
        self
    }

    fn raw(&self, default_host: &str) -> Vec<u8> {
        let mut out = format!("{} {} HTTP/1.1\r\n", self.method, self.path);
        if !self
            .headers
            .iter()
            .any(|(k, _)| k.eq_ignore_ascii_case("host"))
        {
            out.push_str(&format!("Host: {default_host}\r\n"));
        }
        out.push_str("Connection: close\r\n");
        for (k, v) in &self.headers {
            out.push_str(&format!("{k}: {v}\r\n"));
        }
        let body = self.body.clone().unwrap_or_default();
        out.push_str(&format!("Content-Length: {}\r\n\r\n", body.len()));
        let mut bytes = out.into_bytes();
        bytes.extend_from_slice(body.as_bytes());
        bytes
    }
}

/// Sends `req` over TLS to the node's API. `Err` is a failed handshake, as a
/// browser without the CA would see it.
pub async fn https(node: &Node, req: Req) -> Result<Reply, String> {
    let mut roots = RootCertStore::empty();
    if req.trust_ca {
        roots.add(CertificateDer::from(node.ca_der())).unwrap();
    }
    let config = ClientConfig::builder()
        .with_root_certificates(roots)
        .with_no_client_auth();
    let connector = TlsConnector::from(Arc::new(config));
    let tcp = TcpStream::connect(node.https).await.unwrap();
    let name = ServerName::try_from("localhost".to_owned()).unwrap();
    let mut tls = connector
        .connect(name, tcp)
        .await
        .map_err(|e| e.to_string())?;
    tls.write_all(&req.raw(&format!("localhost:{}", node.https.port())))
        .await
        .map_err(|e| e.to_string())?;
    let mut raw = Vec::new();
    match tls.read_to_end(&mut raw).await {
        Ok(_) => {}
        Err(e) if e.kind() == io::ErrorKind::UnexpectedEof => {}
        Err(e) => return Err(e.to_string()),
    }
    if raw.is_empty() {
        return Err("no response".to_owned());
    }
    Ok(parse(&raw))
}

/// Sends `req` in the clear to the node's plain listener.
pub async fn plain(node: &Node, req: Req) -> Reply {
    let mut tcp = TcpStream::connect(node.plain).await.unwrap();
    tcp.write_all(&req.raw(&format!("localhost:{}", node.plain.port())))
        .await
        .unwrap();
    let mut raw = Vec::new();
    tcp.read_to_end(&mut raw).await.unwrap();
    parse(&raw)
}

pub async fn ok(node: &Node, req: Req) -> Reply {
    https(node, req).await.unwrap()
}

/// Claims the node with its armed code and `password`; returns the reply.
pub async fn claim(node: &Node, password: &str) -> Reply {
    let code = node.claim_code();
    ok(
        node,
        Req::post(
            "/api/claim",
            serde_json::json!({ "code": code, "password": password }),
        ),
    )
    .await
}

pub const PASSWORD: &str = "correct horse battery staple";
