#!/usr/bin/env python3
"""Upper bound on S3 and Terraform API requests for ONE attempt of the spike.

Pure arithmetic over request-manifest.json and the Terraform source; makes no
AWS call. Usage (stdlib only):

    python3 -I request_bound.py [--manifest M] [--tf-dir D] [--check]

Prints JSON. With --check, exits 1 if the bound exceeds the reviewed envelope
(1000 PUT/LIST, 10000 GET/HEAD) or the manifest does not match the Terraform
aws_s3_object resources, so a newly staged object cannot be added silently.

S3 pricing classes used: PUT/COPY/POST/LIST (CreateBucket, Put*, multipart
create/part/complete, ListObjects*, DeleteObjects) versus GET/SELECT/other
(GetObject, HeadObject, Get*/Head*). DeleteObject itself is free and not counted.
"""
import argparse
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MANIFEST = os.path.join(HERE, "request-manifest.json")
DEFAULT_TF_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "infra", "terraform", "spikes", "emr-spark-isolated"))
S3_OBJECT_RE = re.compile(r'^\s*resource\s+"aws_s3_object"\s+"([A-Za-z0-9_]+)"', re.M)
RESOURCE_RE = re.compile(r'^\s*resource\s+"([A-Za-z0-9_]+)"\s+"([A-Za-z0-9_]+)"', re.M)


class ManifestMismatch(Exception):
    pass


def tf_sources(tf_dir):
    out = []
    for name in sorted(os.listdir(tf_dir)):
        if name.endswith(".tf"):
            with open(os.path.join(tf_dir, name)) as handle:
                out.append(handle.read())
    return "\n".join(out)


def tf_resources(tf_dir):
    text = tf_sources(tf_dir)
    return sorted(set(RESOURCE_RE.findall(text))), sorted(set(S3_OBJECT_RE.findall(text)))


def object_bytes(obj):
    if "bytes" in obj:
        return int(obj["bytes"])
    size = int(obj["max_bytes"])
    repo_file = obj.get("repo_file")
    if repo_file:
        path = os.path.join(HERE, repo_file)
        if os.path.exists(path):
            actual = os.path.getsize(path)
            if actual > size:
                raise ManifestMismatch(f"{repo_file} is {actual} bytes, over its manifest max_bytes {size}")
    return size


def ceil_div(a, b):
    return int(math.ceil(a / b))


def compute(manifest, tf_dir):
    a = manifest["assumptions"]
    retry = a["retry_multiplier"]
    cycles = a["terraform_read_cycles"]
    objects = manifest["staged_objects"]

    # ---- manifest <-> terraform consistency --------------------------------
    resources, tf_objects = tf_resources(tf_dir)
    manifest_objects = sorted(o["terraform_resource"].split(".", 1)[1] for o in objects)
    if manifest_objects != tf_objects:
        raise ManifestMismatch(
            "request-manifest.json staged_objects do not match aws_s3_object resources in Terraform: "
            f"manifest={manifest_objects} terraform={tf_objects}"
        )

    sizes = {o["id"]: object_bytes(o) for o in objects}
    part = a["provider_upload_part_bytes"]
    cli = a["cli_part_bytes"]

    # ---- PUT/COPY/POST/LIST per attempt ------------------------------------
    tf_upload = 0
    for o in objects:
        b = sizes[o["id"]]
        tf_upload += 1 if b <= part else ceil_div(b, part) + 2  # create + parts + complete
        tf_upload += a["terraform_object_tagging_puts_per_object"]
    bucket_cfg = a["bucket_config_put_calls"]
    collect_parts = ceil_div(a["collect_max_bytes"], cli)
    collect_upload = (collect_parts + 2 if a["collect_max_bytes"] > cli else 1) + a["collect_extra_put_objects"]
    n_objects_destroy = len(objects) + a["bucket_objects_at_destroy_besides_staged"] + a["emr_log_distinct_objects"]
    destroy_put_list = (
        ceil_div(n_objects_destroy, 1000) + a["destroy_extra_list_calls"]  # ListObjectVersions pages + extras
        + ceil_div(n_objects_destroy, a["destroy_delete_post_batch"])      # DeleteObjects POST batches
    )
    evidence_list = a["evidence_list_calls"]
    retried_put_list = (tf_upload + bucket_cfg + collect_upload + destroy_put_list + evidence_list) * retry
    intervals = a["max_cluster_minutes"] // a["emr_log_pusher_interval_minutes"]
    log_pusher = intervals * a["emr_log_pusher_changed_objects_per_interval"] + a["emr_log_pusher_final_flush_objects"]
    put_list_total = retried_put_list + log_pusher

    # ---- GET/HEAD per attempt ----------------------------------------------
    tf_reads = cycles * (a["bucket_resource_get_calls_per_read"] + len(objects) * a["object_get_head_calls_per_read"])
    node_downloads = 0
    for o in objects:
        b = sizes[o["id"]]
        per_node = 2 if (o["downloader"] == "emr" or b <= cli) else 1 + ceil_div(b, cli)  # HEAD + (GET | ranged GETs)
        node_downloads += per_node * len(o["consumers"])
    collect_get = 0  # collect uploads only
    evidence_get = (1 + ceil_div(a["collect_max_bytes"], cli)) + 2 + a["emr_log_distinct_objects"] * 2
    retried_get_head = (tf_reads + node_downloads + collect_get + evidence_get) * retry
    get_head_total = retried_get_head

    # ---- Terraform API calls -------------------------------------------------
    per = a["terraform_api_calls_per_resource"]
    n_res = len(resources)
    tf_calls = n_res * (per["create"] + per["read"] * cycles + per["delete"]) * retry

    limits = manifest["limits"]
    return {
        "inputs": {
            "staged_objects": len(objects),
            "terraform_resources": n_res,
            "object_bytes": sizes,
            "retry_multiplier": retry,
        },
        "put_list": {
            "terraform_uploads_and_object_tags": tf_upload,
            "terraform_bucket_config": bucket_cfg,
            "collect_upload": collect_upload,
            "destroy_list_and_delete": destroy_put_list,
            "evidence_list": evidence_list,
            "subtotal_before_retry": tf_upload + bucket_cfg + collect_upload + destroy_put_list + evidence_list,
            "subtotal_with_retry": retried_put_list,
            "emr_log_pusher_assumption": log_pusher,
            "upper_bound": put_list_total,
            "limit": limits["put_list_per_attempt"],
        },
        "get_head": {
            "terraform_reads": tf_reads,
            "node_downloads": node_downloads,
            "evidence_downloads": evidence_get,
            "subtotal_before_retry": tf_reads + node_downloads + collect_get + evidence_get,
            "upper_bound": get_head_total,
            "limit": limits["get_head_per_attempt"],
        },
        "terraform_api_calls_upper_bound": tf_calls,
        "within_envelope": put_list_total <= limits["put_list_per_attempt"] and get_head_total <= limits["get_head_per_attempt"],
        "assumptions_ref": "scripts/phase12d-spike/request-manifest.json (assumptions)",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--tf-dir", default=DEFAULT_TF_DIR)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    with open(args.manifest) as handle:
        manifest = json.load(handle)
    try:
        result = compute(manifest, args.tf_dir)
    except ManifestMismatch as exc:
        print(f"MANIFEST MISMATCH: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.check and not result["within_envelope"]:
        print("REQUEST BOUND EXCEEDS THE REVIEWED ENVELOPE", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
