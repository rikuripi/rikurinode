"""Mutants of the test-module and `#![cfg(test)]` change, against guard.py as
it will be committed. Run from the repository root inside safe-run.sh. Python
runs with -B (no bytecode cache: a same-size mutant's stale .pyc can outlive
its restore). The file is restored and checked by sha256. `--dry` only checks
that every substitution finds its text exactly once."""
import hashlib
import subprocess
import sys

GUARD_TESTS = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
TIMEOUT = 300  # the suite takes about 25 s
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
    ("E5 a test module's own modules are not tests", [('                if rel not in found and not marked:', '                if not marked:')]),
    ("E6 only the edited file's own folder", [("        if not folder:\n            break\n        folder = os.path.dirname(folder)",
                                               "        break")]),
    ("E7 a new folder is an error", [("        except (FileNotFoundError, NotADirectoryError):\n            names = []",
                                      "        except ():\n            names = []")]),
    ("E8 an unreadable file stops the check", [("        except (OSError, UnicodeDecodeError):\n            continue\n        except _TooBig:",
                                                "        except ():\n            continue\n        except _TooBig:")]),
    ("E9 the token search ignores the deadline", [("        if time.time() > deadline:\n            raise _TooSlow()\n        s = start.search(text, pos)",
                                                   "        s = start.search(text, pos)")]),
    ("E10 the lookup gets no time budget", [("test_module_parent(rel, root, cfg, _DEADLINE_ALL)", "test_module_parent(rel, root, cfg)")]),
    # the declaration of a file that is all tests (verifier round 1, D4)
    ("F1 the parent's declaration is not checked", [("    kept = [repr(d) for d in test_file_declarations(rel, before, root, cfg, _DEADLINE_ALL)]",
                                                     "    kept = []")]),
    ("F2 the module file's rules not read (the edited file's instead)", [('                rules = inline_rules(p, cfg)', '                rules = inline_rules(rel, cfg)')]),
    ("F4 comments read as code in the file's attributes", [('        if m.group("comment"):\n            pos = rust_comment_end(text, pos, deadline)\n        elif m.group("string"):',
                                                             '        if False:\n            pos = rust_comment_end(text, pos, deadline)\n        elif m.group("string"):')]),
    ("F7 only the file's first inner attribute", [('                out.append(text[m.start():end])', '                return out + [text[m.start():end]]')]),
    ("F11 the lookup checks the deadline only inside files", [("    for rel in rels:\n        if time.time() > deadline:\n            raise _TooSlow()\n", "    for rel in rels:\n")]),
    ("F8 an outer attribute counts as the file's", [('            if m.group("inner") and depth == 0:', '            if depth == 0:')]),
    ("F9 an inner attribute in a block counts as the file's", [('            if m.group("inner") and depth == 0:', '            if m.group("inner"):')]),
    ("F10 blocks not tracked in the file's attributes", [('            depth += 1\n        elif m.group("close"):\n            depth = max(depth - 1, 0)', '            depth += 0\n        elif m.group("close"):\n            depth = max(depth - 1, 0)')]),
    ("F12 the edit's declarations looked up in a list (round 7)", [("        left = {repr(d) for d in test_file_declarations(rel, a, root, cfg, _DEADLINE_ALL)}",
                                                                    "        left = [repr(d) for d in test_file_declarations(rel, a, root, cfg, _DEADLINE_ALL)]")]),
    ("F13 each module file read again per declaration (round 7)", [("            if p not in whole:\n", "            if True:\n")]),
    # attributes kept once and capped in scope (verifier round 3, I1; round 4, N4)
    ('C1 no cap', [('        where.append(attr if held < RUST_MAX_ATTRS else RUST_TOO_MANY)', '        where.append(attr)')]),
    ('C2 a repeated attribute counts again', [('        if held > RUST_MAX_ATTRS or attr in where[start:]:', '        if held > RUST_MAX_ATTRS:')]),
    ('C3 the cap one late', [('attr if held < RUST_MAX_ATTRS else', 'attr if held <= RUST_MAX_ATTRS else')]),
    ("C4 a closed block's attributes stay in scope", [('                del scope[start:]\n', '')]),
    ("C5 a declared item's attributes stay in scope", [('        pending, path, state = [], None, 0\n\n\ndef module_files', '        path, state = None, 0\n\n\ndef module_files')]),
    ('C6 past the cap, not test code', [('RUST_TOO_MANY = "#[cfg(test)] /*', 'RUST_TOO_MANY = "#[allow(unused)] /*')]),
    ("C7 the cap's marker once per block (N4)", [('        if held > RUST_MAX_ATTRS or attr in where[start:]:', '        if attr in where[start:]:')]),
    ("F3 the edit's result is not read", [("        left = {repr(d) for d in test_file_declarations(rel, a, root, cfg, _DEADLINE_ALL)}",
                                           "        left = set(kept)")]),
    # attributes that apply (R2)
    ("A1 the blocks' inner attributes ignored", [("                keep(scope, frames[-1][0], attr)\n", "                pass\n")]),
    ("A2 the file's inner attributes ignored", [("                keep(scope, 0, attr)\n", "                pass\n")]),
    ("A3 the declaration's own attributes ignored", [("                    attrs = scope + pending\n", "                    attrs = list(scope)\n")]),
    ("A4 a block does not take the attributes before it", [("            scope += pending  # now the block's: still in scope\n", "            pass\n")]),
    ("A5 `;` does not end an attribute's reach", [('        elif m.group("semi"):\n            if state == 2:',
                                                   '        elif m.group("semi") and state != 2:\n            continue\n        elif m.group("semi"):\n            if state == 2:')]),
    ("A6 a later inner attribute leaves the shared list stale", [("        if where is scope:\n            shared = None\n", "")]),
    ("A7 an opened block leaves the shared list stale", [("            scope += pending  # now the block's: still in scope\n            shared = None\n",
                                                           "            scope += pending  # now the block's: still in scope\n")]),
    ("A8 a closed block leaves the shared list stale", [("                    names.pop()\n            shared = None\n", "                    names.pop()\n")]),
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
    ("P9 a declaration's #[path] ignored", [("                out.append((name, list(names), path, attrs))", "                out.append((name, list(names), None, attrs))")]),
    ("P10 an inline module's #[path] ignored", [("                names.append(path or name)", "                names.append(name)")]),
    ("P11 the inline modules ignored", [("                out.append((name, list(names), path, attrs))", "                out.append((name, [], path, attrs))")]),
    ("P12 a module's inner #![path] ignored", [("                    names[-1] = inner_path\n", "                    pass\n")]),
    ("P13 #![path] names a function's block too", [("                if inner_path is not None and frames[-1][1]:", "                if inner_path is not None:")]),
    ("P14 a declaration's #[path] dropped past the cap (N2)", [("                out.append((name, list(names), path, attrs))",
                                                                "                out.append((name, list(names), next((p for p in map(rust_path, attrs) if p), None), attrs))")]),
    ("P15 a path need not be the whole attribute", [("    if end == len(attr) or not RUST_PATH_END.match(attr, end):", "    if end == len(attr):")]),
    ("P16 a path keeps its closing quote", [("    return attr[m.end():end - 1]", "    return attr[m.end():end]")]),
    # literals are not code (R4), comments nest, unclosed runs to the end (D1, D5, D7)
    ("L1 line comments read as code", [('RUST_SKIP = (r"//[^\\n]*"', 'RUST_SKIP = (r"(?!x)x"')]),
    ("L2 block comments read as code", [('RUST_SCAN = re.compile(r"(?P<comment>/\\*)|"', 'RUST_SCAN = re.compile(r"(?P<comment>(?!x)x)|"')]),
    ("L3 block comments do not nest", [('depth += 1 if m.group() == "/*" else -1', 'depth -= 1 if m.group() == "*/" else 0')]),
    ('L4 an unclosed comment skips only its opener', [('            return m.end()\n    return len(text)\n\n\ndef rust_string_end', '            return m.end()\n    return pos\n\n\ndef rust_string_end')]),
    ("L5 raw strings read as code", [("""             r'|(?<!\\w)[bc]?r(?P<hashes>#*)"[\\s\\S]*?(?:"(?P=hashes)|\\Z)'\n""", "")]),
    ("L6 a raw string runs to its last closer", [("""r(?P<hashes>#*)"[\\s\\S]*?(?:""", """r(?P<hashes>#*)"[\\s\\S]*(?:""")]),
    ("L7 an unclosed raw string is retried", [("""[\\s\\S]*?(?:"(?P=hashes)|\\Z)""", """[\\s\\S]*?"(?P=hashes)""")]),
    ("L8 strings read as code", [(r"""             r'|(?P<string>(?<!\w)[bc]?")'""" + "\n", "")]),
    ("L9 escapes in a string ignored", [(r"""RUST_STRING_BODY = re.compile(r'[^"\\]*(?:\\[\s\S][^"\\]*){0,1000}')""", r"""RUST_STRING_BODY = re.compile(r'[^"]*')""")]),
    ("L10 an unclosed string skips only its quote", [("            pos, state = rust_string_end(text, pos, deadline), 0\n",
                                                      "            end = rust_string_end(text, pos, deadline)\n            pos, state = (end if end < len(text) else pos), 0\n")]),
    ("L11 C strings read as code", [(r"(?<!\w)[bc]?r(?P<hashes>", r"(?<!\w)b?r(?P<hashes>"), (r'(?P<string>(?<!\w)[bc]?")', r'(?P<string>(?<!\w)b?")')]),
    ("L12 characters read as code", [(CHAR, '")')]),
    ("L13 a lifetime read as a character", [(CHAR, """|(?<!\\w)b?'[^']*'")""")]),
    ("L14 an attribute ends at its first ]", [('            depth += len(b.group("open"))', '            depth += 0')]),
    ("L15 a run of ] past the attribute's own", [("                return pos + depth  # just past", "                return pos  # just past")]),
    # one step inside a literal keeps to the deadline and to little memory (verifier round 4, N1)
    ("N1 a comment ignores the deadline", [("    for m in RUST_COMMENT_MARK.finditer(text, pos):\n        if time.time() > deadline:\n            raise _TooSlow()\n",
                                            "    for m in RUST_COMMENT_MARK.finditer(text, pos):\n")]),
    ("N2 a string ignores the deadline", [("    while True:\n        if time.time() > deadline:\n            raise _TooSlow()\n        pos = RUST_STRING_BODY",
                                           "    while True:\n        pos = RUST_STRING_BODY")]),
    ("N3 an attribute ignores the deadline", [("        b = rust_next(RUST_BRACKET, RUST_BRACKET_START, text, pos, deadline)",
                                               '        b = rust_next(RUST_BRACKET, RUST_BRACKET_START, text, pos, float("inf"))')]),
    ("N4 the module scan gives an attribute no deadline", [("            end = rust_attr_end(text, pos, deadline)\n            attr, pos, state",
                                                            "            end = rust_attr_end(text, pos)\n            attr, pos, state")]),
    ("N5 the module scan gives a comment no deadline", [("            pos = rust_comment_end(text, pos, deadline)\n            continue",
                                                         "            pos = rust_comment_end(text, pos)\n            continue")]),
    ("N6 one search for a whole token", [("        s = start.search(text, pos)\n        if s is None:\n            return None\n        m = scan.match(text, s.start())\n"
                                          "        if m is not None:\n            return m\n        pos = s.start() + 1", "        return scan.search(text, pos)")]),
    ("N7 brackets one at a time", [(r'r"|(?P<open>\[+)|(?P<close>\]+)")', r'r"|(?P<open>\[)|(?P<close>\])")')]),
    ("N8 a string's body in one unbounded step", [(r"""(?:\\[\s\S][^"\\]*){0,1000}""", r"""(?:\\[\s\S][^"\\]*)*""")]),
    ("N9 a string ends at its first 1,000 escapes", [("        if pos + 1 >= len(text):  # never closed", "        if True:  # never closed")]),
    ("N10 a `\\` that ends the file loops", [("        if pos + 1 >= len(text):  # never closed", "        if pos >= len(text):  # never closed")]),
    ("N11 non-ASCII names start no token", [("{};A-Za-z_", "{};A-Za-z_]|(?!x)x[")]),
    ("N12 a quote in an attribute starts no string", [(r'''RUST_BRACKET_START = re.compile(r"[/\"'\[\]bcr]")''', r'''RUST_BRACKET_START = re.compile(r"[/'\[\]bcr]")''')]),
    # a file too big to check (round 7: RUST_MAX_BYTES, RUST_MAX_KEPT; verifier round 4, N1, N4)
    ("K1 inline modules not counted", [("                kept += 1 + len(names)", "                kept += 1")]),
    ("K2 a declaration's own list not counted", [("                    kept += len(attrs)\n", "")]),
    ("K3 a shared list not counted", [("                        kept += len(shared)\n", "")]),
    ("K4 no cap on what a file keeps", [("                if kept > RUST_MAX_KEPT:", "                if False:")]),
    ("K5 no cap on a file read", [("    if os.path.getsize(path) > RUST_MAX_BYTES:", "    if False:")]),
    ("K6 no cap on a text scanned", [("    if len(text) > RUST_MAX_BYTES:\n        raise _TooBig()\n    out, pending, scope", "    out, pending, scope")]),
    ("K7 a file too big passed over silently", [("            unchecked.append(rel)\n            continue", "            continue")]),
    ("K8 too big outranks a test module found", [("    if rel in found:\n        return found[rel][0]\n    if unchecked:\n        raise _TooBig()\n",
                                                  "    if unchecked:\n        raise _TooBig()\n    if rel in found:\n        return found[rel][0]\n")]),
    ("K9 a file too big does not stop the lookup", [("    if unchecked:\n        raise _TooBig()\n    return None", "    return None")]),
    ("K10 each declaration's list matched again", [("                if id(attrs) not in lists:", "                if True:")]),
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
    ("D8 a block comment ends a declaration", [("            pos = rust_comment_end(text, pos, deadline)\n            continue",
                                                "            pos, state = rust_comment_end(text, pos, deadline), 0\n            continue")]),
    ("D9 a line comment ends a declaration", [('            if not m.group().startswith("//"):\n                state = 0',
                                               "            state = 0")]),
    # the tripwire (R6, R7) and fix-lock on (R9)
    ('T1 #![cfg(test)] is not a marker', [('RUST_INLINE_TEST = re.compile(r"^[ \\t]*#\\s*(?:!\\s*)?\\[', 'RUST_INLINE_TEST = re.compile(r"^[ \\t]*#\\s*\\[')]),
    ("S1 the scanner's attribute pattern squares (verifier round 2, F1)", [('(?P<attr>#\\s*(?:(?P<inner>!)\\s*)?\\[)', '(?P<attr>#\\s*(?P<inner>!)?\\s*\\[)')]),
    ("S2 the tripwire's marker squares", [('RUST_INLINE_TEST = re.compile(r"^[ \\t]*#\\s*(?:!\\s*)?\\[', 'RUST_INLINE_TEST = re.compile(r"^[ \\t]*#\\s*!?\\s*\\[')]),
    ('S3 the path pattern squares', [("RUST_PATH = re.compile(r'#\\s*(?:!\\s*)?\\[", "RUST_PATH = re.compile(r'#\\s*!?\\s*\\[")]),
    ("T2 test modules not checked", [("        modules = test_modules(root, tracked, lambda", "        modules = test_modules(root, [], lambda")]),
    ("T3 a module no glob names counts as covered", [("                    covered = (bool(inline_rules(child, cfg))\n", "                    covered = (True\n")]),
    ("T4 the lock's lookup not consulted", [("                               and test_module_parent(child, root, cfg, deadline) is not None)",
                                             "                               and True)")]),
    ("T5 a module that is nowhere is not named", [("        elif not any(os.path.lexists(os.path.join(root, p)) for p in places) and parent not in out:",
                                                   "        elif False:")]),
    ("T6 nowhere judged by one place", [("        elif not any(os.path.lexists(os.path.join(root, p)) for p in places) and parent not in out:",
                                         "        elif not os.path.lexists(os.path.join(root, child)) and parent not in out:")]),
    ("T7 untracked modules count", [("        if child in known:", "        if os.path.lexists(os.path.join(root, child)):")]),
    ("T8 any attribute marks a test module", [("lambda _rel, attr: bool(RUST_INLINE_TEST.match(attr))", "lambda _rel, attr: True")]),
    ("T9 a lookup error counts as covered", [("                except (OSError, _TooBig):\n                    covered = False",
                                              "                except (OSError, _TooBig):\n                    covered = True")]),
    ("T10 the tripwire has no time budget (N5)", [("    deadline = time.time() + TRIPWIRE_TIME_BUDGET", '    deadline = float("inf")')]),
    ("T11 its own reading ignores the budget", [(r'''        for raw in filter(None, proc.stdout.split(b"\0")):''' + "\n            if time.time() > deadline:\n                raise _TooSlow()\n",
                                                 r'''        for raw in filter(None, proc.stdout.split(b"\0")):''' + "\n")]),
    ("T12 its lookup ignores the budget", [("lambda _rel, attr: bool(RUST_INLINE_TEST.match(attr)), deadline,",
                                            'lambda _rel, attr: bool(RUST_INLINE_TEST.match(attr)), float("inf"),')]),
    ("T13 a file too big is not named", [("        out += [rel for rel in unchecked if rel not in out]\n", "")]),
    ("T14 a too-big file stops the module check", [("                except (OSError, _TooBig):\n                    covered = False",
                                                    "                except OSError:\n                    covered = False")]),
    ("T15 a timed-out tripwire is not an error", [("    except _TooSlow:\n        raise OSError(", "    except ZeroDivisionError:\n        raise OSError(")]),
    ("W1 the old warning", [('"guard-config.json covers them, or the guard cannot follow the test module\'s declaration "\n'
                             '                  "(a #[path] out of its folder, no such file, or a file too big to check): %s%s"',
                             '"guard-config.json covers them: %s%s"')]),
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
        try:
            r = subprocess.run(GUARD_TESTS, capture_output=True, text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:  # a mutant that hangs the suite is caught: it never passes
            rows.append("%-52s RED   (the suite did not finish in %d s)" % (name, TIMEOUT))
        else:
            fails = sorted({line.split("(")[0].split(":", 1)[1].strip() for line in r.stderr.splitlines()
                            if line.startswith(("FAIL:", "ERROR:"))})
            rows.append(("%-52s %s %s" % (name, "RED  " if r.returncode else "GREEN", ", ".join(fails)[:150])).rstrip())
        with open(G, "wb") as f:
            f.write(orig)
finally:
    with open(G, "wb") as f:
        f.write(orig)
    assert sha(G) == before
print("\n".join(rows))
print("%d of %d red; restored, sha256 checked: %s %s" % (sum("RED" in r for r in rows), len(rows), G, before[:12]))
