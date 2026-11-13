//! The node's LAN address, followed: DHCP may give the node another one, and a
//! browser that reaches the node by its address must still get a certificate
//! naming it (stage 1 change 5c.2). The daemon looks at start, in `boot`, and
//! then every `EVERY`; the address is the source of the route to TEST-NET-1,
//! as the claim screen finds it (`console::lan_address`). 5c.4b-1: each look
//! also reads the node's name again, and a rename asks for a look at once.
//! Records: docs/build-records/2026-11-10-5c2-names-and-mdns.md,
//! docs/build-records/2026-11-13-5c4b1-rename-engine.md

use std::future::Future;
use std::net::IpAddr;
use std::sync::{Arc, Mutex, PoisonError};
use std::time::Duration;

use time::OffsetDateTime;
use tokio::time::MissedTickBehavior;
use tracing::{error, info};

use crate::names::LiveNames;
use crate::state::StateDir;
use crate::tls::{self, CurrentCert, ServerMeta, TlsError};

/// How often the daemon looks at its address, and its name, again.
pub const EVERY: Duration = Duration::from_secs(60);

/// What the certificate is issued for, followed: the node's names (5c.4b-1)
/// and its LAN address. One look at a time, whether a tick or a rename asks.
pub struct Follower {
    dir: StateDir,
    names: Arc<LiveNames>,
    current: Arc<CurrentCert>,
    /// The address the last look saw; a rename re-issues for it.
    lan: Mutex<Option<IpAddr>>,
}

impl Follower {
    pub fn new(
        dir: StateDir,
        names: Arc<LiveNames>,
        current: Arc<CurrentCert>,
        lan: Option<IpAddr>,
    ) -> Self {
        Self {
            dir,
            names,
            current,
            lan: Mutex::new(lan),
        }
    }

    pub fn names(&self) -> &LiveNames {
        &self.names
    }

    /// Reads the node's name again and takes `lan` as its address; lets
    /// `tls::refresh` re-issue the certificate if either calls for it.
    pub fn look(&self, lan: Option<IpAddr>) -> Result<Option<ServerMeta>, TlsError> {
        let mut last = self.lan.lock().unwrap_or_else(PoisonError::into_inner);
        *last = lan;
        self.issue(lan)
    }

    /// The same after a rename, with the address the last look saw.
    pub fn renamed(&self) -> Result<Option<ServerMeta>, TlsError> {
        let last = self.lan.lock().unwrap_or_else(PoisonError::into_inner);
        self.issue(*last)
    }

    fn issue(&self, lan: Option<IpAddr>) -> Result<Option<ServerMeta>, TlsError> {
        let names = self.names.reload();
        tls::refresh(
            &self.dir,
            &names,
            lan,
            OffsetDateTime::now_utc(),
            &self.current,
        )
    }
}

/// Every `every`, until `stop`: asks `probe` for the address and lets the
/// follower look again. A failure keeps the certificate in use, and is
/// logged each time it happens: never silent.
pub async fn follow(
    follower: Arc<Follower>,
    probe: impl Fn() -> Option<IpAddr>,
    every: Duration,
    stop: impl Future<Output = ()>,
) {
    tokio::pin!(stop);
    let mut tick = tokio::time::interval(every);
    tick.set_missed_tick_behavior(MissedTickBehavior::Delay);
    // The first tick is at once; `boot` has just issued for the address.
    tick.tick().await;
    loop {
        tokio::select! {
            () = &mut stop => return,
            _ = tick.tick() => {}
        }
        match follower.look(probe()) {
            Ok(Some(meta)) => info!(
                names = ?meta.names,
                "server certificate re-issued for the node's names and address"
            ),
            Ok(None) => {}
            Err(e) => error!(
                error = %e,
                "server certificate could not be re-issued; the one in use stays"
            ),
        }
    }
}
