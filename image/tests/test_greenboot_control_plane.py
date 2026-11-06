"""Tests for image/rootfs/usr/lib/greenboot/check/required.d/50-rikuri-control-plane.

greenboot runs the check at every boot as a required check. It passes when
the control plane answers `GET /api/setup` over HTTPS on loopback, verified
against the node's own CA, within a bounded wait. A failure counts toward the
rollback: an image can repair a control plane that an update broke.
Record: docs/build-records/2026-11-06-5c1-control-plane-on-node.md
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, os.pardir, "rootfs", "usr", "lib", "greenboot", "check", "required.d",
                     "50-rikuri-control-plane")


def load():
    loader = importlib.machinery.SourceFileLoader("greenboot_control_plane", CHECK)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


m = load()

SETUP = json.dumps({"claimed": False, "claim": "armed", "ca_fingerprint_sha256": "AA:BB",
                    "names": ["localhost"]}).encode()


def response(status=200, body=SETUP, reason="OK"):
    return (b"HTTP/1.1 %d %s\r\ncontent-type: application/json\r\ncontent-length: %d\r\n\r\n"
            % (status, reason.encode(), len(body))) + body


class Shipped(unittest.TestCase):
    def test_it_is_executable_python_in_isolated_mode(self):
        self.assertTrue(os.stat(CHECK).st_mode & 0o111)
        with open(CHECK, encoding="ascii") as f:
            self.assertEqual(f.readline(), "#!/usr/bin/python3 -I\n")

    def test_it_asks_the_node_itself_with_the_nodes_own_ca(self):
        self.assertEqual(m.ADDRESS, ("127.0.0.1", 443))
        self.assertEqual(m.SERVER_NAME, "localhost")
        self.assertEqual(m.CA, "/var/lib/rikuri/control-plane/ca.crt.der")
        self.assertEqual(m.REQUEST, b"GET /api/setup HTTP/1.1\r\nHost: localhost\r\n"
                                    b"Connection: close\r\n\r\n")

    def test_the_wait_is_bounded(self):
        self.assertGreater(m.WAIT_S, 0)
        self.assertLessEqual(m.WAIT_S, 180)


class Verdict(unittest.TestCase):
    def test_a_setup_report_passes(self):
        self.assertEqual(m.verdict(response()), (True, None))
        claimed = json.dumps({"claimed": True, "claim": "done"}).encode()
        self.assertEqual(m.verdict(response(body=claimed)), (True, None))

    def test_anything_else_fails_with_what_was_seen(self):
        for why, raw in (("a refusal", response(421, b'{"error":"x"}', "Misdirected Request")),
                         ("a server error", response(500, b"", "Internal Server Error")),
                         ("not JSON", response(body=b"<html>")),
                         ("JSON without claimed", response(body=b'{"claim":"armed"}')),
                         ("claimed not a boolean", response(body=b'{"claimed":"no"}')),
                         ("a list", response(body=b"[]")),
                         ("not HTTP", b"SSH-2.0-OpenSSH\r\n"),
                         ("nothing", b"")):
            with self.subTest(why=why):
                ok, reason = m.verdict(raw)
                self.assertFalse(ok)
                self.assertIn("journalctl -b -u rikuri-control-plane", reason)

    def test_the_reason_names_the_status(self):
        ok, reason = m.verdict(response(500, b"", "Internal Server Error"))
        self.assertIn("500", reason)


class Main(unittest.TestCase):
    def run_main(self, attempts):
        """main() with a clock that advances by each sleep, and attempts given in order."""
        now = [0.0]
        tries = []

        def attempt():
            tries.append(now[0])
            item = attempts[min(len(tries), len(attempts)) - 1]
            if isinstance(item, Exception):
                raise item
            return item

        out = io.StringIO()
        code = m.main(attempt=attempt, sleep=lambda s: now.__setitem__(0, now[0] + s),
                      clock=lambda: now[0], out=out)
        return code, out.getvalue(), tries

    def test_an_answer_passes_quietly(self):
        code, out, tries = self.run_main([response()])
        self.assertEqual((code, out, len(tries)), (0, "", 1))

    def test_it_waits_for_a_control_plane_still_starting(self):
        code, out, tries = self.run_main([ConnectionRefusedError(111, "refused"),
                                          FileNotFoundError(2, "no CA yet"), response()])
        self.assertEqual((code, out, len(tries)), (0, "", 3))

    def test_it_gives_up_after_the_wait_and_says_why(self):
        code, out, tries = self.run_main([ConnectionRefusedError(111, "refused")])
        self.assertEqual(code, 1)
        self.assertGreaterEqual(tries[-1], m.WAIT_S - m.INTERVAL_S)
        self.assertLessEqual(tries[-1], m.WAIT_S)
        self.assertIn("refused", out)
        self.assertIn("journalctl -b -u rikuri-control-plane", out)

    def test_a_wrong_answer_is_retried_then_reported(self):
        code, out, _ = self.run_main([response(500, b"", "Internal Server Error")])
        self.assertEqual(code, 1)
        self.assertIn("500", out)

    def test_a_certificate_the_ca_did_not_sign_fails(self):
        import ssl
        code, out, _ = self.run_main([ssl.SSLCertVerificationError(1, "certificate verify failed")])
        self.assertEqual(code, 1)
        self.assertIn("certificate verify failed", out)


if __name__ == "__main__":
    unittest.main()
