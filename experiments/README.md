# experiments

Phase 15 experiment definitions (owner: experiment-engineer). Nothing here has been run on AWS; no upload, no cloud call and no spend has happened. Every live run needs the human approval record (`docs/agent-runs/phase-15/human-gate.md` per `RUN_APPROVAL_RECORD_PATH`) and, for EMR, the pre-spend receipt.

Run all commands from the repository root with `python3 -I`.

## Contents

| Path | Purpose |
|---|---|
| `manifests/15a-emr-size-{25,50,100}.json` | the three EMR runs; schema `scholarchain.experiment-manifest.v1`, accepted by `scripts/run-experiment.sh` |
| `manifests/15b-ecs-scaling.json` | query-api scale-out / scale-in driven by `load-tests/loadgen.py`; schema `scholarchain.load-experiment-manifest.v1` (run-experiment.sh is EMR-only and cannot take it) |
| `manifests/16b-live-evaluation.json` | 16B placeholder: the LLM answer budget, the Voyage embeddings allowance, their tie to the shared claude-haiku-5-5 cap and the command (`load-tests/eval16b.py`) that asks the 40 questions |
| `manifests/llm-allocation.json` | proposed split of the USD 1.33 claude-haiku-5-5 (Anthropic API) cap across 14C, 15B and 16B |
| `inputs/15a/prep-config.json`, `datasets.json` | the Hadoop prep config and the dataset snapshot manifest the 15A manifests name |
| `inputs/15a/config-sources.json` | the repository files used for `--er-policy`, `--er-config`, `--spark-config-template` (paths and sha256; item 1 of the 14B pre-session list) |
| `inputs/14c/` | the real include list, smoke body, 40 questions and node IDs derived from export `f6e63b4b`, with a provenance file |
| `scripts/derive_14c_inputs.py` | derives `inputs/14c/` from the local Phase 6 export (deterministic) |
| `scripts/make_dblp_subsets.py` | builds the three input trees locally from the real Phase 6 slice |
| `scripts/render_manifests.py` | renders the 15A manifests (tokens for buckets and run prefix; real artifact hashes) |
| `scripts/check_manifests.py` | offline validation of every manifest and the cost arithmetic |
| `tests/test_experiments.py`, `tests/test_derive_14c_inputs.py` | 28 + 23 tests |

## 15A: three EMR runs at three dataset sizes

One run per size, each on 1 primary + 1 core `m5.xlarge` (capacity 2), 90 minutes of cluster time at most, 900 s idle auto-termination. G6 estimate per run = 2 x (0.192 + 0.048) x (5,400 + 900) / 3,600 = **USD 0.84**; three runs **USD 2.52** against the USD 2.52 cumulative cap (`EMR_CUMULATIVE_CAP_USD=2.52` in `scripts/config/release.conf`, human decision 2026-11-09 "caps = planned use", 3 runs x 0.84, so no headroom) and 3 live runs (`EMR_MAX_LIVE_RUNS`). The same number comes out of the real `run-bounded-pipeline.sh` dry run (`ESTIMATE-USD: 0.84`). EMR capacity is fixed per run: a node-level scale-out would need `max_task_count` above 0 (3 nodes = USD 1.26; 0.84 + 0.84 + 1.26 = 2.94 > 2.52, so `budget.py` would refuse a node-level scale-out, which needs a recorded human cap decision first); the default shows Spark executor scaling only and the report must say so if no capacity change occurs.

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
| config | `emr/<run_prefix>/config/` : `er-policy.json`, `er-config.json`, `spark-config-template.json` |
| input of run N | `emr/<run_prefix>/input/size-N/datasets/samples/{dblp,openalex,crossref,orcid}/...` (the contents of `target/experiment-inputs/15a/size-N/`; sha256 in `size-N.subset.json`) |
| outputs of run N | `s3://<artifacts>/pipeline/<run_prefix>/15a/size-N/<run-id>/...` (the `pipeline/` prefix is the one the EMR role may clean up) |
| metric exports | `s3://<artifacts>/pipeline/<run_prefix>/15a/size-N/metrics/` (cluster logs stay at the cluster `log_uri`, `s3://<logs>/emr/`) |

Inputs are not in the raw bucket and outputs are not in the reports bucket. The upload itself is a separate human-approved step and has not been done.

### Tokens in committed manifests, and the commit freeze

Committed manifests carry **tokens only**, never bucket names, because bucket names embed the AWS account id (Option A, rendering account ids into the repository, was rejected): `${SCHOLARCHAIN_ARTIFACTS_BUCKET}` and `${SCHOLARCHAIN_RUN_PREFIX}`. `scripts/run-experiment.sh` and `scripts/lib/experiment.py` resolve them at run time from the environment (infra-engineer is adding this; until it lands the validator rejects `${...}` in an `s3://` URI, so `check_manifests.py` validates a temporary copy with dummy names). The only value missing until the JARs are built is the sha256 of each artifact (all-zero in the committed form). Before the freeze the human renders the real hashes, reviews and commits:

```bash
python3 -I experiments/scripts/render_manifests.py --overwrite \
    --sha hadoop-submit-jar=<hex> --sha hadoop-libjars=<hex> --sha er-jar=<hex> --sha job-jar=<hex> \
    --sha er-policy=<hex> --sha er-config=<hex> --sha spark-config-template=<hex>
python3 -I experiments/scripts/check_manifests.py --final      # must print RESULT: OK (final: no placeholders)
```

`check_manifests.py` (with or without `--final`) fails a manifest that names any literal bucket (only the artifacts token is allowed) or contains a run of 12 digits outside a sha256 (a possible account id); `--final` additionally refuses all-zero hashes. A run needs the two variables in the environment, for example `SCHOLARCHAIN_ARTIFACTS_BUCKET=scholarchain-<env>-<12 digits>-artifacts`, `SCHOLARCHAIN_RUN_PREFIX=run-20261115` (set in the shell, never in a file).

### Check, then dry run, then (after approval) execute

```bash
python3 -I experiments/scripts/check_manifests.py               # offline; exit 0 ok, 1 failed, 3 blocked by a pinned ceiling
python3 -I -m unittest discover -s experiments/tests -v         # 51 tests
# after the manifests are final and committed (dry run: no aws call, prints every EMR step; needs the cluster id of the Terraform cluster):
scripts/run-experiment.sh --manifest experiments/manifests/15a-emr-size-25.json --cluster-id <j-id>
# execute only with the approval record and pre-spend receipt, one run at a time, in order 25, 50, 100:
scripts/run-experiment.sh --manifest experiments/manifests/15a-emr-size-25.json --cluster-id <j-id> --profile <profile> --approval <record> --prespend <receipt> --execute
```

Raw results of a run: `target/experiment-runs/<experiment-id>-<run>/experiment-record.json`, `experiment-result.json` and the pipeline outputs listed in the pipeline run manifest. Archive with `scripts/archive-evidence.sh`. A failed run keeps its record; rerun is a new run with a new approval record (approvals are single use), and counts against the 3-run ledger.

Known blocker (owner infra-engineer): `scripts/config/release.conf` pins `PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS=1000`, and `maxLocalSampleRecords` is a whole-step record bound in `HadoopPrepMain`, so the 2,648 to 10,577 publication inputs cannot run under it. The prep config sets 12,000 (no truncation at 100 percent: 10,577 plus the small samples). `check_manifests.py` reports it as `CHECK-BLOCKED` (exit 3). With a copy of the config pinned to 12,000 the real `run-bounded-pipeline.sh` dry run for the 100 percent manifest succeeds (`ESTIMATE-USD: 0.84`, no aws call).

## Local configuration files for the EMR upload (`--er-policy`, `--er-config`, `--spark-config-template`)

Decision (user, 2026-11-10): use the files that already exist in the repository from the Phase 5/6 local runs; no new settings. `inputs/15a/config-sources.json` lists them and `tests/test_derive_14c_inputs.py` fails if one changes.

| Flag | Repository file | sha256 |
|---|---|---|
| `--er-policy` | `modules/entity-resolution/src/main/resources/phase5-policy.v1.json` (policy `er-offline-uncalibrated-v2`, the version in the lineage of export `f6e63b4b`) | `2d3d12e7489b18437f96b09754709100cbc3529ffd4fcfd0ff6807db87f2a93f` |
| `--er-config` | `docs/agent-runs/phase-06/evidence/6fg/local-er-config.json` (byte-identical to the ignored `target/phase6-inputs/6fg-runtime/er-config.json` of the Phase 6 run; LLM adjudication disabled) | `a07abd84cbe0e5d30b06726a73535df4c7aa51a0020d059954d9b7f9ab79832c` |
| `--spark-config-template` | `docs/agent-runs/phase-06/evidence/6fg/local-spark-first-config.json` (byte-identical to the ignored `target/phase6-inputs/6fg-runtime/spark-first.json`; `sc-render-spark-config.py` replaces its four path keys per run) | `753adaeccd524d4fdfa6028bb0a7af6394e461021dfb013587a87c24eafcf458` |

The same three values are the `--sha er-policy=`, `--sha er-config=` and `--sha spark-config-template=` arguments of `render_manifests.py`. `scripts/upload-emr-artifacts.sh` hashes the files itself, so its `EMR-RENDER` lines print these values when the three paths above are passed. Neither script takes a default path, so the paths are passed explicitly. Limitations: the template is the Phase 6 first-run config (4 shuffle partitions, local paths in the four replaced keys, which are uploaded to the artifacts bucket as text); the 14C export used a derived config with 64 shuffle partitions that is git-ignored and not part of this decision.

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

### LLM answer buckets (opt-in; shared cap USD 1.33)

User decision 2026-11-08: **14c 10 / 15b 60 / 16b 40 / 17 (demo and final smoke) 5 = 115 answers**, pinned in `manifests/llm-allocation.json` (schema v2). Each bucket is a hard stop. Synthesis runs on **claude-haiku-5-5 through the Anthropic API** (repair round 3, 2026-11-09; the instructor approved the Anthropic API and Voyage AI given the Bedrock quota restriction; the Bedrock route `us.anthropic.claude-haiku-4-5-20251001-v1:0` stays the selectable fallback). Price USD 0.10 input / 0.50 output per 1M tokens for prompts under 100,000 tokens (Anthropic pricing page, 2026-11-09); tokens per answer raised 30% (planner 1,950 in + 260 out, synthesis 5,200 in + 1,040 out), so **USD 0.001365 per answer** (was USD 0.01155 at the Bedrock 1.10 / 5.50 rates). The shared cap **stays USD 1.33** (user decision, easiest option; it was lowered from USD 1.50 on 2026-11-09 for the H0 pre-spend receipt, which reserves the full caps): 115 x 0.001365 = 0.156975, so USD 1.33 is now a conservative upper bound and the bucket counts are the binding limit. Spare allowance moves between buckets only with the user's approval file (`llm_budget.py transfer`). These are estimates, not metered.

| Bucket | Answers | Estimated USD | Step |
|---|---|---|---|
| 14c | 10 | 0.01365 | Phase 14C smoke query |
| 15b | 60 (10 / 15 / 20 / 15 at concurrency 1 / 5 / 25 / 50; none in the hold) | 0.0819 | load generator, charged per call |
| 16b | 40 | 0.0546 | 16B live evaluation (placeholder) |
| 17 | 5 | 0.006825 | demo video and final smoke |
| Total allocated | 115 | 0.156975 | |
| Unused cap headroom | | 1.173025 | cap 1.33 minus allocated |

### Embeddings (Voyage voyage-4-lite; 14C and 16B)

14C ingest and query smoke and the 16B evaluation embed with Voyage `voyage-4-lite` at 256 dimensions (`input_type` document for ingest, query for queries; stored and query vectors must share provider, model and dimension, and changing the model needs a full re-embed and an index rebuild). Price USD 0.02 per 1M tokens, the first 200M account tokens free (Voyage docs, 2026-11-09). **Embeddings cap USD 0.30, enforced with a token counter** by the embedding step (this repository's experiments only pin the numbers in `load-tests/config/load-profile.v1.json` and check them in `check_manifests.py`; `llm_budget.embedding_cost()` derives the charge). Inside the free allowance the charge is USD 0 and the token usage is still recorded. The Bedrock fallback is Titan Text Embeddings V2 (`SCHOLARCHAIN_EMBEDDING_PROVIDER=bedrock`).

### Cost reporting for experiment outputs

Every experiment result reports **AWS, Anthropic and Voyage as separate items, then the combined total** (this is what the instructor ruling requires; external charges count toward the USD 25 project limit). A provider with no charge is listed as USD 0 with its usage noted. `loadgen.py` writes `cost_report` into the 15B run record; the AWS item comes from the AWS bill and the pre-spend receipts, never from the generator.

`python3 -I load-tests/llm_budget.py reserve --bucket <b> --answers N` must run before every LLM-calling command (commands and rules in `load-tests/README.md`). 16B is a placeholder: `manifests/16b-live-evaluation.json` fixes only its answer budget; the benchmark, modes and metrics come from the Phase 16 work order.
