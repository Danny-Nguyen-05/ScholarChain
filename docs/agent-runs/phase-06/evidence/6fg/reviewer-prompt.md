You are the independent, read-only code reviewer for ScholarChain Phase 6,
Subphase 6F+6G, in /Users/danny/Documents/UIC/CS441/ScholarChain.

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Documents/plan/phase6.md, Sections 4–8, 6F+6G in Section 9,
   the Section 10 test matrix and Section 11. Plan SHA-256:
   6df6d856df6c4c6ee0a8f00125e78af1bce5e789666399ae48a9443aec955096.
3. Course Phase 6 and Detailed Spark requirements:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-6-build-the-temporal-coauthorship-graph-and-run-spark-analytics
4. docs/agent-runs/phase-06/{prompt,owner-report,test-report,repairs,review}.md,
   especially the 6F+6G sections, plus evidence/6fg/handoff.md, commands.md,
   final-gate-metadata.json, real-data-report.md, replay-comparison.json and
   manifest-file-audit.json.

Checkpoint facts:
- Branch phase-6; base and unchanged HEAD:
  6ae7378cbef90a176fd1faecae0dee0615eba9e3. Work is uncommitted.
- Exact tracked/untracked inventories: evidence/6fg/changed-files.txt and
  stable-source-before-check.json. Eight modified implementation artifacts:
  core SparkAnalyticsValidation.scala/SparkAnalyticsContractSpec.scala;
  Spark README.md, Phase6CJobs.scala, Phase6CReaders.scala, Phase6DEJobs.scala,
  Phase6CJobsSpec.scala and Phase6DEJobsSpec.scala.
- Nineteen new implementation artifacts: datasets/phase6/{README.md,
  dblp-archive-acquisition.v1.json,dblp-slice-manifest.v1.json};
  datasets/scripts/phase6/{acquire_dblp_slice.py,test_dblp_slice.py};
  Spark production Phase6Context, Phase6EventLog, Phase6Export, Phase6FGJobs,
  Phase6Main, Phase6Plans and Phase6Report; module Phase6FGJobsSpec;
  independent IndependentPhase6FGFixtures, IndependentPhase6FGSpec,
  IndependentPhase6PipelineSpec and IndependentPhase6SafetySpec;
  tests/src/test/resources/phase6/{tiny-pipeline.xml,empty.jsonl}.
  Coordinator changes only phase-06 prompt/reports/repairs and evidence/6fg.
- User approved all six defaults: factual summaries under 1,200 characters;
  pinned DBLP 2026-10-03, eight distributed-systems venues in 2005–2026,
  <=20,000 pubs, 1.25 GiB/30-minute download caps; unchanged local Hadoop→ER→Spark
  with ER LLM disabled; required S-source mean/P90 estimate; N1/N3/N4 fixes;
  per-window LPA iterations and missing-endpoint/sample counter clarification.
  Prior defaults remain CC50/kcore50/checkpoint5/community20/hops6/K20/S32/seed441.
- Exact commands/environment are in commands.md and CLI command JSON files.
  Dataset Python 12/12; core targeted 15/15; latest module 33/33;
  final corrected tiny pipeline 1/1. Earlier independent target 13/13;
  all latest assertions pass in the full independent result below.
- Full JDK17 sbt -batch check: exit 0, 551 passed / 0 failed:
  core144/Hadoop64/ER39/Spark34/independent263/build7; real692.82s, sbt691s.
  final-check.txt: 1,358,948 bytes, SHA-256
  6f48042efe332864661f5d8a73dfa8565fd257db53ff3bcc97371b724919844c.
  Completed 2026-10-22 13:51:06 CDT; Java17.0.20.1, sbt1.10.7.
  Full log is unfiltered; expected injected failure traces are self-tests.
  All 27 source/config/test/manifest files stayed unchanged during the gate.
  Post-gate compiled fingerprint matches both real runs; diff --check exit0.
- Dataset: 10,577 pubs / 21,819 exact names; slice SHA-256
  c25a1e1a0d517abaadf370c88b3528039c50ad8ec3790c27381a3c2e2ecde522.
  One 1,107,081,001-byte download in244.720s, within caps; replay no network.
- Hadoop exit0 real37.38s; ER initial output-bound refusal exit2, then local
  bound-only retry exit0 real97.23s, 20,000 comparisons, fake0/live0.
- First Spark attempt failed checkpoint Union constraint rewriting, exit1,
  real83.61s, no completion marker. Repaired with optimizer-only inferred
  constraint propagation disabled and a multiwindow six-hop regression.
  Full failure/diagnosis evidence retained; no upstream-ticket claim.
- Fresh repaired Spark runs exit0 real180.45s/158.07s, both
  run:f02acf56-4bea-4009-adaf-b11d5afceb49, code fingerprint
  a6719cbb892e795e3b4e20be99c70c1c74c1ee8ce95887e8c418d9aeb3672971.
  Roots target/phase6-runs/6fg-spark-{first,replay}-v2/<runId>;
  shuffle4→2. Every28table count/hash and counter array matches;
  markers verify, all four load manifests are byte-identical, all paths exist.
  Actual all-table Parquet reread/hash tests are separate from the real replay's
  per-pipeline hash comparison; manifest-file-audit.json is a filesystem audit.
- Real all-years graph:81,181coauthor edges;1,045components; largest17,179,
  fraction0.81933515;178singletons. Integrity25non-hard ORCID conflicts,
  zero hard failures/missing endpoints/pair mismatches. All six LPA windows
  non-converged at20; all six S32 estimates reported. The report contains
  metric/community distributions, paths, stages/partitions/shuffle and paths.
- Historical carryovers and dispositions are in repairs.md: summary entity kinds,
  authority/ORCID/counters, compiled identity, schema/layout, pre-checkpoint plans,
  durable event summary, full replay/core parsing, BFS/LPA hardening and R1-O1.
  Initial compile/setup/heap/count assertion failures are honestly disclosed;
  intermediate logs are labeled excerpts with original hashes/full ignored copies.

Known limitations to assess, not conceal:
- Reuse verifies bound metadata/identity, not a deep audit of completed Parquet.
- Fixed256shard hashing retains sorted shard JSON on executors; bounded scale only.
- Local class-directory and packaged-JAR fingerprints differ; cross-runtime or
  cross-artifact replay is unverified. No EMR/AWS/live model/store/embedding calls.
- Distance estimates cover seeded sources in largest components, not exact diameter.
- Synchronous LPA oscillates on isolated pairs and bridge measures depend on partition.
- Representative policy versions tag one ordering rule; no alternate-policy dispatch.
- Temporal rows expose actual current communities and best overlap scores, not a
  separate matched-community ID. Work-source projections/rejects use their own
  documented schemas rather than pretending to be domain GraphNodes.
- Rendered plans may truncate at the memory cap. Phase7 yearless Neptune mapping,
  later packaging guards and Phase13/15 EMR/runtime gates remain open.

Review rules:
- Read-only: do not edit, build, test, run Spark, mutate data, call AWS or model
  providers, read secrets, commit or push. Do not launch another reviewer.
- Inspect git diff 6ae7378cbef90a176fd1faecae0dee0615eba9e3 AND untracked files.
- Check one-writer ownership; forbidden Spark/driver APIs; determinism/tie rules;
  exact fixture correctness; windows/presence; metric invariants; IDs/provenance;
  source-reference grounding; Parquet/schema/layout/hash/manifests; failure/output
  gates; source timing and retained evidence; truthful README/report coverage.
- Report ALL confirmed findings together with severity, path/line, evidence,
  impact, named owner and acceptance check. Separate blockers from later gates.
- Return APPROVE or REQUEST-CHANGES, filled docs/agent-runs/README.md report fields,
  risks/manual action and a complete next prompt. On REQUEST-CHANGES route local
  repairs and a fresh gate/recheck. On APPROVE ask the user to commit before a
  separately requested 6I; do not start 6I, approve the whole phase or close EMR.
