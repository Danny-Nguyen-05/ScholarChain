# Review findings and repairs

The independent read-only reviewer initially requested changes. The factory-engineer made these scoped repairs before the final review:

1. Added a constitutional file edit fence using Claude's `agent_type` and canonicalized Write/Edit paths. Non-factory edits through `./` and `../` now block. Common Bash mutation patterns are also blocked; the shell guard is conservative rather than a complete sandbox.
2. Changed the Scala PostToolUse hook from repository-wide `sbt fmt` to file-scoped `scalafmtOnly` and checked that the edited path stays in the project.
3. Assigned the generated, ignored `.claude/.last-test-run` marker to the build-engineer and excluded it from the factory's `.claude/**` ownership.
4. Added `docs/agent-runs/README.md` to the factory seed's explicit territory.
5. Expanded the Stop source scan to Scala, Java, shell and Python under the implementation and script directories named in `docs/agents.md`.
6. Changed four roles' report language to return report text to the orchestrator rather than claim direct ownership of phase-evidence files.

The reviewer rechecked these changes and approved the revised proposal for human review. No human ratification is recorded in this file.
