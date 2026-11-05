# Phase 12D spike scripts

Authored offline. **Nothing here has been run against AWS.** The deploy-engineer runs the operator scripts only after the recorded human gate; the `emr/` scripts run on the cluster nodes.

| Script | Purpose | Exit codes |
|---|---|---|
| `preflight.sh --account A [--role scholarchain-deployer] [--region us-east-2]` | one `sts get-caller-identity`; prints only Arn, Account, Region; refuses unless account, assumed-role session of the named role, and region match | 0 ok, 1 mismatch, 64 usage |
| `collect-evidence.sh --bucket B --dest DIR` | downloads `results/` and `emr-logs/` (at most 3 tries each, no polling), verifies the tar sha256 against `results-manifest.sha256`, extracts and verifies every file in `files-manifest.sha256`, writes `evidence-manifest.sha256` | 0 ok, 3 mismatch, 4 download failed |
| `inventory.sh --account A [--out FILE]` | read-only describes (tagging API, EMR active clusters, NAT, EIP, ENI, instances, volumes, EFS, KMS aliases and keys, S3 head-bucket), judged by `inventory_eval.py`, JSON on stdout | 0 nothing billable (a `PendingDeletion` key is `expected_retained`), 2 billable remains, 3 inconclusive |
| `request_bound.py [--check]` | per-attempt S3 and Terraform API upper bound from `request-manifest.json`; `--check` fails above 1000 PUT/LIST or 10000 GET/HEAD, or if Terraform and the manifest list different staged objects | 0 / 1 |
| `emr/bootstrap.sh` | EMR bootstrap (arms `shutdown -h +N` first, then resolves Java 17 from an ordered candidate list: explicit `--java-home`, `/usr/lib/jvm/jre-17`, the Corretto directories, the `/etc/alternatives/jre` target, the `java` on `PATH`; writes the choice to `/opt/scholarchain-spike/java-home` and into the node's spark-defaults) | 3 checksum, 4 Java (lists candidates tried), 5 EFS, 10 timer, 64 usage |
| `emr/run-step.sh` | runtime environment (JAVA_HOME read from the file the bootstrap wrote; exit 4 if absent) plus `timeout --kill-after=60` | 4 |
| `emr/collect-results.sh` | primary-node tar and upload, 64 MiB cap | 5 over cap |

Unknown tagged resource types in the inventory fail closed (treated as billable). ENIs are found by tag only, so EFS mount-target ENIs (untagged) are covered through the EFS describe.

## Tests

stdlib `unittest` with fake `aws` and system commands on `PATH` (no network, no credentials):

```
cd scripts/phase12d-spike/tests
python3 -I -m unittest discover -s . -p 'test_*.py'
bash -n ../*.sh ../emr/*.sh
```

`shellcheck` was not available when these were written; run it when installed.

## Operator run method: Terraform and `aws login` credentials

Terraform's AWS provider does not refresh `aws login` credentials by itself: a live run hit `ExpiredToken` in the middle of the multipart upload of the 321 MB runtime. Give Terraform a `credential_process` profile so the provider re-runs the CLI whenever its credentials expire. The human adds this to their **own** `~/.aws/config` (no agent edits it):

```
[profile scholarchain-deployer-tf]
credential_process = aws configure export-credentials --profile scholarchain-deployer --format process
region = us-east-2
```

Then, after `aws login --profile scholarchain-deployer`, run Terraform with `AWS_PROFILE=scholarchain-deployer-tf` (and keep `AWS_REGION=us-east-2` for the scripts above).

What the documentation says (read 2026-11-04; none of it was executed here):

* `aws configure export-credentials --format process` exists. `process` is its default format and prints JSON "in the schema expected by the `credential_process` config value", so a tool that supports `credential_process` can use the CLI's own credential resolution, and the page gives `credential_process = aws configure export-credentials --profile myprofile` as the example: https://docs.aws.amazon.com/cli/latest/reference/configure/export-credentials.html
* The `aws login` announcement lists the same route for older SDKs that lack the console login provider: "support credentials delivered by `aws login` by using the credential_process provider with the AWS CLI": https://aws.amazon.com/blogs/security/simplified-developer-access-to-aws-with-aws-login/
* `aws login` credentials are short-lived (15 minutes) and the CLI and SDKs refresh them from the cached refresh token for up to 12 hours: https://docs.aws.amazon.com/sdkref/latest/guide/feature-login-credentials.html

Limits to expect: whether `export-credentials` resolves a `login_session` profile that also assumes the deployer role was not tested here. If the first Terraform call fails with a credential error, stop and check `aws sts get-caller-identity --profile scholarchain-deployer-tf` (it should name the deployer role session). The deployer role's `max_session_duration` is 3600 seconds, so a single run must finish within an hour of the last role assumption, or credentials will need a fresh `aws login`; keep the multipart upload of the runtime in mind when sizing the run.

