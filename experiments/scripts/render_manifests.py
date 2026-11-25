#!/usr/bin/env python3
"""Render the runnable Experiment 15A manifest (stdlib; python3 -I): experiments/manifests/15a-emr-size-100.json, size S.

Session 2 (user decisions 2026-11-16, docs/agent-runs/phase-15/prompt.md "L, second size" and "S run cap and D3 go-ahead"):
  * S is the only EMR run (run plus at most one retry): 120 minutes (raised from 75 by the human on 2026-11-24,
    docs/agent-runs/phase-18/human-gate.md), r5.xlarge primary (pipeline.primary_instance_type) and one
    m5.xlarge core node (pipeline.instance_type), 900 s idle auto-termination, budget 1.25 USD
    (G6 estimate = (0.315 + 0.240) x (7200 + 900) / 3600 = 1.24875, rounded up to the cent);
  * L does NOT run on EMR (P25 rule): no manifest is rendered for it; its local evidence is experiments/inputs/15a/size-l-local-evidence.json;
  * 15a-emr-size-25.json and 15a-emr-size-50.json are Session 1's historical m5.xlarge runs (ledger history): this script never writes them.

Committed manifests carry TOKENS, never bucket names (bucket names embed the AWS account id): ${SCHOLARCHAIN_ARTIFACTS_BUCKET}
and ${SCHOLARCHAIN_RUN_PREFIX} (the operator_run_prefix, ^run-[a-z0-9][a-z0-9-]{1,27}$). scripts/run-experiment.sh
resolves them at run time from the environment.

sha256 values:
  * the four configuration files (hadoop-config, er-policy, er-config, spark-config-template) are repository files listed in
    experiments/inputs/15a/config-sources.json; the renderer hashes them itself, refuses a file that drifted from that list and refuses
    a --sha for them that differs from the file;
  * the four JARs are all-zero until the human passes --sha (or --keep-jar-shas, which copies them from the existing
    15a-emr-size-100.json in --out-dir), reviews the diff and commits BEFORE the freeze:

  python3 -I experiments/scripts/render_manifests.py --overwrite \\
      --sha hadoop-submit-jar=H --sha hadoop-libjars=H --sha er-jar=H --sha job-jar=H
  python3 -I experiments/scripts/check_manifests.py --final

Existing files are refused unless --overwrite. No network, no AWS.

S3 contract (reconciled with the deployer grant): everything for 15A is in the ARTIFACTS bucket under emr/<run_prefix>/:
  jars/ (hadoop-submit.jar, hadoop-bundle.jar, entity-resolution.jar, spark-job.jar), config/ (hadoop-config.json, er-policy.json,
  er-config.json, spark-config-template.json), input/size-100/datasets/samples/{dblp,openalex,crossref,orcid}/...; outputs go to
  s3://<artifacts>/pipeline/<run_prefix>/15a/size-100; metric exports under s3://<artifacts>/pipeline/<run_prefix>/15a/size-100/metrics/.
  The job JAR (spark-job.jar) is a node-local path in the pipeline: only its sha256 is in the manifest.
  config/hadoop-config.json is the key the infra-engineer's upload option (--hadoop-config FILE, P1) writes.
"""
import argparse
import hashlib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTIFACTS = "${SCHOLARCHAIN_ARTIFACTS_BUCKET}"
RUN = "${SCHOLARCHAIN_RUN_PREFIX}"
PLACEHOLDER_SHA = "0" * 64
HEX64 = re.compile(r"^[0-9a-f]{64}$")
JAR_SHA_NAMES = ("hadoop-submit-jar", "hadoop-libjars", "er-jar", "job-jar")
CONFIG_SHA_NAMES = ("hadoop-config", "er-policy", "er-config", "spark-config-template")
SHA_NAMES = JAR_SHA_NAMES + CONFIG_SHA_NAMES
CONFIG_SOURCES = os.path.join("experiments", "inputs", "15a", "config-sources.json")
S_LABEL = "size-100"
LABELS = (S_LABEL,)  # the runnable EMR set; size-25 and size-50 are Session 1 history, L is local evidence only
PRIMARY_INSTANCE_TYPE, CORE_INSTANCE_TYPE = "r5.xlarge", "m5.xlarge"  # D3 (user, 2026-11-16)
MAX_RUNTIME_MINUTES = 120  # S run cap (user, 2026-11-24, docs/agent-runs/phase-18/human-gate.md; was 75 from 2026-11-16)
MAX_USD = 1.25  # G6 estimate for 120 min: 0.555 x (7200 + 900) / 3600 = 1.24875, rounded up
ARTIFACT_KEYS = {
    "hadoop_submit_jar": "jars/hadoop-submit.jar",
    "hadoop_libjars": "jars/hadoop-bundle.jar",
    "hadoop_config": "config/hadoop-config.json",
    "er_jar": "jars/entity-resolution.jar",
    "er_policy": "config/er-policy.json",
    "er_config": "config/er-config.json",
    "spark_config_template": "config/spark-config-template.json",
}
DESCRIPTION_S = (
    "Experiment 15A, size S (10,577 works, 100 percent of the Phase 6 DBLP slice dblp-2026-10-03; see experiments/README.md): Hadoop prep, "
    "entity resolution and Spark on EMR. One r5.xlarge primary (entity resolution runs there, 12g heap) and one m5.xlarge core node, "
    "120 minutes at most (raised from 75 by the human on 2026-11-24, docs/agent-runs/phase-18/human-gate.md), 900 s idle auto-termination, budget 1.25 USD (run and at most one retry). The other three sources are the "
    "committed Phase 4 samples, unscaled. Spark template: experiments/inputs/15a/spark-emr-template.json (64 shuffle partitions). "
    "Size L is not run on EMR (local evidence only)."
)


class Refused(Exception):
    pass


def sha256_file(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def config_shas(root=REPO):
    """sha256 of the four configuration files named in config-sources.json; refuses a file that drifted from its recorded value."""
    with open(os.path.join(root, CONFIG_SOURCES), encoding="utf-8") as handle:
        files = json.load(handle)["files"]
    if sorted(files) != sorted(CONFIG_SHA_NAMES):
        raise Refused("config-sources.json must list exactly %s" % ", ".join(sorted(CONFIG_SHA_NAMES)))
    out = {}
    for name in CONFIG_SHA_NAMES:
        actual = sha256_file(os.path.join(root, files[name]["path"]))
        if actual != files[name]["sha256"]:
            raise Refused("%s (%s) has sha256 %s but config-sources.json records %s" % (name, files[name]["path"], actual, files[name]["sha256"]))
        out[name] = actual
    return out


def manifest(label, shas, region):
    art = lambda name: "s3://%s/emr/%s/%s" % (ARTIFACTS, RUN, ARTIFACT_KEYS[name])
    return {
        "schema": "scholarchain.experiment-manifest.v1",
        "id": "15a-emr-%s" % label,
        "description": DESCRIPTION_S,
        "budget": {"max_usd": MAX_USD, "max_runtime_minutes": MAX_RUNTIME_MINUTES, "max_capacity": 2, "region": region},
        "teardown": {"mode": "auto-termination", "max_idle_timeout_seconds": 900},
        "pipeline": {
            "instance_type": CORE_INSTANCE_TYPE,
            "primary_instance_type": PRIMARY_INSTANCE_TYPE,
            "core_count": 1,
            "max_task_count": 0,
            "input_prefix": "s3://%s/emr/%s/input/%s" % (ARTIFACTS, RUN, label),
            "output_prefix": "s3://%s/pipeline/%s/15a/%s" % (ARTIFACTS, RUN, label),
            "hadoop_submit_jar": art("hadoop_submit_jar"),
            "hadoop_libjars": art("hadoop_libjars"),
            "hadoop_config": art("hadoop_config"),
            "er_jar": art("er_jar"),
            "er_policy": art("er_policy"),
            "er_config": art("er_config"),
            "spark_config_template": art("spark_config_template"),
            "datasets_manifest": "experiments/inputs/15a/datasets.json",
            "artifact_sha256": {name: shas.get(name, PLACEHOLDER_SHA) for name in SHA_NAMES},
        },
        "metrics": {"locations": ["s3://%s/pipeline/%s/15a/%s/metrics/" % (ARTIFACTS, RUN, label)]},
    }


def render(shas, region="us-east-2"):
    return {"15a-emr-%s.json" % label: manifest(label, shas, region) for label in LABELS}


def dump(document):
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", default=os.path.join(REPO, "experiments", "manifests"))
    parser.add_argument("--region", default="us-east-2")
    parser.add_argument("--sha", action="append", default=[], metavar="NAME=HEX", help="sha256 of an artifact (names: %s)" % ", ".join(SHA_NAMES))
    parser.add_argument("--keep-jar-shas", action="store_true", help="copy the four JAR sha256 values from the existing 15a-emr-size-100.json in --out-dir")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    out_dir = os.path.abspath(args.out_dir)
    try:
        configs = config_shas()
        shas = dict(configs)
        if args.keep_jar_shas:
            existing = os.path.join(out_dir, "15a-emr-%s.json" % S_LABEL)
            if not os.path.isfile(existing):
                raise Refused("--keep-jar-shas needs %s" % existing)
            with open(existing, encoding="utf-8") as handle:
                kept = json.load(handle)["pipeline"]["artifact_sha256"]
            for name in JAR_SHA_NAMES:
                if not HEX64.match(kept.get(name, "")):
                    raise Refused("--keep-jar-shas: %s has no valid %s" % (existing, name))
                shas[name] = kept[name]
        for item in args.sha:
            name, _, value = item.partition("=")
            if name not in SHA_NAMES or not HEX64.match(value):
                raise Refused("--sha needs NAME=<64 lowercase hex> with NAME one of %s" % ", ".join(SHA_NAMES))
            if name in configs and value != configs[name]:
                raise Refused("--sha %s=%s differs from the repository file listed in config-sources.json (%s); upload that file" % (name, value, configs[name]))
            shas[name] = value
    except (Refused, OSError, ValueError, KeyError) as error:
        print("RENDER-REFUSED: %s" % error)
        return 1
    files = render(shas, args.region)
    if not args.overwrite:
        for name in files:
            if os.path.lexists(os.path.join(out_dir, name)):
                print("RENDER-REFUSED: %s exists (use --overwrite to replace the uncommitted form)" % name)
                return 1
    os.makedirs(out_dir, exist_ok=True)
    for name, document in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
            handle.write(dump(document))
        print("RENDERED %s" % os.path.join(out_dir, name))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
