@AGENTS.md
@docs/agents.md

# ScholarChain project memory

ScholarChain is a Scala 3, Hadoop MapReduce, Spark, AWS, and Graph-RAG scholarly collaboration system. Use a fresh Claude Code orchestrator session for each phase and route every edit to the one owner in `docs/agents.md`.

## Module boundaries

`core` defines stable IDs, records, serialization, and configuration contracts. `hadoop` prepares and normalizes distributed input. `entity-resolution` decides cross-dataset identity matches. `spark` builds the temporal graph and computes deterministic metrics. `storage` adapts S3, Neptune, DynamoDB, and S3 Vectors. `rag` plans retrieval and verifies evidence-backed claims. `services` exposes typed APIs and composes the runtime. Dependencies flow from service and adapters toward core contracts; no lower module depends on service routes or Terraform.

## Definition of done

Every behavior change has feature tests. After Phase 2 establishes the build, `sbt check` must pass and its `markTestRun` task must update `.claude/.last-test-run` only after successful tests; the build-engineer must ignore that local marker in `.gitignore`. Reports state exact observed results. Data transformations and runtime claims retain source and run provenance. Secrets use Secrets Manager or approved local placeholders; no secret values enter the repository. AWS infrastructure is authored through Terraform, never by direct cloud-console mutation.

The current Phase 1 control plane is a proposal until human ratification and a fresh session.
