# Retained research attempts and calculation corrections

The public pricing fetch retrieved14 catalogs/pages successfully using bounded anonymous HTTPS requests. Additional Ohio SQS/SNS catalogs and the eventual EBS table also succeeded. All fetch records preserve URLs, times, hashes, status and bounds; the retained HTTP response file is a deterministic gzip of decoded bytes, with original wire/decoded hashes distinguished.

The first three guessed EBS URLs returned404. No rate was inferred from those failures. Reading AWS's pricing page identified token ec2/ebs; reading the linked official pricing JavaScript without executing it established the actual URL construction, ending current/ebs.json. That table returned200 and contains the exact Ohio gp3 rate. The failed URL records and loader bytes/hash are retained. Public web-reader requests to the guessed URLs were also inaccessible. No source or account state was changed by research.

The first cost-record attempt failed closed because SNS SMTP beginRange0 is a free tier. The selector requires a positive paid rate. It was corrected to beginRange1000 and rerun. Scheduler and SNS publish likewise use their positive marginal tiers, explicitly without claiming free entitlement. The first failed record attempt wrote no calculated output.

The arithmetic cross-check uses independent Fraction products/sums with a1e-22USD tolerance to accommodate Decimal rounding of repeating monthly fractions. It does not demand impossible exact equality after finite-precision division. Totals round upward, not downward, to cents.

The initial nominal model produced4.88USD while KMS request allowance was independent of the larger S3 request envelope. Coordinator review found that inconsistency before freezing any review packet. Prior script, selected rates and calculation bytes are retained under prior-cost-model/. The current model couples KMS allowance to all proposed S3 PUT/GET units plus20000 extra operations and raises the nominal result to5.30USD; all sensitivity cases and the explicit lower-request alternative are recalculated. Early commentary/preliminary agent figures are superseded by cost-calculations.json and cost-proposal.md. This correction supplies no account observation or spending authorization.

No full source/test/build suite was rerun for this public document/calculation proposal. The accepted1267-test readiness gate remains historical evidence. No AWS account API, login, recipient/state/plan/credential read, live guard, Terraform resource, actual cost measurement, deployment or cleanup was performed.
