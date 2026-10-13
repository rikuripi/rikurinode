"""A locked Edit of a .rs file of one line and many empty lines, through the
real hook process, in a scratch crate with the hooks copied in and a fix-lock
held. The in-file checks read the edited file line by line with no deadline,
before this change too (owned debt in the record). Run inside safe-run.sh.
Usage: lines_probe.py <hooks dir> <MB>"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS, MB = sys.argv[1], int(sys.argv[2])
LIB = "pub fn two() -> u8 {\n    2\n}\n\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n        assert_eq!(super::two(), 2);\n    }\n}\n"


def hook(root, tin):
    event = {"session_id": "S1", "hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": tin, "cwd": root}
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    t = time.time()
    p = subprocess.run([sys.executable, os.path.join(root, ".claude/hooks/guard.py")], input=json.dumps(event),
                       capture_output=True, text=True, env=env, timeout=120)
    out = json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] if p.stdout.strip() else "allow"
    return out, time.time() - t


root = tempfile.mkdtemp(prefix="lines-", dir=os.environ.get("PROBE_TMP"))
try:
    os.makedirs(os.path.join(root, "src"))
    with open(os.path.join(root, "src/lib.rs"), "w") as f:
        f.write(LIB)
    with open(os.path.join(root, "src/zz.rs"), "w") as f:
        f.write("pub fn zz() {}\n" + "\n" * (MB << 20))
    shutil.copytree(HOOKS, os.path.join(root, ".claude/hooks"), ignore=shutil.ignore_patterns("__pycache__", "test_guard.py"))
    os.makedirs(os.path.join(root, ".claude/state/fix-locks"))
    with open(os.path.join(root, ".claude/state/fix-locks/S1.json"), "w") as f:
        f.write("{}")
    for label, tin in (("src/zz.rs: one line, then %d MB of empty lines" % MB,
                        {"file_path": os.path.join(root, "src/zz.rs"), "old_string": "pub fn zz() {}",
                         "new_string": "pub fn zz() { }"}),
                       ("src/lib.rs, beside it", {"file_path": os.path.join(root, "src/lib.rs"),
                                                  "old_string": "    2\n}", "new_string": "    2 + 0\n}"})):
        decision, took = hook(root, tin)
        print("  locked Edit of %-46s %-5s %6.2f s%s" % (label, decision, took, "  past the hook's 10 s" if took > 10 else ""),
              flush=True)
finally:
    shutil.rmtree(root)
