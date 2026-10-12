"""The scanner (rust_file_modules) and resolution (module_files) over a body
of published Rust, read as text only. Every `mod x;` in a published crate
should name a file that exists, so a scanner that misreads a brace, quote or
comment shows up as declarations whose file is not found. Prints totals, the
misses grouped by the attributes on them, and the misses with none.
Usage: corpus_probe.py <guard dir> <folder>..."""
import collections, os, re, sys, time
sys.path.insert(0, sys.argv[1])
import guard
LINE = re.compile(r"^[ \t]*(?:pub(?:\s*\([^)]*\))?\s+)?mod\s+(?:r#)?(\w+)\s*;", re.M)
files = decls = resolved = line_only = scan_only = 0
kinds, bare, t0 = collections.Counter(), [], time.perf_counter()
for top in sys.argv[2:]:
    for dirpath, dirnames, names in os.walk(top):
        dirnames.sort()
        for n in sorted(names):
            if not n.endswith(".rs"):
                continue
            path = os.path.join(dirpath, n)
            try:
                text = guard.read_text(path)
            except (OSError, UnicodeDecodeError):
                continue
            files += 1
            mods = guard.rust_file_modules(text)
            scan = collections.Counter(m[0] for m in mods)
            line = collections.Counter(LINE.findall(text))
            line_only += sum((line - scan).values())
            scan_only += sum((scan - line).values())
            rel = os.path.relpath(path, "/")
            for name, inline, p, attrs in mods:
                decls += 1
                choices = guard.module_files(rel, name, inline, p)
                if any(os.path.isfile(os.path.join("/", c)) for cs in choices for c in cs):
                    resolved += 1
                    continue
                a = " ".join(attrs)
                kind = ("path inside cfg_attr" if re.search(r"cfg_attr\s*\(.*path\s*=", a, re.S)
                        else "cfg(test): a test file left out of the published crate"
                        if re.search(r"cfg\s*\(\s*(?:test|any\s*\(\s*test|all\s*\(\s*test)", a)
                        else "another cfg: a platform or feature file left out" if re.search(r"cfg\s*\(", a)
                        else "no attribute")
                kinds[kind] += 1
                if kind == "no attribute":
                    bare.append("%s: mod %s; inline=%s path=%s" % (path, name, inline, p))
print("files %d, declarations %d, resolved %d (%.2f%%), not found %d; %.1f s"
      % (files, decls, resolved, 100.0 * resolved / max(decls, 1), decls - resolved, time.perf_counter() - t0))
print("vs a line-anchored regex: only the regex %d, only the scanner %d" % (line_only, scan_only))
print("not found, by the attributes on them: %s" % dict(kinds))
print("not found, no attribute:")
print("\n".join(bare))
