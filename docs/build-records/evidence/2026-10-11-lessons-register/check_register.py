"""Mechanical fact-check of lessons-register.md against its sources.

Sources, beside this script: lessons-harvest.json (the 475 lessons) and
requirement-lessons.json (requirement -> lesson indices); and the previous
repository's build records and files at HEAD, read-only (git ls-tree, never a
checkout), at OLD below — a path on the owner's machine.

Usage: check_register.py [register.md]   (default: docs/requirements/lessons-register.md)
"""
import collections
import json
import os
import re
import subprocess
import sys

S = os.path.dirname(os.path.abspath(__file__))
OLD = "/home/junc/rikuri/rikurinode"
# newline="": a carriage return stays visible to the alphabet check (universal
# newlines would turn it into a line break first; round 10's verifier, A1b/A1c)
REG = open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(S, "..", "..", "..", "requirements",
                                                           "lessons-register.md"), newline="").read()
LESSONS = json.load(open(os.path.join(S, "lessons-harvest.json")))
problems = []


def bad(msg):
    problems.append(msg)


# --- the requirement -> lesson mapping ------------------------------------------
with open(os.path.join(S, "requirement-lessons.json")) as f:
    reqs = {k: {"lessons": v} for k, v in json.load(f)["requirements"].items()}
idx = [i for r in reqs.values() for i in r.get("lessons", [])]
base = 1 if min(idx) == 1 and max(idx) == len(LESSONS) else 0
print("requirements", len(reqs), "lesson refs", len(idx), "distinct", len(set(idx)), "index base", base)
if sorted(idx) != list(range(base, base + len(LESSONS))):
    missing = sorted(set(range(base, base + len(LESSONS))) - set(idx))
    dup = [i for i, n in collections.Counter(idx).items() if n > 1]
    bad("lesson mapping: missing %s, duplicated %s" % (missing[:20], dup[:20]))


def lesson(i):
    return LESSONS[i - base]


# --- contents table: requirements and lessons per theme ---------------------------
for m in re.finditer(r"\| \[(\w+) — [^\]]*\]\(#\w+\) \| (\d+) \((\w+)-01 to \w+-(\d+)\) \| (\d+) \|", REG):
    theme, n, _, last, nles = m.group(1), int(m.group(2)), m.group(3), int(m.group(4)), int(m.group(5))
    ids = [k for k in reqs if k.split("-")[0] == theme]
    got = sum(len(reqs[k]["lessons"]) for k in ids)
    if len(ids) != n or last != n or got != nles:
        bad("contents %s: says %d reqs / %d lessons; mapping has %d reqs / %d lessons" % (theme, n, nles, len(ids), got))

# --- every requirement in the register matches reqs.txt titles ----------------------
reg_ids = re.findall(r"^#### (\w+-\d+) — (.*)$", REG, re.M)
if [i for i, _ in reg_ids] != list(reqs):
    bad("requirement ids/order differ between register and mapping")

# --- cited records exist ---------------------------------------------------------------
records = set(os.listdir(os.path.join(OLD, "docs", "build-records")))
cited = set(re.findall(r"\d{4}-\d{2}-\d{2}-[\w.+-]+?\.md", REG))
for r in sorted(cited - records):
    bad("cited record does not exist: " + r)
harvest_records = {x["record"] for x in LESSONS}
print("records cited", len(cited), "in old repo", len(records - {"README.md"}), "harvested", len(harvest_records))
if harvest_records != records - {"README.md"}:
    bad("harvest records differ from the folder: only harvest %s, only folder %s" % (
        sorted(harvest_records - records), sorted(records - {"README.md"} - harvest_records)))

def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("—", "-").replace("–", "-")
    s = re.sub(r"[*`]", "", s)
    return re.sub(r"\s+", " ", s).strip()             # case kept: a quotation is matched as written


rec_text = {}


def text_of(rec):
    if rec not in rec_text:
        rec_text[rec] = norm(open(os.path.join(OLD, "docs", "build-records", rec), errors="replace").read())
    return rec_text[rec]


CHUNK = re.compile(r"\n\s*\n|\n(?=(?:[-*+]|\d+\.)\s|\s*\||#)")


def said_in(rec):
    """The passages a record puts between quotation marks, paired within one
    paragraph, top-level list item (with its sub-items) or table row, after
    an empty pair ("") is dropped. A part left with an odd number of marks is
    skipped: pairing it would be a guess. A stray mark that leaves the count
    even still mis-pairs its part. This reads markup, not speakers: whose
    words a quotation is, the checker cannot tell."""
    if rec not in said:
        raw = open(os.path.join(OLD, "docs", "build-records", rec), errors="replace").read()
        raw = raw.replace("\u201c", '"').replace("\u201d", '"')
        parts = [part.replace('""', "") for part in CHUNK.split(raw)]
        odd = [part for part in parts if part.count('"') % 2]
        skipped.append(len(odd))
        runs = [q for part in parts if part not in odd for q in re.findall(r'"([^"]+)"', part)]
        said[rec] = [norm(x) for x in runs]
    return said[rec]


said = {}
# Options the owner chose that their record bolds instead of quoting, read by
# hand: 2026-09-29-market-intel-freshness-arkb.md lines 56-71, under "Owner's
# choices (AskUserQuestion, 2026-09-29, costs stated)". No other bold text counts.
OPTION_LABELS = {("2026-09-29-market-intel-freshness-arkb.md", norm(x)) for x in (
    "Stale data: page + Guardian alert (Recommended)", "ARKB (Recommended)", "all spot ETFs (Recommended)",
    "MAs + returns backup:", "funding: a second venue")}
skipped = []   # per record read: parts with an odd number of quotation marks


# The Owner fields' alphabet: printable ASCII and these. A character outside
# it is reported, not read: a new one is added here only after it is checked
# not to mark a quotation (closed-world, verifier round 7).
OWNER_ALPHABET = set(chr(c) for c in range(32, 127)) | set("“”‘’—–…→")


def owner_quotations(line):
    """The quotations in an Owner line, read closed-world: “…”, "…", ‘…’ and
    '…' (an apostrophe inside a word may sit within them), outside code spans.
    Reported, never passed: a character outside OWNER_ALPHABET; an HTML
    entity, tag or blockquote; a backslash or a lone backtick; a quotation
    mark left unpaired or reversed; an empty quotation, or one of code only.
    Returns (quotations, problems)."""
    problems = []
    odd = sorted({c for c in line if c not in OWNER_ALPHABET})
    if odd:
        problems.append("characters outside the Owner fields' alphabet (%s)" % ", ".join(
            "U+%04X" % ord(c) for c in odd))
    if re.search(r"&#?\w+;|<[A-Za-z/!]", line):
        problems.append("an HTML entity or tag")
    if "\\" in line:
        problems.append("a backslash")
    code = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")   # a code span: backtick runs of equal length
    if any(re.search(r"[“”‘’]", m.group(2)) for m in code.finditer(line)):
        problems.append("curly quotation marks inside a code span")
    plain = code.sub("`", line)                   # a code span becomes one `
    if "`" in code.sub("", line):
        problems.append("a lone backtick")
    spans = []

    def take(m):
        spans.append(m.group(1))
        return " "
    rest = re.sub(r"“([^“”]*)”", take, plain)
    rest = re.sub(r'"([^"]*)"', take, rest)
    # letters and digits, not \\w (which holds _): in _'…'_ the quotation sits in emphasis
    an = "A-Za-z0-9"
    rest = re.sub(r"(?<![%s])‘((?:[^‘’]|(?<=[%s])’(?=[%s]))*)’(?![%s])" % (an, an, an, an), take, rest)
    rest = re.sub(r"(?<![%s])'((?:[^']|(?<=[%s])'(?=[%s]))*)'(?![%s])" % (an, an, an, an), take, rest)
    rest = re.sub(r"(?<=[%s])['’](?=[%s])|(?<=s)['’](?![%s])" % (an, an, an), "", rest)   # it's, owner’s, owners'
    left = [c for c in rest if c in "\"“”‘’'"]
    if left:
        problems.append("quotation marks it cannot pair (%s)" % "".join(left))
    if any(not s.strip(" `.,;:") for s in spans):
        problems.append("an empty quotation, or one of code only")
    return spans, problems


def within(span, text):
    """`span`, normalised, is in `text` as whole words (so “OK” is not found
    inside "took")."""
    s = norm(span).strip(" .")
    return re.search(r"(?<!\w)" + re.escape(s) + r"(?!\w)", text) is not None


owner_quote_misses = []
# --- each requirement's Why cites only records that fed it -------------------------------
blocks = re.split(r"^#### ", REG, flags=re.M)[1:]
for b in blocks:
    rid = b.split(" ", 1)[0]
    if rid not in reqs:
        continue
    fed = {lesson(i)["record"] for i in reqs[rid]["lessons"]}
    why = re.search(r"\*\*Why:\*\*(.*?)(?=\n- \*\*|\Z)", b, re.S)
    if not why:
        bad(rid + ": no Why")
        continue
    why_recs = set(re.findall(r"\d{4}-\d{2}-\d{2}-[\w.+-]+?\.md", why.group(1)))
    extra = why_recs - fed
    if extra:
        bad("%s Why cites records that did not feed it: %s" % (rid, sorted(extra)))
    more = re.search(r"\+(\d+) more", why.group(1))
    n_more = int(more.group(1)) if more else 0
    if len(why_recs) + n_more != len(fed):
        bad("%s Why cites %d records + %d more = %d, but %d records fed it" % (
            rid, len(why_recs), n_more, len(why_recs) + n_more, len(fed)))
    # every “…” in an Owner line must be words its cited record(s) contain,
    # and words the record itself quotes (or bolds as a chosen option):
    # quotation marks are for what the record quotes, never for its prose
    # a requirement's body (to the next anchor or heading) holds only its six fields at column 0
    body = re.split(r"\n(?=<a id=|#)", b, maxsplit=1)[0]
    for line_ in body.split("\n")[1:]:
        if line_ and not line_[0].isspace() and not re.match(
                r"- \*\*(?:Rule|Why|Tripwire|Owner|Port|Superseded / caveat):\*\*", line_):
            owner_quote_misses.append("%s: a line at column 0 that is not one of the requirement's fields: %s" % (rid, line_[:60]))
    # an Owner field is written `- **Owner:**` and nothing like it
    for label in re.findall(r"^[ \t]*[-*+][ \t]+(?:\*\*?|__?)[ \t]*Owner\b.*$", b, re.M):
        if not label.startswith("- **Owner:**"):
            owner_quote_misses.append("%s: an Owner field not written `- **Owner:**`: %s" % (rid, label[:60]))
    # an Owner section ends at the next field, at a heading, or at a blank line
    # followed by a line at column 0 (anything indented still belongs to it)
    for q in re.findall(r"\*\*Owner:\*\*(.*?)(?=\n- \*\*|\n {0,3}#{1,6}(?:[ \t]|$)|\n\s*\n(?=\S)|\Z)", b, re.S | re.M):
        for raw in q.split("\n"):
            if re.match(r"\s*(?:(?:[-*+]|\d+[.)])\s+)*>", raw):
                owner_quote_misses.append("%s: a blockquote in an Owner field: %s" % (rid, raw.strip()[:60]))
        for item in re.split(r"\n(?=\s*- )", q.strip()):
            line = re.sub(r"\s*\n\s*", " ", item)   # an item wrapped over lines is one line
            recs = re.findall(r"\d{4}-\d{2}-\d{2}-[\w.+-]+?\.md", line)
            spans, unread = owner_quotations(line)
            for why in unread:
                owner_quote_misses.append("%s: %s in “%s”" % (rid, why, line[:90]))
            for span in spans:
                if not span.strip(" `.,;:"):
                    continue
                if re.search(r"[*`]", span):
                    owner_quote_misses.append("%s: “%s” carries Markdown of its own" % (rid, span[:90]))
                elif not recs or not any(within(span, text_of(r)) for r in recs):
                    owner_quote_misses.append("%s: “%s” is not in its record (%s)" % (rid, span[:90], ", ".join(recs) or "no record"))
                elif not any(within(span, run) for r in recs for run in said_in(r)) \
                        and not any((r, norm(span)) in OPTION_LABELS for r in recs):
                    owner_quote_misses.append("%s: “%s” is the record's own prose, not words it quotes (%s)"
                                              % (rid, span[:90], ", ".join(recs)))

# --- coverage table ------------------------------------------------------------------------
per_record = collections.defaultdict(lambda: [0, set()])
for rid, r in reqs.items():
    for i in r["lessons"]:
        rec = lesson(i)["record"]
        per_record[rec][0] += 1
        per_record[rec][1].add(rid)
order = {k: n for n, k in enumerate(reqs)}
rows = re.findall(r"^\| (\d+) \| (\d{4}-\d{2}-\d{2}-[^|]+?\.md) \| (\d+) \| ([^|]*) \|$", REG, re.M)
print("coverage rows", len(rows))
for _, rec, n, fed in rows:
    want_n, want_fed = per_record.get(rec, [0, set()])
    got_fed = {x.strip() for x in fed.split(",") if x.strip()}
    if int(n) != want_n or got_fed != want_fed:
        bad("coverage %s: says %s lessons %s; mapping %d %s" % (rec, n, sorted(got_fed), want_n, sorted(want_fed)))
if len(rows) != len(harvest_records):
    bad("coverage has %d rows for %d records" % (len(rows), len(harvest_records)))

# --- the file as a whole: closed-world on characters and markup ---------------------------------
# The register's alphabet: printable ASCII and these. A new character is added
# here only after it is checked not to mark a quotation or hide a label.
FILE_ALPHABET = set(chr(c) for c in range(32, 127)) | set("\n—“”…→–×·≤‘’✓≥°")
for n, text in enumerate(REG.split("\n"), 1):
    odd = sorted({c for c in text if c not in FILE_ALPHABET})
    if odd:
        bad("line %d: characters outside the register's alphabet (%s)" % (n, ", ".join("U+%04X" % ord(c) for c in odd)))
    for tag in re.findall(r"<[A-Za-z/!?][^>]*>?", re.sub(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", "", text)):
        if not re.fullmatch(r'<a id="[a-z]+">|</a>|<br>', tag):
            bad("line %d: an HTML tag the register does not use: %s" % (n, tag[:40]))
    if re.search(r"&#?\w+;", text):
        bad("line %d: an HTML entity" % n)
    if re.match(r"\s*(?:(?:[-*+]|\d+[.)])\s+)*(?:\*\*?|__?)\s*(?i:owners?)\b", text) and not re.match(r"- \*\*Owner:\*\*", text):
        bad("line %d: an Owner label not written `- **Owner:**`" % n)
for h in re.findall(r"^#### (.*)$", REG, re.M):
    if not re.match(r"[A-Z]+-\d+ — ", h) or h.split(" ")[0] not in reqs:
        bad("a #### heading that is not a requirement: %s" % h[:60])
first = REG.index("\n#### ")
if re.search(r"^- \*\*Owner:\*\*", REG[:first], re.M):
    bad("an Owner field before the first requirement")

# --- owner decisions section ----------------------------------------------------------------
sec3 = REG[REG.index("## 3. Owner decisions"):REG.index("## 4. Port candidates")]
od_rows = re.findall(r"^\| (\d+) \| (.*) \| ([^|]*\.md[^|]*) \| ([^|]*) \| ([^|]*) \|$", sec3, re.M)
print("owner decision rows", len(od_rows))
# the table runs from its header to the first blank line (GFM continues a table
# until then): every line in it but the header and separator is a five-cell row
HEADER = "| # | Owner decision (verbatim) | Record(s) | Feeds | Status |"
if sec3.count(HEADER) != 1:
    bad("section 3's table header is missing or repeated")
else:
    body = sec3[sec3.index(HEADER):].split("\n\n")[0].split("\n")
    if body[1] != "|---|---|---|---|---|":
        bad("section 3's table separator is not |---|---|---|---|---|")
    table = body[2:]
    five = [x for x in table if re.fullmatch(r"\| (\d+) \| (.*) \| ([^|]*\.md[^|]*) \| ([^|]*) \| ([^|]*) \|", x)]
    if len(five) != len(table) or len(table) != len(od_rows):
        bad("section 3's table has %d lines, %d of them five-cell rows; %d rows read" % (len(table), len(five), len(od_rows)))
    if re.search(r"^\s*\|?.*\|", sec3[sec3.index(HEADER):].split("\n\n", 1)[1] if "\n\n" in sec3[sec3.index(HEADER):] else "", re.M):
        bad("section 3 has a table line after its table")
if [int(r[0]) for r in od_rows] != list(range(1, len(od_rows) + 1)):
    bad("section 3's rows are not numbered 1 to %d in order" % len(od_rows))
od_reqs = collections.defaultdict(set)              # decision -> the requirements its lessons feed
for rid_, r_ in reqs.items():
    for i in r_["lessons"]:
        if lesson(i)["owner_decision"].strip():
            od_reqs[lesson(i)["owner_decision"].strip()].add(rid_)
distinct = collections.OrderedDict()
for i, x in enumerate(LESSONS):
    od = x["owner_decision"].strip()
    if od:
        distinct.setdefault(od, set()).add(x["record"])
# A row may carry a note in its last parentheses, *(…)*: a summary, joined
# answers, or a correction (then the row text may differ from the harvest).
# The notes and the corrected rows' text are a baseline read by hand.
with open(os.path.join(S, "owner-decision-notes.json")) as f:
    baseline = json.load(f)
seen_notes = {}
annotated = 0
harvest = list(distinct)
if len(od_rows) != len(harvest):
    bad("section 3 has %d rows for %d distinct decisions" % (len(od_rows), len(harvest)))
for (num, text, rec_cell, feeds_cell, *_rest), od in zip(od_rows, harvest):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[\w.+-]+?\.md(?:(?:, |<br>)\d{4}-\d{2}-\d{2}-[\w.+-]+?\.md)*", rec_cell.strip()):
        bad("owner decision row %s: its Records cell holds more than record names" % num)
    if {x.strip() for x in feeds_cell.split(",") if x.strip()} != od_reqs[od]:
        bad("owner decision row %s feeds %s; the mapping says %s" % (num, feeds_cell.strip(), sorted(od_reqs[od])))
    if set(re.findall(r"\d{4}-\d{2}-\d{2}-[\w.+-]+?\.md", rec_cell)) != distinct[od]:
        bad("owner decision row %s cites %s; the harvest has it from %s" % (num, rec_cell.strip(), sorted(distinct[od])))
    text = text.replace("\\|", "|")
    m = re.match(r"^(.*) \*\((.*)\)\*$", text)
    base, note = (m.group(1), m.group(2)) if m else (text, "")
    annotated += bool(note)
    if note:
        seen_notes[num] = note
    if num in baseline["corrected_text"]:
        # a corrected row: its note gives the harvest's text, word for word, and
        # its own text is the one read by hand
        if '"%s"' % od not in note.replace("\\|", "|"):
            bad("owner decision row %s: its 'corrected' note does not quote the harvest's text" % num)
        if base != baseline["corrected_text"][num]:
            bad("owner decision row %s: its corrected text differs from the one read by hand" % num)
        continue
    if base != od:
        bad("owner decision row %s not verbatim from the harvest: %r" % (num, base[:100]))
print("owner decision rows annotated:", annotated)
if seen_notes != baseline["notes"]:
    for num in sorted(set(seen_notes) | set(baseline["notes"]), key=int):
        if seen_notes.get(num) != baseline["notes"].get(num):
            bad("owner decision row %s: its note differs from the one read by hand (%r)" % (num, (seen_notes.get(num) or "none")[:80]))

# --- quoted owner words appear in their records -----------------------------------------------
unquoted = 0
for od, recs in distinct.items():
    for q in re.findall(r'"([^"]{12,})"', od):
        if not any(norm(q) in text_of(r) for r in recs):
            bad("quoted words not found in their record(s) %s: %r" % (sorted(recs), q[:120]))
    if '"' not in od:
        unquoted += 1
print("owner decisions without a quoted phrase (summaries):", unquoted)

# --- port candidates exist at the old HEAD ------------------------------------------------------
sec4 = REG[REG.index("## 4. Port candidates"):REG.index("## 5. Gaps")]
ls = subprocess.run(["git", "-C", OLD, "ls-tree", "-r", "--name-only", "HEAD"], capture_output=True, text=True).stdout.split("\n")
tracked = set(ls)
port_rows = [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in re.findall(r"^\| (\d+) \| (`[^|]+?`[^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \|$", sec4, re.M)]
print("port rows", len(port_rows))
verdicts = collections.Counter()
for n, path, tests, what, feeds, verdict in port_rows:
    for one in re.findall(r"`([^`]+)`", path):
        if one not in tracked:
            bad("port path not tracked at old HEAD: " + one)
    for t in re.split(r";\s*", tests):
        t = re.sub(r"\s*\(.*\)$", "", t.strip()).strip("`")  # a note in brackets names a rule, not a file
        if t and t != "itself (a test file)" and "/" in t and t not in tracked:
            bad("port test not tracked at old HEAD: %s (for %s)" % (t, path))
    v = verdict.strip()
    if v.startswith("Port with tests"):
        verdicts["with tests"] += 1
    elif v.startswith("Port after re-check"):
        verdicts["re-check"] += 1
        if "for Fedora/Pi" in v[:40]:
            verdicts["re-check Fedora/Pi"] += 1
    elif v.startswith("Do not port"):
        verdicts["do not port"] += 1
    else:
        bad("port %s: unknown verdict %r" % (n, v[:40]))
print("port verdicts", dict(verdicts))
tot = re.search(r"Totals: (\d+) entries — (\d+) port with tests, (\d+) port after re-check \((\d+) of them for Fedora/Pi mechanics\), (\d+) do not port as is", sec4)
if tot:
    a = [int(x) for x in tot.groups()]
    b = [len(port_rows), verdicts["with tests"], verdicts["re-check"], verdicts["re-check Fedora/Pi"], verdicts["do not port"]]
    if a != b:
        bad("port totals line says %s, rows give %s" % (a, b))
# paths named in requirements' Port lines
for p in sorted({x for line in re.findall(r"^(?:  - |- \*\*Port:\*\* )(.*)$", REG, re.M)
                for x in re.findall(r"`([^`]+)`", line.split(" (tests:")[0].split(" — ")[0])}):
    if p not in tracked:
        bad("requirement Port path not tracked at old HEAD: " + p)

print("records read for quotations", len(skipped), "- parts skipped (odd quotation marks):", sum(skipped))
for miss in owner_quote_misses:
    bad("Owner line: " + miss)
print("\n%d problem(s)" % len(problems))
for p in problems:
    print(" -", p)
sys.exit(1 if problems else 0)
