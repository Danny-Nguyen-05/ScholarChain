# Phase 15 live session 2: evidence index

Session 2 ran on 2026-11-18 from IAM window 1 (14:04:38Z) and H0 = 14:44:25Z (`00-timeline/session-clock.log`) to C10 at 22:59Z, at HEAD `bd0b8180b919ed61f6234fa515f4c07d1137a641` (frozen, no in-session commits). The running decision log (`00-timeline/decision-log.md`) is the timeline of record.

Assembled offline on 2026-11-18 by the orchestrator after Section C. No AWS, Anthropic or Voyage call was made to build it. Sources are local, git-ignored files under `target/phase15/session2/evidence/`, `target/cleanup-evidence/`, `target/phase14/archive/phase-14/evidence/session2-v1/` and `<home>/Documents/scholarchain-session2-downloads/`.

**Redaction.** Every copied file went through one filter: ANSI codes and trailing spaces stripped; the AWS account ID (and its abbreviated `NNN...NNNN` form) replaced with `<acct>`; the repository path with `<repo>`, the home directory with `<home>`, any e-mail address with `<email>`. The scripts had already masked private tfvars values as `<redacted>` and the API host. "unchanged" means the filter changed nothing, so the sha256 here equals the source's. "generated" files are excerpts: for each source they write its path, line count and sha256, then only the RESULT/STEP/Plan/Apply/Error lines (test-name lists and "Still destroying" progress lines dropped). Public IPv4 addresses with a mask are replaced with `<ip>/32` and macOS temp paths with `<tmp>`. A scan of every file here found no account ID, e-mail address, IP address, API key or session token.

**Additions after 2026-11-18.** The `p39/` files (2026-11-19) and the `c11/` file (2026-11-20) were added with the same redaction filter, plus a general mask of any 12-digit number, and the decision-log copy was refreshed on 2026-11-20. A scan of the added files on 2026-11-20 found no account ID, e-mail address, IP address, API key or session token.

**Amended 2026-11-26.** By a one-time human-approved exception (recorded in `docs/agent-runs/phase-18/human-gate.md`, Day 3 decisions), the two used destroy confirmation token values in `section-c/cleanup-results.txt` are replaced with `<used-one-time-token>` wherever they occur (the `CONFIRM-TOKEN:` lines and the lines that repeat them after `--confirm`), because secret scanners flag them as generic high-entropy strings. Each value was an unkeyed sha256 over the plan hash, account hash, region, environment and action list (`scripts/cleanup.sh`), not a credential, and both were used on 2026-11-18 and are no longer valid. That file's hash below is of the amended copy; the old values remain in git history. Nothing else in this folder changed.

**Lean selection.** Full logs are kept where they are small; large or noisy logs are excerpted. Excluded: the ingest-1 report (2.4 MB of per-item rejections; its summary is in `vectors/ingest.log`), the full Terraform plan texts and saved plans, private files under `target/phase15/session2/private/` (tfvars backups, unredacted dry runs, secret ARNs, step stderr), approval records and receipts under `target/phase15/session2/approvals/` (their sha256 values are in the decision log and the archive index), the EMR step logs and experiment downloads (outside the repository; hashes in `archive/downloads-SHA256SUMS`), and the demo clips (outside the repository; hashes in `recordings/clips.txt`).

## Timeline of record

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `00-timeline/decision-log.md` | `4f819c61801742de628caabe8a768cbe24e156fe19a7525a4f61cd37ca03cf69` (redacted copy; source `e6aed6fb825b833b…`) | <repo>/target/phase15/session2/evidence/coordinator-notes.log | Coordinator's running decision and evidence log, the timeline of record: IAM window 1 (14:04:38Z) to C10 (22:59Z) on 2026-11-18; P39 on 2026-11-19 (18:53-19:12Z); the README review record on 2026-11-19/20; C11 and the human's acceptance decision on 2026-11-20. Every human decision is quoted verbatim with its UTC time. |
| `00-timeline/session-clock.log` | `2a97ec1a6e9745fbbe2b9657b38d87c01d699f84b266ca52f0c3925eaf6764ad` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/session-clock.log | Session clock readings (`clk`), including H0 = 2026-11-18T14:44:25Z. |
| `00-timeline/nclock.log` | `e909e6fd9fca99ef3029dd67b62e1b9ce6e02c69d7c92789bfa263f3e24e87f2` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/nclock.log | Neptune clock from T_N0 = 20:01:44Z: load, failure-example, pre-destroy and destroy target/absolute times. |
| `00-timeline/gate1.log` | `109c277d5241f22e47bf28776289e9263b7cedb01dc83ca6149302df39f34142` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/gate1.log | Gate 1 (19:58:59Z) arithmetic: X_a 0.80 <= 2.85 PASS; pre-R-b 20.20 <= 23.00 PASS. |
| `00-timeline/preflight.log` | `b9c5e2ff9e6ce59d6234f8e04e8dcadb3859dc6681907c0af77787147f527595` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/preflight.log | Block 2 pre-flight (human-pasted, IP omitted): HEAD bd0b818, clean tree, LLM ledger 0.075075 from earlier phases, caffeinate running. |

## Setup, IAM window 1, secrets, deployer (blocks 1-15)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `a-setup/a5-login-rehearsal.log` | `4eeabaf26d836ca0a2ddfda82f103d934b2fa6697966213760bf54c2cec0ea28` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/a5-login-rehearsal.log | A5: every operator profile resolved to its own assumed role. |
| `a-setup/a7-secrets.log` | `5c76b07ab055919cb030fc7eca332dedb2416c22d52c33f3e13cf40a15e6257d` (redacted copy; source `91df808988460435…`) | <repo>/target/phase15/session2/evidence/a7-secrets.log | A7: three runs: AccessDenied, a parameter-validation failure (temp dir missing), then the four `scholarchain/course/*` secrets created (names and ARNs only; values never shown). |
| `a-setup/b3b-provider-keys.log` | `86ad7d8f27b1e5685c0705ff1811203ff1e9d4641e673c3fc86976076cccb3f3` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/b3b-provider-keys.log | B3b: Voyage key and Anthropic placeholder put into their secret containers (version ids only). |
| `a-setup/acm-issued.log` | `48e51a485e32f122a8cfbd0c9382073f983bbccf31ec116a82a78af111f13af7` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/acm-issued.log | Block 14: ACM certificate ISSUED. |
| `a-setup/iam-window1-closed.txt` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/iam-window1-closed.txt | Empty: the window-1 check output was not captured to this file. Window 1's close is recorded in the decision log (14:32:48Z; final removal of the narrow b3b/cli-login policies by root at 16:16:32Z). |
| `a-setup/deployer-apply-results.txt` | `45648681007bf9f14637ef8d03fd173febf9fceed329569a4fb65ae8adfd72e6` (generated excerpt) | excerpt of deployer-apply.log | Block 4/5 deployer plan and apply: 13 added (operator roles on). |

## Stage a: base and EMR-enable (blocks 8-17)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `stage-a/stagea-results.txt` | `fcd2b8ad8f6a605512d4951bb9b49a899f1be2eb627c1a1f572ed1037a1bcf46` (generated excerpt) | excerpt of stagea-base-plan.log, stagea-base-plan2.log, stagea-base-apply-dry.log, stagea-base-apply.log, stagea-base-apply2-dry.log, stagea-base-apply2.log, stagea-emr-plan.log, stagea-emr-apply-dry.log, stagea-emr-apply.log | Stage-a plan PASS, base-apply 1 (Terraform applied, runtime-archive upload RequestTimeout, exit 5), recovery plan and base-apply 2 PASS, EMR-enable plan and apply PASS. The failed plan attempt 1 (precondition) is in the decision log (line 17); the 171 creates are in `stagea-base-deltas.log`. |
| `stage-a/stagea-base-deltas.log` | `abc99b60902e1dbf3b12411ee301f1c7448d78755719dd271d5da0c91db1105a` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/stagea-base-deltas.log | Stage-a base plan action list compared with the reviewed derivation: IDENTICAL. |
| `stage-a/stagea-emr-deltas.log` | `a8ae1e57014e4d45a852555bcbbd889c76149d4f15c75fdd8512732ee56152bf` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/stagea-emr-deltas.log | EMR-enable plan action list: IDENTICAL. |
| `stage-a/state-sha-after-stagea-base.log` | `379cc8c2f05e0c9cfc35a860ba38ff6bec136c688fc6530a2624aab4895355b0` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/state-sha-after-stagea-base.log | State sha256 after stage-a base apply. |

## EMR pipeline (blocks 16-23)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `emr/emr-upload-results.txt` | `308a17157e761164856efa361a04226136d6c984ae3fe28dbeba11884cdf32b8` (generated excerpt) | excerpt of emr-upload.log | Block 16: EMR artifact upload, 17 files verified. |
| `emr/emr-upload-manifest.json` | `bcb5efd5cb78cc7be7a878256ad05d7419feed74a41ce9ce5ae3f60142daf610` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/emr-upload-manifest.json | Upload manifest: each artifact's S3 key and sha256. |
| `emr/emr-run-1.log` | `4f0015a16fde0b8c14d6176b52b6c1dbedc1da07784442ad9214303f475eeb83` (redacted copy; source `07dea000ecc246c1…`) | <repo>/target/phase15/session2/evidence/emr-run-1.log | EMR run S attempt 1: stage-in, hadoop-prep, entity-resolution, spark-class-origin COMPLETED; spark-job FAILED (exit 4). |
| `emr/emr-actual-1.log` | `1b28c919ade0b992fa596e84539b002a761df71e6cba4706cdc049bbb585e4c5` (redacted copy; source `96060d651831ed6b…`) | <repo>/target/phase15/session2/evidence/emr-actual-1.log | EMR ledger record-actual after the failure (measured 0.28 + tail 0.14). |
| `emr/emr-actual-1end.log` | `74e7b2e0bb89842359675a08d1858d47933cfa202675dcbff2cb5be715b453b0` (redacted copy; source `f159689373a9ebac…`) | <repo>/target/phase15/session2/evidence/emr-actual-1end.log | EMR ledger final record-actual after termination: measured 0.37; cumulative 2.05 of 3.53; 3 of 4 runs. |
| `emr/cluster-id.log` | `b2a9d825db433976b6db67a2d9b96f6b2557705b8ee640d7cad7a820f58ed28b` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/cluster-id.log | EMR cluster id. |
| `emr/cluster-final-state.log` | `58d1f77e0f870ee3fc1d619072779a49a8f43bc86880da89974f4bdec5ecc4dc` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/cluster-final-state.log | Cluster state read at about 17:02Z: TERMINATING. The end time (17:06:31Z) is in `emr-actual-1end.log`; TERMINATED is recorded in the decision log (line 39). |
| `emr/s1-spark-failure.json` | `f6d9606b36bb85119f541b184367145d2e752895b196366f2d0c81e2eebd043b` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/s1-spark-failure.json | spark-job step FailureDetails. |
| `emr/hadoop-prep-counters.txt` | `6698639ba02f95209d0c5d62b7d9cb8fe14dde1dcb74220bc6a7ad9a06875760` (generated excerpt) | excerpt of emr-hadoop-prep-stdout.txt, emr-entity-resolution-stdout.txt | Counter lines of the Hadoop-prep and entity-resolution step stdout on EMR (from the downloaded step logs): INPUT 290,343, ACCEPTED 515,309, REJECTED 1,243. |
| `emr/emr-dry-100-results.txt` | `e2eec3ba595057713b65def3d4c3705327e108a72c1c47d1191f185b12ebf057` (generated excerpt) | excerpt of emr-dry-100.log | Run-experiment dry run for the size-100 EMR run (unredacted fallback). |

## Render, ingest and query smoke (blocks 24-26)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `vectors/render-manifest.log` | `c2e653b3608d13ec2eb8fb26aad8b7fa7703620fd25d752f251e67f5e57c91bf` (redacted copy; source `62cba711ba3fb681…`) | <repo>/target/phase15/session2/evidence/render-manifest.log | Block 24 render-only from P6 export run:ba7402d1: 10000 documents, manifest sha256 df0d5028.... |
| `vectors/ingest.log` | `32267c3e80f073f91491ac01d7e958a0736659e8f278e9cf8d196c17c6d2285a` (redacted copy; source `3bfc0fd444019e93…`) | <repo>/target/phase15/session2/evidence/ingest.log | Ingest run 1 (run-20261118-ingest): ended with `live-ingestion-rejected-items`. The counts (10000 rejected, `embedding-provider-rejected`) and the HTTP 401 key test are in the decision log (line 40). |
| `vectors/ingest-2.log` | `3ae03d04270e7d91cc6b750924154a58b144bd75a6aa3dabe2ba1ce552253287` (redacted copy; source `af9aa9de71a4ae7b…`) | <repo>/target/phase15/session2/evidence/ingest-2.log | Ingest run 2 (run-20261118-ingest-2): written 10000, rejected 0, exit 0. |
| `vectors/ingest-report-2.json` | `4ffc1389dbf117670e276675ca0774bb065b11768ffe6f99ebe0e61324e994cd` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/ingest-report-2.json | Ingest-2 report (counts per index, calls, timing). |
| `vectors/query-smoke.log` | `13e28afc063a641c5c939a09f7c5447ade2ac43ab4b7168c8c3b0d8ea652d5ca` (redacted copy; source `c54c8a3b12b8588e…`) | <repo>/target/phase15/session2/evidence/query-smoke.log | Block 26 query smoke: 5/5 samples, 7 verified pointers, exit 0. |
| `vectors/query-report.json` | `39a68f7cc348d233dfc680e67b990408b3fb01f60bee2c80305e315e415b3fef` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/query-report.json | Query smoke report with per-index latency. |

## R-b: Neptune, push, runtime, smoke (blocks 27-32)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `rb-runtime/rb-runtime-results.txt` | `4c290dc9018fdbca9910044810e14bf2325e0857271a37119abc267496e6d222` (generated excerpt) | excerpt of rb-base-plan.log, rb-base-apply-dry.log, rb-base-apply.log, push-dry.log, push.log, runtime-plan.log, runtime-apply-dry.log, runtime-apply.log | R-b Neptune base plan/apply PASS, push PASS, runtime plan and runtime-apply PASS (the 25 add / 4 change summary is in the decision log, line 56). |
| `rb-runtime/rb-base-deltas.log` | `da0161b8fadb07682df2e822521661c9f86095000692f57e99434a2d8cd14b91` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/rb-base-deltas.log | R-b base plan action list: IDENTICAL. |
| `rb-runtime/state-sha-after-rb-base.log` | `d403847fd8ac6f05f8a8c6c8ebf792f86b3f55d77c4054f4bb377478771636e8` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/state-sha-after-rb-base.log | State sha256 after the Neptune base apply. |
| `rb-runtime/state-sha-after-runtime.log` | `65d5c811f6f51a440ee130e5562eb741a67c2db69f7d37ecf0b766d16df33b27` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/state-sha-after-runtime.log | State sha256 after runtime-apply. |
| `rb-runtime/b30-keys-check.log` | `96db014ebc3244715398014b5118b8c6b90055f3ed13badf93fe8ff96e8e305f` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/b30-keys-check.log | Block 30 keys check: Voyage secret AWSCURRENT = the working key's version; Anthropic placeholder, 1 version. |
| `rb-runtime/smoke-14b.log` | `15510cf6e6ed31aec53fba1ca9cfd92093e07a8a2f68eba0f5a336a6e1b06be8` (redacted copy; source `ae7ab7f3b25fe023…`) | <repo>/target/phase15/session2/evidence/smoke-14b.log | Block 32 smoke `--checks healthz,readyz`: 2 of 6 checks by design, both 200. |
| `rb-runtime/manual-401.log` | `e16bc1a2563f01cf4139454b5214f92222899237f0042e6fb484c8dd17408146` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/manual-401.log | Manual checks: missing and invalid API key 401, unknown evidence 404. |
| `rb-runtime/b6-checklist.log` | `99459b3c25ec2c52b0ff8d77aee271356df5bfc1c54221cbdccc2606cf5ccef9` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/b6-checklist.log | GO/NO-GO 3: four services 1/1, target healthy. |
| `rb-runtime/p14-7-evidence-404.log` | `f8bf41177a5f5e808a7ccb648b51080b031f15ca8018d91a576263d6cc626eb6` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/p14-7-evidence-404.log | Unknown evidence id returns 404. |

## R-b load test (block 33)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `b10-load/b10-plan.log` | `2d12e8f38936d0f70b6b7554e6631ed4f6f23f9a384cc9c995b7b89b95219190` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/b10-plan.log | Load plan: 7 phases, total 3570 s (LLM disabled). |
| `b10-load/b10-validate.log` | `3b61c3093231f723ec601d517ca21df594410cc5127468efaa3898f3ce2d7465` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/b10-validate.log | Manifest validation MANIFEST-OK. |
| `b10-load/b10-loadgen.log` | `0940f23236bb57bee312d261bcb76bf6fb52f3e32327c61a57d7aa2c75a4edfa` (redacted copy; source `bb8e315fdc7f00d1…`) | <repo>/target/phase15/session2/evidence/b10-loadgen.log | R-b load rb-20261118: 26,962 requests, 0 x 429, ABORTED. The abort time and the 5xx/timeout breakdown are in the decision log (line 62), read from the raw request file (outside the repository). |
| `b10-load/b10-ecs-poll.log` | `23c4e02aba78f7983f175e4fc084f29d2da35205fef40ee6cf5023efb4e48460` (redacted copy; source `1347bf15230e87a8…`) | <repo>/target/phase15/session2/evidence/b10-ecs-poll.log | ECS desired/running/pending poll: 1/1/0 at 20:51:54Z, 2/1/1 at 20:52:55Z, 2/2/0 at 20:53:56Z; blank lines are deployer credential gaps. |

## Failure example (block 35)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `b35-failure/p11-failure.log` | `e091750d7afc71df98029840266ee5dae086c6a7835231e2a4563622a0182cf0` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/p11-failure.log | Block 35 failure example: healthz/readyz watch around the stop-task of the query-api task (503/502, then 200/200 after about 1-2 min). |

## Archive and downloads (block 36)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `archive/archive.log` | `3b344ecfa7954a73e1659d9b6b45d36fb9c56c9435303f9132da00f6dcfc389b` (redacted copy; source `19fbe2aa9044562e…`) | <repo>/target/phase15/session2/evidence/archive.log | Block 36 archive session2-v1 written and verified, RESULT PASS. |
| `archive/receipt-copies-map.log` | `f9b14a29e614e0e15b6c8f44b3661d217b3c99047614de33ea12464daeba05a7` (redacted copy; source `ba7e74190c10eea5…`) | <repo>/target/phase15/session2/evidence/receipt-copies-map.log | Map of receipt copies 01-04 to their sources. |
| `archive/state-sha-before-cleanup.log` | `65d5c811f6f51a440ee130e5562eb741a67c2db69f7d37ecf0b766d16df33b27` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/state-sha-before-cleanup.log | State sha256 before cleanup. |
| `archive/archive-INDEX.json` | `043ce9daf40843634c1a3c3b38e288ba70e797bfed2cd7bab8101a2a9485bd93` (unchanged; equals source) | <repo>/target/phase14/archive/phase-14/evidence/session2-v1/INDEX.json | The archive's own index of archived records with sha256. |
| `archive/downloads-SHA256SUMS` | `e4972a8b062b11f6685c396c86bce1a1afeda61115ee6d8ef1c673376f0c7000` (unchanged; equals source) | <home>/Documents/scholarchain-session2-downloads/SHA256SUMS | SHA256SUMS of the 15 files downloaded before cleanup (outside the repository). |

## Demo clips

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `recordings/clips.txt` | `827ea4646aef23f8b502eb5eb45ca5fe6d8bb5f75602070825574081846274b4` (unchanged; equals source) | <repo>/target/phase15/session2/clips.txt | The ten Session 2 demo clips with duration and sha256 (clips kept outside the repository; the root-console clips may show the human's e-mail, see the decision log). |

## Section C cleanup (blocks 37-40)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `section-c/cleanup-results.txt` | `2846ef8b18f3418a1ff310c3cb7cb3b428de00421c71d00da725994fc7c91aff` (generated excerpt) | excerpt of cleanup-prepare-plan.log, cleanup-prepare-dry.log, cleanup-prepare.log, cleanup-list-1.log, cleanup-pass-1.log, cleanup-list-2.log, cleanup-pass-2.log | Section C: cleanup-prepare plan and apply PASS (20 protection-flag updates); listing 1 REFUSED by design (201 deletes); pass 1 PARTIAL at the EIP 403 (297 -> 65); listing 2 (1 delete); pass 2 PASS (65 -> 63). |
| `section-c/destroy-actions-pass-1.txt` | `25935ad31cb14c5efd07e899228001e902050c5eda25a525e5a5b4c1c68bc0c4` (redacted copy; source `19b13f5837f454ad…`) | <repo>/target/phase15/session2/evidence/cleanup-evidence/pass-1/destroy-actions.txt | Pass 1 destroy actions (201). |
| `section-c/destroy-actions-pass-2.txt` | `e332c521fb2f3449488401942def40dd324af8964b13b19ef4ed94c792a04c31` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/cleanup-evidence/pass-2/destroy-actions.txt | Pass 2 destroy action: `module.network.aws_eip.nat` only. |
| `section-c/deployer-cleanup-apply-results.txt` | `66d25a07c23322a5b076dce060ef85a3bd3cd325322608e908611920d4c61fad` (generated excerpt) | excerpt of deployer-cleanup-apply.log | C4: deployer plan 0/0/13 and apply 13 destroyed (operator roles off; deployer role kept for P39). |
| `section-c/iam-window2-closed.txt` | `175c276e52131c3858bd48eb6ad2fde24bc16d5f95b58cee60cfbcb63e45ba0b` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/iam-window2-closed.txt | IAM window 2 closed check: no attached policies; inline only assume-deployer and billing-assume-role. |
| `section-c/c5-secrets-delete.log` | `18ca0be036902b4bd1185fdab083b75345f15a17363db89fc55df39901acc3fc` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/c5-secrets-delete.log | C5: the four secrets force-deleted; DeletedDate for each. |
| `section-c/c5b-key-revocation.log` | `ca7ab89ea618240ea823f2acf788195cc61777bfe495d26540fa6fbe50bb0294` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/c5b-key-revocation.log | C5b: both Voyage keys revoked 22:46:11Z; no Anthropic key was created. |
| `section-c/c7-kms.log` | `ccb01ed571e9f2c30e3dfcdd222bf7e839f5d926709a0658501ffa2bf32d5f5a` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/c7-kms.log | C7: the Session 2 project KMS key (8398343a) is PendingDeletion. The second key in the inventory (cb0a6f60) was not checked. |
| `section-c/c8-inventory.log` | `49a9804f34fd9539db79cb80850210cd5d24f63820f7503e6a43f42a923784c8` (redacted copy; source `7f528c8e626437f3…`) | <repo>/target/phase15/session2/evidence/c8-inventory.log | C8: tagging API 83 ARNs grouped by type (all leftovers); all 7 data-lake buckets 404. `list-buckets` was denied to the deployer; the `EXISTS` lines are a command artifact, not bucket results. |
| `section-c/llm-status-cleanup.log` | `08ba9dea6f11972c15c306db07001775ecb86489f945afeb066ecf793cb68f4d` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/llm-status-cleanup.log | C9: LLM ledger unchanged at USD 0.075075 (no Anthropic use in Session 2). |
| `section-c/c10-logout.log` | `8c9bb79bbefcda11a2434452279e752480476bad863230b86a143da282390b33` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/c10-logout.log | C10: logout time. |

## P39: deployer role removal (2026-11-19)

Run by the human on 2026-11-19 from the reviewed procedure in `infra/terraform/deployer/README.md` (section "P39: deployer role removal"), in IAM window 3 (18:58:04-19:09:33Z, from the first OPEN stamp). Human decision before the apply, verbatim: "apply P39".

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `p39/p39-deployer-removal.log` | `24f5f549bd9dc72ca5f5a45091c894c2b52777d9752a41a653380271a29dac07` (redacted copy; source `cbb26f891e724622…`) | <repo>/target/phase15/session2/evidence/p39-deployer-removal.log | P39 log: start 18:53:23Z; state 18 = STATE-MATCHES-EXPECTED; window 3 OPEN stamps 18:58:04Z and 18:58:59Z (the stamp line was run twice); pre-plan state backup sha256 (fd0170da…, equal to the post-C4 backup); `Plan: 0 to add, 0 to change, 18 to destroy.` with the 18 `delete` addresses and PLAN-MATCHES-EXPECTED; apply 19:06:31-19:06:35Z `Apply complete! Resources: 0 added, 0 changed, 18 destroyed.`, 18 `Destruction complete`; state sha256 after and state count 0; `NoSuchEntity` with get-role exit 254; roles diff `< scholarchain-deployer` only; window 3 CLOSED 19:09:33Z. |
| `p39/p39-iam-before.txt` | `73f232076e509281c5f008a6f6db7d7e94b9de7746f04f2be8b73a20a1e6166f` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/p39-iam-before.txt | Block 4a: role `scholarchain-deployer` with the 7 `phase14-main` policies attached, inline only `scholarchain-deployer-same-device-login`, no instance profiles; every call exit 0. |
| `p39/p39-roles-before.txt` | `e26b10994afb70e672c1c8f2ff902d570eb551ee8ad7a97f02ab1d93921bf12d` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/p39-roles-before.txt | `scholarchain*` roles before: `scholarchain-billing-deployer`, `scholarchain-deployer`. |
| `p39/p39-policy-entities-before.txt` | `7c6642f5990e1ef3d3ec157f16f2ed5a7532e3fd413051838ebcd0b4da622dfa` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/p39-policy-entities-before.txt | Block 4b DeleteConflict pre-check: the 7 permission-set policies used only by role `scholarchain-deployer`; the 2 boundaries used by no role, user or group; 9 calls exit 0. |
| `p39/p39-policies-after.txt` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/p39-policies-after.txt | Block 7: empty = no `scholarchain-deployer*` policy and neither boundary remains. |
| `p39/p39-roles-after.txt` | `c3e2c7babdd634245f10223e7f606f76b5ec2320c9cb5f94124a458bc3e55e22` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/p39-roles-after.txt | `scholarchain*` roles after: only `scholarchain-billing-deployer` (kept). |
| `p39/p39-budget-after.txt` | `8bfc976f057e2f3cf9865ea2eeb3f0fc80ddf575ec2c7b21e58962b6be5e0dd1` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/p39-budget-after.txt | Block 7 budget call: AccessDeniedException (the admin user has no `budgets:ViewBudget`; expected). The budget was then checked read-only in the root console (decision log). |
| `p39/iam-window3-closed.txt` | `44036792d915a57c0043e2cf8a3132b04505bf3f4bc96f401f01ab90b8b2ec01` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/iam-window3-closed.txt | Window 3 CLI close check: refused, because the CLI login could not refresh once `scholarchain-operator-cli-login` was removed. The close was checked in the root console instead (decision log: only the two inline policies, no `IAMFullAccess`). |

## C11 billing check (2026-11-20)

Read by the human at about 15:45Z on 2026-11-20 (Cost Explorer in the root console and the Voyage dashboard; screenshots not stored; the Budgets figure in the report is the 2026-11-19 19:10Z reading); the totals are in the decision log.

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `c11/cost-report.log` | `6555edba6336ff9e43ef74f3454bec5d5e1ca738d55a9adb03736dafbb5c984d` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/cost-report.log | C11b cost report rendered by `scripts/lib/cost_report.py`: AWS 17.88 (Nov 1-20, credits excluded; Nov 18 = 2.13 with the per-service values; Nov 19 and 20 = 0.00 at the reading), Anthropic 0.08 (earlier phases' ledger), Voyage AI 0.00 (token count not read; R-b window unverified); combined 17.96; remaining 7.04 of the USD 25 ceiling. |

## Inventories

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `inventories/before-cleanup-inventory.txt` | `acef26e600042f5c77bf370abc3d700fd959d35344a1b8f1ca22764e93c8152c` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/cleanup-evidence/pass-1/before-inventory.txt | Tagging-API and state inventory before pass 1 (297 entries). |
| `inventories/after-pass-1-inventory.txt` | `75f4bf4ed6912f0e0afa18480b1ce3271d7cad4c75e98f5614e46e4c8bc46635` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/cleanup-evidence/pass-1/after-inventory.txt | Inventory after pass 1 (65 entries). |
| `inventories/after-cleanup-inventory.txt` | `cba690b78204cf6c6163587fe20b4b2ab49765772759b3595d1f3d9df1bf8b77` (unchanged; equals source) | <repo>/target/phase15/session2/evidence/cleanup-evidence/pass-2/after-inventory.txt | Inventory after pass 2 (63 entries): two free `terraform_data` guards plus tagging-index leftovers of deleted resources. |
