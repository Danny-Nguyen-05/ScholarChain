# Phase 14 human acceptance: live session 1

Recorded: 2026-11-15 (America/Chicago).

## Decision and authority

**ACCEPTED WITH DEFERRALS: Phase 14 Session 1 (live session 14B) closeout.**

This file records the human's decision on live session 1 (2026-11-13T17:44:01Z to the end of the Section C cleanup on 2026-11-15). The agents assembled the evidence; they did not decide. No earlier human decision is changed.

Approval: I accept live session 1 with the deferrals listed below. Given 2026-11-15 in the orchestrator chat.

Scope of the session, on `phase-14` (not merged to `main`):

- Session start HEAD `684aeaf`; in-session commits, each made on the user's explicit yes: `24bf49d` (E1 repair), `155562d` (E1 repair 2), `bc81afd` (repair 3), `9ee5bbe` (repair 4), `83a4168` (repair 5), `bfa393a` (repair 6), `0656dc4` (repair 7), `ae14593` (repair 8), `2b2d263` (repair 9), `7ecc572` (repair 10), `b6dc94d` (repair 11).
- The records commit that adds the Session 1 evidence and report sections: the commit that adds this file (made only on the human's explicit "Yes, commit").

## Session results (from the evidence)

Evidence index: `evidence/14b/session-1/INDEX.md`. Timeline of record: `evidence/14b/session-1/00-timeline/decision-log.md`. Report sections: `owner-report.md`, `test-report.md` and `repairs.md`, each under "Phase 14 live session 1".

- **14B deploy:** base and runtime stacks applied after E1 repairs 1-2 and repairs 3-4; 14B smoke 2 of 6 by design; manual 401 check; GO/NO-GO 3.
- **14C load:** 143 files uploaded; the storage load failed once on a dropped tunnel and passed with `--graph-only` (repair 5, `graphState=LOAD_COMPLETED`); pointer apply PASS; AWS integration test 1/1 (with a test-only tmpdir workaround); ingest 95 written, 0 rejected; query smoke 5/5.
- **B8.8 real-model smoke:** PASS all 6 checks (claims=3, evidence_ids=3) after repairs 6-8.
- **B9 EMR:** PARTIAL. Cluster creation, pipeline-role permissions, cluster-check, step submission and the stage-in step were proven live. Hadoop-prep failed because the 15A manifest's `hadoop_config` is a local path that was never uploaded. Stopped by the human at 2026-11-14T21:17:50Z.
- **B10 (15B):** dropped by the human ("Fix EMR, drop B10").
- **B11 16B:** 40 asked, 40 charged; component 7/8 and ranking 7/8 answered with verified claims (1 HTTP 422); direct-coauthors 0/14; path 0/10. Raw sha256 file `13736cfacf3e83beafed900d01ed904a442c2a93e2db87b4752e8aba19e0d0d4`.
- **B12:** final smoke PASS all 6 checks (2026-11-14T21:22:50Z); demo video 63 s, sha256 `55884100fa640b9185cd3a1b4caa415d818a1b5638424a55100858e153b39303`, kept outside the repository.
- **B13:** 16 files downloaded before cleanup with SHA256SUMS; re-verified offline on 2026-11-15 (16 OK).
- **Section C cleanup:** prepare PASS; destroy pass 1 PARTIAL as expected (309 to 62; EIP 403, carried item 24); pass 2 PASS (62 to 60); guard removed from state by human decision; deployer teardown 13 destroyed; 4 secrets deleted; both provider keys revoked (user, 02:19Z); C7/C8 console checks clean (KMS Pending deletion; S3 0; no EIPs; no load balancers; NAT Deleted; no VPC endpoints; Neptune 0). The 60 remaining inventory entries are tagging-index leftovers plus two free `terraform_data` guards (`inventories/INVENTORIES.md`).

## C11 billing check

| Item | Value |
|---|---|
| AWS charges for the session period, credits excluded | USD 15.75 (Cost Explorer, Nov 1-15 2026) |
| AWS charges after credits | USD 0.00 (Bills page, net after credits; tax 0.00) |
| Billing data period and time read | Nov 1-15 2026, read 2026-11-15 about 11:43 CST; November bill Pending (provisional) |
| Anthropic spend (Console) | about USD 0.08 (LLM ledger estimate 0.075075; console not separable because the key's workspace was shared) |
| Voyage AI spend (dashboard) | USD 0.00 |
| Combined against the USD 25 ceiling | USD 15.83 (provisional) |
| Any running or billable resource seen | none (ECS 0, EMR 0, Neptune 0, S3 0, no EIPs, load balancers or VPC endpoints); the deployer role is kept on purpose for Session 2 |

For comparison, the session's own figures: AWS USD 4.45 to 2026-11-14 (Cost Explorer, credits excluded, read 2026-11-14T16:00Z); LLM ledger estimate 55 answers, USD 0.075075 (not metered); EMR ledger USD 1.68 reserved (estimate).

## Open items and deferrals

Listed as found in the evidence. Unless marked closed or accepted, the items below are **deferred** to Session 2 or Phases 15-17.

- **Phase 15:** no EMR results (no run passed hadoop-prep); one EMR ledger slot unused; 15B dropped.
- **16B gaps:** direct-coauthors 0/14 (context budget 4096 against 22-coauthor researchers); path 0/10 (cause not diagnosed).
- **Demo:** the explain shown is the ABSTAINED warm-up record; no second clip with the verified record (r8a) is recorded; the video shows the account ID (user decision: keep it as is, outside the repository).
- **Not verified:** the C10 logout (no record); the two EC2-instance entries of the after inventory were not checked in the console (ECS and EMR were: 0 clusters each, 2026-11-15); B6.5 image digest comparison; the IAM windows in CloudTrail (E9 12:45-1:09 pm CST; C4/C5 8:11-8:18 pm CST). IAM user checked 2026-11-15: IAMFullAccess and the CLI-login inline policy are detached.
- **Tests and review:** the repair 6-11 test logs were not retained during the session (counts only in the decision log). Closed afterwards: closeout `sbt check` on b6dc94d (exit 0; 1567 succeeded, 0 failed, 1 canceled), `scripts/check.sh --skip sbt` on a clean b6dc94d worktree (every other gate PASS), and the external closeout review (REQUEST-CHANGES, repaired) with its recheck (APPROVE).
- **Runbook deviation:** images changed mid-session (rule 7) for repairs 4 and 6-8, chosen by the user. **Accepted.**
- **Routed follow-ups:** see `repairs.md`, "Open after the session" (S1-F1 to S1-F8).

## Review findings that need your decision

- Ownership deviations (review finding N3):
  - `155562d`: edits to `tests/infra/**` (test-engineer territory); author not recorded. **Accepted.**
  - `2b2d263`: edits to `tests/infra/**` made with the infra-engineer change. **Accepted.**
  - `9ee5bbe`: edits to `Dockerfile` and `project/**` (build-engineer territory). **Accepted.**
- Prompt version (review finding N1): `synthesis-v1` was edited in place during Session 1. **A bump to synthesis-v2 is required before any Session 2 paid answer.**
- External review: closeout review REQUEST-CHANGES (repaired), recheck APPROVE, both in review.md.

## Closeout boundary

This decision authorizes committing the Session 1 records on `phase-14`. It does **not** authorize merging to `main`, any AWS action, Session 2 (which needs its own approval record), or any spending.
