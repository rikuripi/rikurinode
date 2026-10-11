"""The survey behind survey.out: for each repository (root=config), its tracked .rs files, those with a
#[cfg(test)] marker, and those covered by an inline_tests rule (glob alone; glob and a starts_at region
reaching the first marker). Usage: python3 -I -B survey_probe.py <folder with guard.py> root=config ..."""
import json, os, re, subprocess, sys
sys.path.insert(0, sys.argv[1])  # folder holding guard.py
import guard
MARK = re.compile(r"^[ \t]*#\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]", re.M)
for spec in sys.argv[2:]:
    root, cfgpath = spec.split("=")
    cfg = json.load(open(cfgpath))
    files = [f for f in subprocess.run(["git", "-C", root, "ls-files", "-z", "--", "*.rs"],
             capture_output=True, text=True, check=True).stdout.split("\0") if f]
    marked = glob_only = full = 0
    weak = []
    for rel in files:
        text = guard.read_text(os.path.join(root, rel))
        m = MARK.search(text)
        if not m:
            continue
        marked += 1
        rules = guard.inline_rules(rel, cfg)
        if rules:
            glob_only += 1
        if any((reg := guard.inline_region(text, r["starts_at"], r.get("attached_above", ""))) is not None
               and len(reg) >= len(text) - m.start() for r in rules):
            full += 1
        elif rules:
            weak.append(rel)
    print("%s: %d .rs, %d marked, glob-covered %d, region-covered %d, weak %s"
          % (os.path.basename(root), len(files), marked, glob_only, full, weak[:5]))
