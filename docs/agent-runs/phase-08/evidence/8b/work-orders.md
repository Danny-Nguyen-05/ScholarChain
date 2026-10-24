# 8B separate work orders

All owners read AGENTS.md, CLAUDE.md, docs/agents.md, docs/agent-runs/README.md, Phase 8 plan and applicable module contracts. Base 3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e. User authorized R1 repair now. N2–N8/R2–R3 deferred. No nested agents, reviewer, credentials, network/provider calls, commits/pushes, or human-decision writes. Every behavior change has feature tests. Coordinator runs shared sbt slot on JDK17 and retains exact results.

## Domain engineer

Only modules/core/**. Add chunkCount and wholeTextHash document fields with validation and backward compatibility only for genuine single-chunk ordinal0 inputs. Existing slot key unchanged. Shared groupKey excludes ordinal/source run/text/count; renderer always fills actual count and prechunk text hash. No metadata expansion needed. Core tests/wires/README owned here; report dependent fixture migrations.

## Storage engineer

Only modules/storage/**. Bind immutable full groups by type/entity/window/template/policy/model to chunk count and whole-text hash; preflight complete ordinals and reject entire mismatched group before text/prepared/embed/vector writes except rejection report. Keep F1 preembed conflict and prepared recovery. Add reusable validated bounded completed Phase6 export reading and work-selection APIs for RAG CLI. No dependency on rag. Local tests/README. Coordinate public API before dependent edits. R2/R3 remain deferred.

## RAG engineer

Only modules/rag/** and permitted runtime/schema prompts if needed. Populate actual chunkCount/prechunk wholeTextHash. Compose local fake-only CLI reading completed Phase6 export plus work manifest without storage→rag cycle. Local G1 and bounded real export, reproducible fresh counters and persistent replay. Preserve actual source provenance and qualifications. Five fixed-neighbor smoke cases, pointer/hash round trip and descriptive-only metric boundary. Module tests/README. Propose safely disabled authored live command with config caps/template/cleanup, never run.

## Independent test engineer

Only tests/**. Real renderer→item→runner shrink/grow group rejection before data writes; independent dedup/model/dimension/fallback/throttle/permanent-failure/replay matrix; fixed-neighbor/pointer/hash and metric boundary checks. Exercise local CLI and actual G1 completed Phase6 export via existing Spark APIs or retained producer fixture, preserving genuine provenance. No production edits. Coordinate API dependencies, request shared gates, freeze completed tests.

## Live-command authorship clarification

RAG owner may author a guarded live composition entry point reusing existing adapters. Validate disabled/missing/mismatched approval and all configured vector/concurrency/dollar caps before any client is constructed; offline refusal tests only. No provisioning or delete path. Actual invocation is unexecuted and remains an 8C gate. Coordinator authors disabled approval template and cleanup instructions as phase evidence, never a human approval record.

## Resume and runtime-fence prerequisite

Native specialist turns were interrupted by a tool-reported usage limit after early compilation. User instructed “continue”; resumed the same owners and preserved all files. No tests or cloud work occurred during that interruption.

Storage owner receives a minimal prerequisite: extract InMemoryGraphLoader class and its public fake alias from shared runtime-safe fake files into separate administrative files, preserving implementation/API byte identity. RuntimeGraphFence traverses declarations at file granularity; the local CLI references safe fakes. Keep the fence unchanged rather than trusting a mixed administrative file. Run post-extraction storage and actual-runtime-fence checks.

## Build engineer — CLI lifecycle prerequisite

Only build.sbt/project/**. Direct RAG local runMain returns correct persisted replay but nonforked Hadoop shutdown hooks outlive sbt's copied JAR classloader. Add minimal RAG Compile/run fork and repository baseDirectory settings, analogous existing Hadoop composition. No dependency/version/module edits. Coordinator reruns directCLI and fullgate; no sbt by owner. Native ID /root/build_8b.
