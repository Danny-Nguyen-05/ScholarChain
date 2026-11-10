# ScholarChain Phase 14 live session runbook (USD 25 course cap)

**Who this is for:** you, the human, new to AWS, who types every live command. Nothing here is run by an agent.
**What it covers:** the one live session of about 36 hours (hard stop at 37 hours), in this order: 14B apply, deploy and smoke, then 14C data load and vectors (8C), 15A EMR runs, 15B experiments, 16B live evaluation, demo video and final smoke, evidence archive, and full cleanup.
**Status:** authored 2026-11-08 from the repository READMEs and the `--help` text of every script. **No command in this file has been run against AWS.** Anything marked **(unverified until live)** was derived from documentation and may need a correction when it first runs; stop and report it instead of improvising.

Related documents: [approval request](../agent-runs/phase-14/approval-request-14b-replan.md) (the costs and caps you approve), [replan decisions](../agent-runs/phase-14/prompt.md) (your recorded answers), [scripts README](../../scripts/README.md), [deployer README](../../infra/terraform/deployer/README.md), [Terraform README](../../infra/terraform/README.md), [billing README](../../scripts/billing/README.md), [billing verification](../../scripts/billing/VERIFICATION.md), [storage README](../../modules/storage/README.md), [rag README](../../modules/rag/README.md), [load-tests README](../../load-tests/README.md), [experiments README](../../experiments/README.md), [14C templates](../agent-runs/phase-14/evidence/14b/replan/14c-templates.md), [fallback note](../agent-runs/phase-14/evidence/14b/replan/fallback-note.md).

---

## How to use this runbook

Every step has the same six parts. Do them in order and do not skip the "if it fails" part.

- **Where:** which terminal and folder, which AWS console page, or which Cloudflare tab.
- **Do:** the exact command or the exact field values.
- **Success looks like:** the exact lines or markers you must see.
- **If it fails:** the rule is always **stop, do not retry blindly, send the named log to the coordinator**. Retrying a failed `--execute` command can repeat a payment or a half-finished change.
- **Save to:** the log file path. All logs go under `target/phase14/evidence/{14b,14c,15,16b,17}/`. These folders are git-ignored; nothing in them is committed during the session.
- **Tell the coordinator:** the short message to send. **Never send** an account ID, a domain name, an e-mail address, a secret, a key, a `*.local.tfvars` value, plan text, or the contents of `~/.aws`. Send file paths and the marker lines only.

### Terminals and placeholders

| Name | Meaning |
|---|---|
| **T1** | Terminal tab 1, in the repository folder. Almost every command runs here. |
| **T2** | Terminal tab 2, used only to keep the Neptune tunnel open (B7). |
| **T3** | Terminal tab 3, used only for metric polling during 15B. |
| **T4** | Terminal tab 4, `caffeinate` (A11), so the Mac does not sleep. |
| **Console** | The AWS web console, region **us-east-2 (Ohio)** (top-right region menu). |
| **CF** | Cloudflare dashboard, your domain, tab **DNS**, page **Records**. |

**In every command below, replace anything in angle brackets such as `<run-prefix>` with your real value, without the brackets, before pressing Enter.** Placeholders (never write real values into any file you commit): `<acct>` your 12-digit AWS account ID; `<env>` is `course`; `<run-prefix>` is a label like `run-20261115` (must match `^run-[a-z0-9][a-z0-9-]{1,27}$`; choose it once in A4, and keep it for the whole session even if the date slips, because the IAM permissions are tied to this exact label); `<domain>` your Cloudflare domain; `<sha>` the 40-character `git rev-parse HEAD`; `<writer>` the Neptune writer host name; `<architect-admin-profile>` the name of your own administrator CLI profile.

### T1 setup (paste once in every new terminal; macOS zsh)

```
cd /Users/danny/Documents/UIC/CS441/ScholarChain
setopt interactive_comments 2>/dev/null
umask 077; set -o pipefail
export REPO="$PWD" R=us-east-2 SC_ENV=course
export ADMIN="<architect-admin-profile>"
export SCHOLARCHAIN_TF_PRIVATE_VARS="$REPO/infra/terraform/environments/course.local.tfvars"
export TF_PLUGIN_CACHE_DIR="$HOME/.terraform.d/plugin-cache"; mkdir -p "$TF_PLUGIN_CACHE_DIR"
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home; export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$REPO/docs/agent-runs/phase-04/xml-repair-logback.xml"
mkdir -p target/phase14/evidence/{14b,14c,15,16b,17} target/phase14/{approvals,private,14c-work,archive}
tfout() { terraform -chdir="$(mktemp -d)" output -no-color -state="$REPO/infra/terraform/terraform.tfstate" "$@"; }
```

What this does: `JAVA_HOME` selects Java 17 (sbt breaks on newer Java); `tfout` reads outputs from the local Terraform state file. The empty-directory form is deliberate: `terraform -chdir=infra/terraform output -state=infra/terraform/terraform.tfstate` prints "No outputs found" and exit 0 even when the stack exists ([G10 pitfall](../../infra/terraform/README.md)).

**Logging idiom used everywhere:** `<command> 2>&1 | tee -a <LOG>; echo "exit=$?"`. With `pipefail` the printed `exit=` is the command's own exit code, not `tee`'s.

**Exit codes of the three `--execute` scripts (`plan.sh`, `deploy.sh`, `cleanup.sh`):** 0 pass; 2 usage error; **3 refused: nothing mutating ran**, so fix the named problem and re-run once; **4 a check failed after approval, 5 a command failed, 124 timed out: STOP, do not re-run**, send the log and its final `RESULT:` line. See the [scripts README](../../scripts/README.md#exit-codes-all-phase-13-scripts).

**Role sessions (important):** the deployer role session lasts **1 hour**; the operator roles (loader, reader, cleanup, pipeline) last **4 hours**, both counted from the console **Switch Role** click (not from `aws login`). Your IAM user's console session lasts 12 hours, so sign in to the console again about every 11 hours. Always switch to a role **from your IAM user session** (click "Switch back" first); switching from one role to another is role chaining and caps the session at 1 hour. **Rule: do a fresh Switch Role and `aws login` immediately before each stage, and check who you are before you start.** If a stage will not fit in the time left, stop before it, not during it.

**Commit freeze:** from the moment the base plan is made (B1.4) until the end of Section C, you do not commit, do not edit any tracked file and do not create any untracked file outside git-ignored paths (`target/**`, `*.local.tfvars`). See Section D.

---

## 0. Glossary (plain words)

| Term | In one line |
|---|---|
| **AWS** | Amazon's cloud. You rent computers and storage by the hour; stopping a thing stops its meter, deleting it stops it for good. |
| **Terraform** | A tool that builds AWS things from files in `infra/terraform`. You never click-create resources; Terraform does it from reviewed files. |
| **plan / apply** | A *plan* is Terraform's list of what it would create, change or delete (it changes nothing). An *apply* makes those changes real and starts the billing. |
| **Terraform state** | A local file (`infra/terraform/terraform.tfstate`) in which Terraform remembers what it built. Never edit it; always back it up. |
| **tfvars** | A file of settings fed to Terraform (`course.local.tfvars`). Yours is private and git-ignored because it holds your account ID and domain. |
| **ALB** | Application Load Balancer: the public front door that receives HTTPS requests and passes them to the query service. It bills by the hour. |
| **ACM** | AWS Certificate Manager: issues the free HTTPS certificate for `api.<domain>`. |
| **CNAME** | A DNS record saying "this name is an alias for that other name". You add two by hand in Cloudflare. |
| **DNS-only** | A Cloudflare record with the **grey cloud**: Cloudflare only answers DNS and does not sit in the traffic path, so HTTPS ends at the ALB. The **orange cloud (proxied) would break validation: never use it**. |
| **CAA** | A DNS record listing which companies may issue certificates for your domain. If one exists it must allow `amazon.com`. |
| **NAT gateway** | The one-way door that lets private servers reach the internet (about USD 0.05/hour, running all session). |
| **ECS / Fargate** | ECS runs containers; Fargate means AWS supplies the machine. We run four small services (0.25 vCPU, 1 GiB each). |
| **ECR** | The AWS shelf where the four container images are stored (`push` puts them there). |
| **Neptune** | AWS's graph database (the researcher collaboration graph). It runs **serverless**. |
| **NCU** | Neptune Capacity Unit: the size meter of Neptune Serverless; ours idles at the minimum of 1 NCU (about USD 0.16/hour). |
| **S3** | AWS file storage ("buckets"). **S3 Vectors** is a vector store for embeddings (the semantic search index). |
| **Bedrock** | AWS's service for AI models. **Titan** (Titan Text Embeddings V2) turns text into 256 numbers (an embedding). **Haiku** (Claude Haiku 4.5) writes the final answers. |
| **Marketplace** | Haiku 4.5 is billed through AWS Marketplace to your card, **not** covered by the USD 140 credits, but it still counts toward the USD 25 cap. |
| **EMR** | Elastic MapReduce: a short-lived Hadoop/Spark cluster for the three Phase 15A runs (2 machines, at most 90 minutes each). |
| **IAM role** | A set of permissions you temporarily "become". We use a deployer role and four operator roles (loader, reader, cleanup, pipeline) so no single login can do everything. |
| **MFA** | Multi-factor authentication: the 6-digit code from your authenticator app. The roles require it. |
| **Switch Role** | The console menu action that makes you "become" an IAM role (you must be in your IAM-user session first). |
| **aws login** | `aws login --profile <p> --region us-east-2` opens the browser and lets the terminal use the role session you just switched to. It replaces access keys. |
| **profile** | A named block in `~/.aws/config` telling the CLI which login to use. |
| **KMS key** | The encryption key for the data buckets; Terraform schedules it for deletion at cleanup (7 days, free while pending). |
| **Secrets Manager** | AWS's safe for passwords/keys. You create four secrets there by hand; their values never enter Terraform or git. |
| **SigV4** | Amazon's request-signing scheme. Neptune checks the signature **and** the host name, which is why the tunnel needs the real host name (below). |
| **tunnel** | A temporary small container inside the private network plus an SSM port-forward, so your laptop can talk to the private Neptune database. |
| **approval record** | A text file you write (`docs/agent-runs/phase-14/human-gate.md`) naming the exact stage, commit, account hash and plan hash that you approve. The scripts refuse to run without it. |
| **pre-spend receipt** | A small JSON file you write before each paid stage stating money spent so far, reserves, and headroom (must be at least USD 3 for every spending stage; the `cleanup-prepare` stage has no headroom floor). |
| **commit freeze** | The rule that git HEAD must not change during the session, because every record names the exact commit. |
| **Haiku ledger** | A local file (`~/.scholarchain/llm-ledger/...`) that counts Haiku answers per bucket (14c 10, 15b 60, 16b 40, 17 5). |
| **H0, H35, H37** | H0 is the minute you start B1.2. Hours after H0 are written H1:30 and so on. H35 is the latest moment cleanup may start; H37 is the hard stop. |

**Money rule (read twice):** the whole project may spend at most **USD 25**, cumulative, including the USD 0.34 already spent. While the stack is up it costs about **USD 0.31 per hour before tax (about USD 0.35 per hour including about 11% sales tax)** even when idle. Sales tax counts toward the USD 25 cap. The budget alerts at USD 10, 15 and 20 are **only e-mails: they stop nothing, and billing data arrives 8 to 24 hours late.** Our own caps do the protecting. **Start cleanup (Section C) no later than H35, and never let the session pass H37.** If anything is going badly, going to cleanup early is always allowed.

---

## Timeline (planning estimates, not measurements)

| Hour mark | Block | Gate |
|---|---|---|
| Days before | A0 to A12 (free or nearly free) | A12 checklist ticked |
| H0:00 | B1 base plan, receipt, record; base-apply from about H0:30 | GO/NO-GO 1 |
| H1:30 | B2 validation CNAME; B3 push images | GO/NO-GO 2 |
| H2:30 | B4 runtime plan and runtime-apply | (decided in GO/NO-GO 3) |
| H3:30 | B5 api CNAME; B6 14B smoke | GO/NO-GO 3 and **checkpoint H6: 14B passed?** |
| H4:15 | B7 tunnel test | GO/NO-GO 4 |
| H4:45 to H10 | B8 14C data load and 8C vectors | GO/NO-GO 5 and **checkpoint H14: 14C done?** |
| H10 to H18 | B9 15A EMR (three runs) | GO/NO-GO 6 |
| H18 to H21 | B10 15B scaling experiment | GO/NO-GO 7 |
| H21 to H27 | B11 16B live evaluation | GO/NO-GO 8 |
| H27 to H31 | B12 demo video and final smoke | GO/NO-GO 9 |
| H31 to H34 | B13 evidence archive and downloads | GO/NO-GO 10 and **checkpoint H34: Phase 15 and 16 done?** |
| H34 | Section C cleanup starts (**latest H35, finished by the H37 hard stop**) | |

At each checkpoint decide with the coordinator whether to continue or move to cleanup. Phase 15 is never dropped.

---

# A. Before the session (free or nearly free)

Work through A0 to A12 in order, ticking the checklist at the end of the section. A6 (Bedrock) is a hard precondition and decides whether the final commit can exist, so start it early even though it is numbered late.

## A0. Decision point 2026-11-12: Bedrock quotas versus the fallback

Plain words: AWS currently gives this account zero quota for the AI models (Haiku 4.5, Titan V2, Nova). Without non-zero quotas the live answers and vector ingest cannot run.

1. **Where:** Console, Service Quotas and your open AWS Support case; plus chat with the coordinator.
2. **Do:**
   - Run A6 (steps below) as early as possible.
   - On 2026-11-10, if the Support case has no reply, escalate by chat.
   - On **2026-11-12** decide: **GO Bedrock** if all four quotas are non-zero and both playground calls succeed; otherwise **FALLBACK** (direct Anthropic API for answers and a third-party 256-dimension embedding API, described in the [fallback note](../agent-runs/phase-14/evidence/14b/replan/fallback-note.md)).
   - Write one paragraph in your own words with the decision and date.
3. **Success looks like:** your paragraph says "A0 = GO Bedrock" or "A0 = FALLBACK" with a date.
4. **If it fails (FALLBACK):** the coordinator routes the prepared fallback code for review and merge. That is a **new commit**, so everything done in A1 to A3 and A12 (commit, pins, images, JAR hashes) must be redone afterwards. Do not choose the session date before this decision.
5. **Save to:** `target/phase14/evidence/14b/a0-decision.md`.
6. **Tell the coordinator:** "A0 = GO Bedrock" or "A0 = FALLBACK".

## A1. Review, prepare the pre-session commit, and commit

Plain words: every record you write during the session names one exact git commit. This step makes that commit. It must contain everything the session needs, because nothing can be committed after the base plan.

**A1.1 Wait for the independent reviewer's APPROVE.**
- **Where:** coordinator chat.
- **Do:** wait until the coordinator says the reviewer's APPROVE is appended to `review.md`. You do not edit `review.md`, `prompt.md`, `owner-report.md` or `test-report.md`.
- **Success looks like:** the coordinator confirms "APPROVE recorded".
- **If it fails:** a reviewer finding means the owner repairs it and you restart A1 from the top once the coordinator says so.
- **Save to:** nothing.
- **Tell the coordinator:** nothing yet.

**A1.2 Reconfirm the tracked expiry date.**
- **Where:** T1.
- **Do:** `grep -n expiration_date infra/terraform/environments/course.tfvars`
- **Success looks like:** a line `expiration_date = "2026-11-25" # Provisional; reconfirm before deployment.` Decide whether the date is still right. If it must change, tell the coordinator (infra-engineer edits it); do not edit it yourself, it is a reviewed file.
- **If it fails:** a different date or missing line means stop and tell the coordinator.
- **Save to:** `target/phase14/evidence/14b/a1-expiration.log` (`| tee`).
- **Tell the coordinator:** "expiration_date confirmed 2026-11-25" or the change you need.

**A1.3 Flip the EMR price confirmation (G7).**
- **Where:** T1, editor. File `scripts/config/emr-pricing.conf`, line 23.
- **Do:** first open the two source URLs listed in that file (`EMR_PRICING_SOURCES`) in a browser and confirm the hourly rates in the file (m5.xlarge 0.192 EC2 plus 0.048 EMR). Only then change `EMR_PRICING_CONFIRMED_BY_HUMAN=false` to `EMR_PRICING_CONFIRMED_BY_HUMAN=true`. It must be inside the pre-session commit, because `run-bounded-pipeline.sh` refuses a dirty tree and cannot change it later.
- **Success looks like:** `grep -n EMR_PRICING_CONFIRMED_BY_HUMAN scripts/config/emr-pricing.conf` prints `23:EMR_PRICING_CONFIRMED_BY_HUMAN=true`.
- **If it fails:** if the rates on the pages differ from the file, do not flip; tell the coordinator.
- **Save to:** `target/phase14/evidence/14b/a1-emr-pricing.log` (`| tee`).
- **Tell the coordinator:** "EMR pricing confirmed, flag set to true".

**A1.4 Build the EMR JARs and render the experiment manifests with real hashes.**
- **Where:** T1.
- **Do:**
  1. Build the four job JARs (local only, nothing is uploaded):
     ```
     sbt -batch packageEmr 2>&1 | tee -a target/phase14/evidence/14b/a1-packageEmr.log; echo "exit=$?"
     ```
  2. Make sure the three input trees exist: `ls target/experiment-inputs/15a` must list `size-25`, `size-50`, `size-100` and three `*.subset.json`. If they are missing, run `python3 -I experiments/scripts/make_dblp_subsets.py` (it refuses to overwrite existing ones).
  3. Get the hashes the manifests need from the upload script's dry run (it makes no AWS call and writes nothing). Type your account ID at the prompt; it stays in your shell only. You also need the three local configuration files for `--er-policy`, `--er-config`, `--spark-config-template` (see the gap note below).
     ```
     read -r ACCT
     scripts/upload-emr-artifacts.sh --artifacts-bucket "scholarchain-course-${ACCT}-artifacts" --run-prefix <run-prefix> --region us-east-2 --input-dataset size-25=target/experiment-inputs/15a/size-25 --input-dataset size-50=target/experiment-inputs/15a/size-50 --input-dataset size-100=target/experiment-inputs/15a/size-100 --er-policy <er-policy file> --er-config <er-config file> --spark-config-template <spark-config-template file> 2>&1 | tee target/phase14/private/emr-upload-dry-a1.log | grep -E '^(EMR-RENDER|RESULT)'
     unset ACCT
     ```
  4. Render and check the manifests with the seven `--sha NAME=HEX` values the previous command printed:
     ```
     python3 -I experiments/scripts/render_manifests.py --overwrite --sha hadoop-submit-jar=<hex> --sha hadoop-libjars=<hex> --sha er-jar=<hex> --sha job-jar=<hex> --sha er-policy=<hex> --sha er-config=<hex> --sha spark-config-template=<hex>
     python3 -I experiments/scripts/check_manifests.py --final 2>&1 | tee target/phase14/evidence/14b/a1-check-manifests.log
     git diff --stat experiments/manifests
     ```
- **Success looks like:** `sbt` ends with `exit=0`; the dry run prints seven `EMR-RENDER: --sha ...` lines and a `RESULT: DRY-RUN` line; `check_manifests.py --final` prints `RESULT: OK`; the diff stat shows only the `15a-*` manifests changed (all-zero hashes replaced). The manifests hold bucket **tokens** only (`${SCHOLARCHAIN_ARTIFACTS_BUCKET}`), never your account ID.
- **If it fails:** any `CHECK-FAILED`/`CHECK-BLOCKED` line or a missing input file means stop and send `a1-check-manifests.log`. **Gap:** the repository does not say where the three files for `--er-policy`, `--er-config` and `--spark-config-template` come from; if you do not have them, stop and ask the coordinator (the experiment-engineer must supply them before the freeze).
- **Save to:** `target/phase14/evidence/14b/a1-packageEmr.log`, `a1-check-manifests.log`. The dry-run output goes to `target/phase14/private/` because it contains your bucket name.
- **Tell the coordinator:** "manifests rendered, check_manifests --final OK, jar manifest sha256 = `shasum -a 256 target/emr-artifacts/emr-artifact-manifest.json`".
- Later, A12 rebuilds the images; the four JAR hashes must be **unchanged** then (the JARs are byte-reproducible). If they differ, this step is stale: redo it.

**A1.5 Write `approval-14c.md` (the caps record for 14C).**
- **Where:** editor, new file `docs/agent-runs/phase-14/approval-14c.md` (you write it, in your own words; it is your record, not an agent's).
- **Do:** it must state, as wording only (no run-specific hashes, at most 64 KiB, never edited after you hash it):
  - Haiku 4.5: USD 1.33 total, in answer buckets 14c 10 / 15b 60 / 16b 40 / 17 5, each bucket a hard stop;
  - Titan: USD 0.30 (0.25 for the ingest, 0.05 for the query smoke);
  - EMR: USD 2.52 cumulative (3 runs of at most 90 minutes, about USD 0.84 each);
  - the project cap USD 25 and the hard stop H37;
  - the **N11 disclosure**, using the text under "Disclosure for `approval-14c.md`" in the [14C templates](../agent-runs/phase-14/evidence/14b/replan/14c-templates.md);
  - the statuses: R3 fixed, N15 fixed (same file, "Phase 8 findings status").
- **Success looks like:** `wc -c docs/agent-runs/phase-14/approval-14c.md` is under 65536 and the file mentions all five items.
- **If it fails:** if you cannot commit it before the freeze, keep it at `target/phase14/approvals/approval-14c.md` and move it into `docs/` only after Section C (then change the path in the approval JSONs).
- **Save to:** the file itself.
- **Tell the coordinator:** "approval-14c.md written" (no hash yet).

**A1.6 Do A2 now (refresh the pins), then come back to A1.7.**

**A1.7 Run the full check, then commit.**
- **Where:** T1 (a full check takes a long time; keep the terminal open).
- **Do:**
  ```
  scripts/check.sh 2>&1 | tee target/phase14/evidence/14b/a1-check-full.log; echo "exit=$?"
  git add -A
  git status --short | grep -Ei 'tfvars|tfplan|tfstate|\.env|secret|private' | grep -v '\.example$'
  git status --short | head -100
  git commit -m "Phase 14B replan: reviewed tree for the USD 25 session"
  git rev-parse HEAD
  git status --short
  ```
  `git add -A` stages every new file too, including `docs/runbooks/phase-14-live-session.md`, `experiments/`, `load-tests/`, `docs/agent-runs/phase-14/approval-14c.md` and the new Terraform/script/Scala files.
- **Success looks like:** `check.sh` ends `RESULT: PASS gates=7` with `exit=0`; the first `git status | grep` prints **nothing** (no private file is staged); after the commit `git status --short` prints nothing. `RESULT: PARTIAL` (exit 5) is **not** a pass.
- **If it fails:** a failed gate means stop and send `target/check-logs/<run-id>/` and the summary table. If the `grep` prints any line, do not commit; unstage it (`git restore --staged <path>`) and tell the coordinator.
- **Save to:** `target/phase14/evidence/14b/a1-check-full.log`.
- **Tell the coordinator:** "A1 done, HEAD=<sha>". Report the new HEAD after every later commit (A3 makes more). The base-plan HEAD is the last one.

## A2. Refresh `scripts/billing/reviewed-pins.json`

Plain words: this file pins the size and fingerprint (sha256) of 209 tracked files that the budget tool double-checks. Files changed by the replan no longer match, so the pins must be updated by you (agents may not edit it).

- **Where:** T1, repository folder.
- **Do:**
  1. Read-only drift check (local only):
     ```
     python3 -I -c 'import json,hashlib,os;d=json.load(open("scripts/billing/reviewed-pins.json"));bad=[r["path"] for r in d["source_freeze"] if (not os.path.exists(r["path"])) or os.path.getsize(r["path"])!=r["bytes"] or hashlib.sha256(open(r["path"],"rb").read()).hexdigest()!=r["sha256"]];print(len(d["source_freeze"]),"pinned;",len(bad),"drifted");print("\n".join(bad))' | tee target/phase14/evidence/14b/a2-pin-drift.log
     ```
  2. Refresh only the drifted rows (sets `bytes` and `sha256`, leaves everything else byte-for-byte):
     ```
     python3 -I -c 'import hashlib,json,os,sys;p=sys.argv[1];d=json.load(open(p));h=lambda f:hashlib.sha256(open(f,"rb").read()).hexdigest();n=[r.update(bytes=os.path.getsize(r["path"]),sha256=h(r["path"])) for r in d["source_freeze"] if os.path.exists(r["path"]) and (os.path.getsize(r["path"])!=r["bytes"] or h(r["path"])!=r["sha256"])];open(p,"w").write(json.dumps(d,indent=2)+"\n");print(len(n),"rows refreshed")' scripts/billing/reviewed-pins.json
     ```
  3. Check that only value lines changed, then repeat the drift check from 1.
     ```
     git diff --stat scripts/billing/reviewed-pins.json
     git diff scripts/billing/reviewed-pins.json | grep '^[+-] ' | grep -v '"bytes"\|"sha256"'
     ```
- **Success looks like:** first check prints `209 pinned; 24 drifted` (the 24 files listed in section 6 of the [approval request](../agent-runs/phase-14/approval-request-14b-replan.md)); the refresh prints `24 rows refreshed`; the second grep prints nothing; the repeated drift check prints `209 pinned; 0 drifted`. (The refresh command was tested on a scratch copy on 2026-11-08: it changed exactly those 24 rows, 96 changed lines, and nothing else.)
- **If it fails:** a path reported missing, or any changed line other than `bytes`/`sha256`, means stop and tell the coordinator. Any later commit that touches a file under `infra/terraform/` or `tests/` needs this refresh again.
- **Save to:** `target/phase14/evidence/14b/a2-pin-drift.log`.
- **Tell the coordinator:** drift count before and after, and `shasum -a 256 scripts/billing/reviewed-pins.json`. Then return to A1.7 (the pins are committed there). Step A3.10 adds the `modify` object and makes a second commit.

## A3. Budget modify to USD 25 (the FIRST LIVE STEP)

Plain words: the AWS Budget currently warns at 50/80/100% of USD 200. This changes it to a USD 25 budget with warnings at USD 10, 15 and 20. A special billing role and a purpose-built wrapper script do it. It changes only the budget (a monitor); it cannot spend money. Full detail: [billing README, "Phase 14B"](../../scripts/billing/README.md) and [VERIFICATION.md](../../scripts/billing/VERIFICATION.md). The numbers below are the README's step numbers.

- **Where:** T1, one terminal kept open the whole time, started with `umask 077`.
- **Paths to define first:**
  ```
  PRIMARY="/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap"
  BACKUPS="/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap-backups"
  ```

1. **README step 1:** the reviewed source is already committed in A1.7 (that is "commit C"). Record `git rev-parse HEAD`.
2. **Step 2:** `find scripts/billing -name __pycache__ -type d -prune -exec rm -r {} +` - success: no output.
3. **Step 3:** `shasum -a 256 scripts/billing/modify-public-inputs.template.json` - success: `946352f3a60b1d74e5c7b84fb21b06773fe8fe43dd05811ab5d9cc601660af28` (if a reviewer changed the file, recompute and report the new value).
4. **Step 4, sign in as the billing role (this is the only login step; the README calls it "unverified for this round", G16):**
   - Console: sign in as the IAM user `scholarchain-billing-operator` with MFA, then menu (account name, top right) > **Switch role** > account `<acct>`, role `scholarchain-billing-deployer` > **Switch Role**.
   - T1: `aws login --profile scholarchain-billing-deployer --region us-east-2`; in the browser choose the session that shows the **role**.
   - Check: `aws sts get-caller-identity --profile scholarchain-billing-deployer --region us-east-2`
   - Success: the `Arn` ends `assumed-role/scholarchain-billing-deployer/scholarchain-billing-operator`. Check the account without typing it: `printf '%s' "<the Account value printed>" | shasum -a 256` must print `32c67ff8da449cda3889494d51cb67b975431575cadce3aa6dc0da0aae60bf3e`.
   - If it fails: a user ARN or a different role means `aws logout --profile scholarchain-billing-deployer` and repeat. If Terraform later says "no credentials", the deployer README (G16) gives the `scholarchain-billing-login` workaround; ask the coordinator.
5. **Step 5:** back up and refresh the working config copy exactly as billing README step 5 says (copy six files and `tests/budget.tftest.hcl` from `infra/terraform/billing-bootstrap/` into `"$PRIMARY/config/"`, `chmod 600`; keep the `config-before-modify` backup). Success: `shasum -a 256` of each working copy equals the repository file.
6. **Step 6:** render the private inputs; type your account ID at the prompt, it is not stored:
   ```
   read -r ACCT; export ACCT
   python3 -I -c 'import hashlib,json,os,re,sys;t=json.load(open(sys.argv[1]));a=os.environ["ACCT"];assert re.fullmatch("[0-9]{12}",a);assert t["aws_account_id"]=="<acct>";t["aws_account_id"]=a;d=(json.dumps(t,indent=2)+"\n").encode();f=os.open(sys.argv[2],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(f,d);os.close(f);print(hashlib.sha256(d).hexdigest())' scripts/billing/modify-public-inputs.template.json "$PRIMARY/approved-public-inputs.modify.tfvars.json"; unset ACCT
   ```
   Success: one 64-hex line (the `modify.public_input_sha256` pin; note it).
7. **Step 7, make the saved plan** (the long `env -i ... terraform-1.13.5 plan ...` command in billing README step 7, copied exactly). Success: it prints `exit=2` (changes pending). A lock or init error means stop and report; never delete a lock file.
8. **Step 8, read the plan:** `grep -c '@' "$PRIMARY/billing-modify-plan.stdout.txt"` must print `0`; then run the README's `grep -E '^(Plan:|  # |...' ... | tee target/phase14/evidence/14b/budget-modify-plan.log`. Success: exactly `# aws_budgets_budget.project[0] will be updated in-place` and `Plan: 0 to add, 1 to change, 0 to destroy.` Anything else (replace, destroy, create, another resource) means STOP.
9. **Step 9:** `shasum -a 256`, `stat -f%z` and `stat -f%Lp` of `"$PRIMARY/billing.modify.tfplan"`; save to `target/phase14/evidence/14b/budget-modify-plan-binding.log`. Success: mode `600`. Note the hash and byte count.
10. **Steps 10 to 12, pins, gate record, gate JSON:**
    - Add the `modify` object to `scripts/billing/reviewed-pins.json` (README "Pins that become stale": `plan_sha256`, `plan_bytes`, `public_input_sha256`, and seven `config` rows with the repository file hash and byte size). Commit (commit C2).
    - Write the new modify human-gate record in your own words as a new committed file under `docs/agent-runs/phase-14/` (not under `evidence/14b/`): you approve this exact plan hash, the USD 25 target, the alerts at 10/15/20, the state backup and the time window. Commit it; this HEAD is the gate's `source_commit`.
    - Save the gate JSON privately as `"$PRIMARY/approval-<yyyymmdd>-modify.json"` (mode 600, window at most 1 hour; the field list is in billing README step 12) and compute `shasum -a 256` of it.
11. **Step 13, the apply, inside the gate window** (repeat step 4 first if the login is older than the gate allows):
    ```
    python3 -I scripts/billing/budget_execution.py modify --gate "$PRIMARY/approval-<yyyymmdd>-modify.json" --gate-sha256 <gate sha> --operation modify-<yyyymmdd>-01 2>&1 | tee target/phase14/evidence/14b/budget-modify-apply.log; echo "exit=$?"
    ```
    - **Success looks like:** `exit=0` and one JSON line with `"stage": "modify"`, `"applied": true`, `"already_at_target": false`, and a `verify` object with `"notification_count": 3`, `"email_subscribers_each": 1`, `"sns_subscribers": 0`, `"private_recipients_match": true`, `"delivery_verified": false`.
    - **If it fails:** a line like `{"code": "...", "status": "BLOCKED-ON"}` with exit 2 means stop. **Never re-run the same operation.** Send the log.
12. **Step 14:** report the exit code, the full log, `ls -l "$BACKUPS/modify-<yyyymmdd>-01"` and the `post_backup` sha256 and bytes.
13. **Step 15, independent verification (new window, new gate):**
    ```
    python3 -I scripts/billing/budget_verification.py verify-modified --gate <gate> --gate-sha256 <sha> --operation verify-usd25-<id> 2>&1 | tee target/phase14/evidence/14b/budget-modify-verify.log; echo "exit=$?"
    ```
    Success: `"stage": "verify"`, `"option": "M"`, `"notification_count": 3`, `"email_subscribers_each": 1`, `"private_recipients_match": true`, `"delivery_verified": false`. (The old Phase 12D `verify` mode now fails by design.)
14. **Step 16 (optional):** Console > Billing and Cost Management > **Budgets**: one budget, USD 25, three actual-cost alerts at $10, $15 and $20.
15. **Commit the wrapper's public packet and gate record** (it writes `public_packet_root` under `docs/agent-runs/phase-14/evidence/14b/`): `git add -A; git commit -m "Phase 14B: budget modify record"` before A4 and before the base plan. HEAD moves; that is fine because no plan exists yet.

- **Save to:** the `budget-modify-*.log` files named above, under `target/phase14/evidence/14b/`.
- **Tell the coordinator:** each step's report item (hashes, exit codes), the final HEAD, and "budget is USD 25 with alerts at 10/15/20". The pre-spend receipt field `monitoring_confirmed_active` depends on this.

## A4. Deployer apply (creates the roles; IAM only, free)

Plain words: the *deployer role* is the limited identity that will run Terraform in the session. This one-time apply, done with your own administrator profile, gives that role its permissions and creates the four operator roles. It creates only IAM objects, which cost nothing.

- **Where:** T1 with your MFA-authenticated **administrator** profile `$ADMIN`. **Never** with the `scholarchain-deployer` role.
- **Do:**
  1. Choose the `<run-prefix>` now (see Placeholders). Create the private file `infra/terraform/deployer/deployer.local.tfvars` (git-ignored; no secrets):
     ```
     account_id             = "<12-digit-account-id>"
     operator_principal_arn = "arn:aws:iam::<12-digit-account-id>:user/<your-iam-user>"
     owner                  = "<owner tag>"
     operator_roles_enabled = true
     operator_run_prefix    = "<run-prefix>"
     ```
     `operator_principal_arn` must be an IAM **user**, otherwise sessions are capped at 1 hour. Leave `operator_neptune_cluster_resource_id` unset.
  2. Back up the state and make the plan:
     ```
     STATE="$HOME/Library/Application Support/ScholarChain/terraform/spike-emr/deployer.tfstate"
     LOG="$REPO/target/phase14/evidence/14b/deployer-apply.log"
     test -f "$STATE" || echo "STATE FILE MISSING"
     BACKUP="$STATE.pre-replan-$(date -u +%Y%m%dT%H%M%SZ).bak"; cp "$STATE" "$BACKUP"; shasum -a 256 "$BACKUP" | tee -a "$LOG"
     cd "$REPO/infra/terraform/deployer"
     terraform version | tee -a "$LOG"
     AWS_PROFILE="$ADMIN" terraform init -input=false -lockfile=readonly 2>&1 | tee -a "$LOG"
     AWS_PROFILE="$ADMIN" terraform plan -input=false -state="$STATE" -var-file=deployer.local.tfvars -out="$REPO/target/phase14/private/deployer-replan.tfplan" 2>&1 | tee -a "$LOG"
     terraform show -no-color "$REPO/target/phase14/private/deployer-replan.tfplan" > "$REPO/target/phase14/private/deployer-replan.plan.txt"
     terraform show -json "$REPO/target/phase14/private/deployer-replan.tfplan" | jq -r '.resource_changes[] | select(.change.actions != ["no-op"]) | "\(.change.actions | join(",")) \(.address)"' | sort | tee -a "$LOG" | wc -l
     cd "$REPO"
     ```
  3. Read the **whole** file `target/phase14/private/deployer-replan.plan.txt`.
- **Success looks like (no apply yet):**
  - `Terraform v1.13.5`.
  - **Case A (expected: the state still holds the old test-cluster permission set):** `Plan: 29 to add, 0 to change, 9 to destroy.` (a `1 to change` for `tags_all`/`description` drift on `aws_iam_role.deployer` is acceptable) and the `jq` list has exactly **38** lines (29 create, 9 delete). Creates: 2 boundaries, 7 `permission_set["phase14-main--*"]` policies, 7 attachments, 4 operator roles, 5 operator data policies, 4 operator login policies. Destroys (9): the 4 `spike-emr--*` policies, their 4 attachments, `aws_iam_policy.spike_boundary[0]`.
  - **Case B (the 14A deployer apply was already done):** `Plan: 13 to add, 3 to change, 0 to destroy.` and **16** lines (changes: `keys-obs`, `main_boundary_runtime`, `data`).
- **STOP and do not apply if:** any replacement of `aws_iam_role.deployer` (`delete,create`, `-/+`, "must be replaced"); any address outside the lists above; `aws_iam_role_policy.login` changes; an operator role without `max_session_duration = 14400`; a wildcard `Principal`; an operator policy containing `aws-marketplace`, `"Resource": "*"`, or `iam:` other than `iam:PassRole`; the `data` policy's `s3:DeleteObject`/`DeleteObjectVersion` resource being anything other than `arn:aws:s3:::scholarchain-course-<acct>-*/*`; `s3:AbortMultipartUpload` outside the artifacts statement; the pipeline policy containing `RunJobFlow`, `TerminateJobFlows`, `ListClusters`, `AddTags`, any `s3:Delete*` or `iam:`. Full list: [proposal v2 STOP rules](../../infra/terraform/deployer/README.md#replan-w5a-14b-usd-25-course-cap-acm-ecs-exec-channels-and-the-operator-roles).
- **Do the apply only after the coordinator confirms your decision is recorded in the phase evidence** (a reviewed plan is not an approval to apply):
  ```
  cd "$REPO/infra/terraform/deployer"
  AWS_PROFILE="$ADMIN" terraform apply -state="$STATE" "$REPO/target/phase14/private/deployer-replan.tfplan" 2>&1 | tee -a "$LOG"; echo "exit=$?"
  cd "$REPO"
  shasum -a 256 "$STATE" | tee -a "$LOG"
  cp "$STATE" "$STATE.post-replan-$(date -u +%Y%m%dT%H%M%SZ).bak"
  ```
  Also copy both `.bak` files to Google Drive by hand.
- **Then verify (read-only):**
  ```
  aws iam list-attached-role-policies --role-name scholarchain-deployer --query 'length(AttachedPolicies)' --profile "$ADMIN"
  aws iam get-role --role-name scholarchain-deployer --query 'Role.MaxSessionDuration' --profile "$ADMIN"
  for k in loader reader cleanup pipeline; do aws iam get-role --role-name scholarchain-course-operator-$k --query 'Role.MaxSessionDuration' --profile "$ADMIN"; done
  aws iam list-role-policies --role-name scholarchain-course-operator-loader --query PolicyNames --profile "$ADMIN"
  aws iam list-role-policies --role-name scholarchain-course-operator-pipeline --query PolicyNames --profile "$ADMIN"
  AWS_PROFILE="$ADMIN" terraform -chdir="$(mktemp -d)" output -state="$STATE" operator_scope
  ```
  Success: `7`, `3600`, `14400` four times, loader policies `...-loader-data`, `...-loader-tunnel`, `...-loader-same-device-login`, pipeline policies `...-pipeline-data`, `...-pipeline-same-device-login`; `neptune_scope_is_fallback = true` in `operator_scope`.
- **If it fails:** `LimitExceeded` (11 attachments while the old ones detach): stop, re-plan, expect only the remaining attachment creates, re-apply; any other change is a STOP. `EntityAlreadyExists` on an operator role name: STOP, do not import. Any other error: stop and send `deployer-apply.log`. Do not hand-edit the state.
- **Save to:** `target/phase14/evidence/14b/deployer-apply.log`.
- **Tell the coordinator:** the backup sha256 (before), the state sha256 (after), the `Plan:` line, the `jq` line count, the verification outputs, and the `<run-prefix>` you chose (the label only).
- Optional (recommended skip): tightening the Neptune scope later is another deployer apply (3 in-place updates) and another gate.

## A5. `~/.aws/config` profiles and sign-in rehearsal

Plain words: a *profile* is a named login. We use one profile per role. The `-java` profiles exist because the Java programs cannot read `aws login` profiles directly; they ask the AWS command line for the same credentials instead.

- **Where:** a text editor (`~/.aws/config`), the Console, then T1. Do not open or paste `~/.aws/login/cache`.
- **Do:**
  1. Install/check tools: `aws --version` (must be 2.32.0 or newer for `aws login`); `brew install --cask session-manager-plugin` then `session-manager-plugin --version` (needed for the tunnel); `command -v aws` (use that absolute path below, `/opt/homebrew/bin/aws` is typical).
  2. Add these blocks to `~/.aws/config` (keep your existing admin and billing profiles; `aws login` writes the `login_session` line itself):
     ```
     [profile scholarchain-deployer]
     region = us-east-2

     [profile scholarchain-deployer-tf]
     credential_process = /opt/homebrew/bin/aws configure export-credentials --profile scholarchain-deployer --format process
     region = us-east-2

     [profile scholarchain-loader]
     region = us-east-2

     [profile scholarchain-reader]
     region = us-east-2

     [profile scholarchain-cleanup]
     region = us-east-2

     [profile scholarchain-pipeline]
     region = us-east-2

     [profile scholarchain-loader-java]
     credential_process = /opt/homebrew/bin/aws configure export-credentials --profile scholarchain-loader --format process
     region = us-east-2

     [profile scholarchain-reader-java]
     credential_process = /opt/homebrew/bin/aws configure export-credentials --profile scholarchain-reader --format process
     region = us-east-2

     [profile scholarchain-cleanup-java]
     credential_process = /opt/homebrew/bin/aws configure export-credentials --profile scholarchain-cleanup --format process
     region = us-east-2
     ```
     The scripts use **`scholarchain-deployer-tf`** for every Terraform script (`plan.sh`, `deploy.sh`, `cleanup.sh`, G11); you log in with `scholarchain-deployer` and the `-tf` profile re-reads that login. The pipeline role needs no `-java` profile (only the AWS command line uses it).
  3. Rehearse **each** role, one at a time (this proves sign-in before any money is spent). For role X in `deployer`, `loader`, `reader`, `cleanup`, `pipeline`:
     - Console: sign in as your IAM user with MFA; menu > **Switch role** > account `<acct>`, role name `scholarchain-deployer` (for the deployer) or `scholarchain-course-operator-<X>` > **Switch Role**. Click **Switch back** first if you are already in a role. Note the time.
     - T1: `aws login --profile scholarchain-<X> --region us-east-2`; in the browser pick the session that shows the **role**, not the user.
     - T1: `aws sts get-caller-identity --profile scholarchain-<X> --region us-east-2` (for the deployer also check `--profile scholarchain-deployer-tf`).
     - For loader, reader and cleanup also run the Java check: `sbt -batch 'storage / Compile / runMain edu.uic.cs441.scholarchain.storage.StorageLoadMain --check-credentials --profile scholarchain-<X>-java'`
     - `aws logout --profile scholarchain-<X>` when done.
  4. If Switch Role is refused with AccessDenied, read the caller policy from the deployer state (set `STATE` as in A4, then `AWS_PROFILE="$ADMIN" terraform -chdir="$(mktemp -d)" output -state="$STATE" operator_roles_caller_policy_json`) and attach it to your IAM user ([deployer README](../../infra/terraform/deployer/README.md)); ask the coordinator first.
- **Success looks like:** the `Arn` for X ends `assumed-role/scholarchain-deployer/<iam-user>` or `assumed-role/scholarchain-course-operator-<X>/<iam-user>`; the Java check prints `CREDENTIALS-RESOLVED: profile=scholarchain-<X>-java sessionToken=true expiresAt=<about 15 minutes ahead>`.
- **If it fails:** a user ARN (`:user/`) or another role means wrong browser session: `aws logout --profile scholarchain-<X>` and repeat. `CREDENTIALS-FAILED: ... reason=<Class>` (exit 1) means stop and send only that line.
- **Save to:** `target/phase14/evidence/14b/a5-login-rehearsal.log` (paste the `Arn` lines with `<acct>` and the `CREDENTIALS-*` lines).
- **Tell the coordinator:** one line per role: "Arn OK, CREDENTIALS-RESOLVED OK" or the failure class.
- **Risk to know now:** whether Terraform reads the `-tf` credential-process profile for a 1-hour deployer session is **unverified until live**.

## A6. Bedrock preconditions (hard precondition: no session if any fails)

Plain words: before spending anything, prove that AWS will actually answer model calls.

- **Where:** Console (region us-east-2) and T1 with `$ADMIN`.
- **Do:**
  1. Console > **Service Quotas** > AWS services > **Amazon Bedrock**. Search "Claude Haiku 4.5" and check the cross-region tokens-per-minute, requests-per-minute and tokens-per-day; search "Titan Text Embeddings V2" and check the on-demand InvokeModel requests-per-minute and tokens-per-minute. The exact quota names are not in the repository; use these search terms. Take screenshots into `target/phase14/evidence/14b/a6-*.png`.
  2. Console > **Amazon Bedrock** > **Playgrounds** > Chat > select **Anthropic Claude Haiku 4.5** (the US inference profile) > send "Reply with the single word OK." The first call creates the AWS Marketplace subscription.
  3. Console > **AWS Marketplace** > **Manage subscriptions**: a Claude Haiku 4.5 entry should be listed.
  4. Titan call (costs a fraction of a cent):
     ```
     aws bedrock-runtime invoke-model --model-id amazon.titan-embed-text-v2:0 --body '{"inputText":"hello","dimensions":256,"normalize":true}' --cli-binary-format raw-in-base64-out --region us-east-2 --profile "$ADMIN" target/phase14/private/titan-probe.json 2>&1 | tee -a target/phase14/evidence/14b/a6-bedrock-precondition.log
     test -s target/phase14/private/titan-probe.json && echo "titan-probe non-empty"
     ```
  5. Routing check:
     ```
     aws bedrock get-inference-profile --region us-east-2 --inference-profile-identifier us.anthropic.claude-haiku-4-5-20251001-v1:0 --query 'models[].modelArn' --profile "$ADMIN" 2>&1 | tee -a target/phase14/evidence/14b/a6-bedrock-precondition.log
     ```
- **Success looks like:** every quota value is greater than 0; the playground replies with text; a Marketplace entry exists; the Titan command prints `{"contentType": "application/json"}` and `titan-probe non-empty`; three model ARNs (us-east-1, us-east-2, us-west-2) are returned. Do not print `titan-probe.json` (256 numbers). If the console asks you to enable model access, enable it in all three regions. (All of this is **unverified until live**.)
- **If it fails:** `ThrottlingException: Too many tokens per day` means the quota is still not granted: STOP and go back to A0 (escalate the Support case). Do not start the session.
- **Billing fact to carry:** Haiku is a Marketplace charge on your card, outside the credits; Titan is credit-covered. No application role gets Marketplace permissions.
- **Save to:** `target/phase14/evidence/14b/a6-bedrock-precondition.log`.
- **Tell the coordinator:** "Haiku quotas non-zero Y/N; Titan quotas non-zero Y/N; Haiku playground OK Y/N; Titan call OK Y/N; Marketplace subscription listed Y/N".

## A7. Secrets Manager secrets (you create them; the values are never shown)

Plain words: the services need four secret strings. You create them in Secrets Manager by hand so the values never enter git or Terraform; Terraform only learns each secret's address (ARN). They bill about USD 0.40 per secret per month (prorated).

- **Where:** T1 with `$ADMIN` (or Console > Secrets Manager > Store a new secret > Other type > Plaintext, **default encryption key**; do not use the project KMS key, it is destroyed at cleanup).
- **The four secrets:**

| Name | Value | Used as |
|---|---|---|
| `scholarchain/course/api-key-sha256` | sha256 hex of the raw API key | `SCHOLARCHAIN_API_KEY_SHA256`, all four services |
| `scholarchain/course/internal-token-sha256` | sha256 hex of the raw internal token (must differ from the API-key hash) | `SCHOLARCHAIN_INTERNAL_TOKEN_SHA256`, all four services |
| `scholarchain/course/internal-token` | the raw internal token | `SCHOLARCHAIN_INTERNAL_TOKEN`, query-api only |
| `scholarchain/course/graph-cursor-key` | random string, at least 16 characters | `SCHOLARCHAIN_GRAPH_CURSOR_KEY`, graph-service only |

- **Do:** the value must be exactly the string (no newline, no quotes). Nothing is printed or put in the command line:
  ```
  W="$(mktemp -d)"
  export SCHOLARCHAIN_SMOKE_API_KEY="$(openssl rand -hex 32)"
  printf '%s' "$SCHOLARCHAIN_SMOKE_API_KEY" | pbcopy
  ```
  Paste the key into your password manager now, then clear the clipboard with `pbcopy </dev/null`. Continue:
  ```
  printf '%s' "$SCHOLARCHAIN_SMOKE_API_KEY" | shasum -a 256 | cut -d' ' -f1 | tr -d '\n' > "$W/api-key-sha256"
  python3 -I -c 'import secrets;print("internal-"+secrets.token_urlsafe(32),end="")' > "$W/internal-token"
  shasum -a 256 < "$W/internal-token" | cut -d' ' -f1 | tr -d '\n' > "$W/internal-token-sha256"
  python3 -I -c 'import secrets;print(secrets.token_urlsafe(32),end="")' > "$W/graph-cursor-key"
  for n in api-key-sha256 internal-token-sha256 internal-token graph-cursor-key; do aws secretsmanager create-secret --name scholarchain/course/$n --secret-string file://"$W/$n" --region us-east-2 --profile "$ADMIN" --query Name --output text; done 2>&1 | tee -a target/phase14/evidence/14b/a7-secrets.log
  rm -r "$W"
  unset SCHOLARCHAIN_SMOKE_API_KEY
  for n in api-key-sha256 internal-token-sha256 internal-token graph-cursor-key; do echo "$n $(aws secretsmanager describe-secret --secret-id scholarchain/course/$n --query ARN --output text --region us-east-2 --profile "$ADMIN")"; done > target/phase14/private/secret-arns.txt
  cut -d' ' -f1 target/phase14/private/secret-arns.txt
  ```
  The ARN file is private (it contains your account ID): copy each ARN into `service_secret_bindings` in A8. One ARN may be reused by several services. **Never** run `aws secretsmanager get-secret-value`. Later, re-enter the raw key in a shell with `read -rs SCHOLARCHAIN_SMOKE_API_KEY; export SCHOLARCHAIN_SMOKE_API_KEY` (paste from the password manager, Enter).
- **Success looks like:** the loop prints the four secret names, then the final `cut` prints the four names again.
- **If it fails:** `ResourceExistsException` means that name already exists: do not overwrite; tell the coordinator.
- **Save to:** `target/phase14/evidence/14b/a7-secrets.log` (names only).
- **Tell the coordinator:** "4 secrets created: api-key-sha256, internal-token-sha256, internal-token, graph-cursor-key".

## A8. Private tfvars (`infra/terraform/environments/course.local.tfvars`, names only)

Plain words: this git-ignored file holds your real values. You copy `course.local.tfvars.example` ([example](../../infra/terraform/environments/course.local.tfvars.example)) and edit it. Never send its contents to the coordinator; you only report which variables are set.

- **Where:** editor; `cp infra/terraform/environments/course.local.tfvars.example infra/terraform/environments/course.local.tfvars`.
- **Do:** set these (names only here). The same file is edited between stages; the table says what each plan needs.

| Variable(s) | Base plan (B1) | First runtime plan (B4) | Pointer plan (B8.4) | EMR plan (B9.3) |
|---|---|---|---|---|
| `aws_account_id`, `availability_zones` (exactly two), `deployment_trusted_principal_arn`, `budget_limit_usd = 25` | set | set | set | set |
| `neptune_enabled = true`, `neptune_engine_version`, `neptune_parameter_family` | set | set | set | set |
| `embedding_model_id = "amazon.titan-embed-text-v2:0"`, `synthesis_model_id = "anthropic.claude-haiku-4-5-20251001-v1:0"`, `synthesis_inference_profile_id = "us.anthropic.claude-haiku-4-5-20251001-v1:0"`, `synthesis_inference_profile_regions = ["us-east-1","us-east-2","us-west-2"]` | set | set | set | set |
| `container_insights_enabled = false`, `dashboard_enabled = false`, `service_capacity` (four services: `cpu = 256, memory = 1024, min = 1, max = 2`) | set | set | set | set |
| `api_domain_name = "api.<domain>"`, `acm_validation_timeout = "15m"` (do **not** set `https_certificate_arn`; exactly one of the two is allowed) | set | set | set | set |
| the three Q8 values: `embedding_model_version = "amazon.titan-embed-text-v2:0"`, `embedding_text_prefix = "embedding-text"`, `semantic_index_name = "researcher-profile-v1"` | may be set | set | set | set |
| `runtime_enabled`, `runtime_composition_verified` | `false`, `false` | `true`, `true` | `true`, `true` | `true`, `true` |
| `service_secret_bindings` (four services, ARNs only) | `{}` | set | set | set |
| `public_ingress_cidrs` (your public IP, see below) | `[]` | `["<ip>/32"]` | same | same |
| `neptune_tunnel_enabled = true` | `false` | **`true`** (must be in the FIRST runtime plan, G12) | `true` | `true` |
| `query_health_check_grace_period_seconds = 300` | optional | set | set | set |
| `runtime_artifact_key`, `runtime_artifact_sha256`, `runtime_artifact_source_run_id` (and optional `runtime_artifact_bucket`, must equal the rag bucket) | unset | unset | **set all three** (G3) | keep |
| `emr_config` (enabled, runtime_verified, runtime_reference, bootstrap_uri/sha256, runtime_archive_uri, job_jar_uri/sha256, four `extra_artifacts`), `emr_service_policy_json` | `enabled = false` | `enabled = false` | `enabled = false` | **set** (G18) |

- Get your public IP with `curl -s https://checkip.amazonaws.com`. If your home IP changes during the session the ALB stops answering you (see E8); fixing it takes a new runtime plan and apply.
- `emr_service_policy_json` is built from `environments/emr-service-policy.json.example` with the placeholders replaced; the rules are in the [Terraform README, "EMR service policy review"](../../infra/terraform/README.md); ask the coordinator to review the text before B9.
- **Success looks like:** `git check-ignore -v infra/terraform/environments/course.local.tfvars` prints a line containing the `*.tfvars` rule (and `git status --short` does not list the file).
- **If it fails:** if the file is not ignored, stop and tell the coordinator; never commit it.
- **Save to:** `target/phase14/evidence/14b/a8-tfvars-check.log` (`| tee` of the `git check-ignore` output).
- **Tell the coordinator:** "tfvars complete: base set Y/N, runtime set staged Y/N". Never send values.

## A9. Cloudflare CAA check

Plain words: a CAA record can forbid AWS from issuing your certificate. We check and, only if needed, allow `amazon.com`.

- **Where:** CF > DNS > Records (filter type **CAA**) and T1.
- **Do:** `dig +short CAA <domain>` and `dig +short CAA api.<domain>` (the lookup walks up the name tree). Save both outputs.
- **Success looks like:** empty output (no CAA, nothing to do), or a record that includes `0 issue "amazon.com"` (also accepted: `amazontrust.com`, `awstrust.com`, `amazonaws.com`).
- **If it fails:** if a CAA exists that allows only other companies: CF > **Add record** > Type **CAA**, Name `@`, Flags `0`, Tag **Only allow specific hostnames**, Value `amazon.com`, Save. Re-run `dig`.
- **Save to:** `target/phase14/evidence/14b/a9-caa.log` (`| tee -a` the two `dig` commands; it contains your domain, keep it local).
- **Tell the coordinator:** "CAA: none / already allows amazon.com / added".

## A10. Initialize the Haiku answer ledger

Plain words: the ledger is a local counter that makes the Haiku buckets (14c 10 / 15b 60 / 16b 40 / 17 5) hard stops. Every step that can call Haiku reserves answers first.

- **Where:** T1.
- **Do:**
  ```
  python3 -I load-tests/llm_budget.py init 2>&1 | tee -a target/phase14/evidence/14b/a10-llm-ledger.log
  python3 -I load-tests/llm_budget.py status 2>&1 | tee -a target/phase14/evidence/14b/a10-llm-ledger.log
  ```
- **Success looks like:** `init` exits 0 (it records the sha256 of `experiments/manifests/llm-allocation.json`); `status` shows four buckets with sizes 10, 60, 40, 5, none used, and the USD 1.33 cap. The exact output text is **unverified until live**.
- **If it fails:** `init` refuses when the ledger already exists; do not delete it by hand. Tell the coordinator what `status` shows. `ALLOCATION-CHANGED` in `status` means the allocation file differs from the one the ledger was created with: stop and ask.
- **Save to:** `target/phase14/evidence/14b/a10-llm-ledger.log`.
- **Tell the coordinator:** the `status` lines.

## A11. Keep the Mac awake and the network steady

- **Where:** T4 (a terminal you leave alone) and the Mac settings.
- **Do:** plug in the charger, disable automatic sleep for the session, and run in T4: `caffeinate -dims`. Use a steady network; do not change Wi-Fi or VPN during the session (your public IP is allow-listed for the ALB).
- **Success looks like:** T4 stays running with no output; `pmset -g assertions | grep -i caffeinate` shows an active assertion.
- **If it fails:** if the Mac sleeps mid-command, a running `--execute` script may be killed; see E2 and E7 for what to do (do not re-run blindly).
- **Save to:** nothing.
- **Tell the coordinator:** nothing.

## A12. Final pre-flight (images, ledgers, 14C inputs, clean tree)

- **Where:** T1, Docker Desktop running.
- **Do:**
  1. Build the images on the final clean HEAD (never a `-dirty` build):
     ```
     scripts/package.sh 2>&1 | tee target/phase14/evidence/14b/a12-package.log; echo "exit=$?"
     docker image ls 'scholarchain-*'
     ```
  2. Confirm the runtime archive file the base-apply stage uploads: `shasum -a 256 target/phase12d-runtime-repair-20261103/artifacts/scholarchain-spark3.5.4-scala2.13.14-java17-runtime.tgz` and `ls -l` the same file.
  3. Confirm the JAR hashes are unchanged: `shasum -a 256 target/emr-artifacts/emr-artifact-manifest.json` equals the value you reported in A1.4.
  4. Create the EMR run ledger (a local file; it refuses if it already exists): `scripts/run-bounded-pipeline.sh --init-ledger 2>&1 | tee -a target/phase14/evidence/14b/a12-emr-ledger.log`
  5. Prepare the local 14C inputs under `target/phase14/14c-work/` (all local, free):
     - the completed Phase 6 export (already made: `target/phase6-runs/14c-spark-export-capped/run:f6e63b4b-d542-4a32-930c-f21f002cba76`; the `:` in the name needs quotes; see [real-slice-export.md](../agent-runs/phase-14/evidence/14b/replan/real-slice-export.md));
     - `include-ids.txt` (one stable ID per line, `researcher:...` or `work:...`, at most 2000, lines starting with `#` ignored: the entities your smoke question and the 15B/16B questions mention);
     - `real-query.json` (body `{"question":"<a real question naming an entity in the loaded data>","output":{"includeScores":false}}`), `questions.txt` (one question per line, for 15B/16B), `node-ids.txt` (graph node IDs, one per line, for 15B);
     - **Gap:** the repository contains no real `include-ids.txt`, `real-query.json`, `questions.txt` or `node-ids.txt`, and no recipe for producing them from the export ([storage README](../../modules/storage/README.md), "Include list format"). Ask the coordinator who supplies them. Without them B8.2, B8.8, B10 and B11 cannot run as written.
  6. Check the dry runs make no cloud call: `scripts/upload-slice.sh --export-dir "target/phase6-runs/14c-spark-export-capped/run:f6e63b4b-d542-4a32-930c-f21f002cba76" --run-prefix <run-prefix> --bucket "scholarchain-course-<acct>-curated" --region us-east-2` (replace `<acct>` in the terminal only) should end `RESULT: DRY-RUN`.
  7. Final state: `git status --short` prints nothing and `git rev-parse HEAD` is the value every record will name.
- **Success looks like:** `package.sh` ends with exit 0 and `target/release/<sha>/release-manifest.json` exists; four `scholarchain-*` images are listed; the archive sha256 is `789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5` and the size is `321876735` bytes; the ledger command prints `RESULT: PASS`; the upload dry run prints `EXPORT-RUN:` totals and `RESULT: DRY-RUN`; the tree is clean.
- **If it fails:** a `-dirty` tag or a changed JAR hash means a commit slipped in: stop and tell the coordinator (A1.4 and the images must be redone). Docker unreachable: start Docker Desktop and re-run.
- **Save to:** `target/phase14/evidence/14b/a12-package.log`, `a12-emr-ledger.log`.
- **Tell the coordinator:** "A12 done, HEAD=<sha>, images built, JAR manifest hash unchanged".

### A checklist (tick everything before H0)

- [ ] A0 decision recorded (GO Bedrock, or FALLBACK merged and A1 redone)
- [ ] A1 reviewer APPROVE seen; EMR flag true; manifests rendered; `approval-14c.md` committed; `check.sh` PASS gates=7; committed; HEAD noted
- [ ] A2 pins: `209 pinned; 0 drifted` (and `modify` object added in A3)
- [ ] A3 budget is USD 25 with alerts at 10/15/20 (apply log and verify log both OK); packet and gate record committed
- [ ] A4 deployer applied; verification outputs as expected; state backups copied to Drive
- [ ] A5 all five roles rehearsed (Arn shapes OK; three CREDENTIALS-RESOLVED lines)
- [ ] A6 four quotas non-zero; both playground/Titan calls OK; Marketplace subscription listed
- [ ] A7 four secrets created; ARN list saved privately
- [ ] A8 `course.local.tfvars` complete for the base plan; ignored by git
- [ ] A9 CAA none or allows `amazon.com`
- [ ] A10 Haiku ledger initialised
- [ ] A11 charger, no sleep, `caffeinate` running
- [ ] A12 images built on the final HEAD; EMR ledger created; 14C input files exist; tree clean

---

# B. The session (H0 is the start of B1.2)

Money is spent from the first apply until the last cleanup pass. Keep the clock: write the UTC time at every GO/NO-GO box in `target/phase14/evidence/14b/session-clock.log` (`date -u | tee -a ...`).

## B0. Session start (about 15 minutes before H0)

- **Where:** Console and T1.
- **Do:**
  1. Console: sign in as your IAM user with MFA (fresh). In T1: `date -u | tee -a target/phase14/evidence/14b/session-clock.log` and `date -u +%s > target/phase14/private/h0.epoch` (used later to set approval expiry to H0 + 37 hours).
  2. Console > **Billing and Cost Management** > **Cost Explorer**: group by Service, date range from the project start, and untick **Credits** and **Refunds** under Charge type (the USD 25 cap counts usage regardless of credits; confirm this setting with the coordinator). Note the total and the "data through" date. Then Billing > **Budgets**: one budget, USD 25, alerts at 10/15/20.
  3. T1: `git status --short` (must print nothing), `git rev-parse HEAD` (must equal the A12 HEAD), `curl -s https://checkip.amazonaws.com` (must equal the IP in your tfvars), `python3 -I load-tests/llm_budget.py status` (nothing used).
- **Success looks like:** the three checks above agree; the budget page shows USD 25 with three alerts.
- **If it fails:** a dirty tree, a different HEAD or a different IP means stop; tell the coordinator (HEAD change = redo A12; IP change = update `public_ingress_cidrs` before B4).
- **Save to:** `target/phase14/evidence/14b/b0-start.log` (paste the outputs; screenshots to `target/phase14/evidence/14b/b0-*.png`).
- **Tell the coordinator:** H0 time in UTC, cost-to-date and its data period.

## Procedure R: the pre-spend receipt and the approval record (used by B1, B3, B4, B8.4, B9.3 and C2)

Plain words: before every paid stage you write two small files. The *receipt* says how much money is spent and reserved. The *record* says "I approve exactly this stage, commit, account and plan". The script refuses to run unless both are valid and match.

**R.1 Work out the four numbers** (the coordinator gives you the final values; you check the arithmetic):
- `reported_spend_usd`: the Cost Explorer total from B0.2 (gross usage since the project started; USD 0.34 at the start). It is the Cost Explorer total as shown, which already includes sales tax, so do not add tax again.
- `unreported_usage_allowance_usd`: spend that has happened since the last data day Cost Explorer shows (billing lags 8 to 24 h). Use (hours since that data day times USD 0.3096 (about 0.31), plus Haiku answers used so far times USD 0.01155, plus a margin) times 1.11 (the factor 1.11 adds the about 11% sales tax, because tax counts toward the USD 25 cap). Reserves count only up to H36 but the hard stop is H37, so the margin must be at least about USD 0.35 (one hour with tax) on every receipt after H0; the coordinator states the margin when giving the values.
- `reserves_usd`: money still to be spent until the end of cleanup, including sales tax: (remaining hours to H36 times USD 0.3096 (about 0.31), plus USD 3.58 (fixed charges 1.17 and usage 2.41, counted in full to be safe), plus USD 0.05 tunnel if not yet run, plus the unspent caps (Titan 0.30, EMR 2.52, Haiku 1.33)) times 1.11.
- `remaining_headroom_usd` = 25 - reported - unreported - reserves. It must be **at least 3** for every spending stage. The `cleanup-prepare` stage has **no headroom floor**: a negative headroom is accepted there, so overspend never blocks cleanup. Its receipt must still exist, match its approved sha256, be fresh (within 24 h), show monitoring confirmed and carry all four numeric cost fields.
- *Example at H0 (modeled from the [approval request](../agent-runs/phase-14/approval-request-14b-replan.md), section 3.2, with EMR at its USD 2.52 cap):* reserves before tax = 11.15 + 1.17 + 2.41 + 0.05 + 0.30 + 2.52 + 1.33 = 18.93; with tax, 18.93 x 1.11 = 21.01 (rounded to cents). The allowance is 0.50 x 1.11 = 0.56. With reported 0.34 the headroom is 25 - 0.34 - 0.56 - 21.01 = 3.09, which is at least 3. This is tight, so if any stage's receipt comes out below 3, stop new paid work and go to cleanup (E12). For a spending stage the scripts check only that the number you write is at least 3, not the arithmetic, so the coordinator checks it.

**R.2 Write the receipt** (numbers are JSON numbers, no quotes; `cost_snapshot_utc` is the time you read Cost Explorer, at most 24 h old at every paid operation):
```
cat > target/phase14/prespend-receipt.json <<'EOF'
{
  "schema": "scholarchain.prespend-receipt.v1",
  "monitoring_confirmed_active": true,
  "cost_snapshot_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "reported_spend_usd": 0.34,
  "unreported_usage_allowance_usd": 0.56,
  "reserves_usd": 21.01,
  "remaining_headroom_usd": 3.09
}
EOF
shasum -a 256 target/phase14/prespend-receipt.json
```
(Replace the example numbers and the time.) The printed hash goes into the record as `APPROVED_PRESPEND_SHA256`.

**R.3 Write the approval record** in your own words as `docs/agent-runs/phase-14/human-gate.md` (overwritten for every stage; it is the only file exempt from the clean-tree check, and you never `git add` it):
```
# Phase 14 human gate - stage <stage> - serial <n>

In my words: I approve this stage. Ceiling USD 25 total, cumulative, including USD 0.34 already spent.
Reported cost to date USD <x>, data period <...>, read at <UTC time>. Unreported estimate USD <x>.
Reserves USD <x>. Remaining headroom USD <x>. Stage allowance: <...>.
Start <UTC>, planned end <UTC>; cleanup starts no later than H35 (<UTC>); hard stop H37 (<UTC>).
Authorized commands for this stage: <the exact command>.

APPROVED_STAGE=<base-apply or push or runtime-apply or cleanup-prepare>
APPROVED_COMMIT=<sha>
APPROVED_ACCOUNT_SHA256=<64 lowercase hex>
APPROVED_REGION=us-east-2
APPROVED_ENVIRONMENT=course
APPROVED_PRESPEND_SHA256=<hash from R.2>
APPROVED_PLAN_SHA256=<from plan.sh or cleanup.sh>
APPROVED_RECEIPT_SHA256=<from plan.sh or cleanup.sh>
```
Rules: each `APPROVED_` key appears **exactly once**, lowercase hex, no quotes, no trailing comment, no carriage return; **delete the last two lines for the `push` stage** (a push record naming a plan is refused); prose must not start with `APPROVED_`; an unknown `APPROVED_` key is refused; no e-mail address. `APPROVED_ACCOUNT_SHA256` is printed as a candidate line by `plan.sh`; it should equal `32c67ff8da449cda3889494d51cb67b975431575cadce3aa6dc0da0aae60bf3e` (the account hash from A3; this assumes the billing account and the deployment account are the same account, **unverified until live**). If it differs, stop and ask the coordinator before you write anything.

**R.4 Dry run, then execute.** Every `deploy.sh` stage can be run without `--execute` first: it checks your record, receipt, plan hashes and the clean tree locally with **no AWS call** and ends `RESULT: DRY-RUN`. Exit 3 there costs nothing; fix and repeat.

**R.5 Archive after the stage:** `cp docs/agent-runs/phase-14/human-gate.md target/phase14/approvals/<label>.md` and `cp target/phase14/prespend-receipt.json target/phase14/approvals/prespend-<label>.json`.

## B1. Base plan, receipt, record, base-apply (H0:00 to about H1:15)

Plain words: the *base plan* lists everything the network, database, storage, keys and image shelves need. It deliberately leaves the running services off. `base-apply` then builds it. From base-apply on you are billed (NAT, Neptune).

**B1.1 Pre-flight.**
- **Where:** T1.
- **Do:**
  ```
  git status --short; git rev-parse HEAD
  git check-ignore -v infra/terraform/environments/course.local.tfvars
  test ! -e infra/terraform/terraform.tfstate && echo "no main state yet (expected)"
  read -r ACCT
  export SCHOLARCHAIN_RUNTIME_ARCHIVE_S3_URI="s3://scholarchain-course-${ACCT}-artifacts/emr/<run-prefix>/runtime/scholarchain-spark3.5.4-scala2.13.14-java17-runtime.tgz"
  unset ACCT
  echo "$SCHOLARCHAIN_RUNTIME_ARCHIVE_S3_URI" > target/phase14/private/runtime-archive-uri.txt
  ```
  Your tfvars must be in the **base state** (A8 table, first column).
- **Success looks like:** empty `git status`; the expected HEAD; an ignore rule line; the text "no main state yet (expected)".
- **If it fails:** a state file already exists means a previous attempt; stop and tell the coordinator (the base plan then needs different flags).
- **Save to:** `target/phase14/evidence/14b/b1-preflight.log`.
- **Tell the coordinator:** "pre-flight OK at HEAD=<sha>".
- The archive key must later equal `emr_config.runtime_archive_uri` (B9); the file above keeps it.

**B1.2 Sign in as the deployer (fresh).**
- **Where:** Console, then T1.
- **Do:** Console: Switch back, then **Switch role** > `scholarchain-deployer`. T1: `aws login --profile scholarchain-deployer --region us-east-2` (pick the **role** session), then `aws sts get-caller-identity --profile scholarchain-deployer-tf --region us-east-2`.
- **Success looks like:** the `Arn` ends `assumed-role/scholarchain-deployer/<iam-user>`.
- **If it fails:** wrong ARN means `aws logout --profile scholarchain-deployer` and repeat.
- **Save to:** `target/phase14/evidence/14b/b1-identity.log`.
- **Tell the coordinator:** "H0 = <UTC time>, deployer identity OK".

**B1.3 Make the base plan.**
- **Where:** T1.
- **Do:**
  ```
  scripts/plan.sh --env course --region us-east-2 --profile scholarchain-deployer-tf --expect-new-state --execute 2>&1 | tee target/phase14/evidence/14b/base-plan.log; echo "exit=$?"
  ```
- **Success looks like:** `exit=0`; lines `PLAN-TEXT: <path> sha256=<hex>`, `PLAN-ACTIONS-BEGIN count=N` ... `PLAN-ACTIONS-END count=N`, `summary: add=N change=0 destroy=0 replace=0 ...`, `PLAN-FILE: <path>`, `PLAN-RECEIPT: <path> sha256=<hex>`, candidate lines `APPROVED_PLAN_SHA256=`, `APPROVED_RECEIPT_SHA256=`, `APPROVED_COMMIT=`, `APPROVED_ACCOUNT_SHA256=`, and the final `RESULT: PASS plan recorded, not applied; ...`.
- **Then read it:**
  ```
  grep '^PLAN-ACTION:' target/phase14/evidence/14b/base-plan.log | grep -vc '^PLAN-ACTION: create '
  grep '^PLAN-ACTION:' target/phase14/evidence/14b/base-plan.log | grep -E 'module\.emr|aws_lb|aws_ecs_service|aws_acm_certificate_validation'
  grep -E 'will be (destroyed|replaced|updated)|must be replaced' "<PLAN-TEXT path>"
  less "<PLAN-TEXT path>"
  ```
  The first must print `0`; the second and third must print nothing. Every action must be `create`. Expect to see the certificate `aws_acm_certificate.api[0]`, `module.neptune.*`, `module.network.*` (NAT, EIP, S3 endpoint), `module.identity.aws_kms_key.data`, `module.datalake.*`, `module.s3vectors.*`, the ECR repositories, the ECS cluster and IAM roles. Read the whole plan text; it is private, never share it.
- **STOP signs:** any `delete`, `replace` or `update`; any runtime object (ECS service, load balancer, listener, certificate validation) or anything under `module.emr` (the runtime and EMR must be off in the base plan).
- **If it fails:** exit 3 (missing/existing state, wrong Terraform, dirty tree, tfvars not ignored) means fix and re-run once; exit 4 or 5 means stop and send `base-plan.log`.
- **Save to:** `target/phase14/evidence/14b/base-plan.log`.
- **Tell the coordinator:** HEAD, `PLAN-ACTIONS count`, the `summary:` line, the plan and receipt sha256 values. The coordinator compares the action list with the cost plan.

> **The commit freeze starts now** (Section D). Do not commit or edit tracked files until Section C is finished.

**B1.4 Receipt and record for `base-apply`** (Procedure R). `APPROVED_STAGE=base-apply`; the plan and receipt hashes come from B1.3.
- **Tell the coordinator:** the four receipt numbers and the headroom (never the account ID).

**B1.5 Fresh deployer session, then dry run, then base-apply.**
- **Where:** Console, then T1.
- **Do:** Switch back, Switch role to `scholarchain-deployer`, `aws login --profile scholarchain-deployer --region us-east-2`, check `aws sts get-caller-identity --profile scholarchain-deployer-tf`. Then run immediately:
  ```
  scripts/deploy.sh --stage base-apply --plan "<PLAN-FILE from B1.3>" --region us-east-2 --profile scholarchain-deployer-tf 2>&1 | tee target/phase14/evidence/14b/base-apply-dry.log
  scripts/deploy.sh --stage base-apply --plan "<PLAN-FILE from B1.3>" --region us-east-2 --profile scholarchain-deployer-tf --execute 2>&1 | tee target/phase14/evidence/14b/base-apply.log; echo "exit=$?"
  ```
  Expect about 30 to 60 minutes (Neptune, NAT, then the 322 MB runtime archive upload). If the first command is not `RESULT: DRY-RUN`, do not run the second.
- **Success looks like:** the dry run ends `RESULT: DRY-RUN`. The real run prints in order `STEP:` `terraform-version`, `clean-tree`, `approval-record`, `stage-match`, `commit-match`, `region-match`, `environment-match`, `prespend-receipt`, `plan-checksum`, `plan-provenance`, `state-binding`, `plan-inspect`, `runtime-preservation`, `runtime-archive`, `account-check`, then `terraform-apply`, `runtime-archive-upload`, `write-deploy-manifest`, and ends `RESULT: PASS stage base-apply complete; manifest=target/release/<sha>/deploy-manifest-base-apply-<run-id>.json` with `exit=0`.
- **If it fails:** exit 3 at a pre-check means nothing ran: fix the named item and re-run once. A failure after `terraform-apply` begins (exit 4, 5 or 124, an `AccessDenied`, `ExpiredToken`) means **STOP, do not re-run**: send the log (see E1, E2). A fix for `AccessDenied` is a routed infra repair plus a new deployer apply and a new plan.
- **Save to:** `target/phase14/evidence/14b/base-apply.log`.
- **Tell the coordinator:** the `RESULT:` line and the manifest path.

**B1.6 Back up the state and capture outputs.**
- **Where:** T1.
- **Do:**
  ```
  mkdir -p "$HOME/Library/Application Support/ScholarChain/terraform/main-backups"
  cp infra/terraform/terraform.tfstate "$HOME/Library/Application Support/ScholarChain/terraform/main-backups/main-after-base-apply-$(date -u +%Y%m%dT%H%M%SZ).tfstate"
  shasum -a 256 infra/terraform/terraform.tfstate | tee target/phase14/evidence/14b/state-sha-after-base-apply.log
  tfout -json > target/phase14/private/outputs-after-base-apply.json
  tfout -json acm_validation_records
  cp docs/agent-runs/phase-14/human-gate.md target/phase14/approvals/base-apply.md; cp target/phase14/prespend-receipt.json target/phase14/approvals/prespend-base-apply.json
  ```
  Copy the state backup to Google Drive by hand. The outputs file holds your account ID: never paste or share it.
- **Success looks like:** a sha256 line; `tfout -json acm_validation_records` prints a list with one object with `name`, `type` (CNAME) and `value`.
- **If it fails:** "No outputs found" means you used the wrong `-chdir` form; use `tfout` exactly as defined in the T1 setup.
- **Save to:** `target/phase14/evidence/14b/state-sha-after-base-apply.log`.
- **Tell the coordinator:** the state sha256.

> **GO / NO-GO 1 (after base-apply; 2 minutes)** - `date -u` to the clock log.
> - [ ] `RESULT: PASS stage base-apply complete`
> - [ ] state backed up and copied to Drive; outputs readable
> - [ ] elapsed time is within the plan (about H1)
> GO = all ticked: do B2 and B3 straight away (the certificate validates while the images upload). NO-GO: tell the coordinator; the stack already bills about USD 0.21 per hour (Neptune and the NAT gateway), so decide within the hour whether to repair or go to Section C.

## B2. Cloudflare validation CNAME (DNS-only), then check the certificate is ISSUED

Plain words: ACM proves you own the domain by checking a special CNAME record. You add it by hand in Cloudflare, **grey cloud**.

- **Where:** T1 for the values, then CF > DNS > Records > **Add record**.
- **Do:**
  1. T1: `tfout -json acm_validation_records` and `tfout -raw acm_certificate_arn > target/phase14/private/acm-arn.txt`.
  2. CF: Add record > Type **CNAME**; Name = the `name` value (Cloudflare removes your domain from the end, do not double it); Target = the `value`; Proxy status **DNS only (grey cloud)**; TTL **Auto** > **Save**.
  3. T1, wait for issuance (read-only; a few minutes, normally under 30):
     ```
     until [ "$(aws acm describe-certificate --certificate-arn "$(cat target/phase14/private/acm-arn.txt)" --query Certificate.Status --output text --profile "$ADMIN" --region us-east-2)" = ISSUED ]; do date -u; sleep 30; done
     aws acm describe-certificate --certificate-arn "$(cat target/phase14/private/acm-arn.txt)" --query 'Certificate.[Status,DomainValidationOptions[0].ValidationStatus]' --output text --profile "$ADMIN" --region us-east-2 | tee -a target/phase14/evidence/14b/acm-issued.log
     ```
- **Success looks like:** `ISSUED` and then the line `ISSUED   SUCCESS`. `PENDING_VALIDATION` for a few minutes is normal.
- **If it fails:** still pending after about 30 minutes: in CF check it is a **CNAME**, **grey cloud**, with the domain suffix present once; run `dig +short CNAME <record name>` (it must return the ACM value); then re-check A9 (CAA). Do **not** run the runtime-apply until `ISSUED` (it waits only 15 minutes).
- **Save to:** `target/phase14/evidence/14b/acm-issued.log`.
- **Tell the coordinator:** "validation CNAME added (DNS only); certificate ISSUED at <UTC time>".

## B3. Push the four images (H1:30)

Plain words: `push` copies the four container images built in A12 to the AWS image shelf (ECR), tagged with the commit, and records their fingerprints.

- **Where:** T1 with Docker running.
- **Do:** Procedure R with `APPROVED_STAGE=push` (**no** plan or receipt lines; a fresh receipt), then a fresh deployer login (as B1.5), then:
  ```
  scripts/deploy.sh --stage push --region us-east-2 --profile scholarchain-deployer-tf 2>&1 | tee target/phase14/evidence/14b/push-dry.log
  scripts/deploy.sh --stage push --region us-east-2 --profile scholarchain-deployer-tf --execute 2>&1 | tee target/phase14/evidence/14b/push.log; echo "exit=$?"
  ```
  Expect 20 to 40 minutes.
- **Success looks like:** dry run `RESULT: DRY-RUN`; real run `STEP:` `ecr-repositories-exist`, `verify-local-images`, `ecr-login`, `push-images`, `record-digests`, `write-push-record`, `write-deploy-manifest`, then `RESULT: PASS stage push complete for <sha>; manifest=...`; `target/release/<sha>/push-record.json` exists.
- **If it fails:** `ecr-repositories-exist` refusal means base-apply did not create the repositories. A missing local image means the Docker images are gone: tell the coordinator (re-running `package.sh` is a build, not allowed at this point unless the HEAD is unchanged). A digest mismatch is exit 4: STOP.
- **Save to:** `target/phase14/evidence/14b/push.log`; archive per R.5 as `push`.
- **Tell the coordinator:** the `RESULT:` line and the push-record path.

> **GO / NO-GO 2 (after push):** [ ] `RESULT: PASS stage push` [ ] certificate `ISSUED` [ ] your IP unchanged (`curl -s https://checkip.amazonaws.com`) [ ] elapsed about H2:15. GO = B4.

## B4. Runtime plan and runtime-apply (H2:15)

Plain words: the *runtime* is the four services, the load balancer (ALB), the HTTPS listener and the tunnel task definition. After this apply the front door exists and the idle cost is about USD 0.31 per hour before tax (about USD 0.35 per hour including about 11% sales tax).

**B4.1 Switch the tfvars to the runtime state.**
- **Where:** editor on `course.local.tfvars` (A8 table, second column).
- **Do:** `runtime_enabled = true`, `runtime_composition_verified = true`, the four `service_secret_bindings` (ARNs from `target/phase14/private/secret-arns.txt`), `public_ingress_cidrs = ["<ip>/32"]`, **`neptune_tunnel_enabled = true`**, the three Q8 values, `query_health_check_grace_period_seconds = 300`. `runtime_composition_verified = true` is allowed only because the reviewed live composition is in the committed HEAD.
- **Success looks like:** `curl -s https://checkip.amazonaws.com` equals the address in `public_ingress_cidrs`; `git status --short` is still empty (the file is ignored).
- **If it fails:** the tunnel flag left out means a second runtime-apply later (extra record and receipt); fix it now.
- **Save to:** nothing (never copy the file).
- **Tell the coordinator:** "runtime tfvars staged".

**B4.2 Make the runtime plan** (fresh deployer login first; B1.2):
```
scripts/plan.sh --env course --region us-east-2 --profile scholarchain-deployer-tf --image-revision "$(git rev-parse HEAD)" --execute 2>&1 | tee target/phase14/evidence/14b/runtime-plan.log; echo "exit=$?"
grep '^PLAN-ACTION:' target/phase14/evidence/14b/runtime-plan.log | grep -v '^PLAN-ACTION: create '
```
- **Success looks like:** the same markers as B1.3 and `RESULT: PASS`. Expected creates: `aws_acm_certificate_validation.api`, `module.runtime.aws_lb.query`, its target group, `aws_lb_listener.https`, four ECS services, five task definitions (four services plus `scholarchain-course-neptune-tunnel`), the tunnel task role, autoscaling, service discovery, IAM and log changes. The second command (non-create actions) should print nothing.
- **STOP:** any `delete` or `replace` (including `delete+create`) outside `module.runtime`. Any `update` must be explainable from the diff. The script's `runtime-preservation` rule does not guard a plain runtime-apply, so **you are the guard**.
- **If it fails:** as B1.3.
- **Save to:** `target/phase14/evidence/14b/runtime-plan.log`.
- **Tell the coordinator:** the action counts and every non-create action.

**B4.3 Receipt and record `runtime-apply`** (Procedure R), then **fresh deployer login** and:
```
scripts/deploy.sh --stage runtime-apply --plan "<PLAN-FILE from B4.2>" --region us-east-2 --profile scholarchain-deployer-tf 2>&1 | tee target/phase14/evidence/14b/runtime-apply-dry.log
scripts/deploy.sh --stage runtime-apply --plan "<PLAN-FILE from B4.2>" --region us-east-2 --profile scholarchain-deployer-tf --execute 2>&1 | tee target/phase14/evidence/14b/runtime-apply.log; echo "exit=$?"
```
- **Success looks like:** `STEP:` `push-record`, `ecr-repositories-exist`, `verify-registry-images`, `terraform-apply`, `record-ecs`, `write-deploy-manifest`; `RESULT: PASS stage runtime-apply complete for <sha>; manifest=...`; `exit=0`.
- **If it fails:** `push-record` or `verify-registry-images` refusals mean nothing was applied. An ACM validation timeout means re-check B2. ECS services failing to stabilise, or a circuit-breaker rollback, means stop, send the log and the first service-event lines (E3), and decide at once whether to clean up (the stack is billing). A partial runtime state refuses later base-apply and rollback stages; the human decides recovery (see [scripts README, Rollback](../../scripts/README.md#rollback-behavior-policy-13-5)).
- **Save to:** `target/phase14/evidence/14b/runtime-apply.log`.
- **Then:** back up the state again (label `after-runtime-apply`, as B1.6), record the sha256 in `target/phase14/evidence/14b/state-sha-after-runtime-apply.log`, archive the record and receipt as `runtime-apply`.
- **Tell the coordinator:** the `RESULT:` line, the state sha256 and the manifest path.

## B5. Cloudflare `api` CNAME to the load balancer, and DNS wait

- **Where:** T1, then CF > DNS > Records > **Add record**.
- **Do:**
  1. T1: `tfout -raw alb_dns_name` (a name like `...elb.amazonaws.com`).
  2. CF: Type **CNAME**; Name = the first label of your API hostname (for example `api`); Target = the ALB name; Proxy status **DNS only (grey cloud)**; TTL Auto > Save.
  3. T1: `until dig +short api.<domain> | grep -q .; do sleep 15; done; dig +short api.<domain>` then `curl -sS -o /dev/null -w '%{http_code}\n' https://api.<domain>/healthz` and `curl -sSv https://api.<domain>/healthz 2>&1 | grep -E 'issuer:|SSL certificate verify ok'`.
- **Success looks like:** `dig` shows the ALB name and addresses; `curl` prints `200` without a certificate warning; the issuer line mentions Amazon.
- **If it fails:** a timeout usually means your public IP differs from `public_ingress_cidrs` (E8). A certificate warning means the CNAME is not DNS-only or the certificate is not the one on the listener: tell the coordinator.
- **Save to:** `target/phase14/evidence/14b/b5-dns.log` (contains your domain; keep local).
- **Tell the coordinator:** "api CNAME added; /healthz 200 over https".

## B6. The 14B smoke (the Q5 pass definition)

Plain words: a *smoke test* is a quick yes/no check that the new system is alive. Before the data is loaded the answer check cannot pass, so we run only the health checks, the two "wrong key" checks and the "missing evidence" check.

**B6.1 Put the API key in your shell only** (paste from your password manager, then Enter; nothing is shown): `read -rs SCHOLARCHAIN_SMOKE_API_KEY; export SCHOLARCHAIN_SMOKE_API_KEY`

**B6.2 Health smoke:**
```
scripts/smoke-test.sh --url https://api.<domain> --checks healthz,readyz 2>&1 | tee target/phase14/evidence/14b/smoke-14b.log; echo "exit=$?"
```
- **Success looks like:**
  ```
  STEP: smoke-healthz
  CHECK-OK: healthz: GET /healthz 200 status=alive
  STEP: smoke-readyz
  CHECK-OK: readyz: GET /readyz 200 status=ready
  RESULT: PASS only 2 of 6 checks ran (healthz readyz) and passed against https://api.<domain>; this is not the full smoke test
  ```
  and `exit=0`. (`--checks healthz,readyz,error-path` would also run the two 401 checks in one call and needs the key.)
- **If it fails:** `smoke-healthz` or `smoke-readyz` failing, a `5xx`, a timeout (exit 124) or `readyz` returning 503 is a **Q5 failure**: stop, send the log, and do not start any fix without the coordinator (rollback policy 13-5 applies). To see why: `aws ecs describe-services --cluster scholarchain-course --services query-api --query 'services[0].events[:5].message' --output text --region us-east-2 --profile "$ADMIN"`.

**B6.3 The two "wrong key" checks:**
```
curl -sS -w '\n%{http_code}\n' -X POST https://api.<domain>/v1/query -H 'Content-Type: application/json' -H 'Idempotency-Key: manual-401-a' -d '{"question":"x","output":{"includeScores":false}}' | tee target/phase14/evidence/14b/manual-401.log
curl -sS -w '\n%{http_code}\n' -X POST https://api.<domain>/v1/query -H 'Content-Type: application/json' -H 'Idempotency-Key: manual-401-b' -H 'Authorization: Bearer invalid-xxxxxxxxxxxxxxxxxxxxxxxx' -d '{"question":"x","output":{"includeScores":false}}' | tee -a target/phase14/evidence/14b/manual-401.log
```
- **Success looks like:** both bodies contain `"error":"UNAUTHORIZED"` and `"retryable":false`, and the last line of each is `401`. (The invalid key is a made-up string, not a secret.)
- **If it fails:** any other status means stop and send `manual-401.log`.

**B6.4 The P14-7 "missing evidence" check** (the key goes in a temporary header file, never on the command line or in the log):
```
H="$(mktemp)"; printf 'Authorization: Bearer %s\n' "$SCHOLARCHAIN_SMOKE_API_KEY" > "$H"
curl -sS -o /dev/null -w '%{http_code}\n' -H @"$H" "https://api.<domain>/v1/evidence/evidence:metric:$(printf '0%.0s' {1..64})" | tee target/phase14/evidence/14b/p14-7-evidence-404.log
rm -f "$H"
```
- **Success looks like:** `404`. (The identifier format is derived; **unverified until live**.)
- **If it fails:** `403`, or a `500` caused by a 403, is routed to the infra-engineer (S3 permission on an absent key); stop and send the log.

**B6.5 Pass checklist** (read-only; use `$ADMIN`, or the deployer profile if it works):
```
CL=scholarchain-course
aws ecs describe-services --cluster $CL --services $(aws ecs list-services --cluster $CL --query 'serviceArns[]' --output text --region us-east-2 --profile "$ADMIN") --query 'services[].[serviceName,runningCount,desiredCount,deployments[0].rolloutState]' --output text --region us-east-2 --profile "$ADMIN" | tee target/phase14/evidence/14b/b6-checklist.log
aws elbv2 describe-target-groups --query 'TargetGroups[].TargetGroupArn' --output text --region us-east-2 --profile "$ADMIN"
aws elbv2 describe-target-health --target-group-arn "<tg arn>" --query 'TargetHealthDescriptions[].TargetHealth.State' --output text --region us-east-2 --profile "$ADMIN" | tee -a target/phase14/evidence/14b/b6-checklist.log
aws ecs describe-tasks --cluster $CL --tasks $(aws ecs list-tasks --cluster $CL --query 'taskArns[]' --output text --region us-east-2 --profile "$ADMIN") --query 'tasks[].containers[].imageDigest' --output text --region us-east-2 --profile "$ADMIN" | tr '\t' '\n' | sort -u > target/phase14/private/digests-ecs.txt
python3 -I -c 'import json,sys;print("\n".join(sorted({i["pushed_digest"] for i in json.load(open(sys.argv[1]))["images"]})))' target/release/<sha>/push-record.json > target/phase14/private/digests-pushed.txt
diff target/phase14/private/digests-ecs.txt target/phase14/private/digests-pushed.txt && echo "digests match" | tee -a target/phase14/evidence/14b/b6-checklist.log
```
- **Success looks like:** each of the four services shows `1 1 COMPLETED`; the target health prints `healthy`; the `diff` prints nothing and `digests match`. If the cluster name differs, use `aws ecs list-clusters`.
- **If it fails:** a service not at 1/1, an unhealthy target or a digest difference is a **Q5 failure**: stop and send `b6-checklist.log`.
- **Save to:** `smoke-14b.log`, `manual-401.log`, `p14-7-evidence-404.log`, `b6-checklist.log` (all under `target/phase14/evidence/14b/`).
- **Tell the coordinator:** the CHECK-OK markers, "401 / 401 / 404", the four service lines and "digests match". The coordinator verifies against the Q5 definition.

> **GO / NO-GO 3 (14B pass; checkpoint H6):** [ ] healthz and readyz OK [ ] 401, 401, 404 [ ] 4 services 1/1 COMPLETED [ ] target healthy [ ] digests match. GO = continue. NO-GO = tell the coordinator now; do not start 14C on a failed 14B.

## B7. Neptune tunnel test (operator-loader)

Plain words: Neptune sits in a private network. To load data from your laptop we start one tiny container inside that network (the *tunnel task*) and forward a port through it with AWS Session Manager. Neptune checks the host name in the certificate and in the request signature (SigV4), so on your laptop the **real Neptune host name** must point at `127.0.0.1`; "localhost" would fail. The test below proves a TLS, SigV4-signed request works before any data moves.

**B7.1 Sign in as the loader (fresh).** Console: Switch back, Switch role to `scholarchain-course-operator-loader`; note the time (this session ends 4 hours later). T1: `aws login --profile scholarchain-loader --region us-east-2`; `aws sts get-caller-identity --profile scholarchain-loader`. Success: `Arn` ends `assumed-role/scholarchain-course-operator-loader/<iam-user>`. If it fails: wrong ARN, `aws logout --profile scholarchain-loader`, repeat.

**B7.2 Collect the tunnel values (private file):**
```
tfout -json neptune_tunnel > target/phase14/private/neptune_tunnel.json
{ python3 -I -c 'import json;d=json.load(open("target/phase14/private/neptune_tunnel.json"));print("TUNNEL_CLUSTER=%s\nTUNNEL_FAMILY=%s\nTUNNEL_SUBNETS=%s\nTUNNEL_SG=%s"%(d["cluster_name"],d["family"],",".join(d["subnet_ids"]),d["security_group_id"]))'; echo "WRITER=$(tfout -raw neptune_writer_endpoint)"; echo "NEPTUNE_PORT=$(tfout -raw neptune_port)"; echo "RUN_PREFIX=<run-prefix>"; } > target/phase14/private/tunnel.env
set -a; . target/phase14/private/tunnel.env; set +a
echo "port=$NEPTUNE_PORT"
```
- **Success looks like:** `port=8182`. The file holds the real host name (private).
- **If it fails:** an empty `TUNNEL_*` means the first runtime plan had no `neptune_tunnel_enabled = true` (a second runtime-apply is needed, E3); stop and tell the coordinator.

**B7.3 Start the one-off tunnel task** (do not pass `--tags`, `--propagate-tags` or `--enable-ecs-managed-tags`):
```
TASK_ARN="$(aws ecs run-task --cluster "$TUNNEL_CLUSTER" --task-definition "$TUNNEL_FAMILY" --launch-type FARGATE --enable-execute-command --network-configuration "awsvpcConfiguration={subnets=[$TUNNEL_SUBNETS],securityGroups=[$TUNNEL_SG],assignPublicIp=DISABLED}" --profile scholarchain-loader --region us-east-2 --query 'tasks[0].taskArn' --output text)"
TASK_ID="${TASK_ARN##*/}"; echo "task id: $TASK_ID" | tee -a target/phase14/evidence/14b/tunnel-runtask.log
aws ecs wait tasks-running --cluster "$TUNNEL_CLUSTER" --tasks "$TASK_ARN" --profile scholarchain-loader --region us-east-2
until [ "$(aws ecs describe-tasks --cluster "$TUNNEL_CLUSTER" --tasks "$TASK_ARN" --profile scholarchain-loader --region us-east-2 --query "tasks[0].containers[0].managedAgents[?name=='ExecuteCommandAgent'].lastStatus | [0]" --output text)" = RUNNING ]; do date -u; sleep 10; done
RUNTIME_ID="$(aws ecs describe-tasks --cluster "$TUNNEL_CLUSTER" --tasks "$TASK_ARN" --profile scholarchain-loader --region us-east-2 --query 'tasks[0].containers[0].runtimeId' --output text)"
printf 'TASK_ARN=%s\nTASK_ID=%s\nRUNTIME_ID=%s\n' "$TASK_ARN" "$TASK_ID" "$RUNTIME_ID" >> target/phase14/private/tunnel.env
```
- **Success looks like:** a task id is printed; `tasks-running` returns; the loop ends (may take about a minute); `RUNTIME_ID` is non-empty.
- **If it fails:** `AccessDenied` on `ecs:RunTask` or `iam:PassRole` is a routed infra repair plus a deployer apply, not a console change (E1). A task that stops at once: send `aws ecs describe-tasks ... --query 'tasks[0].[stoppedReason,containers[0].reason]'`.

**B7.4 Open the port-forward in T2** (leave it running; this tab prints and holds):
```
cd /Users/danny/Documents/UIC/CS441/ScholarChain; set -a; . target/phase14/private/tunnel.env; set +a
aws ssm start-session --target "ecs:${TUNNEL_CLUSTER}_${TASK_ID}_${RUNTIME_ID}" --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters "{\"host\":[\"$WRITER\"],\"portNumber\":[\"$NEPTUNE_PORT\"],\"localPortNumber\":[\"8182\"]}" --profile scholarchain-loader --region us-east-2 2>&1 | tee target/phase14/evidence/14b/tunnel-session.log
```
- **Success looks like:** `Starting session with SessionId: ...`, `Port 8182 opened for sessionId ...`, `Waiting for connections...`. (The target string and parameters are **unverified until live**.)
- **If it fails:** `TargetNotConnected` means the Exec agent is not up yet: wait a minute and repeat. `AccessDenied` on `ssm:StartSession` is a routed repair (E1).

**B7.5 Point the real host name at your laptop** (needs your Mac password):
```
sudo cp /etc/hosts target/phase14/private/hosts.before
echo "127.0.0.1 $WRITER" | sudo tee -a /etc/hosts
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
```
- **Success looks like:** `grep -c "$WRITER" /etc/hosts` prints `1`.

**B7.6 Prove TLS and SigV4 work:**
```
curl -sS -o /dev/null -w 'http=%{http_code} ssl_verify=%{ssl_verify_result}\n' "https://$WRITER:8182/status" 2>&1 | tee -a target/phase14/evidence/14b/tunnel-test.log
aws neptunedata get-engine-status --endpoint-url "https://$WRITER:8182" --profile scholarchain-loader --region us-east-2 2>&1 | tee -a target/phase14/evidence/14b/tunnel-test.log
aws neptunedata list-loader-jobs --endpoint-url "https://$WRITER:8182" --profile scholarchain-loader --region us-east-2 2>&1 | tee -a target/phase14/evidence/14b/tunnel-test.log
```
- **Success looks like:** the unsigned `curl` prints `http=403 ssl_verify=0` (the certificate is valid for the real name; the database demands a signed request); `get-engine-status` prints JSON with `"status": "healthy"` and `"role": "writer"`; `list-loader-jobs` prints a `payload` with an empty `loadIds` list. (All three are **unverified until live**.)
- **If it fails:** a timeout means check T2 is still running, the hosts entry, and that the task is in the graph-service security group. A certificate error means the host is not the real endpoint name. A `403` on a signed call is an IAM or resource-id scoping problem: send the log (E1).
- **Save to:** `target/phase14/evidence/14b/tunnel-test.log`.
- **Tell the coordinator:** the three observed results.

**B7.7 Keep or tear down.** If B8 starts within about 30 minutes, leave the task, T2 and the hosts entry in place (the task ends itself after 4 hours, and the T2 session may drop when idle: if it does, repeat B7.4 only; if the task is gone, repeat B7.3 to B7.5). Otherwise: T2 Ctrl-C; `sudo cp target/phase14/private/hosts.before /etc/hosts`; `grep -c "$WRITER" /etc/hosts` must print `0`; `aws ecs stop-task --cluster "$TUNNEL_CLUSTER" --task "$TASK_ARN" --profile scholarchain-loader --region us-east-2 --query 'task.lastStatus' --output text`.

> **GO / NO-GO 4 (tunnel):** [ ] `http=403 ssl_verify=0` [ ] `healthy` and `writer` [ ] `loadIds` empty. GO = B8. NO-GO = the fallback is an in-VPC loader task (a new design, new approval): tell the coordinator.

## B8. 14C: data load and vectors (8C), about H4:45 to H10

Re-login rule: each long step starts right after a fresh Switch Role if the role session is more than about 2.5 hours old; every load here is idempotent, so a stopped one can be restarted. Never start a step that needs X minutes with less than X + 30 minutes of session left.

**B8.0 Set up shell variables** (T1; in any new terminal paste the T1 setup block again first, then this block):
```
set -a; . target/phase14/private/tunnel.env; set +a
export EXPORT="$REPO/target/phase6-runs/14c-spark-export-capped/run:f6e63b4b-d542-4a32-930c-f21f002cba76"
tfout -json bucket_names > target/phase14/private/bucket_names.json
bn() { python3 -I -c 'import json,sys;print(json.load(open("target/phase14/private/bucket_names.json"))[sys.argv[1]])' "$1"; }
aws sts get-caller-identity --profile scholarchain-loader --region us-east-2 --query Arn --output text
aws neptunedata get-engine-status --endpoint-url "https://$WRITER:8182" --profile scholarchain-loader --region us-east-2 --query status --output text
```
Success: the loader role ARN and `healthy`. If the engine status fails, the tunnel is down: repeat B7.3 to B7.5.

**B8.1 Upload the Parquet slice** (loader profile; this tool uses the AWS command line):
```
scripts/upload-slice.sh --export-dir "$EXPORT" --run-prefix "$RUN_PREFIX" --bucket "$(bn curated)" --region us-east-2 2>&1 | tee target/phase14/evidence/14c/upload-slice-dry.log
scripts/upload-slice.sh --export-dir "$EXPORT" --run-prefix "$RUN_PREFIX" --bucket "$(bn curated)" --region us-east-2 --profile scholarchain-loader --execute 2>&1 | tee target/phase14/evidence/14c/upload-slice.log; echo "exit=$?"
shasum -a 256 target/phase14/evidence/14c/upload-manifest.json
```
- **Success looks like:** dry run `UPLOAD-FILE:` lines, `EXPORT-RUN:` totals, `RESULT: DRY-RUN`; real run `UPLOADED`/`UNCHANGED` lines, one `VERIFIED` per key, `RESULT: PASS`, `exit=0`, and the manifest file exists.
- **If it fails:** exit 3 names the refusal (not a completed export, wrong caller role, bucket of another account, an existing different object); exit 4 means a verification mismatch (no manifest); exit 5 means an aws failure, and a re-run uploads only what is missing. An `AccessDenied` on `PutObject` may be the `if-none-match` condition (unverified): send the log (E1).
- **Save to:** `target/phase14/evidence/14c/upload-slice.log`, `upload-manifest.json`.
- **Tell the coordinator:** the `EXPORT-RUN:` totals line and the manifest sha256.

**B8.2 Build the bounded runtime artifact** (local first, JDK 17, needs 4 GiB of memory):
```
SBT_OPTS="-Xmx4g $SBT_OPTS" sbt -batch "storage / Compile / runMain edu.uic.cs441.scholarchain.storage.RuntimeArtifactMain --source $EXPORT --include-ids $REPO/target/phase14/14c-work/include-ids.txt --out-dir $REPO/target/phase14/14c-work/runtime-artifact" 2>&1 | tee target/phase14/evidence/14c/runtime-artifact-local.log; echo "exit=$?"
```
Review `target/phase14/14c-work/runtime-artifact/selection-report.json` (it must hold at most 10,000 rows and 16 MiB; note the included researchers, totals, and the first researcher dropped by the caps). Then upload (the same command plus these flags, to the RAG bucket under your run prefix):
```
SBT_OPTS="-Xmx4g $SBT_OPTS" sbt -batch "storage / Compile / runMain edu.uic.cs441.scholarchain.storage.RuntimeArtifactMain --source $EXPORT --include-ids $REPO/target/phase14/14c-work/include-ids.txt --out-dir $REPO/target/phase14/14c-work/runtime-artifact-aws --run-prefix $RUN_PREFIX --execute-aws --profile scholarchain-loader-java --bucket $(bn rag) --region us-east-2" 2>&1 | tee target/phase14/evidence/14c/runtime-artifact-aws.log; echo "exit=$?"
grep '^SCHOLARCHAIN_RUNTIME_ARTIFACT_' target/phase14/evidence/14c/runtime-artifact-aws.log > target/phase14/private/runtime-artifact-pointer.txt
shasum -a 256 target/phase14/14c-work/runtime-artifact-aws/runtime-artifact.json
```
- **Success looks like:** `exit=0`; four lines `SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET=`, `..._KEY=runtime-artifacts/<run-prefix>/versions/<run id>/runtime-subset-<sha256>.json`, `..._SHA256=...`, `..._SOURCE_RUN_ID=...`; the `shasum` equals the `_SHA256` value.
- **If it fails:** exit 1 means the selection or upload was refused (the report is still written): send `selection-report.json` and the log. An `AccessDenied` means the loader's create-only grant on `runtime-artifacts/<run-prefix>/` is not working: E1. Do not change the `--run-prefix`.
- **Save to:** `runtime-artifact-local.log`, `runtime-artifact-aws.log` (14c).
- **Tell the coordinator:** the selection rule counts (rows, bytes, researchers included, first dropped), the three non-bucket values (they are not secret).

**B8.3 Load the graph and the cache through the tunnel.**
- **Where:** T1 (T2 must still be running, hosts entry in place).
- **Do, part 1: build the config from Terraform outputs** (nothing is typed; paste this block exactly as shown, with no indentation, because it contains a here-document):

```
tfout -json table_names > target/phase14/private/table_names.json; tfout -json role_arns > target/phase14/private/role_arns.json
python3 -I - <<'PY'
import json,os
t=json.load(open("target/phase14/private/table_names.json")); r=json.load(open("target/phase14/private/role_arns.json")); b=json.load(open("target/phase14/private/bucket_names.json"))
m={"runLedger":"RunLedger","entityLinks":"EntityLinkCache","querySessions":"QuerySession","evidence":"EvidenceBundle","artifacts":"ArtifactRegistry","metrics":"ResearcherMetricCache"}
tables={k:t[v] for k,v in m.items()}; tables["idempotencyIndex"]="by-idempotency-key"
cfg={"schemaVersion":"scholarchain.storage-load.v1","environment":"course","approvedEnvironment":"course","region":"us-east-2","bucket":b["graph"],"graphPrefix":os.environ["RUN_PREFIX"]+"/graph","tables":tables,"neptune":{"endpoint":"https://%s:8182"%os.environ["WRITER"],"iamRoleArn":r["neptune_loader"]}}
open("target/phase14/14c-work/storage-load.json","w").write(json.dumps(cfg,indent=2)+"\n")
PY
```

  The table-key mapping and the index name `by-idempotency-key` (the default of `query_session_gsi_name`) are **unverified until live**; if a key is missing the python step prints the missing name: tell the coordinator.
- **Do, part 2: dry run, then the real load:**

```
sbt -batch "storage / Compile / runMain edu.uic.cs441.scholarchain.storage.StorageLoadMain --manifest $EXPORT --config $REPO/target/phase14/14c-work/storage-load.json" 2>&1 | tee target/phase14/evidence/14c/storageload-dry.log
sbt -batch "storage / Compile / runMain edu.uic.cs441.scholarchain.storage.StorageLoadMain --manifest $EXPORT --config $REPO/target/phase14/14c-work/storage-load.json --execute-aws --profile scholarchain-loader-java --environment course --load-timeout-seconds 3600" 2>&1 | tee target/phase14/evidence/14c/storageload.log; echo "exit=$?"
```

- **Success looks like:** the dry run prints `runId=run:f6e63b4b-d542-4a32-930c-f21f002cba76 mode=dry-run nodes=78104 edges=328967 support=269753` and `PLAN: cacheWrites=166088 cacheUnchanged=0`; the real run prints `loader: timeoutMillis=3600000 maxPolls=3600 (override)` and ends with the loader status `LOAD_COMPLETED`, `exit=0`.
- **If it fails:** `LOAD_FAILED` or any non-pending status stops the loader: send the log and do **not** re-run until the coordinator has read the run ledger. A timeout while the job is still pending: a re-run polls the same load ID. A credential error: fresh Switch Role, `aws login`, restart. A validation failure means the export lacks the Neptune CSV sidecar (finding B-C).
- **Save to:** `storageload-dry.log`, `storageload.log` (14c).
- **Tell the coordinator:** the exit code, whether a load ID was printed, the final status.

**B8.4 The pointer runtime-apply (G3): give the query service the artifact location.**
- **Where:** editor, then T1 (a fresh deployer session).
- **Do:** open `target/phase14/private/runtime-artifact-pointer.txt` and add to `course.local.tfvars`: `runtime_artifact_key`, `runtime_artifact_sha256`, `runtime_artifact_source_run_id` (all three or none) and optionally `runtime_artifact_bucket` (it must equal the RAG bucket). Then Procedure R (`runtime-apply`, label `pointer-apply`), and
  ```
  scripts/plan.sh --env course --region us-east-2 --profile scholarchain-deployer-tf --image-revision "$(git rev-parse HEAD)" --execute 2>&1 | tee target/phase14/evidence/14c/pointer-plan.log; echo "exit=$?"
  grep '^PLAN-ACTION:' target/phase14/evidence/14c/pointer-plan.log
  scripts/deploy.sh --stage runtime-apply --plan "<PLAN-FILE>" --region us-east-2 --profile scholarchain-deployer-tf 2>&1 | tee target/phase14/evidence/14c/pointer-apply-dry.log
  scripts/deploy.sh --stage runtime-apply --plan "<PLAN-FILE>" --region us-east-2 --profile scholarchain-deployer-tf --execute 2>&1 | tee target/phase14/evidence/14c/pointer-apply.log; echo "exit=$?"
  ```
- **Success looks like:** the plan changes only the query-api task definition (a new revision) and the query-api service (a rolling replacement); no image push and no commit; the apply ends `RESULT: PASS stage runtime-apply complete`. Then `scripts/smoke-test.sh --url https://api.<domain> --checks healthz,readyz` passes again.
- **STOP:** any action on another service, the load balancer, Neptune or data stores.
- **If it fails:** as B4.3.
- **Save to:** `pointer-plan.log`, `pointer-apply.log` (14c); back up the state (label `after-pointer-apply`); archive record and receipt as `pointer-apply`.
- **Tell the coordinator:** the plan actions and the `RESULT:` line.

**B8.5 The `awsIntegration` suite** (the Phase 7 live test of S3, DynamoDB, Neptune and S3 Vectors).
- **Where:** T1; three role sessions are needed at once. Fresh Switch Role plus `aws login` for `scholarchain-reader` and `scholarchain-cleanup` (and the loader if more than about 2.5 hours old); the tunnel must be up.
- **Do:** write `target/phase14/14c-work/aws-itest.json` from the template in the [storage README](../../modules/storage/README.md) ("Configuration and execution gate"): `environment` and `approvedEnvironment` `course`; `phase14cGateReference` the absolute path of `docs/agent-runs/phase-14/approval-14c.md`; `executionApproved`, `pricingValidated`, `budgetValidated` true (your decision); `incrementalBudgetUsd` at most 5.0 (your decision); **`cleanupAuthorized` false recommended** (the loader profile cannot delete; everything is purged at cleanup); `readerProfile`, `loaderProfile`, `cleanupProfile` = the three `-java` profiles; `bucket` = the graph bucket; `fixturePrefix` = `<run-prefix>/awsitest`; `tables` as in B8.3; `vectorBucket` = the graph bucket name with `-graph` replaced by `-vectors` (derived from the loader policy; **unverified until live**); `vectorIndex` `researcher-profile-v1`; `dimension` 256; `metric` `cosine`; `neptuneEndpoint` `https://<writer>:8182`; `neptuneRoleArn` the Neptune loader role; `manifestDirectory` an absolute path under `target/phase14/evidence/14c/`. Then:
  ```
  export SCHOLARCHAIN_AWS_ITEST=1 AWS_PROFILE=scholarchain-loader-java SCHOLARCHAIN_AWS_ITEST_CONFIG="$REPO/target/phase14/14c-work/aws-itest.json"
  sbt -batch 'storage / AwsIntegration / testOnly edu.uic.cs441.scholarchain.storage.AwsIntegrationSpec' 2>&1 | tee target/phase14/evidence/14c/awsintegration.log; echo "exit=$?"
  unset SCHOLARCHAIN_AWS_ITEST AWS_PROFILE SCHOLARCHAIN_AWS_ITEST_CONFIG
  ```
- **Success looks like:** `exit=0` and sbt reports the test passed; a journal file `aws-integration-<UUID>.json` exists in `manifestDirectory`.
- **If it fails:** send the log and the journal; do not clean up by hand (the journal says what the run owns). Cleanup AccessDenied is expected if you set `cleanupAuthorized` true.
- **Save to:** `awsintegration.log` and the journal (14c).
- **Tell the coordinator:** the test result and the journal file name.

**B8.6 8C ingest: embed and store the vectors (Titan, credit-covered, cap USD 0.25).**
- **Where:** T1 (loader session fresh enough; this can run a long time).
- **Do:** use the templates in the [14C templates](../agent-runs/phase-14/evidence/14b/replan/14c-templates.md) and the [render-config template](../agent-runs/phase-08/evidence/8b-r1/render-config.template.json). The three values must be the same ones in tfvars: `model.version` = `amazon.titan-embed-text-v2:0`, `textPrefix` = `embedding-text`, index `researcher-profile-v1`; `dimension` 256; `profile` = `scholarchain-loader-java`; buckets and tables from Terraform outputs (your account ID shown as `<acct>` only in notes).
  1. Render the real-model manifest locally (no cloud call):
     ```
     sbt -batch "rag / Compile / runMain edu.uic.cs441.scholarchain.rag.EmbeddingManifestMain --export $EXPORT --work-manifest $EXPORT/load-manifests/s3vectors.json --config $REPO/target/phase14/14c-work/render-config.json --manifest-output $REPO/target/phase14/14c-work/real-model-manifest.json --report $REPO/target/phase14/14c-work/render-report.json" 2>&1 | tee target/phase14/evidence/14c/render-manifest.log; echo "exit=$?"
     ```
     Success: `exit=0`; the report says `mode=render-only`, `embeddingCalls=0`, `stateWritten=false`. The reviewed `templateVersion` value is a decision for you and the coordinator (the repository does not fix one).
  2. Write `live-config.json` (template in 14c-templates.md) and `ingest-approval.json` (same file): `configSha256` = `shasum -a 256 live-config.json`, `manifestSha256` = `shasum -a 256 real-model-manifest.json`, `phase14GateReference` = the absolute path of `approval-14c.md`, `phase14GateSha256` = `shasum -a 256 docs/agent-runs/phase-14/approval-14c.md`, `runId` = `<run-prefix>-ingest`, `operation` `ingest`, caps 10000 / 2 / 20000 / USD 0.25, `executionApproved`, `pricingValidated`, `budgetValidated` true (your decision), `expiresAtEpochSeconds` = `python3 -I -c 'print(int(open("target/phase14/private/h0.epoch").read())+37*3600)'`.
  3. Run:
     ```
     sbt -batch "rag / Compile / runMain edu.uic.cs441.scholarchain.rag.LiveEmbeddingIngestMain --config $REPO/target/phase14/14c-work/live-config.json --manifest $REPO/target/phase14/14c-work/real-model-manifest.json --approval $REPO/target/phase14/14c-work/ingest-approval.json --report $REPO/target/phase14/evidence/14c/ingest-report.json --run-id ${RUN_PREFIX}-ingest" 2>&1 | tee target/phase14/evidence/14c/ingest.log; echo "exit=$?"
     ```
- **Success looks like:** `exit=0`; `ingest-report.json` shows `"mode":"approved-live"`, `"rejected":0`, `"billingGuarantee":false`, `written` equal to the manifest item count, and `embeddingCalls` within the approved cap of 20000.
- **If it fails:** a `live-approval-*` refusal comes from the offline pre-check (nothing was contacted): fix the JSON (hash, expiry, run id). A throttling error means the Titan quota is not applied: stop (E6). Other failures: send the log and the report.
- **Save to:** `render-manifest.log`, `ingest.log`, `ingest-report.json` (14c).
- **Tell the coordinator:** the exit code, `written`, `rejected`, `embeddingCalls`.

**B8.7 The five retrieval smokes (8C query and latency; no Haiku call).**
- **Do:** write `smoke-config.json` and `smoke-approval.json` from 14c-templates.md (operation `query-smoke`; `vectorCap`, `concurrencyCap`, `embeddingCallCap` 0; `queryRequestCap` 5, `queryEmbeddingCallCap` 10, `queryObjectReadCap` 5; `dollarCapUsd` 0.05; `runId` `<run-prefix>-query-smoke`; the five queries use real `expectedVectorKeys` from the manifest), then:
  ```
  sbt -batch "rag / Compile / runMain edu.uic.cs441.scholarchain.rag.LiveEmbeddingSmokeMain --config $REPO/target/phase14/14c-work/smoke-config.json --manifest $REPO/target/phase14/14c-work/real-model-manifest.json --approval $REPO/target/phase14/14c-work/smoke-approval.json --report $REPO/target/phase14/evidence/14c/query-report.json --run-id ${RUN_PREFIX}-query-smoke" 2>&1 | tee target/phase14/evidence/14c/query-smoke.log; echo "exit=$?"
  ```
- **Success looks like:** `exit=0`; the report lists per-index p50/p95, expected-neighbor outcomes and verified-pointer counts. (Finding N15 is fixed: this approval no longer needs ingest-sized caps.)
- **If it fails:** as B8.6; an expected neighbor that is not returned is a result to report, not a reason to edit the manifest.
- **Save to:** `query-smoke.log`, `query-report.json` (14c).
- **Tell the coordinator:** the exit code and the report summary.

**B8.8 Reserve Haiku answers, then the real-data smoke.**
- **Do:**
  ```
  python3 -I load-tests/llm_budget.py reserve --bucket 14c --answers 2 2>&1 | tee -a target/phase14/evidence/14c/llm-reserve.log; echo "exit=$?"
  scripts/smoke-test.sh --url https://api.<domain> --api-key-env SCHOLARCHAIN_SMOKE_API_KEY --query-body target/phase14/14c-work/real-query.json 2>&1 | tee target/phase14/evidence/14c/smoke-real.log; echo "exit=$?"
  python3 -I load-tests/llm_budget.py status 2>&1 | tee -a target/phase14/evidence/14c/llm-reserve.log
  ```
  (One full smoke needs one answer; reserving two keeps a margin. The key must be in `SCHOLARCHAIN_SMOKE_API_KEY`: B6.1.)
- **Success looks like:** `reserve` exits 0; six `CHECK-OK:` lines (healthz, readyz, query with `claims=N evidence_ids=M`, evidence, idempotency, error-path) and `RESULT: PASS all 6 checks passed against https://api.<domain>`.
- **If it fails:** `reserve` exit 3 means the bucket would be exceeded: **STOP, no Haiku call**. A failing `query` check (for example zero claims, 4xx) with a loaded graph: send the log, then fetch the typed error body with a manual `curl` as in B6.4 (the script prints only the status). The pointer must be live (B8.4). Do not release the reservation unless the coordinator agrees.
- **Save to:** `smoke-real.log`, `llm-reserve.log` (14c).
- **Tell the coordinator:** the six CHECK-OK lines, the `claims`/`evidence_ids` numbers and the bucket status.

**B8.9 Wrap up 14C.** T2 Ctrl-C; `sudo cp target/phase14/private/hosts.before /etc/hosts`; `grep -c "$WRITER" /etc/hosts` must print `0`; `aws ecs stop-task --cluster "$TUNNEL_CLUSTER" --task "$TASK_ARN" --profile scholarchain-loader --region us-east-2 --query 'task.lastStatus' --output text` (if the session expired, re-login first; a 4-hour task ends itself). Save `python3 -I load-tests/llm_budget.py status` to `target/phase14/evidence/14c/llm-status-after-14c.log`.

> **GO / NO-GO 5 (14C done; checkpoint H14):** [ ] upload-slice PASS [ ] runtime artifact uploaded, pointer applied [ ] `LOAD_COMPLETED` [ ] awsIntegration passed [ ] ingest `rejected: 0` [ ] query smoke exit 0 [ ] six-check smoke PASS [ ] tunnel stopped, hosts restored. GO = B9. If time is over H14, decide with the coordinator; Phase 15 is never dropped.

## B9. 15A: three EMR runs (about H10 to H18)

Plain words: *EMR* is a temporary two-machine cluster that runs the Hadoop, entity-resolution and Spark pipeline on three dataset sizes (25%, 50%, 100% of the DBLP slice). Each run is capped at **90 minutes** of cluster time (about USD 0.84). The cluster switches itself off 15 minutes after its last step, so the three runs must follow each other quickly. Every run needs its own single-use approval record, which names the cluster ID, so the records can be written only after the cluster exists. See [scripts README, "Phase 15A"](../../scripts/README.md#phase-15a-three-runs-one-cluster-and-the-approval-records-they-need-replan-g18).

**B9.1 Upload the EMR artifacts (pipeline role).**
- **Where:** Console then T1.
- **Do:** Switch back, Switch role to `scholarchain-course-operator-pipeline`, `aws login --profile scholarchain-pipeline --region us-east-2`, check the `Arn` (`aws sts get-caller-identity --profile scholarchain-pipeline`). In a new terminal repeat the T1 setup and B8.0 first. The two exports below are needed in the same shell for B9.4 to B9.7. Then:
  ```
  export SCHOLARCHAIN_ARTIFACTS_BUCKET="$(bn artifacts)" SCHOLARCHAIN_RUN_PREFIX="$RUN_PREFIX"
  scripts/upload-emr-artifacts.sh --artifacts-bucket "$SCHOLARCHAIN_ARTIFACTS_BUCKET" --run-prefix "$RUN_PREFIX" --region us-east-2 --input-dataset size-25=target/experiment-inputs/15a/size-25 --input-dataset size-50=target/experiment-inputs/15a/size-50 --input-dataset size-100=target/experiment-inputs/15a/size-100 --er-policy <er-policy file> --er-config <er-config file> --spark-config-template <spark-config-template file> 2>&1 | tee target/phase14/private/emr-upload-dry.log | grep -E '^(PLAN-SHA256|APPROVAL-LINE|EMR-CONFIG|EMR-RENDER|EMR-PIPELINE|RESULT)'
  ```
  Write `target/phase14/approvals/emr-upload.md` containing the four `APPROVAL-LINE` values as `KEY=value` lines (`APPROVED_ACTION=upload-emr-artifacts`, `APPROVED_PLAN_SHA256=<PLAN-SHA256>`, `APPROVED_ACCOUNT_SHA256=<the account hash>`, `APPROVED_REGION=us-east-2`), then run the same command with `--profile scholarchain-pipeline --principal-role operator-pipeline --approval target/phase14/approvals/emr-upload.md --manifest-out target/phase14/evidence/15/emr-upload-manifest.json --execute`, logging to `target/phase14/evidence/15/emr-upload.log`.
- **Success looks like:** the dry run ends `RESULT: DRY-RUN` and prints `EMR-CONFIG:` lines (the URIs and hashes for tfvars); the real run prints `UPLOADED`/`UNCHANGED` and one `VERIFIED` per key, then `RESULT: PASS`, and the manifest exists.
- **If it fails:** exit 3 names the refusal (for example `STEP-PROGRAM-DRIFT`, a changed plan hash: write a new record); an `AccessDenied` on `PutObject` may be the `if-none-match` condition (unverified): E1. A re-run uploads only what is missing.
- **Tell the coordinator:** the `RESULT:` line and the manifest sha256.

**B9.2 Prepare the EMR plan inputs.**
- **Do:** set `emr_config` in `course.local.tfvars` from the `EMR-CONFIG:` lines (bootstrap URI and sha256, job JAR URI and sha256, the four `extra_artifacts`), `runtime_archive_uri` = the line in `target/phase14/private/runtime-archive-uri.txt` (this is the key the base-apply stage uploaded), `enabled = true`, `runtime_verified = true`, `runtime_reference` (an evidence reference the coordinator gives you), and `emr_service_policy_json` (A8). Pre-write the shared EMR receipt `target/phase14/prespend-emr-runs.json` (Procedure R.2 format, `reserves_usd` including the three runs) and note its sha256. Prepare record files `target/phase14/approvals/emr-run-1.md`, `emr-run-2.md`, `emr-run-3.md` as text with everything except the cluster-dependent lines.
- **Success looks like:** `emr_config` has the four step programs once each; the receipt headroom is at least 3.
- **If it fails:** the guard refuses a plan without all four step programs or any URI outside the artifacts bucket: tell the coordinator.
- **Tell the coordinator:** "EMR tfvars staged, receipt hash <sha>".

**B9.3 The EMR-enabling runtime-apply.**
- **Do:** Procedure R (`runtime-apply`, label `emr-apply`), a fresh deployer login, then
  ```
  scripts/plan.sh --env course --region us-east-2 --profile scholarchain-deployer-tf --image-revision "$(git rev-parse HEAD)" --execute 2>&1 | tee target/phase14/evidence/15/emr-plan.log; echo "exit=$?"
  grep '^PLAN-ACTION:' target/phase14/evidence/15/emr-plan.log | grep -v '^PLAN-ACTION: create '
  scripts/deploy.sh --stage runtime-apply --plan "<PLAN-FILE>" --region us-east-2 --profile scholarchain-deployer-tf 2>&1 | tee target/phase14/evidence/15/emr-apply-dry.log
  scripts/deploy.sh --stage runtime-apply --plan "<PLAN-FILE>" --region us-east-2 --profile scholarchain-deployer-tf --execute 2>&1 | tee target/phase14/evidence/15/emr-apply.log; echo "exit=$?"
  ```
- **Success looks like:** the plan creates only EMR, EFS and the EMR roles' policy (the ECS services show no change; nothing deleted); the apply ends `RESULT: PASS stage runtime-apply complete`.
- **STOP:** any delete or replace, or any change to the ECS services, the load balancer or the data stores.
- **If it fails:** as B4.3. Whether Terraform plans a new cluster after an old one terminated is **unverified until live**.
- **Tell the coordinator:** the plan actions and the `RESULT:` line. **From the moment the cluster reaches WAITING, 15 minutes run until run 1 is accepted.**

**B9.4 Get the cluster ID and run the three dry runs (seconds each, no AWS call).**
```
CID="$(aws emr list-clusters --active --query 'Clusters[0].Id' --output text --region us-east-2 --profile "$ADMIN")"; echo "$CID" | tee target/phase14/evidence/15/cluster-id.log
for n in 25 50 100; do scripts/run-experiment.sh --manifest experiments/manifests/15a-emr-size-$n.json --cluster-id "$CID" 2>&1 | tee target/phase14/evidence/15/emr-dry-$n.log | grep -E '^(EXPERIMENT-MANIFEST-SHA256|RUN-CONFIG-SHA256|ESTIMATE-USD|G6-STATUS|APPROVAL-LINE|RESULT)'; done
```
- **Success looks like:** one `j-` cluster ID; three dry runs each with `RUN-CONFIG-SHA256`, `ESTIMATE-USD: 0.84` and `RESULT: DRY-RUN`; the three `RUN-CONFIG-SHA256` values differ (each run has its own input prefix).
- **If it fails:** more than one active cluster, none, or a refusal (for example a manifest not committed): stop and send the logs.
- **Tell the coordinator:** the cluster ID and the three estimates.

**B9.5 Write approval record 1 and run 1.**
- **Do:** into `target/phase14/approvals/emr-run-1.md` put the `APPROVAL-LINE` values from the size-25 dry run (they include `APPROVED_ACTION=run-experiment`, the manifest sha256, the cluster ID and the run-config sha256) plus `APPROVED_PRESPEND_SHA256=<sha256 of target/phase14/prespend-emr-runs.json>` and a text line `Approval serial: 1`. Then:
  ```
  scripts/run-experiment.sh --manifest experiments/manifests/15a-emr-size-25.json --cluster-id "$CID" --profile scholarchain-pipeline --approval target/phase14/approvals/emr-run-1.md --prespend target/phase14/prespend-emr-runs.json --execute 2>&1 | tee target/phase14/evidence/15/emr-run-1.log; echo "exit=$?"
  ```
  **While run 1 runs, write records 2 and 3** (each a new file with a different `Approval serial:` line so its sha256 differs, because approvals are single-use).
- **Success looks like:** the six pipeline steps (stage-in, hadoop-prep, entity-resolution, spark-class-origin, spark-job, copy-out) run in order, and the run ends `RESULT: PASS` with `exit=0`, inside 90 minutes. `target/experiment-runs/15a-emr-size-25-<run>/experiment-record.json` and `experiment-result.json` exist.
- **If it fails:** exit 3 (refused, nothing paid): fix the named item (a new record is needed if the approval was started). Exit 4/5/124 means a step failed or the 90-minute cap fired (the step is cancelled and the YARN application killed): **STOP**, send the log; a failed run still counts against the three-run ledger and a re-run is a new run with a new record (E7).
- **Save to:** `target/phase14/evidence/15/emr-run-1.log`.
- **Tell the coordinator:** the exit code, the `RESULT:` line, the per-step outcomes and the end time.

**B9.6 Sign in again between runs 1 and 2** (inside the 15-minute idle window; takes about 3 minutes): Switch back, Switch role `scholarchain-course-operator-pipeline`, `aws login --profile scholarchain-pipeline --region us-east-2`, check the `Arn`. This gives runs 2 and 3 a fresh 4-hour session; never start a run with less than 100 minutes of session left.

**B9.7 Runs 2 and 3.** Immediately after each run finishes, submit the next:
```
scripts/run-experiment.sh --manifest experiments/manifests/15a-emr-size-50.json --cluster-id "$CID" --profile scholarchain-pipeline --approval target/phase14/approvals/emr-run-2.md --prespend target/phase14/prespend-emr-runs.json --execute 2>&1 | tee target/phase14/evidence/15/emr-run-2.log; echo "exit=$?"
scripts/run-experiment.sh --manifest experiments/manifests/15a-emr-size-100.json --cluster-id "$CID" --profile scholarchain-pipeline --approval target/phase14/approvals/emr-run-3.md --prespend target/phase14/prespend-emr-runs.json --execute 2>&1 | tee target/phase14/evidence/15/emr-run-3.log; echo "exit=$?"
```
Success and failure as B9.5. If the cluster ended before the next run (state `TERMINATED`), the remaining records are void: E9 (a second EMR runtime-apply; the three-run and USD 2.52 caps stay cumulative).

**B9.8 Confirm the cluster ends.** About 15 minutes after the last step: `aws emr describe-cluster --cluster-id "$CID" --query Cluster.Status.State --output text --region us-east-2 --profile "$ADMIN" | tee target/phase14/evidence/15/cluster-final-state.log`. Success: `TERMINATED` (or `TERMINATING`). If it is still `WAITING` after 30 minutes, tell the coordinator (every extra hour is about USD 0.48); the final backstop is cleanup.

**B9.9 Back up the state** (label `after-emr`), archive records (`emr-apply` plus `target/phase14/approvals/emr-run-*.md`), save `shasum -a 256 target/phase14/prespend-emr-runs.json`.
- **Tell the coordinator:** the three run results and the ledger state (`wc -l ~/.scholarchain/emr-ledger/runs.jsonl`).

> **GO / NO-GO 6 (15A):** [ ] three runs PASS or each failure reported [ ] cluster terminated [ ] USD spent on EMR within the 2.52 cumulative cap [ ] elapsed time and the receipt headroom still at least 3. GO = B10.

## B10. 15B: ECS scale-out and scale-in (about H18 to H21)

Plain words: we send controlled traffic at 1, 5, 25 and 50 simultaneous users to the query service and watch the number of tasks go up and then down. Almost all traffic hits endpoints that do not call Haiku; a fixed sample of **60** real answers (bucket 15b) is included. The load generator reserves answers in the ledger itself, one by one, and stops calling Haiku the moment the bucket is used up. Details: [load-tests README](../../load-tests/README.md), [experiments README](../../experiments/README.md#15b-ecs-scale-out-and-scale-in-on-query-api).

**B10.1 Pre-flight.**
- **Do:**
  ```
  export SCHOLARCHAIN_LOAD_BASE_URL="https://api.<domain>"
  read -rs SCHOLARCHAIN_LOAD_API_KEY; export SCHOLARCHAIN_LOAD_API_KEY
  python3 -I load-tests/loadgen.py validate-manifest experiments/manifests/15b-ecs-scaling.json 2>&1 | tee target/phase14/evidence/15/b10-validate.log
  python3 -I load-tests/loadgen.py plan --manifest experiments/manifests/15b-ecs-scaling.json --llm --questions-file target/phase14/14c-work/questions.txt 2>&1 | tee target/phase14/evidence/15/b10-plan.log
  python3 -I load-tests/llm_budget.py status 2>&1 | tee -a target/phase14/evidence/15/b10-plan.log
  ```
  The `plan` and `validate-manifest` commands send nothing.
- **Success looks like:** both exit 0; the plan lists the levels 1/5/25/50 with 10/15/20/15 planned answers (60 in total) and any dropped routes; `status` shows bucket 15b with 60 remaining.
- **If it fails:** `ROUTE-DROPPED` lines for graph or evidence routes mean the node or evidence ID files are missing (supply `--node-ids-file`); a refusal (exit 3) names the reason.

**B10.2 Start metric polling in T3** (read-only; leave it running through the experiment and the 30 quiet minutes after it; the service name may differ: check `aws ecs list-services --cluster scholarchain-course`):
```
cd /Users/danny/Documents/UIC/CS441/ScholarChain; ADMIN="<architect-admin-profile>"
while true; do echo "$(date -u +%FT%TZ) $(aws ecs describe-services --cluster scholarchain-course --services query-api --query 'services[0].[desiredCount,runningCount,pendingCount]' --output text --region us-east-2 --profile "$ADMIN")"; sleep 60; done 2>&1 | tee -a target/phase14/evidence/15/b10-ecs-poll.log
```
(Unverified until live: with Container Insights off there is no `RunningTaskCount` metric; this poll is the task-count record.)

**B10.3 Run the experiment** (about 50 minutes: four levels, a 10-minute hold at 50, then 30 minutes with no load):
```
python3 -I load-tests/loadgen.py run --manifest experiments/manifests/15b-ecs-scaling.json --run-id 15b-1 --node-ids-file target/phase14/14c-work/node-ids.txt --llm --questions-file target/phase14/14c-work/questions.txt 2>&1 | tee target/phase14/evidence/15/b10-loadgen.log; echo "exit=$?"
```
(Add `--evidence-ids-file <file>` to include the evidence route. The run id is any short label; the tool prints the accepted pattern if it refuses.)
- **Success looks like:** exit 0; `target/experiment-runs/15b-ecs-scaling-15b-1/raw/run-record.json` shows outcome `completed`; the log may show an event `llm-cap-reached` when the 60 answers are used (expected, not an error).
- **If it fails:** exit 4 means the run aborted (repeated 5xx or authentication failures, or Ctrl-C): the run directory is kept and marked aborted; send the log; a rerun needs a new run id. Exit 3 means refused before sending anything.

**B10.4 Collect the scaling evidence** (after the quiet 30 minutes; use the run's UTC phase bounds from the run record for `<UTC>` values):
```
aws application-autoscaling describe-scaling-activities --service-namespace ecs --resource-id service/scholarchain-course/query-api --region us-east-2 --profile "$ADMIN" 2>&1 | tee target/phase14/evidence/15/b10-scaling-activities.json
aws cloudwatch get-metric-statistics --namespace AWS/ECS --metric-name CPUUtilization --dimensions Name=ClusterName,Value=scholarchain-course Name=ServiceName,Value=query-api --start-time <UTC> --end-time <UTC> --period 60 --statistics Average Maximum --region us-east-2 --profile "$ADMIN" 2>&1 | tee target/phase14/evidence/15/b10-cpu.json
python3 -I load-tests/loadgen.py summarize target/experiment-runs/15b-ecs-scaling-15b-1 2>&1 | tee target/phase14/evidence/15/b10-summarize.log
python3 -I load-tests/llm_budget.py status 2>&1 | tee target/phase14/evidence/15/b10-llm-status.log
```
(`HealthyHostCount` needs the load balancer and target group dimension strings; the [experiments README](../../experiments/README.md#15b-ecs-scale-out-and-scale-in-on-query-api) has the command. All of these are **unverified until live**.) Stop the T3 loop (Ctrl-C).
- **Success looks like:** the polling log shows the desired count rising above 1 and later falling back (if CPU stayed below the 60% target, no scale-out is a valid result: report the CPU values, do not change the service or the target inside the run); `summarize` exits 0.
- **Save to:** the files named above, under `target/phase14/evidence/15/`.
- **Tell the coordinator:** the run outcome, the task counts over time, answers used from bucket 15b, and the ledger status.

> **GO / NO-GO 7 (15B):** [ ] run `completed` (or the abort reported) [ ] scaling evidence saved [ ] bucket 15b status noted. GO = B11.

## B11. 16B: live evaluation (about H21 to H27)

Plain words: a fixed set of real questions is answered through the live system and graded. At most **40** Haiku answers (bucket 16b).

- **Where:** T1.
- **Do:** reserve first, before any LLM-calling command:
  ```
  python3 -I load-tests/llm_budget.py reserve --bucket 16b --answers <N, at most 40> 2>&1 | tee -a target/phase14/evidence/16b/llm-reserve.log; echo "exit=$?"
  ```
  Then run the 16B evaluation as defined by the Phase 16 work order, logging to `target/phase14/evidence/16b/eval-<name>.log`. **Gap: the repository contains no 16B command** (`experiments/manifests/16b-live-evaluation.json` fixes only the answer budget); the coordinator must supply the exact command and the question file before this step.
  After the run: `python3 -I load-tests/llm_budget.py status | tee target/phase14/evidence/16b/llm-status-after-16b.log`; give back answers that were reserved but **not** sent with `python3 -I load-tests/llm_budget.py release --bucket 16b --answers <n>`.
- **Success looks like:** `reserve` exits 0; the evaluation finishes and writes its raw results under `target/phase14/evidence/16b/`.
- **If it fails:** `reserve` exit 3 means the bucket would be exceeded: **STOP, no Haiku call**. A throttling error: E6. Moving spare answers from another bucket needs your approval file (`transfer`, see [load-tests README](../../load-tests/README.md)); ask the coordinator.
- **Tell the coordinator:** answers reserved and released, the log path, the ledger status.

> **GO / NO-GO 8 (16B):** [ ] reserve OK [ ] results saved [ ] ledger status saved. GO = B12.

## B12. Demo video and final smoke (about H27 to H31)

**B12.1 Reserve for the last Haiku bucket:** `python3 -I load-tests/llm_budget.py reserve --bucket 17 --answers 5 2>&1 | tee -a target/phase14/evidence/17/llm-reserve.log` (two answers for the final smoke, up to three for the demo). Exit 3 means stop.

**B12.2 Record the demo video.**
- **Where:** macOS screen recording (QuickTime Player > File > New Screen Recording, or Shift+Cmd+5), on the network allowed by `public_ingress_cidrs`.
- **Do:** show the Console view of the ECS services and a healthy ALB target (blur the account name/ID in the console header), `scripts/smoke-test.sh` passing with a real-data query, one answer with its cited evidence, and the scaling graph. Do not show the API key, the account ID or secrets.
- **Success looks like:** a video file saved **outside the repository**, for example `~/Movies/scholarchain-demo.mov`; `shasum -a 256` of it recorded in `target/phase14/evidence/17/demo-video.log`.
- **If it fails:** re-record; spent answers stay spent (the ledger counts them).
- **Tell the coordinator:** the file name and its sha256.

**B12.3 Final smoke (the full six checks):**
```
scripts/smoke-test.sh --url https://api.<domain> --api-key-env SCHOLARCHAIN_SMOKE_API_KEY --query-body target/phase14/14c-work/real-query.json 2>&1 | tee target/phase14/evidence/17/final-smoke.log; echo "exit=$?"
python3 -I load-tests/llm_budget.py status 2>&1 | tee target/phase14/evidence/17/llm-status-final.log
```
- **Success looks like:** six `CHECK-OK:` lines and `RESULT: PASS all 6 checks passed against https://api.<domain>`.
- **If it fails:** send the log; do not retry more than once (each query is a paid answer).
- **Tell the coordinator:** the six lines and the final ledger status.

> **GO / NO-GO 9:** [ ] video saved and hashed [ ] final smoke PASS [ ] ledger final status saved. GO = B13.

## B13. Evidence archive and downloads (about H31 to H34; BEFORE cleanup)

Plain words: cleanup deletes everything, including S3 data and its old versions, with no undo. Archive and download first.

**B13.1 Capture the facts that disappear on destroy.**
```
tfout -raw kms_key_arn > target/phase14/private/kms-key-arn.txt
tfout -json bucket_names > target/phase14/private/pre-cleanup-buckets.json
tfout -json > target/phase14/private/outputs-before-cleanup.json
shasum -a 256 infra/terraform/terraform.tfstate | tee target/phase14/evidence/14b/state-sha-before-cleanup.log
```

**B13.2 Download what the report needs** (pipeline session fresh; the pipeline role can read `pipeline/<run-prefix>/`):
```
mkdir -p "$HOME/Documents/scholarchain-session-downloads"
aws s3 cp "s3://$(bn artifacts)/pipeline/$RUN_PREFIX/" "$HOME/Documents/scholarchain-session-downloads/pipeline/" --recursive --profile scholarchain-pipeline --region us-east-2 2>&1 | tee target/phase14/evidence/15/download.log
( cd "$HOME/Documents/scholarchain-session-downloads" && find . -type f -print0 | xargs -0 shasum -a 256 ) > "$HOME/Documents/scholarchain-session-downloads/SHA256SUMS"
cp "$HOME/Movies/scholarchain-demo.mov" "$HOME/Documents/scholarchain-session-downloads/" 2>/dev/null; wc -l "$HOME/Documents/scholarchain-session-downloads/SHA256SUMS"
```
Also copy the `target/experiment-runs/` folders and the local `~/.scholarchain/llm-ledger/haiku-ledger.jsonl` and `~/.scholarchain/emr-ledger/runs.jsonl` into the downloads folder. Record each file's sha256. Success: `download.log` shows copies and `SHA256SUMS` has one line per file. If the session expired: fresh Switch Role and `aws login`, repeat (the copy is safe to repeat).

**B13.3 Archive the evidence logs** (into git-ignored `target/`, so the tree stays clean; the coordinator copies the lean evidence into `docs/` after cleanup):
```
scripts/archive-evidence.sh --phase 14 --label session-v1 --dest-root target/phase14/archive --include test-reports=target/phase14/evidence/14b --include test-reports=target/phase14/evidence/14c --include test-reports=target/phase14/evidence/15 --include test-reports=target/phase14/evidence/16b --include test-reports=target/phase14/evidence/17 --include run-manifests=target/release/<sha> --include experiment-outputs=target/experiment-runs 2>&1 | tee target/phase14/evidence/14b/archive.log
```
- **Success looks like:** `RESULT: PASS evidence directory ... written and verified` and `INDEX.json` listing each file. (The archive script was run on a scratch folder on 2026-11-08 with exit 0; its behaviour on the real evidence is **unverified until live**.)
- **If it fails:** exit 3 names the reason, for example a file over 1 MiB or a binary (screenshots, videos, big logs) that needs `--external-location NAME=<Drive text or URL>`, or a refused private file (plan text, state, tfvars). Add the `--external-location` entries it names and run again with a **new label** (`session-v2`); a label directory is never overwritten. Add `--include plan-receipts=<the *.tfplan.receipt.json files>` individually.
- **Tell the coordinator:** the archive path, `INDEX.json` file count, the downloaded file list with sha256.

> **GO / NO-GO 10 (the last one before deletion):** [ ] downloads done and hashed [ ] archive written [ ] kms key ARN and bucket names saved [ ] demo video saved outside the repo [ ] coordinator says "evidence complete". Only when every box is ticked do you start Section C. **There is no undo.**

---

# C. Cleanup (start no later than H35; finished by H37)

Plain words: cleanup deletes everything the session created, in a fixed order, so the meter stops. It needs a *preparation* apply first (it only turns off delete-protection flags), then a **two-pass** destroy (the first pass is expected to fail once at the NAT address), then removal of the operator roles, the secrets and the Cloudflare records. Nothing is deleted before GO / NO-GO 10 is fully ticked. Source: [scripts README, "Ordered teardown"](../../scripts/README.md#ordered-teardown-for-the-single-session-usd-25-replan-w4-user-decision-5).

Every step here uses a **fresh deployer session** (the destroy passes can take close to an hour). If a pass ends `ExpiredToken`, see E2: log in again and run the listing again.

**C1. Stop the tunnel and restore the hosts file** (skip if B8.9 was done).
- **Do:** T2 Ctrl-C. `sudo cp target/phase14/private/hosts.before /etc/hosts`; `grep -c "$WRITER" /etc/hosts`; if a tunnel task is still running (loader session needed): `aws ecs stop-task --cluster "$TUNNEL_CLUSTER" --task "$TASK_ARN" --profile scholarchain-loader --region us-east-2`.
- **Success looks like:** the `grep` prints `0`.
- **If it fails:** edit `/etc/hosts` by hand to remove the one `127.0.0.1 <writer>` line.
- **Save to:** `target/phase14/evidence/14b/c1-tunnel-stop.log`. **Tell:** "tunnel stopped, hosts clean".

**C2. Cleanup preparation (no headroom floor).**
- **Do:** fresh deployer login (B1.2), then
  ```
  scripts/cleanup.sh --env course --region us-east-2 --profile scholarchain-deployer-tf --prepare --image-revision "$(git rev-parse HEAD)" --execute 2>&1 | tee target/phase14/evidence/14b/cleanup-prepare-plan.log; echo "exit=$?"
  ```
  Then Procedure R with `APPROVED_STAGE=cleanup-prepare` (plan and receipt hashes from this output; a fresh receipt; there is no headroom floor, so a negative headroom is accepted and overspend never blocks cleanup; the receipt must still exist, match its approved sha256, be fresh (within 24 h), show monitoring confirmed and carry all four numeric cost fields), and:
  ```
  scripts/deploy.sh --stage cleanup-prepare --plan "<PLAN-FILE>" --region us-east-2 --profile scholarchain-deployer-tf 2>&1 | tee target/phase14/evidence/14b/cleanup-prepare-dry.log
  scripts/deploy.sh --stage cleanup-prepare --plan "<PLAN-FILE>" --region us-east-2 --profile scholarchain-deployer-tf --execute 2>&1 | tee target/phase14/evidence/14b/cleanup-prepare.log; echo "exit=$?"
  ```
- **Success looks like:** the plan step prints `PLAN-FILE: <path>`, `PLAN-RECEIPT: <path> sha256=<hex>`, candidate lines with `APPROVED_STAGE=cleanup-prepare`, and `RESULT: PASS preparation plan recorded, NOT applied`; the apply prints `terraform-apply` then `RESULT: PASS stage cleanup-prepare complete` (in-place updates of protection flags only: Neptune, ALB, DynamoDB, ECR, the S3 buckets and the vector bucket). The deploy output also includes a line stating that cleanup-prepare has no headroom floor; save it with the C2 log (`cleanup-prepare.log`). If the plan step says nothing is needed, no preparation is required and you go to C3.
- **If it fails:** `RESULT: REFUSED step=prepare-policy` with `POLICY-VIOLATION:` lines means the plan creates, deletes or changes something other than the protection flags: STOP and send the log. Otherwise as B1.5.
- **Save to:** the logs above; archive the record as `cleanup-prepare` (R.5). **Tell:** both `RESULT:` lines.

**C3. Two-pass destroy.**
- **Do (pass 1, listing):**
  ```
  scripts/cleanup.sh --env course --region us-east-2 --profile scholarchain-deployer-tf --execute 2>&1 | tee target/phase14/evidence/14b/cleanup-list-1.log; echo "exit=$?"
  grep '^DESTROY-ACTION:' target/phase14/evidence/14b/cleanup-list-1.log
  ```
  Read every `DESTROY-ACTION: delete <address>` line. Then confirm with the token and plan file the listing printed:
  ```
  TOKEN="$(grep '^CONFIRM-TOKEN:' target/phase14/evidence/14b/cleanup-list-1.log | awk '{print $2}')"; DPLAN="$(grep '^DESTROY-PLAN-FILE:' target/phase14/evidence/14b/cleanup-list-1.log | cut -d' ' -f2-)"
  scripts/cleanup.sh --env course --region us-east-2 --profile scholarchain-deployer-tf --execute --confirm "$TOKEN" --plan "$DPLAN" 2>&1 | tee target/phase14/evidence/14b/cleanup-pass-1.log; echo "exit=$?"
  ```
- **Success looks like (pass 1):** the listing prints `DESTROY-PLAN-SHA256:`, `DESTROY-PLAN-FILE:`, `CONFIRM-TOKEN:` and ends `RESULT: REFUSED` with exit 3 **by design** (nothing is destroyed). The confirmed pass is **expected to end** `RESULT: PARTIAL destroy pass incomplete` with exit 5 at `aws_eip.nat` `DisassociateAddress` (HTTP 403, a known carried item 24). Do not widen IAM.
- **Do (pass 2):** fresh deployer login, run the listing again (a fresh plan and a **new** token; log `cleanup-list-2.log`), then confirm again (log `cleanup-pass-2.log`), using the same commands with the new file names.
- **Success looks like (pass 2):** `RESULT: PASS destroy pass complete; before=N after=M; evidence=target/cleanup-evidence/<run-id>`. Then read `target/cleanup-evidence/<run-id>/after-inventory.txt`: only `module.foundation` items (budget and state-backend settings, free) may remain.
- **STOP if:** any `DESTROY-ACTION` touches `module.foundation.` or an address you do not recognise (`step=destroy-policy` would refuse it anyway); a `BucketNotEmpty` error (a failure: send the log).
- **If it fails:** exit 5 other than the expected NAT item, or exit 124: stop and send the log; re-running the listing is safe (it re-plans), but each confirmed pass needs the token of its own listing.
- **Save to:** `cleanup-list-1.log`, `cleanup-pass-1.log`, `cleanup-list-2.log`, `cleanup-pass-2.log`; copy `before-inventory.txt`, `after-inventory.txt`, `destroy-actions.txt` to `target/phase14/evidence/14b/cleanup-evidence/`.
- **Tell the coordinator:** both `RESULT:` lines and the `DESTROY-ACTION` count.

**C4. Remove the operator roles** (admin profile; after the data cleanup, because those roles are the credentials for it).
- **Do:** in `infra/terraform/deployer/deployer.local.tfvars` set `operator_roles_enabled = false` (leave the rest). Then repeat the A4 commands (`STATE` and `LOG` as in A4 with `LOG` = `.../deployer-cleanup-apply.log`; back up the state first; `init`, `plan`, `show`, the `jq` line count). Apply the saved plan only after the coordinator confirms your decision is recorded, exactly as in A4, then record `shasum -a 256 "$STATE"` and make a `.post-cleanup` backup copy.
- **Success looks like:** `Plan: 0 to add, 0 to change, 13 to destroy.` and 13 `jq` lines: the 4 `aws_iam_role_policy.operator[...]`, the 3 `operator_login[...]`, the 3 `aws_iam_role.operator[...]` and the pipeline role's 3 resources (`aws_iam_role_policy.operator_pipeline[0]`, `operator_pipeline_login[0]`, `aws_iam_role.operator_pipeline[0]`); `aws_iam_role.deployer` is untouched. (An older note in the scripts README says 7 or 10: use 13, the number from the final deployer plan.)
- **If it fails:** any other count or any change to `aws_iam_role.deployer` is a STOP.
- **Save to:** `target/phase14/evidence/14b/deployer-cleanup-apply.log`. **Tell:** the plan line, the `jq` count, the new state sha256.

**C5. Delete the four secrets by hand** (admin profile; they bill per month; Terraform never managed them):
```
for n in api-key-sha256 internal-token-sha256 internal-token graph-cursor-key; do aws secretsmanager delete-secret --secret-id scholarchain/course/$n --force-delete-without-recovery --region us-east-2 --profile "$ADMIN" --query Name --output text; done 2>&1 | tee target/phase14/evidence/14b/c5-secrets-delete.log
aws secretsmanager list-secrets --region us-east-2 --profile "$ADMIN" --query "SecretList[?starts_with(Name,'scholarchain/course/')].Name" --output text
```
- **Success looks like:** four names printed by the loop; the final `list-secrets` prints nothing. **Tell:** "4 secrets deleted".

**C6. Cloudflare.** CF > DNS > Records: delete the two DNS-only records (the ACM validation CNAME and the `api` CNAME). Success: both rows gone. **Tell:** "Cloudflare records removed". (The certificate itself was a Terraform resource and went in C3.)

**C7. KMS pending-deletion check** (admin profile; the key is scheduled for deletion with a 7-day window and costs nothing while pending):
```
aws kms describe-key --key-id "$(cat target/phase14/private/kms-key-arn.txt)" --query KeyMetadata.KeyState --output text --region us-east-2 --profile "$ADMIN" | tee target/phase14/evidence/14b/c7-kms.log
```
Success: `PendingDeletion`. If `describe-key` is denied, check Console > **KMS** > Customer managed keys (state "Pending deletion"). **Tell:** the state.

**C8. Final inventory (read-only).**
```
aws resourcegroupstaggingapi get-resources --region us-east-2 --tag-filters Key=project,Values=scholarchain --query 'ResourceTagMappingList[].ResourceARN' --output text --profile "$ADMIN" | tee target/phase14/evidence/14b/c8-inventory.log
aws s3api list-buckets --query "Buckets[?starts_with(Name,'scholarchain-course')].Name" --output text --profile "$ADMIN" | tee -a target/phase14/evidence/14b/c8-inventory.log
```
- **Success looks like:** the first prints nothing or only the KMS key; the second prints nothing. In the Console also look for stray **Elastic IPs**, **NAT gateways**, **Load balancers**, **EMR clusters**, **Neptune clusters**, **EFS file systems** and **ECR repositories** in us-east-2: none should remain.
- **If it fails:** a remaining billable item means tell the coordinator at once (a manual console deletion is not allowed; it needs a routed repair and a decision). **Tell:** the inventory result.

**C9. Haiku ledger final status.** `python3 -I load-tests/llm_budget.py status | tee target/phase14/evidence/17/llm-status-cleanup.log`. Keep `~/.scholarchain/llm-ledger/haiku-ledger.jsonl` and `~/.scholarchain/emr-ledger/runs.jsonl`. When the AWS bill later shows the Marketplace Haiku charge, any spend outside the buckets is recorded with `python3 -I load-tests/llm_budget.py adjust --usd <amount> --source aws-bill`. **Tell:** the totals.

**C10. Sign out.** `aws logout --all`; Console: sign out; stop T4 (`caffeinate`); `unset SCHOLARCHAIN_SMOKE_API_KEY SCHOLARCHAIN_LOAD_API_KEY`; `grep -c "$WRITER" /etc/hosts` is `0`. Removing the Marketplace subscription is optional (it has no fixed fee).

**C11. Next-day billing check.** The day after (billing lags), Console > Billing and Cost Management > **Cost Explorer**, daily, grouped by Service, with Credits unticked, and **Budgets**. Save screenshots to `target/phase14/evidence/14b/c11-billing-*.png`.
- **Success looks like:** no NAT gateway, Elastic IP, load balancer, Neptune, Fargate or EMR line still accrues; the project total (including the Haiku Marketplace charge on your card) is under USD 25; only small residuals remain (Cloud Map hosted zone month, late-posting usage). Run the `scripts/billing/` verification per [VERIFICATION.md](../../scripts/billing/VERIFICATION.md) only if the coordinator says a new gate exists.
- **If it fails:** a line that still accrues means find it in Cost Explorer (grouped by Usage type) and tell the coordinator the same day.
- **Tell the coordinator:** "cleanup complete; billing next-day check: <total>, residuals <...>".

**C12. End of the freeze.** The coordinator copies the lean evidence from `target/phase14/archive/` into `docs/agent-runs/phase-14/evidence/` and writes the closeout record last; only then is a commit made (Section D, rule 6).

---

# D. Commit-freeze rules for the session

Why: `plan.sh` and `deploy.sh` refuse a dirty git tree; every approval record names the exact commit (`APPROVED_COMMIT`), and the container images are tagged with that commit. The only exempt path is the literal `docs/agent-runs/phase-14/human-gate.md`. `cleanup.sh --prepare` and `deploy.sh --stage cleanup-prepare` apply the same checks, so the freeze lasts **through Section C**, not only to runtime-apply.

1. **Before the base plan (all of Section A):** commits are allowed and expected: A1 (including the EMR price flag, the rendered experiment manifests with real hashes, `approval-14c.md` and every new file), the pins (A2), and the budget commits (A3: C2, the gate record, the public packet). The HEAD at `package.sh` and at the base plan is the final HEAD. **Any later commit means rebuilding the images and redoing the plans and records.**
2. **From the base plan (B1.3) to the end of Section C:** no commit, no tracked-file edit, no new untracked file outside git-ignored paths. Allowed writes: `target/**` (logs, approvals, archive, private files), `*.local.tfvars`, and `docs/agent-runs/phase-14/human-gate.md` (overwritten per stage, copied to `target/phase14/approvals/<stage>.md` before the next stage; never `git add` it). Do not edit `prompt.md`, `review.md`, `owner-report.md` or `test-report.md`.
3. **`approval-14c.md`** is written and committed in A1 with caps and wording only. If it was not, keep it at `target/phase14/approvals/approval-14c.md` during the session and move it into `docs/` after Section C (and change the path in the approval JSONs).
4. **Pipeline approvals** live in `target/phase14/approvals/` (`emr-upload.md`, `emr-run-1.md` to `emr-run-3.md`) and are passed with `--approval`. The default `docs/agent-runs/phase-15/human-gate.md` is not exempt for `deploy.sh` or `cleanup.sh`, and a new file under `docs/` would block the next stage.
5. **Evidence** goes to `target/phase14/evidence/{14b,14c,15,16b,17}/`. `scripts/archive-evidence.sh` writes into `target/phase14/archive/` during the session (B13.3); the coordinator copies from there into `docs/agent-runs/phase-14/evidence/` only after Section C.
6. **After Section C:** the coordinator copies the lean evidence and the archived records into `docs/`, writes the closeout `human-gate.md` last, and then you commit. A docs-only commit between runtime-apply and cleanup would move HEAD; rollback and cleanup would then need `--image-revision <old sha>`, so avoid it.
7. **An image or code change mid-session** means a new `package.sh`, a new push, a new plan, record and receipt, and a new commit. Do not do it inside the session: stop and clean up instead.
8. **tfvars changes are not commits.** Raising a Fargate size, the health-check grace, the allowed IP, the pointer values or the EMR settings is a change to the ignored `course.local.tfvars` plus a new plan, record and receipt.

---

# E. Failure playbook

General rules: stop first. Send the log path and the last `STEP:`/`RESULT:` lines, never secrets. Do not "fix" anything in the AWS console. Every idle hour costs about USD 0.31 before tax, about USD 0.35 including about 11% sales tax (about USD 0.79 before tax, about USD 0.88 including tax, with a running EMR cluster), so decide with the coordinator within an hour whether to repair or go to Section C.

**E1. AccessDenied.**
- Look for the line `... is not authorized to perform: <action> on resource: <arn>`. Send that line (write `<acct>` for the account number) and the log path.
- Do **not** widen IAM in the console, create access keys, or use the admin profile to push the step through.
- Route: the infra-engineer repairs the Terraform; you apply it with the deployer apply (new human gate), and any main-root plan made before the repair is stale (new plan, record, receipt).
- Known unverified spots: the S3 `if-none-match` condition on uploads, `ssm:StartSession` and ECS Exec for the tunnel, the exact IAM actions of the first base-apply (see the deployer README disclosure).

**E2. ExpiredToken, "run aws login", "token has expired".**
- Before an `--execute` stage started (dry run or an exit 3 refusal): Switch back, Switch role, `aws login`, re-run once.
- **Mid-`--execute` of base-apply, push, runtime-apply or cleanup: STOP.** Do not re-run the command and do not edit the state. Log in again, then send the log; the state holds what finished, the old plan is stale, so a new plan, record and receipt are needed.
- Idempotent loaders (`upload-slice.sh`, `StorageLoadMain`, ingest): log in again and re-run the same command; they skip what is done.
- During an EMR run: each step also runs under a time limit on the node, so a lost laptop session does not run forever. Log in again as the pipeline role and look at the cluster (E7).
- Prevention: the role-session rules at the top (deployer 1 h, operator roles 4 h from the Switch Role click).

**E3. A service task fails to start, or runtime-apply will not stabilise.**
- Look (read-only, `$ADMIN`): `aws ecs describe-services --cluster scholarchain-course --services <service> --query 'services[0].events[:8].message' --output text --region us-east-2 --profile "$ADMIN"`; stopped tasks: `aws ecs list-tasks --cluster scholarchain-course --desired-status STOPPED --region us-east-2 --profile "$ADMIN"` then `aws ecs describe-tasks ... --query 'tasks[].[stoppedReason,containers[].reason,containers[].exitCode]'`. Application logs are in CloudWatch log group `/scholarchain-course/<service>`.
- Out of memory or CPU: raise that service in `service_capacity` in `course.local.tfvars` (valid pairs: cpu 256 with memory 1024 or 2048; cpu 512 with 1024 or 2048; cpu 1024 with 2048), then make a **new runtime plan**, record and receipt and run `runtime-apply` again. It costs a few cents per hour more and needs **no commit**.
- query-api replaced before the other services were ready: raise `query_health_check_grace_period_seconds` (default 300, at most 3600) the same way.
- Tunnel task definition missing: `neptune_tunnel_enabled = true` was not in the first runtime plan: set it and do another runtime-apply.

**E4. `smoke-query` stops with "the answer holds no claims" before 14C.**
- Expected: a full six-check `scripts/smoke-test.sh` before the data is loaded ends `CHECK-FAILED: query: the answer holds no claims to fetch evidence for` / `RESULT: FAIL step=smoke-query reason=query check failed` with exit 4. That is **not** a rollback trigger, nor is a typed no-evidence 4xx. This is why B6 runs `--checks healthz,readyz`.
- The script prints only the HTTP status for a non-200/202 reply. To read the typed `error` field, repeat the request with `curl` and the key in a temporary header file (as in B6.4).
- It **is** a failure after B8.8 (data loaded, pointer applied): send the log and the curl body.
- Real Q5 failures (rollback policy 13-5): healthz or readyz failing, a 5xx, AccessDenied, a timeout (exit 124) or an authentication failure.

**E5. A budget e-mail arrives (USD 10, 15 or 20).**
- The alerts are informational. They do not stop spending and arrive 8 to 24 hours late.
- USD 10 is expected during the session. Compare with your own running total (Procedure R.1); nothing else to do.
- USD 15: recompute headroom (25 - reported - unreported - reserves). If it is below 3, tell the coordinator and drop optional work (B11, B12); never drop cleanup.
- USD 20: stop all paid work and go to Section C now. Cleanup spends nothing new and the `cleanup-prepare` stage has no headroom floor, so overspend never blocks it.

**E6. Bedrock throttling (`ThrottlingException`, `Too many tokens per day`, `TooManyRequestsException`).**
- Stop the step that called Bedrock. Do not retry in a loop.
- "Per minute" limits: wait a minute and retry once. "Per day" or "quota is 0": the quota is not applied; stop and tell the coordinator. The Bedrock fallback (A0) needs a new commit, so it cannot be switched on mid-session.
- Carry on with the steps that need no model (graph load, EMR, the non-LLM load test) and skip the model steps; tell the coordinator which answers were reserved but not used (`llm_budget.py release` only for answers that were never sent).
- Ingest: ask before re-running; the approval is bound to its run ID.

**E7. An EMR run goes over 90 minutes, hangs, or the script died.**
- Normally `run-experiment.sh` enforces the cap itself: at 90 minutes it cancels the step, kills the YARN application by its tag and exits 124. Each step also runs under a time limit on the node.
- If the script is gone (Mac slept, terminal closed), cancel by hand with the pipeline profile (fresh login first); the step id (`s-...`) is in `emr-run-N.log`, or in Console > EMR > the cluster > **Steps**:
  ```
  aws emr cancel-steps --cluster-id "$CID" --step-ids <s-id> --step-cancellation-option SEND_INTERRUPT --profile scholarchain-pipeline --region us-east-2
  aws emr describe-step --cluster-id "$CID" --step-id <s-id> --query Step.Status.State --output text --profile scholarchain-pipeline --region us-east-2
  ```
  (`ListSteps` and cluster termination are deliberately not granted to the pipeline role.) The cluster ends itself 15 minutes after its last step; the final backstop is Section C.
- A failed or cancelled run still counts against the three-run ledger and the USD 2.52 cumulative cap; a repeat is a new run with a new record.

**E8. The API stops answering you (timeouts) but the stack is healthy.** Your public IP changed: compare `curl -s https://checkip.amazonaws.com` with `public_ingress_cidrs`. Fix: edit the ignored tfvars, make a new runtime plan, record, receipt and runtime-apply (no commit). Until then continue the non-API work.

**E9. The EMR cluster ended before the next run (idle timeout).** The remaining approval records name a cluster that no longer exists and are void. Do the EMR runtime-apply again (B9.3 to B9.5, new plan, record and receipt); the three-run and USD 2.52 caps stay cumulative. If either cap is already used, stop 15A and tell the coordinator.

**E10. Certificate stays `PENDING_VALIDATION`.** B2: check the record is a CNAME, grey cloud, correct name, and CAA (A9). Do not run the runtime-apply until `ISSUED`.

**E11. Tunnel problems.** `TargetNotConnected`: the Exec agent is not ready, wait a minute. The port-forward prints an error or ends: repeat B7.4 only. `curl`/CLI times out: check T2, the hosts line (`grep -c "$WRITER" /etc/hosts` is 1) and that the task is running. Certificate error: the host name is not the real writer name. Task gone (4 hours): repeat B7.3 to B7.5.

**E12. Time or money is running out.** At H35, or when headroom would fall below 3, stop new paid work and go to Section C. The hard stop is H37.

**E13. The Mac slept or the terminal closed during a command.** Do not re-run an `--execute` stage. Read the last `STEP:` line of its log, compare `shasum -a 256 infra/terraform/terraform.tfstate` with the last recorded value, and send both to the coordinator. Loaders and uploads can be re-run (E2).

**E14. Anything this runbook does not describe.** Stop and ask. Do not improvise on AWS.

---

# Appendix: where files live

| What | Where | Committed? |
|---|---|---|
| Logs and evidence | `target/phase14/evidence/{14b,14c,15,16b,17}/` | no (git-ignored) |
| Approvals, receipts (copies) | `target/phase14/approvals/` | no |
| Private values (outputs, ARNs, plan texts, hosts backup, tunnel file) | `target/phase14/private/` | no; never archived or shared |
| 14C work files | `target/phase14/14c-work/` | no |
| Archive (before cleanup) | `target/phase14/archive/phase-14/evidence/session-v1/` | no, until the coordinator copies it after Section C |
| The stage approval record | `docs/agent-runs/phase-14/human-gate.md` | never (the one exempt path) |
| Private variables | `infra/terraform/environments/course.local.tfvars`, `infra/terraform/deployer/deployer.local.tfvars` | never |
| Downloads for the report | `~/Documents/scholarchain-session-downloads/` and `~/Movies/` | no (outside the repository) |
| Ledgers | `~/.scholarchain/llm-ledger/`, `~/.scholarchain/emr-ledger/` | no (outside the repository) |
