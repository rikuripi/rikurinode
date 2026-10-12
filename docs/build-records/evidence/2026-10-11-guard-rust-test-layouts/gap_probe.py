"""The two gaps, shown through the guard's real decision path and its
tripwire (run from the repository root, inside safe-run.sh). A scratch git
repository holds both layouts; the rule is the one rikurinode, AISecurity
and Rikuri-PI configure today."""
import os, shutil, subprocess, sys, tempfile
sys.path.insert(0, ".claude/hooks")
import guard
RULE = {"glob": "*.rs",
        "starts_at": r"^[ \t\f\v\r\u200b-\u200f\u2060\ufeff]*#\s*\[\s*cfg\s*\(\s*(?:test|(?:any|all)\s*\((?:.*[(,]\s*)?(?<!not\()test(?=\s*[,)]).*\))\s*\)\s*\]",
        "attached_above": r"^[ \t\f\v\r\u200b-\u200f\u2060\ufeff]*(#\s*\[|//|/\*|\*)",
        "guarded_lines": r"cfg(?:_attr)?\s*!?\s*\(.*\btest\b|macro_rules!\s*(?:assert\w*|debug_assert\w*|panic|unreachable|todo)\b"}
WIDE = {k: v.replace(r"#\s*\[", r"#\s*!?\s*\[") for k, v in RULE.items()}
FILES = {"src/lib.rs": "pub fn add(a: u8, b: u8) -> u8 {\n    a + b\n}\n\n#[cfg(test)]\nmod tests;\n",
         "src/tests.rs": "use super::*;\n\n#[test]\nfn adds() {\n    assert_eq!(add(2, 2), 4);\n}\n",
         "src/inner.rs": "//! Tests only.\n#![cfg(test)]\n\n#[test]\nfn holds() {\n    assert_eq!(1, 1);\n}\n"}
root = tempfile.mkdtemp()
try:
    for name, text in FILES.items():
        os.makedirs(os.path.join(root, os.path.dirname(name)), exist_ok=True)
        with open(os.path.join(root, name), "w") as f:
            f.write(text)
    env = guard.git_env()
    subprocess.run(["git", "init", "-q", root], check=True, env=env)
    subprocess.run(["git", "-C", root, "add", "."], check=True, env=env)
    for label, rule in (("rule as configured today", RULE), ("rule widened, choice 2(a)", WIDE)):
        if label.startswith("rule widened") and not hasattr(guard, "rust_file_modules"):
            continue  # the old guard: the widened rule is part of this change
        cfg = dict(guard.load_config(), inline_tests=[rule], profile="stable")
        cfg.pop("fix_lock_preflight", None)
        print("--", label)
        for path, old, new in (("src/tests.rs", "add(2, 2), 4", "add(2, 2), 5"),
                               ("src/inner.rs", "assert_eq!(1, 1)", "assert_eq!(1, 2)"),
                               ("src/inner.rs", "#![cfg(test)]", "#![cfg(any())]\n#![cfg(test)]"),
                               ("src/lib.rs", "    a + b\n", "    b + a\n")):
            ev = {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": old, "new_string": new},
                  "cwd": root}
            d = guard.decide(ev, cfg, root, lock_present=True, branch_fn=lambda _c: "feature/x")
            print("fix-lock held, Edit %-13s %-34r -> %s" % (path, new, d[0]))
        print("tripwire, uncovered_inline_tests:", guard.uncovered_inline_tests(root, cfg))
    print("tripwire marker finds #![cfg(test)]:", bool(guard.RUST_INLINE_TEST.search(FILES["src/inner.rs"])))
finally:
    shutil.rmtree(root)
