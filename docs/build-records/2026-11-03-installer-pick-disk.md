# Build Record — the installer: the owner picks the disk by number

| | |
|---|---|
| **Date** | 2026-11-03 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/installer-pick-disk`, from `main` at `2aafcd7`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | PR #61, merge `7950214`: `a2ef8e1` (red), `34ebf2c` (the test's own fixture; red again), `a055b7b` (the fix), `c9b1997` (docs; a stricter pick test) |
| **Status** | DONE (2026-11-03); proven on the N150 the same day (`docs/build-records/2026-11-03-install-n150.md`) |
| **Change type** | feature (a change of the installer's rule) |

## Task Contract

1. **Outcome:** a machine with several internal disks, such as the N150 with a built-in eMMC and a 2 TB SSD, can be installed by picking the disk, and only that disk is erased.
2. **Scope:** stage 1 change 5b, found on the N150 (owner, 2026-11-03: the installer refused, and the 63 GB disk is built in).
   - **`image/installer/rikuri_install.py`:**
     - one candidate disk: as now;
     - several: list them numbered, each by `describe()`, and ask for a number; anything but a listed number stops ("Nothing was erased"); a listed number names that one disk again, then asks for `ERASE`, as now.
     - The candidates are unchanged: never the stick, a removable, read-only, USB or zram disk, or one with no size.
   - **Tests:** `image/tests/test_installer.py`; `image/drill/install_test.py` and its tests.
     - CI's case "two disks" becomes two cases: a wrong number (neither disk written); and pick 2, then `ERASE` (installed on the second disk only, the first unwritten, the second boots alone and passes greenboot, origin and digest read from it).
     - The one-disk `ERASE` case goes: the two-disk install proves more. The one-disk path keeps its unit tests and CI's `no` case.
   - **Docs:** `docs/runbooks/install-node.md` (the list and the number); ADR 0006's clarification, a dated note (the installer now asks which disk); the 5a record, a pointer.
   - Risk tier: **high-risk** (it chooses which disk is erased).
   - **Not included:** the install on the N150 (the owner's, after a new publish); eMMC's boot areas, unless the owner's screen shows them listed (then they are named in this contract first); Fedora 45.
3. **Done when:**
   - tests committed failing first, then pass in `rikuri-drill`; hand mutants of the new rule (the number's range, a non-number, the chosen disk passed to the install, ERASE still asked) turn them red, against a passing baseline;
   - on the PR, `Full gate (Ubuntu)` and the OS image workflow's install test pass, showing the cases above;
   - one `verifier` pass has no Important finding.
4. **Authority:** the owner's "You pick by number (Recommended)" (2026-11-03); this branch; a draft PR; no merge. An independent check is required.
5. **Limits:** one task; two repair cycles; two review rounds; development CI at most 4 runs.

## Evidence log

- **Red, first run** (`a2ef8e1`; rikuri-drill, `safe-run.sh`): `test_installer.py` `Ran 47 tests` `FAILED (errors=6)`. Recorded at first as "each on the missing `picked` or `PICK`": **that was wrong.** Four of the six were `NameError: name 'EMMC' is not defined`, a mistake in the tests (a class attribute used without `self.`), found when the fix's green run still showed them.
- **Test change after the red commit:** `EMMC` moves beside the other fixture disks, at module level; nothing else.
- **Red, corrected** (the new tests against `main`'s installer, `2aafcd7`): `Ran 47 tests` `FAILED (failures=2, errors=4)`. The failures are the old behaviour: `AssertionError: 5 != 0` (it refuses two disks), and no `  1) DA4064, 63 GB, serial 0x1a2b3c4d (/dev/mmcblk0)` in its output. The errors: `AttributeError: … no attribute 'picked'` (×2), `'PICK'` (×2). `test_install_test.py`: `AttributeError: module 'rikuri_install' has no attribute 'PICK'`.
- Test changes, with reasons: the tests that held "several disks are refused" go, because that is the rule the owner changed; the harness's case tests follow its new cases (a wrong number; pick 2, then `ERASE`).
- **Green** (rikuri-drill, `safe-run.sh`): `test_installer.py` 47 tests (one case group, inside an existing test, added after the corrected red: non-ASCII digits after an ASCII one, stricter only), `test_install_test.py` 28, `test_workflows.py` 26; `image/tests` 360; all `OK`. *Corrected 2026-11-03:* first recorded as 48, a miscount found by the verifier; the case group added no test.
- **Hand mutants: 89 of 89 red, none broken,** baseline 75 passing, with `-B`. The new rule's 13: 0 accepted, non-ASCII digits, one past the end, any number, no strip, off by one, not asked, the refusal dropped, the first disk used, numbered from 0, `ERASE` skipped after a pick, the first disk named, the first disk installed. The harness's 9 new ones, and the earlier 70 whose lines remain. Three earlier ones no longer apply, each replaced: "two disks not both named" (the case is gone; the list check), "no not checked" (now two such lines; "no, disk unchecked") and "empty after install ignored" (now disk `b`).
  - Found by them: `[1-9]\d*` survived until the case group above was added.
- **The N150's disk list** (the owner's photo of the old refusal, 2026-11-03): exactly two disks, `unknown model, 63 GB, serial 0x7c5ca232 (/dev/mmcblk0)` and `ORICO, 2048 GB, serial N380000000000001059 (/dev/nvme0n1)`. The eMMC's boot areas (`mmcblk0boot0`, `boot1`) are not listed: the existing read-only rule drops them, so the contract needs no change for them.
- **CI on PR #61:** on `c9b1997`, [CI](https://github.com/rikuripi/rikurinode/actions/runs/41722069323) (`Full gate (Ubuntu)`) and [OS image](https://github.com/rikuripi/rikurinode/actions/runs/41722069316), its install test with the cases "wrong number", "no" and "erase", passed; on the merge with `main`, `1b3ce33`, [CI](https://github.com/rikuripi/rikurinode/actions/runs/41723676148) and [OS image](https://github.com/rikuripi/rikurinode/actions/runs/41723676054) passed.
- **Verifier, one pass** (on `c9b1997`): no Important finding; its verdict was "not yet proven" only until the install test passed, which it then did. It reran the tests in rikuri-drill and the red against `main`, and confirmed the disk listed, the disk named before `ERASE` and the disk installed are one disk on every path. Minor findings:
  1. this record's 48 (corrected above);
  2. four lines of the harness's own checks are not held by its self-tests (dropping `or "(/dev/vda)" in shown`, the `NOTHING_ERASED` wait in "wrong number", the `ERASE_THIS` wait, the `PICK` wait): harness code, not the installer; backlog;
  3. a memory card in a built-in reader (SDHCI, rtsx) can report itself non-removable, so it would be listed by number rather than left out (general knowledge, not tested); the runbook now says so;
  4. `int()` of a number of about 4300 digits raises, which a person at a console does not type; not changed;
  5. a line break in `picked`'s docstring; not changed.
- **On the N150** (owner, 2026-11-03): picked `2`, the ORICO; typed `ERASE`; the installer said it was installed; the node starts Fedora Linux 44 (IoT Edition) from the ORICO. Record: `docs/build-records/2026-11-03-install-n150.md`.

**`DONE`** (2026-11-03). Every "Done when" item passed, above; the owner merged PR #61. Limits: no repair cycle, one review round; development CI used 2 of its 4 runs.
