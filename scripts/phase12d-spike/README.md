# Phase 12D spike scripts

Authored offline. **Nothing here has been run against AWS.** The deploy-engineer runs the operator scripts only after the recorded human gate; the `emr/` scripts run on the cluster nodes.

| Script | Purpose | Exit codes |
|---|---|---|
| `preflight.sh --account A [--role scholarchain-deployer] [--region us-east-2]` | one `sts get-caller-identity`; prints only Arn, Account, Region; refuses unless account, assumed-role session of the named role, and region match | 0 ok, 1 mismatch, 64 usage |
| `collect-evidence.sh --bucket B --dest DIR` | downloads `results/` and `emr-logs/` (at most 3 tries each, no polling), verifies the tar sha256 against `results-manifest.sha256`, extracts and verifies every file in `files-manifest.sha256`, writes `evidence-manifest.sha256` | 0 ok, 3 mismatch, 4 download failed |
| `inventory.sh --account A [--out FILE]` | read-only describes (tagging API, EMR active clusters, NAT, EIP, ENI, instances, volumes, EFS, KMS aliases and keys, S3 head-bucket), judged by `inventory_eval.py`, JSON on stdout | 0 nothing billable (a `PendingDeletion` key is `expected_retained`), 2 billable remains, 3 inconclusive |
| `request_bound.py [--check]` | per-attempt S3 and Terraform API upper bound from `request-manifest.json`; `--check` fails above 1000 PUT/LIST or 10000 GET/HEAD, or if Terraform and the manifest list different staged objects | 0 / 1 |
| `emr/bootstrap.sh` | EMR bootstrap (arms `shutdown -h +N` first) | 3 checksum, 4 Java, 5 EFS, 10 timer, 64 usage |
| `emr/run-step.sh` | runtime environment plus `timeout --kill-after=60` | |
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
