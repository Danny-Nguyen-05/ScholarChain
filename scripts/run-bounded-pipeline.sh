#!/usr/bin/env bash
# Phase 13B bounded pipeline: submit the Hadoop prep, entity-resolution and Spark steps to an EXISTING,
# Terraform-created EMR cluster. Dry run by default. Creates no infrastructure, ever.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/run-bounded-pipeline.sh --cluster-id J-ID --region R --instance-type T --core-count N
         [--max-task-count N] --max-runtime-minutes M --budget-usd B --input-prefix s3://b/k --output-prefix s3://b/k
         --hadoop-submit-jar REF --hadoop-libjars REF --hadoop-config FILE --er-jar REF --er-policy REF --er-config REF
         --spark-config-template REF --datasets-manifest FILE --artifact-sha256 NAME=HEX [...] [--run-id ID]
         [--approval FILE] [--prespend FILE] [--profile P] [--execute] [--help]
       scripts/run-bounded-pipeline.sh --init-ledger

Purpose
  Submit the bounded ScholarChain pipeline to an EXISTING EMR cluster created by Terraform (it never calls
  create-cluster, run-job-flow or any infrastructure API). Six steps, one EMR step each, run in order and stop at
  the first failure:
    1 stage-in            S3 -> EFS copy of the input prefix (G1 option ii), size-ceilinged, never into a used run directory
    2 hadoop-prep         HadoopPrepMain (Phase 4 style: --once, --execution-mode cluster) with the Phase 4 ceilings
    3 entity-resolution   Phase5Main resolve, a single-JVM step on the primary node; Java 17 is resolved at run time
                          from the file the bootstrap wrote (never hard-coded)
    4 spark-class-origin  Phase12Readiness probe on YARN: DRIVER AND EXECUTOR class origins (Spark, scala-library,
                          scala-reflect, scala3-library) must match the packaged job; fails CLOSED on any difference
    5 spark-job           Phase6Main via spark-submit, YARN cluster mode, decision 12-10 settings (portable runtime
                          with spark.yarn.jars=local:..., populateHadoopClasspath=false, codecs without LZO, Spark
                          authentication, AES-CTR with authEngineVersion=1, IO encryption, G2 dynamic allocation with
                          shuffle tracking), spark.yarn.tags=<run-id>; it re-checks the class-origin result first
    6 copy-out            EFS -> S3 copy of results and event logs (size-ceilinged) with a sha256 manifest

Item 1 (carried 12D finding): `timeout` kills only the client, not the YARN application. Every YARN step tags the
application with the run id; when the hard runtime cap fires (or the step is interrupted) the step body runs
`yarn application -list -appTags <run-id>` and `yarn application -kill <id>` for each match. The cluster's
auto-termination must stay set; --execute verifies it first.

Inputs (flags; there are no defaults for these)
  --cluster-id J-ID or SCHOLARCHAIN_EMR_CLUSTER_ID   --region R or SCHOLARCHAIN_AWS_REGION
  --instance-type T    m5.xlarge or m5.2xlarge (a reviewed hourly rate must exist in scripts/config/emr-pricing.conf)
  --core-count N       core nodes (1-10)           --max-task-count N   task nodes at most (default 0)
  --max-runtime-minutes M   hard cap, 10..PIPELINE_MAX_RUNTIME_MINUTES (180); 10 is a real minimum (each step gets its
                            PIPELINE_STEP_WEIGHTS percent, at least PIPELINE_MIN_STEP_SECONDS = 30 s); outside the range it
                            is refused (exit 3, step plan) with a message naming the range
  --budget-usd B       declared budget for this run, at most EMR_MAX_RUN_USD
  --input-prefix s3://bucket/key   must hold datasets/samples/{dblp,openalex,crossref,orcid}/... (Phase 4 layout)
  --output-prefix s3://bucket/key  results go to <prefix>/<run-id>/{hadoop,er,spark,results,config}/
  --hadoop-submit-jar REF, --hadoop-libjars REF, --er-jar REF, --er-policy REF, --er-config REF,
  --spark-config-template REF   a cluster-visible URI or primary-node path; the step localizes each and verifies its
                                sha256 (a local regular file is hashed here; otherwise pass --artifact-sha256)
  --hadoop-config FILE   local Phase 4 prep config; the ceilings are checked here and again on the cluster
  --datasets-manifest FILE   JSON {dblp,openalex,crossref,orcid: {snapshot, retrieval}}; recorded in the run manifest
  --artifact-sha256 NAME=HEX   names: hadoop-submit-jar hadoop-libjars er-jar job-jar hadoop-config er-policy
                                er-config spark-config-template. job-jar (the packaged Phase 6 job on the node at
                                PIPELINE_JOB_JAR_PATH) is always required
  --max-idle-seconds N   optional: require an auto-termination idle timeout of at most N seconds (it can only
                         tighten PIPELINE_MAX_IDLE_TIMEOUT_SECONDS); the value is part of the run configuration
  --delegated-from-experiment SHA   internal: set by run-experiment.sh; the record must then be a run-experiment
                         record whose APPROVED_MANIFEST_SHA256 equals SHA (do not use it by hand)
  --init-ledger  create the run ledger once (who and when), then exit; refuses when it exists; needs no other argument
  --run-id ID    default bp-<UTC time>-<pid>; also the YARN tag and the EFS run directory name (never reused)
  --approval FILE    approval record (default RUN_APPROVAL_RECORD_PATH); --prespend FILE pre-spend receipt
                     (default PRESPEND_RECEIPT_DEFAULT_PATH); --profile P or AWS_PROFILE for --execute
  Environment variable names: SCHOLARCHAIN_EMR_CLUSTER_ID, SCHOLARCHAIN_AWS_REGION, AWS_PROFILE,
  SCHOLARCHAIN_REPO_ROOT, SCHOLARCHAIN_CONFIG_FILE and SCHOLARCHAIN_PRICING_FILE (test-only). Pinned settings
  (caps, ceilings, rates, Spark file) come from scripts/config/*.conf; an environment variable cannot override them.

Modes
  (default)   DRY RUN: prints the run configuration, its sha256 (RUN-CONFIG-SHA256), the G6 estimate and status,
              every verification command and, for each step, the exact `aws emr add-steps` command and the
              readable step body. Runs NO aws, hadoop or spark command and writes nothing.
  --execute   human approval point 2 (plan Section 7.3). Needs an approval record, the pre-spend receipt, confirmed
              pricing and the G6 gates below.

Step form and the EMR argument limit (finding C1)
  EMR accepts at most 10,280 characters per string in a step's HadoopJarStepConfig.Args (PIPELINE_STEP_ARG_MAX_CHARS, pinned;
  it may be lowered, never raised). Each step is therefore `bash -c <short launcher> sc-step <sha256> <STEP> KEY=VALUE...`
  (about 1 KB at most per argument): the static runner scripts/emr/sc-step.sh (the on-node timeout wrapper and the six step
  bodies) and three small Python programs (ceiling check, class-origin verifier, spark-config renderer) are installed on
  the primary node by the bootstrap action as sha256-pinned --artifact files in PIPELINE_STEP_BIN_DIR, and the launcher
  verifies the runner against the sha256 computed here from the repository file (fail closed) before it runs it; the runner
  verifies each Python program the same way. The plan builder refuses (exit 3, STEP: arg-limit, STEP-ARG-TOO-LONG naming
  the step, argument and length) any argument over the limit BEFORE any cloud call, the ledger reservation and the
  approval; the dry run prints every argument length (STEP-ARG-LENGTHS) and runs the same check. The Terraform side pins the
  same hashes (infra/terraform/emr-step-programs.json); a drifted manifest is refused (STEP-PROGRAM-DRIFT).

Ceilings and refusals (all before any cloud call)
  Every step body, including stage-in, copy-out and the localize copies, runs on the node under
  `timeout --kill-after=PIPELINE_KILL_AFTER_SECONDS <its timeout_seconds>`, in its own process group: on timeout, failure or
  cancel the wrapper sends TERM to the whole group and KILL after the grace, so a grandchild that ignores TERM cannot outlive
  the step; YARN-submitting bodies also kill the YARN application by run tag when that timeout fires or on TERM.
  Phase 4 ceilings on the prep config (maxLocalSampleRecords<=12000 [pipeline-specific, PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS; the Phase 4 smoke keeps 1000] reducerCount<=8 maxCandidateBlockSize<=256
  maxCandidatePairsPerBlock<=4096 maxAuthorTeamSize<=64 maxRecordBytes<=8388608 maxXmlEntityExpansion<=8388608),
  input and copy-out byte ceilings, capacity <= PIPELINE_MAX_CAPACITY, runtime <= PIPELINE_MAX_RUNTIME_MINUTES.

G6 cost guard
  estimate = instances x (EC2 on-demand + EMR uplift rate) x (maximum runtime + the auto-termination idle timeout
  PIPELINE_MAX_IDLE_TIMEOUT_SECONDS, 900 s) hours: the idle tail before the cluster stops is billed too. It is printed in
  the dry run and before --execute. --execute is REFUSED when the estimate exceeds EMR_MAX_RUN_USD (3) or the declared
  budget, when the run ledger already holds EMR_MAX_LIVE_RUNS (3) live runs, when the cumulative estimate would exceed
  EMR_CUMULATIVE_CAP_USD (2.52), when a reviewed rate is missing (never read as zero), when the ledger does not exist, when
  the approval record already started a run, or while EMR_PRICING_CONFIRMED_BY_HUMAN is not true (a human flips it after
  checking the sources).

Run ledger (EMR_LEDGER_PATH, default ~/.scholarchain/emr-ledger/runs.jsonl, expanded against HOME)
  It lives OUTSIDE the repository and outside sbt's target/, so `sbt clean`, `git clean` and a fresh clone cannot erase it.
  An ABSENT ledger refuses --execute: it is never read as zero runs. The human creates it once with
      scripts/run-bounded-pipeline.sh --init-ledger
  which records who and when and REFUSES when the ledger already exists (a script never resets the spend record). Deleting
  the file by hand is the only reset and reopens the caps: do it only deliberately.
  Approvals are SINGLE-USE: a reservation stores the sha256 of the approval record, and a later run with the same record
  is refused even after a failed run (a failed run may have spent money). Write a new record (change any text, for example
  a serial line; text that is not an APPROVED_* line is ignored by the parser) for each run.

Human approval record (--execute): KEY=value lines, each exactly once, no quotes or spaces; other text is ignored
  APPROVED_ACTION=run-bounded-pipeline        APPROVED_COMMIT=<HEAD, 40 hex>       APPROVED_ACCOUNT_SHA256=<64 hex>
  APPROVED_REGION=<region>                    APPROVED_CLUSTER_ID=<j-...>          APPROVED_RUN_CONFIG_SHA256=<64 hex>
  APPROVED_BUDGET_USD=<decimal>               APPROVED_MAX_CAPACITY=<integer>      APPROVED_MAX_RUNTIME_MINUTES=<integer>
  APPROVED_TEARDOWN=auto-termination          APPROVED_PRESPEND_SHA256=<64 hex>
  The work tree must be clean (only the literal RUN_APPROVAL_RECORD_PATH is exempt). The pre-spend receipt
  (schema as for deploy.sh) is re-verified immediately before EACH step submission. Before the first paid
  operation --execute also checks the live account hash, describes the cluster (WAITING or RUNNING), requires
  an auto-termination idle timeout (aws emr get-auto-termination-policy) and only the approved instance
  type and counts (aws emr list-instance-groups), then reserves one ledger slot (a reservation counts for good).

Human approval points (plan Section 7.3)
  2. --execute: an approval record naming the run configuration, budget, region, capacity, maximum runtime and
     teardown, plus a pre-spend receipt. A reviewed dry run is not approval to execute. --init-ledger is a local file
     creation by the human, not a cloud action.

Exit codes
  0    success, or the dry run completed
  2    usage error
  3    refused: precondition, ceiling, G6 gate, approval, pre-spend or account check failed; nothing paid ran
  4    a verification gate failed (cluster check, class-origin result, step reported failed or cancelled)
  5    an underlying aws command failed
  124  a command or the hard runtime cap timed out (the running step is cancelled; its body kills the YARN application)

Evidence produced
  STEP: markers and one RESULT: line on stdout. --execute writes, exclusively and git-ignored, below
  PIPELINE_RUNS_DIR/<run-id>/: run-manifest.json (commit, run id, config, dataset snapshots, artifact hashes,
  limits, output locations, teardown) and run-result.json (per-step outcomes). Nothing is ever overwritten.
EOF
}

CLUSTER_ID="${SCHOLARCHAIN_EMR_CLUSTER_ID:-}"
REGION="${SCHOLARCHAIN_AWS_REGION:-}"
PROFILE="${AWS_PROFILE:-}"
INSTANCE_TYPE="" CORE_COUNT="" TASK_COUNT="0" RUNTIME_MIN="" BUDGET=""
INPUT_PREFIX="" OUTPUT_PREFIX=""
HADOOP_JAR="" HADOOP_LIBS="" HADOOP_CONFIG="" ER_JAR="" ER_POLICY="" ER_CONFIG="" SPARK_TEMPLATE="" DATASETS=""
RUN_ID_OPT="" IDLE_MAX_OPT=""
APPROVAL="" PRESPEND="" DELEGATED_MANIFEST_SHA=""
ARTIFACT_SHAS=()
EXECUTE=0
INIT_LEDGER=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cluster-id | --region | --instance-type | --core-count | --max-task-count | --max-runtime-minutes | --budget-usd | --input-prefix | --output-prefix | --hadoop-submit-jar | --hadoop-libjars | --hadoop-config | --er-jar | --er-policy | --er-config | --spark-config-template | --datasets-manifest | --artifact-sha256 | --run-id | --approval | --prespend | --profile | --max-idle-seconds | --delegated-from-experiment)
      if [[ $# -lt 2 ]]; then
        sc_usage_exit "run-bounded-pipeline.sh" "$1 needs a value"
      fi
      case "$1" in
        --cluster-id) CLUSTER_ID="$2" ;;
        --region) REGION="$2" ;;
        --instance-type) INSTANCE_TYPE="$2" ;;
        --core-count) CORE_COUNT="$2" ;;
        --max-task-count) TASK_COUNT="$2" ;;
        --max-runtime-minutes) RUNTIME_MIN="$2" ;;
        --budget-usd) BUDGET="$2" ;;
        --input-prefix) INPUT_PREFIX="$2" ;;
        --output-prefix) OUTPUT_PREFIX="$2" ;;
        --hadoop-submit-jar) HADOOP_JAR="$2" ;;
        --hadoop-libjars) HADOOP_LIBS="$2" ;;
        --hadoop-config) HADOOP_CONFIG="$2" ;;
        --er-jar) ER_JAR="$2" ;;
        --er-policy) ER_POLICY="$2" ;;
        --er-config) ER_CONFIG="$2" ;;
        --spark-config-template) SPARK_TEMPLATE="$2" ;;
        --datasets-manifest) DATASETS="$2" ;;
        --artifact-sha256) ARTIFACT_SHAS+=("$2") ;;
        --run-id) RUN_ID_OPT="$2" ;;
        --approval) APPROVAL="$2" ;;
        --prespend) PRESPEND="$2" ;;
        --profile) PROFILE="$2" ;;
        --max-idle-seconds) IDLE_MAX_OPT="$2" ;;
        --delegated-from-experiment) DELEGATED_MANIFEST_SHA="$2" ;;
      esac
      shift 2
      ;;
    --execute)
      EXECUTE=1
      shift
      ;;
    --dry-run)
      EXECUTE=0
      shift
      ;;
    --init-ledger)
      INIT_LEDGER=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      sc_usage_exit "run-bounded-pipeline.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "run-bounded-pipeline.sh"
sc_load_pricing

# The ledger lives outside the repository: EMR_LEDGER_PATH is expanded from a leading ~/ against HOME (finding B2).
[[ -n "${HOME:-}" && "${HOME}" == /* ]] || sc_usage_error "HOME must be an absolute path: the run ledger lives under it"
LEDGER_ABS="${EMR_LEDGER_PATH}"
case "${LEDGER_ABS}" in
  [~]/*) LEDGER_ABS="${HOME}/${LEDGER_ABS#[~]/}" ;;
esac
LEDGER_WITHIN="${HOME}/.scholarchain"
case "${LEDGER_ABS}" in
  "${LEDGER_WITHIN}"/*) ;;
  *) sc_usage_error "EMR_LEDGER_PATH must be under ~/.scholarchain/ (found ${EMR_LEDGER_PATH})" ;;
esac

if [[ "${INIT_LEDGER}" -eq 1 ]]; then
  [[ "${EXECUTE}" -eq 0 ]] || sc_usage_error "--init-ledger takes no other mode flag"
  [[ ${#ARTIFACT_SHAS[@]} -eq 0 && -z "${CLUSTER_ID}${INSTANCE_TYPE}${CORE_COUNT}${RUNTIME_MIN}${BUDGET}" ]] || sc_usage_error "--init-ledger takes no other argument"
  sc_banner "init-ledger"
  sc_step "ledger-init"
  sc_require_tool python3
  INIT_RC=0
  INIT_OUT="$(python3 -I "${SC_LIB_DIR}/budget.py" ledger-init --root "${HOME}" --within-name ".scholarchain under HOME" --within "${LEDGER_WITHIN}" \
    --ledger "${LEDGER_ABS}" --repo-root "${REPO_ROOT}" --initialized-by "$(id -un)" --initialized-utc "$(sc_now)")" || INIT_RC=$?
  if [[ "${INIT_RC}" -ne 0 ]]; then
    sc_refuse "${EX_REFUSED}" "${INIT_OUT}"
  fi
  sc_info "${INIT_OUT}"
  sc_result PASS "ledger initialised at ${EMR_LEDGER_PATH}; this is a local file, no cloud call was made" "${EX_OK}"
fi
if [[ "${EXECUTE}" -eq 1 ]]; then
  DRY_RUN=0
  sc_banner "execute"
else
  DRY_RUN=1
  sc_banner "dry-run"
fi
ACTION="run-bounded-pipeline"
if [[ -n "${DELEGATED_MANIFEST_SHA}" ]]; then
  ACTION="run-experiment"
fi

# ---------------------------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------------------------
sc_step "inputs"
sc_require_tool python3
for pair in "cluster id (--cluster-id or SCHOLARCHAIN_EMR_CLUSTER_ID)=${CLUSTER_ID}" "region (--region or SCHOLARCHAIN_AWS_REGION)=${REGION}" \
  "--instance-type=${INSTANCE_TYPE}" "--core-count=${CORE_COUNT}" "--max-runtime-minutes=${RUNTIME_MIN}" "--budget-usd=${BUDGET}" \
  "--input-prefix=${INPUT_PREFIX}" "--output-prefix=${OUTPUT_PREFIX}" "--hadoop-submit-jar=${HADOOP_JAR}" "--hadoop-libjars=${HADOOP_LIBS}" \
  "--hadoop-config=${HADOOP_CONFIG}" "--er-jar=${ER_JAR}" "--er-policy=${ER_POLICY}" "--er-config=${ER_CONFIG}" \
  "--spark-config-template=${SPARK_TEMPLATE}" "--datasets-manifest=${DATASETS}"; do
  [[ -n "${pair#*=}" ]] || sc_usage_error "missing required value: ${pair%%=*}"
done
sc_region_valid "${REGION}" || sc_usage_error "region '${REGION}' is not a valid AWS region name"
[[ "${CORE_COUNT}" =~ ^[0-9]+$ && "${TASK_COUNT}" =~ ^[0-9]+$ && "${RUNTIME_MIN}" =~ ^[0-9]+$ ]] || sc_usage_error "--core-count, --max-task-count and --max-runtime-minutes must be integers"
[[ "${BUDGET}" =~ ^[0-9]+(\.[0-9]{1,4})?$ ]] || sc_usage_error "--budget-usd must be a decimal number"
if [[ -n "${RUN_ID_OPT}" ]]; then
  RUN="${RUN_ID_OPT}"
else
  RUN="bp-${RUN_ID}"
fi
IDLE_MAX="${PIPELINE_MAX_IDLE_TIMEOUT_SECONDS}"
if [[ -n "${IDLE_MAX_OPT}" ]]; then
  [[ "${IDLE_MAX_OPT}" =~ ^[0-9]+$ && "${IDLE_MAX_OPT}" -ge 60 && "${IDLE_MAX_OPT}" -le "${PIPELINE_MAX_IDLE_TIMEOUT_SECONDS}" ]] ||
    sc_usage_error "--max-idle-seconds must be an integer from 60 to PIPELINE_MAX_IDLE_TIMEOUT_SECONDS (${PIPELINE_MAX_IDLE_TIMEOUT_SECONDS})"
  IDLE_MAX="${IDLE_MAX_OPT}"
fi
APPROVAL="${APPROVAL:-${REPO_ROOT}/${RUN_APPROVAL_RECORD_PATH}}"
PRESPEND="${PRESPEND:-${REPO_ROOT}/${PRESPEND_RECEIPT_DEFAULT_PATH}}"
if [[ "${EXECUTE}" -eq 1 ]]; then
  [[ -n "${PROFILE}" ]] || sc_refuse "${EX_REFUSED}" "--execute needs the approved AWS profile (--profile or AWS_PROFILE)"
  sc_require_tool aws
else
  [[ -n "${PROFILE}" ]] || PROFILE="<profile>"
fi

sc_step "terraform-only"
sc_info "this script submits steps to the existing cluster ${CLUSTER_ID}; it never creates, resizes or deletes infrastructure (no create-cluster, run-job-flow or Terraform command)"

# ---------------------------------------------------------------------------------------------
# G6 estimate: instances x reviewed hourly rate x maximum runtime
# ---------------------------------------------------------------------------------------------
sc_step "g6-estimate"
TYPE_KEY="$(printf '%s' "${INSTANCE_TYPE}" | tr '[:lower:].' '[:upper:]_')"
EC2_VAR="EMR_RATE_EC2_${TYPE_KEY}"
EMR_VAR="EMR_RATE_EMR_${TYPE_KEY}"
sc_mktemp ESTIMATE_FILE
EST_RC=0
python3 -I "${SC_LIB_DIR}/budget.py" estimate --instance-type "${INSTANCE_TYPE}" --primary-count 1 --core-count "${CORE_COUNT}" \
  --task-count "${TASK_COUNT}" --minutes "${RUNTIME_MIN}" --idle-seconds "${IDLE_MAX}" --ec2-rate "${!EC2_VAR:-}" --emr-rate "${!EMR_VAR:-}" \
  --max-run-usd "${EMR_MAX_RUN_USD}" --budget-usd "${BUDGET}" >"${ESTIMATE_FILE}" || EST_RC=$?
ESTIMATE_AVAILABLE=1
case "${EST_RC}" in
  0) ESTIMATE_JSON="$(cat "${ESTIMATE_FILE}")" ;;
  2)
    ESTIMATE_AVAILABLE=0
    ESTIMATE_JSON='{"estimate_usd": null, "formula": "unavailable: no reviewed hourly rate", "instances": null}'
    while IFS= read -r line; do sc_warn "${line}"; done <"${ESTIMATE_FILE}"
    ;;
  *)
    while IFS= read -r line; do sc_err "${line}"; done <"${ESTIMATE_FILE}"
    sc_refuse "${EX_REFUSED}" "the G6 cost guard refuses this run configuration (see G6-REFUSED above)"
    ;;
esac
if [[ "${ESTIMATE_AVAILABLE}" -eq 1 ]]; then
  ESTIMATE_USD="$(python3 -I -c 'import json,sys; print(json.loads(sys.argv[1])["estimate_usd"])' "${ESTIMATE_JSON}")"
  sc_info "G6 estimate: ${ESTIMATE_JSON}"
  printf 'ESTIMATE-USD: %s\n' "${ESTIMATE_USD}"
else
  ESTIMATE_USD=""
  printf 'ESTIMATE-USD: unavailable (rates %s and %s are not set in %s)\n' "${EC2_VAR}" "${EMR_VAR}" "${PIPELINE_PRICING_FILE}"
fi
printf 'G6-CAPS: per-run=%s USD live-runs=%s cumulative=%s USD pricing-confirmed-by-human=%s rates-retrieved=%s region=%s\n' \
  "${EMR_MAX_RUN_USD}" "${EMR_MAX_LIVE_RUNS}" "${EMR_CUMULATIVE_CAP_USD}" "${EMR_PRICING_CONFIRMED_BY_HUMAN:-unset}" "${EMR_PRICING_RETRIEVED:-unset}" "${EMR_PRICING_REGION:-unset}"

# ---------------------------------------------------------------------------------------------
# Plan: validate inputs and ceilings, hash local inputs, render the six steps (no cloud call)
# ---------------------------------------------------------------------------------------------
sc_step "plan"
sc_mktemp PLAN_FILE
sha_args=()
if [[ ${#ARTIFACT_SHAS[@]} -gt 0 ]]; then
  for item in "${ARTIFACT_SHAS[@]}"; do sha_args+=(--artifact-sha256 "${item}"); done
fi
# Ceiling values in the order of pipeline.py CEILING_FIELDS (the Phase 4 order).
PLAN_RC=0
PLAN_OUT="$(python3 -I "${SC_LIB_DIR}/pipeline.py" plan --out "${PLAN_FILE}" --run-id "${RUN}" --action "${ACTION}" --region "${REGION}" \
  --cluster-id "${CLUSTER_ID}" --instance-type "${INSTANCE_TYPE}" --core-count "${CORE_COUNT}" --max-task-count "${TASK_COUNT}" \
  --max-runtime-minutes "${RUNTIME_MIN}" --budget-usd "${BUDGET}" --input-prefix "${INPUT_PREFIX}" --output-prefix "${OUTPUT_PREFIX}" \
  --hadoop-submit-jar "${HADOOP_JAR}" --hadoop-libjars "${HADOOP_LIBS}" --hadoop-config "${HADOOP_CONFIG}" --er-jar "${ER_JAR}" \
  --er-policy "${ER_POLICY}" --er-config "${ER_CONFIG}" --spark-config-template "${SPARK_TEMPLATE}" --datasets-manifest "${DATASETS}" \
  --spark-conf-file "${REPO_ROOT}/${PIPELINE_SPARK_CONF_FILE}" --efs-mount "${PIPELINE_EFS_MOUNT}" --runtime-dir "${PIPELINE_RUNTIME_DIR}" \
  --job-jar-path "${PIPELINE_JOB_JAR_PATH}" --java-home-file "${PIPELINE_JAVA_HOME_FILE}" --er-xmx "${PIPELINE_ER_XMX}" \
  --expected-spark-version "${PIPELINE_EXPECTED_SPARK_VERSION}" --expected-scala-version "${PIPELINE_EXPECTED_SCALA_VERSION}" \
  --step-weights "${PIPELINE_STEP_WEIGHTS}" --runtime-archive-sha256 "${RUNTIME_ARCHIVE_EXPECTED_SHA256}" --estimate-json "${ESTIMATE_JSON}" \
  --max-capacity-cap "${PIPELINE_MAX_CAPACITY}" --max-runtime-cap "${PIPELINE_MAX_RUNTIME_MINUTES}" --max-input-bytes "${PIPELINE_MAX_INPUT_BYTES}" \
  --max-copyout-bytes "${PIPELINE_MAX_COPYOUT_BYTES}" --max-idle-timeout-seconds "${IDLE_MAX}" \
  --max-executors-per-node "${PIPELINE_MAX_EXECUTORS_PER_NODE}" --kill-after-seconds "${PIPELINE_KILL_AFTER_SECONDS}" --min-step-seconds "${PIPELINE_MIN_STEP_SECONDS}" \
  --step-bin-dir "${PIPELINE_STEP_BIN_DIR}" --step-arg-max-chars "${PIPELINE_STEP_ARG_MAX_CHARS}" \
  --ceiling-0 "${PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS}" --ceiling-1 "${PIPELINE_CEILING_REDUCER_COUNT}" \
  --ceiling-2 "${PIPELINE_CEILING_MAX_CANDIDATE_BLOCK_SIZE}" --ceiling-3 "${PIPELINE_CEILING_MAX_CANDIDATE_PAIRS_PER_BLOCK}" \
  --ceiling-4 "${PIPELINE_CEILING_MAX_AUTHOR_TEAM_SIZE}" --ceiling-5 "${PIPELINE_CEILING_MAX_RECORD_BYTES}" \
  --ceiling-6 "${PIPELINE_CEILING_MAX_XML_ENTITY_EXPANSION}" ${sha_args[@]+"${sha_args[@]}"})" || PLAN_RC=$?
if [[ "${PLAN_RC}" -ne 0 ]]; then
  case "${PLAN_OUT}" in
    *STEP-ARG-TOO-LONG*) sc_step "arg-limit" ;;
  esac
  sc_refuse "${EX_REFUSED}" "${PLAN_OUT:-the plan could not be built}"
fi
RUN_CONFIG_SHA="$(python3 -I "${SC_LIB_DIR}/pipeline.py" show --plan "${PLAN_FILE}" --what run-config-sha256)"
STEP_COUNT="$(python3 -I "${SC_LIB_DIR}/pipeline.py" show --plan "${PLAN_FILE}" --what step-count)"
MAX_CAPACITY="$(python3 -I "${SC_LIB_DIR}/pipeline.py" show --plan "${PLAN_FILE}" --what field:max_capacity)"
python3 -I "${SC_LIB_DIR}/pipeline.py" show --plan "${PLAN_FILE}" --what summary | sc_redact_stream | while IFS= read -r line; do
  printf 'PLAN: %s\n' "${line}"
done
printf 'RUN-CONFIG-SHA256: %s\n' "${RUN_CONFIG_SHA}"
printf 'TEARDOWN: forced auto-termination: the cluster must have an idle timeout of at most %ss (checked with --execute: aws emr get-auto-termination-policy)\n' "${IDLE_MAX}"
printf 'YARN-TAG: %s (the hard runtime cap kills the YARN application by this tag)\n' "${RUN}"

# Finding C1: EMR accepts at most 10,280 characters per step argument. The plan builder has already refused anything longer
# (before this point, hence before the ledger reservation and before any approval is consumed); print every length.
sc_step "arg-limit"
idx=0
while [[ "${idx}" -lt "${STEP_COUNT}" ]]; do
  printf 'STEP-ARG-LENGTHS: %s\n' "$(python3 -I "${SC_LIB_DIR}/pipeline.py" show --plan "${PLAN_FILE}" --what "step-arglens:${idx}")"
  idx=$((idx + 1))
done
printf 'STEP-ARG-LIMIT: no step argument exceeds %s characters (PIPELINE_STEP_ARG_MAX_CHARS, pinned; the EMR HadoopJarStepConfig.Args limit); checked before any cloud call, the ledger reservation and the approval\n' "${PIPELINE_STEP_ARG_MAX_CHARS}"

# ---------------------------------------------------------------------------------------------
# G6 gates (ledger, pricing confirmation). In a dry run they are reported; with --execute they refuse.
# ---------------------------------------------------------------------------------------------
sc_step "g6-gate"
G6_PROBLEMS=()
if [[ "${EMR_PRICING_CONFIRMED_BY_HUMAN:-false}" != "true" ]]; then
  G6_PROBLEMS+=("pricing is not confirmed by the human (EMR_PRICING_CONFIRMED_BY_HUMAN is not true in ${PIPELINE_PRICING_FILE})")
fi
if [[ "${ESTIMATE_AVAILABLE}" -eq 0 ]]; then
  G6_PROBLEMS+=("no reviewed hourly rate for ${INSTANCE_TYPE} (${EC2_VAR} / ${EMR_VAR}): the estimate cannot be computed and is never read as zero")
else
  LEDGER_RC=0
  LEDGER_OUT="$(python3 -I "${SC_LIB_DIR}/budget.py" ledger-check --ledger "${LEDGER_ABS}" --repo-root "${REPO_ROOT}" --estimate "${ESTIMATE_USD}" \
    --max-runs "${EMR_MAX_LIVE_RUNS}" --cumulative-cap "${EMR_CUMULATIVE_CAP_USD}")" || LEDGER_RC=$?
  if [[ "${LEDGER_RC}" -eq 0 ]]; then
    printf '%s\n' "${LEDGER_OUT}"
  else
    while IFS= read -r line; do G6_PROBLEMS+=("${line#G6-REFUSED: }"); done <<<"${LEDGER_OUT}"
  fi
fi
if [[ ${#G6_PROBLEMS[@]} -gt 0 ]]; then
  for line in "${G6_PROBLEMS[@]}"; do
    if [[ "${EXECUTE}" -eq 1 ]]; then
      sc_err "G6 gate: ${line}"
    else
      sc_warn "G6 status: --execute would be REFUSED: ${line}"
    fi
  done
  if [[ "${EXECUTE}" -eq 1 ]]; then
    sc_refuse "${EX_REFUSED}" "G6 gate refused --execute: ${G6_PROBLEMS[0]}"
  fi
  printf 'G6-STATUS: --execute would be refused (%d reason(s) above); this dry run still printed every command\n' "${#G6_PROBLEMS[@]}"
else
  printf 'G6-STATUS: all G6 gates pass for --execute\n'
fi

# ---------------------------------------------------------------------------------------------
# --execute only: clean tree, approval record, pre-spend receipt (local checks, before any aws call)
# ---------------------------------------------------------------------------------------------
AWS_ENV=(env "AWS_PROFILE=${PROFILE}" "AWS_REGION=${REGION}" AWS_PAGER=)
VERIFIED_PRESPEND=""
APPROVED_PRESPEND_SHA256=""
APPROVAL_SHA=""
_prespend_check() {
  local label="$1" now rc=0 clock=()
  now="$(sc_sha256 "${VERIFIED_PRESPEND}")"
  if [[ "${now}" != "${APPROVED_PRESPEND_SHA256}" ]]; then
    sc_refuse "${EX_REFUSED}" "pre-spend receipt copy changed (sha256 ${now}) before ${label}; no further paid operation will run"
  fi
  if [[ -n "${SC_CLOCK_FILE}" ]]; then
    clock=(--clock-file "${SC_CLOCK_FILE}" --label "${label}")
  fi
  python3 -I "${SC_LIB_DIR}/verify.py" prespend --file "${VERIFIED_PRESPEND}" \
    --max-age-hours "${PRESPEND_MAX_AGE_HOURS}" --min-headroom "${PRESPEND_MIN_HEADROOM_USD}" ${clock[@]+"${clock[@]}"} || rc=$?
  [[ "${rc}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "pre-spend receipt rejected before ${label}: that paid operation and every later one is not run"
}

COMMIT="$(sc_git_head || true)"
if [[ "${EXECUTE}" -eq 1 ]]; then
  sc_step "clean-tree"
  EXEMPT_REL="${RUN_APPROVAL_RECORD_PATH}"
  TREE_RC=0
  TREE_DETAIL="$(python3 -I "${SC_LIB_DIR}/verify.py" git-tree --repo "${REPO_ROOT}" --exempt "${EXEMPT_REL}")" || TREE_RC=$?
  case "${TREE_RC}" in
    0) ;;
    1) sc_refuse "${EX_REFUSED}" "work tree is dirty (${TREE_DETAIL}); commit or stash everything before --execute; only the literal ${EXEMPT_REL} is exempt" ;;
    *) sc_refuse "${EX_REFUSED}" "cannot determine whether the work tree is clean (${TREE_DETAIL}); refusing" ;;
  esac
  [[ -n "${COMMIT}" ]] || sc_refuse "${EX_REFUSED}" "not a git work tree with a commit"
  sc_info "clean tree at ${COMMIT}"

  sc_step "approval-record"
  [[ -f "${APPROVAL}" ]] || sc_refuse "${EX_REFUSED}" "approval record not found: ${APPROVAL#"${REPO_ROOT}"/}"
  PARSE_RC=0
  PARSED="$(python3 -I "${SC_LIB_DIR}/run_approval.py" parse --file "${APPROVAL}" --action "${ACTION}")" || PARSE_RC=$?
  if [[ "${PARSE_RC}" -ne 0 ]]; then
    sc_refuse "${EX_REFUSED}" "${PARSED}"
  fi
  _approved() { printf '%s\n' "${PARSED}" | sed -n "s/^$1=//p"; }
  A_ACTION="$(_approved APPROVED_ACTION)"
  A_COMMIT="$(_approved APPROVED_COMMIT)"
  A_ACCOUNT="$(_approved APPROVED_ACCOUNT_SHA256)"
  A_REGION="$(_approved APPROVED_REGION)"
  A_CLUSTER="$(_approved APPROVED_CLUSTER_ID)"
  A_CONFIG="$(_approved APPROVED_RUN_CONFIG_SHA256)"
  A_BUDGET="$(_approved APPROVED_BUDGET_USD)"
  A_CAPACITY="$(_approved APPROVED_MAX_CAPACITY)"
  A_RUNTIME="$(_approved APPROVED_MAX_RUNTIME_MINUTES)"
  A_TEARDOWN="$(_approved APPROVED_TEARDOWN)"
  APPROVED_PRESPEND_SHA256="$(_approved APPROVED_PRESPEND_SHA256)"
  A_MANIFEST="$(_approved APPROVED_MANIFEST_SHA256)"
  sc_info "approval record parsed (each required line exactly once)"
  sc_step "approval-match"
  [[ "${A_ACTION}" == "${ACTION}" ]] || sc_refuse "${EX_REFUSED}" "APPROVED_ACTION ${A_ACTION} != the action being run (${ACTION})"
  [[ "${A_COMMIT}" == "${COMMIT}" ]] || sc_refuse "${EX_REFUSED}" "APPROVED_COMMIT ${A_COMMIT} != HEAD ${COMMIT}"
  [[ "${A_REGION}" == "${REGION}" ]] || sc_refuse "${EX_REFUSED}" "APPROVED_REGION ${A_REGION} != region ${REGION}"
  [[ "${A_CLUSTER}" == "${CLUSTER_ID}" ]] || sc_refuse "${EX_REFUSED}" "APPROVED_CLUSTER_ID ${A_CLUSTER} != cluster id ${CLUSTER_ID}"
  [[ "${A_CONFIG}" == "${RUN_CONFIG_SHA}" ]] || sc_refuse "${EX_REFUSED}" "APPROVED_RUN_CONFIG_SHA256 ${A_CONFIG} != the run configuration sha256 ${RUN_CONFIG_SHA}"
  python3 -I -c 'import decimal,sys; sys.exit(0 if decimal.Decimal(sys.argv[1]) == decimal.Decimal(sys.argv[2]) else 1)' "${A_BUDGET}" "${BUDGET}" ||
    sc_refuse "${EX_REFUSED}" "APPROVED_BUDGET_USD ${A_BUDGET} != --budget-usd ${BUDGET}"
  [[ "${A_CAPACITY}" == "${MAX_CAPACITY}" ]] || sc_refuse "${EX_REFUSED}" "APPROVED_MAX_CAPACITY ${A_CAPACITY} != the maximum capacity ${MAX_CAPACITY}"
  [[ "${A_RUNTIME}" == "${RUNTIME_MIN}" ]] || sc_refuse "${EX_REFUSED}" "APPROVED_MAX_RUNTIME_MINUTES ${A_RUNTIME} != --max-runtime-minutes ${RUNTIME_MIN}"
  [[ "${A_TEARDOWN}" == "auto-termination" ]] || sc_refuse "${EX_REFUSED}" "APPROVED_TEARDOWN must be auto-termination"
  if [[ -n "${DELEGATED_MANIFEST_SHA}" ]]; then
    [[ "${A_MANIFEST}" == "${DELEGATED_MANIFEST_SHA}" ]] || sc_refuse "${EX_REFUSED}" "APPROVED_MANIFEST_SHA256 ${A_MANIFEST} != the experiment manifest sha256 ${DELEGATED_MANIFEST_SHA}"
  fi
  APPROVAL_SHA="$(sc_sha256 "${APPROVAL}")"
  sc_info "approval record matches the commit, region, cluster, run configuration, budget, capacity, runtime and teardown"
  # Finding B4: an approval is single-use. The ledger holds the sha256 of every record that started a run.
  USED_RC=0
  USED_OUT="$(python3 -I "${SC_LIB_DIR}/budget.py" ledger-check --ledger "${LEDGER_ABS}" --repo-root "${REPO_ROOT}" --estimate "${ESTIMATE_USD}" \
    --max-runs "${EMR_MAX_LIVE_RUNS}" --cumulative-cap "${EMR_CUMULATIVE_CAP_USD}" --approval-sha256 "${APPROVAL_SHA}")" || USED_RC=$?
  if [[ "${USED_RC}" -ne 0 ]]; then
    sc_refuse "${EX_REFUSED}" "${USED_OUT#G6-REFUSED: }"
  fi
  sc_info "approval record sha256 ${APPROVAL_SHA} has not started a run before (single-use)"

  sc_step "prespend-receipt"
  [[ -f "${PRESPEND}" ]] || sc_refuse "${EX_REFUSED}" "pre-spend receipt not found: ${PRESPEND#"${REPO_ROOT}"/} (the human writes it; see scripts/README.md)"
  sc_verified_copy "${PRESPEND}" VERIFIED_PRESPEND
  PRESPEND_SHA="$(sc_sha256 "${VERIFIED_PRESPEND}")"
  [[ "${PRESPEND_SHA}" == "${APPROVED_PRESPEND_SHA256}" ]] ||
    sc_refuse "${EX_REFUSED}" "pre-spend receipt sha256 ${PRESPEND_SHA} != APPROVED_PRESPEND_SHA256 ${APPROVED_PRESPEND_SHA256}"
  _prespend_check "initial"
else
  sc_step "approval-record"
  sc_info "dry run: with --execute the approval record ${APPROVAL#"${REPO_ROOT}"/} must name exactly these lines (each once, KEY=value):"
  printf 'APPROVAL-LINE: APPROVED_ACTION=%s\n' "${ACTION}"
  printf 'APPROVAL-LINE: APPROVED_COMMIT=%s\n' "${COMMIT:-<HEAD of a clean tree>}"
  printf 'APPROVAL-LINE: APPROVED_ACCOUNT_SHA256=<sha256 of the 12-digit account id string, no newline>\n'
  printf 'APPROVAL-LINE: APPROVED_REGION=%s\n' "${REGION}"
  printf 'APPROVAL-LINE: APPROVED_CLUSTER_ID=%s\n' "${CLUSTER_ID}"
  printf 'APPROVAL-LINE: APPROVED_RUN_CONFIG_SHA256=%s\n' "${RUN_CONFIG_SHA}"
  if [[ -n "${DELEGATED_MANIFEST_SHA}" ]]; then
    printf 'APPROVAL-LINE: APPROVED_MANIFEST_SHA256=%s\n' "${DELEGATED_MANIFEST_SHA}"
  fi
  printf 'APPROVAL-LINE: APPROVED_BUDGET_USD=%s\n' "${BUDGET}"
  printf 'APPROVAL-LINE: APPROVED_MAX_CAPACITY=%s\n' "${MAX_CAPACITY}"
  printf 'APPROVAL-LINE: APPROVED_MAX_RUNTIME_MINUTES=%s\n' "${RUNTIME_MIN}"
  printf 'APPROVAL-LINE: APPROVED_TEARDOWN=auto-termination\n'
  printf 'APPROVAL-LINE: APPROVED_PRESPEND_SHA256=<sha256 of the pre-spend receipt the human wrote>\n'
  sc_step "prespend-receipt"
  sc_info "dry run: the pre-spend receipt would be verified now and re-verified immediately before each step submission"
fi

# ---------------------------------------------------------------------------------------------
# Cluster verification commands (printed in a dry run; run with --execute before any paid operation)
# ---------------------------------------------------------------------------------------------
sc_step "account-check"
sc_mktemp ID_FILE
RC=0
sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${ID_FILE}" -- \
  "${AWS_ENV[@]}" aws sts get-caller-identity --region "${REGION}" --query Account --output text || RC=$?
ACCOUNT_HASH="<computed at --execute>"
if [[ "${EXECUTE}" -eq 1 ]]; then
  [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "aws sts get-caller-identity failed (exit ${RC}); nothing paid ran"
  ACCOUNT_ID="$(tr -d '[:space:]' <"${ID_FILE}")"
  sc_register_account "${ACCOUNT_ID}"
  [[ "${ACCOUNT_ID}" =~ ^[0-9]{12}$ ]] || sc_refuse "${EX_REFUSED}" "unexpected account identity output; nothing paid ran"
  ACCOUNT_HASH="$(sc_sha256_string "${ACCOUNT_ID}")"
  [[ "${ACCOUNT_HASH}" == "${A_ACCOUNT}" ]] || sc_refuse "${EX_REFUSED}" "account sha256 ${ACCOUNT_HASH} != APPROVED_ACCOUNT_SHA256 ${A_ACCOUNT}; nothing paid ran"
  sc_info "account sha256 matches the approval record"
else
  sc_info "dry run: the account comparison runs only with --execute, before any paid operation"
fi

sc_step "cluster-check"
sc_mktemp DESCRIBE_FILE
sc_mktemp POLICY_FILE
sc_mktemp GROUPS_FILE
RC=0
sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${DESCRIBE_FILE}" -- \
  "${AWS_ENV[@]}" aws emr describe-cluster --region "${REGION}" --cluster-id "${CLUSTER_ID}" --output json || RC=$?
[[ "${EXECUTE}" -eq 0 || "${RC}" -eq 0 ]] || sc_fail "$(sc_rc_to_exit "${RC}")" "aws emr describe-cluster failed (exit ${RC})"
RC=0
sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${POLICY_FILE}" -- \
  "${AWS_ENV[@]}" aws emr get-auto-termination-policy --region "${REGION}" --cluster-id "${CLUSTER_ID}" --output json || RC=$?
[[ "${EXECUTE}" -eq 0 || "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "aws emr get-auto-termination-policy failed (exit ${RC}): forced auto-termination cannot be verified"
RC=0
sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${GROUPS_FILE}" -- \
  "${AWS_ENV[@]}" aws emr list-instance-groups --region "${REGION}" --cluster-id "${CLUSTER_ID}" --output json || RC=$?
[[ "${EXECUTE}" -eq 0 || "${RC}" -eq 0 ]] || sc_fail "$(sc_rc_to_exit "${RC}")" "aws emr list-instance-groups failed (exit ${RC})"
if [[ "${EXECUTE}" -eq 1 ]]; then
  CHECK_RC=0
  CHECK_OUT="$(python3 -I "${SC_LIB_DIR}/pipeline.py" check-cluster --describe "${DESCRIBE_FILE}" --policy "${POLICY_FILE}" --groups "${GROUPS_FILE}" \
    --cluster-id "${CLUSTER_ID}" --instance-type "${INSTANCE_TYPE}" --core-count "${CORE_COUNT}" --max-task-count "${TASK_COUNT}" \
    --max-capacity "${MAX_CAPACITY}" --max-idle-seconds "${IDLE_MAX}")" || CHECK_RC=$?
  if [[ "${CHECK_RC}" -ne 0 ]]; then
    while IFS= read -r line; do sc_err "${line}"; done <<<"${CHECK_OUT}"
    sc_fail "${EX_GATE}" "cluster verification failed (forced auto-termination, state or capacity); nothing paid ran"
  fi
  sc_info "${CHECK_OUT}"
else
  sc_info "dry run: --execute requires a WAITING or RUNNING cluster WITH an auto-termination idle timeout (60..${IDLE_MAX} s) and only ${INSTANCE_TYPE} groups within primary=1 core<=${CORE_COUNT} task<=${TASK_COUNT}"
fi

# ---------------------------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------------------------
_print_step() {
  local index="$1" name json seconds
  name="$(python3 -I "${SC_LIB_DIR}/pipeline.py" show --plan "${PLAN_FILE}" --what "step-name:${index}")"
  seconds="$(python3 -I "${SC_LIB_DIR}/pipeline.py" show --plan "${PLAN_FILE}" --what "step-seconds:${index}")"
  json="$(python3 -I "${SC_LIB_DIR}/pipeline.py" show --plan "${PLAN_FILE}" --what "step-json:${index}")"
  sc_step "step-${name}"
  printf 'STEP-TIMEOUT: %s %ss (the whole step body, including every copy, runs on the node under timeout --kill-after=%ss in its own process group, which is sent TERM and then KILL after the grace on timeout or cancel; YARN applications are also killed by tag when it fires)\n' "${name}" "${seconds}" "${PIPELINE_KILL_AFTER_SECONDS}"
  printf 'STEP-BODY-BEGIN: %s\n' "${name}"
  python3 -I "${SC_LIB_DIR}/pipeline.py" show --plan "${PLAN_FILE}" --what "step-body:${index}" | sc_redact_stream
  printf 'STEP-BODY-END: %s\n' "${name}"
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" -- \
    "${AWS_ENV[@]}" aws emr add-steps --region "${REGION}" --cluster-id "${CLUSTER_ID}" --steps "${json}"
}

if [[ "${EXECUTE}" -eq 0 ]]; then
  idx=0
  while [[ "${idx}" -lt "${STEP_COUNT}" ]]; do
    _print_step "${idx}"
    idx=$((idx + 1))
  done
  sc_step "dry-run-complete"
  sc_result DRY-RUN "run=${RUN} steps=${STEP_COUNT} run_config_sha256=${RUN_CONFIG_SHA} estimate_usd=${ESTIMATE_USD:-unavailable}; no aws, hadoop or spark command was run and nothing was written" "${EX_OK}"
fi

# ---- --execute: reserve the G6 ledger slot, write the private manifest, submit and watch each step ----
sc_step "ledger-reserve"
RES_RC=0
RES_OUT="$(python3 -I "${SC_LIB_DIR}/budget.py" ledger-reserve --root "${HOME}" --ledger "${LEDGER_ABS}" --repo-root "${REPO_ROOT}" --run-id "${RUN}" \
  --estimate "${ESTIMATE_USD}" --max-runs "${EMR_MAX_LIVE_RUNS}" --cumulative-cap "${EMR_CUMULATIVE_CAP_USD}" --action "${ACTION}" \
  --run-config-sha256 "${RUN_CONFIG_SHA}" --approval-sha256 "${APPROVAL_SHA}" --reserved-utc "$(sc_now)")" || RES_RC=$?
if [[ "${RES_RC}" -ne 0 ]]; then
  sc_refuse "${EX_REFUSED}" "ledger reservation refused: ${RES_OUT}"
fi
sc_info "${RES_OUT}"

sc_step "run-manifest"
RUNS_ABS="${REPO_ROOT}/${PIPELINE_RUNS_DIR}"
sc_safeio ensure-dir --root "${REPO_ROOT}" --within-name "${PIPELINE_RUNS_DIR}" --within "${RUNS_ABS}" --path "${RUNS_ABS}"
RUN_OUT_DIR="${RUNS_ABS}/${RUN}"
sc_require_ignored "${RUN_OUT_DIR}"
sc_safeio fresh-dir --root "${REPO_ROOT}" --within-name "${PIPELINE_RUNS_DIR}" --within "${RUNS_ABS}" --path "${RUN_OUT_DIR}"
RUN_OUT_DIR="${SC_SAFEIO_OUT}"
MANIFEST_PATH="${RUN_OUT_DIR}/run-manifest.json"
MAN_OUT="$(python3 -I "${SC_LIB_DIR}/pipeline.py" write-manifest --root "${REPO_ROOT}" --out "${MANIFEST_PATH}" --plan "${PLAN_FILE}" --kind planned \
  --at "$(sc_now)" --commit "${COMMIT}" --account-sha256 "${ACCOUNT_HASH}" --approval-sha256 "${APPROVAL_SHA}" --prespend-sha256 "${APPROVED_PRESPEND_SHA256}")" ||
  sc_refuse "${EX_REFUSED}" "${MAN_OUT}"
sc_info "run manifest: ${MANIFEST_PATH#"${REPO_ROOT}"/}"

DEADLINE_SECONDS=$((RUNTIME_MIN * 60))
if [[ -n "${SCHOLARCHAIN_TEST_DEADLINE_SECONDS:-}" ]]; then
  if [[ -n "${SCHOLARCHAIN_CONFIG_FILE:-}" ]]; then
    printf 'DEADLINE-OVERRIDE: using %ss as the wall-clock cap (test-only; honoured because SCHOLARCHAIN_CONFIG_FILE is set)\n' "${SCHOLARCHAIN_TEST_DEADLINE_SECONDS}"
    DEADLINE_SECONDS="${SCHOLARCHAIN_TEST_DEADLINE_SECONDS}"
  else
    printf 'DEADLINE-IGNORED: SCHOLARCHAIN_TEST_DEADLINE_SECONDS is honoured only together with the test-only SCHOLARCHAIN_CONFIG_FILE\n'
  fi
fi
START_SECONDS="${SECONDS}"
OUTCOMES=()
STEP_ID=""

_finish() { # status code
  local status="$1" code="$2" args=() item
  for item in ${OUTCOMES[@]+"${OUTCOMES[@]}"}; do args+=(--outcome "${item}"); done
  python3 -I "${SC_LIB_DIR}/pipeline.py" write-manifest --root "${REPO_ROOT}" --out "${RUN_OUT_DIR}/run-result.json" --plan "${PLAN_FILE}" \
    --kind result --at "$(sc_now)" --status "${status}" ${args[@]+"${args[@]}"} >/dev/null || sc_warn "the result record could not be written"
  if [[ "${code}" -eq 0 ]]; then
    sc_result PASS "run=${RUN} all ${STEP_COUNT} steps COMPLETED; manifest ${MANIFEST_PATH#"${REPO_ROOT}"/}" "${EX_OK}"
  fi
  sc_fail "${code}" "run=${RUN} ${status}"
}

_cancel() {
  local rc=0
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" -- "${AWS_ENV[@]}" aws emr cancel-steps --region "${REGION}" --cluster-id "${CLUSTER_ID}" \
    --step-ids "${STEP_ID}" --step-cancellation-option SEND_INTERRUPT || rc=$?
  sc_warn "step ${STEP_ID} cancellation requested (exit ${rc}); the step body kills the YARN application tagged ${RUN} on SIGTERM and the cluster auto-terminates when idle"
}

idx=0
while [[ "${idx}" -lt "${STEP_COUNT}" ]]; do
  NAME="$(python3 -I "${SC_LIB_DIR}/pipeline.py" show --plan "${PLAN_FILE}" --what "step-name:${idx}")"
  JSON="$(python3 -I "${SC_LIB_DIR}/pipeline.py" show --plan "${PLAN_FILE}" --what "step-json:${idx}")"
  sc_step "step-${NAME}"
  _prespend_check "step-${NAME}"
  sc_info "pre-spend receipt re-verified before submitting step ${NAME}"
  sc_mktemp SUBMIT_OUT
  RC=0
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${SUBMIT_OUT}" -- \
    "${AWS_ENV[@]}" aws emr add-steps --region "${REGION}" --cluster-id "${CLUSTER_ID}" --steps "${JSON}" --query 'StepIds[0]' --output text || RC=$?
  if [[ "${RC}" -ne 0 ]]; then
    OUTCOMES+=("${NAME}=SUBMIT-FAILED")
    _finish "FAILED at step ${NAME}: aws emr add-steps failed (exit ${RC})" "$(sc_rc_to_exit "${RC}")"
  fi
  STEP_ID="$(tr -d '[:space:]' <"${SUBMIT_OUT}")"
  [[ "${STEP_ID}" =~ ^s-[A-Z0-9]+$ ]] || {
    OUTCOMES+=("${NAME}=SUBMIT-FAILED")
    _finish "FAILED at step ${NAME}: unexpected step id output" "${EX_CMDFAIL}"
  }
  printf 'STEP-SUBMITTED: %s %s\n' "${NAME}" "${STEP_ID}"
  while true; do
    sc_mktemp STATE_OUT
    RC=0
    sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${STATE_OUT}" -- \
      "${AWS_ENV[@]}" aws emr describe-step --region "${REGION}" --cluster-id "${CLUSTER_ID}" --step-id "${STEP_ID}" --query 'Step.Status.State' --output text || RC=$?
    if [[ "${RC}" -ne 0 ]]; then
      _cancel
      OUTCOMES+=("${NAME}=STATE-UNKNOWN")
      _finish "FAILED at step ${NAME}: describe-step failed (exit ${RC}); the step was asked to stop" "$(sc_rc_to_exit "${RC}")"
    fi
    STATE="$(tr -d '[:space:]' <"${STATE_OUT}")"
    case "${STATE}" in
      COMPLETED)
        printf 'STEP-RESULT: %s %s COMPLETED\n' "${NAME}" "${STEP_ID}"
        OUTCOMES+=("${NAME}=COMPLETED")
        break
        ;;
      FAILED | CANCELLED | INTERRUPTED)
        printf 'STEP-RESULT: %s %s %s\n' "${NAME}" "${STEP_ID}" "${STATE}"
        OUTCOMES+=("${NAME}=${STATE}")
        _finish "FAILED at step ${NAME}: state ${STATE}" "${EX_GATE}"
        ;;
      PENDING | RUNNING | CANCEL_PENDING) ;;
      *)
        _cancel
        OUTCOMES+=("${NAME}=STATE-UNKNOWN")
        _finish "FAILED at step ${NAME}: unexpected step state '${STATE}'" "${EX_GATE}"
        ;;
    esac
    if [[ $((SECONDS - START_SECONDS)) -gt "${DEADLINE_SECONDS}" ]]; then
      _cancel
      OUTCOMES+=("${NAME}=TIMED-OUT")
      _finish "TIMED OUT at step ${NAME}: the hard runtime cap of ${DEADLINE_SECONDS}s was reached" "${EX_TIMEOUT}"
    fi
    sleep "${PIPELINE_POLL_SECONDS}"
  done
  idx=$((idx + 1))
done
_finish "all steps COMPLETED" 0
