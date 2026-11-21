# Report section: Bedrock quota restriction and the provider fallback

No course report document exists under `docs/`, so this file is the report section for the provider change; merge it into the final report. Everything below is authored and tested offline. Nothing was run against Anthropic, Voyage AI, Bedrock or AWS, and no figure here is a measured result.

## 1. The restriction

The design called for Amazon Bedrock models: Claude Haiku 4.5 for synthesis and Titan Text Embeddings V2 for embeddings. The course AWS account had a Bedrock quota of 0 for these models in us-east-2 (Haiku 4.5, Titan V2 and Amazon Nova Micro all showed 0; this is an account-wide restriction, so Nova was not an alternative). Evidence: `docs/agent-runs/phase-14/prompt.md`. The student requested a quota increase; the student reports that AWS declined it (the AWS reply is not stored in the repository).

## 2. The instructor ruling

On 2026-11-09 the instructor approved using the Anthropic API for synthesis and Voyage AI for embeddings, keeping the rest of the infrastructure and processing on AWS, retaining the Bedrock switch, and requiring: documentation of the restriction and the fallback; regeneration of stored embeddings and a rebuilt vector index if the embedding model changes; external API charges counted toward the USD 25 limit and reported as separate AWS, Anthropic and Voyage items followed by the combined total. The ruling text is in `docs/agent-runs/phase-14/prompt.md` ("Subphase 14B, repair round 3") and the screenshot is `docs/agent-runs/phase-14/evidence/14b/fallback/instructor-approval.png`.

## 3. Configurations

| | Primary | Fallback (retained) |
|---|---|---|
| Synthesis provider and model | Anthropic API, `claude-haiku-5-5` | Amazon Bedrock, Claude Haiku 4.5, `anthropic.claude-haiku-4-5-20251001-v1:0` through the inference profile `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| Embedding provider and model | Voyage AI, `voyage-4-lite` (version tag `voyage-4-lite`) | Amazon Bedrock, Titan Text Embeddings V2, `amazon.titan-embed-text-v2:0` |
| Embedding dimension | 256 (`output_dimension` 256) | 256 (index fixed at 256) |
| Credential | two API keys in Secrets Manager, entered by hand | IAM only |

Provenance of the identifiers: `modules/rag/src/main/scala/edu/uic/cs441/scholarchain/rag/ProviderDefaults.scala`, `infra/terraform/phase14b-providers.tf`, `scripts/config/release.conf`. Prices and limits were taken from public provider documentation on 2026-11-09 (recorded in the work order); no account or API call was made to check them.

## 4. Selecting and running a configuration

Terraform variables `synthesis_provider` (`anthropic` or `bedrock`) and `embedding_provider` (`voyage` or `bedrock`) in the private tfvars file; the services read `SCHOLARCHAIN_SYNTHESIS_PROVIDER` and `SCHOLARCHAIN_EMBEDDING_PROVIDER` (Terraform sets them in the aws service mode), plus the model, version and dimension settings `SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL`, `SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION`, `SCHOLARCHAIN_MODELS_EMBEDDING_MODEL`, `SCHOLARCHAIN_EMBEDDING_MODEL_VERSION`, `SCHOLARCHAIN_EMBEDDING_DIMENSION`. With a non-Bedrock provider the Bedrock model variables must stay unset (a guard refuses leftovers). The step-by-step run, including entering the two keys after the base apply and before the runtime apply, is `docs/runbooks/phase-14-live-session.md`. **A Bedrock run also needs the matching deployer variable(s), applied before the base plan.** The deployer stack (`infra/terraform/deployer`) writes the AWS permission limit (the "permissions boundary") that caps what the app and loader roles may ever do. By default that limit contains no Bedrock access. If you choose `bedrock` only in the main `course.local.tfvars` and not there, the roles are not allowed to call Bedrock and every Bedrock call fails with AccessDenied. So set, in the private, git-ignored `infra/terraform/deployer/deployer.local.tfvars`, `main_synthesis_provider = "bedrock"` for Bedrock answers and/or `main_embedding_provider = "bedrock"` for Bedrock embeddings (defaults `anthropic` and `voyage`; keep them equal to `synthesis_provider` and `embedding_provider` of the main file), then re-apply the deployer (runbook A4) before making the base plan. The Titan grant of the loader role depends on `main_embedding_provider`; the runtime boundary's Bedrock statement on either variable. See `infra/terraform/deployer/README.md` and `infra/terraform/README.md` ("Repair round 3"). The default configuration needs none of this. The same selection instructions are in the root `README.md`.

## 5. Consistency and re-embedding

Stored and query vectors must share provider, model, version tag and dimension; the services refuse a mismatch with a typed error. Changing the embedding model requires re-embedding all stored documents and rebuilding the affected index; Titan and Voyage vectors never share an index.

## 6. Limitations and risks

- **Not deterministic.** The Anthropic path cannot use temperature 0: `claude-haiku-5-5` rejects `temperature`, `top_p` and `top_k` at non-default values, so the client never sends them. Identical questions can produce different answers; no result in this project may claim otherwise on this path.
- **Data leaves AWS.** Question text and evidence snippets go to Anthropic; document and query text go to Voyage AI.
- **Billing outside AWS.** AWS budgets do not cover either provider; the human reads both consoles.
- **Unverified live.** Model id acceptance, tool-use behavior, latency, quality and cost are unmeasured.

## 7. Cost reporting and the USD 25 ceiling

The USD 25 limit covers AWS, Anthropic and Voyage together. The final cost report lists AWS, Anthropic and Voyage AI as separate items and then the combined total; a provider with no charge is shown as USD 0 with its usage documented. The tool is `python3 -I scripts/lib/cost_report.py render --input <file>` (human-entered figures from the three bills; it calls no service). The pre-spend receipt carries Anthropic and Voyage spend to date, so the headroom arithmetic includes them.

Planning estimates only (not measurements): `claude-haiku-5-5` at USD 0.10 / 0.50 per 1M input / output tokens, USD 0.001365 per answer, 160 answers (buckets 10 / 60 / 80 / 10, raised from 115 answers = USD 0.156975 by the user decision of 2026-11-21) = USD 0.2184, shared synthesis cap USD 1.33 kept as a conservative upper bound (the per-answer cost is not metered in full, because planner-call tokens are not recorded; the synthesis call alone, from local git-ignored raw run evidence, was 27,359 input / 264 output tokens for one probe answer, about USD 0.0029 or about 2.1 times the unit, and a mean of 8,664 input / 316 output tokens, about USD 0.0010 or about 0.75 times the unit, over the 15 of 33 benchmark answers that record usage; the cost varies with the retrieval context, the worst case at the probe rate is 160 x USD 0.0029, about USD 0.46, under the USD 1.33 cap, and the Anthropic console is the cost of record); `voyage-4-lite` at USD 0.02 per 1M tokens with the first 200M account tokens free and a USD 0.30 embedding cap enforced with a token counter. The ceiling is not a target: stop paid resources when the experiments finish and revoke both keys after cleanup.

Actual spend, token counts and the combined total: **to be filled in from the three bills after the live session** (none exist yet).
