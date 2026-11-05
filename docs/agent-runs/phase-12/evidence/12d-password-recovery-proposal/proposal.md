Password-only recovery proposal — NOT AUTHORIZED / NOT EXECUTED

Prepared November1,2026 at the user's report that the operator password was not saved. This is a coordinator proposal, not a human approval. The durable-path billing plan remains waiting for fresh role-session authentication and hidden recipient entry.

Target: existing IAM user scholarchain-billing-operator in account530332961125. One action: human resets that user's console password and stores the new password privately in their chosen password manager. Keep existing MFA/passkey, operator caller policy, role/trust/two policies, governance tags and all permissions. No user/role recreation, access key, IAM grant, root CLI, budget/apply, resource deployment or spending.

Actor: human uses an existing authorized IAM administrator if available. If no privileged non-root administrator is available, a separately human-written, limited console-recovery exception may authorize the human account owner to perform this one reset through the MFA-protected root console. Agent never signs in, handles the password/MFA or controls that console. Prior setup exception and read-only plan authorization do not automatically authorize recovery.

Required gate before action: human personally writes the decision in docs/agent-runs/phase-12/billing-password-reset-authorization.md, identifying the account/user, chosen actor/route, this one-password scope, and whether that limited console exception is authorized if root is needed. Human records actual recovery start/end contemporaneously; no agent-written approval/signature, invented time or backdating. No fixed clock window is proposed here. This proposal is not copied or relabelled as an approval.

Proposed manual steps, only after that gate:
1. Human signs into the authorized administrative console with MFA; verifies account530332961125.
2. IAM → Users → scholarchain-billing-operator → Security credentials → Console sign-in → Manage console access → Reset password.
3. Human chooses Custom password, enters it privately and saves it in their password manager. Keep Require password change at next sign-in unchecked because this operator has no reviewed ChangePassword self-service grant. Stop if account policy forces it; do not grant new permissions to work around it.
4. For this reported forgotten-password recovery with no reported compromise, keep Revoke active console sessions unchecked: AWS documents that it adds an inline denial policy, outside the password-only scope. If compromise is suspected or revocation is needed, stop and scope separate incident handling instead of silently adding policy. Do not disable/remove MFA.
5. Human confirms Reset password, retains only non-sensitive success evidence, and signs out of the privileged session. No password screenshot or credential CSV is requested or stored in Git/chat.
6. Human tests operator sign-in with new password and existing MFA, switches to existing billing role, then performs fresh aws login and sanitized GetCallerIdentity using the dedicated profile. Resume only on exact account/role match. Record actual outcome, failures and times without secrets; stop on denial, no widening.

Authoritative procedure: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_passwords_admin-change-user.html (checked November1,2026). The page documents password reset, forced-change option and that session revocation attaches an inline policy. Documentation is not authorization or evidence that any recovery succeeded.

No change to P1's completed historical review. Any new recovery event is recorded separately. G1 pre-apply personal affirmation, P2 durable plan/new review, P3 pre-apply checks, all live budget/EMR gates and spending limits remain open/unchanged. Existing durable setup/offline tests must not be needlessly recreated.
