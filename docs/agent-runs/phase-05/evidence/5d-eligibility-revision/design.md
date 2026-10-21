# Versioned request eligibility decision

This opt-in revision separates requesting model advice from granting an automatic identity merge. It does not change weights, score thresholds, LLM score bands, source observations, or the original three-group acceptance sufficiency requirement.

The separate closed request-policy document permits a Researcher request only for an unresolved pair inside the existing inclusive band, with name similarity at least 0.8, equal initials, comparable affiliation similarity at least 0.8, and available positive coauthor overlap from distinct publications. Work eligibility retains the legacy rule. Exact identifiers, hard conflicts, absent context, same-publication copies and name-only evidence do not gain a request route.

A validated model acceptance on a newly request-eligible pair that lacks the original automatic-acceptance sufficiency remains UNRESOLVED, with an explicit blocked-acceptance reason. Reject and abstain remain traceable model outputs. This demonstrates provider integration; it does not establish recovered identity accuracy.

The original ResolutionPolicy and configuration formats and fingerprints remain unchanged without the opt-in. The effective policyVersion binds the separately versioned request-policy document by its full SHA-256; API calls and exporters require the corresponding document. Requests, cache identities and exports bind the effective policy fingerprint. Existing policy resources and historical outputs are retained unchanged.

The gate was selected from the existing evidence-group semantics and synthetic adversarial cases, before the ER implementer inspected the actual Rice pair records and without reading human label values. The coordinator already knew the earlier aggregate Rice feature summary; this is a development policy revision, not an independently selected unseen evaluation.

No further acquisition is authorized or performed. The existing durable Rice input is available for canonical held-out exclusion before scoring, followed by a preview and, after passing offline tests, an attempt under the original approval and durable ledger. A successful provider response may accept, reject or abstain; none will be represented as human gold.

The original label tree and 5E outputs remain byte-identical. Any new evaluation on the previously exposed held-out cohort is descriptive post-policy validation, not fresh unseen held-out confirmation. Original and revised results must be shown together. No acceptance or Phase 6 authorization is inferred.
