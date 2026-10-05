# Phase 2 work order

The human architect assigned the coordinator to spawn a build-engineer, then a separate read-only code-reviewer, and not to implement the build in the coordinator session. Models: build-engineer `composer-2.5-fast`; code-reviewer `grok-4.7-high-fast`.

Human decisions held for the whole phase:

- For Phase 2 only, the build-engineer may add `.gitkeep` placeholders in `modules/{core,hadoop,entity-resolution,spark,storage,rag,services}/src/{main,test}/scala` and in `datasets/`, `tests/`, `prompts/`, `infra/terraform/`, `scripts/`, `load-tests/`, `experiments/`, and `reports/`. That grants no ownership of future source files.
- The committed marker-behavior test stays under `project/`. `tests/**` stays with the test-engineer except `tests/.gitkeep`.

## Initial build order

Create the deterministic Scala 3 sbt multi-project build and empty repository skeleton. Required sbt projects: `core`, `hadoop`, `entityResolution`, `sparkAnalytics`, `storage`, `rag`, and `services`, mapped to folders by `docs/agents.md`.

Create `build.sbt`, `project/build.properties`, `project/plugins.sbt`, a centralized pinned version ledger, `.scalafmt.conf`, `.gitignore`, empty module source roots, and the required top-level directories. Add local compose configuration only if a specific local test dependency justifies it.

Use one JSON library, preferably uPickle unless a compatibility issue is documented. Choose ScalaTest or MUnit consistently. Put runtime-supplied Hadoop and Spark dependencies in Provided scope, test libraries in Test scope, and logging implementation in Runtime scope. Use no floating versions.

Define `fmt`, `check`, `packageJobs`, and `dockerLocal` aliases. `check` must check formatting, compile, run tests and AWS-free contract tests, then update the ignored `.claude/.last-test-run` marker only after success. Verify that failure does not update the marker. Container packaging must use a pinned Java runtime, a non-root user, and percentage-based memory limits.

Keep secrets, hardcoded cloud endpoints, deployment procedures, and application features out of the build. Do not edit Phase 1 control files or evidence. Run `sbt Test/compile` and `sbt check`, fix owned failures, and report exact observed results. Do not commit or push.

## Human repair order after the first approval

The human architect required two further repairs before acceptance:

1. `sbt check` must format-check test sources for all modules. A badly formatted test file passed `sbt check` while `core / Test / scalafmtCheck` failed.
2. The committed marker tests must run the actual failed-`check` path. The simulated guard and the hard-coded task-name list do not. A manual contract-test failure left the marker unchanged, so the behavior already worked.

The coordinator must save the owner, validation, repair, and review reports under `docs/agent-runs/phase-02/` before the human acceptance gate. `human-gate.md` and `accepted-commit.md` remain human-owned.
