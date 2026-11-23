Phase 15 commits, listed in Phase 17 (package 17D) from the pull-request merge(s) that brought this phase into main (git log <merge>^1..<merge>^2, oldest first).

Merge 80f965bc8324886674c2d5f7db09065d7e550928 Merge pull request #11 from Danny-Nguyen-05/phase-15
d5e74aaf0c9ff3f59e93c87b16231c0b3f069545 Phase 15 P0: AWS budget alerts at USD 18/20/22 (USD 25 limit, credits and refunds excluded), with tests and reviewed records
cceb1f5d3d40d8a23fe1c0f042593923046c1bfd Phase 15 P40: public POST /v1/semantic/retrieve (API key, bounded topK/question/body/filters, 32-level JSON depth limit, per-key token-bucket rate limit with typed 429) and LRU query-embedding cache with /metrics counters; offline-synthetic smoke, independent adversarial tests, reviewed records (review 1 APPROVE)
7a02de252c36d284267f162911383dce02160fe5 Phase 15 P41: ALB request-count target tracking for query-api (optional, query-api only, CPU policy kept), validated rate-limit env wiring, ALB dashboard panel, terraform tests; records (gate run 2 PASS, review 1 APPROVE)
f801d28fb18a600fa1ba70439fb7799f5df6dea2 Phase 15 pipeline bundle: EMR step chain fixes D1/D2 (UUID hadoop run id, plain output root, selective copy-out), bootstrap mount retry, D3 cluster (r5.xlarge primary, ER heap 12g, S run cap 75 min with per-step timeouts), per-run ledger estimate and --record-actual, release caps (4 runs, 3.36, 60000 sample records), batched and concurrent embedding ingest with the completeRun fix, storage loader concurrency and ledger, L local evidence and identity-bypass Spark run, shared elasticity Terraform edits (P9/F2/F3), tests and reviewed records (clean-snapshot check PARTIAL passed=6, sbt check pass, review 1 APPROVE)
a975775a321beaa82befdbc008d70f411ff0797d Phase 15 repair round, P42 and P35: EMR cumulative cap 3.53 (one S retry admitted when S measures <= 0.87) with operator rounding-budget steps and timeout-then-retry tests; P42 semantic loadgen (150 pinned questions, capped levels, 429s counted apart, --observe-seconds loopback-only) with manifest and checks; P35 local rehearsal evidence and scaling target T=3000, semantic rate limit 3500/burst 7000; runbook P18/P19/P35 updates; records (reviews 2 and 3 APPROVE, clean-snapshot check PARTIAL passed=6, sbt check pass)
8d0e2116352b3fe9b9ddedf790b11f207ab66635 Phase 15 P0: refresh billing pins for the Phase 14B modify
2611cc63b21798ce9f1e0f51054058590b9fce30 Phase 15 P0: human gate record for the Phase 14B budget modify
9e881a2e595328c5d3a4a9fc45827cb6b4a6367f Phase 15 frozen session commit: P0 modify incident modify-20261116-01 record; budget_execution modify drops the .backup byte-equality check (Terraform re-serializes it) and records the failure cause in the preservation receipt; budget_verification read-only incident-linkage verify bound to the preserved artifacts; billing README/VERIFICATION, session-2 plan and live-session runbook amendments; records (P0 reviews 1 and 2 APPROVE, clean-snapshot check.sh PASS gates=7)
c5689e7633c38dac7f6ad02d6be97280a44f278f Phase 15 P0: incident linkage verification of modify-20261116-01 (I1 differences=0, I3 exit=0)
0b37c9d2611938d0a0b8fdf892ccb90d8172f77f Phase 15: spark.task.maxFailures 1 -> 2 (EMR module with pinned validation, scripts/config/spark-12-10.conf) for SPARK-43221 transient task failures; maxAppAttempts stays 1; tests; records (Phase 12D authEngineVersion misattribution corrected, review APPROVE, clean-snapshot check.sh PASS gates=7)
aa748d15b53773ff5f313472acb9a27b0e297fba Phase 15: records for the maxFailures=2 local S run (counters equal to the reference; clean-build JAR reproducibility finding)
8123ebb810935c74b9277ec70f1df0e09f47c9f4 Merge phase-15-maxfail: spark.task.maxFailures 1 -> 2 (SPARK-43221), reviewed, check.sh PASS gates=7, local S counters equal
fa9ad7ec22623b61ad206e524ffbc0c04e858044 Phase 15: refresh source-freeze pins for the maxFailures=2 change (emr/variables.tf, infra/terraform/README.md)
aee1c022d2e6df7d76475600ec04ed6e4f83fe21 Phase 15 Session 2 amendment: no Anthropic spend in Session 2 (B10.3 --llm, six-check smoke B8.8/B12.3, B11, B12 marked not in Session 2; Anthropic secret is a non-working placeholder, no real key, no spend limit or revocation); section 4a item 8 revised; records (review APPROVE, fix round checked)
bd0b8180b919ed61f6234fa515f4c07d1137a641 Phase 15: Session 2 approval record (Procedure R)
5c74643868e24f939467aae8701f5ac4686e2760 phase-15 orchestrator: Session 2 records, C11 cost check and human acceptance; P39 deployer removal procedure and test (infra-engineer)
bd446e9d99502be719f9da9b1e1a7a68cee52d2b phase-15 documentation-engineer: README agent catalog and "Reproducing the agentic workflow"

Merge 6168aa0ad5d0a6b41310309f628ea6f4e3fe9773 Merge pull request #12 from Danny-Nguyen-05/phase-15-q12-merge
7c13904f61b37e57662a0f1a67bc6ef99c1ea9e4 phase-15 rag-engineer: P36 synthesis-v2 prompt and schema label, v1 retired and refused
d92362158d24df7024203051891ec74821d2dffe phase-15 domain-engineer: P36 core runtime config pins synthesis-v2
494737bdfbe7f66c6bdf6612949eb954bdedca42 phase-15 experiment-engineer: Q12 benchmark inputs, answer key, scorer and evalq12 harness (33 questions, 3 x 11 types)
9f77a5ef19c180500a7e728fd7bb029dc058ff58 phase-15 rag-engineer: P3/P4 direct-coauthor and path context budget, verified N-of-M, L2 label guard, L4 README
0b69f940ff41f27682a2c2b74a23156128432b5b Merge phase-15-q12-experiment into phase-15-q12-rag (Q12 inputs for the planner spec)
7c34772b5414196b29eeea92030cf0c37a91bb89 phase-15 rag-engineer: Q12 planner spec (24 fallback, 9 scripted-LLM) and reachable explain-the-topic fallback
336950e0037b17f0aa137af1f484c95e784cc0e0 phase-15 storage-engineer: local export loader (LocalExportStores, indexed LocalGraphReader, typed runtime artifact rows)
b334906bda1a7437d63840da0caa7f1d1fb32ec6 phase-15 rag-engineer: review round 1 (count-mismatch invariant, descriptive cap for list operations, docs, tests)
44559557e512300300fc45e10c7c13529d85e38e phase-15 experiment-engineer: Q12 review round 1 (expected 422 handling, strict abstention, Jaccard lower bound, replayable key validation, preflight, probe mode, cost bounds)
3e5ddc8ed651d04c2e2b44bfedf05d1023b74fc3 phase-15 experiment-engineer: revert llm-allocation.json note edit (keep the Q12 cost caveat in the Q12 manifest and README only)
42d73cd389b5ed364dcb24f8500f331876b3a255 phase-15 storage-engineer: README note, measured CSV validation cost for the local export loader
6ddd85f7fe51540d995e2191f80ee964b8d3591e Merge phase-15-q12-experiment (Q12 review round 1 inputs) into phase-15-q12-rag
0318473ca0186f8932827c832171df2021da3442 Merge phase-15-q12-storage into phase-15-q12-services (local export loader for the Q12 launcher)
13c33303b63e552028095ba2e444b11335c37ddd phase-15 rag-engineer: Q12 planner spec derives routes and expectations from question-specs.json, no hard-coded ids
ae39642e8e5b2850342e8ba270fb5198b0b47cff phase-15 experiment-engineer: Q12 review round 2 (transfer 36, neutral expected refusals, unverified in the scorer output, fullmatch, preflight wording, input cross-check, own run-record schema)
7e5efc03d7acb8b13baeaa81bd8a1c3a02fc5ba4 phase-15 storage-engineer: review round 1 for the local export loader (shared GraphProjection, local reader parity tests, scope and doc fixes)
5a3ff7cfd1fdf68e3a9f4fca8b29821f074e0076 phase-15 storage-engineer: round 2 notes (strict graph-edge columns, README difference list, drop unused helper)
a72d25c6291c3aa4dc06839f8af005c114987a86 phase-15 experiment-engineer: Q12 evidence type becomes a graph-answerable joint-works pair question (no vectors locally); run settings graph mode and 30 s deadlines
c1ecc1d2d0ba823ec0a27f9112ced809c5a855df Merge phase-15-q12-experiment (graph-answerable evidence questions) into phase-15-q12-rag
669498507c01935f64b4a99e235cb33ce4c9676d phase-15 rag-engineer: Q12 planner spec for graph-answerable evidence questions (27 fallback, 6 model-planned)
09bcb3d8260f84aa5b6b1459013a4688d42636cc phase-15 experiment-engineer: Q12 run settings (packaged deadlines primary, disclosed raised profile only if the probe needs it), substituted evidence framing, planner-spec open item cleared
886b0f7403cbc37580b8a5c27bbaa30971246d55 phase-15 service-engineer: local query stack (LocalPortFactory, LocalQueryStackMain), retrieval-mode override, no-key refusal, tests, README (review rounds 1-3)
842fb69c678d3b3a9768dee3b00f537ebd657e71 Merge phase-15-q12-services into phase-15-q12 (Q12 local benchmark stack)
840802a5eaf0f211778fc7b39b9a524b63d5c7ad Merge phase-15-q12-rag into phase-15-q12 (Q12 local benchmark stack)
8ae001d469e280368c52eec26073855619505692 Merge phase-15-q12-storage into phase-15-q12 (Q12 local benchmark stack)
ec675d562d9e923f36885d8dc9bd27c04d59b719 Merge phase-15-q12-experiment into phase-15-q12 (Q12 local benchmark stack)
443e4891719a9fa1137a143f7c9022a28f7b0175 phase-15 service-engineer: Q12 graph paths (level-by-level BFS, depth clamp, truncation) and community routes, tests (review rounds 1-2)
86822024ee828b6dec6e7b0f82ca311bdd912fc5 phase-15 rag-engineer: Q12 planner window normalisation, closed stage-log reasons, display names in answers, stage-log capture level fix, tests (review rounds 1-2, test repair rounds 1-2)
1a6f3427e3f359515335b8e4344cff64ac03a638 phase-15 experiment-engineer: option A, raise LLM buckets 16b 40->80 and 17 5->10, sourced observed-cost notes, tests (review rounds 1-2)
9348c857f98070cf7781ddb774eb18bce04ff51f phase-15 test-engineer: option A bucket pins and allocation manifest cross-check (review rounds 1-2)
827fcd5a425c6da65143c3460f36e00673772fc3 phase-15 documentation-engineer and coordinator: option A bucket and observed-cost rows, runbook note, recorded decisions (review rounds 1-2)
