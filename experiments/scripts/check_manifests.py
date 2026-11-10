#!/usr/bin/env python3
"""Offline checks for the Phase 15 experiment manifests (stdlib; python3 -I). No AWS, no network, writes nothing in the repository.

  python3 -I experiments/scripts/check_manifests.py [--final]

Checks
  15A  experiments/manifests/15a-emr-size-*.json
       * policy: only the committed token ${SCHOLARCHAIN_ARTIFACTS_BUCKET} names a bucket (no literal bucket),
         and no run of 12 digits outside a sha256 (an AWS account id);
       * scripts/lib/experiment.py validate (the validator run-experiment.sh uses) on a temporary copy in which the tokens are replaced by
         syntactically valid dummy names, with the pinned caps read from scripts/config/release.conf;
       * the G6 estimate (instances x (EC2 + EMR rate) x (runtime + idle timeout)) from scripts/config/emr-pricing.conf is within
         budget.max_usd, and the three runs together are within EMR_CUMULATIVE_CAP_USD and EMR_MAX_LIVE_RUNS;
       * the prep config satisfies the pinned Phase 4 ceilings (a violation is CHECK-BLOCKED, exit 3: the pin is infra-engineer's);
       * the datasets manifest names exactly dblp, openalex, crossref, orcid with snapshot and retrieval.
  15B  experiments/manifests/15b-ecs-scaling.json against load-tests/loadgen.py (strict schema, phase limits, answer budget).
  16B  16b-live-evaluation.json and llm-allocation.json (v2, buckets 14c/15b/16b/17): allocated answers x the pinned cost per answer must fit in the shared Haiku cap,
       and the 15B and 16B figures must equal the allocation.
  --final  also refuses the all-zero sha256 placeholders: the state required before the commit freeze (tokens plus real hashes pass).

Exit: 0 all checks pass, 1 a check failed, 3 blocked by a pinned ceiling owned by another role.
"""
import argparse
import decimal
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


def g6_estimate(manifest, pricing):
    pipeline, budget = manifest["pipeline"], manifest["budget"]
    suffix = pipeline["instance_type"].upper().replace(".", "_")
    ec2 = D(pricing["EMR_RATE_EC2_" + suffix])
    emr = D(pricing["EMR_RATE_EMR_" + suffix])
    nodes = 1 + pipeline["core_count"] + pipeline.get("max_task_count", 0)
    seconds = budget["max_runtime_minutes"] * 60 + manifest["teardown"]["max_idle_timeout_seconds"]
    return ((ec2 + emr) * nodes * D(seconds) / D(3600)).quantize(CENT, rounding=decimal.ROUND_UP)


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
    """--final only: the all-zero sha256 placeholder must be replaced by the real artifact hash."""
    return ["an all-zero sha256 placeholder remains"] if re.search(r'"0{64}"', text) else []


def _validate(root, path, conf):
    return subprocess.run(
        [sys.executable, "-I", os.path.join(root, "scripts", "lib", "experiment.py"), "validate", "--manifest", path, "--max-run-usd", conf["EMR_MAX_RUN_USD"],
         "--max-runtime-cap", conf["PIPELINE_MAX_RUNTIME_MINUTES"], "--max-capacity-cap", conf["PIPELINE_MAX_CAPACITY"], "--max-idle-cap", conf["PIPELINE_MAX_IDLE_TIMEOUT_SECONDS"]],
        capture_output=True, text=True, timeout=60)


def check_15a(root, final, lines):
    """Returns (failed, blocked) booleans; appends human readable lines."""
    failed = blocked = False
    conf = read_conf(os.path.join(root, "scripts", "config", "release.conf"))
    pricing = read_conf(os.path.join(root, conf["PIPELINE_PRICING_FILE"]))
    manifests_dir = os.path.join(root, "experiments", "manifests")
    names = sorted(n for n in os.listdir(manifests_dir) if re.match(r"^15a-.*\.json$", n))
    if len(names) != 3:
        lines.append("CHECK-FAILED: expected three 15A manifests, found %d" % len(names))
        return True, blocked
    total = D(0)
    for name in names:
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
        total += estimate
        if estimate > D(str(manifest["budget"]["max_usd"])):
            failed = True
            lines.append("CHECK-FAILED: %s: G6 estimate %s exceeds budget.max_usd %s" % (name, estimate, manifest["budget"]["max_usd"]))
        else:
            lines.append("CHECK-OK: %s G6 estimate %s USD <= budget %s USD" % (name, estimate, manifest["budget"]["max_usd"]))
        if manifest["budget"]["max_runtime_minutes"] != 90:
            failed = True
            lines.append("CHECK-FAILED: %s: the approved cluster time per run is 90 minutes" % name)
        prep_path = os.path.join(root, manifest["pipeline"]["hadoop_config"])
        datasets_path = os.path.join(root, manifest["pipeline"]["datasets_manifest"])
        try:
            with open(prep_path, encoding="utf-8") as handle:
                prep = json.load(handle)
            with open(datasets_path, encoding="utf-8") as handle:
                datasets = json.load(handle)
        except (OSError, ValueError):
            failed = True
            lines.append("CHECK-FAILED: %s: the hadoop_config or datasets_manifest file is missing or not JSON" % name)
            continue
        if sorted(datasets) != sorted(SOURCES) or any(sorted(v) != ["retrieval", "snapshot"] for v in datasets.values()):
            failed = True
            lines.append("CHECK-FAILED: %s: datasets manifest must name exactly %s with snapshot and retrieval" % (name, ", ".join(SOURCES)))
        for field, key in CEILING_KEYS:
            if prep.get(field) is None or prep[field] > int(conf[key]):
                blocked = True
                lines.append("CHECK-BLOCKED: %s: prep config %s=%s exceeds %s=%s in scripts/config/release.conf (infra-engineer owns the pin)" % (name, field, prep.get(field), key, conf[key]))
        if final:
            for row in placeholder_problems(text):
                failed = True
                lines.append("CHECK-FAILED: %s: %s" % (name, row))
    cap, runs = D(conf["EMR_CUMULATIVE_CAP_USD"]), int(conf["EMR_MAX_LIVE_RUNS"])
    if total > cap or len(names) > runs:
        failed = True
        lines.append("CHECK-FAILED: 15A total %s USD over %d runs exceeds the cumulative cap %s USD / %d runs" % (total, len(names), cap, runs))
    else:
        lines.append("CHECK-OK: 15A total %s USD over %d runs <= cumulative cap %s USD / %d runs" % (total, len(names), cap, runs))
    return failed, blocked


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
    return failed


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--final", action="store_true", help="also refuse placeholders (the state required before the commit freeze)")
    parser.add_argument("--root", default=REPO, help="repository root (tests use a fixture copy)")
    args = parser.parse_args(argv)
    lines = []
    failed_a, blocked = check_15a(args.root, args.final, lines)
    failed_b = check_15b_16b(args.root, args.final, lines)
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
