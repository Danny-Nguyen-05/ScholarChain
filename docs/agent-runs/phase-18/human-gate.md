# Phase 18 human gate: EMR Spark fix

Drafted: 2026-11-24 (America/Chicago), by the coordinator, from the human's chat answers.

## Decisions so far

- 2026-11-24, about 1:30 PM CST. The coordinator proposed Phase 18 (Day 1 offline fix on a branch; Day 2 live EMR run only after an official 3-day extension; Day 3 update and resubmit) and noted that `CLAUDE.md` asks for a fresh Claude Code session for each phase. The human answered: "That's fine, don't need to sepearte session for this, You can do it. Should we do phase 1 now". Recorded as a disclosed deviation: Phase 18 Day 1 runs in the Phase 17 coordinator session. This covers offline work on branch `phase-18` only.

- 2026-11-24, about 3:00 PM CST. Package 18A changed `scripts/emr/sc-step.sh`; three tracked sha256 pins under `infra/terraform/**` still held the old hash, the first launch's file list named only `scripts/**`, and the infra-engineer's attempt to update them was blocked by the auto-mode permission check. The coordinator asked: "May I relaunch the infra-engineer to update the three infra/terraform pins?" The human answered: "Yes, relaunch it". Covers `infra/terraform/emr-step-programs.json`, `infra/terraform/environments/course.local.tfvars.example` and `infra/terraform/tests/phase14a.tftest.hcl` only; not the ignored `course.local.tfvars`.

- 2026-11-24, about 5:05 PM CST. After review round 2 APPROVE and the full check `20261124T213555Z-18186` `RESULT: PASS gates=7` (`test-report.md`), the coordinator asked: "Approve the fix, and commit it on phase-18 in 2 commits and push that branch?" The human answered: "Approve, commit, push". **DECISION: package 18A fix APPROVED by the human (offline; not proven on EMR).** Covers two commits on `phase-18` (infra-engineer files; coordinator records) and the push of that branch. Not a pull request or merge; `main` and `v1.0-final` unchanged.

- 2026-11-24, about 5:27 PM CST. The human reported turning in `v1.0-final` on Teams ("alright I have turned it in"). The coordinator had asked "Start Day 2 tonight? Yes, or wait for the extension." The human answered: "let's start tonight". This starts Day 2 preparation without an official extension. It does not approve any plan, apply, spend, run-cap change or deployer access; each of those still needs its own recorded human decision.

- 2026-11-24, about 5:40 PM CST. Day 2 choices, asked by the coordinator with options (answers verbatim):
  1. Timing: "Tonight, start now (Recommended)".
  2. "Raise the total cap to 120 minutes (Spark about 50 min)? It needs a manifest and test change, review and a commit first (about 1 hour), and costs about $1.25 instead of $0.84 at most." Answer: "Raise to 120 min (Recommended)".
  3. "The EMR ledger allows exactly 1 more run (4 of 4). Raise it so a second try is possible?" Answer: "Yes, allow 1 retry".
  4. "After the run, the deployer role is needed only for teardown. Remove it again at the end, as on Nov 19?" Answer: "Remove it at the end (Recommended)".
  Size L (48,187 works) stays dropped on EMR (no manifest; entity resolution ran out of memory locally at -Xmx22g; P25 rule of 2026-11-16). These answers authorize the offline changes for 2 and 3 (owners, review, gates, then a commit on the human's yes). They do not approve any plan, apply or spend.

- 2026-11-24, about 5:45 PM CST. Human-supplied record (pasted in chat): the instructor changed the course project deadline to November 30, 2026, 8:00 PM CST, and stated that only the last commit before the deadline is pulled for grading. The extension is now official.

- 2026-11-24, about 9:05 PM CST. After review round 2 APPROVE and the full check `20261125T013045Z-81496` `RESULT: PASS gates=7` (`test-report.md`, package 18B), the coordinator asked: "Approve 18B and commit it on phase-18 in 4 commits, then push?" The human answered: "Appovec" (read as "Approve"). **DECISION: package 18B APPROVED by the human (offline).** Covers four commits on `phase-18` (experiment-engineer, infra-engineer, test-engineer files; coordinator records) and the push of that branch. Not a pull request or merge; `main` and `v1.0-final` unchanged. The git-ignored entity-resolution JAR was restored to its pin (`e8df4ee2...2768`, 12,863,882 bytes) by copying a Phase 15 build from `../ScholarChain-wt/phase15-maxfail`; a rebuild at `bd0b818` did not reproduce it.

## Not covered

- Any AWS step, Terraform apply or destroy, deployment, or spend.
- Any EMR run-time or ledger cap change beyond the offline changes authorized by the 5:40 PM answers 2 and 3 (S run 120 minutes and USD 1.25; ledger caps derived from them in `scripts/config/release.conf`: 5 live runs, USD 4.70 in total).
- Any change to `main` or the tag `v1.0-final`.
- Commits: each needs the human's explicit yes.
