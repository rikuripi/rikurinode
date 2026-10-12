"""The new scanner and lookup over every tracked .rs file of the three Rust
repositories, read-only: declarations found (compared with a line-anchored
regex), files the lock would treat as test modules (expected: none), the
tripwire's answer, and the time a locked Edit of each file takes.
Usage: real_repos_probe.py <guard dir> (<label> <repo> <guard-config.json>)..."""
import os, re, subprocess, sys, time
sys.path.insert(0, sys.argv[1])
import guard
LINE = re.compile(r"^[ \t]*(?:pub(?:\s*\([^)]*\))?\s+)?mod\s+(?:r#)?\w+\s*;", re.M)
args = sys.argv[2:]
for label, root, cfgp in zip(args[0::3], args[1::3], args[2::3]):
    cfg = dict(guard.load_config(cfgp), profile="stable")
    rels = [os.fsdecode(r) for r in subprocess.run(["git", "-C", root, "ls-files", "-z", "--", "*.rs"],
            capture_output=True, check=True, env=guard.git_env()).stdout.split(b"\0") if r]
    scanned = simple = 0
    for rel in rels:
        text = guard.read_text(os.path.join(root, rel))
        scanned += len(guard.rust_file_modules(text))
        simple += len(LINE.findall(text))
    parents, worst, total = {}, 0.0, 0.0
    for rel in rels:
        first = guard.read_text(os.path.join(root, rel)).split("\n")[0] + "\n"
        ev = {"tool_name": "Edit", "tool_input": {"file_path": rel, "old_string": first, "new_string": first},
              "cwd": root}
        t0 = time.perf_counter()
        guard.decide(ev, cfg, root, lock_present=True, branch_fn=lambda _c: "feature/x")
        dt = time.perf_counter() - t0
        worst, total = max(worst, dt), total + dt
        p = guard.test_module_parent(rel, root, cfg)
        if p:
            parents[rel] = p
    t0 = time.perf_counter()
    gaps = guard.uncovered_inline_tests(root, cfg)
    print("%s: %d tracked .rs; mod declarations: scanner %d, line regex %d; test modules: %s; tripwire: %s (%.2f s);"
          " locked Edit decide(): mean %.1f ms, worst %.1f ms"
          % (label, len(rels), scanned, simple, parents or "none", gaps, time.perf_counter() - t0,
             1000 * total / len(rels), 1000 * worst))
