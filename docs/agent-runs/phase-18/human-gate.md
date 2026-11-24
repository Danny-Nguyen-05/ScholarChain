# Phase 18 human gate: EMR Spark fix

Drafted: 2026-11-24 (America/Chicago), by the coordinator, from the human's chat answers.

## Decisions so far

- 2026-11-24, about 1:30 PM CST. The coordinator proposed Phase 18 (Day 1 offline fix on a branch; Day 2 live EMR run only after an official 3-day extension; Day 3 update and resubmit) and noted that `CLAUDE.md` asks for a fresh Claude Code session for each phase. The human answered: "That's fine, don't need to sepearte session for this, You can do it. Should we do phase 1 now". Recorded as a disclosed deviation: Phase 18 Day 1 runs in the Phase 17 coordinator session. This covers offline work on branch `phase-18` only.

- 2026-11-24, about 3:00 PM CST. Package 18A changed `scripts/emr/sc-step.sh`; three tracked sha256 pins under `infra/terraform/**` still held the old hash, the first launch's file list named only `scripts/**`, and the infra-engineer's attempt to update them was blocked by the auto-mode permission check. The coordinator asked: "May I relaunch the infra-engineer to update the three infra/terraform pins?" The human answered: "Yes, relaunch it". Covers `infra/terraform/emr-step-programs.json`, `infra/terraform/environments/course.local.tfvars.example` and `infra/terraform/tests/phase14a.tftest.hcl` only; not the ignored `course.local.tfvars`.

- 2026-11-24, about 5:05 PM CST. After review round 2 APPROVE and the full check `20261124T213555Z-18186` `RESULT: PASS gates=7` (`test-report.md`), the coordinator asked: "Approve the fix, and commit it on phase-18 in 2 commits and push that branch?" The human answered: "Approve, commit, push". **DECISION: package 18A fix APPROVED by the human (offline; not proven on EMR).** Covers two commits on `phase-18` (infra-engineer files; coordinator records) and the push of that branch. Not a pull request or merge; `main` and `v1.0-final` unchanged.

## Not covered

- Any AWS step, Terraform apply or destroy, deployment, raising the EMR run cap, or spend.
- Any change to `main` or the tag `v1.0-final`.
- Commits: each needs the human's explicit yes.
