"""Owner lines: quotation marks only around words the cited record contains.

A harvest field often wrapped a whole decision in “…”, with the owner's own
words inside in straight quotes. For each “…” in an Owner line whose text the
cited record does not contain: if it holds straight-quoted words, drop the
outer marks and make the inner straight quotes the quotation; otherwise leave
it for a hand fix (listed). Usage: fix_owner_quotes.py <register.md>"""
import os
import re
import sys

OLD = "/home/junc/rikuri/rikurinode"
F = sys.argv[1]


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("—", "-").replace("–", "-")
    s = re.sub(r"[*`]", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


cache = {}


def text_of(rec):
    if rec not in cache:
        cache[rec] = norm(open(os.path.join(OLD, "docs", "build-records", rec), errors="replace").read())
    return cache[rec]


t = open(F).read()
out, left, fixed = [], [], 0
in_owner = False
for line in t.split("\n"):
    if line.startswith("- **Owner:**"):
        in_owner = True
    elif line.startswith("- **") or line.startswith("#"):
        in_owner = False
    if in_owner:
        recs = re.findall(r"\d{4}-\d{2}-\d{2}-[\w.+-]+?\.md", line)

        def fix(m):
            global fixed
            span = m.group(1)
            if recs and any(norm(span) in text_of(r) for r in recs):
                return m.group(0)
            if '"' in span:
                fixed += 1
                return re.sub(r'"([^"]+)"', r"“\1”", span).rstrip(".")
            left.append("%s" % span[:100])
            return m.group(0)
        line = re.sub(r"“(.*?)”", fix, line)
    out.append(line)
open(F, "w").write("\n".join(out))
print(fixed, "spans unwrapped;", len(left), "left for a hand fix:")
for x in left:
    print("  ", x)
