# ScholarChain release manifest

Status: draft for the Phase 17 final gate, written on 2026-11-22 by the documentation-engineer (instance 2). Each entry is copied from committed evidence and carries a link. "Not recorded" means no committed evidence holds the value; nothing was filled in from memory. The final commit SHA cannot be known until the release commit exists, so it is marked "set at the release commit".

**Phase 18 update (2026-11-26, documentation-engineer, branch `phase-18` at `b11afe9`).** Sections 1, 3, 6, 9, 10, 11 and 12 were updated from the committed Phase 18 records ([human gate](../docs/agent-runs/phase-18/human-gate.md), [test report](../docs/agent-runs/phase-18/test-report.md), [Day 2 evidence index](../docs/agent-runs/phase-18/evidence/day2/INDEX.md)). Added rows are marked "Phase 18"; Session 2 rows are history and are unchanged. Hash pins in this file are recomputed at the release commit (unchanged rule). **Pins updated on 2026-11-26:** only the evaluation manifest in section 9 (`experiments/manifests/16-evaluation.json` changed in `b11afe9`; its new sha256 was computed with `shasum -a 256`). These other pins that name a repository file were recomputed the same way on 2026-11-26 and equal the value already written, so they were not changed: `datasets/samples/SHA256SUMS`, `datasets/dataset-manifest.yaml`, the four prompt and schema files, `infra/terraform/.terraform.lock.hcl`, `project/Versions.scala`, the Q12 `SHA256SUMS`, answer key and questions, the Session 2 cost report, EMR upload manifest and downloads list, and the Session 2 decision log. Pins not in that list (for example the dataset sample hashes inside `SHA256SUMS`, plan checksums, image IDs and values cited from logs) were not recomputed in this update. They must be recomputed again at the release commit.

Rules used: values that name an account (account ID, bucket names, ARNs) are left out on purpose; hashes of public artifacts are copied as recorded. Commands marked "not replayed in 17A" were not run for this manifest; the 17G clean-checkout replay (fresh clone of `main` at `d1d4fe7`, JDK 17, offline, 2026-11-22) ran the commands listed in section 25 of the [final report](final-report.md), and its record is `docs/agent-runs/phase-17/17g-replay.md`.

## 1. Commit and tag

| Item | Value | Source |
|---|---|---|
| Final release commit SHA | set at the release commit | to be filled by the coordinator after the last commit on `main` |
| Current `main` (when this manifest was written) | `55fb1b379e2408af0bbfa3a3bc9d2e69b613a84d` (`55fb1b3`, merge of pull request 13, phase-16) | `git rev-parse main`, observed 2026-11-22 |
| Working branch | `phase-17` from `main` at `55fb1b3` | [Phase 17 work order](../docs/agent-runs/phase-17/prompt.md) |
| Git tag | on 2026-11-22 none existed (`git tag` printed nothing). Phase 18, observed 2026-11-26: `git tag` prints `v1.0-final`, which points at commit `ad86b07` (the merge of pull request 17, the first submission). A tag for the Phase 18 release is for the human to decide | observed 2026-11-22 and 2026-11-26 |
| Phase 18 branch and head | branch `phase-18`, head `b11afe9` when this update was written; Phase 18 started from `ad86b07`. The merge to `main` is the human's decision and had not happened at the time of writing | `git rev-parse --short HEAD` observed 2026-11-26; [Phase 18 work order](../docs/agent-runs/phase-18/work-order.md) |
| Phase 18 live-session code | `fe0b6ccdf1089deb24e2967a09d94ada9b1aae33`, frozen for Day 2 (no commit during the session) | [Day 2 evidence index](../docs/agent-runs/phase-18/evidence/day2/INDEX.md) |
| Session 1 live-session code | `b6dc94d` (end of repairs) | [Phase 14 human gate](../docs/agent-runs/phase-14/human-gate.md) |
| Session 2 live-session code | `bd0b8180b919ed61f6234fa515f4c07d1137a641`, frozen for the whole session | [Phase 15 human gate](../docs/agent-runs/phase-15/human-gate.md) |
| Q12 run-1 code | `ec675d562d9e923f36885d8dc9bd27c04d59b719` | [docs/evaluation.md](../docs/evaluation.md) |
| Q12 run-2 code | `827fcd5a425c6da65143c3460f36e00673772fc3` | [docs/evaluation.md](../docs/evaluation.md) |
| Phase 16 commits | `0b422215743a11c31482fc4f876e9c43634ccdcf`, `fa908da6b797eca20283197068513b53d70d2134`, `b391bea7c038d3d54d1eeb181a626a8226df1d52` | [phase-16/commit.txt](../docs/agent-runs/phase-16/commit.txt) |
| Accepted commit per phase | recorded per phase | [docs/agent-runs/](../docs/agent-runs/) (`human-gate.md`, `commit.txt`, `accepted-commit.md`) |

## 2. Test counts

Source: the full check `scripts/check.sh` run `20261122T055838Z-17867` on `main` at `55fb1b3` (JDK 17), result `RESULT: PASS gates=7`, **as observed and reported by the coordinator**. The run log is not in the repository at the time of writing; the coordinator records it in `docs/agent-runs/phase-17/test-report.md` after the final full check. The counts below are the coordinator's, copied as given.

| Gate or suite | Count |
|---|---|
| `scripts/tests` | 1200 |
| `scripts/phase12d-spike/tests` | 78 |
| `scripts/billing/tests` (three suites) | 121, 84, 39 |
| `tests/scripts` | 487 |
| `tests/infra` | 468 |
| sbt (three test blocks, in the order the check prints them) | 194, 707, 30; 1 canceled |
| Terraform tests (six, in the order printed) | 12, 19, 114, 40, 6, 333 |
| Overall | `RESULT: PASS gates=7` |

Earlier archived check results for comparison (different trees): `sbt check` at Session 1 closeout, 1567 succeeded, 0 failed, 1 canceled ([Phase 14 human gate](../docs/agent-runs/phase-14/human-gate.md)); regeneration of the Phase 16 tables, `REGENERATION: PASS pass=24 fail=0 skipped_scripts=0` ([regeneration-check.log](../experiments/results/phase16/reproducibility/regeneration-check.log); replayed 2026-11-22 in 17A with the same line, exit 0). `sbt -batch clean check` from a clean checkout: not replayed in 17A; passed in the 17G replay (fresh clone of `main` at `d1d4fe7`, JDK 17, offline, 2026-11-22): 1,773 tests succeeded, 0 failed, 2 canceled, sbt total time 14:48. The full `scripts/check.sh` result on that clone is in `docs/agent-runs/phase-17/17g-replay.md`.

## 3. Terraform plan checksums

Terraform and provider pins: Terraform 1.13.5, AWS provider 6.44.0, lock file `infra/terraform/.terraform.lock.hcl` ([infra/terraform/README.md](../infra/terraform/README.md)). The plans below were saved, reviewed and applied in Session 2 on 2026-11-18 at commit `bd0b818`; the saved plan files are private and not in the repository, only their sha256 values are recorded in the [decision log](../docs/agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md).

| Plan | Run ID | Summary | `APPROVED_PLAN_SHA256` |
|---|---|---|---|
| Stage a base | `20261118T144713Z-72996` | add 171, change 0, destroy 0 | `8e3a37045adf9b0a627b4c79f084fac8524493faacc238e7d97494b6202bf7ec` |
| Recovery (after the upload timeout) | `20261118T151242Z-76267` | no changes | `9078b23b17b93e204cc2a1eeb5c8e0b73e3721c15a33da0d6ca9c0fa7092c17f` |
| EMR enable | `20261118T162405Z-84268` | add 13 | `62ce522ec5947078fccd551dfb25888f499e1a552565b6a73f2cc4f879c4545f` |
| R-b Neptune base | `20261118T195957Z-7910` | add 5, change 1, destroy 12 | `322eca6d43f2f40e4bf6f249b3e9a7a33a2eeae08b315f5d779d0fb8b066808a` |
| Runtime | `20261118T202333Z-13858` | add 25, change 4 | `39f7d083fd5385fa0d4c1c0d3a285330bc5cb887ba32e2c47637a8426cceee02` |
| Cleanup prepare | `20261118T215001Z-25148` | 20 updates (protection flags) | `3efd07006132ee8b048da00b6586966ad220dcef3fb9be311347c89fbc2c4225` |
| Phase 18 stage a base (2026-11-25, commit `fe0b6cc`) | `20261125T164849Z-66547` | add 171 (the human gate and test report give 171 creates, plan identical to the reviewed list) | `b1b73a15d9efd48ea9b1d9d6863eac29468aa00d46c900b0443bc3cedc2cb40c` |
| Phase 18 runtime archive upload plan | `20261125T165515Z-72896` | no changes (0 changes per the human gate) | `cfd3e485d5b88182d5b80baa5d39bd800e5f70dfe66ffc6e143f6f2196edaac6` |
| Phase 18 EMR enable | `20261125T172425Z-89082` | add 13 | `468c8713e0958cc4052113a816a6635dcde3654b587207141f4c3a1033949b94` |
| Phase 18 EMR artifact upload plan | not a Terraform plan; PLAN-SHA256 of the upload script | 17 files verified | `944e04bd92708f37e31fa5af4410d020479323814557a8d4cb6d8bb4fc6fab3e` |

Other recorded checksums: Terraform state sha256 after the stage-a base apply `9d4807e9d412bfb39865e9b7ad9936eaddbcd2c7144239e5732d4e2bb95f5ac6` ([state-sha-after-stagea-base.log](../docs/agent-runs/phase-15/evidence/session-2/stage-a/state-sha-after-stagea-base.log)); before cleanup `bcf4d0fbaa0fceecc8735c7bac62f9598c2fba4a000e1fb245925589f4922fc5` (both values are the hashes written inside the two logs; the logs' own file hashes are in the Session 2 INDEX) ([state-sha-before-cleanup.log](../docs/agent-runs/phase-15/evidence/session-2/archive/state-sha-before-cleanup.log)). Deployer stack plan: 13 adds, backup sha256 `24864772984bfced596c748ab4172732f873c2b98a2cd7d59b459206fbf3b101` (decision log, line 2); P39 removal plan: 18 destroys (the saved plan file is private; its hash is not recorded, the state sha256 before it is `fd0170da40c6d084d428c0979de1d9cd2b5458b02bad35d9917cdc0bd59d3e3a`, [p39-deployer-removal.log](../docs/agent-runs/phase-15/evidence/session-2/p39/p39-deployer-removal.log)).

The three Phase 18 Terraform plan rows (stage a base, runtime archive upload, EMR enable) were saved, reviewed and applied on 2026-11-25 ([stagea-base-plan.log](../docs/agent-runs/phase-18/evidence/day2/stage-a/stagea-base-plan.log), [stagea-upload-plan.log](../docs/agent-runs/phase-18/evidence/day2/stage-a/stagea-upload-plan.log), [stagea-emr-plan.log](../docs/agent-runs/phase-18/evidence/day2/emr/stagea-emr-plan.log), [emr-upload.log](../docs/agent-runs/phase-18/evidence/day2/emr/emr-upload.log)); the values are the `APPROVED_PLAN_SHA256` and `PLAN-SHA256` lines of those redacted logs. The cleanup and the deployer-role plans of that day have their own logs in the same evidence folder and are not repeated here.

**Archived plan versus the final state.** The deployed environment was destroyed in Session 2 (cleanup pass 1: 201 deletes, inventory 297 to 65; pass 2: 1 delete, 65 to 63; [section-c results](../docs/agent-runs/phase-15/evidence/session-2/section-c/cleanup-results.txt)), and the deployer role stack by P39 on 2026-11-19. Phase 18 recreated part of the stack for the EMR proof on 2026-11-25 and destroyed it again (pass 1: 183 deletes, 331 to 87 inventory entries, partial at the known Elastic IP 403; pass 2: 1 delete, 48 to 46; then the 13 operator-role resources and the deployer role with its 18 resources; [Phase 18 test report](../docs/agent-runs/phase-18/test-report.md), Day 2). The final state is the same "destroyed" state; the 46 remaining inventory entries are tag-index records, none billable, and the KMS key is pending deletion. The Session 2 leftovers (63 entries) are listed in the [Phase 15 human gate](../docs/agent-runs/phase-15/human-gate.md). A Terraform plan for the release commit: **not recorded** (a real plan needs AWS read access and the private variable file; it is a human-gated step, not run in 17A). The terraform gate of the full check in section 2 passed (the check records `RESULT: PASS gates=7`; the Terraform test counts are in section 2).

## 4. Image digests

| Image (commit tag `bd0b8180b919ed61f6234fa515f4c07d1137a641`) | Local image ID recorded before the push | Source |
|---|---|---|
| `scholarchain-query-api` | `sha256:1fecd6604e8aa902fd7d48a7912bec6cdd6503d51356c608791127ec95093ddc` | [rb-runtime-results.txt](../docs/agent-runs/phase-15/evidence/session-2/rb-runtime/rb-runtime-results.txt) (push dry run) |
| `scholarchain-graph-service` | `sha256:99a7e7a9e96aa1ae2d44878ced198dc541ee0acc0a50b18e802d777664df3d1b` | same |
| `scholarchain-semantic-service` | `sha256:b8e734f26862709b26aa7da5ae46957786a1b0384b6bf2f28972c0a9a955d31b` | same |
| `scholarchain-embedding-worker` | `sha256:607f8b01d12c00106fb2f4213c3eae110a757f22bcc06b0f99ceeab32bb1ab9a` | same |

These are image IDs of the local build (linux/amd64, `--provenance=false --sbom=false`), which the push script matched against the release manifest before pushing. The push log states that each registry digest "equals the pushed digest" ([rb-runtime-results.txt](../docs/agent-runs/phase-15/evidence/session-2/rb-runtime/rb-runtime-results.txt), lines 186-189). The runtime-apply dry run records the four digests the verified push resolved to (same file, lines 252-255): they are the same four `sha256:` values as the image IDs in the table above, in the same order, with the repository names masked in those lines, so the order-based pairing is inferred, not printed. The push record `push-record.json` itself lives under the git-ignored `target/release/` directory and is not committed. The running-task digests could not be read (no role had `ecs:ListTasks` or `DescribeTasks`; [Phase 15 human gate](../docs/agent-runs/phase-15/human-gate.md), kit gaps), so the registry digest check with immutable tags was used. The images no longer exist: the ECR repositories were destroyed on 2026-11-18. Base image: `eclipse-temurin` 17 JRE index digest `sha256:8993f1aed8b25fcea7a7047a7949c1866fa558fc6830d938c22c4f13b26be9d7`, as inspected in Phase 13 ([imagetools-inspect.txt](../docs/agent-runs/phase-13/evidence/13a/build/imagetools-inspect.txt)); whether the Session 2 images used that exact base digest is not recorded.

## 5. Dataset snapshots

| Source | Snapshot or version | Retrieval | Checksum | Source |
|---|---|---|---|---|
| DBLP XML | `dblp-2026-10-03` (DOI 10.4230/dblp.xml.2026-10-03), upstream MD5 `cbd329100ea1bbb2873fa2f6d414ea00` | 2026-10-05 | committed sample `samples/dblp/linked-records.xml` sha256 `e23d50c04b2cadcc01ff719ea1841157f2d865dd0e2657b27d3bd4931fe2a935` | [dataset-manifest.yaml](../datasets/dataset-manifest.yaml), [provenance note](../datasets/provenance/dblp-snapshot-2026-10-03-dagstuhl.txt) |
| DBLP S slice (10,577 works) | slice of `dblp-2026-10-03` | n/a | EMR input file sha256 `c25a1e1a0d517abaadf370c88b3528039c50ad8ec3790c27381a3c2e2ecde522` (6,003,592 bytes) | [emr-upload-manifest.json](../docs/agent-runs/phase-15/evidence/session-2/emr/emr-upload-manifest.json); [slice manifest](../datasets/phase6/dblp-slice-manifest.v1.json) |
| DBLP L slice (48,187 works, local only) | slice of `dblp-2026-10-03` | n/a | sha256 `7e62bb428a6ef34dd7961f337b6a2d42978d7c2cbf1c566c7ce83eac3b21ea34` | [experiments/README.md](../experiments/README.md); [L slice manifest](../datasets/phase15/dblp-l-slice-manifest.v1.json) |
| OpenAlex | live REST at retrieval; bulk snapshot date not pinned | see manifest | sample sha256 `6cff12f2ec1439acc66b89a9c30c54aa90bec8e3e11c317561f3e4a0f9a65d8c` | [dataset-manifest.yaml](../datasets/dataset-manifest.yaml) |
| Crossref | live REST at retrieval; snapshot not pinned | see manifest | sample sha256 `a6e3c40e178b7ce7f74ed870a48b4a2951de1705e7a0ed8f8fd40838bc4d39cc` | same |
| ORCID | live public API record at retrieval; annual file date not pinned | see manifest | sample sha256 `5000694a8e93f5ff2393f7f25f9a908d139e7ba20d26c0d98141e5ce1e070325` | same |

Sample checksums file: [datasets/samples/SHA256SUMS](../datasets/samples/SHA256SUMS), file sha256 `deef0c58a1ce191cc31bed6c43fb7677c102d952dc3836a4b47e1bf46bcd7d51` (computed 2026-11-22). Manifest file sha256 `cf1cba59e3fe8e7f2553a46cf4b27894b8409343082e766531b3ba1951e8a1b3` (computed 2026-11-22). Re-verify both at the release commit.

## 6. Run IDs

| Run | ID | Source |
|---|---|---|
| Spark export used downstream (local P6 chain, size S) | `run:ba7402d1-959a-4277-8c6e-e92878a38afa`; its `SHA256SUMS` sha256 `fa41d3e094ae1a25b724456fb0dc2a503d8698f1537cfbbc916075ff29e5541e` | [decision log](../docs/agent-runs/phase-15/evidence/session-2/00-timeline/decision-log.md) (block 22) |
| Session 1 Spark export loaded into Neptune | `run:f6e63b4b-d542-4a32-930c-f21f002cba76` (78,104 nodes, 328,967 edges) | [real-slice-export.md](../docs/agent-runs/phase-14/evidence/14b/replan/real-slice-export.md) |
| Session 2 run prefix | `run-20261118` | decision log |
| EMR run (size 100), Session 2 | `15a-emr-size-100-20261118T163203Z-87466` (Spark step failed) | [incident record](../docs/incidents/2026-11-18-emr-spark-job-step-emrfilesystem.md), [performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md) |
| Phase 18 EMR run 4 (failed at `hadoop-prep`) | `15a-emr-size-100-20261125T173348Z-95764` | [incident record](../docs/incidents/2026-11-25-emr-hadoop-prep-intermediate-missing.md), [emr-run-1.log](../docs/agent-runs/phase-18/evidence/day2/emr/emr-run-1.log) |
| Phase 18 EMR run 5 (all six steps COMPLETED) | `15a-emr-size-100-20261125T174034Z-99560`, cluster `j-05116692OZ06APLO3FMD` | [emr-run-2.log](../docs/agent-runs/phase-18/evidence/day2/emr/emr-run-2.log) |
| Phase 18 Spark export (EMR, size S; not used downstream) | `run:30b3ef84-11dc-4c8c-b9c2-c632477d7282`; Hadoop run `run:1c9222da-8c90-4e2a-96a4-aff08ca46318`; entity-resolution run `run:08c55f9a-b026-4555-8402-4e5c1c8dd64e` | [spark-counters.json](../docs/agent-runs/phase-18/evidence/day2/emr/spark-counters.json) (`context.lineage`) |
| Vector ingest 1 (failed, HTTP 401) / ingest 2 | `run-20261118-ingest` / `run-20261118-ingest-2` | [ingest-2.log](../docs/agent-runs/phase-15/evidence/session-2/vectors/ingest-2.log) |
| Query smoke | `run-20261118-query-smoke` | decision log |
| Load test (aborted) | `rb-20261118` | [performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md) |
| Q12 runs and probes | `q12-run-1`, `q12-run-2`, `q12-probe-1`, `q12-probe-2` | [q12-raw](../experiments/results/phase16/q12-raw/) |
| 16B Session 1 evaluation | `16b-1` | [q12-raw](../experiments/results/phase16/q12-raw/) |
| P35 local rehearsal | `p35-local-1` | [performance-metrics.md](../experiments/results/phase16/performance/performance-metrics.md) |
| Plan run IDs | see section 3 | decision log |

## 7. Prompt versions

| Prompt or schema | Version | File | sha256 (computed 2026-11-22) |
|---|---|---|---|
| Planner prompt | `planner-v1`, schema `scholarchain.runtime.planner.v1` | [prompts/runtime/planner-v1.md](../prompts/runtime/planner-v1.md) | `aed20ab1fda01d58574dc8bb7876cb6ee92872ad33dfa930eb5a4653fd1c2249` |
| Synthesis prompt | `synthesis-v2`, schema `scholarchain.runtime.synthesis.v2` | [prompts/runtime/synthesis-v2.md](../prompts/runtime/synthesis-v2.md) | `0d9c6c16abd9b64ec372270595bc50c8398d519532fe47873737ed0ac5c4c337` |
| Query-plan schema | `query-plan-v1` | [prompts/schemas/query-plan-v1.json](../prompts/schemas/query-plan-v1.json) | `d35ad231ab1e742f036773e3ccbfb514e06e31eae2c8aeabfb331d438a39338b` |
| Answer-synthesis schema | `answer-synthesis-v2` | [prompts/schemas/answer-synthesis-v2.json](../prompts/schemas/answer-synthesis-v2.json) | `a95648b5bca53f8ca07ec918de513a421ec5e4df5330aff36b08d646fdc60adf` |

History: `synthesis-v1` was edited in place during Session 1, and the Phase 14 gate required a bump to `synthesis-v2` before any later paid answer ([Phase 14 human gate](../docs/agent-runs/phase-14/human-gate.md)). Which prompt version each Q12 answer used is recorded in the frozen raw ([q12-raw](../experiments/results/phase16/q12-raw/)); it was not re-read for this manifest.

## 8. Model versions

| Role | Model | Version tag and settings | Source |
|---|---|---|---|
| Answer synthesis (default) | Anthropic `claude-haiku-5-5` | no `temperature`, `top_p` or `top_k` is sent; prompts up to 100,000 tokens | [README, providers](../README.md#model-providers-the-bedrock-restriction-and-the-fallback-configuration); [scripts/config/release.conf](../scripts/config/release.conf) |
| Embeddings (default) | Voyage AI `voyage-4-lite` | version tag `voyage-4-lite`, dimension 256 | same |
| Bedrock fallback, synthesis | `anthropic.claude-haiku-4-5-20251001-v1:0` | authored and tested offline; never run live | README, `release.conf` |
| Bedrock fallback, embeddings | `amazon.titan-embed-text-v2:0` | authored and tested offline; never run live | README, `release.conf` |

The planner's own model setting is not recorded separately in this manifest. Instructor approval of the Anthropic and Voyage deviation: [Phase 14 work order](../docs/agent-runs/phase-14/prompt.md), screenshot at `docs/agent-runs/phase-14/evidence/14b/fallback/instructor-approval.png`. Agent models (workers, reviewer, orchestrator): [README version record](../README.md#version-record).

## 9. Artifact checksums

| Artifact | sha256 | Source |
|---|---|---|
| Runtime archive (expected) | `789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5`, 321876735 bytes | [scripts/config/release.conf](../scripts/config/release.conf) |
| EMR job JAR, entity resolution | `e8df4ee269f1a2f1000cd88caad2d1b19e78f78f2be09238a3372d8ce7e52768` | [emr-upload-manifest.json](../docs/agent-runs/phase-15/evidence/session-2/emr/emr-upload-manifest.json) |
| EMR Hadoop submit JAR | `3defe8e6aa3688e4bebb87f8d766115fd8e960732c91a898db9ffe7e127a61c6` | same |
| EMR Hadoop dependency bundle | `76a1b455ce22d38cc3325592a7d10bc52d2d89b208655eb7b8e6ca484154838a` | same |
| EMR Spark job JAR | `22c1928ac6f64831a4798ec9b6999ca495e5d23742d413a84910a693a8042e44` | same |
| EMR upload manifest file | `bcb5efd5cb78cc7be7a878256ad05d7419feed74a41ce9ce5ae3f60142daf610` | [Session 2 INDEX](../docs/agent-runs/phase-15/evidence/session-2/INDEX.md) |
| Phase 18 EMR upload manifest file | `3d86dbe198d8ca2d094eb2d42a625dd524fab92925c7e3e0290f69637cadb40f`; the four jar hashes above appear unchanged in it | [Day 2 INDEX](../docs/agent-runs/phase-18/evidence/day2/INDEX.md), [emr-upload-manifest.json](../docs/agent-runs/phase-18/evidence/day2/emr/emr-upload-manifest.json) |
| EMR step program `scripts/emr/sc-step.sh` (Phase 18 fix) | `1edcf68d29481015da5675aad7fbe74d4af685f9d0c27a5378f23ffeab7c8eed` (recomputed 2026-11-26 from the working tree; equals the value uploaded on 2026-11-25 and the pin in `infra/terraform/emr-step-programs.json`) | [emr-upload-manifest.json](../docs/agent-runs/phase-18/evidence/day2/emr/emr-upload-manifest.json), [test report](../docs/agent-runs/phase-18/test-report.md) |
| Render manifest (10,000 documents) | `df0d50289cf2a1acd2edc72fd64e2212bfd93c21d5104bb568604fa509059f7f` | decision log (block 24) |
| Ingest 2 approval record | `5a06ba975529b455f95beec5155e64b48a831d1fe029fba5dfdb7485f11ee7ce` | decision log (block 25) |
| Session 2 cost report | `6555edba6336ff9e43ef74f3454bec5d5e1ca738d55a9adb03736dafbb5c984d` | [Session 2 INDEX](../docs/agent-runs/phase-15/evidence/session-2/INDEX.md) |
| Session 2 decision log (redacted copy) | `4f819c61801742de628caabe8a768cbe24e156fe19a7525a4f61cd37ca03cf69` at the time of the index; later refreshed | [Session 2 INDEX](../docs/agent-runs/phase-15/evidence/session-2/INDEX.md) |
| Session 2 downloads list | `e4972a8b062b11f6685c396c86bce1a1afeda61115ee6d8ef1c673376f0c7000` | [downloads-SHA256SUMS](../docs/agent-runs/phase-15/evidence/session-2/archive/downloads-SHA256SUMS) |
| 16B Session 1 raw sha256 file | `13736cfacf3e83beafed900d01ed904a442c2a93e2db87b4752e8aba19e0d0d4` | [Phase 14 human gate](../docs/agent-runs/phase-14/human-gate.md) |
| Q12 and 16B frozen raw, `SHA256SUMS` | `1b085aa214cb8535d29031a2b143d5e587f86e472a7f41859da0e90be3fb5175` | [q12-raw/SHA256SUMS](../experiments/results/phase16/q12-raw/SHA256SUMS) |
| Q12 answer key | `6f5ef014d310136d7016447f7eefa39912e49c467a5f3bf2ec58ee1dc937a9b3` | [answer-key.json](../experiments/inputs/q12/answer-key.json) |
| Q12 questions | `afc09952096c49ebacd61a051542295570ec9bcd39ffb72cb7a3d4fc014e4734` | [questions.txt](../experiments/inputs/q12/questions.txt) |
| Evaluation manifest | `9af12cecedc19e9cd62285d88d1ef55681793421690181e419bb3f9b129b3a72` (computed 2026-11-26 at `b11afe9`; the file changed in `b11afe9` and in the Phase 18 commits before it; the 2026-11-22 value was `20b9738fcc5e...6a89b`) | [16-evaluation.json](../experiments/manifests/16-evaluation.json) |
| Terraform provider lock file | `421b75245b0080edee2b434482ff348419a75d7a6b798d5218e0a0f9f723eaea` (computed 2026-11-22) | `infra/terraform/.terraform.lock.hcl` |
| Version ledger | `f268658bd45ea6f73a5dbe394f997aebd9bb2b5061eb30457a85da600e4520dc` (computed 2026-11-22) | [project/Versions.scala](../project/Versions.scala) |
| Demo clips (Session 2) | per-clip sha256 values | [clips.txt](../docs/agent-runs/phase-15/evidence/session-2/recordings/clips.txt) |

Hashes marked "computed 2026-11-22" were taken from the working tree at `main` `55fb1b3`; those named in the Phase 18 update note at the top were rechecked on 2026-11-26 (one changed, see above). All must be re-computed at the release commit. Build artifacts of the release commit (JARs, images, service distribution): **not recorded**; a `package.sh` run writes `target/release/<commit>/release-manifest.json`, which is git-ignored (`package.sh` was not replayed in 17A or 17G: the Docker daemon was not running in 17G; `sbt -batch packageRelease` succeeded in the 17G replay). The Phase 13 record shows the shape of that file for a dirty tree at an older commit ([release-manifest-real.json](../docs/agent-runs/phase-13/evidence/13a/infra/release-manifest-real.json)); it is not the release manifest of this submission.

## 10. Deployed revisions, smoke tests and rollback evidence

| Item | Evidence |
|---|---|
| Deployed revision (Session 2, destroyed) | commit `bd0b818`, four services at 1/1 and the target healthy ([b6-checklist.log](../docs/agent-runs/phase-15/evidence/session-2/rb-runtime/b6-checklist.log)); ECS task-definition ARNs are in git-ignored deploy manifests and are not recorded here |
| Smoke tests (live) | `healthz` 200 and `readyz` 200, 2 of 6 checks by design; missing and invalid key 401; unknown evidence 404 ([smoke-14b.log](../docs/agent-runs/phase-15/evidence/session-2/rb-runtime/smoke-14b.log), [manual-401.log](../docs/agent-runs/phase-15/evidence/session-2/rb-runtime/manual-401.log), [p14-7-evidence-404.log](../docs/agent-runs/phase-15/evidence/session-2/rb-runtime/p14-7-evidence-404.log)) |
| Smoke tests (local, offline) | `bash scripts/smoke-local.sh --build`, recorded `RESULT: PASS` ([Phase 15 test report](../docs/agent-runs/phase-15/test-report.md), line 71); not replayed in 17A; replayed in 17G on a fresh clone: `RESULT: PASS local offline-synthetic query-api passed all smoke checks (the six plus the semantic route and its cache counter) on 127.0.0.1:<port>` |
| Failure and recovery | stop-task of the query-api task, recovered in 113 s and 68 s ([p11-failure.log](../docs/agent-runs/phase-15/evidence/session-2/b35-failure/p11-failure.log)) |
| Rollback | not exercised live. `scripts/rollback.sh` is covered by dry-run records in Phase 13 ([dryrun-rollback.txt](../docs/agent-runs/phase-13/evidence/13a/infra/dryrun-rollback.txt)); Session 2 used cleanup, not rollback |
| Cleanup and inventories (Phase 18, 2026-11-25) | pass 1: [before](../docs/agent-runs/phase-18/evidence/day2/cleanup/pass-1-before-inventory.txt) and [after](../docs/agent-runs/phase-18/evidence/day2/cleanup/pass-1-after-inventory.txt) (331 to 87 entries per the test report); pass 2: [before](../docs/agent-runs/phase-18/evidence/day2/cleanup/pass-2-before-inventory.txt) and [after](../docs/agent-runs/phase-18/evidence/day2/cleanup/pass-2-after-inventory.txt) (48 to 46); deployer removal in [p39/](../docs/agent-runs/phase-18/evidence/day2/p39/) |
| Cleanup and inventories (Session 2) | [before](../docs/agent-runs/phase-15/evidence/session-2/inventories/before-cleanup-inventory.txt) (297 entries), [after pass 1](../docs/agent-runs/phase-15/evidence/session-2/inventories/after-pass-1-inventory.txt) (65), [after cleanup](../docs/agent-runs/phase-15/evidence/session-2/inventories/after-cleanup-inventory.txt) (63) |

## 11. Costs recorded against this release

AWS USD 17.88, Anthropic USD 0.08 (earlier phases), Voyage AI USD 0.00, combined USD 17.96 of the USD 25.00 ceiling as of 2026-11-20T15:48:56Z ([cost-report.log](../docs/agent-runs/phase-15/evidence/session-2/c11/cost-report.log)). The Q12 Anthropic key's own Console figure (USD 0.08, 2026-11-20 and 2026-11-21 UTC) is a separate scope and is not in the combined figure ([docs/report/evaluation.md](../docs/report/evaluation.md)).

Phase 18 (2026-11-25), recorded separately and not added to the figures above: the EMR ledger after termination reads 5 of 5 live runs and USD 2.65 of its USD 4.70 cap, as ledger estimates at 0.555 USD per hour, not billed amounts ([emr-actual-2end.log](../docs/agent-runs/phase-18/evidence/day2/emr/emr-actual-2end.log)); the AWS Budgets console, read as root at about 9:12 PM CST on 2026-11-25, showed USD 19.26 of USD 25.00, not final because Cost Explorer lags ([decision-log.md](../docs/agent-runs/phase-18/evidence/day2/00-timeline/decision-log.md), line 90; [human gate](../docs/agent-runs/phase-18/human-gate.md), Day 2). The final Phase 18 AWS cost is not recorded.

## 12. Items not recorded or not yet done

- Final commit SHA and tag (set at the release commit; the earlier tag `v1.0-final` marks `ad86b07`).
- The `push-record.json` file with the registry digests (the digest values are cited above from the dry-run log lines).
- A Terraform plan for the release commit (human-gated; the deployment is destroyed).
- Build artifact hashes of the release commit (`package.sh` output is git-ignored).
- The full-check result of `20261122T055838Z-17867` inside the repository (to be recorded in `docs/agent-runs/phase-17/test-report.md`).
- Bounded pipeline rerun and cleanup rehearsal: not part of the 17G replay (the P6 local chain was not run; cleanup was not run). The clean-checkout `sbt -batch clean check` and the README command replay are recorded above and in `docs/agent-runs/phase-17/17g-replay.md`.
- Prompt version per answer, from the frozen Q12 raw (not read here).
- The code-reviewer's final verdict and the test-engineer's final run for Phase 17 (separate gates).
- Phase 18 (added 2026-11-26): the cause of the 2026-11-25 `hadoop-prep` failure (incident open); a repeat of the EMR run (the ledger is at 5 of 5); the final Phase 18 AWS cost; recomputation of every hash pin at the release commit; the Day 3 full-check results are in the [Phase 18 test report](../docs/agent-runs/phase-18/test-report.md), section "Day 3": run `20261126T170301Z-26256` passed six gates and failed the terraform gate (formatting of two ignored local variable files), and the terraform rerun `20261126T190048Z-32280` passed after a whitespace-only format; no single run passed all seven gates after the change.
