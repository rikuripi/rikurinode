//! One rate limit for the whole node, never per address: a LAN peer owns as
//! many addresses as it likes, and the previous node's per-address limiter
//! locked out the owner's own Mac instead (register port 19's incident). After
//! `threshold` failures each further failure doubles the delay before the next
//! try, up to `cap`; a success clears it. The claim's count is also kept on
//! disk by its caller and synced here, so a restart never gives more tries;
//! the sign-in's lives here only, so a restart resets its delay and nothing
//! else (the password is never locked).

use std::time::{Duration, Instant};

#[derive(Debug, Clone)]
pub struct Limiter {
    threshold: u32,
    cap: Duration,
    failures: u32,
    blocked_until: Option<Instant>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Gate {
    Open,
    /// Refuse the try; the client may come back after `retry_after`.
    Blocked {
        retry_after: Duration,
    },
}

impl Limiter {
    /// Delays start at the `threshold`th failure (one second) and double from
    /// there, never above `cap`.
    pub const fn new(threshold: u32, cap: Duration) -> Self {
        Self {
            threshold,
            cap,
            failures: 0,
            blocked_until: None,
        }
    }

    pub fn failures(&self) -> u32 {
        self.failures
    }

    /// Whether a try may proceed at `now`.
    pub fn check(&self, now: Instant) -> Gate {
        match self.blocked_until {
            Some(until) if until > now => Gate::Blocked {
                retry_after: until - now,
            },
            _ => Gate::Open,
        }
    }

    /// Takes the count from the store. A count below the current one means the
    /// store was reset (the claim re-armed), which also lifts the block.
    pub fn sync(&mut self, failures: u32) {
        if failures < self.failures {
            self.blocked_until = None;
        }
        self.failures = failures;
    }

    /// Records a failure at `now` and returns the delay before the next try,
    /// zero while under the threshold.
    pub fn record_failure(&mut self, now: Instant) -> Duration {
        self.failures = self.failures.saturating_add(1);
        let delay = self.delay_after(self.failures);
        if !delay.is_zero() {
            self.blocked_until = Some(now + delay);
        }
        delay
    }

    pub fn record_success(&mut self) {
        self.failures = 0;
        self.blocked_until = None;
    }

    fn delay_after(&self, failures: u32) -> Duration {
        if failures < self.threshold {
            return Duration::ZERO;
        }
        let doublings = failures - self.threshold;
        if doublings >= 32 {
            return self.cap;
        }
        Duration::from_secs(1u64 << doublings).min(self.cap)
    }
}

/// Whole seconds for a `Retry-After` header, rounded up so the client never
/// comes back early.
pub fn retry_after_seconds(delay: Duration) -> u64 {
    let secs = delay.as_secs();
    if delay.subsec_nanos() > 0 {
        secs + 1
    } else {
        secs.max(1)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn limiter() -> Limiter {
        Limiter::new(5, Duration::from_secs(300))
    }

    #[test]
    fn under_the_threshold_nothing_is_delayed() {
        let mut l = limiter();
        let now = Instant::now();
        for n in 1..5 {
            assert_eq!(l.record_failure(now), Duration::ZERO, "failure {n}");
            assert_eq!(l.check(now), Gate::Open, "failure {n}");
        }
        assert_eq!(l.failures(), 4);
    }

    #[test]
    fn from_the_threshold_on_delays_double_and_block_the_next_try() {
        let mut l = limiter();
        let now = Instant::now();
        for _ in 0..4 {
            l.record_failure(now);
        }
        assert_eq!(l.record_failure(now), Duration::from_secs(1));
        assert_eq!(
            l.check(now),
            Gate::Blocked {
                retry_after: Duration::from_secs(1)
            }
        );
        assert_eq!(l.check(now + Duration::from_secs(1)), Gate::Open);
        assert_eq!(l.record_failure(now), Duration::from_secs(2));
        assert_eq!(l.record_failure(now), Duration::from_secs(4));
        assert_eq!(l.record_failure(now), Duration::from_secs(8));
    }

    #[test]
    fn the_delay_never_passes_the_cap() {
        let mut l = limiter();
        let now = Instant::now();
        for _ in 0..40 {
            l.record_failure(now);
        }
        assert_eq!(l.record_failure(now), Duration::from_secs(300));
        assert_eq!(
            l.check(now),
            Gate::Blocked {
                retry_after: Duration::from_secs(300)
            }
        );
        // Far past any doubling: still the cap, no overflow.
        l.sync(u32::MAX - 1);
        assert_eq!(l.record_failure(now), Duration::from_secs(300));
        assert_eq!(l.failures(), u32::MAX);
    }

    #[test]
    fn a_success_clears_the_count_and_the_block() {
        let mut l = limiter();
        let now = Instant::now();
        for _ in 0..6 {
            l.record_failure(now);
        }
        assert_ne!(l.check(now), Gate::Open);
        l.record_success();
        assert_eq!(l.failures(), 0);
        assert_eq!(l.check(now), Gate::Open);
        assert_eq!(l.record_failure(now), Duration::ZERO);
    }

    #[test]
    fn syncing_a_lower_count_lifts_the_block_and_a_higher_one_does_not() {
        let mut l = limiter();
        let now = Instant::now();
        for _ in 0..6 {
            l.record_failure(now);
        }
        l.sync(7);
        assert_eq!(l.failures(), 7);
        assert_ne!(l.check(now), Gate::Open, "a higher count keeps the block");
        l.sync(0);
        assert_eq!(l.failures(), 0);
        assert_eq!(l.check(now), Gate::Open, "a reset store lifts the block");
    }

    #[test]
    fn retry_after_rounds_up_and_is_at_least_one_second() {
        assert_eq!(retry_after_seconds(Duration::ZERO), 1);
        assert_eq!(retry_after_seconds(Duration::from_millis(1)), 1);
        assert_eq!(retry_after_seconds(Duration::from_secs(2)), 2);
        assert_eq!(retry_after_seconds(Duration::from_millis(2001)), 3);
    }
}
