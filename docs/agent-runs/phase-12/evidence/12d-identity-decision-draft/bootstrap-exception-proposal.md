# Proposed one-time AWS account-access setup

**DRAFT FOR DANNY TO REVIEW — NOT APPROVED — DO NOT EXECUTE**

Prepared October 31, 2026 at the user’s request. This is an agent-authored proposal, not a human decision, signature, exception record or permission to act. No AWS action has been taken.

## What this proposal is for

Prepare a separate sign-in and a limited billing role so that a later, separately approved Terraform operation can create the project’s USD 200 budget monitor. This proposal does not authorize creating that budget or deploying the project.

The project normally requires Terraform for AWS resources. The proposed exception would allow **Danny personally** to perform just the initial access setup in the MFA-protected root console, because no privileged non-root bootstrap identity has been confirmed. Agents would not operate the console or use root credentials.

## Proposed selection

| Item | Proposed choice for review |
| --- | --- |
| Account | 530332961125 |
| Operator user | scholarchain-billing-operator |
| Billing role | scholarchain-billing-deployer |
| Authentication Region | us-east-2 (Ohio), same-device browser login |
| Setup actor | Danny, personally, through the root console protected by MFA |
| Setup window | One supervised session, at most 60 minutes; exact start and end must be selected by Danny before any action |
| Operator password | Set privately by the bootstrap actor; no forced reset or ChangePassword permission |
| Operator MFA | Assigned by the bootstrap actor before operator use; no MFA self-management permissions |
| Role maximum session duration | Proposed 3,600 seconds; complete browser-login refresh lifetime remains unverified |
| Governance tags | course=CS441; project=scholarchain; environment=course; owner=danny; proposed expiration_date=2027-01-01 for retention/reconciliation review, not automatic deletion |

The names and resulting identities are still proposed, not confirmed to exist. The proposed tag date must be reviewed if account-access retention changes.

## Exact limited scope to consider

- Create only the named console operator, its console password/MFA, the named billing role, and the policies/attachments necessary to install the four independently reviewed policy documents. Use inline policies where practical to avoid unrelated managed-policy resources.
- Operator caller policy: only assumption of the named billing role, with the reviewed strict MFA condition. No budget permissions directly on the operator.
- Role trust policy: only the actual same-account named operator user, with strict MFA. Never root, the planner, a wildcard or another account. Verify the actual operator ARN after creation before using it in trust; the proposed name is not evidence of an existing principal.
- Role budget policy: exactly budgets:ModifyBudget, budgets:ViewBudget, budgets:TagResource, budgets:UntagResource and budgets:ListTagsForResource on arn:aws:budgets::530332961125:budget/scholarchain-project-budget.
- Separate role login policy: exactly signin:AuthorizeOAuth2Access and signin:CreateOAuth2Token on arn:aws:signin:us-east-2:530332961125:oauth2/public-client/localhost, with StringEquals signin:OAuthClientId=arn:aws:signin:::devtools/same-device.
- Apply the five required governance tags to the taggable user/role/policy resources created within this limited scope. No extra permissions to allow console navigation merely because a page reports access denied.

The reviewed policy source and limitations are in [billing-execution/README.md](../../../../../infra/terraform/billing-execution/README.md). Its independent amendment review is recorded in [review.md](../../review.md) under “Subphase 12D offline billing-execution policy amendment — independent review”. No policy scope may be widened automatically.

## Excluded from this proposal

No root access keys or root CLI/Terraform use; no AdministratorAccess; no changes to scholarchain-planner; no Organizations or Identity Center enablement; no permanent operator access key; no broader IAM administration; no budget creation; no real Terraform plan/apply/import/destroy; no application infrastructure or EMR; no paid calls or spending authorization. No agent login, account calls or console actions.

Actual operator sign-in, role switching, browser/CLI login and account verification need their own clearly bounded authorization/checklist. The intended later flow is operator console MFA → strict Switch Role → browser login selects the role. This complete flow remains unverified. A denial stops the process; it does not authorize broader console, remote-client or wildcard permissions.

Do not send passwords, MFA QR seeds, recovery information, one-time codes or credentials to the agent, and do not put them in this file or the repository.

## Checks and later decisions

1. Danny reviews this proposal and selects proceed with this scope, request changes, or defer. No option is selected by this draft.
2. Before action, Danny personally records the actual decision and exact setup window in the human-owned exception file. This proposal is not moved or relabelled as an approval by the agent.
3. Prepare the separately bounded manual-setup/read-only verification checklist. If the proposed names already exist or the reviewed policies cannot be installed as scoped, stop to resolve ownership and authorization instead of overwriting or broadening.
4. After any separately authorized setup, verify the exact installed identities, four policy documents, tags and session configuration. Record sanitized evidence only. Terraform ownership/adoption of manually created IAM resources remains a separate reviewed procedure; no ad hoc import or duplicate ownership.
5. Authentication verification, a fresh budget plan/checksum, independent plan review, human-written apply approval, budget readback and alert delivery remain separate gates. The old planner-bound plan was deleted and cannot be reused.

The proposed USD 5 EMR spike allocation, USD 10 remaining all-EMR reserve and USD 5.09 upper-window project margin are unchanged and unapproved. All live billing and EMR prerequisites remain open.

## Human decision — intentionally pending

- Selection: not supplied.
- Actual setup start/end: not supplied.
- Human-authored exception record: not supplied or verified.

This document contains no approval or signature.
