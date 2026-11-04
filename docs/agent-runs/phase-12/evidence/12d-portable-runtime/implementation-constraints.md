# Carried implementation requirements — no live work

These requirements accompany the future isolated infrastructure work order; they do not change the previously reviewed design or implement Terraform here.

## Canary without an extra cluster

The required first canary is an offline regression suite: fake EMR/EC2/tag/inventory/lease clients, unknown cluster ID, create accepted then response lost, matching/nonmatching tags, wrong account/region/window, duplicate matches, paginated discovery, stale eventual visibility, denied termination and failed compare-and-swap. No real cluster, non-EMR resource or account request is created by that test. Its cloud cost is zero because it makes no cloud calls, not because a provider simulator is assumed free.

Test the proposed IAM policy documents and resource/action/context conditions offline as a separate gate. A locally implemented evaluator or mock does not establish AWS policy effectiveness, service-supported condition keys, tags appearing in time, SCP behavior or actual discovery consistency. AWS’s IAM policy simulator also documents differences from actual service behavior. Calling its APIs would still be account access, separately authorized later; none is invoked now.

Before the single cluster attempt, the human must either accept the explicitly documented remaining service/unknown-ID risk or approve a separately reviewed no-cluster live policy check with an exact API inventory, existing resources only, complete price/cap accounting and a new personal gate. Such a check may not secretly create an extra cluster or any other paid canary resources. Never label offline mocks a successful live canary or claim they close eventual-consistency risk.

## Certificate provider and costs

Exclude AWS Private CA, paid certificate issuance, ACM provisioning and Secrets Manager resources from the proposed USD5 implementation. A Terraform plan introducing them must fail the shape/cost gate and return for repricing and human approval. EMR7.8.0 cannot use the later EMR-managed certificate feature: AWS documents only PEMzip or a custom provider for releases4.8.0–7.10.0.

The narrow proposed path is a human-reviewed, pre-staged PEMzip referenced by the EMR security configuration, with privateKey.pem/certificateChain.pem and an explicit trust chain. This step creates, reads and uploads no keys or certificates. Reserve one S3 object no larger than65536bytes and its two-node retrievals in the conditional transfer inventory; bytes/hash remain unknown until a later protected-input protocol. No dummy certificate is represented as usable. Future protected generation/supply, host/domain SAN coverage, expiry, trust/hostname checking, permissions, transmission, retention and deletion need their own reviewed mechanism and human authority. Do not put keys in Terraform source/state, Git, command logs or public evidence.

AWS’s self-signed example is explicitly a proof-of-concept, with production risk; it is not implicit approval for this cluster. If an acceptable manually supplied certificate requires a paid issuer or exceeds the size/input assumptions, block and reprice. Custom Spark RPC authentication/AES-GCM and spill encryption must be validated separately and do not inherit all managed Spark security merely from the EMR security configuration.

## Explicit volume layout

Set both instance groups’ additional data layout explicitly: one32GiB gp3 data volume per instance, plus an explicitly32GiB gp3 root at3000IOPS/125MiB/s. Primary1+core1 must therefore show four volumes/128GiB total in the eventual plan and before/after inventory. Check provider/API fields and actual root/data count; additional/missing/different/default volumes fail closed and require recosting.

The AWS default table lists two32GiB data volumes for xlarge EBS-only instances; relying on that default would violate the one-data-volume model. Nothing in this document proves Terraform replacement semantics or real disk sufficiency. The later implementation must prove them with static/mock gates and the genuine reviewed plan. No Terraform command or resource change occurs here.
