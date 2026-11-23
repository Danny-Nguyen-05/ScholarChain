# Phase 17 work order 2: remove the stray `file:` test output

Assembled by the coordinator on 2026-11-22 (Sun, about 5:20 PM CST), on branch `phase-17` at `b125d0f`.

## Human decision

- The coordinator asked: "Assign removing the 24 stray file: files to the hadoop-engineer?" The human answered: "Yes, hadoop-engineer". The top-level `file:` path was unassigned (an orphan in `docs/agents.md`); this order assigns its removal to the `hadoop-engineer` only.

## Facts

- `git ls-files 'file:*'`: 24 tracked files, all `stats/j05`, `j07` and `j08` job-statistics files and their `.crc` checksums under `file:/<temp>/review-block*` and `file:/<temp>/review-repeat*` folders. They were added in the Phase 4 commit `3ccd61c` (2026-10-07).
- The folder names match `Files.createTempDirectory("review-block")` and `("review-repeat")` in `modules/hadoop/src/test/scala/edu/uic/cs441/scholarchain/hadoop/HadoopPrepReviewSpec.scala`.
- The full check `20261122T174646Z-52571` (which runs the Hadoop tests) left no new untracked `file:` path.

## Work

| ID | Work | Owner | Writes | Gate |
|---|---|---|---|---|
| 17I | Remove the 24 tracked files under `file:`; confirm from the code and a run of the Hadoop review tests that the tests no longer write into the repository; repair the module test only if they still do | hadoop-engineer | `file:/**` (removal only); `modules/hadoop/src/test/**` only if a repair is needed | targeted Hadoop tests, review, full check |

Not in scope: `.gitignore` (build-engineer), any production source.
