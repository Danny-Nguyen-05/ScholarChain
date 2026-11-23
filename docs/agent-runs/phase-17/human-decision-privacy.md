# Phase 17 human decision: account ID and e-mail addresses already in the repository

Recorded 2026-11-22 (Sun, about 5:15 PM CST) by the coordinator from the human's chat answers. This closes the open item "review M3" in `human-gate.md`, which earlier drafts of `docs/threat-model.md` tracked as package 17F.

## Facts the coordinator presented (observed on `phase-17` at `b125d0f`)

- AWS account ID: 77 tracked files (73 under `docs/agent-runs/phase-12/`, many listed in hash manifests or holding human decision records; 4 under `scripts/billing/`), 160 occurrences, introduced by 8 commits.
- The human's personal e-mail address: the author e-mail of 141 of the 154 commits, and 30 record files under `docs/agent-runs/phase-07/` to `phase-13/`, inside a local Google Drive folder path.
- Other people's e-mail addresses: copied unchanged from public sources (OpenAlex author records under `datasets/entity-resolution/`, the Apache Spark public signing-key file under `docs/agent-runs/phase-12/evidence/`).
- The repository was private with 0 forks; GitHub keeps pull-request commits after a force push, so a full removal would need a rewritten history in a new repository.

## Questions and answers (verbatim)

1. "Two more things are in the repo. Your AWS account ID: in 77 files [...]. Other people's email addresses: copied unchanged from public sources [...]. Keep both?" Answer (option chosen): "Keep both (Recommended)".
2. After the coordinator explained the commit-author and folder-path exposure and the history-rewrite option, the human asked: "what if I just leave it there?" The coordinator explained the effect (spam and the link between the address and the project; no effect on grading; no access risk). Question: "Leave your Gmail as is?" Answer: "Yes, leave it".

## What the decision covers

- No history rewrite and no new repository.
- The account ID, the human's personal e-mail address and the public third-party addresses stay in the tracked files and in history as they are.
- Unchanged: new tracked files still add no account ID or personal e-mail address (the `NoRealAccountIdIsAdded` scan stays in force), and only `cnguye69@uic.edu` is written as the student's address.
