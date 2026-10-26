# Subphase 9A repair round 1

User supplied external REQUEST-CHANGES and NEXT PROMPT for B1–B4, then explicitly instructed:

> Fix all blockings for me

This selects FIX NOW for B4 and authorizes all four listed blocking repairs. No additional
questions for this round. Preserve the entire uncommitted9A tree on phase-9, base/HEAD
5fee9ffc607cf802e4aaddf4a261c21f1f232fec; do not ask for a commit before repairing the same subphase.

Read the external review (external-review.txt) and ten original user decisions
(../9a/user-answers.md). Plan of record remains the Drive phase9.md, snapshot ../9a/plan-of-record.md.
Only repair B1–B4; log/carry N1–N7; no9B preparation or code.

Domain owner adds only B2 config/disclosure contract gaps; RAG owner fixes B1/B2/B3 resolver;
storage owner fixes B3/B4; test owner writes independent B1–B3 regressions. Coordinator alone
assembles phase evidence. No nested delegation, reviewer, commits/pushes, live/cloud/provider calls
or human-owned gate edits. Run affected targets, touched formatting and full JDK17 sbt check.
Retain exact commands, exits, counts, raw-log hashes, source hashes and git diff --check.
Return a complete recheck prompt for user-launched read-only review and stop.
