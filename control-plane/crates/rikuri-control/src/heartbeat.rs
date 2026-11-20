//! The heartbeat (D22, plan §4.1): the Unix time, written to the state folder
//! at start and every minute, so that the next boot can date a power cut to
//! within a minute. The root service `rikuri-boot-cause` reads it at boot, before
//! this daemon starts (`image/rootfs/usr/libexec/rikuri/boot-cause`); it takes
//! the file as untrusted and accepts only decimal digits and one newline.
//! Record: docs/build-records/2026-11-19-boot-cause-record.md

use std::future::Future;
use std::time::Duration;

use tokio::time::MissedTickBehavior;
use tracing::warn;

use crate::state::{StateDir, StateError};

/// The file's name in the state folder; the boot service reads it there.
pub const FILE: &str = "heartbeat";

/// How often it beats: the precision of a power cut's time.
pub const EVERY: Duration = Duration::from_secs(60);

/// One beat: `now` in decimal and a newline, the whole file at once (synced,
/// then renamed over the last one).
pub fn beat(dir: &StateDir, now: u64) -> Result<(), StateError> {
    dir.write(FILE, format!("{now}\n").as_bytes())
}

/// Beats at once, then every `every`, until `stop` completes. A beat that
/// fails, or a clock before 1970, is logged, and the next tick tries again.
pub async fn keep(
    dir: StateDir,
    now: impl Fn() -> Option<u64>,
    every: Duration,
    stop: impl Future<Output = ()>,
) {
    tokio::pin!(stop);
    let mut tick = tokio::time::interval(every);
    tick.set_missed_tick_behavior(MissedTickBehavior::Delay);
    loop {
        tokio::select! {
            biased;
            () = &mut stop => return,
            _ = tick.tick() => {}
        }
        match now() {
            Some(t) => {
                if let Err(e) = beat(&dir, t) {
                    warn!(
                        error = %e,
                        "heartbeat not written: a power cut now would be dated from the last one"
                    );
                }
            }
            None => warn!("heartbeat not written: the clock reads before 1970"),
        }
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;
    use std::sync::atomic::{AtomicU64, Ordering};

    use super::*;
    use crate::state::testing::Scratch;

    fn read(dir: &StateDir) -> Option<String> {
        dir.read(FILE)
            .unwrap()
            .map(|b| String::from_utf8(b).unwrap())
    }

    async fn until(dir: &StateDir, want: &str) {
        let wait = async {
            while read(dir).as_deref() != Some(want) {
                tokio::time::sleep(Duration::from_millis(5)).await;
            }
        };
        tokio::time::timeout(Duration::from_secs(5), wait)
            .await
            .unwrap_or_else(|_| panic!("the heartbeat never read {want:?}, last {:?}", read(dir)));
    }

    #[test]
    fn the_names_the_boot_service_relies_on() {
        assert_eq!(FILE, "heartbeat");
        assert_eq!(EVERY, Duration::from_secs(60));
    }

    #[test]
    fn a_beat_is_the_time_in_decimal_and_a_newline() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        beat(&dir, 1_763_500_000).unwrap();
        assert_eq!(read(&dir).as_deref(), Some("1763500000\n"));
        beat(&dir, 7).unwrap();
        assert_eq!(
            read(&dir).as_deref(),
            Some("7\n"),
            "the whole file is replaced"
        );
    }

    #[test]
    fn a_beat_into_a_missing_folder_fails() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        std::fs::remove_dir_all(&scratch.0).unwrap();
        assert!(beat(&dir, 1).is_err());
    }

    #[tokio::test]
    async fn it_beats_at_once_then_on_each_tick_until_stopped() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        let clock = Arc::new(AtomicU64::new(100));
        let now = {
            let clock = clock.clone();
            move || Some(clock.load(Ordering::SeqCst))
        };
        let (stop, stopped) = tokio::sync::oneshot::channel::<()>();
        let task = tokio::spawn(keep(dir.clone(), now, Duration::from_millis(10), async {
            let _ = stopped.await;
        }));
        until(&dir, "100\n").await;
        clock.store(200, Ordering::SeqCst);
        until(&dir, "200\n").await;
        stop.send(()).unwrap();
        tokio::time::timeout(Duration::from_secs(5), task)
            .await
            .expect("keep ends when told to stop")
            .unwrap();
        clock.store(300, Ordering::SeqCst);
        tokio::time::sleep(Duration::from_millis(50)).await;
        assert_eq!(
            read(&dir).as_deref(),
            Some("200\n"),
            "no beat after the stop"
        );
    }

    #[tokio::test]
    async fn the_first_beat_is_not_a_tick_late() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        let task = tokio::spawn(keep(
            dir.clone(),
            || Some(5),
            Duration::from_secs(3600),
            std::future::pending(),
        ));
        until(&dir, "5\n").await;
        task.abort();
    }

    #[tokio::test]
    async fn a_clock_before_1970_writes_nothing_and_it_carries_on() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        let clock = Arc::new(AtomicU64::new(0));
        let now = {
            let clock = clock.clone();
            move || match clock.load(Ordering::SeqCst) {
                0 => None,
                t => Some(t),
            }
        };
        let task = tokio::spawn(keep(
            dir.clone(),
            now,
            Duration::from_millis(10),
            std::future::pending(),
        ));
        tokio::time::sleep(Duration::from_millis(50)).await;
        assert_eq!(read(&dir), None);
        clock.store(42, Ordering::SeqCst);
        until(&dir, "42\n").await;
        task.abort();
    }

    #[tokio::test]
    async fn a_failed_beat_does_not_end_it() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        std::fs::remove_dir_all(&scratch.0).unwrap();
        let task = tokio::spawn(keep(
            dir.clone(),
            || Some(9),
            Duration::from_millis(10),
            std::future::pending(),
        ));
        tokio::time::sleep(Duration::from_millis(50)).await;
        assert!(!task.is_finished());
        std::fs::create_dir_all(&scratch.0).unwrap();
        until(&dir, "9\n").await;
        task.abort();
    }
}
