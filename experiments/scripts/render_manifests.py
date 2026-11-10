#!/usr/bin/env python3
"""Render the three Experiment 15A manifests (stdlib; python3 -I). Single source of truth for experiments/manifests/15a-*.json.

Committed manifests carry TOKENS, never bucket names (bucket names embed the AWS account id): ${SCHOLARCHAIN_ARTIFACTS_BUCKET}
and ${SCHOLARCHAIN_RUN_PREFIX} (the operator_run_prefix, ^run-[a-z0-9][a-z0-9-]{1,27}$). scripts/run-experiment.sh
resolves them at run time from the environment. The only value that does not exist until the JARs are built is the sha256 of each
artifact, so the files hold all-zero hashes until the human renders the real ones, reviews the diff and commits BEFORE the freeze:

  python3 -I experiments/scripts/render_manifests.py --overwrite \\
      --sha hadoop-submit-jar=H --sha hadoop-libjars=H --sha er-jar=H --sha job-jar=H \\
      --sha er-policy=H --sha er-config=H --sha spark-config-template=H
  python3 -I experiments/scripts/check_manifests.py --final

Without --sha it writes the all-zero form. Existing files are refused unless --overwrite. No network, no AWS.

S3 contract (reconciled with the deployer grant): everything for 15A is in the ARTIFACTS bucket under emr/<run_prefix>/:
  jars/ (hadoop-submit.jar, hadoop-bundle.jar, entity-resolution.jar, spark-job.jar), config/ (er-policy.json, er-config.json,
  spark-config-template.json), input/size-{25,50,100}/datasets/samples/{dblp,openalex,crossref,orcid}/...; outputs go to
  s3://<artifacts>/pipeline/<run_prefix>/15a/size-N; metric exports under s3://<artifacts>/pipeline/<run_prefix>/15a/size-N/metrics/ (cluster logs stay at the cluster log_uri).
  The job JAR (spark-job.jar) is a node-local path in the pipeline: only its sha256 is in the manifest.

Fixed design: every run 1 primary + 1 core m5.xlarge (capacity 2), 90 minutes, 900 s idle auto-termination, budget 0.84 USD
(G6 estimate = 2 x (0.192 + 0.048) x (5400 + 900) / 3600), three runs = 2.52 USD against the 2.52 USD cumulative cap (EMR_CUMULATIVE_CAP_USD).
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTIFACTS = "${SCHOLARCHAIN_ARTIFACTS_BUCKET}"
RUN = "${SCHOLARCHAIN_RUN_PREFIX}"
PLACEHOLDER_SHA = "0" * 64
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SHA_NAMES = ("hadoop-submit-jar", "hadoop-libjars", "er-jar", "job-jar", "er-policy", "er-config", "spark-config-template")
SIZES = (25, 50, 100)
ARTIFACT_KEYS = {
    "hadoop_submit_jar": "jars/hadoop-submit.jar",
    "hadoop_libjars": "jars/hadoop-bundle.jar",
    "er_jar": "jars/entity-resolution.jar",
    "er_policy": "config/er-policy.json",
    "er_config": "config/er-config.json",
    "spark_config_template": "config/spark-config-template.json",
}
DESCRIPTION = (
    "Experiment 15A, run %d of 3: Hadoop prep, entity resolution and Spark on EMR over %d percent of the Phase 6 DBLP slice "
    "(first ceil(n_venue*P/100) records per venue of dblp-2026-10-03, nested sets; see experiments/README.md). One primary and one core "
    "m5.xlarge, 90 minutes at most, auto-termination. The other three sources are the committed Phase 4 samples, unscaled."
)


def manifest(size, run_number, shas, region):
    art = lambda name: "s3://%s/emr/%s/%s" % (ARTIFACTS, RUN, ARTIFACT_KEYS[name])
    return {
        "schema": "scholarchain.experiment-manifest.v1",
        "id": "15a-emr-size-%d" % size,
        "description": DESCRIPTION % (run_number, size),
        "budget": {"max_usd": 0.84, "max_runtime_minutes": 90, "max_capacity": 2, "region": region},
        "teardown": {"mode": "auto-termination", "max_idle_timeout_seconds": 900},
        "pipeline": {
            "instance_type": "m5.xlarge",
            "core_count": 1,
            "max_task_count": 0,
            "input_prefix": "s3://%s/emr/%s/input/size-%d" % (ARTIFACTS, RUN, size),
            "output_prefix": "s3://%s/pipeline/%s/15a/size-%d" % (ARTIFACTS, RUN, size),
            "hadoop_submit_jar": art("hadoop_submit_jar"),
            "hadoop_libjars": art("hadoop_libjars"),
            "hadoop_config": "experiments/inputs/15a/prep-config.json",
            "er_jar": art("er_jar"),
            "er_policy": art("er_policy"),
            "er_config": art("er_config"),
            "spark_config_template": art("spark_config_template"),
            "datasets_manifest": "experiments/inputs/15a/datasets.json",
            "artifact_sha256": {name: shas.get(name, PLACEHOLDER_SHA) for name in SHA_NAMES},
        },
        "metrics": {"locations": ["s3://%s/pipeline/%s/15a/size-%d/metrics/" % (ARTIFACTS, RUN, size)]},
    }


def render(shas, region="us-east-2"):
    return {"15a-emr-size-%d.json" % size: manifest(size, index + 1, shas, region) for index, size in enumerate(SIZES)}


def dump(document):
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", default=os.path.join(REPO, "experiments", "manifests"))
    parser.add_argument("--region", default="us-east-2")
    parser.add_argument("--sha", action="append", default=[], metavar="NAME=HEX", help="sha256 of an artifact (names: %s)" % ", ".join(SHA_NAMES))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    shas = {}
    for item in args.sha:
        name, _, value = item.partition("=")
        if name not in SHA_NAMES or not HEX64.match(value):
            print("RENDER-REFUSED: --sha needs NAME=<64 lowercase hex> with NAME one of %s" % ", ".join(SHA_NAMES))
            return 1
        shas[name] = value
    out_dir = os.path.abspath(args.out_dir)
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
