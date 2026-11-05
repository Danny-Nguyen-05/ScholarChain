# Browser-login evaluation — offline conclusion

The offline evaluation is complete. **Recommend candidate B for the next offline policy-design work order:** IAM operator console login with MFA → strict-MFA console Switch Role → `aws login` selects the already-assumed billing role → the pinned provider consumes that role's native `login_session`. This is a documented-component composition and an engineering recommendation, **not an observed working AWS session**. No identity, login, grant, account check, plan or apply occurred.

The proposed user name is `scholarchain-billing-operator`; the proposed role name is `scholarchain-billing-deployer`. Neither is established or verified by this evaluation. The planner remains a separate read-only user. The account context remains 530332961125/us-east-2, but no actual operator ARN or privileged non-root bootstrap identity is confirmed.

## What the evidence establishes

- The installed AWS CLI is 2.35.4. Its local help includes an assumed-role login example. The [public CLI reference](https://docs.aws.amazon.com/cli/latest/reference/login/) also shows login selecting an assumed-role session. Four local version/help commands exited 0 under a fresh allowlisted environment, AWS config/credential paths set to /dev/null and metadata disabled. They performed no login or account operation.
- [AWS's console-switch documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-console.html) says the original identity authorizes the switch, root cannot switch, and user/role permissions are not cumulative. [The MFA guide](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_configure-api-require.html) documents strict MFA trust. These support evaluating MFA at the console role-assumption boundary, rather than assuming an IAM-user OAuth session carries the desired downstream context.
- Pinned provider 6.44.0 uses AWS SDK Go config 1.32.17 and credentials 1.19.16. The retained pinned SDK source resolves native `login_session`. It also rejects an MFA role profile with a serial number but no TokenProvider; the audited provider-base configuration does not supply an interactive MFA token prompt. Therefore a CLI `mfa_serial` role profile alone is not a complete Terraform authentication design. See infra/public-references.json and the retained source files for precise URLs and hashes.
- Current [SignInLocalDevelopmentAccess v3](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/SignInLocalDevelopmentAccess.html) includes **both** `signin:AuthorizeOAuth2Access` and `signin:CreateOAuth2Token`. The [Sign-In authorization reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_signin.html) and [CLI guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html) support the same-device localhost client resource. The managed policy's wildcard scope is not the proposed project scope.

## Candidate comparison

| Candidate | MFA boundary and login principal | Terraform path | Disposition |
| --- | --- | --- | --- |
| B: console role first | Operator signs into the console with MFA and switches through the unchanged strict trust; CLI login selects the assumed billing role | Native role `login_session`; no second AssumeRole or credential-process bridge | Recommended next offline design; needs two scoped login actions on the role, review and live proof |
| A: operator CLI login first | CLI obtains temporary operator credentials, then a role profile supplies fresh MFA to AssumeRole | CLI can prompt, but the pinned provider cannot directly supply that MFA token; a separately reviewed CLI-backed credential-process workflow would be needed | Documented-component alternative, more complex; not selected or automatically authorized |
| Direct operator OAuth context alone | Assumes browser-user MFA context reaches downstream role assumption without explicit verification | Depends on unproven context propagation | Not accepted as proof |
| GetSessionToken shortcut | Requires long-term IAM-user credentials under the STS API contract | Conflicts with the no-long-lived-key path | Not selected |
| Identity Center or permanent IAM user key | Requires a different credential/trust/bootstrap design | Not evaluated as an approved substitute | New human choice and separate review required |

The [STS comparison](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_sts-comparison.html) and [AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html) support the components of A; they do not prove this specific composed workflow works. No live result is claimed for either candidate.

## Required amendment before any setup

For B, the next source work order should render an additional login policy for the **billing role only**, allowing exactly the two Sign-In actions on the single proposed resource:

`arn:aws:signin:us-east-2:530332961125:oauth2/public-client/localhost`

That is the proposed IAM resource scope, not an OAuth clientId, and it is not an installed grant. The installed CLI's logical same-device client identifier is a different string. No remote-client or wildcard grant is proposed. An account/region-specific scope must be configurable and tested with independent synthetic values in the policy-only Terraform root. Do not add Sign-In actions to the five-action budget statement or weaken its exact budget ARN. Do not add Sign-In to the planner. Candidate B does not require an operator-level CLI login grant because login selects the already-assumed role; this is part of the unverified composition to check later.

Keep the caller's exact-role MFA condition and the trust's exact-user strict MFA condition. Fix carried E1 with case-insensitive planner comparison and a mixed-case rejection test during that next source edit. No source edits were made in this evaluation. A policy output alone does not create or attach permissions.

## Future setup proposal — not permission to execute

1. First author and independently review the bounded policy-only amendment above, with feature and negative tests and the required source/build gates. No account calls or IAM installation in that work order.
2. The human then chooses an existing privileged non-root Terraform bootstrap route, or personally records the exact one-time root-console exception. No exception is inferred from accepting this evaluation. No root CLI/access keys, AdministratorAccess, planner elevation, Organizations/Identity Center enablement or budget creation are included in the proposed exception.
3. After separately authorized establishment, the human verifies the actual dedicated operator, MFA enrollment, role/trust/caller/login attachments, required tags and session settings. Passwords, QR seeds and one-time codes stay private. Any Terraform ownership/adoption of manually created IAM resources is a separately reviewed procedure, not ad hoc import.
4. Under a separately authorized authentication-only verification, use the operator's MFA console session to switch to the exact billing role, then select that role during login to a new dedicated profile. The login permission scope is proposed for us-east-2 same-device authentication; it does not restrict later AWS resource Regions. Do not select root, planner or the unswitched operator. Stop on any failure, without widening trust or permissions.
5. Read back only the non-sensitive caller ARN/account and the installed public policy configuration through an approved path. `GetCallerIdentity` alone proves identity, not MFA; successful role assumption is meaningful only with the independently verified strict trust. CloudTrail MFA metadata alone is not a substitute for IAM condition evaluation. Do not disable MFA just to manufacture a negative test. Do not print/export credentials or read caches. Live policy/session evaluation remains unrun here.
6. Only after the authentication gate is accepted, re-enter the private recipient outside Git and create a fresh execution-identity budget plan. Its checksum, independent review and human-written apply approval remain separate. The deleted planner-bound plan is unavailable and cannot be reused.

Role duration and OAuth refresh behavior must be checked live. A proposed one-hour role maximum is not proof of the complete refresh-chain lifetime and never imposes a spending deadline. Expired/wrong-identity sessions must fail closed; logout or reauthentication must use the dedicated profile and never alter the planner. No credential-process bridge, permanent key or Identity Center fallback may be selected automatically.

## Remaining gates

No active budget monitor, recipient delivery, before-credit accounting acceptance, usable cost data or conservative remaining allowance is established. CUSTOM periods, deprecated CostTypes and tag acceptance remain unverified. USD 5 proposed spike allocation, USD 10 remaining all-EMR reserve and USD 5.09 upper-window margin remain unchanged and unapproved. Every G1/same-JAR/runtime/class-origin/shared-filesystem/elapsed-deadline/isolated-plan/teardown gate remains open. Prior B1/B2/B3/R1 and N19/N20 are unchanged. Phase 12D is not complete and Phase 13 has not started.
