# Phase 12D Step C — live EMR spike (work order)

**Authority:** [human-approval.md](human-approval.md). The approval values and wording were given by the human in chat on 2026-11-04 (approved at 11:16 CST). The coordinator transcribed them into the file at the human's explicit request. The human removed the transcription notice at the top of the file during the session, so this note records that provenance.

**Base:** branch `phase-12`, commit `f6ee322` (Step A plus the deployer login addendum, both reviewed and pushed).

## Before Step C (human-run, reported in chat)

- **Deployer root:**
  - First plan: rejected by the root's input check because a placeholder `ACCOUNT_ID` was left in the operator ARN. Nothing was created.
  - Second plan: `Plan: 11 to add, 0 to change, 0 to destroy`, sha256 `c823637800eb9e7b2f36d76760efd328b17ced6388e32ef3faae8aa56bd6ba58`. Its resources matched the reviewed source; the coordinator checked the full plan text the human pasted.
  - Applied by the human.
- **Preflight** as `scholarchain-deployer`: printed `assumed-role/scholarchain-deployer/...`, region us-east-2, `PREFLIGHT OK`, exit 0. The account ID is redacted here.
- **Manual IAM window:** opened at about 10:45 CST (human's estimate) and closed at about 11:07 CST (human's report). See human-approval.md.

## Step C scope

This scope is exactly the "Actions authorized" list in human-approval.md, inside the 11:45–15:45 CST window. Owner: deploy-engineer (Sonnet 5.5, high effort), run by the coordinator. Raw outputs go to `target/phase12d-spike-live/` (git-ignored). The coordinator copies redacted, hashed evidence into this folder.
