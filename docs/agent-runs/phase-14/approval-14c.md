# Phase 14 approval: spending caps for 14C and the later paid steps

Written 2026-11-11. Drafted by the coordinator at my request from the runbook's A1.5 checklist; I read it and adopt it as my own record. It states caps and wording only, and it is not edited after its sha256 is taken.

## 1. Answers: Anthropic API

- Model: `claude-haiku-5-5` on the Anthropic API.
- Cap: **USD 1.33** for all answers together. This is a conservative upper bound. The estimate is USD 0.001365 per answer, so 115 answers cost about USD 0.156975.
- The 115 answers are split into buckets, and each bucket is a hard stop: **14c 10, 15b 60, 16b 40, 17 5**.

## 2. Embeddings: Voyage AI

- Model: `voyage-4-lite`, 256 dimensions.
- Cap: **USD 0.30** in total: USD 0.25 for the ingest and USD 0.05 for the query smoke.
- The cap is enforced with a token counter.

## 3. What leaves AWS, and what the USD 25 covers

- The question text and the evidence snippets are sent to Anthropic. The document text and the question text are sent to Voyage AI. This data leaves AWS.
- The project limit of USD 25 covers **AWS, Anthropic and Voyage together**, not AWS alone.

## 4. EMR

- Cap: **USD 2.52** cumulative.
- That is 3 runs of at most 90 minutes each, about USD 0.84 per run.

## 5. Project limit and hard stop

- The whole project may spend at most **USD 25**, cumulative.
- The session has a hard stop at **H37**. Cleanup starts no later than H35.

## 6. Disclosure (finding N11)

"The researcher-profile, community, paper and collaboration-path vectors carry no `sourceDataset` metadata and no `sourceDataset` filter, because a mixed-export summary can reference several source datasets and none is guessed (finding N11, accepted in Phase 8); only topic-institution-summary node vectors carry `sourceDataset`. Source provenance for the other four types is in `sourceReferences` and the ordinary-S3 text object, so the course's compact 'source dataset' metadata field is not available as a vector filter for them."

## 7. Phase 8 findings status

| Finding | Status |
|---|---|
| R3 | Fixed: the metadata budget is checked before any embedding call (storage-engineer, `EmbeddingMetadataBudgetSpec`). |
| N15 | Fixed: the query smoke has its own small caps (rag-engineer, `LiveEmbeddingCapsSpec`). |
| N11 | Disclosure only: section 6 above. |
