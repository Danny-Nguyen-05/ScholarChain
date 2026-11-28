# ScholarChain demonstration video script

**Status: updated for the final demo on 2026-11-22 (Phase 17, package 17A-2) by the documentation-engineer; not approved.** The human recorded the clips (17H, outside the repository); an agent edited them at the human's request (cuts, 1.2x speech, labels and captions); the coordinator added correction captions and the item 6 owner-report clip after reviews by a separate agent session (pasted in chat, not stored in the repository); and the human uploaded the video. The final video is linked from the [README](../README.md) (Unlisted YouTube video, 22:59.6, 26 chapters; see the Phase 18 video update below). The first upload of this script's cut (19:22, 24 chapters) was replaced on 2026-11-27 and is no longer available. The 2026-11-15 draft is in git history. Commands marked "(rehearse)" were not replayed in 17A; the 17G clean-checkout replay (2026-11-22) observed the commands it names in `docs/agent-runs/phase-17/17g-replay.md`; a "(rehearse)" mark that remains means that command was not part of it. The AWS stack was destroyed on 2026-11-18 ([Phase 15 human gate](agent-runs/phase-15/human-gate.md)), so every live item is shown from a recorded clip or from archived evidence opened on screen, never from a running stack. The Session 2 plan, [session-2-plan.md](runbooks/session-2-plan.md), stays as the plan record; section 4 below states what actually happened.

**Phase 18 note (2026-11-26, documentation-engineer).** The item text below describes the state of 2026-11-18 to 2026-11-24, when the Spark step on EMR had failed, as the 19:22 cut showed it. After that cut, Phase 18 fixed that step and a size-S EMR run on 2026-11-25 completed all six steps, Spark included (one run; the first attempt that day failed at `hadoop-prep`; sources: [Phase 18 test report](agent-runs/phase-18/test-report.md), [incident, resolved](incidents/2026-11-18-emr-spark-job-step-emrfilesystem.md), [incident, open](incidents/2026-11-25-emr-hadoop-prep-intermediate-missing.md)). The statements below that the Spark step failed are correct for the clips they describe and are dated; they are not the current status. The human also recorded Phase 18 clips on 2026-11-25 outside the repository (hashes in [clips.txt](agent-runs/phase-18/evidence/day2/recordings/clips.txt)); all six (clip1 to clip5 and clip7; no clip 6 was recorded) are used in the 10b and 22b inserts of the replacement video (see the video update below). The stack was created again and destroyed again on 2026-11-25 (see the [runbook](runbook.md), section 4.3).

**Video update (2026-11-27, documentation-engineer).** The video linked from the README was replaced by [https://youtu.be/Bb6OzssRdWg](https://youtu.be/Bb6OzssRdWg) (Unlisted, 22:59.6, 26 chapters: Opening, items 1 to 22, 10b, 22b and Closing). It is the 19:22 cut, unchanged except for added correction captions, plus two Phase 18 inserts. The coordinator assembled it with ffmpeg; the build files are git-ignored and not in the repository. The per-item script below still describes the 24 chapters of the earlier cut; the two inserts and the added captions are:

- **10b. Phase 18 update: Spark on EMR fixed (2026-11-25)** (after item 10, from 07:45): a title card, then four clips the human recorded on 2026-11-25: the EMR console Steps tab of run 5 with all six steps Completed; the S3 Spark export folder with its completion marker; the terminal run script ending in `RESULT: PASS` (17:40:34 to 18:14:39 UTC); and the counters (10,578 works, 21,819 researchers, 81,181 edges, 3,942 components, equal to the local run of item 10). A caption at 08:50 corrects the narration: the run took 34 minutes, not 24, and the narrated 51 cents is the EMR ledger estimate for that run, not a billed amount.
- **22b. Phase 18 cleanup and final inventory (2026-11-25/26)** (after item 22, from 19:33): a title card, then two clips of the second cleanup: destroy pass 2 with `RESULT: PASS`, and the final console inventory with nothing billable left.
- **Added captions:** at the end of item 10, "Update 2026-11-25: the Spark step was fixed and completed on EMR. See the next chapter."; in the Closing (from 21:37), the AWS Budgets console figure of USD 19.26 of 25.00 on 2026-11-25 (not final) with Phase 18 EMR runs about USD 0.60 (ledger estimates), and notes that size L was not run on EMR and that Neptune shows Session 1 evidence only; and at 22:29 a dated caption: Spark failed on EMR on 2026-11-18, the Phase 18 run on 2026-11-25 completed all six steps, and the API demo still uses the earlier local export.
- The new clips play at 1.2x speech like the rest. Chapter starts of the final video, as in its description: 00:00 Opening, 00:23 item 1, 01:13 item 2, 01:44 item 3, 02:07 item 4, 02:58 item 5, 03:36 item 6, 04:20 item 7, 05:11 item 8, 06:06 item 9, 07:07 item 10, 07:45 item 10b, 09:19 item 11, 09:55 item 12, 10:27 item 13, 10:58 item 14, 12:01 item 15, 12:50 item 16, 14:31 item 17, 15:31 item 18, 16:18 item 19, 16:59 item 20, 17:41 item 21, 18:29 item 22, 19:33 item 22b, 21:37 Closing.

History of earlier amendments (kept): Amended 2026-11-16 (P34 impossible, then option (i) in the plan, section 6.4): Neptune runs at min 1 / max 2.5 NCU with a 5.8 h hard stop (this script said "Neptune capped at 1 NCU"), and R-c is dropped, so the "With R-c" column in section 4 is a record only. Item rows 11 and 14-16 in section 1 said "live with R-c"; they now read "Session 1 result only; R-c dropped". Amended 2026-11-16 (L dropped on EMR): items 9 and 10 show S on EMR plus the measured L local evidence, replacing "two real DBLP sizes on the same cluster".

**Target length:** 10 to 15 minutes. This script totals **14 min 15 s** (section 2).
**Recording rule from the course:** the demonstration must show every item "without relying only on prerecorded screenshots". Every item below is a screen recording of a real command, console page or file being opened, never a still image. Live items are recorded while the AWS stack exists; they cannot be re-shot after cleanup.
**Privacy rule:** never show a key, a secret, a key-creation page or a password. Put an API key in a temporary header file, as in the runbook's smoke steps; never type it on the command line. Recordings kept outside the repository may show the account ID, bucket names and ARNs: the human accepted this for the first video ("keep it as is, outside the repository", [Phase 14 human gate](agent-runs/phase-14/human-gate.md)) and the Session 2 clip list says it applies ([clips.txt](agent-runs/phase-15/evidence/session-2/recordings/clips.txt)); the tracked files and the git history of this repository do contain the AWS account ID (a Phase 17 review finding: many files of the current tree, mostly Phase 12 evidence); whether it is removed is a separate decision of the human and is not made here, so do not read or show those files in the video. The root-console clips REC19, REC20 and REC22 may show the account e-mail by the human's decisions of 2026-11-18 and 2026-11-20 ([Phase 15 human gate](agent-runs/phase-15/human-gate.md)); the human checks those clips before using them, and the final cut's Opening shows the README, which contains the university e-mail address; no other e-mail address was seen in the sampled frames. The Session 1 video (63 s) showed the account ID in two ARN lines and is replaced; do not reuse that footage.

---

## 1. Item list and how it matches the course

**Source:** course README, section "Demonstration requirements", https://raw.githubusercontent.com/0x1DOCD00D/ScholarChain/main/README.md, read 2026-11-15T16:51:58Z. The course lists **22 numbered items**. This script uses the course's numbering and wording.

**Mismatch to note:** the Phase 17 plan (section 7.2, "Demonstration script (20 items from the course)") lists 20 items. Its list ends at "scale-out and scale-in evidence" and leaves out course item 21 ("One failure and recovery example") and item 22 ("Cleanup or resource inventory evidence"). The course README is authoritative, and the human's count of 22 agrees with it.

The course also requires, in its hooks section, "at least three safe probes showing that the guard blocks prohibited commands". Item 4 therefore shows three probes.

**The human's offline/live split, checked:**

- Offline: items 1-8, 17 and 22. Live: items 9-16 and 18-21.
- This matches the course list, with three nuances:
  - **Items 9 and 10** are produced in **stage a** (EMR), not stage c. Record them while the EMR run happens. Stage c can only show the terminated cluster's Steps page and the copied-out files.
  - **Item 16** is live (an answer's claim verdicts) plus an **offline** unit-test clip for "one unsupported claim test".
  - **Item 22** is recorded after cleanup (stage d and the next day). The inventory files are offline. The empty console pages are a live, read-only check of AWS after the destroy.

| # | Course item (verbatim) | Offline or live | Produced in | Seconds | Running total |
|---|---|---|---|---:|---:|
| - | Opening | offline | any time | 15 | 0:15 |
| 1 | Private repository structure. | offline | before freeze | 20 | 0:35 |
| 2 | Agent ownership map. | offline | before freeze | 25 | 1:00 |
| 3 | At least one agent role file. | offline | before freeze | 20 | 1:20 |
| 4 | A dangerous-command hook safely blocking a probe. | offline | before freeze | 45 | 2:05 |
| 5 | A test-stop hook or equivalent deterministic gate. | offline | before freeze | 30 | 2:35 |
| 6 | A phase report and repair record. | offline | before freeze | 30 | 3:05 |
| 7 | A clean `sbt check` result. | offline | before freeze | 35 | 3:40 |
| 8 | A dataset manifest and actual source samples. | offline | before freeze | 30 | 4:10 |
| 9 | Hadoop job execution evidence and counters. | clip REC09 (EMR, Session 2) + L local evidence | recorded 2026-11-18 | 45 | 4:55 |
| 10 | Spark job execution evidence and graph outputs. | clip REC10 (graph outputs of the local run; the EMR Spark step failed) + L local evidence (ER bypassed, disclosed) | recorded 2026-11-18 + P6 local | 45 | 5:40 |
| 11 | Neptune graph query. | **Session 1 evidence only** (no Neptune clip exists; Neptune was empty in Session 2) | Session 1 files | 35 | 6:15 |
| 12 | DynamoDB run or query record. | clip REC12 | recorded 2026-11-18 | 25 | 6:40 |
| 13 | S3 Vectors query returning source pointers. | clip REC13 | recorded 2026-11-18 | 35 | 7:15 |
| 14 | A complete user query through the API. | clip REC14 (Q12 rerun, live model; local loopback stack, not AWS) | recorded 2026-11-21 | 45 | 8:00 |
| 15 | Evidence and explain endpoints for the answer. | clip REC15 (same rerun) | recorded 2026-11-21 | 40 | 8:40 |
| 16 | Claim verification behavior, including one unsupported claim test. | clip REC16 (same rerun) + offline test clip | recorded 2026-11-21 + offline | 45 | 9:25 |
| 17 | Reproduction scripts, agent replay instructions, and a clean-checkout bounded run. | offline | after the 17G replay on `main` (done 2026-11-22) | 45 | 10:10 |
| 18 | Terraform plan or deployed-resource evidence. | clips REC18a and REC18b | recorded 2026-11-18 | 30 | 10:40 |
| 19 | CloudWatch elasticity dashboard. | clip REC19 (root console, read-only) | recorded 2026-11-18 | 35 | 11:15 |
| 20 | Scale-out and scale-in evidence. | clip REC20 (root console, read-only) | recorded 2026-11-18 | 55 | 12:10 |
| 21 | One failure and recovery example. | clip REC21 (stop one query-api task) | recorded 2026-11-18 | 50 | 13:00 |
| 22 | Cleanup or resource inventory evidence. | clip REC22 + inventory files | recorded 2026-11-18 | 35 | 13:35 |
| - | Closing: costs and disclosures | offline | after the C11-style check | 40 | **14:15** |

Edit the clips into this course order. All live items are already recorded or come from archived evidence, so nothing in this table can be re-shot (the stack is destroyed). Clips kept outside the repository, with the durations of the Session 2 files in [clips.txt](agent-runs/phase-15/evidence/session-2/recordings/clips.txt): REC09 81.8 s, REC10 55.7 s, REC12 45.7 s, REC13 46.3 s, REC18a 27.6 s, REC18b 45.4 s, REC19 61.9 s, REC20 60.1 s, REC21 93.9 s, REC22 93.2 s (several are longer than the slot above, so cut them). REC14, REC15 and REC16 were recorded on 2026-11-21 for the API query, the evidence and explain endpoints, and claim verification; the recorded durations are 88.2 s (REC14, API query), 75.5 s (REC15, evidence explain) and 109.8 s (REC16, claim verification) ([q12-rerun-addendum.md](agent-runs/phase-15/q12-rerun-addendum.md)); the clip files and their hashes stay outside the repository. No clip file for items 1-8 and 17 is recorded in the repository; those are offline and the human records them. The totals in the table are the plan, not measured clip lengths.

---

## 2. Per-item script

Terminal setup for every offline clip: the runbook's "T1 setup" block (JDK 17, `cd` to the repository). For live clips, the stage's own setup (runbook B8.0 or B10.1). `<domain>`, `<run-prefix>`, `<run-id>` and the other angle-bracket names are placeholders: fill them in the terminal only, never in a file.

### Opening (15 s, 0:15)
- **Show:** the repository README title in the editor.
- **Say:** "This is ScholarChain. It turns DBLP and linked open scholarly data into a researcher collaboration graph with Hadoop and Spark, stores it in Neptune, DynamoDB, S3 and S3 Vectors on AWS, and answers questions with evidence that every claim is checked against."

### 1. Private repository structure (20 s, 0:35), offline
- **Show:** the GitHub repository page. The course asks for a private repository; the human decided on 2026-11-19 that the repository is public and clonable without authentication at the deadline ([Phase 17 work order](agent-runs/phase-17/prompt.md)), so say which it is at recording time. Then in the terminal: `git ls-files | cut -d/ -f1 | sort | uniq -c` and `ls modules`.
- **Say:** "Core holds the shared contracts. Hadoop prepares the data, entity resolution decides identities, Spark builds the graph, storage adapts the AWS stores, rag retrieves and verifies, and services expose the API. Dependencies point toward core."

### 2. Agent ownership map (25 s, 1:00), offline
- **Show:** `sed -n '1,30p' docs/agents.md` (the artifact ownership table).
- **Say:** "Every class of file has exactly one writer. Reviewers report findings but never edit. I, the human, own the phase gates and ratification."

### 3. Agent role file (20 s, 1:20), offline
- **Show:** `sed -n '1,40p' .claude/agents/hadoop-engineer.md`
- **Say:** "A role file states the agent's territory, what it must decline, its ordered procedure and its report fields."

### 4. Dangerous-command hook blocking probes (45 s, 2:05), offline
- **Show (three safe probes; the hook only reads the JSON and never runs the command):**
  ```
  printf '%s' '{"tool_name":"Bash","tool_input":{"command":"echo terraform destroy"}}' | .claude/hooks/guard-dangerous.sh; echo "exit=$?"
  printf '%s' '{"tool_name":"Bash","tool_input":{"command":"aws s3 rm --recursive s3://example-bucket/x"}}' | .claude/hooks/guard-dangerous.sh; echo "exit=$?"
  printf '%s' '{"tool_name":"Bash","tool_input":{"command":"aws emr terminate-clusters --cluster-ids j-EXAMPLE"}}' | .claude/hooks/guard-dangerous.sh; echo "exit=$?"
  ```
  Expected (derived from the hook source, rehearse): `Blocked: terraform apply or destroy…`, `Blocked: recursive S3 deletion…` and `Blocked: destructive AWS operation…`, each followed by `exit=2`.
  Then a short clip in a fresh Claude Code session of probe 3 in `.claude/PROBES.md`: the guard rejects a proposed `echo 'terraform destroy'` Bash call.
- **Say:** "The hook is executable policy. It blocks Terraform destroy, recursive S3 deletion and EMR termination before anything runs. In Codex and Cursor this hook does not run, so there the same rules are enforced by process and review."

### 5. Test-stop hook or deterministic gate (30 s, 2:35), offline
- **Show:** in a Claude Code session, probe 5 of `.claude/PROBES.md`: change a harmless Scala file, try to finish, and the Stop hook refuses until `sbt check` refreshes `.claude/.last-test-run`. Alternatively, `scripts/check.sh` ending in `RESULT: PASS gates=7` (rehearse).
- **Say:** "An agent cannot claim it is done after a source change unless the tests ran and passed."

### 6. Phase report and repair record (30 s, 3:05), offline
- **Show:** `sed -n '1,25p' docs/agent-runs/phase-14/owner-report.md`, `sed -n '1,25p' docs/agent-runs/phase-14/repairs.md` and `git log --oneline | grep -i 'live repair' | head -11`.
- **Say:** "Each phase has a prompt, an owner report, a test report, an independent review and my gate. Live failures in Session 1 became numbered repairs, each with tests and a commit I approved."

### 7. Clean `sbt check` (35 s, 3:40), offline
- **Show:** the JDK 17 setup, then `sbt -batch check`. Show the start, cut the middle (the sbt gate of the 2026-11-20 full check took 816 s) and show the final summary with the test counts and exit 0; the counts of the latest full check are in [reports/release-manifest.md](../reports/release-manifest.md). Say on camera that the cut was made.
- **Say:** "This is the repository's definition of done: formatting, compilation and every module's tests."

### 8. Dataset manifest and actual source samples (30 s, 4:10), offline
- **Show:** `sed -n '1,40p' datasets/dataset-manifest.yaml`, then `head -c 800 datasets/samples/dblp/linked-records.xml`, then `(cd datasets && shasum -a 256 -c samples/SHA256SUMS)` (replayed in 17G from the `datasets` directory: 4 files OK).
- **Say:** "Every source has a snapshot, a retrieval date, a license and checksums. The DBLP input is a bounded slice of about 10,577 papers, not the full dump."

### 9. Hadoop execution evidence and counters (45 s, 4:55), clip REC09 (EMR, Session 2)
- **Show:**
  - Clip REC09 (81.8 s, recorded 2026-11-18). Its content is in the clip, not in the repository.
  - Archived evidence opened on screen: [hadoop-prep-counters.txt](agent-runs/phase-15/evidence/session-2/emr/hadoop-prep-counters.txt) (counters summed over the nine jobs: INPUT 290,343, ACCEPTED 515,309, REJECTED 1,243; ACCEPTED can exceed INPUT because each counter is summed over all jobs) and [emr-run-1.log](agent-runs/phase-15/evidence/session-2/emr/emr-run-1.log).
  - **Also show (local evidence, labelled "local P6 run"):** the L Hadoop pass: about 132 s (131.8, 137.2 and 141.3 s in three runs), 210 works dropped by the team limit, maximum team 79 ([experiments/README.md](../experiments/README.md)).
- **Say:** "Hadoop MapReduce parses and normalises the records. On EMR we ran the S slice, 10,577 real DBLP works. The Hadoop counters, summed over the nine jobs, were 290,343 input, 515,309 accepted and 1,243 rejected, and the rejects are kept. The counters are identical to the local run. The larger size, 48,187 works (48,188 canonical works in the Spark graph), was dropped on EMR: locally its Hadoop step passes in about 132 seconds, but entity resolution ran out of memory at 22 GB, so L is shown from local runs only."

### 10. Spark execution evidence and graph outputs (45 s, 5:40), clip REC10 and local evidence
- **Show:**
  - Clip REC10 (55.7 s, recorded 2026-11-18), named "spark-graph" (its content is in the clip, not in the repository). Whatever it shows, say plainly that **the Spark step failed on EMR on 2026-11-18** (a later Phase 18 run completed it, see the Phase 18 note at the top; it died in its template fetch with `ClassNotFoundException ... EmrFileSystem`, [incident record](incidents/2026-11-18-emr-spark-job-step-emrfilesystem.md)) and that the graph outputs come from the local run of the same step chain on the same inputs and commit (export run `ba7402d1`).
  - Local L next to S, labelled on screen "ER bypassed: identity pass-through, local only, not the EMR path": L Spark 1,110.14 s, 48,188 works, 76,623 researchers, 320,690 all-years edges, against S 459.84 s, 10,578 works, 21,819 researchers, 81,181 edges with the same bypass ([experiments/README.md](../experiments/README.md)).
  - The graph's measured structure: [graph-correctness.md](../experiments/results/phase16/graph/graph-correctness.md) (78,104 nodes, 100,252 graph edges, 228,715 coauthor edges, no dangling edge).
- **Say:** "Spark builds the temporal weighted coauthorship graph and computes components, communities, bridges, k-core and paths in a distributed way, never by collecting the graph to one machine. On EMR this step failed; the graph you see is the local run of the same job."

### 11. Neptune graph query (35 s, 6:15), Session 1 evidence (no live clip)
- **Show:** archived Session 1 files opened on screen, not stills: [14c-results.txt](agent-runs/phase-14/evidence/14b/session-1/14c-load/14c-results.txt) (`graphState=LOAD_COMPLETED`, 78,104 nodes, 328,967 edges, recorded in [real-slice-export.md](agent-runs/phase-14/evidence/14b/replan/real-slice-export.md)) and [tunnel-test.log](agent-runs/phase-14/evidence/14b/session-1/14b-deploy/tunnel-test.log). The graph-through-the-API answers of item 14 also rest on Neptune data.
- **Say:** "The graph lives in Neptune. This is from the first live session: the load completed with 78,104 nodes and 328,967 edges. In the second session Neptune ran empty for the load test and was destroyed afterwards, so there is no live query clip."

### 12. DynamoDB run or query record (25 s, 6:40), clip REC12
- **Show:** clip REC12 (45.7 s, recorded 2026-11-18): the run-ledger RUN item with state complete and 10001 records, as seen from a terminal with the reader role ([decision log](agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md)). Cut to about 25 s.
- **Say:** "DynamoDB holds the run ledger, caches and query sessions, so every load and answer has a provenance record."

### 13. S3 Vectors query returning source pointers (35 s, 7:15), clip REC13
- **Show:** clip REC13 (46.3 s, recorded 2026-11-18): the ingest report and the query report ([ingest-report-2.json](agent-runs/phase-15/evidence/session-2/vectors/ingest-report-2.json), [query-report.json](agent-runs/phase-15/evidence/session-2/vectors/query-report.json)). Recorded results: 10,000 vectors written, 0 rejected; 5 of 5 known-item queries returned the expected neighbour; 7 pointers verified.
- **Say:** "10,000 vectors were embedded with Voyage voyage-4-lite at 256 dimensions from the Spark semantic summaries of the real slice. S3 Vectors returns the nearest items, each with a pointer back to its source text. The queries here are known items, so this shows that ingest and query agree, not recall on new questions."

### 14. Complete user query through the API (45 s, 8:00), clip REC14
- **Show:** clip REC14, recorded 2026-11-21 during the Q12 rerun, a request to the query-api with the live model. The Q12 rerun ran on the local loopback stack (client, service and graph export on one machine), **not** on AWS: confirm against the clip and say so on camera. For the call shape, the README [query examples](../README.md#query-examples). Results of the same runs: [docs/evaluation.md](evaluation.md), group 4.
- **Say:** "One API call: the planner resolves the question into a typed plan, retrieval gathers graph evidence, and the model writes claims that cite evidence IDs. This was recorded on the local stack on the real graph export, with the live model."

### 15. Evidence and explain endpoints (40 s, 8:40), clip REC15
- **Show:** clip REC15 (recorded 2026-11-21): the evidence record for a cited ID and the explain record for the same query. For the first-session equivalent opened as files: [query-explain-r8a.json](agent-runs/phase-14/evidence/14b/session-1/b8-8-smoke/query-explain-r8a.json) and [query-evidence.json](agent-runs/phase-14/evidence/14b/session-1/b8-8-smoke/query-evidence.json). Route names are in [docs/api.md](api.md).
- **Say:** "Every cited ID resolves to stored evidence. Explain shows the stages, prompt and model versions and the verifier's verdicts, not hidden model reasoning."

### 16. Claim verification, including one unsupported claim test (45 s, 9:25), clip REC16 + offline test clip
- **Show (recorded):** clip REC16 (recorded 2026-11-21): the claim counts (attempted, verified, rejected) in the explain output. Recorded context: in Q12 run-2, 65 verified claims were re-checked against the export with 0 contradictions, and 6 of 6 abstain-expected questions were correctly abstained ([docs/evaluation.md](evaluation.md), group 4); say that the independent re-check, not the runtime's own counters, is the evidence.
- **Show (offline clip):** the rag test that feeds the verifier an unsupported claim and sees it rejected, run with `sbt -batch "rag / testOnly <verifier spec>"` (rehearse: fill in the exact spec name from `modules/rag/src/test`; the rag tests ran inside the 17G `sbt -batch clean check`, the single spec was not run on its own).
- **Say:** "The verifier checks every claim against the evidence. A claim with no supporting evidence is rejected, and the system abstains instead of guessing."

### 17. Reproduction scripts, agent replay instructions, clean-checkout bounded run (45 s, 10:10), offline
- **Show:**
  - The README sections "Reproducing the agentic workflow" and the new setup, build and bounded-run sections ([README](../README.md#reproducing-the-agentic-workflow)).
  - Then a fresh clone of `main` in a new directory and the bounded local run: `bash scripts/smoke-local.sh --build` (starts the real query-api offline with a throwaway key and runs the smoke checks on fixture data; replayed in 17G on a fresh clone: `RESULT: PASS local offline-synthetic query-api passed all smoke checks (the six plus the semantic route and its cache counter) on 127.0.0.1:<port>`). Show the recorded result of the clean-checkout replay from `docs/agent-runs/phase-17/17g-replay.md`.
- **Say:** "Anyone can replay one bounded phase and the test gates without rebuilding the cloud. The smoke run uses fixture data and contacts nothing."

### 18. Terraform plan or deployed-resource evidence (30 s, 10:40), clips REC18a and REC18b
- **Show:**
  - Clip REC18a (27.6 s): the stage-a plan action list, summary add 171, result IDENTICAL to the reviewed derivation.
  - Clip REC18b (45.4 s): terminal view of four services with running equal to desired and a healthy target. Cut to the slot.
  - Plan checksums: [reports/release-manifest.md](../reports/release-manifest.md), section 3.
- **Say:** "Everything on AWS was created by Terraform from reviewed plans, each applied only after my approval record that names the plan's checksum."

### 19. CloudWatch elasticity dashboard (35 s, 11:15), clip REC19
- **Show:** clip REC19 (61.9 s, root console read-only, recorded 2026-11-18): the elasticity dashboard over the load run. The human's reading of it: HealthyHostCount 1 to 2 at about 20:54-20:55Z, CPU max 75.79%, request peak about 4.21K per minute and a p99 spike to about 5 s ([performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md)). The account e-mail may show in this clip (see the privacy rule); check it first.
- **Say:** "The dashboard shows load balancer requests and latency percentiles, healthy query-api tasks and CPU on one time axis."

### 20. Scale-out and scale-in evidence (55 s, 12:10), clip REC20 and archived logs
- **Show:**
  - Clip REC20 (60.1 s, root console read-only, recorded 2026-11-18): healthy hosts 1 to 2 at about 20:54-20:55Z and 2 to 1 at about 21:09-21:10Z.
  - The poll log lines: [b10-ecs-poll.log](agent-runs/phase-15/evidence/session-2/b10-load/b10-ecs-poll.log) (1/1/0 at 20:51:54Z, 2/1/1 at 20:52:55Z, 2/2/0 at 20:53:56Z; blank lines are credential gaps).
  - The load summary: [performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md) (levels 1, 5, 25 and 50 with 0 errors; the run **aborted** in hold-50 after 67 failed requests: 65 server errors and 2 timeouts).
- **Say:** "At 50 workers ECS scaled out; the polls show a second task running about a minute after the decision. The run then ended early on a burst of 503 and 504 responses, so the hold phase and the cooldown never completed. The scale-in back to one task was seen on the dashboard at about 21:09-21:10Z. I report that burst as a known limitation; its cause is not diagnosed." Do not claim throughput at two tasks.

### 21. One failure and recovery example (50 s, 13:00), clip REC21
- **Show:** clip REC21 (93.9 s, recorded 2026-11-18; cut to the slot): stop one query-api task, the 503 and 502 responses, the replacement task and `healthz` and `readyz` returning 200. Timestamps from [p11-failure.log](agent-runs/phase-15/evidence/session-2/b35-failure/p11-failure.log): stop at 21:37:55Z, both 200 from 21:39:48Z (113 s); second effective event 68 s.
- **Say:** what failed, what detected it, that recovery was automatic (a replacement task started and registered) and took about two minutes and about one minute in the two events, and that nothing was edited by hand.

### 22. Cleanup or resource inventory evidence (35 s, 13:35), clip REC22 and inventory files
- **Show:**
  - Clip REC22 (93.2 s, recorded 2026-11-18, root console read-only views may show the account e-mail; check first; cut to the slot): the pass-2 `RESULT:` line and the inventory counts.
  - Files: [before inventory](agent-runs/phase-15/evidence/session-2/inventories/before-cleanup-inventory.txt) (297 entries), [after pass 1](agent-runs/phase-15/evidence/session-2/inventories/after-pass-1-inventory.txt) (65) and [after cleanup](agent-runs/phase-15/evidence/session-2/inventories/after-cleanup-inventory.txt) (63).
- **Say:** "Everything was destroyed in two passes after the evidence was archived. The 63 entries left are two free Terraform guards and tag-index entries that were judged to be leftovers of deleted or inactive resources; I did not read the state of the second KMS key in the inventory. Both Voyage keys were revoked, and the deployer role was removed the next day."

### Closing (40 s, 14:15)
- **Show:** the cost report from runbook step C11b (AWS, Anthropic, Voyage and the combined total).
- **Say:** the oral points in section 3, briefly.

---

## 3. Things you must explain orally

- **Tool-policy disclosure:**
  - The course describes a Claude Code orchestrator; the main workflow used Codex and Cursor, with Claude Code for compatibility.
  - The instructor's 2026-09-29 chat reply allowed Claude, Codex and Cursor. It did not address the orchestrator and hook enforcement model, so do not claim more than it says.
  - The `.claude/` hooks run only in Claude Code. In Codex and Cursor the same rules were followed by process and human review.
- **Provider deviation:**
  - AWS Bedrock quotas were 0, so on 2026-11-09 the instructor approved the Anthropic API (`claude-haiku-5-5`) for answers and Voyage AI (`voyage-4-lite`, 256 dimensions) for embeddings.
  - Question text, evidence snippets and document text leave AWS.
  - The Anthropic path cannot use temperature 0, so repeated answers can vary.
- **Session 1 outcomes (say them plainly):**
  - EMR was PARTIAL: cluster, permissions, step submission and stage-in were proven, but hadoop-prep failed because a config file was never uploaded.
  - The 15B elasticity experiments were dropped for budget.
  - In 16B, 40 questions were asked: component 7/8, ranking 7/8, direct coauthors 0/14 (context budget), path 0/10 (cause not diagnosed during the session; the offline diagnosis and fix are Session 2 prerequisite P4; report what P4 actually found).
  - The first video was 63 s and exposed the account ID; this video replaces it.
- **Session 2 outcomes (2026-11-18, say them plainly; sources in [reports/final-report.md](../reports/final-report.md) and [docs/incidents/](incidents/)):**
  - EMR ran stage-in, Hadoop prep, entity resolution and the class-origin check. The Spark step failed (`EmrFileSystem` class not found); there was no retry, and the Spark export came from the local run of the same chain. (Later, in Phase 18 on 2026-11-25, the fixed step completed on EMR; see the Phase 18 note at the top.)
  - The first vector ingest failed for all 10,000 items with HTTP 401 (an invalid pasted key); the second wrote 10,000 vectors with none rejected.
  - The load run was aborted by a burst of 67 failed requests in the hold phase (65 server errors, 503 and 504, and 2 timeouts); the human accepted it as the result, with no rerun. Scale-out and scale-in were seen.
  - The base apply stopped once at a runtime-archive upload timeout and was recovered with a no-change plan.
- **Q12 rerun (2026-11-20 and 2026-11-21):** 33 questions, run twice on different code: 4 then 23 of 27 answer-expected questions passed all three scorer checks, 6 of 6 abstain-expected questions abstained, all three community questions failed in both runs ([docs/evaluation.md](evaluation.md)). Clips REC14-16 come from this rerun.
- **What Session 2 changed:** the repairs P1-P14 in the Session 2 plan, each tested and reviewed before going live.
- **Cost:**
  - The project ceiling is USD 25 across AWS, Anthropic and Voyage together, tax included. AWS budget alerts at 18, 20 and 22 are e-mails only, so our own caps did the protecting.
  - Give each bill separately, then the total. The final AWS figure comes from the bill, not the model.
  - Final figures ([cost-report.log](agent-runs/phase-15/evidence/session-2/c11/cost-report.log), 2026-11-20T15:48:56Z): AWS USD 17.88, Anthropic USD 0.08 (earlier phases), Voyage AI USD 0.00, combined USD 17.96, remaining USD 7.04 of 25.00. The Q12 Anthropic key is a separate scope: Console USD 0.08 for 2026-11-20 and 2026-11-21 UTC, not in the combined figure.
- **Dataset limitations:**
  - A bounded DBLP slice (dblp-2026-10-03, about 10,577 papers).
  - The OpenAlex, Crossref and ORCID inputs are small committed samples and were not scaled with the DBLP subsets.
  - Ranking questions rank only the researchers included in the runtime artifact, not the whole corpus.
- **Identity resolution:** say which ER mode produced the loaded graph (session-2-plan P10). The Session 1 graph came from the ER-disabled run. The Session 2 local chain ran the entity-resolution step (96.7 s at S), and the offline evaluation reports precision 100.0% (57/57) and recall 79.2% (57/72) on 194 binary held-out pairs with the deterministic policy ([docs/evaluation.md](evaluation.md), group 1).
- **Elasticity limits:**
  - HTTP services scale between 1 and 2 tasks.
  - Container Insights was off for cost, so task counts come from ALB healthy hosts and a once-a-minute poll.
  - The embedding worker stayed at one task.
  - Only one AWS load run exists, it was aborted, and it used the semantic route on an empty graph.
- **Schedule deviations:** Phase 12 Terraform was written in parallel with Phase 7, and the Phase 6 EMR gate and the Phase 7/8 live gates ran in Phases 14-15 (Phase 17 plan, section 2).
- **Offline versus live:** which clips were recorded live (the ten Session 2 clips REC09, REC10, REC12, REC13, REC18a, REC18b and REC19 to REC22, on 2026-11-18; REC14 to REC16 on 2026-11-21 on the local stack) and which come from archived evidence (items 11 and 17 and the log and file views); the AWS stack was destroyed on 2026-11-18, before the video was edited.
- **Agent-generated code:** be ready to explain any file the instructor picks: why Hadoop and then Spark, how each metric is defined, how ER decides, how the verifier works, what each store is for, and what scaled and why.

---

## 4. What was recorded live in Session 2 and what comes from other evidence (final)

The plan was [session-2-plan.md](runbooks/session-2-plan.md), sections 5 and 6 (R0 + R-b; R-c dropped 2026-11-16). This table records what happened, from [human-gate.md](agent-runs/phase-15/human-gate.md) and the [decision log](agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md).

| # | Source of the clip or evidence | Note |
|---|---|---|
| 9, 10 | REC09, REC10 (Session 2); L local evidence | the Spark step failed on EMR; Spark outputs come from the local run; L is local only and bypasses ER |
| 11 Neptune query | Session 1 files ([14c-results.txt](agent-runs/phase-14/evidence/14b/session-1/14c-load/14c-results.txt), [tunnel-test.log](agent-runs/phase-14/evidence/14b/session-1/14b-deploy/tunnel-test.log)) | R-c was dropped, so Neptune stayed empty in Session 2 |
| 12 DynamoDB record | REC12 (Session 2) | run-ledger RUN item, 10001 records |
| 13 S3 Vectors query | REC13 (Session 2) | 5 of 5 known-item queries, 7 pointers verified |
| 14, 15, 16 API query, evidence and explain, claim verification | REC14, REC15, REC16 (2026-11-21, Q12 rerun) + offline verifier test | local loopback stack with the live model, not AWS; the first-session equivalents are in [b8-8-smoke](agent-runs/phase-14/evidence/14b/session-1/b8-8-smoke/) |
| 18 Terraform or resources | REC18a, REC18b (Session 2) | plan action list; four services running |
| 19, 20 Dashboard, scale-out and scale-in | REC19, REC20 (Session 2, root console read-only) | the load run was aborted; scale-out and scale-in were seen |
| 21 Failure and recovery | REC21 (Session 2) | stop one query-api task; recovery 113 s and 68 s |
| 22 Cleanup and inventory | REC22 (Session 2) + inventory files | the deployer role was removed on 2026-11-19 (P39) |

**Items 19 and 20, what to say:** "The load was semantic search: each request looks up the embedding for one of a fixed set of real topic questions (cached after its first use) and queries about 10,000 real vectors in S3 Vectors. Query-api scaled on requests per task, with CPU as a second signal. The graph was empty during this run, so this measures the retrieval tier, not graph or LLM work. The run was aborted by a burst of 5xx responses in the hold phase."

The running time stays about 14 minutes if each clip is cut to the slot in section 1. Replace the "Say" lines of earlier-session items with the provenance sentence: which session the clip is from, and that the stack was destroyed afterwards.
