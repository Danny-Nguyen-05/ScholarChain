# Phase 14 live session 1: evidence index

Session 1 ran from H0 2026-11-13T17:44:01Z (`00-timeline/session-clock.log`) to the end of the Section C cleanup on 2026-11-15 UTC. The last timestamped cleanup action is the C5b key revocation at 2026-11-15T02:19Z; the C7 and C8 console checks came after it and carry no timestamp. The running decision log (`00-timeline/decision-log.md`) is the timeline of record from B8.3 onward. It runs through the C11 entries and the Session 2 decisions of 2026-11-15; it is recopied byte-identical from its git-ignored source, which was last read for this index at sha256 `bc7254e8…2c5b`.

Assembled offline on 2026-11-15 by the orchestrator and updated in repair round 1 the same day (C11 report, approval-check excerpt, decision-log recopy, INVENTORIES.md). No AWS, Anthropic or Voyage call was made to build it. Sources are local, git-ignored files under `target/` and `~/Documents/scholarchain-session-downloads/`.

**Redaction.** Every copied file was passed through one filter. It strips ANSI codes and trailing spaces, replaces the AWS account ID (and its abbreviated `NNN...NNNN` form) with `<acct>` and the custom domain with `<domain>`, and replaces the repository path with `<repo>`, the home directory with `<home>` and any email address with `<email>`. Files where the filter changed nothing are marked "unchanged; equals source", and their sha256 equals the source file's sha256. Excerpt files ("generated") keep only the matching lines of each source and write each source's path, line count and sha256 above its lines. The smoke-test logs already carried `https://<redacted>` for the API host; the cleanup inventories were already masked by `scripts/cleanup.sh`.

**Lean selection.** RESULT and summary lines are used instead of full logs where a log is large or noisy. The Excluded section below lists what was left out and why.

## Timeline of record

| File | Source | sha256 of file here | Proves |
|---|---|---|---|
| `00-timeline/decision-log.md` | target/phase14/evidence/14b/b8-3-graph-only-decision.md | `bc7254e83c4382c9f61f2d8d419b5d169e8501653fe10fa01922c452bf722c5b` (unchanged; equals source) | Running decision and evidence log (timeline of record) from B8.3 through the C8 console checks and the C11 entries of 2026-11-15 (costs, budget, final ECS/EMR console checks, Session 2 budget position); human decisions with UTC times |
| `00-timeline/session-clock.log` | target/phase14/evidence/14b/session-clock.log | `2591e639bb8dbee037d2b667d0e6f1131946ce8cae6615832b4d5460c1055a8e` (unchanged; equals source) | Session clock readings; H0 = 2026-11-13T17:44:01Z (second line) |
| `00-timeline/b0-start.log` | target/phase14/evidence/14b/b0-start.log | `52836cfbd0e962c04b05412a36d8803cd47f38267128367c5264964f31f03a81` (unchanged; equals source) | B0 start state: cost read USD 0.38 AWS, Anthropic 0, Voyage 0, clean tree at 684aeaf, LLM ledger 0 |

## 14B apply, deploy and smoke

| File | Source | sha256 of file here | Proves |
|---|---|---|---|
| `14b-deploy/b3b-decision.md` | target/phase14/evidence/14b/b3b-decision.md | `0a8919948119fc92fcd975389233f0edfd1237d6e496b86cf96d36890b2856a2` (unchanged; equals source) | B3b provider-key method decision ("terminal", 2026-11-13T18:49:17Z) and IAM window close |
| `14b-deploy/deployer-e1-decision.md` | target/phase14/evidence/14b/deployer-e1-decision.md | `5e0fc848e72952fd07eb6fb39647233e47baa6cdddcde7783a1e3f75760a39e3` (unchanged; equals source) | E1 deployer repair (24bf49d) apply decision 2026-11-13T18:27:25Z; 0/3/0 |
| `14b-deploy/deployer-e1r2-decision.md` | target/phase14/evidence/14b/deployer-e1r2-decision.md | `9f8ae339708ba5dd501203adef2a0581170bd94deba87a3e65158391b6ee9ef6` (unchanged; equals source) | E1 repair 2 (155562d) apply decision 2026-11-13T19:45:16Z; 0/1/0; push 155562d PASS |
| `14b-deploy/14b-apply-push-results.txt` | excerpt of 21 file(s): base-plan.log, base-apply.log, deployer-e1-apply.log, base-plan-2.log, base-apply-2.log, push.log, push-2.log, runtime-plan.log, runtime-apply.log, deployer-e1r2-apply.log, push-155562d.log, runtime-plan-2.log, runtime-plan-3.log, push-bc81afd.log, runtime-apply-3.log, push-9ee5bbe.log, runtime-plan-4.log, runtime-apply-4.log, acm-issued.log, state-sha-after-base-apply.log, state-sha-after-runtime-apply.log (each source path, line count and sha256 is written in the file) | `144f70f1f68f654eb05e22df5c78055eabea01352166364046b91fb9365ddd97` (generated) | 14B stage results: base apply 1 FAIL (Cloud Map / SFN permissions) then PASS at 24bf49d; push PASS; runtime apply 1 FAIL then PASS at bc81afd and 9ee5bbe; ACM ISSUED |
| `14b-deploy/smoke-14b.log` | target/phase14/evidence/14b/smoke-14b.log | `717e16379412a16c97822cfb9045ca5a6677cca7116a46ef1c172ad396396684` (redacted copy; source `10e6d3f44727fed060aaad92ce81d331c743c471a3500cb93250760c0c580c33`) | 14B smoke: healthz 200 and readyz 200 (2 of 6 checks, by design before data load) |
| `14b-deploy/manual-401.log` | target/phase14/evidence/14b/manual-401.log | `a07653b7bf25c05ab687bf064480c00e6bcd12c197a0e134f621be5313288a07` (unchanged; equals source) | 14B manual check: missing/invalid key returns 401 UNAUTHORIZED, retryable false |
| `14b-deploy/b6-checklist.log` | target/phase14/evidence/14b/b6-checklist.log | `88d5c9f3006a8ce044b0559e193d5a263b4051b53ddcf67c6a8772185ab58c5a` (unchanged; equals source) | GO/NO-GO 3: 4 services 1/1, target healthy; digest comparison not run (limitation) |
| `14b-deploy/tunnel-test.log` | target/phase14/evidence/14b/tunnel-test.log | `d10f7ac8441043eff6465ca6c942f2353d9d56167ef56f0013696aa494a18718` (unchanged; equals source) | Neptune tunnel checks: 403 without auth, cluster healthy writer 1.4.8.1.R1, empty loader list |
| `14b-deploy/b5-dns.log` | target/phase14/evidence/14b/b5-dns.log | `63b12324286ab3a926a44e8febab61d3d5bff430cce16e5c00c60658f99e5793` (unchanged; equals source) | B5: TLS certificate for the API verified |

## 14C load and smoke (B8.1-B8.7)

| File | Source | sha256 of file here | Proves |
|---|---|---|---|
| `14c-load/14c-results.txt` | excerpt of 15 file(s): upload-slice-dry.log, upload-slice.log, storageload-dry.log, storageload.log, storageload-graph-only-1.log, storageload-graph-only-2.log, pointer-plan.log, pointer-apply.log, awsintegration.log, awsintegration-2.log, awsintegration-3.log, awsintegration-4.log, ingest.log, ingest-2.log, query-smoke.log (each source path, line count and sha256 is written in the file) | `73391d816e5abd0384683cb9b3debc7bfa3878d91755b16199ba5399044f7d57` (generated) | B8.1-B8.7: upload 143 files PASS; storage load FAIL (tunnel), graph-only attempt 1 FAIL, attempt 2 LOAD_COMPLETED; pointer apply PASS; AWS integration 3 FAIL then 1/1 PASS; ingest 1 rejected items, ingest 2 PASS; query smoke PASS |
| `14c-load/pointer-plan-deltas.log` | target/phase14/evidence/14c/pointer-plan-deltas.log | `42d6adc63ac2d28fb0b181b5a871dddb671e585a1822f4a53cb66697126fd602` (unchanged; equals source) | B8.4 pointer plan IDENTICAL to the reviewed derivation (2 actions, query-api only) |
| `14c-load/pointer-smoke.log` | target/phase14/evidence/14c/pointer-smoke.log | `98b4d3b580d33d14f68e87dd582bffaf9bed83d3db4a9bbc4db85fbc8efe1ad6` (redacted copy; source `5d30e9805655307de3947691d0069e858d16b3509e0ff90e6525656af57b892e`) | B8.4 smoke after the pointer apply: healthz/readyz 200 |
| `14c-load/ingest-2.log` | target/phase14/evidence/14c/ingest-2.log | `2f7a05e07185495387ee65804ae633c63af524ae7197b36982561e1f66a7021d` (redacted copy; source `f91478f4d14e33c60dd50c658186ccce7b68ba6692ab83831a7a1b09e54f9d82`) | B8.6 ingest 2 report: written 95, unchanged 9, rejected 0, embeddingCalls 95 |
| `14c-load/query-smoke.log` | target/phase14/evidence/14c/query-smoke.log | `957b98aa64fa7273a22ccf8f23b0f36afdd2a78799353d8726500c48f838814e` (redacted copy; source `d7cd772e5762a780e0609a8476a8dbdde8753f338b0cb20d12baa31f6dde1229`) | B8.7 query smoke report: 5/5 samples, allNeighborsMatched true, verifiedPointers 7 |

## B8.8 real-model smoke

| File | Source | sha256 of file here | Proves |
|---|---|---|---|
| `b8-8-smoke/smoke-real.log` | target/phase14/evidence/14c/smoke-real.log | `6d5fd2e82acb0f30be29a4e768cbd9cb57afe9adbf5d7433f34ec40226184683` (redacted copy; source `e3b5607eea6f15df82aef3ea7d4f99b2150b8759ae61ad67c6bc109ec9650c07`) | B8.8 attempt 1: query timed out at the 10 s client timeout |
| `b8-8-smoke/query-evidence.json` | target/phase14/evidence/14c/query-evidence.json | `ea63b3dfa006a88f24438f5a61aba9b2c12a3d951a66aa99758508acc9795833` (unchanged; equals source) | B8.8 manual query qry-ecbe91cc...: no evidence ids (abstained) |
| `b8-8-smoke/repair6-smoke.log` | target/phase14/evidence/14c/repair6-smoke.log | `0b0c28b5045619b7aaca17156d8385cdbda611cd003d828bd14db1c3b3f3d4ba` (redacted copy; source `466fbbe1b989b43026d1a3e424d46867523ea7bef49ec176a5f632a9de71d06b`) | After repair 6 (bfa393a) runtime apply: healthz/readyz 200 |
| `b8-8-smoke/smoke-real-9.log` | target/phase14/evidence/14c/smoke-real-9.log | `19f71f0f060655aa1cb536e0168bf6e9ccaefa6238feb1328ff4af64016fc2b1` (redacted copy; source `e5b0c165ccfe8a85fac8232012351a61ff86713520f2fd79f6c33c5d36b22fbc`) | After repair 7 (0656dc4): query 504 (synthesis stage deadline) |
| `b8-8-smoke/query-explain-r8a.json` | target/phase14/evidence/14c/query-explain-r8a.json | `ead77c88e7e99d0d35ab1f5603288692ac0d33a9df2714408826057639f35671` (unchanged; equals source) | r8a after repair 8 (ae14593): explain record, synthesis-v1, claude-haiku-5-5 |
| `b8-8-smoke/query-response-r8a.json` | target/phase14/evidence/14c/query-response-r8a.json | `1523166cc340fb62f3b209a79c500b7bf0d13a36778d306c99f5a0d7a3c276c2` (unchanged; equals source) | r8a response: ANSWERED with verified claims |
| `b8-8-smoke/smoke-real-10.log` | target/phase14/evidence/14c/smoke-real-10.log | `a49665bd1001a765ae21702835cc6490df5e7bf4554b9a084f3359de56e7098e` (redacted copy; source `b9632c6bfd6cb91fe7fe3b86f43945aa88c9cebc20742aa7baf41df196ab41e7`) | smoke-real-10: query 504 (first query after idle; graph cold) |
| `b8-8-smoke/smoke-real-11.log` | target/phase14/evidence/14c/smoke-real-11.log | `c53c82b66e302859ffcd0048113ff065394a2a771ee30202b2bfb2b42c71b631` (redacted copy; source `93e0405bdf0d8996cfbe0ba110e4e13066406dc4d5fac9a7cf2c252b260e42bb`) | B8.8 PASS: all 6 checks, claims=3 evidence_ids=3 |
| `b8-8-smoke/llm-reserve.log` | target/phase14/evidence/14c/llm-reserve.log | `3f145964b929cdd1d246e4d4ea5a63db9946187dcf5004390182b68646dd2ade` (unchanged; equals source) | LLM ledger reservations for bucket 14c (10/10) and the first bucket-17 answer |

## Live repairs 6-11

| File | Source | sha256 of file here | Proves |
|---|---|---|---|
| `live-repairs/commits-6-11.txt` | git show --stat of bfa393a 0656dc4 ae14593 2b2d263 7ecc572 b6dc94d | `e8cf87170d169cf7af06d92af51ab98908bcf79daa0c9159b5c7c8569e836bde` (generated) | The six live-repair commits exist with their dates, subjects and changed files (tests included in each) |
| `live-repairs/repair-rollout-results.txt` | excerpt of 9 file(s): push-bfa393a.log, runtime-plan-5.log, runtime-apply-5.log, push-0656dc4.log, runtime-plan-6.log, runtime-apply-6.log, push-ae14593.log, deployer-e9-plan.log, deployer-e9-apply.log (each source path, line count and sha256 is written in the file) | `3d93e2597efcff8906a90752bef389318cbe4f772f11200fc6898ada80061542` (generated) | Repairs 6-8 pushed and applied (RESULT PASS); repair 9 deployer plan 0/1/0 and apply 0/1/0; repair 8 images reached the services through the EMR apply (see b9-emr) |

## B9 EMR (PARTIAL)

| File | Source | sha256 of file here | Proves |
|---|---|---|---|
| `b9-emr/b9-results.txt` | excerpt of 17 file(s): emr-upload.log, emr-plan.log, emr-apply.log, emr-plan-2.log, emr-apply-2.log, emr-plan-3.log, emr-apply-3.log, emr-plan-4.log, emr-apply-4.log, emr-plan-5.log, emr-apply-5.log, emr-run-1.log, emr-run-2.log, emr-run-3.log, emr-run-4.log, cluster-id.log, cluster-final-state.log (each source path, line count and sha256 is written in the file) | `96021326255767ffc3f32ed49e9d7e055f292c829de2241ad9073891da4f66b0` (generated) | B9 PARTIAL: upload 24 files PASS; apply serial 16 FAIL (BOOTSTRAP_FAILURE, EFS race) then PASS; runs 1-2 FAIL cluster-check (repairs 9, 10); run 3 FAIL add-steps shape (repair 11); run 4 stage-in COMPLETED, hadoop-prep FAILED |
| `b9-emr/emr-plan-deltas.log` | target/phase14/evidence/15/emr-plan-deltas.log | `95a9684feebfdbba897e48089749bf43daa5ddacab55ec1e059c77031af4ab8b` (unchanged; equals source) | Combined EMR plan vs reviewed derivation: 13 MATCH, 9 UNEXPECTED (module.runtime image rollout, accepted) |
| `b9-emr/emr-run-4.log` | target/phase14/evidence/15/emr-run-4.log | `755b77e03d4f962abf8d5de02069ce28503edac06e13a25596eec4ea91be20c2` (redacted copy; source `7136d4dc3f8ba59782b8f8f3affd68ef8ce7f430b837b703560a1c11f37832fc`) | Full run 4 log: cluster-check ok, ledger live_runs=2 of 3, stage-in COMPLETED, hadoop-prep FAILED |

## B11 16B evaluation

| File | Source | sha256 of file here | Proves |
|---|---|---|---|
| `b11-16b/eval-plan.log` | target/phase14/evidence/16b/eval-plan.log | `9ce48ab7880277d7b05bd349458c435e5a0ad0f2f29f7a66e40eaab7cb44b11c` (redacted copy; source `dad977c5cb7bda01b4610fbe8512d5b17560f6eb36408330cd22280af2832acb`) | 16B plan: 40 questions (sha256 e4b6d48b...), PLAN-OK, nothing sent |
| `b11-16b/eval-16b-1.log` | target/phase14/evidence/16b/eval-16b-1.log | `260fc76c355c26f23bd2f6870f6d607da8f06ae2295791ecd7e0eb309fd7b698` (redacted copy; source `d596eab1625b04b27936dd5177c86fc032f7d090a187da2d54414f764d405dbc`) | 16B run 16b-1: COMPLETED asked=40 charged=40; COST-REPORT anthropic 0.054600 (estimate) |
| `b11-16b/llm-status-after-16b.log` | target/phase14/evidence/16b/llm-status-after-16b.log | `69d95861c47badf69529c5dc47e44c157d595486b20697e4110f4dd029cd53e4` (unchanged; equals source) | LLM ledger after 16B: bucket 16b 40/40, total 51 answers |
| `b11-16b/raw.sha256` | target/experiment-runs/16b-live-evaluation-16b-1/raw/raw.sha256 | `13736cfacf3e83beafed900d01ed904a442c2a93e2db87b4752e8aba19e0d0d4` (unchanged; equals source) | sha256 of the three raw 16B files; this file's own sha256 is 13736cfa... as recorded |
| `b11-16b/run-record.json` | target/experiment-runs/16b-live-evaluation-16b-1/raw/run-record.json | `636777fb34f7669d3b0e643bbbe3b23c0daff185f591036536c0db7c68ba5ba1` (redacted copy; source `7954aaf8ea8db81df5db007a96eb02f4b1fd6ba744daddf85e417616761d8a0d`) | 16B run record: outcomes ok 39 / client_error 1, commit b6dc94d, tree clean, host withheld |
| `b11-16b/outcomes-by-type.txt` | computed from target/experiment-runs/16b-live-evaluation-16b-1/raw/answers.jsonl | `138df30e44d0c15cf0e03294f737cd9fcb84006fcb6a767b8d5b99e6ba7367f5` (generated) | Outcome counts: component 7/8, ranking 7/8 (1 HTTP 422), direct-coauthors 0/14, path 0/10 |

## B12 final smoke and demo

| File | Source | sha256 of file here | Proves |
|---|---|---|---|
| `b12-final/final-smoke.log` | target/phase14/evidence/17/final-smoke.log | `a8af43ab51954e5e7276ca12e11f9bd9e1001a86b0f3f0bedce9780d74a677ef` (redacted copy; source `23a7e6e7386d9f33ae49d3749a33893ff50e28741ad4a496d19ded8038b353a8`) | B12.3 final smoke PASS all 6 checks, 2026-11-14T21:22:50Z |
| `b12-final/llm-reserve-17.log` | target/phase14/evidence/17/llm-reserve.log | `620148e174ef349262f8e6d2bb0fcd7a8e1ffc1efc536db30757b67112d0f879` (unchanged; equals source) | Bucket 17 reservation: 4 answers; total 55 |
| `b12-final/llm-status-final.log` | target/phase14/evidence/17/llm-status-final.log | `08ba9dea6f11972c15c306db07001775ecb86489f945afeb066ecf793cb68f4d` (unchanged; equals source) | Final LLM ledger: 55 answers, USD 0.075075 estimated of the 1.33 cap |
| `b12-final/demo-video.sha256.txt` | target/phase14/evidence/17/demo-video.log | `a4fc78c3a7f70f5470399b6c27816fe34a13e166e8d7e7ab6ef67d18901fb798` (redacted copy; source `7a27d907a573a6e1a665d3413d6f5e660833af3cc2e45a528c3ad2cd2aec74d2`) | B12.2 demo video sha256 55884100... (video kept outside the repository) |

## B13 downloads before cleanup

| File | Source | sha256 of file here | Proves |
|---|---|---|---|
| `b13-downloads/SHA256SUMS` | ~/Documents/scholarchain-session-downloads/SHA256SUMS | `dd3b2ecdf8ca89cc2de1f6e80871069eb86156aebc11454377510831a482dbf9` (unchanged; equals source) | B13.2 checksums of the 16 files downloaded before cleanup (ledgers, 15A experiment records, 16B raw files) |
| `b13-downloads/verify-2026-11-15.txt` | shasum -a 256 -c SHA256SUMS run offline | `949a0aa7b6f2c675c985ad6a6eb9f85bc49f5b10fd587d83aef8da1912fa111b` (generated) | All 16 downloaded files still match SHA256SUMS; the demo copy matches the recorded video sha256 |
| `b13-downloads/state-sha-before-cleanup.log` | target/phase14/evidence/14b/state-sha-before-cleanup.log | `3fd6ddef299e6bf204e09f7d4977ccefc42ec716c06cdf1b66224ec19bc45c45` (unchanged; equals source) | B13.1 main Terraform state sha256 before cleanup (hash only; state not copied) |

## Section C cleanup

| File | Source | sha256 of file here | Proves |
|---|---|---|---|
| `section-c/cleanup-results.txt` | excerpt of 12 file(s): cleanup-prepare-plan.log, cleanup-prepare-dry.log, cleanup-prepare.log, cleanup-list-1.log, state-sha-before-guard-rm.log, guard-state-rm.log, cleanup-list-1b.log, cleanup-pass-1.log, cleanup-list-2.log, cleanup-pass-2.log, deployer-cleanup-plan.log, deployer-cleanup-apply.log (each source path, line count and sha256 is written in the file) | `9f167ca4ad6575ae42dd2265e680f5b59c2e59c60a66724f6b361ea5e9253031` (generated) | C2 prepare PASS; C3 listing 1 REFUSED (guard), guard state rm, listing 1b 213 actions, pass 1 PARTIAL 309->62 (EIP 403, carried item 24), pass 2 PASS 62->60; C4 deployer 13 destroyed |
| `section-c/destroy-actions-pass-1.txt` | target/cleanup-evidence/20261115T014213Z-74524/destroy-actions.txt | `404ae96596603fe076fb4f9e05897b35e63bb5e7d57a7d8a1199a41f0ec9357a` (unchanged; equals source) | The 213 Terraform destroy actions confirmed for pass 1 (run 20261115T014213Z-74524) |
| `section-c/destroy-actions-pass-2.txt` | target/cleanup-evidence/20261115T020725Z-78532/destroy-actions.txt | `e332c521fb2f3449488401942def40dd324af8964b13b19ef4ed94c792a04c31` (unchanged; equals source) | Pass 2 destroy action: delete module.network.aws_eip.nat |
| `section-c/deployer-cleanup-apply.log` | target/phase14/evidence/14b/deployer-cleanup-apply.log | `d3a7acaa7012bb9254aea7f98186a91de7eeb595ce8305a5b135dc85a64dcaba` (redacted copy; source `73e95f4a84d6077640d45f2f04eb12cc55be660a40bf422aef896dc94f8bda38`) | C4 deployer apply: 13 destroyed (4 operator roles, 9 inline policies); deployer role kept |
| `section-c/c5-secrets-delete.log` | target/phase14/evidence/14b/c5-secrets-delete.log | `57a5c07df7b8aa560bf19d0db880c626c07f995731229c882911845ce3a910a8` (unchanged; equals source) | C5: names of the 4 Secrets Manager secrets force-deleted (names only, no values) |
| `section-c/c5b-key-revocation.log` | target/phase14/evidence/14b/c5b-key-revocation.log | `fd52aa3ebf98141ccb1abd138652904248d92c0b8a211c3773c5b9704cd5a15d` (unchanged; equals source) | C5b: Anthropic and Voyage keys revoked 2026-11-15T02:19Z (user statement) |
| `section-c/llm-status-cleanup.log` | target/phase14/evidence/17/llm-status-cleanup.log | `08ba9dea6f11972c15c306db07001775ecb86489f945afeb066ecf793cb68f4d` (unchanged; equals source) | C9 LLM ledger at cleanup: 55 answers, USD 0.075075 estimated |
| `section-c/c11-cost-report.md` | coordinator-written from the user's console screenshots (Cost Explorer, Bills, Taxes, Budgets, Voyage dashboard, ECS and EMR consoles); screenshots kept by the user | `f42e2691d1f161ec4e35a42c12081e7af390ec452f44c89635649c7178c3caf3` (generated) | C11 (provisional, 2026-11-15): AWS USD 15.75 before credits, tax 0.00, Anthropic about 0.08 (ledger estimate), Voyage 0.00, combined 15.83 of the USD 25 cap; AWS by service and day; budget finding (live USD 200, alerts 50/80/100%; billing-bootstrap USD 25 never applied); ECS Clusters (0), EMR on EC2 Clusters (0) |

## Approval records

| File | Source | sha256 of file here | Proves |
|---|---|---|---|
| `approvals-digest.txt` | excerpt of 1 file(s): *.md (25 records) (each source path, line count and sha256 is written in the file) | `2d2102ba1933964121b907098c42813f1b28b01bc7312179b5ca3ed21a296220` (generated) | Every live stage ran under a recorded approval bound to a commit and (where applicable) a plan sha256 |
| `approval-checks-unarchived-serials.txt` | excerpt of 2 file(s): runtime-apply-3.log, emr-apply.log (each source path, line count and sha256 is written in the file) | `6e39c7985f0ebd62a4506793eb172c932d4eee024c4f8a004d7e3ca48eebface` (generated) | For the two applies whose approval records are not archived (serial 7 at bc81afd, serial 16 combined EMR): the deploy script parsed an approval record, matched the plan sha256 and the account sha256, and checked plan provenance and the pre-spend receipt |

## Resource inventories

| File | Source | sha256 of file here | Proves |
|---|---|---|---|
| `inventories/before-cleanup-inventory.txt` | target/cleanup-evidence/20261115T014213Z-74524/before-inventory.txt | `e8ab1f36b9fa74d4a84d49a1776f43de54f50dac64e7931b38a70669dd844e08` (unchanged; equals source) | True before-cleanup inventory (destroy pass 1): 309 entries |
| `inventories/after-cleanup-inventory.txt` | target/cleanup-evidence/20261115T020725Z-78532/after-inventory.txt | `52c3df033b9b44e764ed1d259836a0dcce457f7c4450b8e4947d1b27180f2657` (unchanged; equals source) | Final after-cleanup inventory (destroy pass 2): 60 entries |
| `inventories/INVENTORIES.md` | written by the orchestrator from the two inventories, the destroy actions and the decision log | `d4ff4aaecf96e78083690954c1782f71251e75c7efeaccab350cfb0c1fc6e77b` (authored) | Source runs, counts 309 -> 62 -> 60, by-type summary, why the 60 are tagging-index leftovers, which console checks back it, what was not checked, masking check |
## Excluded on purpose

| Source | Why left out |
|---|---|
| `target/phase14/evidence/14c/awsintegration*.log` (0.5-1.5 MB each) | DEBUG wire logs include SigV4 headers and temporary `X-Amz-Security-Token` values; only ScalaTest summary lines are kept in `14c-load/14c-results.txt` |
| `target/phase14/evidence/14c/upload-slice.log` (277 KB), `upload-manifest.json` (67 KB), `15/emr-upload.log`, `15/emr-upload-manifest.json` | Per-object lines with bucket names; RESULT lines kept |
| `target/phase14/evidence/14c/storageload*.log` | Hadoop shutdown-hook stack traces after the result; COMPLETE/FAILED and total-time lines kept |
| `target/phase14/evidence/14b/deployer-cleanup-plan.log` (140 KB), `cleanup-list-1*.log`, `cleanup-pass-*.log` | Full plan and destroy listings; the `Plan:`/RESULT lines and `destroy-actions-pass-*.txt` carry the result. CONFIRM-TOKEN lines and lines that repeat `--confirm <token>` were dropped |
| `target/phase14/evidence/14b/*sbt-check*.log`, `post-approval/`, `replan/` (1.7 MB each) | Pre-session gates already recorded in `test-report.md`; not session evidence |
| `target/phase14/evidence/14b/push-*.log`, `push-dry-*.log`, `b4-repackage*.log`, `runtime-apply-*-dry.log`, `emr-apply-*-dry.log`, `emr-dry-25.log` | Full stage logs; RESULT lines kept in the excerpt files |
| `target/phase14/evidence/14b/a9-caa.log` | Names the custom domain; nothing else needed from it |
| `target/phase14/evidence/14b/tunnel-session.log`, `tunnel-runtask.log` | Session and task IDs only; the decision log records the tunnel facts |
| `target/phase14/evidence/14c/query-explain-*.json`, `query-response-*.json` other than r8a | Intermediate diagnosis records; r8a (the first ANSWERED record) is kept |
| `target/experiment-runs/16b-live-evaluation-16b-1/raw/answers.jsonl` (197 KB) | Large; its sha256 is in `b11-16b/raw.sha256` and `b13-downloads/SHA256SUMS`, and `b11-16b/outcomes-by-type.txt` summarizes it |
| `~/Documents/scholarchain-session-downloads/ledgers/*`, `experiment-runs/15a-*` | Kept outside the repository; sha256 in `b13-downloads/SHA256SUMS` and re-verified in `b13-downloads/verify-2026-11-15.txt` |
| Demo video (`scholarchain-demo.mov`, 5.8 MB) | Shows the account ID in two ARN lines (user decision: keep it as is, outside the repository); only its sha256 is tracked |
| `target/phase14/private/**`, `*.local.tfvars`, Terraform state files | Never read (hard rule); only the state sha256 lines the session wrote are copied |

## Gaps (no surviving log)

- **C7 and C8 console checks**: `target/phase14/evidence/14b/c7-kms.log` and `c8-inventory.log` are empty (0 bytes). The results (KMS key Pending deletion; S3 0 buckets; no Elastic IPs; no load balancers; NAT gateway Deleted; no VPC endpoints; Neptune 0 clusters) survive only as lines in the decision log, with no timestamp.
- **C10 logout**: still unrecorded. No log or decision-log line records the C10 sign-out step. It is unverified.
- **C11 billing check**: done on 2026-11-15 but **provisional**: the November bill is Pending and Nov 15 may still fill in. The figures come from the user's console screenshots, which stay with the user (they show the account ID and e-mail); the tracked record is `section-c/c11-cost-report.md` plus the C11 decision-log entries. The Anthropic figure is the ledger estimate, because the console total is not separable.
- **C6 DNS records**: recorded only as the user's "deleted" in the decision log (C5b/C6 entry).
- **Repair 6-11 test runs**: the `sbt check` and unittest counts for repairs 6-11 survive only as decision-log lines. No raw sbt or unittest log was kept for these runs. The commits themselves are in `live-repairs/commits-6-11.txt`. A later `sbt check` on HEAD `b6dc94d` is recorded in `test-report.md` ("Session 1 closeout").
- **Agent identities**: native agent IDs were not recorded. Roles and models per commit are in `owner-report.md`, "Agent roster"; roles for E1 through repair 4 are not recorded.
- **B8.8 diagnosis**: the Logs Insights results (runtime-artifact fetch pairs at 04:42:39Z and 04:46:16Z; warm-up `elapsedMs=28107`) were read in the console and survive only in the decision log; the log groups were deleted in Section C.
- **B9 hadoop-prep stderr** (`STEP-FAIL hadoop-prep: source is not a regular file: experiments/inputs/15a/prep-config.json`) and the bootstrap EFS-mount diagnosis were read from the EMR logs bucket, which was destroyed in Section C; they survive only in the decision log.
- **Console coverage**: the C11 checks (2026-11-15T18:04Z) found ECS Clusters (0) and EMR on EC2 Clusters (0) in us-east-2. The 2 EC2 instance entries and the 28 security-group-rule entries of the after inventory were not separately checked (see `inventories/INVENTORIES.md`).
- **14B runtime apply at 155562d**: the approval digest and the logs show a runtime plan at 155562d (`runtime-plan-2.log`) but no apply log at that commit; the next applied runtime commit is bc81afd (`runtime-apply-3.log`).
- **Approval records not archived**: `target/phase14/approvals/` has no record for serial 7 (the runtime apply at bc81afd, `runtime-apply-3.log`) or serial 16 (the failed combined EMR apply, `15/emr-apply.log`). Serial 16 is referenced only in the text of `emr-apply.md` (serial 17). For both applies, the deploy script's own approval, plan-sha256 and account checks are in `approval-checks-unarchived-serials.txt`.
- **E1 / repairs 1-5** (24bf49d, 155562d, bc81afd, 9ee5bbe, 83a4168) are in the timeline and the 14B excerpt, but this set adds no separate repair record for them beyond `14b-deploy/deployer-e1*-decision.md` and the decision log's B8.3 entries.
