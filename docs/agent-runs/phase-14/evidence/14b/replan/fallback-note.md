# Fallback note: synthesis and embeddings without Bedrock (Phase 14B replan)

Assembled by the coordinator on 2026-11-08 from the read-only `rag-engineer` reports. Nothing here was run live. Activation needs the user's decision on 2026-11-12; until then the Bedrock path (Haiku 4.5, Titan V2) stays configured.

## Why

The account has an account-wide Bedrock restriction: Haiku 4.5, Titan V2 and Nova Micro quotas are all 0 in us-east-2. An AWS Support case is open; the user escalates on 2026-11-10. Nova is therefore not a fallback.

## (a) Synthesis on the direct Anthropic API

- **Seam.** `LlmClient` (`modules/rag/.../RuntimeLlm.scala:27-29`) already isolates the provider. The new `AnthropicMessagesLlmClient` is a sibling of `BedrockConverseLlmClient`. It needs no agent, prompt, schema or core change, and no new dependency (it uses `java.net.http.HttpClient`).
- **Behaviour.** Forced `tool_choice {type:"tool"}` and `temperature` are valid for Haiku 4.5 on the direct API. The forced call emits no text before `tool_use`, so the existing "exactly one block" acceptance rule holds. Do not set `strict`. Strip `$schema`, `$id` and `title` from the tool schema as insurance.
- **Wiring, after the decision.**
  - Services: a `SCHOLARCHAIN_SYNTHESIS_PROVIDER` switch and the API key read as a secret.
  - Terraform: a `synthesis_provider` variable; an extended `service_secret_bindings` name list (it allows only four names today); no Bedrock synthesis grant for `anthropic`.
  - Execution role and runtime boundary: already allow `GetSecretValue` by ARN.
  - Network: query-api already reaches 443 on 0.0.0.0/0 through the NAT.
- **Price.** Haiku 4.5 direct API: USD 1 input / 5 output per 1M tokens (platform.claude.com pricing, fetched 2026-11-08). That is about USD 0.008–0.0105 per answer, so about 140–190 answers per USD 1.50.
- **Flags for the user.**
  - Billing goes to Anthropic, outside AWS. Ask the course whether it counts toward the USD 25 cap and whether it is allowed.
  - Haiku 4.5's "earliest retirement" date (2026-10-15) has passed, so a retirement notice could come at any time.
  - The question text and evidence snippets leave AWS.
- **Effort.** About 2–2.5 engineer-days across rag, service, infra and test.
- **Status.** The offline client is being prepared in an isolated worktree, not merged (user decision 2026-11-08).

## (b) Embeddings without Bedrock

- **Constraint.** The S3 Vectors indexes are fixed at dimension 256 (`infra/terraform/phase12b.tf:26-27`), and a changed model tag forces a full re-ingest. The dimension must be decided before base-apply, because index replacement after apply is blocked in normal mode.
- **No native alternative.** No credit-covered Bedrock embedding model is reachable from us-east-2 except Titan V2 itself. Titan V2 in us-east-1 or us-west-2 is unlikely to help under an account-wide restriction.
- **Recommended: a third-party embeddings API at 256 dimensions.** Either option keeps every Terraform guard. Effort is about 2–2.5 engineer-days.
  - Voyage `voyage-4-lite` with `output_dimension=256`: USD 0.02 per 1M tokens, with the first 200M tokens free.
  - OpenAI `text-embedding-3-small` with `dimensions=256`: USD 0.02 per 1M tokens, about USD 0.06 for the corpus.
- **Not recommended: a local open-source model** (ONNX in semantic-service).
  - It needs 5–7 days.
  - It adds ONNX Runtime and a tokenizer, which needs a build-engineer dependency approval.
  - It carries a tokenizer-parity risk.
  - Memory is tight on 1 GiB Fargate. The 256-dimension route is `snowflake-arctic-embed-m-v1.5` int8 at 110 MB, which probably needs 2 GiB.
- **Billing and data.** Same flags as (a): outside AWS, and query strings go to the vendor.

## Before 2026-11-12, with no commitment

- Create the provider accounts and set hard spend limits.
- Create API keys only into Secrets Manager; never in chat or in the repository.
- Ask the course about third-party spend.
- Keep the 256 dimension.
