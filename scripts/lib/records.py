#!/usr/bin/env python3
"""The private push record (stdlib; python3 -I).

`deploy.sh --stage push` writes the record after every image was pushed AND the registry digest of each
<repository>:<commit> equals the digest the push reported. `deploy.sh --stage runtime-apply` requires it:
the record must name the same commit, account hash, region, environment and the four repositories, and the
current registry digest of every <repository>:<commit> must equal the recorded pushed digest before apply.

  write-push-record --root R --out FILE --commit C --account-sha256 H --region R --environment E
                    --run-id ID --pushed-utc T --pushed FILE
        --pushed lines: "<service>\\t<repository>\\t<digest>\\t<local image id>". The record is created exclusively
        (never overwritten) with mode 0600 below the repository root.
  check-push-record --file F --commit C [--account-sha256 H] --region R --environment E
                    --repositories "a/x b/y" --services "x y"
        prints "<service> <digest>" per service; exit 1 with "PUSH-RECORD-FAILED: ..." lines otherwise.
        --account-sha256 is omitted ONLY by rollback.sh's early pre-check (it has no account identity); deploy.sh
        always passes it, so the account is always compared before any apply.
  revision --file F
        prints the record's commit (= the image tag it pushed) when it is a 40-hex SHA; exit 1 otherwise.
        Used by the infrastructure rollback that keeps the runtime: the carried revision is the record's own.
"""
import argparse
import importlib.util
import json
import os
import re
import sys

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SCHEMA = "scholarchain.push-record.v1"


def _safeio():
    spec = importlib.util.spec_from_file_location("sc_safeio", os.path.join(os.path.dirname(os.path.abspath(__file__)), "safeio.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cmd_write(args):
    images = []
    with open(args.pushed, encoding="utf-8") as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 4:
                continue
            service, repository, digest, image_id = fields
            if not DIGEST.match(digest):
                print("PUSH-RECORD-FAILED: malformed pushed digest for %s" % service)
                return 1
            images.append({"service": service, "repository": repository, "tag": args.commit, "pushed_digest": digest, "local_image_id": image_id})
    if not images:
        print("PUSH-RECORD-FAILED: no pushed image to record")
        return 1
    document = {
        "schema": SCHEMA,
        "commit": args.commit,
        "account_sha256": args.account_sha256,
        "region": args.region,
        "environment": args.environment,
        "run_id": args.run_id,
        "pushed_utc": args.pushed_utc,
        "images": sorted(images, key=lambda image: image["service"]),
    }
    safeio = _safeio()
    try:
        handle = safeio.open_new(args.root, args.out)
    except safeio.Refused as error:
        print("PUSH-RECORD-FAILED: %s" % error)
        return 1
    with handle:
        handle.write((json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print("wrote push record %s" % os.path.basename(args.out))
    return 0


def cmd_check(args):
    problems = []
    try:
        with open(args.file, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError) as error:
        print("PUSH-RECORD-FAILED: push record unreadable: %s" % type(error).__name__)
        return 1
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        print("PUSH-RECORD-FAILED: unexpected push record schema")
        return 1
    for key, wanted, label in (
        ("commit", args.commit, "commit"),
        ("account_sha256", args.account_sha256, "account"),
        ("region", args.region, "region"),
        ("environment", args.environment, "environment"),
    ):
        if key == "account_sha256" and wanted is None:
            continue
        if document.get(key) != wanted:
            problems.append("push record %s differs from the deployment's %s" % (label, label))
    services = args.services.split()
    repositories = args.repositories.split()
    by_service = {}
    for image in document.get("images") or []:
        if isinstance(image, dict):
            by_service.setdefault(image.get("service"), []).append(image)
    if sorted(k for k in by_service if k) != sorted(services):
        problems.append("push record services %s differ from the expected services" % ",".join(sorted(str(k) for k in by_service)))
    for service, repository in zip(services, repositories):
        entries = by_service.get(service, [])
        if len(entries) != 1:
            problems.append("push record has %d entries for %s" % (len(entries), service))
            continue
        image = entries[0]
        if image.get("repository") != repository:
            problems.append("push record repository for %s differs from %s" % (service, repository))
        if image.get("tag") != args.commit:
            problems.append("push record tag for %s differs from the commit" % service)
        if not DIGEST.match(str(image.get("pushed_digest", ""))):
            problems.append("push record digest for %s is malformed" % service)
    if len(services) != len(repositories):
        problems.append("expected repositories and services differ in number")
    for problem in problems:
        print("PUSH-RECORD-FAILED: %s" % problem)
    if problems:
        return 1
    for service in services:
        print("%s %s" % (service, by_service[service][0]["pushed_digest"]))
    return 0


def cmd_revision(args):
    try:
        with open(args.file, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError) as error:
        print("PUSH-RECORD-FAILED: push record unreadable: %s" % type(error).__name__)
        return 1
    commit = document.get("commit") if isinstance(document, dict) else None
    if not isinstance(document, dict) or document.get("schema") != SCHEMA or not isinstance(commit, str) or not HEX40.match(commit):
        print("PUSH-RECORD-FAILED: the push record has no valid schema and commit")
        return 1
    print(commit)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("write-push-record")
    for name in ("root", "out", "commit", "account-sha256", "region", "environment", "run-id", "pushed-utc", "pushed"):
        p.add_argument("--" + name, required=True)
    p.set_defaults(fn=cmd_write)
    p = sub.add_parser("check-push-record")
    for name in ("file", "commit", "region", "environment", "repositories", "services"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--account-sha256")
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("revision")
    p.add_argument("--file", required=True)
    p.set_defaults(fn=cmd_revision)
    return parser


if __name__ == "__main__":
    namespace = build_parser().parse_args(sys.argv[1:])
    sys.exit(namespace.fn(namespace))
