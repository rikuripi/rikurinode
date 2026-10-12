"""Mutants of the test-module and `#![cfg(test)]` change, against guard.py as
it will be committed. Run from the repository root inside safe-run.sh. Python
runs with -B (no bytecode cache: a same-size mutant's stale .pyc can outlive
its restore). The file is restored and checked by sha256. `--dry` only checks
that every substitution finds its text exactly once."""
import hashlib
import subprocess
import sys

GUARD_TESTS = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
G = ".claude/hooks/guard.py"
CHAR = r"""|(?<!\w)b?'(?:\\(?:u\{[0-9A-Fa-f_]*\}|x[0-9A-Fa-f]{2}|[^\n])|[^'\\\n])'")"""
MUTANTS = [
    # enforcement (R1, R2, R5) and its time budget (verifier round 1, D1)
    ("E1 a test module is not refused", [("    if parent is not None:\n        return (\"deny\", \"fix-lock is engaged: %s is a test module",
                                          "    if False:\n        return (\"deny\", \"fix-lock is engaged: %s is a test module")]),
    ("E2 a folder that cannot be listed allows the edit",
     [('        return ("deny", "fix-lock is engaged and the folders above %s could not be read to check whether it is "\n'
       '                        "a test module (%s)" % (rel, e), True)', "        return None")]),
    ("E3 any attribute marks a test", [('        return any(re.search(r["starts_at"], attr, re.M) for r in inline_rules(declaring, cfg))',
                                        "        return True")]),
    ("E4 the edited file's rules, not the declaring file's",
     [('def test_module_parent(rel: str, root: str, cfg: dict, deadline: float = float("inf")) -> str | None:',
       'def test_module_parent(rel: str, root: str, cfg: dict, deadline: float = float("inf")) -> str | None:\n    edited = rel'),
      ('for r in inline_rules(declaring, cfg))', 'for r in inline_rules(edited, cfg))')]),
    ("E5 a test module's own modules are not tests", [("                if rel not in found and not any(is_test(rel, a) for a in attrs):",
                                                       "                if not any(is_test(rel, a) for a in attrs):")]),
    ("E6 only the edited file's own folder", [("        if not folder:\n            break\n        folder = os.path.dirname(folder)",
                                               "        break")]),
    ("E7 a new folder is an error", [("        except (FileNotFoundError, NotADirectoryError):\n            names = []",
                                      "        except ():\n            names = []")]),
    ("E8 an unreadable file stops the check", [("            text = read_text(os.path.join(root, rel))\n        except (OSError, UnicodeDecodeError):\n            continue\n        if RUST_MOD_WORD",
                                                "            text = read_text(os.path.join(root, rel))\n        except ():\n            continue\n        if RUST_MOD_WORD")]),
    ("E9 the scanner ignores the time budget", [("        if time.time() > deadline:\n            raise _TooSlow()\n        m = RUST_SCAN",
                                                 "        m = RUST_SCAN")]),
    ("E10 the lookup gets no time budget", [("test_module_parent(rel, root, cfg, _DEADLINE_ALL)", "test_module_parent(rel, root, cfg)")]),
    # the declaration of a file that is all tests (verifier round 1, D4)
    ("F1 the parent's declaration is not checked", [("    kept = [repr(d) for d in test_file_declarations(rel, before, root, cfg, _DEADLINE_ALL)]",
                                                     "    kept = []")]),
    ("F2 the module file's rules not read (the edited file's instead)", [('            rules = inline_rules(p, cfg)', '            rules = inline_rules(rel, cfg)')]),
    ("F4 a comment ends the file's attributes", [('        if m.group("comment"):\n            pos = rust_comment_end(text, m.end())', '        if m.group("comment"):\n            return out')]),
    ("F5 a line comment ends the file's attributes", [('        elif m.group().startswith("//"):\n            pos = m.end()', '        elif m.group().startswith("//"):\n            return out')]),
    ("F6 a byte-order mark hides the file's attributes", [('pos = [], 1 if text.startswith("\\ufeff") else 0', 'pos = [], 0')]),
    ("F7 only the file's first inner attribute", [('            out.append(text[m.start():pos])', '            return out + [text[m.start():pos]]')]),
    ("F8 an outer attribute counts as the file's", [('        elif m.group("attr") and m.group("inner"):\n            pos = rust_attr_end', '        elif m.group("attr"):\n            pos = rust_attr_end')]),
    ("F3 the edit's result is not read", [("        left = [repr(d) for d in test_file_declarations(rel, a, root, cfg, _DEADLINE_ALL)]",
                                           "        left = kept")]),
    # attributes that apply (R2)
    ("A1 the blocks' attributes ignored", [("top + [a for f in frames for a in f[1]] + pending", "top + pending")]),
    ("A2 the file's inner attributes ignored", [("top + [a for f in frames for a in f[1]] + pending", "[a for f in frames for a in f[1]] + pending")]),
    ("A3 the declaration's own attributes ignored", [("top + [a for f in frames for a in f[1]] + pending", "top + [a for f in frames for a in f[1]]")]),
    ("A4 a block does not take the attributes before it", [("            frames.append([(path or name) if state == 2 else None, pending])",
                                                            "            frames.append([(path or name) if state == 2 else None, []])")]),
    ("A5 `;` does not end an attribute's reach", [('        elif m.group("semi"):\n            if state == 2:',
                                                   '        elif m.group("semi") and state != 2:\n            continue\n        elif m.group("semi"):\n            if state == 2:')]),
    # where the file is (R3) and both places (verifier round 1, D3)
    ("P1 lib.rs and main.rs are not mod-rs", [('base in ("mod.rs", "lib.rs", "main.rs")', 'base in ("mod.rs",)')]),
    ("P2 no crate-root place", [("[os.path.join(folder, os.path.splitext(base)[0]), folder])", "[os.path.join(folder, os.path.splitext(base)[0])])")]),
    ("P3 the crate-root folder first", [("[os.path.join(folder, os.path.splitext(base)[0]), folder])", "[folder, os.path.join(folder, os.path.splitext(base)[0])])")]),
    ("P4 a file-level #[path] from the module's folder", [("    if path is not None and not inline:\n", "    if False:\n")]),
    ("P5 no name/mod.rs", [('[name + ".rs", os.path.join(name, "mod.rs")]', '[name + ".rs"]')]),
    ("P6 paths outside the repository kept", [('        paths = [p for p in paths if not (os.path.isabs(p) or p == ".." or p.startswith("../"))]\n', "")]),
    ("P7 only the first place locked", [("                places = [p for ps in module_files(rel, name, inline, path) for p in ps]",
                                         "                places = module_files(rel, name, inline, path)[0]")]),
    ("P8 only places that exist locked", [("                places = [p for ps in module_files(rel, name, inline, path) for p in ps]",
                                           "                places = [p for ps in module_files(rel, name, inline, path) for p in ps if os.path.isfile(os.path.join(root, p))]")]),
    ("P9 a declaration's #[path] ignored", [("            if state == 2:\n                path = next(", "            if state == 2:\n                path = None and next(")]),
    ("P10 an inline module's #[path] ignored", [("frames.append([(path or name) if state == 2 else None, pending])", "frames.append([name if state == 2 else None, pending])")]),
    ("P11 the inline modules ignored", [("[f[0] for f in frames if f[0] is not None]", "[]")]),
    ("P12 a module's inner #![path] ignored", [("                    frames[-1][0] = inner_path.group(1)", "                    pass")]),
    ("P13 #![path] names a function's block too", [("                if inner_path and frames[-1][0] is not None:", "                if inner_path:")]),
    # literals are not code (R4), comments nest, unclosed runs to the end (D1, D5, D7)
    ("L1 line comments read as code", [('RUST_SKIP = (r"//[^\\n]*"', 'RUST_SKIP = (r"(?!x)x"')]),
    ("L2 block comments read as code", [('RUST_SCAN = re.compile(r"(?P<comment>/\\*)|"', 'RUST_SCAN = re.compile(r"(?P<comment>(?!x)x)|"')]),
    ("L3 block comments do not nest", [('depth += 1 if m.group() == "/*" else -1', 'depth -= 1 if m.group() == "*/" else 0')]),
    ('L4 an unclosed comment skips only its opener', [('            return m.end()\n    return len(text)\n\n\ndef rust_attr_end', '            return m.end()\n    return pos\n\n\ndef rust_attr_end')]),
    ("L5 raw strings read as code", [("""             r'|(?<!\\w)[bc]?r(?P<hashes>#*)"[\\s\\S]*?(?:"(?P=hashes)|\\Z)'\n""", "")]),
    ("L6 a raw string runs to its last closer", [("""r(?P<hashes>#*)"[\\s\\S]*?(?:""", """r(?P<hashes>#*)"[\\s\\S]*(?:""")]),
    ("L7 an unclosed raw string is retried", [("""[\\s\\S]*?(?:"(?P=hashes)|\\Z)""", """[\\s\\S]*?"(?P=hashes)""")]),
    ("L8 strings read as code", [("""             r'|(?<!\\w)[bc]?"(?:\\\\[\\s\\S]|[^"\\\\])*(?:"|\\Z)'\n""", "")]),
    ("L9 escapes in a string ignored", [("""[bc]?"(?:\\\\[\\s\\S]|[^"\\\\])*(?:"|\\Z)""", """[bc]?"[^"]*(?:"|\\Z)""")]),
    ("L10 an unclosed string skips only its quote", [("""[^"\\\\])*(?:"|\\Z)'""", """[^"\\\\])*"'""")]),
    ("L11 C strings read as code", [("(?<!\\w)[bc]?r(?P<hashes>", "(?<!\\w)b?r(?P<hashes>"), ('(?<!\\w)[bc]?"(?:', '(?<!\\w)b?"(?:')]),
    ("L12 characters read as code", [(CHAR, '")')]),
    ("L13 a lifetime read as a character", [(CHAR, """|(?<!\\w)b?'[^']*'")""")]),
    ("L14 an attribute ends at its first ]", [('depth += 1 if b.group("open") else -1 if b.group("close") else 0',
                                              'depth += -1 if b.group("close") else 0')]),
    # a declaration as rustc reads it (verifier round 1, D2)
    ("D1 the keyword `mod` at a word's end", [('state = 1 if word == "mod" else 0', 'state = 1 if word.endswith("mod") else 0')]),
    ("D2 raw identifiers not words", [("|(?P<word>(?:r#)?[^\\W\\d]\\w*)", "|(?P<word>[^\\W\\d]\\w*)")]),
    ("D3 a raw name keeps its r#", [('name, state = (word[2:] if word.startswith("r#") else word), 2', "name, state = word, 2")]),
    ("D4 ASCII names only", [("|(?P<word>(?:r#)?[^\\W\\d]\\w*)", "|(?P<word>(?:r#)?[A-Za-z_]\\w*)")]),
    ("D5 the pre-check wants `mod name;` on its own", [('RUST_MOD_WORD = re.compile(r"(?<!\\w)mod(?!\\w)")',
                                                         'RUST_MOD_WORD = re.compile(r"(?<!\\w)mod\\s+(?:r#)?\\w+\\s*;")')]),
    ("D6 anything between the words is skipped", [("        if RUST_SPACE.match(text, pos, m.start()).end() != m.start():\n            state = 0",
                                                   "        if False:\n            state = 0")]),
    ("D7 Python's whitespace for Rust's", [('RUST_SPACE = re.compile(r"[\\t\\n\\v\\f\\r \\x85\\u200e\\u200f\\u2028\\u2029]*")',
                                            'RUST_SPACE = re.compile(r"\\s*")')]),
    ("D8 a block comment ends a declaration", [("            pos = rust_comment_end(text, pos)\n            continue",
                                                "            pos, state = rust_comment_end(text, pos), 0\n            continue")]),
    ("D9 a line comment ends a declaration", [('            if not m.group().startswith("//"):\n                state = 0',
                                               "            state = 0")]),
    # the tripwire (R6, R7) and fix-lock on (R9)
    ('T1 #![cfg(test)] is not a marker', [('RUST_INLINE_TEST = re.compile(r"^[ \\t]*#\\s*(?:!\\s*)?\\[', 'RUST_INLINE_TEST = re.compile(r"^[ \\t]*#\\s*\\[')]),
    ("S1 the scanner's attribute pattern squares (verifier round 2, F1)", [('(?P<attr>#\\s*(?:(?P<inner>!)\\s*)?\\[)', '(?P<attr>#\\s*(?P<inner>!)?\\s*\\[)')]),
    ("S2 the tripwire's marker squares", [('RUST_INLINE_TEST = re.compile(r"^[ \\t]*#\\s*(?:!\\s*)?\\[', 'RUST_INLINE_TEST = re.compile(r"^[ \\t]*#\\s*!?\\s*\\[')]),
    ('S3 the path pattern squares', [("RUST_PATH = re.compile(r'#\\s*(?:!\\s*)?\\[", "RUST_PATH = re.compile(r'#\\s*!?\\s*\\[")]),
    ("T2 test modules not checked", [("in test_modules(root, tracked,", "in test_modules(root, [],")]),
    ("T3 a module no glob names counts as covered", [("covered = bool(inline_rules(child, cfg)) and test_module_parent", "covered = test_module_parent")]),
    ("T4 the lock's lookup not consulted", [("covered = bool(inline_rules(child, cfg)) and test_module_parent(child, root, cfg) is not None",
                                             "covered = bool(inline_rules(child, cfg))")]),
    ("T5 a module that is nowhere is not named", [("        elif not any(os.path.lexists(os.path.join(root, p)) for p in places) and parent not in out:",
                                                   "        elif False:")]),
    ("T6 nowhere judged by one place", [("        elif not any(os.path.lexists(os.path.join(root, p)) for p in places) and parent not in out:",
                                         "        elif not os.path.lexists(os.path.join(root, child)) and parent not in out:")]),
    ("T7 untracked modules count", [("        if child in known:", "        if os.path.lexists(os.path.join(root, child)):")]),
    ("T8 any attribute marks a test module", [("lambda _rel, attr: bool(RUST_INLINE_TEST.match(attr))", "lambda _rel, attr: True")]),
    ("T9 a lookup error counts as covered", [("            except OSError:\n                covered = False", "            except OSError:\n                covered = True")]),
    ("W1 the old warning", [('"guard-config.json covers them, or the guard cannot follow the test module\'s declaration "\n'
                             '                  "(a #[path] out of its folder, or no such file): %s%s"', '"guard-config.json covers them: %s%s"')]),
]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


orig = open(G, "rb").read()
before = sha(G)
if "--dry" in sys.argv:  # only check that every substitution finds its text once
    for name, subs in MUTANTS:
        for a, _b in subs:
            if orig.decode().count(a) != 1:
                print("NOT ONCE (%d): %s: %r" % (orig.decode().count(a), name, a))
    sys.exit(0)
rows = []
try:
    for name, subs in MUTANTS:
        src = orig.decode()
        for a, b in subs:
            assert src.count(a) == 1, (name, a, src.count(a))
            src = src.replace(a, b)
        with open(G, "w") as f:
            f.write(src)
        r = subprocess.run(GUARD_TESTS, capture_output=True, text=True)
        fails = sorted({line.split("(")[0].split(":", 1)[1].strip() for line in r.stderr.splitlines()
                        if line.startswith(("FAIL:", "ERROR:"))})
        rows.append("%-52s %s %s" % (name, "RED  " if r.returncode else "GREEN", ", ".join(fails)[:150]))
        with open(G, "wb") as f:
            f.write(orig)
finally:
    with open(G, "wb") as f:
        f.write(orig)
    assert sha(G) == before
print("\n".join(rows))
print("%d of %d red; restored, sha256 checked: %s %s" % (sum("RED" in r for r in rows), len(rows), G, before[:12]))
