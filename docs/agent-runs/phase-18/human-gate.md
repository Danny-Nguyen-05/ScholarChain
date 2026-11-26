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

## Day 2 decisions (2026-11-25, live EMR proof and cleanup)

Drafted after the session by the coordinator from its decision log (`evidence/day2/00-timeline/decision-log.md`) and the chat. Each answer is quoted verbatim from the chat with the question it answered; the decision log records most of them, and items marked "chat only" are not in it. Times are CST, with UTC where the evidence uses it. HEAD stayed `fe0b6cc` all day; no commit was made during the session. The last "Not covered" list in this file was written on Day 1 and is kept unchanged; the Day 2 answers below cover only the AWS steps they name.

- About 10:21 AM. Asked whether the dry runs in kit blocks 11, 12 and 14 may run with `env -u SCHOLARCHAIN_TF_PRIVATE_VARS`, logs only in the private folder. The human answered: "3. yes". The `--execute` runs kept redaction.
- About 10:22 AM. "Approve opening IAM window 1 and re-creating the deployer plan?" The human answered: "Yes, open window 1". Covers root attaching `IAMFullAccess` and the inline `scholarchain-operator-cli-login` to the admin IAM user, and the deployer plan only. The coordinator gave the inline policy document in chat, rebuilt from the Phase 12D role-login readback (us-east-2, same-device client), because the earlier copy was not kept (chat only: the decision log records the rebuild but not who made it).
- About 10:41 AM, GATE 1 (deployer plan: 31 creates). The human answered: "Approve, apply". Window 1 closed at 16:45:21Z.
- About 10:50 AM, GATE 2 (stage-a base-apply, plan run `20261125T164849Z-66547`, 171 creates, pre-spend receipt sha256 `897ffdf9dd3fcb3e…`). The human answered: "I approve".
- About 11:04 AM, GATE 3 (runtime archive upload, plan run `20261125T165515Z-72896`, 0 changes). The human answered: "Approve upload".
- About 11:12 AM, GATE 4 (EMR artifact upload, 17 files, PLAN-SHA256 `944e04bd…`). The human answered: "Approve upload".
- About 11:25 AM, GATES 5 and 6 (EMR-enable plan `468c8713…`, 13 creates; S run attempt 1 at USD 1.25 and 120 minutes). The human answered: "Approve EMR + run". This did not cover a retry.
- About 11:40 AM, GATE 7, after S attempt 1 failed at `hadoop-prep` (incident `docs/incidents/2026-11-25-emr-hadoop-prep-intermediate-missing.md`). The human answered: "Retry now". The retry was run 5, the last the ledger allows; it passed, `spark-job` included. **The Phase 18 fix is proven on EMR (one run).**
- About 12:22 PM, GATE 8 (evidence complete before cleanup; a coordinator check after kit block 20). Archive `day2-v1` written and verified (30 entries); downloads saved with `SHA256SUMS`. The coordinator then moved on to cleanup.
- About 12:37 PM, cleanup-prepare. **Gate-order deviation:** the human ran `deploy.sh --stage cleanup-prepare --execute` without a chat yes; the kit's GATE 9 ("wait for my OK") was skipped. The human's own approval record `cleanup-prepare.md` (sha256 in `evidence/day2/00-timeline/approval-hashes.txt`) stands as the approval. The run passed. Disclosed here; no repair needed.
- About 12:57 PM. The human asked (chat only): "why didn't you tell me to do any recordings". The Day 2 kit had one optional line for clips while the run was in progress (`day2-kit.md:364`) and no "record now" step before the destroy; this was the coordinator's omission. Clips 1 to 4 were recorded before the destroy (hashes in `evidence/day2/recordings/clips.txt`).
- About 1:02 PM, GATE 10 (two-pass destroy, listing 1b: 183 deletes, 0 foundation). The human answered: "approve destroy". This covered both passes. Pass 1 ended PARTIAL at the known `aws_eip.nat` 403 (IAM not widened); pass 2 passed at 02:46Z on 2026-11-26.
- About 9:00 PM, GATE 11 (C4: 13 operator-role resources, IAM window 2 open since 02:57:35Z). The human answered: "appove C4", read as "approve C4". The human made the `operator_roles_enabled = false` edit in the git-ignored tfvars by a command the coordinator gave; the coordinator did not read or edit that file.
- About 9:08 PM, GATE 12 (P39: delete `scholarchain-deployer` and its 18 resources). **Gate-order note:** the human's "yes" arrived in the same message as the pasted apply output, so the yes was not recorded before the run. The plan matched the expected 18 addresses exactly. IAM window 2 closed at 03:11:50Z; the admin user keeps only `scholarchain-assume-deployer` (harmless, the role is gone) and `scholarchain-billing-assume-role`.
- About 9:26 PM. The human confirmed the final inventory (chat only; the decision log records "all matched"): "yes all matched". The coordinator checked clip 7 frame by frame. Nothing billable remains; the KMS key is pending deletion. Budget seen in the console as root: USD 19.26 of USD 25.00.
- About 10:05 PM, after the Day 2 records passed review round 2 (APPROVE). "Commit the Day 2 records on phase-18 in 2 commits and push?" The human answered: "Commit and push". Covers one coordinator commit (this file, `test-report.md`, `evidence/day2/**`) and one incident-responder commit (`docs/incidents/**`) on `phase-18`, and the push of that branch. Not a pull request or merge.

## Not covered by the Day 2 decisions

- Any further EMR run: the ledger is at 5 of 5 runs (USD 2.65 of 4.70).
- Any commit, pull request or merge; any change to `main` or `v1.0-final`.

## Not covered

- Any AWS step, Terraform apply or destroy, deployment, or spend.
- Any EMR run-time or ledger cap change beyond the offline changes authorized by the 5:40 PM answers 2 and 3 (S run 120 minutes and USD 1.25; ledger caps derived from them in `scripts/config/release.conf`: 5 live runs, USD 4.70 in total).
- Any change to `main` or the tag `v1.0-final`.
- Commits: each needs the human's explicit yes.
