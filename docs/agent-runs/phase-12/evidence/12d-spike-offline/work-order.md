# Phase 12D Step A — offline spike packaging, deployer root and isolated EMR root

Base: branch `phase-12`, HEAD `b4207c8`. Coordinator: Claude Code session started 2026-11-03 (takeover from an interrupted Codex session).

## Human decisions this work order follows (from chat, 2026-11-03; not rewritten here)

- Spike cap USD 10 hard, from the shared USD 200.
- Spark network crypto uses the default AES-CTR cipher. The AES-GCM probe failure is a disclosed known limitation; no more GCM work.
- The simplified isolated root is approved as proposed, including the listed drops and the disclosed residual risk: Hadoop/YARN RPC inside the single private subnet is unencrypted.
- Deploy identity: a separate small Terraform root for a scoped spike deployer role, which the human applies. It must be extensible for Phase 14. `scholarchain-billing-deployer` is untouched.
- Evidence: EMR logs and job outputs are copied to local evidence with SHA-256 hashes before destroy. Then the bucket is force-destroyed in the same session.
- Candidate (b), EMR Serverless, is unavailable. If (a) fails, report the plan's fallback options. No Docker setup.
- Termination layers:
  1. Steps-then-terminate.
  2. TERMINATE_CLUSTER on step failure.
  3. A node shutdown timer.
  4. An `auto_termination_policy` idle timeout.

  Whether a node-level `shutdown -h` actually ends the EMR instance and cluster is verified from documentation or a mock test, or the limitation is stated.
- The destroy runs in the same session as the job. Step B lists the per-day cost of leftover resources.
- Lean evidence: this one folder. Reviews are run by the human in a separate session.
- Subagents run on Sonnet 5.5 (`model: sonnet`) at high effort.

## Supersedes

`../12d-runtime-guard-repair/`, the interrupted Codex work order and baseline, is kept unchanged as history. Its controller, lease, cleanup and protected-archive design and its GCM investigation are superseded by the decisions above.

## Owners and scope (offline only)

| Owner | Writes | Task |
|---|---|---|
| build-engineer | `target/phase12d-spike-offline/**` (ignored) | Verify the existing runtime package (0644 job JAR, Scala 2.13 only). Preserve the `/tmp` packaging and probe sources. Run local `local-cluster` probes and the G1 pipeline with the AES-CTR security config, and compare against the baseline. |
| infra-engineer | `infra/terraform/deployer/**`, `infra/terraform/spikes/emr-spark-isolated/**`, `scripts/phase12d-spike/**` | Deployer role root, isolated spike root, bootstrap/step/collect/inventory scripts, mock-only Terraform tests, script tests, request bound, shutdown-semantics research |
| coordinator | this folder | Work order, baseline, cost replay for the simplified shape, gates, report, reviewer prompt in chat |

Not authorized: AWS API calls, login, reading credentials, `.env`, state or tfvars, real plan or apply, resource creation, spending. Also not authorized: changes to `infra/terraform/spikes/emr-spark/`, the billing roots, the main environment, application or build source, human-gate files, or earlier evidence.
