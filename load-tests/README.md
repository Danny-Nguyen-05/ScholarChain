# load-tests

`loadgen.py` is the Phase 15 query-load generator (experiment D / 15B). Python 3 standard library only, no install step. Owner: experiment-engineer. It has **not** been run against the deployed stack; its tests use a fake query-api on `127.0.0.1`.

Run everything from the repository root with `python3 -I` (isolated mode).

## What it does

- Drives `query-api` over HTTPS (plain `http` is accepted only for a loopback host) at concurrency 1, 5, 25 and 50: that many worker threads, each closed-loop (next request after the previous response), for a bounded duration and request cap per level.
- Writes one JSON line per request (run id, experiment id, sequence, phase, level, worker, route, method, status, outcome, latency in ms, bytes, UTC start time, `X-Request-Id` sent and echoed) plus an event log with UTC phase boundaries, then seals the files.
- **Default: non-LLM endpoints only** (`/healthz`, `/readyz`, `/metrics`, `/v1/graph/nodes/{id}`, `/v1/graph/nodes/{id}/neighbors`, `/v1/evidence/{id}`). Routes that need IDs you did not supply are dropped and reported (`ROUTE-DROPPED`, `routes_dropped` in the run record), never silently. `POST /v1/query` (planner + synthesis on claude-haiku-5-5 through the Anthropic API; the Bedrock route is the selectable fallback) is **opt-in** with `--llm`.
- Aborts (exit 4, run kept and marked `aborted`) on repeated 5xx or transport failures (20 of the last 40 requests) or 5 consecutive 401/403. Timeouts: 10 s per request, 30 s for an answer, whole run at most 7,200 s, at most 300,000 requests. All limits are in `config/load-profile.v1.json`.

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

The ledger is an append-only JSONL file outside the repository and outside `target/` (so `sbt clean` cannot erase it): default `~/.scholarchain/llm-ledger/haiku-ledger.jsonl` (the file name is unchanged on purpose: the path is pinned in the profile and the runbook, and the ledger counts Haiku answers on either route). Every read and write holds a file lock, so concurrent reservations never pass a bucket. The runbook requires `reserve` **before** every LLM-calling command (14C smoke query, 16B evaluation, 17 demo and final smoke).

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
| `derived/summary.json`, `summary.csv` | per phase and per route: requests, throughput, error rates, p50/p95/p99 (nearest-rank, all responses and 2xx only) |
| `derived/timeline.csv` | one row per UTC minute (the CloudWatch period) for lining up with ECS and ALB metrics |

Failed and aborted runs keep their directory and record; reruns get a new run id.

## Tests

```bash
python3 -I -m unittest discover -s load-tests/tests -v     # 54 tests, about 40 s, loopback only
```

## Limits

- Not wired into `scripts/check.sh` or `sbt check` (those are infra/build-owned); run the command above.
- With Container Insights off there is no `RunningTaskCount` metric; use `ecs describe-services` polling, ALB `HealthyHostCount` and the scaling activity history (`experiments/README.md`).
- The generator measures client-side latency from one machine; it is not a distributed load source, so a very fast target can be limited by the client. The graph routes need real node IDs; wrong IDs return 404 and do not load the graph path.
