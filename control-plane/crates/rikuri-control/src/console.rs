//! The claim screen at the node's console (`rikuri-control-plane claim-screen`,
//! on `tty2`, reached with Ctrl+Alt+F2): the node's address, the CA fingerprint,
//! and a claim code that only a key press at the node arms (stage 1 change
//! 5c.1; owner, 2026-11-06). The code is shown here and nowhere else: only its
//! hash is kept. Record: docs/build-records/2026-11-06-5c1-control-plane-on-node.md

#[cfg(test)]
mod tests {
    use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};

    use super::*;
    use crate::claim::{self, Attempt};
    use crate::owner;
    use crate::random;
    use crate::state::StateDir;
    use crate::state::testing::Scratch;
    use crate::tls;

    const NOW: u64 = 1_800_000_000;
    const FP: &str = "00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:\
                      F0:E1:D2:C3:B4:A5:96:87:78:69:5A:4B:3C:2D:1E:0F";
    const LAN: IpAddr = IpAddr::V4(Ipv4Addr::new(192, 168, 1, 20));

    fn open() -> (Scratch, StateDir) {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        (scratch, dir)
    }

    fn claimed(dir: &StateDir) {
        dir.write(owner::FILE, b"{}").unwrap();
    }

    fn made() -> Fingerprint {
        Fingerprint::Made(FP.to_owned())
    }

    // ---- what the screen does ---------------------------------------------

    #[test]
    fn the_first_screen_arms_nothing() {
        let (_scratch, dir) = open();
        assert!(matches!(initial(&dir), Shown::Prompt));
        assert_eq!(
            claim::load(&dir).unwrap(),
            None,
            "a code was armed with no key press"
        );
        claimed(&dir);
        assert!(matches!(initial(&dir), Shown::Claimed));
    }

    #[test]
    fn enter_on_an_unclaimed_node_arms_a_code_that_the_api_accepts() {
        let (_scratch, dir) = open();
        let Shown::Code(code) = press_enter(&dir, NOW) else {
            panic!("no code shown");
        };
        let (verdict, _) = claim::attempt(&dir, &code.formatted(), NOW + 1).unwrap();
        assert_eq!(verdict, Attempt::Accepted);
    }

    #[test]
    fn enter_again_retires_the_code_on_the_screen_for_a_new_one() {
        let (_scratch, dir) = open();
        let Shown::Code(first) = press_enter(&dir, NOW) else {
            panic!("no first code");
        };
        let Shown::Code(second) = press_enter(&dir, NOW + 1) else {
            panic!("no second code");
        };
        let (old, _) = claim::attempt(&dir, &first.formatted(), NOW + 2).unwrap();
        assert_ne!(old, Attempt::Accepted, "the old code still works");
        let (new, _) = claim::attempt(&dir, &second.formatted(), NOW + 2).unwrap();
        assert_eq!(new, Attempt::Accepted);
    }

    #[test]
    fn enter_on_a_claimed_node_arms_nothing() {
        let (_scratch, dir) = open();
        claimed(&dir);
        assert!(matches!(press_enter(&dir, NOW), Shown::Claimed));
        assert_eq!(claim::load(&dir).unwrap(), None);
    }

    #[test]
    fn a_code_that_cannot_be_armed_is_shown_as_a_problem_not_a_code() {
        let (_scratch, dir) = open();
        // A folder where the claim file goes: the write fails.
        std::fs::create_dir(dir.path(claim::FILE)).unwrap();
        let Shown::Problem(why) = press_enter(&dir, NOW) else {
            panic!("a failed arm was not shown as a problem");
        };
        assert!(why.contains(claim::FILE), "{why}");
    }

    #[test]
    fn the_fingerprint_is_the_ca_certificates_once_it_exists() {
        let (_scratch, dir) = open();
        assert!(matches!(ca_fingerprint(&dir), Fingerprint::NotYet));
        dir.write(tls::CA_CERT, b"not really DER").unwrap();
        let Fingerprint::Made(shown) = ca_fingerprint(&dir) else {
            panic!("no fingerprint");
        };
        assert_eq!(shown, random::fingerprint(b"not really DER"));
    }

    #[test]
    fn a_fingerprint_that_cannot_be_read_says_so() {
        let (_scratch, dir) = open();
        std::fs::create_dir(dir.path(tls::CA_CERT)).unwrap();
        assert!(matches!(ca_fingerprint(&dir), Fingerprint::Unreadable(_)));
    }

    #[test]
    fn only_an_address_another_machine_could_use_is_shown() {
        assert_eq!(shown_address(LAN), Some(LAN));
        let v6 = IpAddr::V6(Ipv6Addr::new(0xfd00, 0, 0, 0, 0, 0, 0, 7));
        assert_eq!(shown_address(v6), Some(v6));
        for none in [
            IpAddr::V4(Ipv4Addr::LOCALHOST),
            IpAddr::V4(Ipv4Addr::UNSPECIFIED),
            IpAddr::V6(Ipv6Addr::LOCALHOST),
            IpAddr::V6(Ipv6Addr::UNSPECIFIED),
        ] {
            assert_eq!(shown_address(none), None, "{none}");
        }
    }

    // ---- what the screen says ---------------------------------------------

    #[test]
    fn the_screen_shows_the_address_as_a_browser_would_open_it() {
        let text = render(Some(LAN), &made(), &Shown::Prompt);
        assert!(text.contains("http://192.168.1.20"), "{text}");
        let v6 = IpAddr::V6(Ipv6Addr::new(0xfd00, 0, 0, 0, 0, 0, 0, 7));
        let text = render(Some(v6), &made(), &Shown::Prompt);
        assert!(text.contains("http://[fd00::7]"), "{text}");
    }

    #[test]
    fn with_no_address_the_screen_says_to_connect_the_cable() {
        let text = render(None, &made(), &Shown::Prompt);
        assert!(text.contains("none yet"), "{text}");
        assert!(text.contains("network cable"), "{text}");
        assert!(!text.contains("http://"), "{text}");
    }

    #[test]
    fn the_whole_fingerprint_is_shown_on_two_lines_that_fit() {
        let text = render(Some(LAN), &made(), &Shown::Prompt);
        let (first, second) = FP.split_at(48);
        let first = first.trim_end_matches(':');
        assert!(text.lines().any(|l| l.trim() == first), "{text}");
        assert!(text.lines().any(|l| l.trim() == second), "{text}");
    }

    #[test]
    fn a_missing_or_unreadable_fingerprint_says_why() {
        let text = render(Some(LAN), &Fingerprint::NotYet, &Shown::Prompt);
        assert!(text.contains("not made yet"), "{text}");
        let text = render(
            Some(LAN),
            &Fingerprint::Unreadable("ca.crt.der: denied".to_owned()),
            &Shown::Prompt,
        );
        assert!(text.contains("cannot be read"), "{text}");
        assert!(text.contains("ca.crt.der: denied"), "{text}");
    }

    #[test]
    fn the_prompt_offers_a_code_and_shows_none() {
        let text = render(Some(LAN), &made(), &Shown::Prompt);
        assert!(text.contains("Press Enter"), "{text}");
        assert!(!text.contains("Claim code:"), "{text}");
    }

    #[test]
    fn a_code_is_shown_with_its_lifetime_and_what_enter_does_next() {
        let (_scratch, dir) = open();
        let Shown::Code(code) = press_enter(&dir, NOW) else {
            panic!("no code");
        };
        let formatted = code.formatted();
        let text = render(Some(LAN), &made(), &Shown::Code(code));
        assert!(
            text.contains(&format!("Claim code:  {formatted}")),
            "{text}"
        );
        assert!(text.contains("24 hours"), "{text}");
        assert!(text.contains("stops working"), "{text}");
    }

    #[test]
    fn a_claimed_node_offers_no_code() {
        let text = render(Some(LAN), &made(), &Shown::Claimed);
        assert!(text.contains("has an owner"), "{text}");
        assert!(!text.contains("Press Enter"), "{text}");
        assert!(!text.contains("Claim code:"), "{text}");
    }

    #[test]
    fn a_problem_is_shown_in_full() {
        let text = render(Some(LAN), &made(), &Shown::Problem("disk full".to_owned()));
        assert!(text.contains("could not be armed"), "{text}");
        assert!(text.contains("disk full"), "{text}");
    }

    #[test]
    fn every_screen_is_plain_ascii_that_fits_eighty_columns_and_says_how_to_go_back() {
        let (_scratch, dir) = open();
        let Shown::Code(code) = press_enter(&dir, NOW) else {
            panic!("no code");
        };
        let v6 = IpAddr::V6(Ipv6Addr::new(
            0xfd00, 0xabcd, 0xef01, 0x2345, 0x6789, 0xabcd, 0xef01, 0x2345,
        ));
        for (address, fingerprint, shown) in [
            (Some(LAN), made(), Shown::Prompt),
            (Some(v6), made(), Shown::Code(code)),
            (None, Fingerprint::NotYet, Shown::Claimed),
            (None, made(), Shown::Problem("x".to_owned())),
        ] {
            let text = render(address, &fingerprint, &shown);
            assert!(text.is_ascii(), "{text}");
            for line in text.lines() {
                assert!(line.len() <= 80, "{} columns: {line}", line.len());
            }
            // kmscon on tty1 switches only on Ctrl+Alt+Fn; the kernel on tty2 on both.
            assert!(text.contains("Ctrl+Alt+F1"), "{text}");
        }
    }
}
