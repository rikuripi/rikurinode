# Build Record — the installer: the owner picks the disk by number

| | |
|---|---|
| **Date** | 2026-11-03 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/installer-pick-disk`, from `main` at `2aafcd7`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
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
