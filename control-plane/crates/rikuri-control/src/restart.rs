//! Why the node last restarted (D22, plan §4.1): this boot's entry, as the
//! root service `rikuri-boot-cause` wrote it under `/run` at this boot
//! (`image/rootfs/usr/libexec/rikuri/boot-cause`, `THIS_BOOT`). `/run` is
//! empty at every boot, so a file there is this boot's: no clock and no boot
//! id are compared (this daemon's sandbox cannot read the boot id, and a
//! clock may be far behind at boot). Read on each request, never kept.
//!
//! The record is the boot service's; this reads it strictly all the same.
//! Anything but exactly that entry, with a cause this code knows, is "could
//! not be read": the owner is never told a guess (lessons register EVID-02).
//! Record: docs/build-records/2026-11-19-boot-cause-sentence.md

use std::fs;
use std::io::Read;
use std::os::unix::fs::MetadataExt;
use std::path::Path;

use serde::{Deserialize, Serialize};
use tracing::warn;

/// Where the boot service writes this boot's entry; always this on a node.
pub const THIS_BOOT: &str = "/run/rikuri-boot-cause/this-boot.json";

/// The entry is under 200 bytes; anything larger is not one.
pub const MAX: u64 = 4096;

// The boot service's causes (`CAUSES`), a closed set: a `match` over them
// must name every one, and the page has a sentence for each. (`//`, not `///`:
// ts-rs copies a doc comment into the generated type.)
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(test, derive(ts_rs::TS))]
#[serde(rename_all = "kebab-case")]
pub enum RestartCause {
    KernelCrash,
    Watchdog,
    RolledBack,
    UpdateApplied,
    Clean,
    PowerCut,
    Unknown,
    FirstBoot,
}

// Why this boot happened: the cause, when this boot was recorded, and when
// the boot that ended was last known alive (a clean shutdown's time, or the
// last heartbeat), if anything says.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[cfg_attr(test, derive(ts_rs::TS))]
pub struct LastRestart {
    pub cause: RestartCause,
    pub at_unix: u64,
    pub last_alive_unix: Option<u64>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Entry {
    boot_id: String,
    at: u64,
    cause: RestartCause,
    last_alive: Option<u64>,
}

/// The boot id's form, as the kernel writes it.
fn is_boot_id(id: &str) -> bool {
    let groups: Vec<&str> = id.split('-').collect();
    groups.len() == 5
        && groups
            .iter()
            .zip([8, 4, 4, 4, 12])
            .all(|(g, n)| g.len() == n && g.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f')))
}

/// The entry's bytes as this boot's restart, or why they are not one.
pub fn parse(bytes: &[u8]) -> Result<LastRestart, String> {
    let entry: Entry =
        serde_json::from_slice(bytes).map_err(|e| format!("not this boot's entry: {e}"))?;
    if !is_boot_id(&entry.boot_id) {
        return Err("not this boot's entry: the boot id has another form".to_owned());
    }
    // What the boot service's classifier always gives (no clock comparison:
    // a clock behind at boot puts `at` before `last_alive`, and that is fine).
    let fits = match entry.cause {
        RestartCause::Clean | RestartCause::PowerCut => entry.last_alive.is_some(),
        RestartCause::FirstBoot => entry.last_alive.is_none(),
        RestartCause::KernelCrash
        | RestartCause::Watchdog
        | RestartCause::RolledBack
        | RestartCause::UpdateApplied
        | RestartCause::Unknown => true,
    };
    if !fits {
        return Err(format!(
            "not this boot's entry: {:?} with last_alive {:?}",
            entry.cause, entry.last_alive
        ));
    }
    Ok(LastRestart {
        cause: entry.cause,
        at_unix: entry.at,
        last_alive_unix: entry.last_alive,
    })
}

/// Reads the file at `path`: a regular file, not a link, at most [`MAX`]
/// bytes, and the same file once open as when looked at. Its folder is
/// root's, so nothing this daemon's user can do swaps it; the checks hold
/// anyway.
pub fn read(path: &Path) -> Result<LastRestart, String> {
    let seen = fs::symlink_metadata(path).map_err(|e| {
        if e.kind() == std::io::ErrorKind::NotFound {
            "no record of this boot: the boot service wrote none".to_owned()
        } else {
            format!("cannot be read: {e}")
        }
    })?;
    if !seen.file_type().is_file() {
        return Err("not a regular file".to_owned());
    }
    let file = fs::File::open(path).map_err(|e| format!("cannot be read: {e}"))?;
    let open = file
        .metadata()
        .map_err(|e| format!("cannot be read: {e}"))?;
    // The same inode is the same regular file. The size is bounded by the
    // read itself, which also holds for a file that grows once open.
    if (open.dev(), open.ino()) != (seen.dev(), seen.ino()) {
        return Err("changed while it was read".to_owned());
    }
    let mut bytes = Vec::new();
    file.take(MAX + 1)
        .read_to_end(&mut bytes)
        .map_err(|e| format!("cannot be read: {e}"))?;
    if bytes.len() as u64 > MAX {
        return Err("more than an entry".to_owned());
    }
    parse(&bytes)
}

/// This boot's restart for a reply, or `None`, logged with the reason.
pub fn now(path: &Path) -> Option<LastRestart> {
    read(path)
        .inspect_err(|why| {
            warn!(
                path = %path.display(),
                why = %why,
                "why the node restarted cannot be told"
            );
        })
        .ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::testing::Scratch;

    const ID: &str = "0f1e2d3c-4b5a-4968-8776-655443322110";

    fn entry(cause: &str, at: u64, last_alive: Option<u64>) -> String {
        format!(
            r#"{{"at": {at}, "boot_id": "{ID}", "cause": "{cause}", "last_alive": {}}}"#,
            last_alive.map_or("null".to_owned(), |t| t.to_string())
        ) + "\n"
    }

    #[test]
    fn the_path_the_boot_service_writes() {
        assert_eq!(THIS_BOOT, "/run/rikuri-boot-cause/this-boot.json");
    }

    #[test]
    fn every_cause_the_boot_service_writes_reads() {
        for (word, cause, alive) in [
            ("kernel-crash", RestartCause::KernelCrash, Some(90)),
            ("kernel-crash", RestartCause::KernelCrash, None),
            ("watchdog", RestartCause::Watchdog, Some(90)),
            ("rolled-back", RestartCause::RolledBack, Some(90)),
            ("update-applied", RestartCause::UpdateApplied, None),
            ("clean", RestartCause::Clean, Some(90)),
            ("power-cut", RestartCause::PowerCut, Some(90)),
            ("unknown", RestartCause::Unknown, None),
            ("first-boot", RestartCause::FirstBoot, None),
        ] {
            assert_eq!(
                parse(entry(word, 100, alive).as_bytes()),
                Ok(LastRestart {
                    cause,
                    at_unix: 100,
                    last_alive_unix: alive
                }),
                "{word}"
            );
        }
    }

    #[test]
    fn a_clock_behind_at_boot_is_not_a_reason_to_refuse() {
        // The lesson of the record's I-2: never compare the two clocks.
        let read = parse(entry("power-cut", 50, Some(1_790_000_000)).as_bytes()).unwrap();
        assert_eq!(read.last_alive_unix, Some(1_790_000_000));
    }

    #[test]
    fn anything_else_is_refused() {
        for bad in [
            String::new(),
            "{}".to_owned(),
            entry("power-outage", 100, Some(90)),
            entry("Clean", 100, Some(90)),
            entry("power-cut", 100, None),
            entry("clean", 100, None),
            entry("first-boot", 100, Some(90)),
            entry("clean", 100, Some(90)).replace("\"at\": 100", "\"at\": -1"),
            entry("clean", 100, Some(90)).replace("\"at\": 100", "\"at\": 1.5"),
            entry("clean", 100, Some(90)).replace("\"at\": 100", "\"at\": \"100\""),
            entry("clean", 100, Some(90)).replace("\"last_alive\": 90", "\"last_alive\": true"),
            entry("clean", 100, Some(90)).replace(ID, "not-a-boot-id"),
            entry("clean", 100, Some(90)).replace(ID, &ID.to_uppercase()),
            entry("clean", 100, Some(90)).replace("}", ", \"evidence\": []}"),
            entry("clean", 100, Some(90)).replace("\"cause\": \"clean\", ", ""),
            r#"[{"at": 1}]"#.to_owned(),
        ] {
            assert!(parse(bad.as_bytes()).is_err(), "{bad:?}");
        }
    }

    #[test]
    fn the_file_is_read_as_the_boot_service_writes_it() {
        let scratch = Scratch::new();
        fs::create_dir_all(&scratch.0).unwrap();
        let path = scratch.0.join("this-boot.json");
        assert_eq!(
            read(&path),
            Err("no record of this boot: the boot service wrote none".to_owned())
        );
        assert_eq!(now(&path), None);
        fs::write(&path, entry("power-cut", 2000, Some(1940))).unwrap();
        let want = LastRestart {
            cause: RestartCause::PowerCut,
            at_unix: 2000,
            last_alive_unix: Some(1940),
        };
        assert_eq!(read(&path), Ok(want));
        assert_eq!(now(&path), Some(want));
    }

    #[test]
    fn a_link_a_folder_or_a_long_file_is_refused() {
        let scratch = Scratch::new();
        fs::create_dir_all(&scratch.0).unwrap();
        let target = scratch.0.join("elsewhere.json");
        fs::write(&target, entry("clean", 2000, Some(1500))).unwrap();
        let link = scratch.0.join("link.json");
        std::os::unix::fs::symlink(&target, &link).unwrap();
        assert_eq!(read(&link), Err("not a regular file".to_owned()));
        let folder = scratch.0.join("folder.json");
        fs::create_dir(&folder).unwrap();
        assert_eq!(read(&folder), Err("not a regular file".to_owned()));
        let long = scratch.0.join("long.json");
        let mut text = entry("clean", 2000, Some(1500));
        text.push_str(&" ".repeat(MAX as usize));
        fs::write(&long, &text).unwrap();
        assert!(read(&long).unwrap_err().contains("more than an entry"));
        let just = scratch.0.join("just.json");
        let mut text = entry("clean", 2000, Some(1500));
        text.push_str(&" ".repeat(MAX as usize - text.len()));
        fs::write(&just, &text).unwrap();
        assert!(read(&just).is_ok(), "exactly MAX bytes is still an entry");
    }

    #[test]
    fn the_json_is_the_api_the_page_reads() {
        let restart = LastRestart {
            cause: RestartCause::PowerCut,
            at_unix: 2000,
            last_alive_unix: None,
        };
        assert_eq!(
            serde_json::to_string(&restart).unwrap(),
            r#"{"cause":"power-cut","at_unix":2000,"last_alive_unix":null}"#
        );
    }
}
