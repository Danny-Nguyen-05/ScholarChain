# Phase 12D initial billing-budget apply proposal

Prepared November 1, 2026 (America/Chicago). **PROPOSAL ONLY — no live command below has been executed.** The user-supplied independent review approves the durable read-only plan and satisfies P2 only at plan stage. This document does not approve an apply, payment, IAM mutation, EMR run or Phase 12D completion.

## Exact scope and artifact

The proposed change is only `aws_budgets_budget.project[0]`: one create, zero changes, destroys or replacements. Account `530332961125`; region `us-east-2`; AWS profile `scholarchain-billing-deployer`; budget `scholarchain-project-budget`; ARN `arn:aws:budgets::530332961125:budget/scholarchain-project-budget`.

The immutable reviewed artifact is `/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/billing.execution.tfplan`, 6,631 bytes, regular file owned by uid 501, mode 0600, SHA256 **ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855**. Check metadata and opaque binary hash immediately before a later approved operation; never decode it or expose its contents. Hash/size/type/mode/owner mismatch is a stop, not permission to regenerate or repair silently. Do not use the superseded temporary plan.

All current values below are taken from previously reviewed public evidence, not freshly inspected durable/private artifacts. The seven previous Terraform calls exited 0/0/0/0/0/2/0, with seven billing tests passed; these are historical, not newly run tests. No feature/source behavior changed in this authoring task.

## Preconditions that remain open

Proceed no further than independent proposal review in this task. A later coordinator must collect the remaining requirements together, without inventing human statements or launching a reviewer:

1. A user-launched independent review approves this apply proposal and any subsequently authored execution/backup/sanitizer scripts. `infra-engineer` authors scripts; `deploy-engineer` only executes approved source-controlled scripts and returns evidence. This document is not an executable script. No execution-script path/checksum is assigned yet: that missing artifact is an explicit future blocking dependency, not a grant for deploy-engineer to improvise shell commands.
2. Satisfy deploy-engineer’s clean-tree and approved-source-control gate. At this handoff the known branch is `phase-12`, HEAD `5ca8406bad5fe55f732458fa0cbd5d561ac83d8f`, and the reviewed packet reports 664 dirty/untracked entries. This proposal neither commits them nor grants an exception. The human must make the commit/source-control decision; a future coordinator records the approved commit and independently verifies a clean execution checkout and byte-identical reviewed sources. Any source/plan drift requires new review. No implicit dirty-tree exception or self-approval is allowed.
3. G1: the human supplies their own affirmation of the personal record identified by SHA256 `abe3a50ad7167fa01227c73e15e92a422a50609f6313bdcc56404cb61765d71a` (1,334 bytes). Preserve the record untouched; the agent does not draft, sign or rewrite this affirmation. G2 remains disclosed: actual setup times and original 60-minute compliance are uncertain, with retrospective acceptance already recorded; no backdated original compliance is claimed.
4. The human personally writes a later execution gate naming the complete plan SHA above, actor/role/profile/account, precise dated start/end window and timezone, this proposal and approved execution-script versions, exact single-budget create, and explicit permission for P3 read-only checks, one initial apply, immediate private backup, private post-apply readbacks and sanitized evidence. Also record the retention choice and handling of any partial-state artifacts. There is no human approval template/signature in this proposal. A general “approved” or this review verdict is insufficient.
5. P3 and apply occur within that window and one fresh role session. The human performs login/MFA and supplies fresh user-run STS; agents never inspect credentials/config/cache. The exact acceptable identity is Account `530332961125`, ARN `arn:aws:sts::530332961125:assumed-role/scholarchain-billing-deployer/scholarchain-billing-operator`. STS alone does not prove MFA; strict reviewed trust/caller policy and human login provenance remain relevant. Any different role/session/account or auth expiry stops the operation. Do not refresh login halfway through an apply or retry it under another identity.
6. Before any live request, the future execution-script review verifies the installed AWS CLI’s required options and safe error parsing offline. Its version and the `--show-filter-expression` capability have not been run or verified here. If the required explicit filter readback cannot be supported, return BLOCKED-ON; do not silently drop it or install/upgrade anything.
7. Immediately before initial apply, verify all reviewed source/copies/locks/toolchain hashes, paths, symlink targets, modes and owner. Reject symlinked data destinations; ensure no concurrent operation. Metadata-only inspection must find no resource `*.tfstate` or `*.tfstate.backup`, lock or recovery state anywhere under the primary/config and selected backups locations (including workspace subdirectories). A provider-working-data backend metadata file named `tf-data/terraform.tfstate`, if encountered, is not to be read or assumed harmless: stop for separately reviewed classification. Any unexpected state blocks initial apply. Never delete it, import, switch workspace, edit state or infer remote absence from local absence. Check main environment remains budget-disabled and does not manage the same ARN from another state; unresolved ownership blocks apply.
8. The immediately preceding exact-name budget request must establish absence under the exact identity/account/name described below. A present budget blocks initial apply even if it looks compatible. This proposal does not authorize adoption/import or overwrite.

## Identical execution context and source freeze

Define `primary` only as `/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap` and `backups` only as `/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap-backups`. Actual argv below uses expanded absolute paths; these labels are explanatory, not shell variables.

| Item | Required value |
| --- | --- |
| cwd | primary/config |
| executable | primary/toolchain/terraform-1.13.5 |
| executable SHA256 | 899b3c0ca0d2669ebd67be4bcd98e84bd9a914ce2fb3897ad0b86c98cbf3c962 |
| Terraform/provider versions | 1.13.5 / hashicorp/aws6.44.0 |
| provider executable SHA256 | 050fc3a7514d11585206c2a059be393ee54f50b9276ed1b092a1a975ae2afa73 |
| provider mirror | primary/toolchain/provider-mirror/registry.terraform.io/hashicorp/aws/6.44.0/darwin_arm64/terraform-provider-aws_v6.44.0_x5 |
| CLI config | primary/toolchain/terraform.tfrc |
| CLI config SHA256 | bd77a0311cac1f89c0ea02f5b328aec41a93ae6f11ddcd7873c61eae6045361e |
| dependency lock SHA256 | 421b75245b0080edee2b434482ff348419a75d7a6b798d5218e0a0f9f723eaea |
| resource state | primary/billing.execution.tfstate |
| TF_DATA_DIR | primary/tf-data |
| directories / data / executables | 0700 /0600 /0700; uid 501 |

The future process must use the prior minimal explicit environment: normal HOME=/Users/danny; PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin; TF_CLI_CONFIG_FILE=primary/toolchain/terraform.tfrc; TF_IN_AUTOMATION=1; AWS_EC2_METADATA_DISABLED=true; AWS_PAGER empty; AWS_PROFILE=scholarchain-billing-deployer; AWS_REGION=us-east-2; AWS_DEFAULT_REGION=us-east-2; AWS_SDK_LOAD_CONFIG=1; TF_DATA_DIR=primary/tf-data; umask 077. No inherited AWS credential overrides, custom endpoints, alternate profile/files, TF_CLI_ARGS, TF_VAR values, debug logging, provider overrides or alternate workspace. Normal named-profile consumption by the approved provider is allowed only in the later authorized operation; the agent never dumps or inspects those credential files. Do not repurpose HOME. Provider working links must resolve inside the durable mirror. No runtime `/tmp` dependency, init/upgrade, changing mirror/signature policy or disabling locks.

Before future apply, compare each public source below and its durable config counterpart to this reviewed freeze; also check the 209-file source freeze and approved public-input hash (`48f19c4526b63c8e194dcfeea8466591a0667c3a5956e06cdb31116e110a8e02`). Do not open or hash private recipient input. The CLI config is approved public tool configuration; AWS credential/config files are excluded from inspection.

| Reviewed repository source | Bytes | SHA256 |
| --- | --- | --- |
| infra/terraform/billing-bootstrap/README.md | 7866 | `46506dade67af6ec882f4bbd81661d00d92c8f9d5bebe6f6ed1e47e2c30143a0` |
| infra/terraform/billing-bootstrap/main.tf | 2215 | `5e69e4235e417c72968097af6050f66c434fd1d1049ee0f655d1b6635e101549` |
| infra/terraform/billing-bootstrap/outputs.tf | 1005 | `e729e4b3d6523074f293b95c9a5f85fc03c8eec0f8a40928c24a1c227ce3174f` |
| infra/terraform/billing-bootstrap/variables.tf | 3033 | `3e37054f1187192ae3188052d52630e50a3db950ce7436b639d98ef066a8c937` |
| infra/terraform/billing-bootstrap/versions.tf | 150 | `38c0d27255f1ccf0c6f57b6854b80e5bcecde516ebfbcdfbd7ae95ad220ba0a1` |
| infra/terraform/billing-bootstrap/tests/budget.tftest.hcl | 3984 | `8f79abffe3fe71e4a6736dddf461a0c8a7c136cdd7a5bf29394185e81da4550b` |
| infra/terraform/billing-bootstrap/.terraform.lock.hcl | 1406 | `421b75245b0080edee2b434482ff348419a75d7a6b798d5218e0a0f9f723eaea` |

## Proposed P3 checks — NOT EXECUTED

Only after the later personally written gate and fresh human login, the human runs:

```bash
aws sts get-caller-identity \
  --profile scholarchain-billing-deployer --region us-east-2 \
  --query '{Account:Account,Arn:Arn}' --output json --no-cli-pager
```

Record the supplied non-secret result, exact command, execution time/window provenance and exit when observed. Never invent an unknown timestamp or exit. This is a fresh window check; previous pasted STS is not reused as current identity.

A later approved read-only execution step uses the same session, with argv:

```bash
aws budgets describe-budget \
  --account-id 530332961125 \
  --budget-name scholarchain-project-budget \
  --show-filter-expression \
  --profile scholarchain-billing-deployer --region us-east-2 \
  --output json --no-cli-pager
```

All stdout/stderr is captured to a new exclusive 0600 private file under primary, never streamed to chat or Git. No `--debug`, credential diagnostics or account-wide inventory. Record only the sanitized operation/account/name/result category, exit and observation time. This exact request is only allowed if the installed CLI accepts the documented option; no live probe or alternative command is silently substituted.

Absence qualifies only if the captured response is positively identified as the AWS Budgets **NotFoundException** from **DescribeBudget**, with the recorded request matching account530332961125 and exact budget name and no mixed auth/transport/parse error. AWS lists NotFoundException as HTTP400, as it also does several failures; HTTP400 is not an absence test. CLI error text must be parsed with anchored known operation/service/error identity, not substring matches or `exit !=0`. A generic error, blank output, malformed JSON, `AccessDeniedException`, expiration, throttling, network/DNS/TLS failure or unrecognized message is BLOCKED-ON. A successful response means EXISTS and stop. Human/operator must avoid concurrent budget creation after this check; if a name collision still occurs, stop without retry or adoption. Exact-name absence is not a complete account inventory or ownership proof.

Permission basis is explicit: AWS’s current [service authorization operation mapping](https://docs.aws.amazon.com/service-authorization/latest/reference/list_budgets.html) maps DescribeBudget, DescribeNotificationsForBudget and DescribeSubscribersForNotification to `budgets:ViewBudget`; ListTagsForResource maps to `budgets:ListTagsForResource`. Those actions and the exact budget ARN appear in reviewed `infra/terraform/billing-execution/main.tf` and the installed human policy readback. The mapping supports this narrow proposal without adding imaginary `budgets:DescribeBudget` permissions. Actual authorization can still be denied by other policies, service requirements or session context; no effective-permission test was run here. On any unsupported permission/dependency or denial, stop and route to the human/infra owner for a separately reviewed decision; never widen IAM, add legacy console permissions or use root as a workaround. CreateBudget with tags is documented to involve `ModifyBudget` and `TagResource`, both present; live create/tag acceptance remains unproven.

## Proposed single apply — NOT EXECUTED

The following exact argv is for later execution by deploy-engineer through an independently approved source-controlled wrapper, after every prerequisite. It is not permission to paste/run it now. The wrapper sets the exact cwd/environment above, rechecks the opaque plan binding and absence of state, allocates exclusive 0600 private logs, then invokes:

```text
/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/toolchain/terraform-1.13.5
apply
-input=false
-no-color
-lock-timeout=30s
-state=/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/billing.execution.tfstate
/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/billing.execution.tfplan
```

These are separate argv elements; paths containing spaces must never be split. No `-auto-approve` is necessary: passing a saved plan immediately executes it without another interactive approval, per [Terraform 1.13 apply documentation](https://developer.hashicorp.com/terraform/cli/v1.13.x/commands/apply). Hence the written human gate and wrapper checks must happen before process start. No `-var`, `-var-file`, `-target`, `-replace`, `-destroy`, automatic planning, unlocked state or changed executable/configuration is allowed.

The [Terraform 1.13 apply reference](https://developer.hashicorp.com/terraform/cli/v1.13.x/commands/apply) permits local legacy state flags. Pinned 1.13.5 implementation confirms the binding: [ApplyCommand.PrepareBackend](https://raw.githubusercontent.com/hashicorp/terraform/v1.13.5/internal/command/apply.go) applies state arguments before loading the saved backend; [BackendForLocalPlan and backendCLIOpts](https://raw.githubusercontent.com/hashicorp/terraform/v1.13.5/internal/command/meta_backend.go) pass state input/output/backup overrides; [local StatePaths](https://raw.githubusercontent.com/hashicorp/terraform/v1.13.5/internal/backend/local/backend.go) prioritizes CLI overrides and defaults output to input and backup to output plus `.backup`. Thus the plan checksum does not alone freeze the state pathname: the exact absolute `-state` above is mandatory, with no `-state-out` or alternate workspace/backend. TF_DATA_DIR selects working metadata, not resource state. No runtime behavior was probed. Pinned source fetches succeeded; earlier guessed argument/local-document URLs failed and are disclosed in sources.json. The [latest local-backend reference](https://developer.hashicorp.com/terraform/language/backend/local) is supplementary, not the version-specific authority. There is no previous resource state to back up at initial create; Terraform's automatic previous-state backup cannot protect the newly created state. The immediate independent copy below is mandatory.

## Immediate state preservation and failure path

The later approved wrapper must implement and test the following private copy procedure without exposing state semantics. This proposal does not author or invoke that wrapper:

- Reserve a unique operation directory under backups using exclusive creation, mode 0700, owned by uid 501. The initial operation path proposed is `backups/initial-ab9f141e83058209/`. It must not already exist. Never overwrite/reuse an earlier backup. Allocate private operation logs separately with exclusive creation and0600. A reservation is not a completed backup.
- On apply exit 0, before any AWS readback, require the exact primary state path to be a nonempty regular nonsymlink file, uid 501 and0600; if mode is unexpectedly permissive, stop and preserve under a separately reviewed incident decision rather than publish or silently continue. The wrapper’s 077 umask is set before Terraform starts. Reject unexpected extra state/recovery files and classify them privately; do not ignore them.
- Open state with no-follow semantics and verify the descriptor identity matches metadata; hash its opaque bytes in memory, copy byte-for-byte to an exclusive 0600 `billing.execution.tfstate` file inside the reserved backup directory, fsync it and the directory, rehash copy and source, and require equality and stable source identity/size/mtime through the copy. Do not parse, redact, print or return state contents. A source/copy SHA and metadata receipt can be published; state bytes cannot. Record start/end and failure precisely. Copy or fsync/hash failures block completion and trigger incident routing, not another apply. No backup-success claim without observed receipt.
- An apply error can follow partial cloud mutation. On any nonzero/error/interrupt, stop further live calls. The already reviewed preservation branch may perform only local opaque preservation of any existing primary state and Terraform-generated recovery/backup files to uniquely named0600 copies under the same protected operation directory, with hashes and source filenames; it must not overwrite or delete originals. Capture private logs and metadata even if no state exists; “no state” does not prove “nothing created.” Do not read/print their contents. If the bounded preservation branch cannot safely identify/copy a file, stop and ask the incident responder for a reviewed diagnosis. Never rerun apply, import, destroy, manually edit state, force-unlock, refresh, regenerate a plan or widen a policy to recover.
- Successful later approved changes require a separately reviewed plan and human gate, a verified exclusive **pre-change** snapshot of existing state, then the same immediate **post-change** copy/hash receipt procedure to a new unique version directory. Terraform’s automatic `.backup` may exist but is not the versioned backup policy. This initial empty-state proposal does not authorize subsequent changes.

## Private post-apply verification — NOT EXECUTED

After exit 0 and verified backup, the later approved wrapper can perform only these narrow readbacks, in the same approved session/window, with private 0600 stdout/stderr and no live data printed. Each uses profile scholarchain-billing-deployer, region us-east-2, output json, no-cli-pager. The future wrapper must validate/cap pagination and fail if truncated or ambiguous; no broad new inventory.

1. `aws budgets describe-budget --account-id 530332961125 --budget-name scholarchain-project-budget --show-filter-expression ...`
2. `aws budgets list-tags-for-resource --resource-arn arn:aws:budgets::530332961125:budget/scholarchain-project-budget ...`
3. `aws budgets describe-notifications-for-budget --account-id 530332961125 --budget-name scholarchain-project-budget ...`
4. For each exact notification only, `aws budgets describe-subscribers-for-notification --account-id 530332961125 --budget-name scholarchain-project-budget --notification '{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":50,"ThresholdType":"PERCENTAGE"}' ...`, then the same fixed structure at 80 and 100. No recipient is passed as a CLI argument. Any need for further calls requires a new bounded decision, not an automatic retry loop.

These displayed suffix ellipses refer only to the explicit common flags already stated; they are not executable commands. A future source-controlled wrapper must use full, reviewed argv arrays and pagination limits, and hold private subscriber addresses in memory only. The documents for [notification reads](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_DescribeNotificationsForBudget.html), [subscriber reads](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_DescribeSubscribersForNotification.html) and [tag reads](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_ListTagsForResource.html) define those narrow request structures. Subscriber responses contain addresses, so they must not be pasted or generically serialized to evidence.

The allowlisted comparison must require exact account/request name and returned name; USD 200 COST/CUSTOM; start 2026-10-01T00:00:00Z and end 2027-01-01T00:00:00Z after exact UTC conversion (no date rounding); no CostFilters and no FilterExpression; exactly the five tags `course=CS441`, `project=scholarchain`, `environment=course`, `owner=danny`, `expiration_date=2027-01-01`; all 11 CostTypes fields matching the reviewed summary: IncludeCredit=false, IncludeRefund=false, UseAmortized=false, UseBlended=false; IncludeDiscount, IncludeOtherSubscription, IncludeRecurring, IncludeSubscription, IncludeSupport, IncludeTax and IncludeUpfront=true. Missing/deprecated or changed fields are a mismatch requiring review, not assumed defaults.

Require exactly three ACTUAL/GREATER_THAN/PERCENTAGE notifications at 50/80/100, no extras, each exactly one EMAIL subscriber and zero SNS subscribers. Compare the private address to the human-approved private input only in the approved wrapper’s memory; publish solely equality/count booleans. Require returned budget health/status, if provided, to be recorded honestly; a healthy config response alone is not proof of data coverage or delivery. Publish only allowlisted public field comparisons/counts, observation times, operation/exits, private artifact metadata and state backup receipts. Never publish raw objects, address hashes, credential data, spending totals or notification contents. After all public content is fully assembled and frozen, the future authorized wrapper must run the approved exact-recipient zero-match scan over that frozen public packet. Only that future authorized wrapper may read the approved private recipient in memory for this comparison; this authoring task performs no private reads. Publish only the safe receipt with exact scope/count/time and zero-match outcome, never the recipient or its hash. The receipt itself and derived manifests may be excluded explicitly from the content freeze to avoid circular hashes; their fixed allowlisted schemas must contain no recipient-bearing content. Any subsequent public content change requires a new scan of the newly frozen packet before handoff, rather than reusing the earlier receipt.

The human privately checks the intended mailbox, any subscription confirmation required by AWS and any delivery they actually observe. Record only their confirmation category/time or “unverified,” never the address. Do not manufacture spend or promise an immediate alert to test delivery. No email arriving is not proof of failure when no threshold event occurred; configured subscribers are not proof of delivered mail. Any mismatch/error stops the operation at its achieved stage; there is no implicit rollback or cleanup.

## Retention and completion limits

Keep primary state and each verified backup through reviewed budget teardown/final reconciliation and human-approved cleanup. Keep plans until superseded and human-approved cleanup. Both selected directories are protected local storage outside Git and recognized cloud-sync paths; arbitrary third-party sync remains unverified. These same-disk backups protect accidental deletion, not disk failure. No new offsite location is selected. The old `/tmp/scholarchain-phase12d-billing-execution-plan/billing.execution.tfplan` remains superseded and untouched; do not delete it or any private artifact without human approval.

Only subsequent successful apply/backup/readback and honest private confirmation can establish the billing-monitor portion of the pre-spend gate. Notifications are delayed monitoring, not spending enforcement. No current spend/allowance/account-plan/quota proof, paid Cost Explorer call, IAM adoption/inventory (F4), full OAuth refresh lifetime or complete runtime proof is supplied here. G1, G2, F4, P3 and live billing/EMR gates remain open. B1/B2/B3/R1/N19/N20 carry forward unchanged. The USD 200 total before-credit ceiling, proposed USD 5 spike within USD 15 EMR reserve (leaving USD 10 if spent), and USD 5.09 minimum upper-window margin remain planning assumptions, not spending authority. The main 171-create environment remains unapplied. No Phase 13 work, runtime selection or Phase 12D completion is inferred.

Next gate: independent proposal review, then separately scoped script authorship/review and human source-control/clean-tree/G1/exact-checksum/window decisions. This proposal task ends without executing anything live.
