# Phase 12D preparation — coordinator transcription

User requests, verbatim: “so lets do 12D now”; “use recommendations”. This records the preparation work order; it is not a human-owned live execution approval.

- Proposed spike allocation: USD 10 from the shared USD 200 total before credits, with no additional budget.
- Maximum proposed total cluster runtime: two hours, including any retry, provisioning, bootstrap and shutdown reserve; not two hours per attempt.
- First candidate only: EMR on EC2 with a separate Spark 3.5.4 / Scala 2.13 distribution, one primary and one core, no Spot or task nodes. Stop after the first attempt. Serverless needs a new decision.
- Region remains us-east-2. The proposed m5.xlarge type requires the exact reviewed live plan and human-written approval before launch.
- Prepare a separate billing-bootstrap Terraform root and an EMR readiness proposal using local authoring and mock tests only. The main environment remains unchanged and unapplied.
- Keep the actual notification recipient private, supplied later as a sensitive input outside Git. No real recipient in fixtures or evidence.
- The last account check in 12C found zero budgets. The user has not confirmed creating one since then. Current budget state, alert delivery, Cost Explorer activation, current spend and deployment identity remain unverified. The user first answered: “Not yet; guide me through it”. After guidance, the user supplied a screenshot of AWS Cost Management saying this was the first visit, cost/usage data was being prepared and to check back in 24 hours. Record console initialization in progress; usable spending data and account-level activation are not independently API-verified. No optional paid data feature was selected by the agent.
- Keep scholarchain-planner read-only. Do not elevate it or inspect credentials. Future execution requires a separate non-root temporary deployment identity, scoped permissions and a human gate.
- No account API calls, real Terraform plan/apply/destroy/import, security mutations, paid Cost Explorer/model calls, commits, pushes or reviewer launch in this preparation work order.
- Do useful local preparation without inventing a runnable cluster where the portable G1 CLI inputs, filesystem mapping, class-origin probe or deadline controller are unresolved.
