# Deployer-root apply proposal (phase14-main), 14A round 2

Status: PROPOSAL. Nothing here was run against AWS. The human runs every command below in their own terminal with their own admin
profile (MFA-authenticated), never as `scholarchain-deployer`. A reviewed plan is not an approval to apply: the decision is recorded in
the phase evidence first. An agent never reads the state file.

Order (decision D1): 14A commit -> human backs up the deployer state -> human applies the deployer root -> `plan.sh` for base-apply.

## Variables

State file (decision D5, never read by an agent; the path contains a space, so it is always quoted):
`$HOME/Library/Application Support/ScholarChain/terraform/spike-emr/deployer.tfstate`

`infra/terraform/deployer/deployer.local.tfvars` (git-ignored by `*.tfvars`; no secrets):

```
account_id             = "<12-digit-account-id>"
operator_principal_arn = "arn:aws:iam::<12-digit-account-id>:user/<operator>"
owner                  = "<owner tag>"
```

Defaults that matter: `enabled_permission_sets = ["phase14-main"]`, `role_name = "scholarchain-deployer"`, `main_environment = "course"`,
`region = "us-east-2"`.

## Commands (exact argv, one per line)

```
export AWS_PROFILE=<architect-admin-profile>
STATE="$HOME/Library/Application Support/ScholarChain/terraform/spike-emr/deployer.tfstate"
cd infra/terraform/deployer
test -f "$STATE"
BACKUP="$STATE.pre-phase14-$(date -u +%Y%m%dT%H%M%SZ).bak"
cp "$STATE" "$BACKUP"
shasum -a 256 "$BACKUP"
terraform init -input=false -lockfile=readonly
terraform plan -input=false -state="$STATE" -var-file=deployer.local.tfvars -out=deployer-phase14.tfplan
terraform show -no-color deployer-phase14.tfplan
terraform show -json deployer-phase14.tfplan | jq -r '.resource_changes[] | select(.change.actions != ["no-op"]) | "\(.change.actions | join(",")) \(.address)"' | sort
terraform apply -state="$STATE" deployer-phase14.tfplan        # ONLY after the recorded decision
shasum -a 256 "$STATE"                                         # record; back the file up again
aws iam list-attached-role-policies --role-name scholarchain-deployer --query 'length(AttachedPolicies)'
aws iam get-role --role-name scholarchain-deployer --query 'Role.MaxSessionDuration'
```

Backup step: "back up this file before apply" is the `BACKUP=` / `cp` / `shasum` group above; the SHA-256 of the copy goes into the phase evidence (`shasum -a 256 "$BACKUP"`).
If `test -f "$STATE"` fails, STOP: do not plan. Fallback (only then): `terraform import -state="$STATE" -var-file=deployer.local.tfvars
aws_iam_role.deployer scholarchain-deployer` and `... aws_iam_role_policy.login scholarchain-deployer:scholarchain-deployer-same-device-login`,
then re-plan and compare with the expectations below.

## Expected plan

Addresses derived from the code (`terraform console` over `local.selected_policies`, mock values, no provider call; script
`addr.sh` in this directory, output reproduced here), not from memory.

Create (16):
- `aws_iam_policy.main_boundary_runtime[0]` (`scholarchain-course-permissions-boundary`)
- `aws_iam_policy.main_boundary_emr[0]` (`scholarchain-course-emr-service-boundary`)
- `aws_iam_policy.permission_set["phase14-main--compute"]`, `["phase14-main--data"]`, `["phase14-main--emr-efs"]`, `["phase14-main--iam"]`, `["phase14-main--keys-obs"]`, `["phase14-main--network"]`, `["phase14-main--network-mod"]` (7; names `scholarchain-deployer-phase14-main--<part>`)
- `aws_iam_role_policy_attachment.permission_set["phase14-main--compute"]`, `--data`, `--emr-efs`, `--iam`, `--keys-obs`, `--network`, `--network-mod` (7)

Destroy (9), spike set from the previous code:
- `aws_iam_policy.permission_set["spike-emr--emr"]`, `["spike-emr--iam"]`, `["spike-emr--network"]`, `["spike-emr--storage"]` (4)
- `aws_iam_role_policy_attachment.permission_set["spike-emr--emr"]`, `--iam`, `--network`, `--storage` (4)
- `aws_iam_policy.spike_boundary[0]` (1; the spike roles that carried it are destroyed, so IAM allows the delete)

`aws_iam_role.deployer`: expected **no change**. Its configured attributes did not change in this work: name `scholarchain-deployer`, description,
`max_session_duration = 3600`, the one-principal MFA trust, provider `default_tags` (`environment = deployer`, `scholarchain:stack = deployer`).
If anything, an in-place **update** limited to `tags_all` (default-tag drift) or `description` is acceptable. `aws_iam_role_policy.login`: no change.

Expected summary line: `Plan: 16 to add, 0 to change, 9 to destroy.` (or `1 to change` if the role updates in place). Repair round 1 (F2) removed statements from existing documents but added or removed no resource, so the counts and addresses are unchanged.

The two `jq` lines make the check mechanical: the filtered list must be exactly the 25 lines above (16 `create`, 9 `delete`).

## STOP rules

- **ANY replacement of `aws_iam_role.deployer` (actions `delete,create` or `create,delete`, "must be replaced", `-/+`) = STOP. Do not apply.**
  A replacement would delete the role the human is about to use and invalidate its sessions; report it instead.
- Any address outside the lists above, any other destroy, or `aws_iam_role_policy.login` changing = STOP and report.
- Plan counts different from 16 / 0-1 / 9 = STOP and report.
- **On `LimitExceeded` (11 > 10 attachments while the 4 spike detachments race the 7 new attachments), stop, re-plan, expect only the remaining creates, re-apply; any other change is a stop.** Terraform does not order the 7 new attachments after the 4 spike detachments, so a run can briefly exceed the managed-policy quota of 10 on `scholarchain-deployer`. The failure is safe (a partial run leaves the role with some of both sets). After it, run `terraform plan -input=false -state="$STATE" -var-file=deployer.local.tfvars -out=deployer-phase14.tfplan` again, read it in full, and go on only if it shows creates of the missing `aws_iam_role_policy_attachment.permission_set[...]` entries and nothing else (no replacement of `aws_iam_role.deployer`, no new destroy).

## Where the real state could differ from this derivation

- The state was written by the Phase 12D/13C code. Its policy documents differ from the current spike code (13C edited them): irrelevant, they are destroyed.
- If the state predates commit `f6ee322` (same-device login policy), `aws_iam_role_policy.login` would show as a CREATE: acceptable only if the live role
  lacks that policy; otherwise STOP (EntityAlreadyExists). The address `aws_iam_policy.spike_boundary[0]` has had its `count` since the first
  commit (`f52b981`), so an un-indexed `aws_iam_policy.spike_boundary` should not occur; if it does, STOP.
- If the deployer role was changed by hand outside Terraform, the plan shows drift on `aws_iam_role.deployer`: review each attribute; a trust or MFA
  difference = STOP.
- The AWS provider is pinned (`hashicorp/aws 6.44.0`, lock file); a different version in the state's history would show in `terraform init` output.
