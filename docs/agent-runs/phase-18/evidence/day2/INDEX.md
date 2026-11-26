# Phase 18 Day 2: evidence index

Day 2 ran on 2026-11-25 (America/Chicago) from 10:06 AM to 9:27 PM CST, at HEAD `fe0b6ccdf1089deb24e2967a09d94ada9b1aae33` on branch `phase-18` (frozen; no commits during the session). The coordinator's decision log (`00-timeline/decision-log.md`) is the timeline of record. Kit: `target/phase18/day2/day2-kit.md` (git-ignored; reviewed, round 2 APPROVE).

Assembled offline on 2026-11-25 by the coordinator after the final inventory. No AWS, Anthropic or Voyage call was made to build it. Sources are local, git-ignored files under `target/phase18/day2/evidence/`, the Spark export in `<home>/Documents/scholarchain-day2-downloads/`, and the demo clips in `<home>/Movies/`.

**Redaction.** Every copied file went through one filter: ANSI codes and trailing spaces stripped; the AWS account ID (and its abbreviated form) replaced with `<acct>`; the repository path with `<repo>`, the home directory with `<home>`, any e-mail address with `<email>`, any IPv4 address with `<ip>`, macOS temp paths with `<tmp>`. An empty source stays empty. The scripts had already masked private tfvars values as `<redacted>` and the account ID in bucket names. "unchanged" means the filter changed nothing, so the sha256 here equals the source's. "generated" files are summaries written by the coordinator. A scan of every file here found no account ID, e-mail address, IP address, AWS access key, API key, session token or private key.

**Committing.** `.gitignore` ignores `*.log`, so the `.log` files here must be staged explicitly (`git add -f`); the folder holds 46 files besides this index.

**Lean selection.** Excluded: the dry-run logs (run with `env -u SCHOLARCHAIN_TF_PRIVATE_VARS`, human decision of 10:21 CST), the listing logs other than 1b and 2b (superseded by a fresh token), private files under `target/phase18/day2/private/` (including the EMR step stderr), the approval records and pre-spend receipts under `target/phase18/day2/approvals/` (their sha256 values are in `00-timeline/approval-hashes.txt`), the EMR step logs and the full Spark export (outside the repository; their hashes are in the downloads `SHA256SUMS`: 468 export objects, 4 files of the two experiment-run folders, 1 ledger copy), and the demo clips (hashes in `recordings/clips.txt`).

## Timeline of record

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `00-timeline/decision-log.md` | `bb42dad9d0cd17f74297e9081f2d703a1f4c60188087a3b7581c082a85e749d0` (redacted copy; source `ee1a48c12191ca68…`) | <repo>/target/phase18/day2/evidence/coordinator-notes.log | Coordinator's running decision log for Day 2 (2026-11-25 10:06 to 21:27 CST): most human decisions quoted verbatim (the rest are in `../../human-gate.md`, marked chat only), every gate result, the two gate-order notes. |
| `00-timeline/session-clock.log` | `8f47241b6b05ad248f4431e3fe36a62b2834eda9534e55d71ed539e58314c6a7` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/session-clock.log | Session clock readings and IAM window 1/2 open times. |
| `00-timeline/approval-hashes.txt` | `3a570565513fd96979e335c9bcc63cd78f0792bc05b66f7108cc76d1a3dec300` (generated excerpt) | <repo>/target/phase18/day2/approvals | sha256 of every Day 2 approval record and pre-spend receipt (the four receipts are byte-identical copies of one receipt, 897ffdf9...). |

## Deployer and stage a (blocks 5-10)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `stage-a/deployer-apply.log` | `d1fbcbb2afa512ac1ede82ccbae8883e69c5396544ebb3315ad56dea86fa1258` (redacted copy; source `c98afc56852203ba…`) | <repo>/target/phase18/day2/evidence/deployer-apply.log | Block 5: deployer plus 4 operator roles recreated from an empty deployer state (31 added), read-only verification. |
| `stage-a/stagea-base-plan.log` | `0eb6a1d3b6ff2acaae919a615273715835afa57c482742b230b59ebdf732c6b8` (redacted copy; source `259d9eba73163d1e…`) | <repo>/target/phase18/day2/evidence/stagea-base-plan.log | Block 8: stage-a base plan run 20261125T164849Z-66547, 171 creates, stagea-base IDENTICAL. |
| `stage-a/stagea-base-deltas.log` | `abc99b60902e1dbf3b12411ee301f1c7448d78755719dd271d5da0c91db1105a` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/stagea-base-deltas.log | Block 8: every planned address matched to the reviewed stage-a list. |
| `stage-a/stagea-base-apply.log` | `a24c8282aae88cf82d32fe6efe552830479d8a41eaf82d52034f956331de8dcd` (redacted copy; source `558a4c9232a0dc1c…`) | <repo>/target/phase18/day2/evidence/stagea-base-apply.log | Block 9: base-apply --skip-runtime-archive run 20261125T165206Z-70331, RESULT PASS. |
| `stage-a/state-sha-after-stagea-base.log` | `8132ecac4663147b01865c4045a0c44f1f5265808264af505da7108b3f0b9fc0` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/state-sha-after-stagea-base.log | Main state sha256 after stage-a base. |
| `stage-a/stagea-upload-plan.log` | `5a53d69fee40488c1b7594cc5be257d93e8e56542fcab40146c98805afa359fc` (redacted copy; source `4123b605d37eb643…`) | <repo>/target/phase18/day2/evidence/stagea-upload-plan.log | Upload plan run 20261125T165515Z-72896, 0 changes. |
| `stage-a/stagea-upload.log` | `56c9d11c5fb92a300a7af7c82ed81ccea4a6d4bd9a73e2b9cd1f2934b93b045b` (redacted copy; source `79c345d67379cf46…`) | <repo>/target/phase18/day2/evidence/stagea-upload.log | Block 10: runtime archive upload run 20261125T170532Z-77052, RESULT PASS. |

## EMR upload, enable, runs, download and archive (blocks 11-20)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `emr/emr-upload.log` | `e082380bdfd8a32c7e371954f0c500e890c7ff2a72682a0c38f70746b781668b` (redacted copy; source `353e7e2b0bf0c0ad…`) | <repo>/target/phase18/day2/evidence/emr-upload.log | Block 11: EMR artifact upload, 17 files verified, PLAN-SHA256 944e04bd…. |
| `emr/emr-upload-manifest.json` | `3d86dbe198d8ca2d094eb2d42a625dd524fab92925c7e3e0290f69637cadb40f` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/emr-upload-manifest.json | Block 11: uploaded EMR artifact manifest (names and sha256). |
| `emr/stagea-emr-plan.log` | `b92baddc604b577ba0cfad45ec54c765f7f9b7b10b8aafbd4eb3b2ad2e59b2c6` (redacted copy; source `182e95af3eeea3fa…`) | <repo>/target/phase18/day2/evidence/stagea-emr-plan.log | Block 13: EMR-enable plan, 13 creates, IDENTICAL. |
| `emr/stagea-emr-apply.log` | `c0fedc5984100655b35a4daed37d8eb6bca5d36ba11d29c618266c6044eacf87` (redacted copy; source `609f8655e3b3e7d1…`) | <repo>/target/phase18/day2/evidence/stagea-emr-apply.log | Block 13: EMR-enable deploy run 20261125T172606Z-90273, RESULT PASS. |
| `emr/cluster-id.log` | `51a0dbd31789ec35ec552e2e03872def448da177c9e20c046b3dd1ddb7bf499d` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/cluster-id.log | Cluster id j-05116692OZ06APLO3FMD. |
| `emr/emr-run-1.log` | `dfc93fdff75fbcc192eae34b7eafa5265166b4e6f2fa2f3375301b850f96b43f` (redacted copy; source `821e6c90ec4ba339…`) | <repo>/target/phase18/day2/evidence/emr-run-1.log | S attempt 1 (run 4): FAILED at hadoop-prep, exit 4 (incident 2026-11-25). |
| `emr/emr-actual-1.log` | `9dae6862b77d78aeec4b3cff29ff15f746aeffa83f5326c13a21120ed368b887` (redacted copy; source `1902ed2ed89db833…`) | <repo>/target/phase18/day2/evidence/emr-actual-1.log | record-actual after run 4: ledger 4 of 5. |
| `emr/emr-run-2.log` | `5a8aaebdca2e70992d60d6fc96b013e128c384d3eca01c0c956a66540156ed69` (redacted copy; source `09a8fe57a926a259…`) | <repo>/target/phase18/day2/evidence/emr-run-2.log | S retry (run 5): all six steps COMPLETED, spark-job included; RESULT PASS. The Phase 18 fix on EMR. |
| `emr/emr-actual-2.log` | `47e1de28a72d3d6ba1acc1c49bae268be88f03f97b4ee539249444a7ae6b4258` (redacted copy; source `a2048dc48dc9d09c…`) | <repo>/target/phase18/day2/evidence/emr-actual-2.log | record-actual after run 5 (idle tail counted). |
| `emr/emr-actual-2end.log` | `d479a5c2bc46017f136a174175848be28b06e1ef7546d91b32e3431307a7a0ee` (redacted copy; source `aa7c4fed6345bf11…`) | <repo>/target/phase18/day2/evidence/emr-actual-2end.log | record-actual after termination: ledger 5 of 5, USD 2.65 of 4.70. |
| `emr/cluster-final-state.log` | `95823108f25102c15d88f11839509742d2684a5813846901b96ee527ed3f4e63` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/cluster-final-state.log | Cluster TERMINATED. |
| `emr/download-excerpt.log` | `c76e49554dbef25e13a6e9db636929f581b82f48ec696277ca0d4ae32b60087f` (generated excerpt) | <repo>/target/phase18/day2/evidence/download.log | Block 19: run download (468 files); excerpt only. |
| `emr/archive.log` | `28e7d81dac44e24e50433483a543e239e64b85cf6576e45f07d90ec61aa8bb0c` (redacted copy; source `6595e3f8b41df97f…`) | <repo>/target/phase18/day2/evidence/archive.log | Block 20: archive-evidence day2-v1 written and verified (30 entries). |
| `emr/spark-counters.json` | `c99f2ceefc78d875c84bb9131e3b1dd79245f67100897844a9cebb7274c091a0` (unchanged; equals source) | <home>/Documents/scholarchain-day2-downloads/pipeline/15a/size-100/15a-emr-size-100-20261125T174034Z-99560/spark/run:30b3ef84-11dc-4c8c-b9c2-c632477d7282/counters.json | Spark export counters of run 5 (canonicalWorks 10578, canonicalResearchers 21819, allYearsEdges 81181, components 3942). |

## Cleanup prepare and two-pass destroy (block 21)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `cleanup/cleanup-prepare-plan.log` | `dd65420b8d5c2a6493715d2b15038411fe060da721d00889060f04ab95e54d19` (redacted copy; source `f3be3c4e8ec68b19…`) | <repo>/target/phase18/day2/evidence/cleanup-prepare-plan.log | Block 21a: preparation plan (18 protection-flag changes), second attempt PASS. |
| `cleanup/cleanup-prepare.log` | `167aea591f51081149ce5a49a7930602c27a611ad992ab4e34dde63524631a37` (redacted copy; source `d196c8c34a0c3029…`) | <repo>/target/phase18/day2/evidence/cleanup-prepare.log | Block 21a: cleanup-prepare run 20261125T183716Z-21162, RESULT PASS. |
| `cleanup/cleanup-list-1b.log` | `d200f72d8b61e571ddcb918eeaa239f8aec20a5972ed54fb1e79777099bbf9be` (redacted copy; source `8ee3fd6bde47ad93…`) | <repo>/target/phase18/day2/evidence/cleanup-list-1b.log | Listing 1b: 183 deletes, 0 foundation, token for pass 1. |
| `cleanup/cleanup-pass-1.log` | `08ab943a78bad3a3a8df56404ce14e638ade3845c5d6ba0b5c4c96d7be43d89d` (redacted copy; source `492af726ecc19661…`) | <repo>/target/phase18/day2/evidence/cleanup-pass-1.log | Destroy pass 1: PARTIAL at aws_eip.nat DisassociateAddress 403, 331 to 87. |
| `cleanup/cleanup-list-2b.log` | `45b2c508770aaccc659f9fadcc23e181633c36ee60a968b895969ea9b8e6a0bc` (redacted copy; source `cc06dd8cde0ed9f1…`) | <repo>/target/phase18/day2/evidence/cleanup-list-2b.log | Listing 2b: 1 delete (aws_eip.nat). |
| `cleanup/cleanup-pass-2.log` | `6ee7060064f75d764cdd90dd67d771a8ea98b84c9afd4d9ca797fdb373a6dd29` (redacted copy; source `2db02e9c329268c4…`) | <repo>/target/phase18/day2/evidence/cleanup-pass-2.log | Destroy pass 2: RESULT PASS, 48 to 46. |
| `cleanup/pass-1-before-inventory.txt` | `d587b7cc3d4bbf72c841e9d3c7c7abf426947a149b8f5d12c0192538a932a568` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/cleanup-evidence/20261125T190246Z-33667/before-inventory.txt | Cleanup pass-1 before-inventory.txt (evidence folder 20261125T190246Z-33667). |
| `cleanup/pass-1-after-inventory.txt` | `aca39cfd29353d90aeb3e86e175c54041a10b1e70ce1284509f82221484f501f` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/cleanup-evidence/20261125T190246Z-33667/after-inventory.txt | Cleanup pass-1 after-inventory.txt (evidence folder 20261125T190246Z-33667). |
| `cleanup/pass-1-destroy-actions.txt` | `14136032320bd24fbc2dbd91d2f842db99e33dfe0c4854504b27684d335e4920` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/cleanup-evidence/20261125T190246Z-33667/destroy-actions.txt | Cleanup pass-1 destroy-actions.txt (evidence folder 20261125T190246Z-33667). |
| `cleanup/pass-2-before-inventory.txt` | `b9fd49e834b55e1031cdf07abd06359aa0f313cc108b47512ff8160aec1bf948` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/cleanup-evidence/20261126T024608Z-59055/before-inventory.txt | Cleanup pass-2 before-inventory.txt (evidence folder 20261126T024608Z-59055). |
| `cleanup/pass-2-after-inventory.txt` | `5abddd5115fd2a44a21269890d01127b5bd62896c66163e154457c9aa759f649` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/cleanup-evidence/20261126T024608Z-59055/after-inventory.txt | Cleanup pass-2 after-inventory.txt (evidence folder 20261126T024608Z-59055). |
| `cleanup/pass-2-destroy-actions.txt` | `e332c521fb2f3449488401942def40dd324af8964b13b19ef4ed94c792a04c31` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/cleanup-evidence/20261126T024608Z-59055/destroy-actions.txt | Cleanup pass-2 destroy-actions.txt (evidence folder 20261126T024608Z-59055). |

## IAM window 2: C4 and P39 deployer removal (block 22)

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `p39/deployer-c4.log` | `78afcc691b91832a7c0a8c45a4cedbce4bb0a4069eadc5b190929894117022ed` (redacted copy; source `f943bcf55f9b4823…`) | <repo>/target/phase18/day2/evidence/deployer-c4.log | C4: 13 operator-role resources planned and destroyed. |
| `p39/p39-budget-after.txt` | `8bfc976f057e2f3cf9865ea2eeb3f0fc80ddf575ec2c7b21e58962b6be5e0dd1` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/p39/p39-budget-after.txt | P39 deployer removal: p39-budget-after.txt |
| `p39/p39-deployer-removal.log` | `482a267911a4a2fd9b316f6b104c99d2bafa6da6d846d78f54000824ef098eeb` (redacted copy; source `79af27d91f7ae9af…`) | <repo>/target/phase18/day2/evidence/p39/p39-deployer-removal.log | P39 deployer removal: p39-deployer-removal.log |
| `p39/p39-iam-before.txt` | `cf499bec9bed04f92a72897d4fb1662216ca6f7f1822856e8f535fb27dc2733a` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/p39/p39-iam-before.txt | P39 deployer removal: p39-iam-before.txt |
| `p39/p39-policies-after.txt` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/p39/p39-policies-after.txt | P39 deployer removal: p39-policies-after.txt |
| `p39/p39-policy-entities-before.txt` | `886da293d47b2fdf7ee2f20573a2515dfd37c78eaccf267019e829b7811b21d8` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/p39/p39-policy-entities-before.txt | P39 deployer removal: p39-policy-entities-before.txt |
| `p39/p39-roles-after.txt` | `c3e2c7babdd634245f10223e7f606f76b5ec2320c9cb5f94124a458bc3e55e22` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/p39/p39-roles-after.txt | P39 deployer removal: p39-roles-after.txt |
| `p39/p39-roles-before.txt` | `e26b10994afb70e672c1c8f2ff902d570eb551ee8ad7a97f02ab1d93921bf12d` (unchanged; equals source) | <repo>/target/phase18/day2/evidence/p39/p39-roles-before.txt | P39 deployer removal: p39-roles-before.txt |

## Recordings

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `recordings/clips.txt` | `ebed9c03c3bb0babee11713d3e280eeffb50564ad6a1d12f9694f064d2cb7f88` (generated excerpt) | <home>/Movies | sha256 and size of each Day 2 demo clip. |

## Downloads

| File | sha256 of file here | Source | Proves |
|---|---|---|---|
| `archive/downloads-SHA256SUMS.txt` | `0df476aa06a01bc1d1074c6c897addf2986ab6054725df0af9964343a5bbb9ba` (generated excerpt) | <home>/Documents/scholarchain-day2-downloads/SHA256SUMS | Hash of the local downloads checksum list. |
