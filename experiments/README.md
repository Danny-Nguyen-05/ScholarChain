# experiments

Phase 15 experiment definitions (owner: experiment-engineer). Nothing here has been run on AWS; no upload, no cloud call and no spend has happened. Every live run needs the human approval record (`docs/agent-runs/phase-15/human-gate.md` per `RUN_APPROVAL_RECORD_PATH`) and, for EMR, the pre-spend receipt.

Run all commands from the repository root with `python3 -I`.

## Contents

| Path | Purpose |
|---|---|
| `manifests/15a-emr-size-{25,50,100}.json` | the EMR runs: size-25 and size-50 are Session 1 history, size-100 is size S (120 min since 2026-11-24, r5.xlarge primary); size L has no EMR manifest; schema `scholarchain.experiment-manifest.v1`, accepted by `scripts/run-experiment.sh` |
| `manifests/15b-ecs-scaling.json` | query-api scale-out / scale-in driven by `load-tests/loadgen.py`; schema `scholarchain.load-experiment-manifest.v1` (run-experiment.sh is EMR-only and cannot take it) |
| `manifests/15b-ecs-scaling-semantic.json` | the P42 semantic variant of 15B (R-b load): warm-up pass, levels 1/5/25/50, hold at 50, 30 quiet minutes; required per-level request limits 600 / 3,000 / 15,000 / 30,000 / 150,000 (198,600); semantic block pins the questions file; hand-authored (the renderer covers 15A only), checked by `check_manifests.py` |
| `inputs/15b/` | the fixed semantic question set (`semantic-questions.txt`, 150 DBLP topic phrases) and its provenance file |
| `scripts/derive_semantic_questions.py` | derives `inputs/15b/` from the Phase 6 DBLP slice (deterministic, offline) |
| `manifests/16b-live-evaluation.json` | 16B placeholder: the LLM answer budget, the Voyage embeddings allowance, their tie to the shared claude-haiku-5-5 cap and the command (`load-tests/eval16b.py`) that asks the 40 questions |
| `manifests/llm-allocation.json` | pinned split of the USD 1.33 claude-haiku-5-5 (Anthropic API) cap across the buckets 14c, 15b, 16b and 17 (160 answers since the user decision of 2026-11-21, option A) |
| `inputs/15a/prep-config.json`, `datasets.json` | the Hadoop prep config (uploaded as `config/hadoop-config.json`, P1; `maxLocalSampleRecords` 60,000, P22) and the dataset snapshot manifest the 15A manifests name |
| `inputs/15a/spark-emr-template.json` | the EMR Spark template for both sizes (P24; 64 shuffle partitions), uploaded as `config/spark-config-template.json` |
| `inputs/15a/config-sources.json` | the repository files used for `--hadoop-config`, `--er-policy`, `--er-config`, `--spark-config-template` (paths and sha256) |
| `inputs/14c/` | the real include list, smoke body, 40 questions and node IDs derived from export `f6e63b4b`, with a provenance file |
| `scripts/derive_14c_inputs.py` | derives `inputs/14c/` from the local Phase 6 export (deterministic) |
| `inputs/q12/`, `manifests/q12-benchmark.json` | the Q12 benchmark: 33 questions (3 x 11 types), include list, question specs, computed answer key and provenance, derived from the same export; see "Q12 benchmark" below |
| `scripts/q12_graph.py`, `derive_q12_inputs.py`, `q12_answer_key.py`, `q12_score.py` | Q12 graph helpers (ports of modules/spark), input derivation, answer key and scorer (stdlib, offline); `tests/test_q12.py` |
| `scripts/make_dblp_subsets.py` | builds the three input trees locally from the real Phase 6 slice (and, with `--tree-label`, the L tree) |
| `scripts/build_l_input.py` | one command for the local size-L tree: builds `size-l/` from the dataset-engineer's L slice, rechecks S ⊂ L and the evidence record |
| `inputs/15a/size-l-local-evidence.json` | size L, local evidence only (not an EMR run): slice facts, P6 numbers, identity-bypass Spark summaries |
| `scripts/render_manifests.py` | renders the size S manifest (tokens for buckets and run prefix; config hashes from the files, JAR hashes from `--sha`); never rewrites the Session 1 history |
| `scripts/check_manifests.py` | offline validation of every manifest and the cost arithmetic |
| `tests/test_experiments.py`, `tests/test_derive_14c_inputs.py`, `tests/test_semantic_manifest.py` | 48 + 23 + 16 tests (the directory holds 100 with `test_er_identity_bypass.py`) |

## 15A: EMR runs (Session 1 history and size S)

Session 1 (history): one run per size, each on 1 primary + 1 core `m5.xlarge` (capacity 2), 90 minutes of cluster time at most, 900 s idle auto-termination. G6 estimate per run = 2 x (0.192 + 0.048) x (5,400 + 900) / 3,600 = **USD 0.84**. `15a-emr-size-25.json` and `15a-emr-size-50.json` stay byte-identical to commit 7a02de2 as the ledger history of the two Session 1 runs (USD 1.68); they are not rerun. EMR capacity is fixed per run: a node-level scale-out would need `max_task_count` above 0, which the ledger cannot afford; the report must say if no capacity change occurs.

### Session 2: size S on EMR, size L as local evidence only (P1, P21, P22, P24, P25, D3)

**S run** (`15a-emr-size-100.json`, user decisions 2026-11-16 in `docs/agent-runs/phase-15/prompt.md`, "S run cap and D3 go-ahead"): 10,577 works (the Phase 6 slice), **120 minutes** at most (raised from 75 by the human on 2026-11-24, "Raise to 120 min", `docs/agent-runs/phase-18/human-gate.md`; the manifest `max_usd` went 0.84 -> 1.25), one **r5.xlarge primary** (`pipeline.primary_instance_type`; entity resolution runs on the primary with `PIPELINE_ER_XMX=12g`) and one **m5.xlarge core** node (`pipeline.instance_type`), no task nodes, 900 s idle auto-termination, budget USD 1.25. G6 estimate, the primary priced at its own type (`scripts/config/emr-pricing.conf`, us-east-2, retrieved 2026-11-16): (r5.xlarge 0.252 + 0.063 = 0.315/h + m5.xlarge 0.192 + 0.048 = 0.240/h) x (7,200 + 900) / 3,600 = 1.24875, rounded up to **USD 1.25** (at the former 75 minutes: 0.8325, 0.84). At 120 minutes the step timeouts (`PIPELINE_STEP_WEIGHTS`, 5/20/20/5/40/10 percent) are 6 / 24 / 24 / 6 / 48 / 12 minutes (stage-in, Hadoop, ER, class origin, Spark, copy-out); at 75 minutes they were 3.75 / 15 / 15 / 3.75 / 30 / 7.5.

**Ledger** (`check_manifests.py`): the real ledger holds three runs before S: Session 1 history 0.84 + 0.84 (reserves, USD 1.68) and the Session 2 S attempt of 2026-11-18, recorded at its measured actual **USD 0.37** (`docs/agent-runs/phase-15/evidence/session-2/emr/emr-actual-1end.log:9-10`: `measured_usd=0.37 tail_seconds=0 tail_usd=0.00`, `live_runs=3 of 4 cumulative_usd=2.05`; 1.68 + 0.37 = 2.05). The check models that history plus S 1.25 and **one S retry** 1.25 = **USD 4.55 of reserves over 5 runs** against the pins of USD 4.70 and 5 runs: **margin USD 0.15 against the reserves and 0 spare runs** (S is run 4, the retry run 5). The Session 2 attempt is a constant in the check, and the check fails if that evidence file is missing or no longer says 0.37 and 2.05. Two figures, not to be mixed: 0.15 compares reserves with the cap; the real admission rule of `scripts/lib/budget.py` (`ledger_problems`: refuse when runs >= limit or recorded + estimate > cap) counts measured actuals plus the 0.14 idle tail of a cluster still up (`release.conf:243-257`), so run 4 is admitted (2.05 + 1.25 = 3.30 <= 4.70) and run 5 only if run 4's measured cost is at most 4.70 - 2.05 - 0.14 - 1.25 = **1.26**; a run 4 measuring its full 1.25 estimate leaves a margin of **USD 0.01**, and one measuring 1.27 would be refused. The check prints both and reports `CHECK-BLOCKED` when either is negative. The human chose on 2026-11-24 (`docs/agent-runs/phase-18/human-gate.md`, "Yes, allow 1 retry") to raise the ledger so a second try is possible; the pins are `EMR_CUMULATIVE_CAP_USD` and `EMR_MAX_LIVE_RUNS` in `scripts/config/release.conf` (infra-engineer, Phase 18 package 18B; the P25 values were 3.53 and 4, from the 2026-11-16 decision "Raise cap to 3.53"). `check_manifests.py` reports `CHECK-BLOCKED` (exit 3) while the pinned cap is below 4.55 or the pinned runs below 5, or while the real-admission margin is negative (cap below 4.69). `check_manifests.py` pins S at exactly 120 minutes (`EMR_LEDGER`), so a different S cap needs a new human decision and a change to that pin; any other 15A manifest, and size L, are refused. `scripts/lib/budget.py` rounds the per-run estimate up to the cent the same way: it reserves 1.25 per S run ((0.315 + 0.240)/h x (7,200 + 900) s = 1.24875, rounded up to 1.25), the same figure as this check. Record the EMR actuals right after each S run.

**L: local evidence only.** The user dropped L on EMR on 2026-11-16 (P25 rule; `prompt.md`, "L, second size"). No EMR manifest exists for L, and `check_manifests.py` fails any 15A manifest other than the two history runs and S. The record is `inputs/15a/size-l-local-evidence.json`:

- L slice (dataset-engineer, `datasets/phase15/dblp-l-slice-manifest.v1.json`): **48,187** inproceedings of `dblp-2026-10-03`, 33 venues (the 8 S venues plus 25 candidates, at most 2,500 per venue, 2005-2026), 76,623 distinct exact author strings, 27,964,881 bytes, sha256 `7e62bb428a6ef34dd7961f337b6a2d42978d7c2cbf1c566c7ce83eac3b21ea34`, nesting check S ⊂ L PASS. L/S = 4.66 x bytes, 4.56 x records, 4.47 x authorships (203,584 / 45,587), 4.17 x coauthor pairs (489,889 / 117,425), counted from the two XML files.
- P6 local chain at L (user statement in `prompt.md`; run log `target/phase15/lanes/p6-progress.md`): Hadoop prep passes in about 132 s (131.8, 137.2 and 141.3 s in three runs); 210 works are dropped by the team limit (`OVERSIZE_TEAM`, `maxAuthorTeamSize` 16); the largest team is 79. Entity resolution runs out of memory (`java.lang.OutOfMemoryError: Java heap space`) at `-Xmx22g` after 963.5 s (about 16 min).
- Spark at L with **ER bypassed: identity pass-through (no cross-source resolution), local only, not the EMR path** (`scripts/er_identity_bypass.py`, `scripts/run_spark_bypass.py`; the unchanged Spark job, the same template; summaries `target/phase15/p6/l-bypass/spark-{S,L}/summary.json`, sha256 in the evidence record):

| | S (identity bypass) | L (identity bypass) |
|---|---|---|
| Spark wall time (local) | 459.84 s | 1,110.14 s |
| canonical works / researchers | 10,578 / 21,819 | 48,188 / 76,623 |
| all-years coauthor edges | 81,181 | 320,690 |
| all-years components / largest | 1,045 / 17,179 | 2,811 / 65,597 |
| component / k-core iterations (cap 50) | 17 / 16 | 15 / 26 |
| stages / tasks (64 partitions) | 1,984 / 27,282 | 2,000 / 32,117 |
| shuffle write | 12.57 GB | 58.59 GB |
| sidecar CSV parts / largest (cap 16 MiB) | 57 / 8,506,349 B | 231 / 8,565,999 B |
| hard invariants (pair-count mismatches, missing endpoints) | 0, 0 | 0, 0 |

  At S the identity graph has the same per-window sizes as the real-ER S run (the real S ER produced 0 researcher links and 1 work link), so the bypass is close to real at S; at L it is a disclosed approximation, not an ER result.

The one command still builds the L input tree (for local runs only) and checks it against the slice and the evidence record:

```bash
python3 -I experiments/scripts/build_l_input.py      # writes target/experiment-inputs/15a/size-l/ and size-l.subset.json; refuses an existing tree
```

Observed (`--output-root target/phase15/lanes/lane-C-l-input-check2`, 2026-11-16): exit 0, 48,187 publications, DBLP file byte-identical to the L slice, S ⊂ L rechecked on the files (10,577 keys), evidence record matches.

`maxLocalSampleRecords` (P22) is 60,000: `SampleBound` is one record budget per Hadoop job across all inputs (XML elements for DBLP, non-blank lines for JSONL). The largest input is L (at most 50,000 records by the dataset-engineer's `TARGET_MAX`; 48,187 actual) plus the three committed one-line samples (openalex 1, crossref 1, orcid 1) = 50,003 at most, rounded up to 60,000. The same prep config is uploaded for S (S needs 10,577 + 3). `check_manifests.py` fails if the bound drops below the L slice count + 3. The matching ceiling `PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS` must be at least 60,000 (infra-engineer).

Spark template (P24; used by S on EMR and by the local L runs): `inputs/15a/spark-emr-template.json` is the Phase 6 first-run config with `shufflePartitions` 64, which is the accepted 14C export config (`target/phase6-inputs/14c-runtime/spark-export.json`, sha256 `ee27421d...c1e1`) in every key except the four path keys (`/replaced-at-run-time/<key>`; `sc-render-spark-config.py` replaces them per run). The Phase 6 evidence file is not changed. The same value is used for L, because:

- executors: `spark-12-10.conf` gives 1-core, 3g executors and `PIPELINE_MAX_EXECUTORS_PER_NODE=2` with 1 core node, so at most 2 tasks run at once;
- data volume: the largest shuffle of the 64-partition S export read 865,231,386 bytes (`event-log-summary.json` of run `f6e63b4b`, stage 4177, 16 tasks after AQE coalescing, at most 60.6 MB per task); x 4.66 gives about 4.03 GB at L, so 64 partitions hold about 63 MB each before coalescing, under AQE's 64 MiB advisory size; 4 partitions would give about 1 GB per task;
- task overhead: 320 of the 2,024 S stages kept all 64 tasks (AQE does not coalesce them); S at 64 ran 27,344 tasks against 5,237 at 4 partitions (run `f02acf56`; summed stage time 517 s against 277 s locally). These counts grow with the partition count, not with the data, and the Spark step has 48 of S's 120 minutes (30 of 75 before 2026-11-24) (`PIPELINE_STEP_WEIGHTS` spark-job=40), so a proportional value (about 300) would add tens of thousands of tasks on 2 slots;
- loader cap: the Neptune CSV sidecar part count is `ceil(bytes / 8 MiB)` per dataset (`Phase7NeptuneExport`, 16 MiB hard limit), independent of `shufflePartitions`;
- comparability: S and L differ only in input data (same logical and physical Spark config).

The spark-engineer confirms these settings (P24). `componentMaxIterations` 50 and `kCoreMaxIterations` 50 fail a run when not converged (`require`); S needed 17 / 16 iterations and the identity-bypass L run 15 / 26. The local L run (1,110 s) confirms 64 partitions complete at L with all sidecar parts under the cap.

### The three sizes (real Phase 6 slice)

Source: `target/phase6-inputs/6fg-dblp/dblp.xml` (sha256 `c25a1e1a...e2ecde522`, `datasets/phase6/dblp-slice-manifest.v1.json`: 10,577 inproceedings from PODC, DISC, ICDCS, OSDI, SOSP, NSDI, EuroSys and Middleware, 2005 to 2026, DBLP 2026-10-03, CC0). It is also the input of the Phase 6 Spark run `target/phase6-runs/14c-spark-export-capped/run:f6e63b4b-d542-4a32-930c-f21f002cba76` (canonicalWorks 10,578, canonicalResearchers 21,819, allYearsEdges 81,181, activeResearchers 62,757).

Rule (deterministic and nested): per venue keep the first `ceil(n_venue x P / 100)` records in the slice's own file order; keep the original order. The 100 percent file is byte-identical to the slice (checked).

| Run | Size P | Publications | Authorships (author elements) | Distinct exact author strings | DBLP file bytes | Actual fraction |
|---|---|---|---|---|---|---|
| 1 `15a-emr-size-25` | 25 | 2,648 | 11,363 | 7,843 | 1,499,564 | 25.04 % |
| 2 `15a-emr-size-50` | 50 | 5,290 | 22,712 | 13,308 | 3,002,669 | 50.01 % |
| 3 `15a-emr-size-100` | 100 | 10,577 | 45,587 | 21,819 | 6,003,592 | 100 % |

Per-venue counts (disc, eurosys, icdcs, middleware, nsdi, osdi, podc, sosp): 25 % = 265, 333, 625, 392, 315, 166, 385, 167; 50 % = 529, 665, 1,250, 784, 629, 331, 769, 333; 100 % = 1,058, 1,329, 2,500, 1,567, 1,257, 662, 1,538, 666. These are input counts from the local files. The **author, edge and graph counts per size are outputs of each EMR run** (Hadoop counters, ER manifest, Spark `counters.json`) and are reported from the raw run output, not predicted here.

Limitations to state in the report: (1) a convenience slice with a per-venue source-order bias, not a random sample; (2) the 25 and 50 percent sets keep the venue mix but cut each venue's tail, so they are not independent samples; (3) only DBLP is scaled; the pipeline's Hadoop step also reads the committed Phase 4 `openalex`, `crossref` and `orcid` samples (unscaled) at the fixed path `datasets/samples/<source>/...`, and the committed `dblp/linked-records.xml` sample is replaced by the subset, so the cross-source linking in the committed samples is absent; (4) the Phase 6 local run read DBLP only, so EMR counts at 100 percent are comparable to it only after accounting for those extra sample inputs.

### How each input is produced (local only, no upload)

```bash
python3 -I experiments/scripts/make_dblp_subsets.py
# writes target/experiment-inputs/15a/size-{25,50,100}/datasets/samples/{dblp/linked-records.xml,openalex/works.jsonl,crossref/works.jsonl,orcid/records.jsonl}
# and target/experiment-inputs/15a/size-{25,50,100}.subset.json (counts, sha256 of every file); refuses to overwrite
```

It verifies the source against the slice manifest's sha256 and publication count and the sample files against `datasets/samples/SHA256SUMS`. Observed: counts as in the table above (exit 0).

S3 contract (reconciled with the deployer grant). Everything for 15A lives in the **artifacts** bucket under `emr/<run_prefix>/`, where `<run_prefix>` is the human's `operator_run_prefix` (`^run-[a-z0-9][a-z0-9-]{1,27}$`, for example `run-20261115`):

| Content | Location |
|---|---|
| `bin/`, `steps/` | uploaded by the infra/deploy tooling (not named in the manifests) |
| jars | `emr/<run_prefix>/jars/` : `hadoop-submit.jar`, `hadoop-bundle.jar`, `entity-resolution.jar`, `spark-job.jar` (the job JAR is a node-local path in the pipeline; only its sha256 is in the manifest) |
| config | `emr/<run_prefix>/config/` : `hadoop-config.json` (P1; the key the upload option `--hadoop-config` must write), `er-policy.json`, `er-config.json`, `spark-config-template.json` |
| input of run N | `emr/<run_prefix>/input/size-N/datasets/samples/{dblp,openalex,crossref,orcid}/...` (N = 25, 50, 100 or l; the contents of `target/experiment-inputs/15a/size-N/`; sha256 in `size-N.subset.json`) |
| outputs of run N | `s3://<artifacts>/pipeline/<run_prefix>/15a/size-N/<run-id>/...` (the `pipeline/` prefix is the one the EMR role may clean up) |
| metric exports | `s3://<artifacts>/pipeline/<run_prefix>/15a/size-N/metrics/` (cluster logs stay at the cluster `log_uri`, `s3://<logs>/emr/`) |

Inputs are not in the raw bucket and outputs are not in the reports bucket. The upload itself is a separate human-approved step and has not been done.

### Tokens in committed manifests, and the commit freeze

Committed manifests carry **tokens only**, never bucket names, because bucket names embed the AWS account id (Option A, rendering account ids into the repository, was rejected): `${SCHOLARCHAIN_ARTIFACTS_BUCKET}` and `${SCHOLARCHAIN_RUN_PREFIX}`. `scripts/run-experiment.sh` and `scripts/lib/experiment.py` resolve them at run time from the environment (infra-engineer is adding this; until it lands the validator rejects `${...}` in an `s3://` URI, so `check_manifests.py` validates a temporary copy with dummy names). The only value missing until the JARs are built is the sha256 of each artifact (all-zero in the committed form). Before the freeze the human renders the real hashes, reviews and commits:

```bash
python3 -I experiments/scripts/render_manifests.py --overwrite \
    --sha hadoop-submit-jar=<hex> --sha hadoop-libjars=<hex> --sha er-jar=<hex> --sha job-jar=<hex>
# the hadoop-config, er-policy, er-config and spark-config-template hashes come from the files in inputs/15a/config-sources.json;
# a --sha for them must equal the file; --keep-jar-shas reuses the JAR hashes already in 15a-emr-size-100.json
python3 -I experiments/scripts/check_manifests.py --final      # must print RESULT: OK (final: no placeholders)
```

`check_manifests.py` (with or without `--final`) fails a manifest that names any literal bucket (only the artifacts token is allowed) or contains a run of 12 digits outside a sha256 (a possible account id); `--final` additionally refuses all-zero hashes. A run needs the two variables in the environment, for example `SCHOLARCHAIN_ARTIFACTS_BUCKET=scholarchain-<env>-<12 digits>-artifacts`, `SCHOLARCHAIN_RUN_PREFIX=run-20261115` (set in the shell, never in a file).

### Check, then dry run, then (after approval) execute

```bash
python3 -I experiments/scripts/check_manifests.py               # offline; exit 0 ok, 1 failed, 3 blocked by a pinned ceiling
python3 -I -m unittest discover -s experiments/tests -v         # 100 tests (48 + 23 + 16 + the 13 identity-bypass tests)
# after the manifests are final and committed (dry run: no aws call, prints every EMR step; needs the cluster id of the Terraform cluster):
scripts/run-experiment.sh --manifest experiments/manifests/15a-emr-size-100.json --cluster-id <j-id>
# execute only with the approval record and pre-spend receipt (Session 2: size S, and at most one S retry):
scripts/run-experiment.sh --manifest experiments/manifests/15a-emr-size-100.json --cluster-id <j-id> --profile <profile> --approval <record> --prespend <receipt> --execute
```

Raw results of a run: `target/experiment-runs/<experiment-id>-<run>/experiment-record.json`, `experiment-result.json` and the pipeline outputs listed in the pipeline run manifest. Archive with `scripts/archive-evidence.sh`. A failed run keeps its record; rerun is a new run with a new approval record (approvals are single use), and counts against the 5-run ledger.

History (resolved for S by the 12,000 pin; for L see "Session 2" above, 60,000): `scripts/config/release.conf` pinned `PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS=1000`, and `maxLocalSampleRecords` is a whole-step record bound in `HadoopPrepMain`, so the 2,648 to 10,577 publication inputs cannot run under it. The prep config sets 12,000 (no truncation at 100 percent: 10,577 plus the small samples). `check_manifests.py` reports it as `CHECK-BLOCKED` (exit 3). With a copy of the config pinned to 12,000 the real `run-bounded-pipeline.sh` dry run for the 100 percent manifest succeeds (`ESTIMATE-USD: 0.84`, no aws call).

## Local configuration files for the EMR upload (`--hadoop-config`, `--er-policy`, `--er-config`, `--spark-config-template`)

Decision (user, 2026-11-10): use the files that already exist in the repository from the Phase 5/6 local runs; no new settings. `inputs/15a/config-sources.json` lists them and `tests/test_derive_14c_inputs.py` fails if one changes.

| Flag | Repository file | sha256 |
|---|---|---|
| `--er-policy` | `modules/entity-resolution/src/main/resources/phase5-policy.v1.json` (policy `er-offline-uncalibrated-v2`, the version in the lineage of export `f6e63b4b`) | `2d3d12e7489b18437f96b09754709100cbc3529ffd4fcfd0ff6807db87f2a93f` |
| `--er-config` | `docs/agent-runs/phase-06/evidence/6fg/local-er-config.json` (byte-identical to the ignored `target/phase6-inputs/6fg-runtime/er-config.json` of the Phase 6 run; LLM adjudication disabled) | `a07abd84cbe0e5d30b06726a73535df4c7aa51a0020d059954d9b7f9ab79832c` |
| `--spark-config-template` | `experiments/inputs/15a/spark-emr-template.json` (P24, 2026-11-16; replaces the Phase 6 first-run file `753adaec...`, whose 4 shuffle partitions gave sidecar parts above the loader cap in Session 1) | `9341c162c8b05c9496685083d5a470a77f555ee24626eb4b946a439e1fd8206a` |
| `--hadoop-config` (P1) | `experiments/inputs/15a/prep-config.json` (`maxLocalSampleRecords` 60,000, P22) | `5330214bda284c4152a700549942b40931a64994b82b19ecdd99bcadb9f1bc57` |

`render_manifests.py` hashes these four files itself and pins them in every 15A manifest; `check_manifests.py` fails a manifest whose pin differs from the file. `scripts/upload-emr-artifacts.sh` hashes the files itself, so its `EMR-RENDER` lines print these values when the four paths above are passed. Neither script takes a default path, so the paths are passed explicitly. The four path keys of the template hold `/replaced-at-run-time/<key>`, so no local path is uploaded.

## Real 14C / 15B / 16B inputs (`inputs/14c/`)

Derived once from the local, git-ignored export `target/phase6-runs/14c-spark-export-capped/run:f6e63b4b-d542-4a32-930c-f21f002cba76` by a committed, deterministic script (stdlib; no Parquet reader needed because it reads the plain-CSV Neptune sidecar; the sha256 of every file it read equals the committed `real-slice-export.sha256`):

```bash
python3 -I experiments/scripts/derive_14c_inputs.py \
    --export-dir "target/phase6-runs/14c-spark-export-capped/run:f6e63b4b-d542-4a32-930c-f21f002cba76" \
    --out-dir experiments/inputs/14c            # refuses to overwrite; --overwrite replaces; same input gives identical bytes
```

| File | Content | Used by |
|---|---|---|
| `include-ids.txt` | 40 `researcher:dblp:<hash>` IDs, sorted: every researcher named in the questions plus the smoke subject; total all-years degree 813 (budget 900) | `RuntimeArtifactMain --include-ids` (14C artifact) |
| `real-query.json` | `{"question":"Who are the direct coauthors of \"Songwu Lu\"?","output":{"includeScores":false}}` | `scripts/smoke-test.sh --query-body` |
| `questions.txt` | 40 fixed questions (14 direct coauthors, 8 component, 10 shortest path, 8 ranking), shaped after the planner's request grammar (checked by the shape test in `experiments/tests/test_derive_14c_inputs.py` and by `Phase14QuestionSetPlannerSpec` in the rag module, which loads the committed file and asserts all 40 are `Planned` through the planner's fallback, using an always-failing model client and the default runtime config) | 15B (`--questions-file`, cycled) and 16B (`eval16b.py`, each once) |
| `node-ids.txt` | 100 IDs (60 researchers, 40 works), chosen inside the include-list closure: the 40 named researchers, then their coauthors by (-degree, id), and works authored by the named researchers | `loadgen.py --node-ids-file` |
| `provenance.json` | export run id, sha256 of the 58 files read, the selection rule including the degree band 10..22 and budget 900, counts (including `include_total_degree`), sha256 and line count of every output | review |

Selection rule (full text in the script docstring): degree is the number of distinct all-years coauthors. A researcher is eligible when the display name is unique among all researcher nodes (the runtime name resolver would otherwise answer "ambiguous"), is plain ASCII letters, **and the degree is in the band 10 to 22**. The pool is the 80 highest-degree eligible researchers (ties by ID); the 22 subjects are spread over the pool; path pairs are 5 strongest direct coauthor pairs and 5 two-hop pairs. IDs, DBLP author names (CC0) and question text only.

Degree budget (why): the runtime artifact is capped at 10,000 rows and 16 MiB, and the first version of this list (hubs such as a degree-247 researcher, about 2,200 rows alone) was refused by `RuntimeArtifactMain` (`include-list-exceeds-cap`, row cap). The artifact needs about 9 to 12 rows per unit of all-years degree of each included researcher, so the script refuses to write anything when the include list's total degree passes `--degree-budget` (default 900). The committed list has total degree 813.

Offline check (experiments engineer, 2026-11-10, no AWS; output only under `target/`): `RuntimeArtifactMain --source <export> --include-ids experiments/inputs/14c/include-ids.txt --out-dir target/phase14/14c-work-check/<fresh dir>` exited 0, report status `written`, `SELECTION: rows=9643 bytes=9633173 researchers=41 (include-list=40 fill=1) includeListSha256=5d4d99a0326292221a4414b8f5533c532287f8cbbd37a9bee94e7cf86b645552`. The 40 listed researchers' closures need about 7.3 thousand rows; the degree fill then added one hub researcher (degree 247) up to the cap.

## 16B live evaluation (`load-tests/eval16b.py`)

One command asks the 40 questions of `inputs/14c/questions.txt` once each, in file order, through `POST /v1/query`, and charges bucket 16b itself (do not also run `llm_budget.py reserve --bucket 16b`; see `load-tests/README.md`). The 15B load generator uses the same file (and cycles it for its 60 answers), because one file means one include list and one artifact covers both steps; a separate 16B file would only help if the 16B set had to differ from 15B.

**Method note for the 16B report:** the runtime artifact is a bounded subset (40 listed researchers, one fill researcher, 9,643 rows), not the corpus. The ranking questions (most distinct coauthors, largest team size, strongest bridges, repeated collaborations, with their window variants) rank only the researchers included in the artifact, so their answers differ from corpus-wide ranks; the storage README states that rankings are exact only within the included population. Report them as rankings within the artifact, and compare against the artifact's own contents, not the full Phase 6 export. Direct-coauthor, component and path questions about the 40 listed researchers are answered from their complete closures.

```bash
python3 -I load-tests/eval16b.py plan                                  # no network, no key; prints the bucket state and the cost estimate
python3 -I load-tests/eval16b.py run --run-id <run-id>                 # needs SCHOLARCHAIN_LOAD_BASE_URL and SCHOLARCHAIN_LOAD_API_KEY in the shell
```

## Q12 benchmark (`load-tests/evalq12.py`, `inputs/q12/`, `manifests/q12-benchmark.json`)

The course requires a benchmark of at least 30 questions covering coauthor breadth, max team size, direct collaboration, shortest paths, components, communities, bridge researchers, temporal change, topics, institutions and evidence. User decision 2026-11-16: ask all **33** questions (3 per type) with real answers, run it after P3 and P4 are fixed, and score retrieval, claims and the answer text against the computed answer key. It runs against the **local** stack with a real Anthropic writer (key handling: the approved procedure in `docs/agent-runs/phase-15/prompt.md`; the key is only an environment variable of the one run process, shell tracing off, never a CLI argument). Nothing here has been run against a service.

**What is asked.** `inputs/q12/questions.txt` (ids `q01`..`q33` in file order, round-robin over the types with the two abstain-expected types never adjacent), derived by `scripts/derive_q12_inputs.py` from the plain-CSV sidecar of the Phase 6 export `run:ba7402d1-959a-4277-8c6e-e92878a38afa` (size S, seed `q12-v1`, selection rule in the script docstring and `provenance.json`). 27 questions are in the deterministic fallback grammar of `QueryPlannerAgent`; 6 (temporal and community comparison) need the planner LLM (`planner` field of `question-specs.json`). The researchers named in the questions, plus the middle researcher of the 3-hop path, are in `inputs/q12/include-ids.txt` (25 IDs, total all-years degree 394, below the 900 artifact budget); load them with the runtime artifact builder as for 14C.

| Type | Questions | Key |
|---|---|---|
| coauthor breadth | most distinct coauthors: all-years, since 2015, 2010-2014 | values and order (every cited value is checked against the export; top-100 recorded; the runtime ranks only its artifact population) |
| max team size | largest/maximum team size: all-years, since 2015, 2020-2026 | all-years values and order; two windowed ones bounded (the CSV has no work years) |
| direct collaboration | direct coauthors of a researcher with 28 coauthors (page of 25 truncates), one with 11, one since 2015 | exact (complete coauthor lists) |
| shortest paths | hop distance 1, 2 (since 2015), 3 | exact (BFS, up to 25 shortest paths, depth 6) |
| components | all-years giant component; through-2009 and since-2015 smaller components | exact (size, id) |
| communities | "Compare communities of X": all-years, since 2015, 2020-2026 | exact via an independent port of the synchronous label propagation |
| bridge researchers | strongest bridges (cross-community degree): all-years, since 2015, 2020-2026 | values and order via the same port |
| temporal change | "Did X change from W1 to W2?" for the three adjacent window pairs | exact except two deltas that need work years (not checked) and the community Jaccard overlap (a lower bound: the runtime also counts one-person communities of researchers with no edge in the window, Phase6FGJobs.scala:118-147, which the CSV lacks; accepted when key <= runtime <= 1) |
| topics | rankings filtered by `topic "..."` | **thin data, abstain expected** |
| institutions | rankings filtered by `institution "..."` | **thin data, abstain expected** |
| evidence | "What is the shortest path between A and B?" for a pair of direct coauthors with 2 to 5 joint works: all-years (3 joint works), since 2015 (2), 2020-2026 (2) | exact: the set and count of joint works; the answer must cite edge evidence whose `workIds` are exactly those works |

**Thin data, stated plainly.** The export has 3 TOPIC nodes (all on one work that has no AUTHORED edge), 1 INSTITUTION node and 0 AFFILIATED_WITH edges, so no researcher has authoritative topic or institution metadata; the runtime rejects a filtered ranking (`unsupported-authoritative-filter-metadata`) and must abstain. For these 6 questions a verified abstention (or an HTTP 4xx refusal, recorded as such) is the **correct** answer and the key says so; abstention is scored correct nowhere else. **Evidence type (substituted): a provenance check on a direct collaboration, asked in the shortest-path request form because the explain route needs vectors, which the local stack does not have; it scores the exact supporting works and their count, not the hop path; it is not coverage of the explain/semantic route.** In detail, evidence is defined as "the answer shows which works prove a collaboration": a 1-hop shortest path whose edge evidence carries the joint work ids (key: exactly the joint works, from the edge row's representative work ids, which for 2 to 5 joint works are exactly the joint works in every window of the real export and, all-years, equal the AUTHORED intersection of the pair). The first design used the explain / SemanticExplanation form ("Explain the research collaboration of X"), but the local stack has no vectors (Voyage keys revoked, S3 Vectors destroyed), so that form always abstains there; the grammar cannot plan 'What evidence shows that A and B collaborated?' (the word "evidence" is outside its vocabulary), so the shortest-path form without the word "coauthor" is used, which the deterministic fallback accepts. Every question is also scored on its evidence trail (cited evidence must resolve through `/v1/evidence/{id}`). The course README is not in this repository, so the type list is quoted from the user's decision, not from the README.

**How the key is computed** (`q12_answer_key.py`, helpers in `q12_graph.py`; no Parquet reader is needed). Distinct coauthors, components (union-find), BFS paths, team sizes and coauthor lists come straight from the CSV sidecar. Communities, bridges and temporal changes are Parquet-only in the export, so they are computed by an independent Python port of `modules/spark` (synchronous label propagation of job06, bridge measures, the temporal deltas of Phase6FGJobs). The port is validated against `analytics-report.json` of the same export, and the validation is replayable: `q12_answer_key.py` compares, for every one of the six windows, the largest component, the community iterations (20), the final changed count (e.g. all-years 1,349), the largest community size, the maxima of all four bridge measures and (all-years) the maximum team size, refuses to write the key on any mismatch, and records the compared values under `source.validation` of `answer-key.json` (`--skip-validation` records `skipped`). In addition the community id, component id, degree, bridge values and maximum team size of two researchers observed in the Session 1 answers (Ion Stoica, Atul Adya) are reproduced exactly. Not checked: `deltaAverageCoauthorsPerPaper` and `deltaMaximumCoauthorsOnOnePaper`.

**Ranking population.** The runtime ranks only the researchers inside its bounded artifact (include list plus degree fill), so the recorded top-100 lists are corpus-wide. The scorer checks every cited value against the export (not against the top list), the descending order inside the answer, and the name and value of the rank-1 cited researcher in the text; agreement with the corpus-wide top-1 is reported as information only.

**Run settings for the human run** (service settings, recorded with the run; the harness cannot see them): retrieval mode **graph** (the local stack has no vectors; the runtime-config default is fused, so the run overrides it). Deadlines: the primary run uses the **packaged** deadlines (planner 5,000 ms, synthesis 5,000 ms, as in the AWS deployment). A disclosed **raised** profile (planner 15,000 ms, synthesis 30,000 ms, `SCHOLARCHAIN_RUNTIME_SYNCHRONOUS_DEADLINE_MS` 60,000, service `SCHOLARCHAIN_SYNCHRONOUS_DEADLINE_MS` and `SCHOLARCHAIN_WORKFLOW_TIMEOUT_MS` 70,000) is used only if the `--only q04` probe shows planner or synthesis deadline outcomes; the run evidence records which profile was used, and a raised-profile run is reported as such. All of this is also in `manifests/q12-benchmark.json` under `run_settings`.

**Cost.** 33 answers x USD 0.001365 (`manifests/llm-allocation.json`, estimate, not metered) = **USD 0.045045 as a LOWER BOUND** from bucket 16b. After P3 and P4 (a separate rag change) the direct-coauthor and path answers carry larger evidence and may cost about 1.5 to 5 times the unit: reviewers estimate about USD 0.08 typical and about USD 0.24 worst for the 33 (not metered); the bucket count is the binding limit and the Anthropic console is the cost of record. Bucket 16b was at 0 remaining after Session 1; the human-approved transfer `APPROVED_LLM_TRANSFER=15b->16b:36` was applied (15b keeps 24), and the user decision of 2026-11-21 (option A) raised the pinned 16b base 40 -> 80 (and bucket 17 5 -> 10) so the benchmark can be rerun in full on the fixed code: the ledger adds the pinned base and its transfers, so 16b reads size 116 and `status` prints `ALLOCATION-CHANGED` (a warning; `reserve` and the harness do not check it) until the user confirms the bucket sizes; no agent creates an approval or writes the real ledger. Observed usage (local, git-ignored raw evidence; the synthesis model call only, read from explain.body.modelVersions inputTokens/outputTokens; planner-call tokens are not recorded there, so the full per-answer cost is not metered in the repository): target/experiment-runs/q12-benchmark-q12-probe-1/raw/answers.jsonl, 1 answer, 27,359 in / 264 out = about USD 0.00287 at the pinned 0.10 / 0.50 per 1M, about 2.1 times the USD 0.001365 unit; target/experiment-runs/q12-benchmark-q12-run-1/raw/answers.jsonl, 15 of the 33 answers record usage (the others record none), 129,959 in / 4,742 out, mean 8,664 in / 316 out, about USD 0.00102 per answer, about 0.75 times the unit. The cost varies with the retrieval context (up to about 27,000 input tokens). Upper bound if every answer cost like the probe: 160 x 0.0029 is about USD 0.46, under the USD 1.33 cap. The Anthropic console is the cost of record. The probe and the full run charge 34 answers in total (each question asked is charged once); the plan check of the full run needs 33 remaining, so run the probe first and the full run second. `evalq12.py run` charges bucket 16b itself before every request; do not also `reserve`. The explain and evidence fetches are GET requests and call no model. Confirm the ledger with `python3 -I load-tests/llm_budget.py status` before the run.

```bash
# derive (offline; the export is git-ignored under target/); refuses to overwrite without --overwrite
python3 -I experiments/scripts/derive_q12_inputs.py --export-dir "<spark export dir>" --out-dir experiments/inputs/q12 --overwrite
python3 -I experiments/scripts/q12_answer_key.py --export-dir "<spark export dir>" --specs experiments/inputs/q12/question-specs.json --out experiments/inputs/q12/answer-key.json --overwrite
# after a re-derive, put the sha256 of questions.txt into manifests/q12-benchmark.json (questions.sha256); evalq12.py refuses a file that does not match it
python3 -I load-tests/evalq12.py plan                                  # no network, no key; bucket state and the USD 0.045045 lower-bound estimate
set +x
# a one-question probe first (one ledger answer): q04 is the 28-coauthor direct question, a 25-row page, to check the 5 s synthesis deadline
python3 -I load-tests/evalq12.py run --only q04 --run-id <probe-run-id>
python3 -I load-tests/evalq12.py run --run-id <run-id>                 # SCHOLARCHAIN_LOAD_BASE_URL (loopback host only) and SCHOLARCHAIN_LOAD_API_KEY in the shell; before the first charge it GETs /v1/graph/nodes/{id} for every include ID and refuses if the running artifact lacks one
python3 -I experiments/scripts/q12_score.py --key experiments/inputs/q12/answer-key.json --raw target/experiment-runs/q12-benchmark-<run-id>/raw --export-dir "<spark export dir>" --out-json <scores.json> --out-md <scores.md>   # --export-dir is required (or --allow-shallow: labelled SHALLOW)
```

**Scoring** (`q12_score.py`; per question three pass/fail scores with the reasons, a per-type summary, JSON and Markdown). (i) retrieval: every evidence id cited by the claims or by `/v1/explain` resolves, the evidence names the required researchers and has the required kind, and every cited value is correct (with `--export-dir`: distinct coauthors, weighted degree, component and community ids, bridge measures, team sizes and max-team works, coauthor lists, path edges and shortestness, community members, temporal deltas; without it only the key-level checks run and the output says so). (ii) claims: attempted, verified and rejected from `/v1/explain`; passes when at least one claim was attempted, none rejected, all verified, and every verified claim's values match the key or the export. Totals are reported separately: the headline is the 27 answer-expected questions; the 6 abstain-expected questions are scored on exactly an HTTP 200 ABSTAINED answer or an HTTP 422 whose recorded closed error code is `UNSUPPORTED_QUERY` (any other 4xx, a 429 for example, or a 5xx is an error, never an abstention; the harness records only the closed error code of a 4xx body, and treats an expected 422 as neutral for its consecutive-failure stop (outcome `expected_refusal`, counted under that name in the run record)). Evidence not fetched because of the 60-id cap or too large to store is counted as unverified, not as unresolved. (iii) text: the answer's `summary` and `uncertainty` contain the key facts (numbers with or without thousands separators and in absolute value, a component answer by size or by id, researcher names with or without a DBLP homonym suffix, the hop count as a digit or a word with the interior names of a shortest path, the rank-1 name and value for rankings). A question passes only if all three pass. The raw run is `answers.jsonl` (answer, explain body and every cited evidence item per question), sealed with `raw.sha256`; the scorer is deterministic and can be re-run.

## 15B: ECS scale-out and scale-in on query-api

`manifests/15b-ecs-scaling.json` is driven by `load-tests/loadgen.py` (see `load-tests/README.md`). Phases: baseline at concurrency 1 (120 s), 5 (120 s), 25 (150 s), 50 (180 s), a 10-minute hold at 50 (up to 150,000 requests, no LLM calls), then 30 minutes with no load for the scale-in. The service scales on `ECSServiceAverageCPUUtilization` (target `cpu_target_percent`, default 60; scale-out cooldown 60 s, scale-in cooldown 300 s; min 1, max 2 tasks in the example tfvars; Fargate 0.25 vCPU / 1 GiB). AWS target tracking scales out after three one-minute datapoints above the target and scales in only after 15 consecutive minutes below 90 percent of it, which is why the observation window is 30 minutes.

```bash
python3 -I experiments/scripts/check_manifests.py
python3 -I load-tests/loadgen.py plan --manifest experiments/manifests/15b-ecs-scaling.json
# after the approval record, with SCHOLARCHAIN_LOAD_BASE_URL and SCHOLARCHAIN_LOAD_API_KEY set in the shell:
python3 -I load-tests/loadgen.py run --manifest experiments/manifests/15b-ecs-scaling.json --run-id <run-id> --node-ids-file <node-ids.txt>
```

Metric collection (not part of loadgen; run in a second terminal during the experiment and again afterwards; **unverified, never run**; replace the names, keep UTC):

```bash
aws ecs describe-services --region <region> --cluster <cluster> --services query-api --query 'services[0].[desiredCount,runningCount,pendingCount]' --output text   # poll every 60 s, prefix each line with date -u
aws application-autoscaling describe-scaling-activities --region <region> --service-namespace ecs --resource-id service/<cluster>/query-api
aws cloudwatch get-metric-statistics --region <region> --namespace AWS/ECS --metric-name CPUUtilization --dimensions Name=ClusterName,Value=<cluster> Name=ServiceName,Value=query-api --start-time <UTC> --end-time <UTC> --period 60 --statistics Average Maximum
aws cloudwatch get-metric-statistics --region <region> --namespace AWS/ApplicationELB --metric-name HealthyHostCount --dimensions Name=LoadBalancer,Value=<lb> Name=TargetGroup,Value=<tg> --start-time <UTC> --end-time <UTC> --period 60 --statistics Minimum Maximum
```

Container Insights is off, so `AWS/ECS RunningTaskCount` does not exist: the task count over time comes from the `describe-services` poll, the ALB `HealthyHostCount` and the scaling activity history. The loadgen `derived/timeline.csv` has one row per UTC minute for lining up.

Risks stated up front: scale-out happens only if CPU exceeds the target; if non-LLM routes at concurrency 50 do not push 0.25 vCPU past 60 percent, report the CPU values and that no scale-out occurred, rather than changing the service or target inside the run (a different target is a new run). Node IDs for the graph routes must come from the loaded 14C graph.

### 15B semantic variant (P42, R-b load)

`manifests/15b-ecs-scaling-semantic.json` drives `POST /v1/semantic/retrieve` (the P40 public route; API key in `Authorization: Bearer`, body `{"question": ..., "topK": 10}`) instead of the graph routes, so every request does real work against S3 Vectors without Neptune. Phases: **warm-up** (level 1, one pass over the 150 questions, at most 200 requests, its own phase so cold-cache latency stays out of the level-1 baseline), baseline at 1 (120 s), 5 (120 s), 25 (150 s), 50 (180 s), the hold at 50 (600 s), then 30 quiet minutes (at least 25 are required).

- **Required per-level request limits (user answer Q16, 2026-11-15): 600 / 3,000 / 15,000 / 30,000 / 150,000, 198,600 in total, plus the warm-up of at most 200.** They are the S3 Vectors cost bound of R-b (plan section 6.3a) and must not be raised. `loadgen.py` (`validate-manifest`, `plan`, `run`) and `check_manifests.py` refuse a manifest above them; the committed manifest must carry exactly these values. A 429 reply counts toward its phase limit.
- **Questions** (`inputs/15b/semantic-questions.txt`): 150 distinct topic phrases (two or three words, such as "leader election" or "serverless computing") taken from the titles of the Phase 6 DBLP slice (dblp-2026-10-03, 10,577 inproceedings, CC0; sha256 `c25a1e1a0d51...` as recorded in `datasets/phase6/dblp-slice-manifest.v1.json`). Rule: lowercase title words, stop and generic words break a phrase, 2- and 3-word windows counted once per title, document frequency at least 5, ranked by (frequency, words, text), fragments of a longer topic and plural duplicates skipped. `inputs/15b/semantic-questions.provenance.json` holds the source sha256, the rule, the counts and the title count of every phrase; `python3 -I experiments/scripts/derive_semantic_questions.py --out-dir <dir>` reproduces both files byte for byte from the (git-ignored) slice at `target/phase6-inputs/6fg-dblp/dblp.xml`. The manifest pins the questions file by sha256 and count; `loadgen.py` refuses a different file.
- **Route weights** (`load-tests/config/load-profile.v1.json`): semantic 40 against healthz 2, readyz 1, metrics 1 (90.9 percent semantic with no ID files, 74.1 percent with both ID files). `/readyz` fans out to graph-service and semantic-service probes, so a few thousand `/readyz` calls reach Neptune and S3 Vectors `GetVectors` probes in R-b. The S3 Vectors `GetVectors` pricing is unverified (this repository does not pin a per-request price); the cost is bounded and small, about 4,500 calls. `/readyz` stays in the semantic mix by the coordinator's recorded default.
- **429 replies** are counted per level (`rate_limited_429` in `summary.json`, `summary.csv`, `timeline.csv`, the run record and a `RATE-LIMITED-429:` console line per phase) and excluded from latency, `throughput_rps`, `success_rps` and the error rates. `success_rps` (2xx over the phase window), `success_rps_active` (2xx over the span in which requests were sent, because a phase that reaches its limit early sends nothing afterwards) and `peak_success_rps_1s` are the served rates P35 derives `query_requests_per_target_target` and `r_S2` from.
- Voyage calls: at most the distinct questions per semantic-service task (query-embedding cache); the figure for the R-b window comes from the Voyage usage page after the session (plan review finding R2), not from this process.

```bash
python3 -I experiments/scripts/check_manifests.py
python3 -I load-tests/loadgen.py plan --manifest experiments/manifests/15b-ecs-scaling-semantic.json --questions-file experiments/inputs/15b/semantic-questions.txt
# R-b (after the approval record; no --node-ids-file, --evidence-ids-file or --llm):
python3 -I load-tests/loadgen.py run --manifest experiments/manifests/15b-ecs-scaling-semantic.json --questions-file experiments/inputs/15b/semantic-questions.txt --run-id <run-id>
# P35 rehearsal against the local query-api (loopback http; same phases, quiet window shortened; the flag can only lower it):
python3 -I load-tests/loadgen.py run --manifest experiments/manifests/15b-ecs-scaling-semantic.json --questions-file experiments/inputs/15b/semantic-questions.txt --run-id <rehearsal-id> --base-url http://127.0.0.1:<port> --observe-seconds 30
```

### LLM answer buckets (opt-in; shared cap USD 1.33)

User decision 2026-11-08, with 16b and 17 raised by the user decision of 2026-11-21 (option A: the Q12 benchmark rerun of 33 questions + 1 probe, and room for the Phase 17 demo): **14c 10 / 15b 60 / 16b 80 (was 40) / 17 (demo and final smoke) 10 (was 5) = 160 answers (was 115)**, pinned in `manifests/llm-allocation.json` (schema v2). Each bucket is a hard stop. Synthesis runs on **claude-haiku-5-5 through the Anthropic API** (repair round 3, 2026-11-09; the instructor approved the Anthropic API and Voyage AI given the Bedrock quota restriction; the Bedrock route `us.anthropic.claude-haiku-4-5-20251001-v1:0` stays the selectable fallback). Price USD 0.10 input / 0.50 output per 1M tokens for prompts under 100,000 tokens (Anthropic pricing page, 2026-11-09); tokens per answer raised 30% (planner 1,950 in + 260 out, synthesis 5,200 in + 1,040 out), so **USD 0.001365 per answer** (was USD 0.01155 at the Bedrock 1.10 / 5.50 rates). The shared cap **stays USD 1.33** (user decision, easiest option; it was lowered from USD 1.50 on 2026-11-09 for the H0 pre-spend receipt, which reserves the full caps): 160 x 0.001365 = 0.2184 (115 x 0.001365 = 0.156975 before 2026-11-21), so USD 1.33 is a conservative upper bound and the bucket counts are the binding limit. Spare allowance moves between buckets only with the user's approval file (`llm_budget.py transfer`). These are estimates, not metered.

| Bucket | Answers | Estimated USD | Step |
|---|---|---|---|
| 14c | 10 | 0.01365 | Phase 14C smoke query |
| 15b | 60 (10 / 15 / 20 / 15 at concurrency 1 / 5 / 25 / 50; none in the hold) | 0.0819 | load generator, charged per call |
| 16b | 80 | 0.1092 | 16B live evaluation (placeholder) and the Q12 benchmark rerun (34 answers) |
| 17 | 10 | 0.01365 | demo video and final smoke |
| Total allocated | 160 | 0.2184 | |
| Unused cap headroom | | 1.1116 | cap 1.33 minus allocated |

Observed usage (local, git-ignored raw evidence; the synthesis model call only, read from explain.body.modelVersions inputTokens/outputTokens; planner-call tokens are not recorded there, so the full per-answer cost is not metered in the repository): target/experiment-runs/q12-benchmark-q12-probe-1/raw/answers.jsonl, 1 answer, 27,359 in / 264 out = about USD 0.00287 at the pinned 0.10 / 0.50 per 1M, about 2.1 times the USD 0.001365 unit; target/experiment-runs/q12-benchmark-q12-run-1/raw/answers.jsonl, 15 of the 33 answers record usage (the others record none), 129,959 in / 4,742 out, mean 8,664 in / 316 out, about USD 0.00102 per answer, about 0.75 times the unit. The cost varies with the retrieval context (up to about 27,000 input tokens). Upper bound if every answer cost like the probe: 160 x 0.0029 is about USD 0.46, under the USD 1.33 cap. The Anthropic console is the cost of record. The ledger keeps the pinned unit USD 0.001365. The ledger records the sha256 of the allocation file at init, so after this edit `llm_budget.py status` prints `ALLOCATION-CHANGED` (a warning only): bucket sizes are the pinned base plus the ledger's transfers, so with the earlier 15b->16b transfer of 36 the effective sizes are 15b 24 and 16b 116.

### Embeddings (Voyage voyage-4-lite; 14C and 16B)

14C ingest and query smoke and the 16B evaluation embed with Voyage `voyage-4-lite` at 256 dimensions (`input_type` document for ingest, query for queries; stored and query vectors must share provider, model and dimension, and changing the model needs a full re-embed and an index rebuild). Price USD 0.02 per 1M tokens, the first 200M account tokens free (Voyage docs, 2026-11-09). **Embeddings cap USD 0.30, enforced with a token counter** by the embedding step (this repository's experiments only pin the numbers in `load-tests/config/load-profile.v1.json` and check them in `check_manifests.py`; `llm_budget.embedding_cost()` derives the charge). Inside the free allowance the charge is USD 0 and the token usage is still recorded. The Bedrock fallback is Titan Text Embeddings V2 (`SCHOLARCHAIN_EMBEDDING_PROVIDER=bedrock`).

### Cost reporting for experiment outputs

Every experiment result reports **AWS, Anthropic and Voyage as separate items, then the combined total** (this is what the instructor ruling requires; external charges count toward the USD 25 project limit). A provider with no charge is listed as USD 0 with its usage noted. `loadgen.py` writes `cost_report` into the 15B run record; the AWS item comes from the AWS bill and the pre-spend receipts, never from the generator.

`python3 -I load-tests/llm_budget.py reserve --bucket <b> --answers N` must run before every LLM-calling command (commands and rules in `load-tests/README.md`). 16B is a placeholder: `manifests/16b-live-evaluation.json` fixes only its answer budget; the benchmark, modes and metrics come from the Phase 16 work order.

## Phase 16 evaluation (groups 1, 2 and 4: entity resolution, graph correctness, answer quality)

Offline only: every number comes from a committed script that reads raw evidence which already existed (no network, no AWS, no model call, no spend). Stdlib only, run as `python3 -I`, deterministic (sorted keys, fixed seeds), so a rerun gives identical bytes. The table below describes groups 1, 2 and 4 (instance A); groups 3, 5, 6 and 7 are written by the other experiment-engineer instance and are described in the instance B paragraph at the end of this section. The write-up is `docs/report/evaluation.md` (documentation-engineer). A metric without raw evidence is reported as a GAP with its reason, never estimated.

| Group | Script | Reads | Writes |
|---|---|---|---|
| 1 entity resolution | `scripts/eval16_identity.py` | the Phase 5E queue, labels, predictions and exclusions under `docs/agent-runs/phase-05/` and `datasets/entity-resolution/`; the 5E evaluator outputs only as a cross-check | `results/phase16/identity/identity-metrics.{json,md}` |
| 2 graph correctness | `scripts/eval16_graph.py --export-dir <spark export dir of run ba7402d1>` | the plain-CSV Neptune sidecar of the S export (`target/`, git-ignored; streamed), the Spark job's own counters and load manifest as a cross-check, the Spark test sources (listed, not run) | `results/phase16/graph/graph-correctness.{json,md}` |
| 4 answer quality | `scripts/eval16_answers.py freeze`, then `run --export-dir <same export>` | the raw Q12 and 16B runs under `target/experiment-runs/` (frozen first), `inputs/q12/answer-key.json`, `scripts/q12_score.py` (unchanged) | `results/phase16/q12-raw/` (frozen copies, `SHA256SUMS`, `freeze-report.json`), `results/phase16/answers/` (scorer outputs, `answer-quality.{json,md}`) |
| manifest | `scripts/eval16_answers.py manifest --run-date YYYY-MM-DD` | the files above | `manifests/16-evaluation.json` (inputs, scripts and outputs with sha256), verified by `scripts/check_manifests.py` |

```
python3 -I experiments/scripts/eval16_identity.py
python3 -I experiments/scripts/eval16_graph.py --export-dir "target/phase15/p6/size-S/run:ba7402d1-959a-4277-8c6e-e92878a38afa/spark"
python3 -I experiments/scripts/eval16_answers.py freeze      # once: copies the five raw runs read-only after a secret-pattern scan; never overwrites a different file
python3 -I experiments/scripts/eval16_answers.py run --export-dir "target/phase15/p6/size-S/run:ba7402d1-959a-4277-8c6e-e92878a38afa/spark"
python3 -I experiments/scripts/eval16_answers.py manifest --run-date 2026-11-21
python3 -I experiments/scripts/check_manifests.py            # includes the 16-evaluation.json check: offline scope, no account id, sha256 of every tracked file
python3 -I -m unittest discover -s experiments/tests         # includes tests/test_eval16_a.py
```

Method notes. Proportions carry Wilson 95% intervals (F1 carries a seeded percentile bootstrap interval). Each result file has separate sections for measured facts, the cross-check against numbers recorded elsewhere (a cross-check, never a source), threats to validity and missing data, gaps, and interpretation. The frozen raw copies are the only input of the Q12 scoring and of every answer-quality number; the originals stay under `target/experiment-runs/` (untracked). Run-1 and run-2 of Q12 ran different code (two commits), so they are a before/after pair and not repeats: variability across repeats is unmeasured. The Anthropic Console figure (USD 0.08 for key CS441-key, 2026-11-20 and 2026-11-21 UTC only, as of 2026-11-21 23:33 UTC) is a user-supplied screenshot value recorded as the cost of record for that key; the earlier-phase Anthropic spend (Session 1 16B and 14C, another key; project ledger USD 0.075075) is a separately scoped figure with its own source. The token-derived figure covers synthesis calls only, at the rates read from `load-tests/config/load-profile.v1.json` (its sha256 is recorded in the result).

`manifests/16-evaluation.json` covers the whole Phase 16 package: the scripts, test files and every result file of all seven groups with sha256 (only `results/phase16/reproducibility/regeneration-check.log` is excluded and declared in `excluded_outputs`, because instance B refreshes it after each verify run). Its `inputs` list enumerates only the inputs of groups 1, 2 and 4; the raw inputs of groups 3, 5, 6 and 7 are read by instance B's scripts and are not enumerated in the manifest (each result file names what it read). `check_manifests.py` fails an entry without a sha256 and a result file that is neither listed nor declared excluded.

The frozen run records (`results/phase16/q12-raw/*/run-record.json`) contain `ledger_path` with a local home-directory prefix. The copies are kept byte-identical to the originals (coordinator decision); `q12-raw/freeze-report.json` records this and the computed counts (no e-mail-like string, no standalone 12-digit run). `freeze-report.json` keeps the first-freeze record (`first_freeze`) written once; a later `freeze` only rewrites `last_invocation`. The first-freeze time was recovered from the earliest file mtime of the frozen copies because the original record had been overwritten, and says so.

**Phase 16 groups 3, 5, 6, 7 (instance B).** Offline, stdlib, `python3 -I`; every number is recomputed from raw evidence and every table says whether it is measured or a GAP.
- `eval16_perf.py` writes `results/phase16/performance/` (throughput, nearest-rank p50/p95/p99, errors by level for the AWS ECS run `rb-20261118` and the local Docker P35 run, ECS poll brackets, stop-task recovery, EMR step times, local P6 chain, LLM answer latency and token cost, vector ingest). It needs the git-ignored `target/experiment-runs/15b-*` raw files; exit 3 if absent.
- `eval16_factory.py` writes `results/phase16/factory/` (verdicts, first-pass acceptance, findings by severity, repair rounds, BLOCKED-ON, guard blocks, with file:line for every item). The coordinator-notes tables read the first 199 lines of the git-ignored notes log.
- `eval16_retrieval.py` writes `results/phase16/retrieval/`. P@K, MRR and nDCG for the Q12 ranking questions against the answer key; scorer pass rates with Wilson intervals; vector-only and fused retrieval are GAPs (no labels, stack destroyed).
- `eval16_repro.py` writes `results/phase16/reproducibility/`; `--verify` regenerates every `eval16_*` table into a temporary directory and prints PASS, FAIL or SKIP per file against the committed copy. A fresh-clone build is pending (Phase 17).
- Tests: `python3 -I -m unittest discover -s experiments/tests -p test_eval16_b.py`.
