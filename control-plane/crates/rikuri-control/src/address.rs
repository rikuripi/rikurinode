//! The node's LAN address, followed: DHCP may give the node another one, and a
//! browser that reaches the node by its address must still get a certificate
//! naming it (stage 1 change 5c.2). The daemon looks at start, in `boot`, and
//! then every `EVERY`; the address is the source of the route to TEST-NET-1,
//! as the claim screen finds it (`console::lan_address`).
//! Record: docs/build-records/2026-11-10-5c2-names-and-mdns.md

use std::future::Future;
use std::net::IpAddr;
use std::sync::Arc;
use std::time::Duration;

use time::OffsetDateTime;
use tokio::time::MissedTickBehavior;
use tracing::{error, info};

use crate::names::Names;
use crate::state::StateDir;
use crate::tls::{self, CurrentCert};

/// How often the daemon looks at its address again.
pub const EVERY: Duration = Duration::from_secs(60);

/// Every `every`, until `stop`: asks `probe` for the address and lets
/// `tls::refresh` re-issue the server certificate if the address (or the
/// date) calls for it. A failure keeps the certificate in use, and is logged
/// each time it happens: never silent.
pub async fn follow(
    dir: StateDir,
    names: Names,
    current: Arc<CurrentCert>,
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
        match tls::refresh(&dir, &names, probe(), OffsetDateTime::now_utc(), &current) {
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
