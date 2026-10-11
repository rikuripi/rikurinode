"""Tests for scripts/quality/repo_hygiene.py: what may never be tracked.

Owner, 2026-10-10: logs stay local, never in git; machine state, secrets and
unpinned images do not belong in the repository either. Each rule has a case
that must fail and a neighbour that must pass, so a rule cannot drift into
blocking legitimate files or into letting the real thing through.
Record: docs/build-records/2026-10-10-bootstrap.md
Run: python3 -m unittest discover -s scripts/quality/tests -p 'test_*.py'
"""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import repo_hygiene as rh  # noqa: E402


def problems_for(path, text="x\n"):
    """Problems the check reports for one tracked file with this content."""
    return rh.check_file(path, text.encode(), len(text.encode()))


class ForbiddenPaths(unittest.TestCase):
    def assertRefused(self, path, why):
        found = problems_for(path)
        self.assertTrue(found, "%s should be refused" % path)
        self.assertIn(why, " ".join(found), path)

    def assertAccepted(self, path, text="x\n"):
        self.assertEqual(problems_for(path, text), [], path)

    def test_logs_stay_local(self):
        for p in ("app.log", "lnd/lnd.log.3", "lnd.log.gz", "debug.LOG", "nohup.out",
                  "logs/today.txt", "log/x.json"):
            self.assertRefused(p, "log")
        for p in ("docs/logging.md", "src/logger.ts", "tests/fixtures/lnd-startup.log",
                  "src/log/mod.rs", "dashboard/src/pages/logs/LogViewer.tsx"):
            self.assertAccepted(p)

    def test_secrets_never(self):
        for p in (".env", "deploy/.env.production", "config/node.env", "admin.macaroon",
                  "lnd/wallet.db", "channel.backup", ".cookie", "bitcoin/.cookie",
                  "tls.key", "cert.pem", "id_ed25519", "api.token", "owner.secret",
                  "vault.kdbx", "credentials.json", "config.local.toml", "tests/fixtures/admin.macaroon",
                  # the node's own key files, and copies under another name (verifier, round 1)
                  "lnd/wallet_password.txt", "bitcoin/wallets/default/wallet.dat", "lnd/data/macaroons.db",
                  "tor/hidden_service/hs_ed25519_secret_key", "wallet.db.bak", "channel.backup.2026-10-10",
                  "channel.backup.gz", "admin.macaroon.b64", ".ENV",
                  # the guard's credential files: one list for both (no drift)
                  ".netrc", ".git-credentials", ".npmrc", ".pypirc", ".envrc", "service-account-ci.json",
                  ".claude/.credentials.json",
                  # round 2's verifier
                  "tor/control_auth_cookie", "credentials.toml", "lnd/channels.backup", "wg0.conf",
                  "secrets.json", "deploy/secrets.yaml"):
            self.assertRefused(p, "secret")
        for p in (".env.example", "config/node.env.example", "id_ed25519.pub", "docs/macaroons.md",
                  "src/cookie_reader.rs", "docs/wallet-password.md",
                  # source and docs that only share a key file's name (round 2's verifier)
                  "crates/lnd/src/aezeed.rs", "src/db/wallet.db.ts", "docs/runbooks/channel.backup.md",
                  "docs/macaroon.example.md"):
            self.assertAccepted(p)

    def test_a_template_name_exempts_from_the_secret_rule_only(self):
        # `.env.example` is a template; `logs/x.sample` is still a log
        self.assertRefused("logs/startup.sample", "log")
        self.assertRefused("backups/rollback.example", "state")

    def test_runtime_state_lives_outside_the_repo(self):
        for p in ("data/upgrade-state.json", "dashboard/backend/data/auth.db", "backups/rollback/x.yml",
                  "node.sqlite", "state.db-wal", "x.db-journal", "run/node.state", "node.pid", "core.12345",
                  "peers.dat", "blocks/blk00001.dat", "chainstate/000123.ldb", "compose.lock",
                  "nodes.db.old-n150",
                  # a fixtures folder inside a runtime folder is still runtime data (round 2's verifier)
                  "data/fixtures/peers.dat"):
            self.assertRefused(p, "state")
        self.assertRefused("logs/fixtures/node.log", "log")
        # source folders that only share a name with runtime folders (verifier, round 1)
        for p in ("tests/fixtures/data/sample.json", "src/data_model.rs", "docs/database.md",
                  "crates/node/src/data/mod.rs", "src/backups/scheduler.ts", "src/run/mod.rs",
                  "docs/runbooks/backups/restore-drill.md", "tests/data/vectors.json",
                  "Cargo.lock", "package-lock.json"):
            self.assertAccepted(p)

    def test_build_output_and_dependencies(self):
        for p in ("node_modules/x/index.js", "target/debug/app", "web/dist/index.html",
                  "src/__pycache__/m.cpython-312.pyc", ".venv/bin/python"):
            self.assertRefused(p, "build output")
        self.assertAccepted("src/target.rs")
        self.assertAccepted("src/target/mod.rs")  # a module, not Cargo's root target/
        self.assertAccepted("docs/distribution.md")

    def test_agent_state_and_models(self):
        for p in (".claude/state/fix-lock", ".claude/settings.local.json"):
            self.assertRefused(p, "local")
        for p in ("models/qwen.gguf", "models/x.safetensors"):
            self.assertRefused(p, "model")
        self.assertAccepted(".claude/settings.json")

    def test_archives_except_fixtures(self):
        self.assertRefused("release.tar.gz", "archive")
        self.assertRefused("backup.zip", "archive")
        self.assertAccepted("tests/fixtures/sample.tar.gz")


class Size(unittest.TestCase):
    def test_large_blob_refused(self):
        found = rh.check_file("docs/screenshot.png", b"", rh.MAX_BYTES + 1)
        self.assertTrue(any("large" in p for p in found), found)

    def test_at_the_limit_accepted(self):
        self.assertEqual(rh.check_file("docs/screenshot.png", b"", rh.MAX_BYTES), [])


class Pins(unittest.TestCase):
    def compose(self, image):
        return "services:\n  tor:\n    image: %s\n" % image

    def test_compose_unpinned_refused(self):
        for image in ("dockurr/tor", "dockurr/tor:latest", "'redis:latest'", "${TOR_IMAGE}",
                      "${TOR_IMAGE:-dockurr/tor}", "${TOR_IMAGE:-dockurr/tor:latest}",
                      # floating tags without a version (BUILD-PROCEDURE Phase 0; verifier, round 1)
                      "node:lts", "fedora:rawhide", "x/y:stable", "x/y:main", "x/y:nightly",
                      # a registry port is not a tag
                      "registry.local:5000/tor", "${TOR_IMAGE:-registry.local:5000/tor}",
                      # a major version alone still floats (round 2's verifier)
                      "python:3", "node:20-alpine", "rust:1"):
            found = problems_for("compose/docker-compose.yml", self.compose(image))
            self.assertTrue(any("pinned" in p for p in found), image)

    def test_compose_pinned_accepted(self):
        for image in ("dockurr/tor:0.4.9.14", "\"redis:8.10.2\"", "lightninglabs/lnd:v0.21.4-beta",
                      "${RIKURI_IMAGE_TOR:-dockurr/tor:0.4.9.14}",
                      "registry.local:5000/tor:1.2", "bitcoin/bitcoin@sha256:" + "a" * 64,
                      "lightninglabs/lnd:${LND_VERSION:-v0.18.3-beta}", "bitcoin/bitcoin:31.1",
                      "rust:1.90-bookworm", "bitcoinknots/bitcoin:29.3.knots20260507", "mariadb:10.11.19"):
            self.assertEqual(problems_for("docker-compose.yml", self.compose(image)), [], image)

    def test_every_compose_file_name(self):
        for name in ("compose.yaml", "compose.yml", "docker-compose.yaml", "deploy/stack.compose.yaml"):
            self.assertTrue(any("pinned" in p for p in problems_for(name, self.compose("redis:latest"))), name)
        # any YAML with a top-level services: map is a compose file
        self.assertTrue(any("pinned" in p for p in problems_for("deploy/lnd.yml", self.compose("redis:latest"))))
        self.assertEqual(problems_for("docs/example.yml", "image: redis:latest\n"), [])

    def test_copy_from_an_image(self):
        self.assertTrue(any("pinned" in p for p in problems_for("Containerfile", "FROM alpine:3.20\nCOPY --from=alpine:latest /x /x\n")))
        good = "FROM rust:1.90 AS build\nFROM alpine:3.20\nCOPY --from=build /x /x\nCOPY --from=0 /z /z\nCOPY --from=alpine:3.20 /y /y\n"
        self.assertEqual(problems_for("Containerfile", good), [])

    def test_a_distribution_release_is_pinned_by_digest(self):
        # fedora:41 names a release, but the image behind it changes with every update
        self.assertTrue(any("pinned" in p for p in problems_for("Containerfile", "FROM fedora:41\n")))
        self.assertEqual(problems_for("Containerfile", "FROM fedora:41@sha256:" + "b" * 64 + "\n"), [])

    def test_containerfile_arg_pins(self):
        self.assertEqual(problems_for("Containerfile", "ARG BASE=alpine:3.20\nFROM ${BASE}\n"), [])
        self.assertTrue(any("pinned" in p for p in problems_for("Containerfile", "ARG BASE=fedora\nFROM $BASE\n")))
        self.assertTrue(any("pinned" in p for p in problems_for("Containerfile", "ARG BASE\nFROM ${BASE}\n")))

    def test_containerfile(self):
        bad = "FROM fedora\nRUN true\n"
        self.assertTrue(any("pinned" in p for p in problems_for("Containerfile", bad)))
        self.assertTrue(any("pinned" in p for p in problems_for("build/Dockerfile.node", "FROM node:latest\n")))
        good = ("FROM --platform=$BUILDPLATFORM rust:1.90-bookworm AS build\nRUN true\n"
                "FROM scratch\nCOPY --from=build /x /x\nFROM build AS test\n")
        self.assertEqual(problems_for("Containerfile", good), [])

    def test_quadlet(self):
        self.assertTrue(any("pinned" in p for p in problems_for("deploy/tor.container", "[Container]\nImage=dockurr/tor\n")))
        self.assertEqual(problems_for("deploy/tor.container", "[Container]\nImage=dockurr/tor:0.4.9.14\n"), [])

    def test_other_files_not_parsed_for_images(self):
        self.assertEqual(problems_for("docs/upgrades.md", "image: dockurr/tor\nFROM fedora\n"), [])


class WholeRepository(unittest.TestCase):
    """The command line, on a real git index: what the hook and CI run."""

    def run_check(self, files):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            for rel, data in files.items():
                path = os.path.join(d, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as f:
                    f.write(data)
            subprocess.run(["git", "-C", d, "add", "-A"], check=True)
            return subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), "repo_hygiene.py"), d],
                                  capture_output=True, text=True)

    def test_clean_tree_passes(self):
        r = self.run_check({"README.md": b"# x\n", "src/main.rs": b"fn main() {}\n"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_each_offender_is_named(self):
        r = self.run_check({"README.md": b"# x\n", "app.log": b"boom\n", ".env": b"K=v\n"})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("app.log", r.stdout)
        self.assertIn(".env", r.stdout)
        self.assertNotIn("K=v", r.stdout + r.stderr)  # never prints contents

    def test_the_index_is_checked_not_the_working_tree(self):
        # a staged log is refused even if the file was deleted afterwards
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            with open(os.path.join(d, "x.log"), "w") as f:
                f.write("boom\n")
            subprocess.run(["git", "-C", d, "add", "x.log"], check=True)
            os.remove(os.path.join(d, "x.log"))
            r = subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), "repo_hygiene.py"), d],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("x.log", r.stdout)

    def test_pins_are_checked_through_the_command_line(self):
        r = self.run_check({"compose.yaml": b"services:\n  tor:\n    image: dockurr/tor:latest\n"})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("compose.yaml: line 3: image not pinned", r.stdout)

    def test_a_missing_object_fails_loudly_never_reads_as_empty(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            with open(os.path.join(d, "app.log"), "w") as f:
                f.write("boom\n")
            subprocess.run(["git", "-C", d, "add", "app.log"], check=True)
            sha = subprocess.run(["git", "-C", d, "rev-parse", ":app.log"], capture_output=True, text=True).stdout.strip()
            os.remove(os.path.join(d, ".git", "objects", sha[:2], sha[2:]))
            r = subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), "repo_hygiene.py"), d],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("missing", r.stderr)

    def test_not_a_repository_fails_loudly(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), "repo_hygiene.py"), d],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
