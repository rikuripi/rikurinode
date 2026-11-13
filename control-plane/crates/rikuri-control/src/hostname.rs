//! The node's name, and the one call that changes it (5c.4b-1).
//! RED STUB: the public surface only; every answer is wrong.
//! Record: docs/build-records/2026-11-13-5c4b1-rename-engine.md

use std::fmt;
use std::io;
use std::path::Path;
use std::time::Duration;

pub const BUS_SOCKET: &str = "/run/dbus/system_bus_socket";
pub const BUS_TIMEOUT: Duration = Duration::from_secs(10);
pub const MAX_MESSAGE: usize = 64 * 1024;
pub const MAX_READ: usize = 4 * MAX_MESSAGE;
pub const HELLO_SERIAL: u32 = 1;
pub const CALL_SERIAL: u32 = 2;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NodeName(String);

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NotAName;

impl fmt::Display for NotAName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("not a name for the node")
    }
}

impl std::error::Error for NotAName {}

impl NodeName {
    pub fn parse(_raw: &str) -> Result<Self, NotAName> {
        Err(NotAName)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }

    pub fn local(&self) -> String {
        self.0.clone()
    }
}

impl fmt::Display for NodeName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

pub fn first_line(_text: &str) -> Option<&str> {
    None
}

pub fn name_in(_text: &str) -> Option<NodeName> {
    None
}

pub fn own_uid() -> io::Result<u32> {
    Ok(u32::MAX)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Kind {
    Call,
    Return,
    Error,
    Signal,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Message {
    pub kind: Kind,
    pub serial: u32,
    pub reply_serial: Option<u32>,
    pub error_name: Option<String>,
}

#[derive(Debug)]
pub enum BusError {
    Unreachable(io::Error),
    Io(io::Error),
    Auth(String),
    Denied(String),
    Refused(String),
    Protocol(&'static str),
    TimedOut,
}

impl fmt::Display for BusError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}

impl std::error::Error for BusError {}

pub fn auth_line(_uid: u32) -> Vec<u8> {
    Vec::new()
}

pub fn hello(_serial: u32) -> Vec<u8> {
    Vec::new()
}

pub fn set_static_hostname_call(_name: &NodeName, _serial: u32) -> Vec<u8> {
    Vec::new()
}

pub fn parse_message(_buf: &[u8]) -> Result<Option<(Message, usize)>, BusError> {
    Err(BusError::Protocol("a red stub"))
}

pub async fn set_static_hostname(
    _socket: &Path,
    _uid: u32,
    _name: &NodeName,
    _limit: Duration,
) -> Result<(), BusError> {
    Err(BusError::Protocol("a red stub"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::MetadataExt;

    fn le(n: u32) -> [u8; 4] {
        n.to_le_bytes()
    }

    fn cat(parts: &[&[u8]]) -> Vec<u8> {
        parts.concat()
    }

    #[test]
    fn a_name_is_one_label_lower_cased() {
        let long = "a".repeat(63);
        for good in ["rikuri01", "a", "node-2", "0rikuri", "123", long.as_str()] {
            assert_eq!(NodeName::parse(good).unwrap().as_str(), good);
        }
        assert_eq!(NodeName::parse("RikuRi01").unwrap().as_str(), "rikuri01");
        assert_eq!(
            NodeName::parse("rikuri01").unwrap().local(),
            "rikuri01.local"
        );
    }

    #[test]
    fn anything_else_is_not_a_name() {
        let long = "a".repeat(64);
        for bad in [
            "",
            " rikuri01",
            "rikuri01 ",
            "rikuri01\n",
            "rikuri.local",
            "rikuri01.",
            "-rikuri",
            "rikuri-",
            "-",
            "riku_ri",
            "ríkuri",
            "rikuri01:443",
            "a/b",
            "localhost",
            "LocalHost",
            long.as_str(),
        ] {
            assert_eq!(NodeName::parse(bad), Err(NotAName), "{bad:?}");
        }
    }

    #[test]
    fn the_files_name_is_its_first_line_neither_blank_nor_a_comment() {
        assert_eq!(
            first_line("# a comment\n\n  rikuri02  \nother\n"),
            Some("rikuri02")
        );
        assert_eq!(first_line("\n# only a comment\n"), None);
        assert_eq!(first_line(""), None);
        assert_eq!(
            name_in("rikurisetup\n"),
            Some(NodeName::parse("rikurisetup").unwrap())
        );
        assert_eq!(name_in("Rikuri03\n").unwrap().as_str(), "rikuri03");
        assert_eq!(name_in("not a name\n"), None);
        assert_eq!(name_in("rikuri.example.org\n"), None);
    }

    #[test]
    fn the_auth_line_is_external_with_the_uids_digits_in_hex() {
        assert_eq!(auth_line(1000), b"\0AUTH EXTERNAL 31303030\r\n");
        assert_eq!(auth_line(0), b"\0AUTH EXTERNAL 30\r\n");
        assert_eq!(auth_line(978), b"\0AUTH EXTERNAL 393738\r\n");
    }

    #[test]
    fn hello_is_byte_for_byte_the_buses_own_call() {
        let want = cat(&[
            b"l\x01\x00\x01",
            &le(0),
            &le(1),
            &le(110),
            // 16: the path
            b"\x01\x01o\x00",
            &le(21),
            b"/org/freedesktop/DBus\0",
            &[0; 2],
            // 48: the destination
            b"\x06\x01s\x00",
            &le(20),
            b"org.freedesktop.DBus\0",
            &[0; 3],
            // 80: the interface
            b"\x02\x01s\x00",
            &le(20),
            b"org.freedesktop.DBus\0",
            &[0; 3],
            // 112: the member, then padding to 128 and no body
            b"\x03\x01s\x00",
            &le(5),
            b"Hello\0",
            &[0; 2],
        ]);
        assert_eq!(want.len(), 128);
        assert_eq!(hello(1), want);
    }

    #[test]
    fn set_static_hostname_is_byte_for_byte_and_never_interactive() {
        let name = NodeName::parse("rikuri01").unwrap();
        let want = cat(&[
            b"l\x01\x00\x01",
            &le(20),
            &le(2),
            &le(160),
            // 16: the path
            b"\x01\x01o\x00",
            &le(26),
            b"/org/freedesktop/hostname1\0",
            &[0; 5],
            // 56: the destination
            b"\x06\x01s\x00",
            &le(25),
            b"org.freedesktop.hostname1\0",
            &[0; 6],
            // 96: the interface
            b"\x02\x01s\x00",
            &le(25),
            b"org.freedesktop.hostname1\0",
            &[0; 6],
            // 136: the member
            b"\x03\x01s\x00",
            &le(17),
            b"SetStaticHostname\0",
            &[0; 6],
            // 168: the body's signature, ending at 176, already aligned
            b"\x08\x01g\x00",
            b"\x02sb\0",
            // 176: the body: the name, padding to 4, and false
            &le(8),
            b"rikuri01\0",
            &[0; 3],
            &le(0),
        ]);
        assert_eq!(want.len(), 196);
        assert_eq!(set_static_hostname_call(&name, 2), want);
    }

    #[test]
    fn the_bodys_padding_follows_the_names_length() {
        let call = set_static_hostname_call(&NodeName::parse("a").unwrap(), 7);
        assert_eq!(&call[4..8], &le(12), "a 1-byte name: 4 + 2 + 2 + 4");
        assert_eq!(&call[8..12], &le(7), "the serial");
        assert_eq!(call.len(), 176 + 12);
        assert_eq!(&call[176..], cat(&[&le(1), b"a\0", &[0; 2], &le(0)]));
    }

    /// A method return to serial 2, as the bus sends it: reply serial,
    /// destination and sender; no body.
    fn a_return() -> Vec<u8> {
        cat(&[
            b"l\x02\x01\x01",
            &le(0),
            &le(7),
            &le(37),
            b"\x05\x01u\x00",
            &le(2),
            b"\x06\x01s\x00",
            &le(5),
            b":1.42\0",
            &[0; 2],
            b"\x07\x01s\x00",
            &le(4),
            b":1.3\0",
            &[0; 3],
        ])
    }

    /// An error to serial 2: reply serial, error name, signature, and the
    /// message in the body.
    fn an_error() -> Vec<u8> {
        cat(&[
            b"l\x03\x01\x01",
            &le(22),
            &le(9),
            &le(63),
            b"\x05\x01u\x00",
            &le(2),
            b"\x04\x01s\x00",
            &le(39),
            b"org.freedesktop.DBus.Error.AccessDenied\0",
            b"\x08\x01g\x00",
            b"\x01s\0",
            &[0; 1],
            &le(17),
            b"Permission denied\0",
        ])
    }

    #[test]
    fn a_return_and_an_error_are_read() {
        let ret = a_return();
        assert_eq!(ret.len(), 56);
        assert_eq!(
            parse_message(&ret).unwrap(),
            Some((
                Message {
                    kind: Kind::Return,
                    serial: 7,
                    reply_serial: Some(2),
                    error_name: None
                },
                56
            ))
        );
        let err = an_error();
        assert_eq!(err.len(), 102);
        assert_eq!(
            parse_message(&err).unwrap(),
            Some((
                Message {
                    kind: Kind::Error,
                    serial: 9,
                    reply_serial: Some(2),
                    error_name: Some("org.freedesktop.DBus.Error.AccessDenied".to_owned())
                },
                102
            ))
        );
        let both = cat(&[&ret, &err]);
        let (_, used) = parse_message(&both).unwrap().unwrap();
        assert_eq!(used, 56);
        assert_eq!(
            parse_message(&both[used..]).unwrap().unwrap().0.kind,
            Kind::Error
        );
    }

    #[test]
    fn an_incomplete_message_waits_for_more() {
        let err = an_error();
        for cut in 0..err.len() {
            assert!(
                matches!(parse_message(&err[..cut]), Ok(None)),
                "cut at {cut}"
            );
        }
    }

    #[test]
    fn what_this_client_does_not_read_is_refused() {
        let ret = a_return();
        let with = |at: usize, byte: u8| {
            let mut m = ret.clone();
            m[at] = byte;
            m
        };
        let refused = |m: &[u8]| matches!(parse_message(m), Err(BusError::Protocol(_)));
        assert!(refused(&with(0, b'B')), "big-endian");
        assert!(refused(&with(1, 0)), "no type");
        assert!(refused(&with(1, 5)), "an unknown type");
        assert!(refused(&with(3, 2)), "another protocol version");
        assert!(
            refused(&with(18, b'x')),
            "a field of a type it does not read"
        );
        assert!(refused(&with(17, 2)), "a two-character field type");
        // A reply serial sent as a string.
        let as_string = cat(&[
            b"l\x02\x01\x01",
            &le(0),
            &le(7),
            &le(10),
            b"\x05\x01s\x00",
            &le(1),
            b"x\0",
            &[0; 6],
        ]);
        assert_eq!(as_string.len(), 32);
        assert!(refused(&as_string), "a reply serial that is not a u32");
        // The destination's length runs past the fields.
        let mut long = ret.clone();
        long[28..32].copy_from_slice(&le(200));
        assert!(refused(&long), "a string past the fields");
        // A missing NUL after a string.
        assert!(refused(&with(37, b'x')), "a string without its NUL");
        // An error name of the wrong type.
        let mut wrong = an_error();
        wrong[26] = b'u';
        assert!(refused(&wrong), "an error name that is a u32");
    }

    #[test]
    fn a_message_over_the_limit_is_refused_before_it_is_read() {
        let mut huge = a_return();
        huge[4..8].copy_from_slice(&le(MAX_MESSAGE as u32));
        assert!(matches!(
            parse_message(&huge[..16]),
            Err(BusError::Protocol(_))
        ));
        let mut fields = a_return();
        fields[12..16].copy_from_slice(&le(u32::MAX));
        assert!(matches!(
            parse_message(&fields[..16]),
            Err(BusError::Protocol(_))
        ));
    }

    #[test]
    fn the_uid_is_this_processes() {
        let uid = own_uid().unwrap();
        // A file this process makes is owned by its uid.
        let probe = std::env::temp_dir().join(format!("rikuri-uid-{}", std::process::id()));
        std::fs::write(&probe, b"").unwrap();
        let made = std::fs::metadata(&probe).unwrap().uid();
        let _ = std::fs::remove_file(&probe);
        assert_eq!(uid, made);
    }
}
