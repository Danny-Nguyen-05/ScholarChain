# Billing execution identity — offline policy drafts

This root renders policy JSON only. Source inspection establishes that it contains no resource, data source, provider configuration, module or provisioner. Its tests inspect the rendered documents and input validation; tests do not prove the absence of AWS resources. No identity, role, permission, budget or session is created. The actual operator ARN is deliberately unset. No credential, state, private recipient or prior real plan is needed.

The proposed deployment role is `scholarchain-billing-deployer`, configurable by a concrete role name. Its only service permissions are five Budgets actions on one exact `arn:aws:budgets::<account>:budget/<name>` ARN. All account/budget inputs remain explicit; tests use synthetic identities. The caller and trust drafts remain null until a distinct same-account IAM user is supplied. `scholarchain-planner` is never trusted, elevated, given AssumeRole or repurposed.

## Permission audit — provider 6.44.0

Checked against [AWS Budgets service authorization](https://docs.aws.amazon.com/service-authorization/latest/reference/list_budgets.html), the versioned [budget implementation](https://github.com/hashicorp/terraform-provider-aws/blob/v6.44.0/internal/service/budgets/budget.go) and [tag implementation](https://github.com/hashicorp/terraform-provider-aws/blob/v6.44.0/internal/service/budgets/tags_gen.go) on October 31, 2026. API operation names are not IAM action names.

| Provider operation | IAM permission in this API-only draft | Reason |
| --- | --- | --- |
| CreateBudget, UpdateBudget | budgets:ModifyBudget | Budget amount, period, cost basis and initial creation |
| CreateNotification, DeleteNotification | budgets:ModifyBudget | Provider creates notifications with subscribers and reconciles changes by deletion/recreation |
| DescribeBudget, DescribeNotificationsForBudget, DescribeSubscribersForNotification | budgets:ViewBudget | Refresh and recipient/threshold readback |
| CreateBudget with ResourceTags; TagResource | budgets:TagResource | Five mandatory tags and changed values |
| ListTagsForResource | budgets:ListTagsForResource | Provider tag refresh/readback |
| UntagResource | budgets:UntagResource | Provider removes stale or changed tag keys during reconciliation; required governance tags must remain in reviewed configuration |
| DeleteBudget | budgets:ModifyBudget | Coarse IAM action also authorizes deletion; not a separate permission grant |

Every row is scoped to the exact budget ARN. No account-wide inventory, Cost Explorer API, report subscription, Budget Action, IAM, PassRole, EC2, EMR or model permission is included. `budgets:ModifyBudget` cannot distinguish authorized changes from deleting this budget, changing its recipient or raising its amount. The policy therefore cannot enforce USD 200 or the five tag values. Terraform validation, `prevent_destroy`, a reviewed plan and human approval are separate controls; none is an IAM deletion guarantee or a hard billing cutoff.

The service authorization operation table also lists legacy `aws-portal:ViewBilling`/`ModifyBilling`. Those actions cannot be scoped to a budget ARN. They are deliberately absent, rather than assigned an ineffective budget resource or broadened globally. [AWS migration guidance](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/migrate-granularaccess-whatis.html) says the aws-portal namespace reached end of standard support in July 2023, fine-grained permissions apply to accounts created after March 6, 2023, and Budgets API access is unaffected by console migration. This project's account was created in October 2026. The draft is for direct provider API use, not Billing-console navigation. This is a documentation-based authorization interpretation, not a live acceptance test. If exact-budget access fails, retain a sanitized diagnostic and stop for review; never add global portal access automatically. Console access, if later needed, needs a separate documented review.

## Trust and temporary credentials

The proposed contract is a concrete same-account IAM user distinct from root and planner, with registered MFA. Trust permits only that user's `sts:AssumeRole` with strict `Bool aws:MultiFactorAuthPresent=true`; no IfExists fallback. The caller policy permits only the exact billing role with the same condition. The caller draft is an explicit audit boundary even where same-account direct trust can independently authorize the named user. No grant is installed here.

[AWS MFA API guidance](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_configure-api-require.html) describes MFA-aware AssumeRole/GetSessionToken requests. A later approved credential workflow must establish that the request satisfies this trust and returns only temporary role credentials. No long-lived access key is proposed. **Compatibility of browser-based `aws login` with this MFA condition remains unverified**; do not assume console MFA, root MFA or a federated session supplies that condition. [AWS condition-key documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-multifactorauthpresent) describes context-key availability. If the available login mechanism cannot satisfy it without a new credential arrangement, stop and route a separately reviewed trust/session design. Never weaken the condition silently or invent credentials.

For a future role, propose `max_session_duration=3600` seconds (IAM's minimum configurable maximum); request a shorter bounded STS session if supported by the selected authentication path. These durations are proposals and are not enforced by this output-only root. MFA-protected AssumeRole sessions and session expiry do not impose an AWS resource spending timeout.

## Establishment strategy — human choice still required

1. Preferred Terraform-first route: the human supplies an already authorized, non-root privileged bootstrap identity. A separately authored and reviewed Terraform IAM bootstrap would install only the named operator/role/policy/trust arrangement, with a fresh plan and human-written security-change approval. Such an identity has not been confirmed. This policy-only root cannot install its own permissions.
2. If root plus the read-only planner are the only available identities, strict Terraform-only bootstrap is blocked. Proposed exception for explicit human consideration: a one-time **human-performed account access bootstrap** using the MFA-protected root console to establish a new dedicated console operator, MFA, and the single billing role with the reviewed exact trust, execution and caller documents. No root access keys, no planner changes, no broad AdministratorAccess, no Organizations/Identity Center enablement and no project budget creation in that console step. The human would record the exact resources, session/login method and limits in their own approval. Later Terraform ownership/adoption of the IAM resources needs its own reviewed procedure and authorization; no ad hoc import or duplicate ownership. This is a proposed deviation from Terraform-only authorship, not an approved exception or instructions to execute now.
3. Stop until the human chooses a route, supplies the actual operator identity and authorizes the corresponding bounded IAM-establishment work order. A rejected/unworkable exception leaves the route blocked; it does not permit root-run Terraform. IAM provisioning permissions, any adoption procedure, credential setup and actual grants remain future reviewed work. The billing execution role itself receives no IAM provisioning permissions.

## Later gates, not authorized here

After separately approved identity establishment, verify the non-root temporary caller without printing credentials. Re-enter the private recipient outside Git; the earlier read-only-planner plan and private artifacts were deleted by the human and cannot be reused. Obtain a fresh execution-identity plan of `billing-bootstrap`, protected binary/JSON/state outside Git, checksum, independent read-only review and human-written approval of that exact plan. The proposed identity may also need explicitly reviewed read-only provider preflight access; no wildcard service permission is inferred from an access error.

Only after a separately approved billing apply: read back the exact USD 200 CUSTOM account-wide budget, dates, five tags, 50/80/100 ACTUAL alerts and exclusion of credits/refunds. Prove recipient delivery privately and usable cost data/conservative remaining allowance before any paid work. CostTypes is deprecated and live acceptance is still open. The USD 5 proposed 12D cap, USD 10 remaining EMR reserve and USD 5.09 upper-window project margin remain unchanged and unapproved; alerts are not enforceable cutoffs.

Every Spark/G1, same-JAR baseline, driver/executor origin probe, shared filesystem, independent elapsed deadline, isolated launch plan/review and human cap/region/types/counts/runtime/teardown approval remains open. This draft authorizes no real plan, IAM change, apply, AWS account call, paid call or Phase 13 work.

## Local verification

Use the pinned Terraform 1.13.5/AWS 6.44.0 toolchain, `init -backend=false -input=false -no-color -lockfile=readonly`, `fmt -check -recursive`, `validate -no-color` and `test -no-color`. Tests use mock_provider aws with command=plan, synthetic inputs, exact JSON comparisons and rejected root/planner/foreign/wildcard/role identities. A scratch wildcard-budget-resource mutation must fail the exact-policy assertion; retain RED/GREEN evidence and repository before/after hashes. No real account plan is required by these checks.
