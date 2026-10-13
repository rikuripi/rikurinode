"""Round 2 of the register's corrections: what the verifier found left over.
Exact replacements; each must match."""
import re
import sys

F, R = sys.argv[1], sys.argv[2]   # the register, its build record
t = open(F).read()


def sub(old, new, text=None):
    global t
    n = t.count(old)
    if n == 0:
        sys.exit("no match: %r" % old[:80])
    t = t.replace(old, new)
    print("%d× %s" % (n, old[:70]))


sub("reads Docker start times; the live skip was never observed |",
    "reads Docker start times; the live skip was not yet observed when the record closed |")
sub("re-check under the current LND; this path never once ran with a channel open |",
    "re-check under the current LND; this backup has never succeeded; its first real run is the first channel open |")
sub("(no live run, no verifier)", "(no live revival run, no verifier)")
sub("“Owner decision (2026-09-14): delete the file (fsmEngine.test.ts), after its 3 surviving assertions were shown "
    "to duplicate existing coverage.”",
    "Owner decision (2026-09-14, same session): delete the file (fsmEngine.test.ts) — the record's account; its 3 "
    "surviving assertions had been shown to duplicate existing coverage")
sub("a ratchet sat red for over a month, each session calling it \"pre-existing\"",
    "a ratchet sat red across sessions, each calling it \"pre-existing\"")
sub("tapd's start runbook ran 783 times (48 a day)",
    "tapd's start runbook ran 841 times, 48 a day, 783 of them without fixing it")
sub("“Owner spec for the class fix: \"eject wrong-faction peers, locate the right headers, self-heal stands down "
    "during the switch, rotate peers cleanly\". reconsiderblock was blocked from automation and run by the owner by "
    "hand.”",
    "The owner's spec for the class fix, as the record quotes it: “eject wrong-faction peers, locate the right "
    "headers, self-heal stands down during the switch, rotate peers cleanly”; reconsiderblock was blocked from "
    "automation and run by the owner by hand")
sub("of which 44 were wrong (a figure, a quotation or an event misstated), 13 could not be found in the record cited, "
    "and 33 claimed more than the record shows",
    "of which 44 were wrong (a figure, a quotation or an event misstated), 13 could not be found in the record cited, "
    "and 32 claimed more than the record shows")
sub("a sandboxed planning-only assistant (`docs/architecture/platform-plan.md`)",
    "a sandboxed planning-only assistant (the platform plan, `docs/architecture/platform-plan.md`, a change of its own)")

sec3_start, sec3_end = t.index("## 3. Owner decisions"), t.index("## 4. Port candidates")
sec3 = t[sec3_start:sec3_end]
for n, note in ((1, "the record's summary, quoting the owner's spec"),
                (78, "the owner's choice and the record's note joined")):
    m = re.search(r"^(\| %d \| )(.*?)( \| [^|]*\.md[^|]* \| [^|]* \| [^|]* \|)$" % n, sec3, re.M)
    sec3 = sec3[:m.start()] + m.group(1) + m.group(2) + " *(" + note + ")*" + m.group(3) + sec3[m.end():]
    print("section 3 row", n)
t = t[:sec3_start] + sec3 + t[sec3_end:]
open(F, "w").write(t)

r = open(R).read()
for old, new in (("wrong, 13 not found in the cited record, 33 overclaims.", "wrong, 13 not found in the cited record, 32 overclaims."),
                 ("table. One reader also found the known \"12 of 16\" (LN-03).",
                  "table. Two readers (C and E) found the known \"12 of 16\" (LN-03); it is counted once."),
                 ("E ~165/6/1/12, F 232/5/4/7 (claims / wrong / not found / overclaims)",
                  "E ~165/6/1/12, F 232/5/4/6 (claims / wrong / not found / overclaims; LN-03 found by C and E)"),
                 ("fact-check A 131/7/1/2, B 112/14/2/3, C ~112/6/5/4, D 82/7/0/4,",
                  "fact-check A 131/7/1/2, B 112/14/2/3, C ~112/6/5/5, D 82/7/0/4,")):
    if r.count(old) != 1:
        sys.exit("record: no match %r" % old[:60])
    r = r.replace(old, new)
open(R, "w").write(r)
print("record updated")
