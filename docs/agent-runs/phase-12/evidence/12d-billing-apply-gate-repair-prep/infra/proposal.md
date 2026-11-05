# Phase 12D P2 storage and regeneration proposal (offline only)

Prepared October 31, 2026 (America/Chicago). Owner: infra-engineer. This is a public technical proposal for coordinator assembly, not an apply handoff or execution approval. No durable directory has been created, no plan regenerated, and no Terraform/AWS command run in this preparation. Coordinator reports the human selected the proposed local paths and retention, and conditionally agreed to regeneration after prerequisites. The coordinator owns recording the exact answers. P1's actual timing clarification and user-launched independent identity-packet APPROVE remain prerequisites; this agent has not independently reviewed those human answers.

## Proposed durable layout

Human choice is reported by the coordinator, not independently verified here. Selected proposed base (R): `/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap`. Selected proposed backup sibling (B): `/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap-backups`.

| Path relative to R | Purpose |
|---|---|
| `config/` | Frozen copy of the seven approved billing-bootstrap source/lock/test/README files; actual Terraform cwd |
| `terraform-data/` | Explicit TF_DATA_DIR for this working copy, consistent from init onward |
| `state/billing.tfstate` | Explicit sole local state path, independent of the main course root |
| `inputs/approved-public-inputs.tfvars.json` | Approved public inputs, including exact budget name, dates, amount, account/profile/region |
| `inputs/notification.private.tfvars.json` | Newly entered hidden recipient; no reuse, direct inspection, hash or output |
| `plans/12d-durable-01/billing.tfplan` | New private plan, never the old /tmp binary copied or renamed |
| `plans/12d-durable-01/protected/` | Private raw plan JSON and raw logs, not repository evidence |
| `toolchain/terraform-1.13.5` | Actual durable executable, not a symlink into /tmp |
| `toolchain/terraform.tfrc` | New public credential-free CLI config pointing only to durable installation artifacts |
| `toolchain/provider-mirror/` | Durable AWS 6.44.0 package for the verified host platform |
| `public-provenance/` | Allowlisted source/config/toolchain/command hashes and sanitized plan summary for later copying into evidence |

All owned directories must be mode 0700. Data, input, source, lock, logs, plans, JSON, state and backup files must be 0600; executable Terraform/provider binaries need owner execution, mode 0700. Do not chmod executable binaries to 0600. Use umask 077 and verify newly generated nested directories, file ownership, and ACLs. Reject symlink destinations or resolved descendants/ancestors under /tmp, the repository, cloud-synced directories or another state root. The spelling of Application Support alone is not proof of absence of redirection/sync. Preserve existing unrelated paths; stop on a preexisting state or conflicting layout rather than overwrite or initialize an empty replacement state.

The sibling B is separate from R so replacing a working copy cannot casually remove backups. It remains on the same physical disk and therefore is not disaster recovery. Any encrypted off-device backup is a separate human choice; do not silently send recipient-bearing state to cloud storage.

## What actually selects state in Terraform 1.13.5

The 1.13.x apply reference permits local-backend legacy `-state`, `-state-out` and `-backup` options, including saved-plan mode. A saved plan is already an execution instruction and does not prompt for a new plan approval. Therefore the future execution gate must precede invocation. [Apply reference](https://developer.hashicorp.com/terraform/cli/v1.13.x/commands/apply).

Pinned implementation: ApplyCommand.PrepareBackend first applies state arguments, then reads the saved plan's backend and invokes BackendForLocalPlan. That function decodes/configures the saved backend and supplies CLIOpts containing StatePath, StateOutPath and StateBackupPath. Thus the saved backend is relevant, but a local saved plan does not make the earlier CLI state pathname immutable. [apply.go](https://raw.githubusercontent.com/hashicorp/terraform/v1.13.5/internal/command/apply.go), [meta_backend.go](https://raw.githubusercontent.com/hashicorp/terraform/v1.13.5/internal/command/meta_backend.go).

The local backend's StatePaths uses CLI OverrideStatePath/Out/Backup before configured/default paths; absent a distinct output path, output uses input. Default backup is output plus `.backup`; `-backup=-` disables it. The operative binding is the selected local backend, operation CLI overrides, workspace, cwd for relative paths, and filesystem, not the binary plan's checksum alone. Require the exact same absolute `-state=R/state/billing.tfstate` at plan and any separately authorized saved-plan apply; reject missing/different `-state`, all `-state-out`, different workspace and cwd. Record the actual argv as an array. [Pinned local backend](https://raw.githubusercontent.com/hashicorp/terraform/v1.13.5/internal/backend/local/backend.go).

TF_DATA_DIR relocates per-working-directory backend/provider/module metadata; it does not select the resource state path. Keep it identical for init, plan and any future apply. Keep TF_CLI_CONFIG_FILE durable too. Use an environment allowlist, remove inherited TF_CLI_ARGS*, TF_WORKSPACE, TF_VAR_* and debug/provider-reattach/developer overrides, and record only nonsecret settings. [Environment reference](https://developer.hashicorp.com/terraform/cli/v1.13.x/config/environment-variables).

The source currently has implicit local backend, no explicit backend block. Retain that approved source and use the explicit absolute state override consistently. Adding a new backend block or migrating state would be a separate reviewed source/state change. Do not imply this proposal already changed backend configuration.

## Toolchain and provenance

Do not retain the old `/tmp/scholarchain-phase12b-repair1-infra/terraform` or its terraformrc/provider targets as runtime dependencies. Future authorized preparation must place the same verified Terraform 1.13.5 binary in R and record SHA-256, platform, file mode and source provenance; reference binary SHA is `899b3c0ca0d2669ebd67be4bcd98e84bd9a914ce2fb3897ad0b86c98cbf3c962` from prior public toolchain evidence, not newly verified here. AWS stays 6.44.0 and the lock remains byte-identical (`421b75245b0080edee2b434482ff348419a75d7a6b798d5218e0a0f9f723eaea` reference SHA).

Create a credential-free tfrc with disable_checkpoint=true and an explicit filesystem_mirror for registry.terraform.io/hashicorp/aws under R/toolchain/provider-mirror, with no direct fallback for this provider and no dev_overrides. Retain the pinned release package and lock verification provenance, use init -lockfile=readonly and no -upgrade, and record executable/package hashes. Terraform may symlink installed providers to mirror/cache directories; inspect resolved targets and ensure all are durable. Do not copy an old TF_DATA_DIR blindly or assume moving its directory fixes an external symlink. [CLI configuration reference](https://developer.hashicorp.com/terraform/cli/v1.13.x/config/config-file).

Future preparation hashes source/config copies, public inputs, credential-free tfrc, executable/package files and public runner/helper; compares all seven copies to the approved source; records cwd/environment/argv/tool versions; and retains a new sanitized summary, new plan byte count/SHA-256 and protected-artifact metadata. Recipient input remains excluded from hashes/content reads. The old plan stays historical and cannot be upgraded by copying it to R.

## Locking, retention and failure handling

Local state locks use local system APIs and require the same state path. They do not coordinate two distinct state roots or another computer. Retain locking and bounded -lock-timeout=30s; never use -lock=false, force-unlock, or a second empty state to bypass contention. [Local backend reference](https://developer.hashicorp.com/terraform/language/backend/local).

Backup policy selected according to the coordinator, whose exact transcription governs: preserve every pre/post state snapshot under unique operation directories in B, mode 0700, files 0600. For any future approved state write, set -backup to a unique B/<operation-id>/pre-operation.tfstate; never reuse/overwrite that name. The first create may have no prior state to back up. After completion or partial failure, preserve the resulting state and verify a protected post-operation copy without printing contents. Retain active state, plans, private artifacts and backups through reviewed teardown AND final billing reconciliation, then only clean up under an explicit human decision. No automatic age/date deletion, expiration job or /tmp lifecycle. This storage choice is not apply approval.

Saved-plan apply checks state lineage/serial and rejects stale/different state; this does not discover an existing remote budget when the local state is empty. On stale plan, unknown state, lock failure, authentication expiry, AccessDenied, provider/config/hash drift, or partial failure, stop and preserve evidence/state; no retry into empty state, no permission widening, no import, no automatic rollback. Regenerate and independently re-review when required. [Pinned state checks](https://raw.githubusercontent.com/hashicorp/terraform/v1.13.5/internal/backend/local/backend_local.go).

`prevent_destroy` protects configured Terraform-managed objects against planned destruction; it cannot recover lost state or stop remote deletion/expiry or another tool. This budget's end date remains a reconciliation concern. Local state absence is not remote absence. [Lifecycle reference](https://developer.hashicorp.com/terraform/language/v1.13.x/meta-arguments/lifecycle).

## Future bounded regeneration sequence (not executed)

After the prerequisite human/external-review gates only: verify resolved storage ownership/modes and no conflicting state; construct the durable public toolchain/config/mirror; copy the approved seven source files and verify; run fmt/validate and the seven offline billing mock tests using credentials disabled; obtain newly hidden recipient input; initialize the live data directory with the pinned lock; run only the authorized read-only plan with same public inputs and dedicated profile. Plan exit2 means changes and must be inspected through the fail-closed public sanitizer. Require exactly 1 add/0 change/0 destroy/0 replace and all approved fields. No state file from this plan is expected, but filesystem absence proves nothing about AWS.

Future proposed plan arguments (an argv design, not a command executed here): `plan`, `-input=false`, `-no-color`, `-detailed-exitcode`, `-lock-timeout=30s`, `-state=/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/state/billing.tfstate`, `-var-file=/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/inputs/approved-public-inputs.tfvars.json`, `-var-file=/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/inputs/notification.private.tfvars.json`, `-out=/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/plans/12d-durable-01/billing.tfplan`.

The later handoff must name the actual new checksum, not invent one now; include exact executable, cwd, argv, state path, TF_DATA_DIR, source/config hashes and backup path. It will authorize no automatic planning, `-var`, `-target`, `-replace`, state migration/import or permission changes. Human approval of the exact reviewed new plan checksum/window precedes deploy-engineer execution. This proposal does not supply or activate that handoff.

P1 and P2 remain open until their acceptance evidence exists. P3's offline preflight design is in preflight-design.md; live checks remain window-gated. No change to USD200 total, proposed USD5 spike subcap/USD10 remaining EMR reserve/USD5.09 margin, B1/B2/B3/R1, N19/N20 or any runtime/spending gate.
