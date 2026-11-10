# ScholarChain

ScholarChain is a Scala 3, Hadoop MapReduce, Spark, AWS and Graph-RAG scholarly collaboration system. Modules: `core` (stable IDs, records, configuration contracts), `hadoop` (distributed input preparation), `entity-resolution` (cross-dataset identity matching), `spark` (temporal graph and deterministic metrics), `storage` (S3, Neptune, DynamoDB, S3 Vectors adapters), `rag` (retrieval planning and evidence-checked claims) and `services` (typed APIs and runtime composition). All AWS infrastructure is authored in Terraform (`infra/terraform`).

This README currently documents one topic: the model providers. Other documents: the live-session runbook is [docs/runbooks/phase-14-live-session.md](docs/runbooks/phase-14-live-session.md); the report section for the provider change is [docs/report/provider-fallback.md](docs/report/provider-fallback.md); module and tool details are in [modules/rag/README.md](modules/rag/README.md), [infra/terraform/README.md](infra/terraform/README.md), [scripts/README.md](scripts/README.md), [load-tests/README.md](load-tests/README.md) and [experiments/README.md](experiments/README.md).

Status of every claim below: **authored and tested offline only** (fake HTTP servers, Terraform tests, unit tests). No Anthropic, Voyage or Bedrock call has been made. Live behavior, latency and real cost are unverified until the human-gated live session.

## Model providers, the Bedrock restriction and the fallback configuration

### The restriction

The planned models run on Amazon Bedrock (Claude Haiku 4.5 for answers, Titan Text Embeddings V2 for embeddings). The course AWS account had a Bedrock quota of 0 for these models (Haiku 4.5, Titan V2 and Nova Micro were all 0 in us-east-2; recorded in `docs/agent-runs/phase-14/prompt.md`). The student asked AWS to raise the quota and reports that AWS declined the increase (the AWS reply itself is not stored in the repository). On 2026-11-09 the instructor approved the fallback: the Anthropic API for synthesis and Voyage AI for embeddings, with all remaining infrastructure and processing staying on AWS. The ruling is recorded verbatim in `docs/agent-runs/phase-14/prompt.md` (section "Subphase 14B, repair round 3") with a screenshot at `docs/agent-runs/phase-14/evidence/14b/fallback/instructor-approval.png`. The Bedrock switch is retained.

### The two configurations

| | Primary (default) | Bedrock fallback |
|---|---|---|
| Synthesis provider | Anthropic API (`https://api.anthropic.com/v1/messages`) | Amazon Bedrock Converse |
| Synthesis model id | `claude-haiku-5-5` | Claude Haiku 4.5: `anthropic.claude-haiku-4-5-20251001-v1:0`, called through the inference profile `us.anthropic.claude-haiku-4-5-20251001-v1:0` (regions us-east-1, us-east-2, us-west-2) |
| Embedding provider | Voyage AI (`https://api.voyageai.com`) | Amazon Bedrock |
| Embedding model id | `voyage-4-lite` (model version tag `voyage-4-lite`) | Titan Text Embeddings V2: `amazon.titan-embed-text-v2:0` |
| Embedding dimension | 256 (`output_dimension` 256) | 256 (Titan also supports 512 and 1024; the index and `vector_dimension` are fixed at 256) |
| Credential | an API key in Secrets Manager (entered by hand) | AWS IAM only, no key |
| Temperature 0 | not possible: the Anthropic path never sends `temperature`, `top_p` or `top_k` (Haiku 5.5 rejects non-default values), so answers are not deterministic | kept as configured |
| Billing | Anthropic and Voyage, outside AWS | AWS |

The defaults live in one place per provider: `modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/ProviderDefaults.scala` (`AnthropicDefaults`, `VoyageDefaults`, `BedrockDefaults`) and `infra/terraform/phase14b-providers.tf`; `scripts/config/release.conf` mirrors them as data and `scripts/tests/test_providers.py` fails if they drift.

### Selecting a configuration

The two capabilities are chosen independently, so four combinations exist (primary, Bedrock for synthesis only, Bedrock for embeddings only, Bedrock for both).

1. **Terraform (the deployed choice).** In the private, git-ignored `infra/terraform/environments/course.local.tfvars` (copy of `course.local.tfvars.example`) set `synthesis_provider` (`anthropic` default or `bedrock`) and `embedding_provider` (`voyage` default or `bedrock`).
   - `anthropic`: leave `synthesis_model_id` and `synthesis_inference_profile_*` unset. `voyage`: leave `embedding_model_id`, `embedding_inference_profile_*` and `embedding_model_version` unset (or exactly `voyage-4-lite`) and keep `vector_dimension = 256`. A leftover Bedrock id is refused by `terraform_data.provider_guard`.
   - `bedrock` synthesis: set `synthesis_model_id` (and the inference profile id and regions above). `bedrock` embeddings: set `embedding_model_id` (default Titan V2) and `embedding_model_version`.
   - **A Bedrock run also needs the matching deployer variable(s), applied before the base plan.** The deployer stack (`infra/terraform/deployer`) writes the AWS permission limit (the "permissions boundary") that caps what the app and loader roles may ever do. By default that limit contains no Bedrock access. If you choose `bedrock` only in the main `course.local.tfvars` and not there, the roles are not allowed to call Bedrock and every Bedrock call fails with AccessDenied. So set, in the private, git-ignored `infra/terraform/deployer/deployer.local.tfvars`, `main_synthesis_provider = "bedrock"` for Bedrock answers and/or `main_embedding_provider = "bedrock"` for Bedrock embeddings (defaults `anthropic` and `voyage`; keep them equal to `synthesis_provider` and `embedding_provider` of the main file), then re-apply the deployer (runbook A4) before making the base plan. The Titan grant of the loader role depends on `main_embedding_provider`; the runtime boundary's Bedrock statement on either variable. See `infra/terraform/deployer/README.md` and `infra/terraform/README.md` ("Repair round 3"). The default configuration needs none of this.
2. **Runtime environment (set by Terraform for the aws service mode).** `SCHOLARCHAIN_SYNTHESIS_PROVIDER` (`anthropic` or `bedrock`), `SCHOLARCHAIN_EMBEDDING_PROVIDER` (`voyage` or `bedrock`), `SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL`, `SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION`, `SCHOLARCHAIN_MODELS_EMBEDDING_MODEL`, `SCHOLARCHAIN_EMBEDDING_MODEL_VERSION` and `SCHOLARCHAIN_EMBEDDING_DIMENSION`. Unset or blank selects the default; an unknown value is refused. The API keys are injected as `SCHOLARCHAIN_ANTHROPIC_API_KEY` and `SCHOLARCHAIN_VOYAGE_API_KEY` from Secrets Manager, never as plain environment settings.
3. **Keys.** Terraform creates only empty Secrets Manager containers `scholarchain-<environment>/anthropic-api-key` and `scholarchain-<environment>/voyage-api-key` (only for a selected provider). The human enters each value by hand; no key is ever in the repository, a variable file, the plan or the state. Steps: runbook section "Entering the Anthropic and Voyage API keys".

### Running each configuration

Follow [docs/runbooks/phase-14-live-session.md](docs/runbooks/phase-14-live-session.md). For the **primary** configuration leave both variables at their defaults, enter both keys after the base apply and before the runtime apply, then run the runtime apply, the 14C ingest (Voyage embeds the documents with `input_type` document) and the smoke queries (`input_type` query). For a **Bedrock** run set the variable to `bedrock`, complete the runbook's Bedrock preconditions (quota check, playground call, Marketplace subscription; kept in that section only for a Bedrock run) and skip the key container of that provider. Offline verification of either path needs no account: `cd infra/terraform && terraform init -backend=false && terraform test` and the module tests (`rag` provider specs use fake HTTP only).

### Re-embedding rule

Stored vectors and query vectors must use the same provider, model, version tag and dimension. The services refuse any difference with a typed error. **Changing the embedding model or provider is therefore not a toggle: it requires re-embedding every stored document and rebuilding the affected vector index** (Titan and Voyage vectors must never share an index). Do it with the 14C ingest, not with Terraform.

### Data leaves AWS

With the primary configuration the question text and the evidence snippets inside each prompt are sent to Anthropic, and document text and query text are sent to Voyage AI. Both providers bill outside AWS and AWS budgets and alerts do not cover them. The Anthropic path also accepts only prompts estimated under 100,000 tokens (a higher price tier starts above that).

### Cost and the USD 25 ceiling

The USD 25 project limit covers all three bills: AWS, Anthropic and Voyage AI. They are reported as separate items, followed by the combined total; a provider with no charge is listed as USD 0 with its usage documented (for example Voyage `voyage-4-lite` inside the free allowance of 200M tokens per account). Planned estimates (public prices of 2026-11-09, estimates not measurements):

| Item | Value |
|---|---|
| `claude-haiku-5-5` price | USD 0.10 input / 0.50 output per 1M tokens (prompts up to 100,000 tokens) |
| Estimated cost per answer | USD 0.001365 (tokens raised 30% for the new tokenizer) |
| Answer buckets | 14c 10, 15b 60, 16b 40, 17 5 = 115 answers = USD 0.156975 |
| Synthesis cap | USD 1.33, a conservative upper bound; the bucket counts bind first |
| `voyage-4-lite` price and cap | USD 0.02 per 1M tokens; embedding cap USD 0.30 enforced with a token counter |

Report the real figures with `python3 -I scripts/lib/cost_report.py render --input <cost-report-input.json>` (input format in `scripts/README.md`, "Model providers and the cost report"). The pre-spend receipt also carries the human-entered Anthropic and Voyage spend to date. The USD 25 limit is a ceiling, not a target: monitor actual charges at AWS, Anthropic and Voyage and stop paid resources when the experiments finish. Revoke both provider keys in their consoles after cleanup.

### Not yet verified

No live call to either provider has been made; the model id spelling, tool-use acceptance, latency, cost and quality of `claude-haiku-5-5` and `voyage-4-lite` are unverified until a human-gated live run, and the provider API keys have not been created.
