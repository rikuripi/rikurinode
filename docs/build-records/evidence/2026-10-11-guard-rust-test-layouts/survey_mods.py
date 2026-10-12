"""Survey: file-module declarations (`mod x;`) in tracked .rs files, and where
they sit relative to the file's first #[cfg(test)] marker. Read-only."""
import os, re, subprocess, sys
MARK = re.compile(r"^[ \t]*#\s*!?\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]", re.M)
MOD = re.compile(r"^[ \t]*(?:pub(?:\s*\([^)]*\))?\s+)?mod\s+(r#)?(\w+)\s*;", re.M)
PATH = re.compile(r"#\s*\[\s*path\s*=")
INNER = re.compile(r"^[ \t]*#\s*!\s*\[\s*cfg\s*\(\s*test", re.M)
for root in sys.argv[1:]:
    files = subprocess.run(["git", "-C", root, "ls-files", "-z", "--", "*.rs"], capture_output=True).stdout.split(b"\0")
    after, attr, inner, paths, total = [], [], [], [], 0
    for raw in filter(None, files):
        rel = os.fsdecode(raw)
        t = open(os.path.join(root, rel), encoding="utf-8", errors="replace").read()
        m = MARK.search(t)
        if INNER.search(t): inner.append(rel)
        if PATH.search(t): paths.append(rel)
        for d in MOD.finditer(t):
            total += 1
            above = t[:d.start()].rstrip("\n").split("\n")[-3:]
            if any(re.search(r"cfg\s*\(\s*test", l) for l in above):
                attr.append("%s: %s" % (rel, d.group(0).strip()))
            elif m and d.start() > m.start():
                after.append("%s: %s" % (rel, d.group(0).strip()))
    print("==", root, "| mod decls:", total)
    print("  cfg(test)-attributed mod x; :", attr)
    print("  other mod x; after first marker:", after)
    print("  #![cfg(test)] files:", inner)
    print("  files with #[path]:", paths)
