#!/usr/bin/env python3
"""Offline checks for the Phase 15 experiment manifests (stdlib; python3 -I). No AWS, no network, writes nothing in the repository.

  python3 -I experiments/scripts/check_manifests.py [--final]

Checks
  15A  experiments/manifests/15a-*.json: size-25 and size-50 (Session 1 history, 90 min, m5.xlarge) and size-100 = size S (120 min,
       r5.xlarge primary + m5.xlarge core, charged twice: run plus one retry); any other 15A manifest fails (size L is local evidence only,
       experiments/inputs/15a/size-l-local-evidence.json)
       * policy: only the committed token ${SCHOLARCHAIN_ARTIFACTS_BUCKET} names a bucket (no literal bucket),
         and no run of 12 digits outside a sha256 (an AWS account id);
       * scripts/lib/experiment.py validate (the validator run-experiment.sh uses) on a temporary copy in which the tokens are replaced by
         syntactically valid dummy names, with the pinned caps read from scripts/config/release.conf;
       * the G6 estimate ((primary rate + core and task rates) x (runtime + idle timeout), the primary priced at primary_instance_type) from
         scripts/config/emr-pricing.conf is within budget.max_usd; max_runtime_minutes equals the approved cap (history 90, S 120); the ledger
         (Session 1 history 2 x 0.84 + the Session 2 S attempt recorded at 0.37, evidence docs/agent-runs/phase-15/evidence/session-2/emr/
         emr-actual-1end.log + 2 x S reserves, 5 runs) must fit EMR_CUMULATIVE_CAP_USD and EMR_MAX_LIVE_RUNS, and so must the stricter
         admission rule of scripts/lib/budget.py (measured actuals 2.05 + the 0.14 idle tail of run 4 + the 1.25 retry estimate); otherwise
         CHECK-BLOCKED, exit 3: the ledger decision is the human's and the pin is infra-engineer's; the configuration checks below apply to S only;
       * the four configuration URIs (hadoop_config, er_policy, er_config, spark_config_template) are
         s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}/config/<name>.json and their artifact_sha256 equal the sha256 of
         the repository files listed in experiments/inputs/15a/config-sources.json (which must match the files);
       * the local prep config (config-sources.json hadoop-config) satisfies the pinned Phase 4 ceilings (a violation is CHECK-BLOCKED,
         exit 3: the pin is infra-engineer's), and its maxLocalSampleRecords covers L plus the other-source records (the L slice manifest's
         publicationCount once it exists, else the planning bound 50,000);
       * the datasets manifest names exactly dblp, openalex, crossref, orcid with snapshot and retrieval;
       * the L local-evidence record says L is not an EMR run and, once datasets/phase15/dblp-l-slice-manifest.v1.json exists, states its
         publication count and sha256.
  15B  experiments/manifests/15b-ecs-scaling.json against load-tests/loadgen.py (strict schema, phase limits, answer budget).
  15B semantic (P42)  experiments/manifests/15b-ecs-scaling-semantic.json: the REQUIRED per-level limits 600 / 3,000 / 15,000 / 30,000 / 150,000 (198,600 in
       total), one warm-up phase at level 1 of at most 200 requests, at least 25 quiet minutes, the fixed questions file (sha256, count, distinct, provenance).
  16B  16b-live-evaluation.json and llm-allocation.json (v2, buckets 14c/15b/16b/17): allocated answers x the pinned claude-haiku-5-5 (Anthropic API) cost per answer must fit in the shared cap (USD 1.33 stays; the bucket counts bind first),
       and the 15B and 16B figures must equal the allocation.
  16 evaluation (Phase 16)  experiments/manifests/16-evaluation.json (the whole Phase 16 package, written by eval16_answers.py manifest): the schema and id, the offline scope (no network, no
       AWS, no model call, spend 0.00), the policy above (no account id, no literal bucket), well-formed relative paths and sha256 values, and, when experiments/results/phase16
       exists in the root, that every tracked input, script and output exists with exactly the recorded sha256 (an untracked input under target/ is verified only where present), that no entry lacks a sha256 (except an untracked directory entry with a listing hash), and that every file under experiments/results/phase16 is listed or declared in excluded_outputs.
  --final  also refuses the all-zero sha256 placeholders and the PLACEHOLDER-L-* markers: the state required before the commit freeze
           (tokens plus real hashes pass).

Exit: 0 all checks pass, 1 a check failed, 3 blocked by a pinned ceiling owned by another role.
"""
import argparse
import decimal
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = decimal.Decimal
CENT = D("0.01")
CEILING_KEYS = (
    ("maxLocalSampleRecords", "PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS"),
    ("reducerCount", "PIPELINE_CEILING_REDUCER_COUNT"),
    ("maxCandidateBlockSize", "PIPELINE_CEILING_MAX_CANDIDATE_BLOCK_SIZE"),
    ("maxCandidatePairsPerBlock", "PIPELINE_CEILING_MAX_CANDIDATE_PAIRS_PER_BLOCK"),
    ("maxAuthorTeamSize", "PIPELINE_CEILING_MAX_AUTHOR_TEAM_SIZE"),
    ("maxRecordBytes", "PIPELINE_CEILING_MAX_RECORD_BYTES"),
    ("maxXmlEntityExpansion", "PIPELINE_CEILING_MAX_XML_ENTITY_EXPANSION"),
)
SOURCES = ("dblp", "openalex", "crossref", "orcid")
CONFIG_SOURCES = os.path.join("experiments", "inputs", "15a", "config-sources.json")
# config-sources.json name -> manifest pipeline field, and the S3 key under emr/<run_prefix>/ the upload script writes.
CONFIG_URIS = {"hadoop-config": "hadoop_config", "er-policy": "er_policy", "er-config": "er_config", "spark-config-template": "spark_config_template"}
CONFIG_KEYS = {"hadoop-config": "config/hadoop-config.json", "er-policy": "config/er-policy.json", "er-config": "config/er-config.json",
               "spark-config-template": "config/spark-config-template.json"}
S_MANIFEST = "15a-emr-size-100.json"
# The EMR ledger (user decisions 2026-11-16, docs/agent-runs/phase-15/prompt.md): Session 1's two historical m5.xlarge runs, then S and one
# S retry. name -> (role, runs charged to the ledger, approved run cap in minutes). L is local evidence only: no EMR manifest may exist for it.
EMR_LEDGER = {
    "15a-emr-size-25.json": ("Session 1 history", 1, 90),
    "15a-emr-size-50.json": ("Session 1 history", 1, 90),
    S_MANIFEST: ("size S run and one retry", 2, 120),  # 75 -> 120 min, max_usd 0.84 -> 1.25: human, 2026-11-24, docs/agent-runs/phase-18/human-gate.md
}
# The ledger also holds a third run that has no manifest here: the Session 2 S attempt of 2026-11-18 (75-minute cap, reserved 0.84), recorded
# at its measured actual. It is history, not a reserve: it counts as one live run and its recorded USD amount, never as a new estimate.
# Source (committed evidence): LEDGER-ACTUAL line "measured_usd=0.37 tail_seconds=0 tail_usd=0.00" and "live_runs=3 of 4 cumulative_usd=2.05".
SESSION2_EVIDENCE = os.path.join("docs", "agent-runs", "phase-15", "evidence", "session-2", "emr", "emr-actual-1end.log")
SESSION2_EVIDENCE_LINES = ("measured_usd=0.37 tail_seconds=0 tail_usd=0.00", "live_runs=3 of 4 cumulative_usd=2.05")
SESSION2_ATTEMPT_USD = D("0.37")
S_INSTANCE_TYPES = ("r5.xlarge", "m5.xlarge")  # D3: (primary, core)
L_EVIDENCE = os.path.join("experiments", "inputs", "15a", "size-l-local-evidence.json")
L_SLICE_MANIFEST = os.path.join("datasets", "phase15", "dblp-l-slice-manifest.v1.json")
L_PLANNING_MAX = 50000  # TARGET_MAX of datasets/scripts/phase15/select_dblp_l_slice.py, used until the L slice manifest exists
OTHER_SAMPLES = ("openalex/works.jsonl", "crossref/works.jsonl", "orcid/records.jsonl")


def read_conf(path):
    values = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip()
    return values


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hourly_rate(pricing, instance_type):
    suffix = instance_type.upper().replace(".", "_")
    return D(pricing["EMR_RATE_EC2_" + suffix]) + D(pricing["EMR_RATE_EMR_" + suffix])


def g6_hourly(manifest, pricing):
    """primary rate + (core + task) x core rate, USD per hour; the primary is priced at its own type (pipeline.primary_instance_type)."""
    pipeline = manifest["pipeline"]
    primary = hourly_rate(pricing, pipeline.get("primary_instance_type", pipeline["instance_type"]))
    return primary + hourly_rate(pricing, pipeline["instance_type"]) * (pipeline["core_count"] + pipeline.get("max_task_count", 0))


def g6_estimate(manifest, pricing):
    """(primary rate + (core + task) x core rate) x (runtime + idle timeout), rounded up to the cent. The primary is priced at its own type
    (pipeline.primary_instance_type, default instance_type; Phase 15 D3), as scripts/lib/budget.py does."""
    seconds = manifest["budget"]["max_runtime_minutes"] * 60 + manifest["teardown"]["max_idle_timeout_seconds"]
    return (g6_hourly(manifest, pricing) * D(seconds) / D(3600)).quantize(CENT, rounding=decimal.ROUND_UP)


TOKENS = ("${SCHOLARCHAIN_ARTIFACTS_BUCKET}", "${SCHOLARCHAIN_RUN_PREFIX}")
# Syntactically valid stand-ins used ONLY to run the existing validator on a temporary copy; they hold no digits and name nothing real.
DUMMY = {"${SCHOLARCHAIN_ARTIFACTS_BUCKET}": "scholarchain-check-artifacts", "${SCHOLARCHAIN_RUN_PREFIX}": "run-check"}
HEX64 = re.compile(r"[0-9a-f]{64}")
S3_REF = re.compile(r's3://([^/"]+)/')


def substitute(text):
    for token, value in DUMMY.items():
        text = text.replace(token, value)
    return text


def policy_problems(text):
    """Rules that hold for every committed manifest: tokens only, no account id (a run of 12 digits outside a sha256), no literal bucket."""
    out = []
    if re.search(r"(?<![0-9])[0-9]{12}(?![0-9])", HEX64.sub("", text)):
        out.append("a run of 12 digits (possible AWS account id) appears outside a sha256")
    for bucket in sorted(set(S3_REF.findall(text))):
        if bucket != "${SCHOLARCHAIN_ARTIFACTS_BUCKET}":
            out.append("s3 bucket %r is not the committed token ${SCHOLARCHAIN_ARTIFACTS_BUCKET}" % bucket)
    return out


def placeholder_problems(text):
    """--final only: the all-zero sha256 placeholders and the L slice markers must be replaced by real values."""
    out = ["an all-zero sha256 placeholder remains"] if re.search(r'"0{64}"', text) else []
    for marker in sorted(set(re.findall(r"PLACEHOLDER-[A-Z0-9-]+", text))):
        out.append("the placeholder %s remains (render after the L slice manifest exists)" % marker)
    return out


def _validate(root, path, conf):
    return subprocess.run(
        [sys.executable, "-I", os.path.join(root, "scripts", "lib", "experiment.py"), "validate", "--manifest", path, "--max-run-usd", conf["EMR_MAX_RUN_USD"],
         "--max-runtime-cap", conf["PIPELINE_MAX_RUNTIME_MINUTES"], "--max-capacity-cap", conf["PIPELINE_MAX_CAPACITY"], "--max-idle-cap", conf["PIPELINE_MAX_IDLE_TIMEOUT_SECONDS"]],
        capture_output=True, text=True, timeout=60)


def config_files(root):
    """{name: (repository path, sha256 of the file)} for the four configuration files of config-sources.json, or a problem string."""
    with open(os.path.join(root, CONFIG_SOURCES), encoding="utf-8") as handle:
        files = json.load(handle)["files"]
    if sorted(files) != sorted(CONFIG_URIS):
        return None, "config-sources.json must list exactly %s" % ", ".join(sorted(CONFIG_URIS))
    out = {}
    for name, entry in files.items():
        with open(os.path.join(root, entry["path"]), "rb") as handle:
            actual = hashlib.sha256(handle.read()).hexdigest()
        if actual != entry["sha256"]:
            return None, "%s (%s) has sha256 %s but config-sources.json records %s" % (name, entry["path"], actual, entry["sha256"])
        out[name] = (entry["path"], actual)
    return out, None


def other_source_records(root):
    """Non-blank lines of the three committed one-file samples (each line is one record for SampleBound.scanLines)."""
    base = root if os.path.isdir(os.path.join(root, "datasets", "samples")) else REPO
    total = 0
    for relative in OTHER_SAMPLES:
        with open(os.path.join(base, "datasets", "samples", relative), "rb") as handle:
            total += sum(1 for line in handle.read().split(b"\n") if line.strip())
    return total


def l_slice(root):
    """(publicationCount, output sha256) of the dataset-engineer's L slice manifest, or None while it does not exist."""
    path = os.path.join(root, L_SLICE_MANIFEST)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)
    return document["selection"]["publicationCount"], document["output"]["sha256"]


def check_15a(root, final, lines):
    """Returns (failed, blocked) booleans; appends human readable lines."""
    failed = blocked = False
    conf = read_conf(os.path.join(root, "scripts", "config", "release.conf"))
    pricing = read_conf(os.path.join(root, conf["PIPELINE_PRICING_FILE"]))
    manifests_dir = os.path.join(root, "experiments", "manifests")
    names = sorted(n for n in os.listdir(manifests_dir) if re.match(r"^15a-.*\.json$", n))
    if S_MANIFEST not in names:
        lines.append("CHECK-FAILED: the session-2 EMR run needs %s (size S)" % S_MANIFEST)
        return True, blocked
    for name in [n for n in names if n not in EMR_LEDGER]:
        failed = True
        lines.append("CHECK-FAILED: %s is not in the EMR run set (Session 1 history size-25/size-50, size S); size L is local evidence only (%s), never an EMR manifest (user 2026-11-16, P25 rule)" % (name, L_EVIDENCE))
    names = [n for n in names if n in EMR_LEDGER]
    try:
        configs, problem = config_files(root)
    except (OSError, ValueError, KeyError) as error:
        configs, problem = None, "config-sources.json or a file it names is unreadable (%s)" % error
    if problem:
        lines.append("CHECK-FAILED: %s" % problem)
        return True, blocked
    prep_path = os.path.join(root, configs["hadoop-config"][0])
    try:
        with open(prep_path, encoding="utf-8") as handle:
            prep = json.load(handle)
    except (OSError, ValueError):
        lines.append("CHECK-FAILED: the hadoop prep config %s is missing or not JSON" % configs["hadoop-config"][0])
        return True, blocked
    for field, key in CEILING_KEYS:
        if prep.get(field) is None or prep[field] > int(conf[key]):
            blocked = True
            lines.append("CHECK-BLOCKED: prep config %s=%s exceeds %s=%s in scripts/config/release.conf (infra-engineer owns the pin)" % (field, prep.get(field), key, conf[key]))
    others = other_source_records(root)
    facts = l_slice(root)
    l_records = facts[0] if facts else L_PLANNING_MAX
    basis = "the L slice manifest publicationCount" if facts else "the L planning bound (dataset-engineer TARGET_MAX)"
    need = l_records + others
    if prep.get("maxLocalSampleRecords", 0) < need:
        failed = True
        lines.append("CHECK-FAILED: prep config maxLocalSampleRecords=%s < %d = %s %d + %d other-source records (records past the bound are rejected)" % (prep.get("maxLocalSampleRecords"), need, basis, l_records, others))
    else:
        lines.append("CHECK-OK: prep config maxLocalSampleRecords=%s >= %d = %s %d + %d other-source records" % (prep["maxLocalSampleRecords"], need, basis, l_records, others))
    total, ledger_runs, history, s_facts = D(0), 0, D(0), None
    for name in names:
        role, charged, approved_minutes = EMR_LEDGER[name]
        path = os.path.join(manifests_dir, name)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        manifest = json.loads(text)
        for row in policy_problems(text):
            failed = True
            lines.append("CHECK-FAILED: %s: %s" % (name, row))
        scratch = tempfile.mkdtemp(prefix="check-manifest-")
        try:
            validated = os.path.join(scratch, name)
            with open(validated, "w", encoding="utf-8") as handle:
                handle.write(substitute(text))
            done = _validate(root, validated, conf)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        if done.returncode != 0:
            failed = True
            lines.extend("CHECK-FAILED: %s: %s" % (name, row) for row in done.stdout.splitlines())
            continue
        lines.append("CHECK-OK: %s passes scripts/lib/experiment.py validate" % name)
        estimate = g6_estimate(manifest, pricing)
        total += estimate * charged
        ledger_runs += charged
        if name == S_MANIFEST:
            s_facts = (estimate, g6_hourly(manifest, pricing), manifest["teardown"]["max_idle_timeout_seconds"])
        else:
            history += estimate * charged
        if estimate > D(str(manifest["budget"]["max_usd"])):
            failed = True
            lines.append("CHECK-FAILED: %s: G6 estimate %s exceeds budget.max_usd %s" % (name, estimate, manifest["budget"]["max_usd"]))
        else:
            lines.append("CHECK-OK: %s (%s) G6 estimate %s USD <= budget %s USD, charged %d x to the ledger" % (name, role, estimate, manifest["budget"]["max_usd"], charged))
        runtime = manifest["budget"]["max_runtime_minutes"]
        if runtime != approved_minutes:
            failed = True
            lines.append("CHECK-FAILED: %s: max_runtime_minutes is %s but the approved cap for %s is %d minutes" % (name, runtime, role, approved_minutes))
        if name != S_MANIFEST:
            if final:
                for row in placeholder_problems(text):
                    failed = True
                    lines.append("CHECK-FAILED: %s: %s" % (name, row))
            continue  # Session 1 history: kept as committed, not rerun; only its validity and ledger charge are checked
        pipeline = manifest["pipeline"]
        types = (pipeline.get("primary_instance_type", pipeline["instance_type"]), pipeline["instance_type"])
        if types != S_INSTANCE_TYPES:
            failed = True
            lines.append("CHECK-FAILED: %s: primary/core types are %s/%s; D3 approved %s primary and %s core" % ((name,) + types + S_INSTANCE_TYPES))
        else:
            lines.append("CHECK-OK: %s: %s primary, %s core, %d minutes" % (name, types[0], types[1], runtime))
        shas = pipeline["artifact_sha256"]
        for config_name, field in CONFIG_URIS.items():
            want = "s3://%s/emr/%s/%s" % (TOKENS[0], TOKENS[1], CONFIG_KEYS[config_name])
            if pipeline[field] != want:
                failed = True
                lines.append("CHECK-FAILED: %s: pipeline.%s must be %s (the key the upload script writes)" % (name, field, want))
            pinned = shas.get(config_name)
            if pinned != configs[config_name][1] and not (pinned == "0" * 64 and not final):
                failed = True
                lines.append("CHECK-FAILED: %s: artifact_sha256.%s=%s is not the sha256 of %s (%s); re-render" % (name, config_name, pinned, configs[config_name][0], configs[config_name][1]))
        if all(shas.get(n) == configs[n][1] for n in CONFIG_URIS):
            lines.append("CHECK-OK: %s pins the sha256 of the four repository config files (hadoop-config %s..., spark-config-template %s...)" % (
                name, configs["hadoop-config"][1][:12], configs["spark-config-template"][1][:12]))
        datasets_path = os.path.join(root, pipeline["datasets_manifest"])
        try:
            with open(datasets_path, encoding="utf-8") as handle:
                datasets = json.load(handle)
        except (OSError, ValueError):
            failed = True
            lines.append("CHECK-FAILED: %s: the datasets_manifest file is missing or not JSON" % name)
            continue
        if sorted(datasets) != sorted(SOURCES) or any(sorted(v) != ["retrieval", "snapshot"] for v in datasets.values()):
            failed = True
            lines.append("CHECK-FAILED: %s: datasets manifest must name exactly %s with snapshot and retrieval" % (name, ", ".join(SOURCES)))
        if final:
            for row in placeholder_problems(text):
                failed = True
                lines.append("CHECK-FAILED: %s: %s" % (name, row))
    failed = check_session2_evidence(root, lines) or failed
    cap, runs = D(conf["EMR_CUMULATIVE_CAP_USD"]), int(conf["EMR_MAX_LIVE_RUNS"])
    reserves, all_runs = total + SESSION2_ATTEMPT_USD, ledger_runs + 1
    parts = "Session 1 history %s + Session 2 S attempt as recorded %s + S + one S retry" % (history, SESSION2_ATTEMPT_USD)
    if reserves > cap or all_runs > runs:
        blocked = True
        lines.append("CHECK-BLOCKED: 15A ledger reserves %s USD over %d runs (%s) exceed the cumulative cap %s USD / %d runs pinned in scripts/config/release.conf (the human decides, infra-engineer pins EMR_MAX_LIVE_RUNS and EMR_CUMULATIVE_CAP_USD)" % (reserves, all_runs, parts, cap, runs))
    else:
        lines.append("CHECK-OK: 15A ledger reserves %s USD over %d runs (%s) <= cumulative cap %s USD / %d runs (margin %s USD against the reserves, %d spare runs)" % (reserves, all_runs, parts, cap, runs, cap - reserves, runs - all_runs))
    # The stricter rule scripts/lib/budget.py applies at admission: recorded measured actuals (history + the Session 2 attempt at its actual),
    # plus the provisional idle tail of a cluster that is still up, plus the new run's estimate. The retry (run 5) is admitted iff run 4's recorded
    # cost (measured + tail) leaves room; run 4 at its full estimate is the worst case the gate can model.
    recorded = history + SESSION2_ATTEMPT_USD
    if s_facts is None:  # the size S manifest failed validation above; the reserves line and CHECK-FAILED already say so
        failed = check_l_evidence(root, facts, lines) or failed
        return failed, blocked
    s_estimate, s_hourly, idle_seconds = s_facts
    tail = (s_hourly * D(idle_seconds) / D(3600)).quantize(CENT, rounding=decimal.ROUND_UP)  # the provisional tail of a cluster still up
    bound = cap - recorded - tail - s_estimate
    strict_margin = bound - s_estimate
    detail = ("recorded %s USD (Session 1 history %s + Session 2 attempt %s); run 4 admitted if %s + %s <= %s; run 5 admitted iff run 4's measured cost is at most "
              "%s - %s - %s - %s = %s; run 4 measuring its full estimate %s leaves a margin of %s USD" % (
                  recorded, history, SESSION2_ATTEMPT_USD, recorded, s_estimate, cap, cap, recorded, tail, s_estimate, bound, s_estimate, strict_margin))
    if strict_margin < 0:
        blocked = True
        lines.append("CHECK-BLOCKED: 15A real admission (scripts/lib/budget.py ledger_problems, idle tail %s USD) can refuse the retry even when run 4 measures only its estimate: %s" % (tail, detail))
    else:
        lines.append("CHECK-OK: 15A real admission (scripts/lib/budget.py ledger_problems, idle tail %s USD; stricter than the reserves figure above): %s" % (tail, detail))
    failed = check_l_evidence(root, facts, lines) or failed
    return failed, blocked


def check_session2_evidence(root, lines):
    """The Session 2 S attempt (USD 0.37, 1 run) is modelled from committed evidence, not from memory: the file must still say so."""
    try:
        with open(os.path.join(root, SESSION2_EVIDENCE), encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        lines.append("CHECK-FAILED: %s is missing; the ledger model needs the recorded Session 2 S attempt (USD %s)" % (SESSION2_EVIDENCE, SESSION2_ATTEMPT_USD))
        return True
    missing = [row for row in SESSION2_EVIDENCE_LINES if row not in text]
    if missing:
        lines.append("CHECK-FAILED: %s no longer states %s; update the Session 2 ledger model" % (SESSION2_EVIDENCE, " and ".join(missing)))
        return True
    lines.append("CHECK-OK: Session 2 S attempt recorded at USD %s (1 run) per %s" % (SESSION2_ATTEMPT_USD, SESSION2_EVIDENCE))
    return False


def check_l_evidence(root, facts, lines):
    """Size L is local evidence only: the record must exist, say so, and (once the L slice manifest exists) state its count and sha256."""
    try:
        with open(os.path.join(root, L_EVIDENCE), encoding="utf-8") as handle:
            evidence = json.load(handle)
    except (OSError, ValueError):
        lines.append("CHECK-FAILED: %s is missing or not JSON" % L_EVIDENCE)
        return True
    if evidence.get("schema") != "scholarchain.experiment-local-evidence.v1" or not str(evidence.get("emr", "")).startswith("NOT an EMR run"):
        lines.append("CHECK-FAILED: %s must be scholarchain.experiment-local-evidence.v1 and state that L is NOT an EMR run" % L_EVIDENCE)
        return True
    if facts and (evidence["slice"]["publicationCount"], evidence["slice"]["sha256"]) != facts:
        lines.append("CHECK-FAILED: %s states %s publications / sha256 %s, the L slice manifest %s / %s" % (
            L_EVIDENCE, evidence["slice"]["publicationCount"], evidence["slice"]["sha256"], facts[0], facts[1]))
        return True
    lines.append("CHECK-OK: size L is local evidence only (%s; %s publications, not an EMR run)" % (L_EVIDENCE, evidence["slice"]["publicationCount"]))
    return False


def check_15b_16b(root, final, lines):
    failed = False
    loadgen = load_module("loadgen_for_check", os.path.join(root, "load-tests", "loadgen.py"))
    profile = loadgen.load_profile(os.path.join(root, "load-tests", "config", "load-profile.v1.json"))
    cost = loadgen.cost_per_answer(profile)
    cap = D(profile["llm"]["shared_cap_usd"])
    base = os.path.join(root, "experiments", "manifests")
    with open(os.path.join(base, "15b-ecs-scaling.json"), encoding="utf-8") as handle:
        m15b = json.load(handle)
    problems = loadgen.manifest_problems(m15b)
    if problems:
        failed = True
        lines.extend("CHECK-FAILED: 15b-ecs-scaling.json: %s" % row for row in problems)
    else:
        lines.append("CHECK-OK: 15b-ecs-scaling.json passes the load-tests manifest schema")
        levels = [p["level"] for p in m15b["phases"] if p["type"] == "load"]
        if not {1, 5, 25, 50} <= set(levels):
            failed = True
            lines.append("CHECK-FAILED: 15b-ecs-scaling.json must cover concurrency 1, 5, 25 and 50")

        class Args:
            llm_answers = None
            levels = ""
            duration_seconds = None
            max_requests = None
            pause_seconds = 0

        phases = loadgen.build_phases(Args, profile, m15b)
        try:
            loadgen.check_phase_limits(phases, profile)
            lines.append("CHECK-OK: 15b phases within the profile limits (%d s total)" % sum(p["duration_seconds"] for p in phases))
        except loadgen.Refused as error:
            failed = True
            lines.append("CHECK-FAILED: 15b-ecs-scaling.json: %s" % error)
        answers_15b = sum(p["llm_answers"] for p in phases if p["type"] == "load")
        if any(p["llm_answers"] for p in phases if p["name"].startswith("hold")):
            failed = True
            lines.append("CHECK-FAILED: the hold phase must send no LLM answers")
    with open(os.path.join(base, "llm-allocation.json"), encoding="utf-8") as handle:
        allocation = json.load(handle)
    with open(os.path.join(base, "16b-live-evaluation.json"), encoding="utf-8") as handle:
        m16b = json.load(handle)
    if allocation.get("schema") != "scholarchain.llm-allocation.v2":
        failed = True
        lines.append("CHECK-FAILED: llm-allocation.json must have schema scholarchain.llm-allocation.v2")
    by_owner = {name: entry["answers"] for name, entry in allocation["buckets"].items()}
    if set(by_owner) != {"14c", "15b", "16b", "17"}:
        failed = True
        lines.append("CHECK-FAILED: llm-allocation.json buckets must be exactly 14c, 15b, 16b, 17 (found %s)" % sorted(by_owner))
    if D(allocation["shared_cap_usd"]) != cap:
        failed = True
        lines.append("CHECK-FAILED: llm-allocation.json shared_cap_usd differs from the pinned profile cap %s" % cap)
    planned = cost * sum(by_owner.values())
    if planned > cap:
        failed = True
        lines.append("CHECK-FAILED: allocated %d answers x %s = %s USD exceeds the shared cap %s USD" % (sum(by_owner.values()), cost, planned, cap))
    else:
        lines.append("CHECK-OK: buckets %s = %d answers x %s = %s USD <= shared cap %s USD (reserve %s USD)" % (
            "/".join("%s %d" % (k, v) for k, v in by_owner.items()), sum(by_owner.values()), cost, planned, cap, cap - planned))
    unit_text = loadgen.money(cost).rstrip("0")
    for name, text in (("llm-allocation.json", allocation.get("note", "")), ("15b-ecs-scaling.json", json.dumps(m15b.get("llm", {})))):
        if unit_text not in text:
            failed = True
            lines.append("CHECK-FAILED: %s does not state the pinned cost per answer %s USD (update the estimate text when the profile changes)" % (name, unit_text))
    lines.append("CHECK-OK: per-bucket estimates (USD) %s, total %s of the shared cap %s" % (
        ", ".join("%s %s" % (k, loadgen.money(cost * v)) for k, v in by_owner.items()), loadgen.money(planned), cap))
    pricing = profile["llm"]["pricing"]
    if profile["llm"].get("provider") != "anthropic" or not pricing["model_route"].startswith("claude-haiku-5-5") or "bedrock" not in pricing.get("fallback_model_route", "").lower():
        failed = True
        lines.append("CHECK-FAILED: the profile must price claude-haiku-5-5 on the Anthropic API and name the Bedrock fallback route")
    emb = profile.get("embeddings", {})
    expected = (emb.get("provider"), emb.get("model"), emb.get("output_dimension"), emb.get("usd_per_million_tokens"), emb.get("free_tokens"), emb.get("cap_usd"))
    if expected != ("voyage", "voyage-4-lite", 256, "0.02", 200000000, "0.30"):
        failed = True
        lines.append("CHECK-FAILED: the profile embeddings block must be voyage / voyage-4-lite / 256 / 0.02 USD per 1M / 200000000 free tokens / cap 0.30 (found %s)" % (expected,))
    else:
        lines.append("CHECK-OK: embeddings voyage-4-lite 256 dims USD 0.02 per 1M tokens, first 200M tokens free, cap USD 0.30 with a token counter")
    m16b_emb = m16b.get("llm", {}).get("embeddings", {})
    if (m16b_emb.get("model"), m16b_emb.get("cap_usd")) != (emb.get("model"), emb.get("cap_usd")):
        failed = True
        lines.append("CHECK-FAILED: 16b-live-evaluation.json embeddings model and cap must match the profile")
    if not problems and by_owner.get("15b") != answers_15b:
        failed = True
        lines.append("CHECK-FAILED: 15b manifest answers (%s) differ from the 15b bucket (%s)" % (answers_15b, by_owner.get("15b")))
    if m16b.get("schema") != "scholarchain.llm-evaluation-placeholder.v1" or m16b.get("llm", {}).get("answers") != by_owner.get("16b"):
        failed = True
        lines.append("CHECK-FAILED: 16b-live-evaluation.json is not a valid placeholder or its answers differ from the 16b bucket")
    else:
        lines.append("CHECK-OK: 16b-live-evaluation.json placeholder matches the 16b bucket (%d answers)" % m16b["llm"]["answers"])
    profile_sum = sum(v["llm_answers"] for v in profile["per_level"].values())
    if by_owner.get("15b") != profile_sum:
        failed = True
        lines.append("CHECK-FAILED: the profile per-level answers sum to %d, the 15b bucket is %s" % (profile_sum, by_owner.get("15b")))
    return check_semantic(root, final, lines, loadgen, profile) or failed


SEMANTIC_MANIFEST = "15b-ecs-scaling-semantic.json"
SEMANTIC_PHASE_CAPS = (("baseline-1", 1, 600), ("level-5", 5, 3000), ("level-25", 25, 15000), ("level-50", 50, 30000), ("hold-50", 50, 150000))
SEMANTIC_QUIET_MINUTES = 25


def check_semantic(root, final, lines, loadgen, profile):
    """P42: the semantic 15B manifest against load-tests/loadgen.py: the REQUIRED per-level limits 600 / 3,000 / 15,000 / 30,000 / 150,000 (198,600 in
    total), a warm-up of at most 200 requests, at least 25 quiet minutes, the fixed questions file and its provenance, and the semantic route weight."""
    failed = False

    def fail(message):
        nonlocal failed
        failed = True
        lines.append("CHECK-FAILED: %s: %s" % (SEMANTIC_MANIFEST, message))

    path = os.path.join(root, "experiments", "manifests", SEMANTIC_MANIFEST)
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        manifest = json.loads(text)
    except (OSError, ValueError):
        fail("is missing or not valid JSON")
        return failed
    for row in policy_problems(text):
        fail(row)
    problems = loadgen.manifest_problems(manifest)
    for row in problems:
        fail(row)
    if problems:
        return failed
    block = manifest["semantic"]

    class Args:
        llm_answers = None
        levels = ""
        duration_seconds = None
        max_requests = None
        pause_seconds = 0

    try:
        phases = loadgen.build_phases(Args, profile, manifest)
        loadgen.check_phase_limits(phases, profile, block)
    except loadgen.Refused as error:
        fail(str(error))
        return failed
    load = {p["name"]: p for p in manifest["phases"] if p["type"] == "load"}
    for name, level, cap in SEMANTIC_PHASE_CAPS:
        phase = load.get(name)
        if phase is None or phase["level"] != level or phase["max_requests"] != cap:
            fail("phase %s must run at level %d with max_requests exactly %d (the required per-level limit; it must not be raised)" % (name, level, cap))
    total = sum(p["max_requests"] for p in load.values())
    if set(load) != {name for name, _, _ in SEMANTIC_PHASE_CAPS} or total != loadgen.SEMANTIC_RAMP_TOTAL:
        fail("the load phases must be exactly baseline-1, level-5, level-25, level-50 and hold-50 with %d requests in total (found %d)" % (loadgen.SEMANTIC_RAMP_TOTAL, total))
    warmup = [p for p in manifest["phases"] if p["type"] == "warmup"]
    if len(warmup) != 1 or manifest["phases"][0] is not warmup[0] or warmup[0]["level"] != 1 or not block["questions_count"] <= warmup[0]["max_requests"] <= loadgen.SEMANTIC_WARMUP_MAX:
        fail("one warmup phase at level 1 must come first, with max_requests from the question count to %d" % loadgen.SEMANTIC_WARMUP_MAX)
    tail = 0
    for phase in reversed(manifest["phases"]):
        if phase["type"] != "observe":
            break
        tail += phase["duration_seconds"]
    if tail < SEMANTIC_QUIET_MINUTES * 60:
        fail("the quiet window after the last load phase is %.0f s, under %d minutes" % (tail, SEMANTIC_QUIET_MINUTES))
    if manifest["llm"].get("default_enabled") is not False or any(p.get("llm_answers") for p in manifest["phases"]):
        fail("a semantic manifest sends no LLM answers")
    semantic_route = profile["routes"].get("semantic", {})
    others = sum(r["weight"] for name, r in profile["routes"].items() if name != "semantic" and not r["llm"])
    if (semantic_route.get("method"), semantic_route.get("path"), semantic_route.get("auth"), semantic_route.get("llm")) != ("POST", "/v1/semantic/retrieve", True, False) \
            or semantic_route.get("weight", 0) <= others:
        fail("the profile must have the semantic route (POST /v1/semantic/retrieve, API key) with a weight above all other routes together (%d)" % others)
    # the fixed questions file and its provenance
    questions_path = os.path.join(root, block["questions_file"])
    provenance_path = os.path.join(root, block["provenance"])
    try:
        questions = loadgen.read_lines(questions_path, "semantic questions", limit=loadgen.SEMANTIC_QUESTIONS_MAX, maxlen=loadgen.SEMANTIC_QUESTION_MAXLEN)
        with open(questions_path, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        with open(provenance_path, encoding="utf-8") as handle:
            provenance = json.load(handle)
    except (loadgen.Refused, OSError, ValueError) as error:
        fail("the questions file or its provenance cannot be read: %s" % error)
        return failed
    if digest != block["questions_sha256"] or len(questions) != block["questions_count"]:
        fail("the questions file (%d lines, sha256 %s) differs from the manifest pin (%d, %s)" % (len(questions), digest, block["questions_count"], block["questions_sha256"]))
    if len({q.casefold() for q in questions}) != len(questions):
        fail("the questions are not all distinct")
    recorded = provenance.get("outputs", {}).get("semantic-questions.txt", {})
    if recorded.get("sha256") != digest or [x.get("phrase") for x in provenance.get("phrases", [])] != questions:
        fail("the provenance record does not match the questions file")
    slice_manifest = os.path.join(root, "datasets", "phase6", "dblp-slice-manifest.v1.json")
    if os.path.isfile(slice_manifest):
        with open(slice_manifest, encoding="utf-8") as handle:
            if provenance.get("source", {}).get("sha256") != json.load(handle)["output"]["sha256"]:
                fail("the provenance source sha256 differs from the Phase 6 slice manifest")
    if not failed:
        lines.append("CHECK-OK: %s: per-level limits 600 / 3,000 / 15,000 / 30,000 / 150,000 = %d requests, warm-up %d <= %d at level 1, quiet window %.0f min, %d fixed questions (sha256 pinned, provenance matches)" % (
            SEMANTIC_MANIFEST, total, warmup[0]["max_requests"], loadgen.SEMANTIC_WARMUP_MAX, tail / 60, len(questions)))
    return failed


EVAL16_MANIFEST = "16-evaluation.json"
EVAL16_SCOPE = {"offline": True, "network_calls": 0, "aws_calls": 0, "model_calls": 0, "spend_usd": "0.00"}


def check_16_evaluation(root, lines):
    """Phase 16 evaluation manifest (instance A: groups 1, 2, 4). Returns True when a check failed."""
    path = os.path.join(root, "experiments", "manifests", EVAL16_MANIFEST)
    if not os.path.isfile(path):
        lines.append("CHECK-SKIP: %s is not present" % EVAL16_MANIFEST)
        return False
    failed = False

    def fail(message):
        nonlocal failed
        failed = True
        lines.append("CHECK-FAILED: %s: %s" % (EVAL16_MANIFEST, message))
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    try:
        manifest = json.loads(text)
    except ValueError as error:
        fail("not valid JSON: %s" % error)
        return True
    for row in policy_problems(text):
        fail(row)
    if manifest.get("schema") != "scholarchain.eval16-manifest.v1" or manifest.get("id") != "16-evaluation":
        fail("schema must be scholarchain.eval16-manifest.v1 and id 16-evaluation")
    if manifest.get("scope") is None or any(manifest["scope"].get(k) != v for k, v in EVAL16_SCOPE.items()):
        fail("scope must state offline true, network_calls 0, aws_calls 0, model_calls 0 and spend_usd \"0.00\"")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(manifest.get("run_date", ""))):
        fail("run_date must be YYYY-MM-DD")
    verify = os.path.isdir(os.path.join(root, "experiments", "results", "phase16"))
    checked = skipped = 0
    for section in ("inputs", "scripts", "outputs"):
        entries = manifest.get(section)
        if not isinstance(entries, list) or not entries:
            fail("%s must be a non-empty list" % section)
            continue
        for item in entries:
            rel = item.get("path", "") if isinstance(item, dict) else ""
            if not rel or os.path.isabs(rel) or ".." in rel.split("/"):
                fail("%s entry has a missing, absolute or parent-relative path: %r" % (section, rel))
                continue
            digest = item.get("sha256")
            if digest is None:
                # only an untracked directory-level input may carry a listing hash instead of a sha256; every other entry without a sha256 fails
                if not (section == "inputs" and item.get("tracked") is False and HEX64.fullmatch(str(item.get("files_listing_sha256", "")))):
                    fail("%s entry %s has no sha256 (and is not an untracked directory entry with files_listing_sha256)" % (section, rel))
                continue
            if not HEX64.fullmatch(str(digest)):
                fail("%s entry %s has no valid sha256" % (section, rel))
                continue
            untracked = item.get("tracked") is False
            full = os.path.join(root, *rel.split("/"))
            if not verify or (untracked and not os.path.isfile(full)):
                skipped += 1
                continue
            if not os.path.isfile(full):
                fail("%s entry %s does not exist" % (section, rel))
                continue
            with open(full, "rb") as handle:
                actual = hashlib.sha256(handle.read()).hexdigest()
            checked += 1
            if actual != digest:
                fail("%s entry %s differs from the recorded sha256 (recorded %s, found %s)" % (section, rel, digest[:12], actual[:12]))
    if verify:
        listed = {i.get("path") for i in (manifest.get("outputs") or []) if isinstance(i, dict)}
        excluded = manifest.get("excluded_outputs") or {}
        results = os.path.join(root, "experiments", "results", "phase16")
        for base, _, names in os.walk(results):
            for name in sorted(names):
                rel = os.path.relpath(os.path.join(base, name), root).replace(os.sep, "/")
                if rel not in listed and rel not in excluded:
                    fail("outputs: %s exists under experiments/results/phase16 but is neither listed nor declared in excluded_outputs" % rel)
    if not failed:
        lines.append("CHECK-OK: %s: offline scope (spend 0.00), policy clean, %d file hashes verified, %d not verifiable here (%s)" % (
            EVAL16_MANIFEST, checked, skipped, "untracked target/ inputs or no results tree in this root"))
    return failed


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--final", action="store_true", help="also refuse placeholders (the state required before the commit freeze)")
    parser.add_argument("--root", default=REPO, help="repository root (tests use a fixture copy)")
    args = parser.parse_args(argv)
    lines = []
    failed_a, blocked = check_15a(args.root, args.final, lines)
    failed_b = check_15b_16b(args.root, args.final, lines)
    failed_b = check_16_evaluation(args.root, lines) or failed_b
    for line in lines:
        print(line)
    if failed_a or failed_b:
        print("RESULT: FAILED")
        return 1
    if blocked:
        print("RESULT: BLOCKED-ON infra-engineer (raise the pinned ceiling; see CHECK-BLOCKED lines)")
        return 3
    print("RESULT: OK%s" % (" (final: no placeholders)" if args.final else " (placeholders allowed; run with --final before the commit freeze)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
