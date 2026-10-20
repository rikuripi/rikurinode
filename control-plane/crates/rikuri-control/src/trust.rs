//! Peer trust, decided in one place (EXEC-07, register port 19): loopback,
//! link-local, private or public, for IPv4 and IPv6 in every form the previous
//! node got wrong, including the Mac that reached it over IPv6 link-local and
//! was rate-limited by a helper that knew only IPv4 (2026-09-14).
//!
//! What the control plane does with the class: a loopback peer reads the
//! status route without a session (greenboot's checks and the console ask it
//! there, plan §4.1); every other peer needs a session, a LAN peer included
//! (EXEC-02: every LAN client is untrusted). Refusals are logged with the
//! class. No proxy sits in front of the control plane, which terminates TLS
//! itself, so the peer address is the socket's own; a loopback source behind a
//! proxy would never be trusted (EXEC-07).

use std::fmt;
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};

use serde::Serialize;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
pub enum Trust {
    /// 127.0.0.0/8 or ::1: a process on the node itself.
    Loopback,
    /// 169.254.0.0/16 or fe80::/10: the same link, no router between.
    LinkLocal,
    /// RFC 1918 or fc00::/7: the owner's network, still untrusted for the API.
    Private,
    /// Everything else, the shared 100.64.0.0/10 range included: no remote
    /// path exists yet, so nothing in it is special.
    Public,
}

impl Trust {
    pub fn is_loopback(self) -> bool {
        self == Trust::Loopback
    }
}

impl fmt::Display for Trust {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Trust::Loopback => "loopback",
            Trust::LinkLocal => "link-local",
            Trust::Private => "private",
            Trust::Public => "public",
        })
    }
}

/// The class of a peer address. An IPv4 address carried in IPv6
/// (`::ffff:a.b.c.d`, how a dual-stack socket reports an IPv4 peer) is
/// classified as that IPv4 address.
pub fn classify(ip: IpAddr) -> Trust {
    match ip {
        IpAddr::V4(v4) => classify_v4(v4),
        IpAddr::V6(v6) => match v6.to_ipv4_mapped() {
            Some(v4) => classify_v4(v4),
            None => classify_v6(v6),
        },
    }
}

fn classify_v4(ip: Ipv4Addr) -> Trust {
    if ip.is_loopback() {
        Trust::Loopback
    } else if ip.is_link_local() {
        Trust::LinkLocal
    } else if ip.is_private() {
        Trust::Private
    } else {
        Trust::Public
    }
}

fn classify_v6(ip: Ipv6Addr) -> Trust {
    if ip.is_loopback() {
        Trust::Loopback
    } else if ip.is_unicast_link_local() {
        Trust::LinkLocal
    } else if ip.is_unique_local() {
        Trust::Private
    } else {
        Trust::Public
    }
}

#[cfg(test)]
mod tests {
    use super::Trust::{LinkLocal, Loopback, Private, Public};
    use super::*;

    fn class(s: &str) -> Trust {
        classify(s.parse().unwrap_or_else(|e| panic!("{s}: {e}")))
    }

    #[test]
    fn the_table_of_the_previous_nodes_incidents() {
        // The Mac that macOS put on IPv6 link-local for a .local name (2026-09-14).
        assert_eq!(class("fe80::182f:212:5192:1bbd"), LinkLocal);
        assert_eq!(class("fe80::1"), LinkLocal);
        assert_eq!(class("fd12:3456:789a::1"), Private);
        assert_eq!(class("fc00::1"), Private);
        assert_eq!(class("::1"), Loopback);
        assert_eq!(class("127.0.0.1"), Loopback);
        assert_eq!(class("127.1.2.3"), Loopback);
        assert_eq!(class("192.168.68.61"), Private);
        assert_eq!(class("10.0.0.5"), Private);
        assert_eq!(class("172.18.0.1"), Private);
        assert_eq!(class("172.31.255.255"), Private);
        assert_eq!(class("172.32.0.1"), Public);
        assert_eq!(class("169.254.169.254"), LinkLocal);
        assert_eq!(class("8.8.8.8"), Public);
        assert_eq!(class("2001:4860:4860::8888"), Public);
    }

    #[test]
    fn the_shared_range_is_public_until_a_remote_path_exists() {
        // 100.64.0.0/10 (the previous node trusted it for Tailscale): no such
        // path exists in this node yet, so nothing in it is special.
        assert_eq!(class("100.123.157.110"), Public);
    }

    #[test]
    fn ipv4_carried_in_ipv6_is_classified_as_the_ipv4() {
        assert_eq!(class("::ffff:127.0.0.1"), Loopback);
        assert_eq!(class("::ffff:192.168.1.5"), Private);
        assert_eq!(class("::ffff:169.254.1.1"), LinkLocal);
        assert_eq!(class("::ffff:8.8.8.8"), Public);
    }

    #[test]
    fn unspecified_and_deprecated_site_local_are_public() {
        assert_eq!(class("0.0.0.0"), Public);
        assert_eq!(class("::"), Public);
        assert_eq!(class("fec0::1"), Public);
    }

    #[test]
    fn only_loopback_is_loopback() {
        assert!(Loopback.is_loopback());
        for other in [LinkLocal, Private, Public] {
            assert!(!other.is_loopback(), "{other}");
        }
    }

    #[test]
    fn the_class_serializes_in_kebab_case() {
        assert_eq!(serde_json::to_value(LinkLocal).unwrap(), "link-local");
        assert_eq!(serde_json::to_value(Loopback).unwrap(), "loopback");
        assert_eq!(Private.to_string(), "private");
    }
}
