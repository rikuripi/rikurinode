"""A ratchet on the guard's verdicts: every case the verifiers wrote (rounds 6
to 8) and round 8's own, with the verdict the policy gave it in each profile
(data/guard-baseline.jsonl). Any change fails until the baseline is
regenerated and its diff reviewed:

    python3 scripts/quality/tests/test_guard_baseline.py --update

A loosening (ask to allow, deny to ask) must be named in the change's record.
Record: docs/build-records/2026-10-10-bootstrap.md (round 9)
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, ".claude", "hooks"))
import guard  # noqa: E402

BASELINE = os.path.join(HERE, "data", "guard-baseline.jsonl")
PROFILES = ("stable", "development")


def verdict(cfg, tool, text, profile):
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    tin = {"command": text} if tool == "Bash" else {key: text}
    event = {"tool_name": tool, "tool_input": tin, "cwd": guard.ROOT}
    return guard.decide(event, dict(cfg, profile=profile), guard.ROOT, lock_present=False,
                        branch_fn=lambda _cwd: "feature/x")[0]


def rows():
    with open(BASELINE) as f:
        return [json.loads(line) for line in f if line.strip()]


class Baseline(unittest.TestCase):
    def test_no_verdict_changed(self):
        cfg = guard.load_config()
        cases = rows()
        self.assertGreater(len(cases), 1000)
        changed = ["%s %s: was %s, now %s | %s" % (r["tool"], p, r[p], now, r["text"][:120])
                   for r in cases for p in PROFILES
                   for now in [verdict(cfg, r["tool"], r["text"], p)] if now != r[p]]
        self.assertEqual(changed, [], "%d verdicts changed (regenerate with --update and review the diff):\n%s"
                         % (len(changed), "\n".join(changed)))


def update():
    cfg = guard.load_config()
    out = [dict(r, **{p: verdict(cfg, r["tool"], r["text"], p) for p in PROFILES}) for r in rows()]
    with open(BASELINE, "w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("rewrote", BASELINE, len(out), "cases")


if __name__ == "__main__":
    if "--update" in sys.argv[1:]:
        update()
    else:
        unittest.main()
