#!/usr/bin/env python3
"""Pure evaluation of the after-destroy inventory (stdlib only, no AWS calls).

Subcommands (run with `python3 -I`):
  key-ids   --dir D                       print KMS key ids seen in tagging/aliases output
  evaluate  --dir D --account A --region R --bucket B
            print the inventory JSON; exit 0 clean, 2 billable remains, 3 inconclusive

Input files in D are the raw JSON outputs of the describe calls made by
inventory.sh (tagging.json, emr.json, nat.json, eip.json, eni.json,
instances.json, volumes.json, efs.json, aliases.json, kms-describe-N.json,
head-bucket.rc/.err) and errors.txt (names of calls that failed).
"""
import argparse
import glob
import json
import os
import sys

STACK_KEY = "scholarchain:stack"
STACK_VALUE = "spike-emr"
PREFIX = "scholarchain-spike-emr-"

# Tagged resource types that have an explicit describe elsewhere; the tagging
# API is only used as a cross-check for these (it can lag deletions).
COVERED_TYPES = {
    "ec2:natgateway", "ec2:elastic-ip", "ec2:network-interface", "ec2:instance", "ec2:volume",
    "elasticfilesystem:file-system", "elasticmapreduce:cluster", "kms:key", "s3:",
}
# Residue that never bills but is reported.
NONBILLABLE_TYPES = {
    "ec2:vpc", "ec2:subnet", "ec2:route-table", "ec2:internet-gateway", "ec2:security-group",
    "ec2:security-group-rule", "ec2:vpc-endpoint", "ec2:launch-template", "ec2:dhcp-options",
    "iam:role", "iam:instance-profile", "iam:policy", "elasticfilesystem:access-point",
}


def load(d, name, default=None):
    path = os.path.join(d, name)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return default
    with open(path) as handle:
        return json.load(handle)


def arn_type(arn):
    """Return 'service:resource-type' from an ARN (best effort)."""
    parts = arn.split(":", 5)
    if len(parts) < 6:
        return "unknown:"
    service, resource = parts[2], parts[5]
    if service == "s3":
        return "s3:"
    rtype = resource.split("/", 1)[0] if "/" in resource else resource.split(":", 1)[0]
    return f"{service}:{rtype}"


def key_ids(d):
    ids = []
    tagging = load(d, "tagging.json", {}) or {}
    for item in tagging.get("ResourceTagMappingList", []):
        arn = item.get("ResourceARN", "")
        if arn_type(arn) == "kms:key":
            ids.append(arn.rsplit("/", 1)[-1])
    aliases = load(d, "aliases.json", {}) or {}
    for alias in aliases.get("Aliases", []):
        if alias.get("AliasName", "").startswith("alias/" + PREFIX) and alias.get("TargetKeyId"):
            ids.append(alias["TargetKeyId"])
    seen, out = set(), []
    for key in ids:
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def tag_value(tags, key):
    for tag in tags or []:
        if tag.get("Key") == key:
            return tag.get("Value")
    return None


def evaluate(d, account, region, bucket):
    billable, retained, nonbillable, errors = [], [], [], []

    def add(kind, ident, detail):
        billable.append({"kind": kind, "id": ident, "detail": detail})

    failed = set()
    if os.path.exists(os.path.join(d, "errors.txt")):
        with open(os.path.join(d, "errors.txt")) as handle:
            failed = {line.strip() for line in handle if line.strip()}
    for name in sorted(failed):
        errors.append(f"describe call failed: {name}")

    # EMR (active states only; list-clusters --active)
    for cluster in (load(d, "emr.json", {}) or {}).get("Clusters", []):
        if cluster.get("Name", "").startswith(PREFIX):
            add("emr-cluster", cluster.get("Id"), cluster.get("Status", {}).get("State"))

    for gateway in (load(d, "nat.json", {}) or {}).get("NatGateways", []):
        state = gateway.get("State")
        if state not in ("deleted", "failed"):
            add("nat-gateway", gateway.get("NatGatewayId"), state)

    for address in (load(d, "eip.json", {}) or {}).get("Addresses", []):
        add("elastic-ip", address.get("AllocationId") or address.get("PublicIp"), "allocated")

    for eni in (load(d, "eni.json", {}) or {}).get("NetworkInterfaces", []):
        add("network-interface", eni.get("NetworkInterfaceId"), eni.get("Status"))

    for reservation in (load(d, "instances.json", {}) or {}).get("Reservations", []):
        for inst in reservation.get("Instances", []):
            state = inst.get("State", {}).get("Name")
            if state not in ("terminated",):
                add("ec2-instance", inst.get("InstanceId"), state)

    for vol in (load(d, "volumes.json", {}) or {}).get("Volumes", []):
        add("ebs-volume", vol.get("VolumeId"), vol.get("State"))

    for fs in (load(d, "efs.json", {}) or {}).get("FileSystems", []):
        mine = tag_value(fs.get("Tags"), STACK_KEY) == STACK_VALUE or str(fs.get("Name", "")).startswith(PREFIX)
        if mine and fs.get("LifeCycleState") != "deleted":
            add("efs-file-system", fs.get("FileSystemId"), fs.get("LifeCycleState"))

    # KMS keys
    for path in sorted(glob.glob(os.path.join(d, "kms-describe-*.json"))):
        meta = (load(d, os.path.basename(path), {}) or {}).get("KeyMetadata", {})
        state = meta.get("KeyState")
        ident = meta.get("KeyId")
        if state in ("PendingDeletion", "PendingReplicaDeletion"):
            retained.append({"kind": "kms-key", "id": ident, "detail": state + " (expected-retained)"})
        elif state:
            add("kms-key", ident, state)
    for alias in (load(d, "aliases.json", {}) or {}).get("Aliases", []):
        if alias.get("AliasName", "").startswith("alias/" + PREFIX):
            nonbillable.append({"kind": "kms-alias", "id": alias["AliasName"], "detail": "alias still present"})

    # S3 bucket
    rc_text = ""
    rc_path = os.path.join(d, "head-bucket.rc")
    if os.path.exists(rc_path):
        with open(rc_path) as handle:
            rc_text = handle.read().strip()
    err_text = ""
    if os.path.exists(os.path.join(d, "head-bucket.err")):
        with open(os.path.join(d, "head-bucket.err")) as handle:
            err_text = handle.read()
    if rc_text == "0":
        add("s3-bucket", bucket, "exists")
    elif rc_text and ("404" in err_text or "Not Found" in err_text or "NoSuchBucket" in err_text):
        pass
    else:
        errors.append(f"head-bucket inconclusive (rc={rc_text or 'missing'}): cannot confirm {bucket} is absent")

    # Tagging API: anything not covered by an explicit describe above.
    tagged = []
    for item in (load(d, "tagging.json", {}) or {}).get("ResourceTagMappingList", []):
        arn = item.get("ResourceARN", "")
        rtype = arn_type(arn)
        tagged.append(arn)
        if rtype in COVERED_TYPES:
            continue
        if rtype in NONBILLABLE_TYPES:
            nonbillable.append({"kind": rtype, "id": arn, "detail": "tagged resource still listed"})
        else:
            add("unclassified-" + rtype, arn, "tagged resource of an unrecognised type; treated as billable")

    clean = not billable and not errors
    result = {
        "stack": STACK_VALUE,
        "account": account,
        "region": region,
        "bucket": bucket,
        "billable_remaining": billable,
        "expected_retained": retained,
        "nonbillable_residual": nonbillable,
        "tagged_arns_seen": sorted(tagged),
        "errors": errors,
        "clean": clean,
    }
    return result, (0 if clean else (2 if billable else 3))


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("key-ids")
    k.add_argument("--dir", required=True)
    e = sub.add_parser("evaluate")
    e.add_argument("--dir", required=True)
    e.add_argument("--account", required=True)
    e.add_argument("--region", required=True)
    e.add_argument("--bucket", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "key-ids":
        for key in key_ids(args.dir):
            print(key)
        return 0
    result, code = evaluate(args.dir, args.account, args.region, args.bucket)
    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
