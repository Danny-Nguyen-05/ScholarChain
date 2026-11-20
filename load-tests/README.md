# load-tests

`loadgen.py` is the Phase 15 query-load generator (experiment D / 15B); `eval16b.py` is the Phase 16B live-evaluation runner (bucket 16b). Python 3 standard library only, no install step. Owner: experiment-engineer. It has **not** been run against the deployed stack; its tests use a fake query-api on `127.0.0.1`.

`evalq12.py` is the Q12 benchmark runner (33 questions, bucket 16b): a parameterised variant of `eval16b.py` (same plan/run commands, hard stops and ledger charging) that also fetches `/v1/explain/{queryId}` and every cited `/v1/evidence/{id}` (GET only, at most 60 per question) and keeps the raw responses in `answers.jsonl` for `experiments/scripts/q12_score.py`. It refuses a questions file that differs from the sha256 pinned in `experiments/manifests/q12-benchmark.json`. See "Q12 benchmark" in `experiments/README.md`; tests: `tests/test_evalq12.py` (fake query-api on `127.0.0.1`, never run against a service).

Run everything from the repository root with `python3 -I` (isolated mode).

## What it does

- Drives `query-api` over HTTPS (plain `http` is accepted only for a loopback host) at concurrency 1, 5, 25 and 50: that many worker threads, each closed-loop (next request after the previous response), for a bounded duration and request cap per level.
- Writes one JSON line per request (run id, experiment id, sequence, phase, level, worker, route, method, status, outcome, latency in ms, bytes, UTC start time, `X-Request-Id` sent and echoed) plus an event log with UTC phase boundaries, then seals the files.
- **Default: non-LLM endpoints only** (`/healthz`, `/readyz`, `/metrics`, `/v1/graph/nodes/{id}`, `/v1/graph/nodes/{id}/neighbors`, `/v1/evidence/{id}`). Routes that need IDs you did not supply are dropped and reported (`ROUTE-DROPPED`, `routes_dropped` in the run record), never silently. `POST /v1/query` (planner + synthesis on claude-haiku-5-5 through the Anthropic API; the Bedrock route is the selectable fallback) is **opt-in** with `--llm`.
- Aborts (exit 4, run kept and marked `aborted`) on repeated 5xx or transport failures (20 of the last 40 requests) or 5 consecutive 401/403. Timeouts: 10 s per request, 30 s for an answer, whole run at most 7,200 s, at most 300,000 requests. All limits are in `config/load-profile.v1.json`.

## Semantic route (P42; manifest `experiments/manifests/15b-ecs-scaling-semantic.json`)

A manifest with a `semantic` block adds `POST /v1/semantic/retrieve` (the P40 public route: API key as `Authorization: Bearer`, body `{"question": ..., "topK": N}`, `N` at most 20) to the route mix with weight 40 (profile). The questions come from the one fixed file given with `--questions-file`: 100-200 distinct lines, each at most 1,000 characters, and its sha256 and count must equal the manifest pin (`semantic.questions_sha256`, `questions_count`); a different, duplicated or missing file is refused before anything is sent. `--llm` cannot be combined with it. The raw rows keep the index of the question, never its text. Without the block the semantic route does not exist for a run (it is neither used nor listed as dropped).

- **Required per-level request limits** (constants in `loadgen.py`, `SEMANTIC_LEVEL_CAPS` and `SEMANTIC_HOLD_CAP`): level 1 600, level 5 3,000, level 25 15,000, level 50 30,000, a phase named `hold...` at level 50 150,000; at most 198,600 in total (`SEMANTIC_RAMP_TOTAL`). `validate-manifest`, `plan` and `run` refuse a phase above its limit, a missing `max_requests`, a level without a limit, a second phase for the same limit or a hold below level 50. They are the S3 Vectors cost bound of R-b and must not be raised; lowering one is allowed.
- **Warm-up phase** (`"type": "warmup"`, exactly one, first, level 1, `max_requests` from the question count up to 200): one worker sends each question once in file order and stops; no retries. It is a phase of its own in the raw rows and every summary, so it never mixes into the level-1 figures. Without the `semantic` block a warm-up phase is refused.
- **429 replies** (outcome `throttled`) count toward the phase limit and are reported **separately**: `rate_limited_429` per phase and route in `summary.json`, the `summary.csv` and `timeline.csv` columns of the same name, `totals.rate_limited_429` and a `rate_limited_429` field per phase in the run record, and one `RATE-LIMITED-429: phase=... count=...` console line per phase. They are excluded from `throughput_rps`, `success_rps`, the error rates and every latency figure (`latency_ms_all_responses` holds served responses other than 429; `latency_ms_2xx` holds 2xx only), and they never count toward the abort rules. Added figures: `served_requests`, `successful_requests`, `success_rps` (2xx over the phase window), `active_seconds` and `success_rps_active` (over the span in which requests were sent), `peak_success_rps_1s`.
- `--observe-seconds N` shortens every observe phase of a manifest to at most `N` seconds (it can only lower a window; for local rehearsals, never R-b). The value is recorded in the run record.

```bash
python3 -I load-tests/loadgen.py plan --manifest experiments/manifests/15b-ecs-scaling-semantic.json --questions-file experiments/inputs/15b/semantic-questions.txt
python3 -I load-tests/loadgen.py run  --manifest experiments/manifests/15b-ecs-scaling-semantic.json --questions-file experiments/inputs/15b/semantic-questions.txt --run-id <run-id>
```

## LLM budget: answer buckets (opt-in)

claude-haiku-5-5 on the Anthropic API is billed by Anthropic, outside the AWS credits (primary route since repair round 3, 2026-11-09, after the instructor approved the Anthropic API and Voyage AI given the Bedrock quota restriction). The USD 1.33 session cap (lowered from USD 1.50 on 2026-11-09, user decision "Caps = planned use"; kept at 1.33 in round 3, user decision "easiest option") is split into **answer buckets**, pinned in `experiments/manifests/llm-allocation.json` (user decision 2026-11-08): **14c 10 / 15b 60 / 16b 40 / 17 5 = 115 answers**, 115 x 0.001365 = USD 0.156975 at the estimate below. At these prices USD 1.33 is a **conservative upper bound** and the bucket counts are the binding limit (the cap would allow 974 answers). **Each bucket is a hard stop**: once used up, that step makes no more LLM calls; the USD 1.33 total is the backstop; nothing rolls over automatically.

Pinned in `config/load-profile.v1.json`: claude-haiku-5-5 USD 0.10 input / 0.50 output per 1M tokens for prompts under 100,000 tokens (USD 0.50 / 2.50 above that; our prompts stay far below), confirmed from the Anthropic pricing page on 2026-11-09. Tokens per answer are the earlier plan raised 30% because the claude-haiku-5-5 tokenizer produces about 30% more tokens: planner 1,950 in + 260 out and synthesis 5,200 in + 1,040 out (was 1,500 / 200 and 4,000 / 800). So (7,150 x 0.10 + 1,300 x 0.50) / 1M = **USD 0.001365 per answer** (was USD 0.01155 on Bedrock Haiku 4.5 at 1.10 / 5.50; an estimate, not metered; the Anthropic console is the record). The **Bedrock fallback** is `us.anthropic.claude-haiku-4-5-20251001-v1:0` (geo cross-region, USD 1.10 / 5.50), selected with `SCHOLARCHAIN_SYNTHESIS_PROVIDER=bedrock`; switching back means changing the pricing and token blocks in the profile together (a new unit needs the manifests and tests updated, `check_manifests.py` fails if the estimate text no longer matches).

**Embeddings** (14C ingest and query smoke, 16B evaluation; not part of the answer buckets): Voyage `voyage-4-lite`, 256 dimensions, USD 0.02 per 1M tokens, the first 200M account tokens free. Embeddings cap USD 0.30, enforced with a token counter by the step that embeds; `llm_budget.embedding_cost()` computes the charge (USD 0 inside the free allowance). The load generator sends no embedding requests itself.

**Cost reporting** for every experiment output: AWS, Anthropic and Voyage as separate items, then the combined total; a provider with no charge is USD 0 with its usage noted. `loadgen.py run` writes `cost_report` in `raw/run-record.json` and prints a `COST-REPORT:` line; AWS is never estimated by the generator (take it from the AWS bill, `llm_budget.cost_report(..., aws_usd=...)`), so the combined total says it excludes AWS until you add it.

15B answer budget per level (bucket 15b, configurable with `--llm-answers 1=10,5=15,...` or `llm_answers` per manifest phase; with a manifest the keys are phase names such as `level-50=15`):

| Level | Answers | Estimated cost (USD) |
|---|---|---|
| 1 | 10 | 0.01365 |
| 5 | 15 | 0.020475 |
| 25 | 20 | 0.0273 |
| 50 | 15 | 0.020475 |
| Total | **60** | **0.0819** |

### `llm_budget.py`: the command every LLM-calling step uses

The ledger is an append-only JSONL file outside the repository and outside `target/` (so `sbt clean` cannot erase it): default `~/.scholarchain/llm-ledger/haiku-ledger.jsonl` (the file name is unchanged on purpose: the path is pinned in the profile and the runbook, and the ledger counts Haiku answers on either route). Every read and write holds a file lock, so concurrent reservations never pass a bucket. The runbook requires `reserve` **before** every LLM-calling command that does not charge the ledger itself (14C smoke query, 17 demo and final smoke). The two commands in this directory charge it themselves: `loadgen.py --llm` (bucket 15b) and `eval16b.py run` (bucket 16b); do not `reserve` for them as well, or each answer is counted twice.

```bash
python3 -I load-tests/llm_budget.py init                                        # once; records the sha256 of the allocation; refuses if it exists
python3 -I load-tests/llm_budget.py status                                      # per bucket size / used / remaining, total, cap
python3 -I load-tests/llm_budget.py reserve --bucket 14c --answers 3            # exit 3 and nothing written if the bucket or the total would be exceeded
python3 -I load-tests/llm_budget.py release --bucket 14c --answers 1            # give back reserved answers that were not used
python3 -I load-tests/llm_budget.py transfer --from 14c --to 15b --answers 2 --approval <file>
python3 -I load-tests/llm_budget.py adjust --usd 0.05 --source aws-bill         # spend seen outside the buckets; counts against the total only
```

`reserve` refuses when bucket used + N > bucket size, or when the ledger total + N answers x USD 0.001365 would exceed USD 1.33 (the total counts all buckets plus `adjust`). `transfer` moves unused allowance only and refuses unless the approval file exists and holds the exact line `APPROVED_LLM_TRANSFER=<from>-><to>:<N>` (for example `APPROVED_LLM_TRANSFER=14c->15b:2`); the line, the file sha256 and the new sizes are recorded, and the same approval file cannot be applied twice. `status` warns `ALLOCATION-CHANGED` if the allocation file differs from the one the ledger was created with. Reservations are bookkeeping: the tool cannot see calls made by other programs.

### The load generator and the 15b bucket

`--llm` charges the **15b** bucket (`--bucket` can name another) and refuses to start (exit 3, nothing sent) when planned answers exceed the bucket's remaining answers, when (ledger total + planned) would pass USD 1.33, when the ledger does not exist or is corrupt, or when `--questions-file` or the API key is missing. `--remaining-cap-usd` is optional and only lowers this run's own spend limit.

During the run, **before every LLM request**, the generator takes the ledger lock, re-reads the state, and appends one `answer` line (bucket `15b`) only if the bucket and the total still allow it. The moment the 15b bucket (or the total, or the run limit) is exhausted, it stops all LLM calls for the rest of the run (event `llm-cap-reached` with the reason `bucket-cap`, `ledger-cap` or `run-cap`), keeps the non-LLM load going, and records the bucket usage in the run record. At most 2 answers are in flight (`llm_max_inflight`, matching the runtime `maxConcurrentLlmCalls`). Answers are spread over the phase (slot i is due when the phase is (i + 0.5) / N done, by time or by share of the request cap).

### `eval16b.py`: the 16B live-evaluation command (bucket 16b)

Asks the fixed questions of `experiments/inputs/14c/questions.txt` (40, the same file 15B cycles through) once each, in file order, one at a time, through `POST /v1/query` (a 202 answer is polled at `/v1/jobs/{id}` and its result read at `/v1/jobs/{id}/result`).

```bash
python3 -I load-tests/eval16b.py plan                                      # no network, no key, no ledger write: question count, bucket state, estimate
python3 -I load-tests/eval16b.py run --run-id <run-id>                     # needs SCHOLARCHAIN_LOAD_BASE_URL and the key (name via --api-key-env) in the shell
python3 -I load-tests/eval16b.py run --run-id <run-id> --max-answers 10    # only the first 10 questions (can only lower the plan)
```

Refuses (exit 3, nothing sent, nothing charged) when the number of questions exceeds the bucket's remaining answers (a file of 41 against a bucket of 40 is refused, never truncated), when ledger total + planned cost would pass USD 1.33, when the ledger is absent or corrupt, or when the key, the base URL or the questions file is missing. During the run, one `answer` line for bucket 16b is appended under the ledger lock before every request; if the bucket or cap no longer allows it, the run stops (`llm-cap-reached`). It also stops on the first 401/403 and after 3 failed answers in a row (`--max-consecutive-failures`). A charge is not refunded after a failed request. Raw output (git-ignored, mode 0444, sealed): `target/experiment-runs/16b-live-evaluation-<run-id>/raw/answers.jsonl` (the question, ids, status, latency and the answer JSON of each 2xx answer; error bodies are never stored), `events.jsonl`, `run-record.json` (cost report: AWS, Anthropic, Voyage, combined) and `raw.sha256`. Grading is a separate step on `answers.jsonl`. Not run against the deployed stack.

## Secrets and privacy

The API key is read only from the environment variable **named** by `--api-key-env` (default `SCHOLARCHAIN_LOAD_API_KEY`); only its name is recorded. It is sent only on routes that need it (never on `/healthz` or `/readyz`) and is never printed, logged or written; response bodies are not stored (only `queryId` and `jobId` of an answer). The target host name is not written to the raw results (only its sha256, because the domain is private); loopback hosts are recorded in clear for tests. TLS certificates are always verified. A base URL with user-info, a path, a query or a fragment is refused.

## Commands

```bash
export SCHOLARCHAIN_LOAD_BASE_URL="https://<api host>"        # no path; value never committed
export SCHOLARCHAIN_LOAD_API_KEY="<the course API key>"       # set in your shell, never in a file

# 1. show the plan and the answer budget table; sends nothing
python3 -I load-tests/loadgen.py plan
python3 -I load-tests/loadgen.py plan --llm --questions-file <questions.txt>      # needs the ledger

# 2. the four levels, non-LLM only (default). node-ids-file: one graph node id per line, taken from the loaded 14C graph
python3 -I load-tests/loadgen.py run --experiment-id 15b-ecs-scaling --run-id <run-id> \
    --node-ids-file <node-ids.txt> [--evidence-ids-file <evidence-ids.txt>]

# 3. the full 15B scale-out / scale-in experiment from the committed manifest (about 50 minutes)
python3 -I load-tests/loadgen.py run --manifest experiments/manifests/15b-ecs-scaling.json --run-id <run-id> \
    --node-ids-file <node-ids.txt>

# 4. the same with the opt-in answer sample (60 answers at the defaults, bucket 15b; run llm_budget.py status first)
python3 -I load-tests/loadgen.py run --manifest experiments/manifests/15b-ecs-scaling.json --run-id <run-id> \
    --node-ids-file <node-ids.txt> --llm --questions-file <questions.txt>

# useful flags: --levels 1,5 --duration-seconds N --max-requests N --max-rps N --pause-seconds N --llm-answers 1=5,5=5
python3 -I load-tests/loadgen.py summarize target/experiment-runs/<experiment-id>-<run-id>   # re-derive, hash-verified
python3 -I load-tests/loadgen.py validate-manifest experiments/manifests/15b-ecs-scaling.json
```

Exit codes: 0 ok, 2 usage, 3 refused before sending, 4 run aborted or interrupted, 5 I/O error. Run only after the human approval record for the experiment exists; nothing in this directory is approval to spend or to run against the deployed stack.

## Output

`target/experiment-runs/<experiment-id>-<run-id>/` (git-ignored, the `EXPERIMENT_RUNS_DIR` of `scripts/config/release.conf`; inside the repository the output root must be under `target/`). A run directory is never reused.

| Path | Content |
|---|---|
| `raw/requests.jsonl`, `raw/events.jsonl`, `raw/run-record.json` | immutable raw evidence, mode 0444. The run record holds commit, tree dirty flag, profile sha256, manifest sha256, phases with UTC bounds, outcome (`completed`, `aborted`, `interrupted`), LLM answers sent and estimated cost, ledger totals |
| `raw/raw.sha256` | `sha256sum`-format listing of the other raw files; `summarize` refuses if any file changed |
| `derived/summary.json`, `summary.csv` | per phase and per route: requests, `rate_limited_429` (separate; excluded from the other figures), throughput, `success_rps`, error rates, p50/p95/p99 (nearest-rank, served responses other than 429, and 2xx only) |
| `derived/timeline.csv` | one row per UTC minute (the CloudWatch period) for lining up with ECS and ALB metrics; `successful_requests` and `rate_limited_429` columns split the minute's requests, and the p95 excludes 429 replies |

Failed and aborted runs keep their directory and record; reruns get a new run id.

## Tests

```bash
python3 -I -m unittest discover -s load-tests/tests -v     # loopback only; 91 tests, about 70 s in total (test_loadgen_semantic.py: 20 tests, about 18 s; test_eval16b.py alone: 17 tests, about 10 s)
```

## Limits

- Not wired into `scripts/check.sh` or `sbt check` (those are infra/build-owned); run the command above.
- With Container Insights off there is no `RunningTaskCount` metric; use `ecs describe-services` polling, ALB `HealthyHostCount` and the scaling activity history (`experiments/README.md`).
- The generator measures client-side latency from one machine; it is not a distributed load source, so a very fast target can be limited by the client. The graph routes need real node IDs; wrong IDs return 404 and do not load the graph path.
