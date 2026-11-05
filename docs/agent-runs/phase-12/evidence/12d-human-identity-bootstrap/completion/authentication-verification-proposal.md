# Proposed next continuation — authentication verification only

Status: PREPARED, NOT AUTHORIZED, NOT EXECUTED. This is a coordinator checklist, not a human gate. The saved setup proposal reserves actual sign-in/role-switch/browser-CLI login and account verification for a separately bounded authorization.

## Proposed scope for the human to select

One authentication-only verification of account `530332961125` in authentication region `us-east-2`, using only the dedicated IAM operator and billing role. Danny performs all password, passkey and browser-consent prompts. No root or planner session is used. The agent does not read credentials/config/cache files, operate the account console, or call AWS under this proposed human-performed path. Only sanitized account/ARN and success/error results are returned.

## Checklist to use only after a fresh go-ahead

1. Human opens the account IAM sign-in URL and signs in as `scholarchain-billing-operator` using the private console password and assigned passkey. Confirm account 530332961125. If the existing password does not work, stop; this verification does not authorize resetting passwords, removing MFA or changing IAM.
2. Human switches through the account menu to role `scholarchain-billing-deployer` in account 530332961125. Verify the selected role and account. A console access-denied widget does not authorize adding permissions. Stop on failed role assumption; never weaken the trust/MFA condition.
3. Human uses a new, dedicated CLI profile proposed as `scholarchain-billing-deployer`. If that profile name is already in use for another purpose, stop and choose a fresh name before any profile modification. Leave scholarchain-planner and the default profile untouched. Use same-device browser login; no remote-code or permanent-key fallback.
4. Proposed human Terminal command, not executed by this packet:

   `aws login --profile scholarchain-billing-deployer --region us-east-2`

   In the browser select the already-assumed billing role session. Approve only if the principal is the expected role/account. If root, the planner or the unswitched IAM operator is selected, cancel. CLI login normally writes its own local profile and token cache; no cache/config contents are shared with the agent or committed.
5. After successful role-selected CLI login, proposed human identity-only command, not executed by this packet:

   `aws sts get-caller-identity --profile scholarchain-billing-deployer --region us-east-2 --query '{Account:Account,Arn:Arn}' --output json --no-cli-pager`

   Expected account: 530332961125. Expected ARN prefix: `arn:aws:sts::530332961125:assumed-role/scholarchain-billing-deployer/`. Share only this non-secret result or sanitized errors. GetCallerIdentity proves the selected identity; it does not independently prove MFA. Successful role assumption is assessed together with the already-read-back strict MFA trust.
6. Stop after the identity result. Report success or failure. One-hour role maximum is observed configuration, not proof of complete OAuth refresh lifetime. Refresh/session-lifetime testing and SDK/provider consumption remain separately identified checks; this short verification must not overclaim them. Any failed login stops the flow without automatic policy widening, a credential-process bridge, a permanent key or Identity Center fallback.

## Exclusions and later gates

No IAM/tag/policy changes, root login, credential-file inspection, Terraform plan/apply/import/destroy, budget creation, billing/account inventory, paid calls, EMR launch, Phase 13, commit or push. No agent AWS calls are authorized by accepting the human-performed path above unless the human explicitly adds a bounded agent call.

A fresh execution-identity budget plan, independent review and human-written approval of the exact apply remain later gates. Active monitoring, recipient delivery, usable cost data, conservative remaining allowance and all live EMR prerequisites remain open. USD 5 proposed spike cap, USD 10 remaining EMR reserve and USD 5.09 upper-window margin are unchanged and are not spending approval.

## Documentation checked while preparing this proposal

- https://docs.aws.amazon.com/cli/latest/reference/login/
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-console.html
- Earlier independently reviewed decision memo: ../../12d-login-path-evaluation/decision-memo.md

The installed CLI 2.35.4 help was read from retained offline evidence; no CLI command ran now. The current public reference reports 2.38.5; no tool upgrade is implied. Both describe selecting an assumed-role console session for login. The complete candidate-B flow still needs live verification.
