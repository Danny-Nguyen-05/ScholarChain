#!/usr/bin/env python3
"""Fake `aws` CLI for tests. Makes no network call and reads no credentials.

Behaviour is driven by files under $FAKE_AWS_DIR; every invocation is appended
(one line, space-joined) to $FAKE_AWS_LOG together with a global order marker
when $SHIM_ORDER_LOG is set.

  sts get-caller-identity          -> prints sts.txt (text form "Arn Account")
  configure get region             -> prints configure-region.txt (rc 1 if absent)
  s3 cp SRC DST [--recursive]      -> local copies between $FAKE_AWS_DIR/s3/<bucket>/<key> and local paths
  s3api head-bucket                -> rc from head-bucket.rc, stderr from head-bucket.err
  kms describe-key --key-id X      -> kms-describe-key-X.json
  <svc> <op>                       -> <svc>-<op>.json (prints {} if absent); <svc>-<op>.rc forces an exit code
"""
import os
import shutil
import sys


def main(argv):
    d = os.environ["FAKE_AWS_DIR"]
    log = os.environ.get("FAKE_AWS_LOG")
    order = os.environ.get("SHIM_ORDER_LOG")
    line = "aws " + " ".join(argv)
    if log:
        with open(log, "a") as handle:
            handle.write(line + "\n")
    if order:
        with open(order, "a") as handle:
            handle.write(line + "\n")
    args = [a for a in argv if a not in ("--only-show-errors",)]
    # drop --region X / --output X / --query X
    cleaned, skip = [], False
    for i, a in enumerate(args):
        if skip:
            skip = False
            continue
        if a in ("--region", "--output", "--query", "--filter", "--filters", "--tag-filters"):
            skip = True
            continue
        cleaned.append(a)
    args = cleaned
    svc, op = (args + ["", ""])[:2]

    def read(name):
        path = os.path.join(d, name)
        return open(path).read() if os.path.exists(path) else None

    rc_text = read(f"{svc}-{op}.rc")
    if rc_text is not None and svc not in ("s3api",):
        sys.stderr.write(read(f"{svc}-{op}.err") or "forced failure\n")
        return int(rc_text.strip())

    if svc == "sts" and op == "get-caller-identity":
        text = read("sts.txt")
        if text is None:
            return 255
        sys.stdout.write(text)
        return 0
    if svc == "configure":
        text = read("configure-region.txt")
        if text is None:
            return 1
        sys.stdout.write(text)
        return 0
    if svc == "s3" and op == "cp":
        src, dst = args[2], args[3]
        recursive = "--recursive" in args
        if src.startswith("s3://"):
            path = os.path.join(d, "s3", src[len("s3://"):])
            if recursive:
                if os.path.isdir(path):
                    shutil.copytree(path, dst, dirs_exist_ok=True)
                return 0
            if not os.path.exists(path):
                sys.stderr.write("fatal error: An error occurred (404) when calling the HeadObject operation: Key not found\n")
                return 1
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            shutil.copyfile(path, dst)
            return 0
        path = os.path.join(d, "s3", dst[len("s3://"):])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        shutil.copyfile(src, path)
        return 0
    if svc == "s3api" and op == "head-bucket":
        rc = int((read("head-bucket.rc") or "254").strip())
        err = read("head-bucket.err")
        if err:
            sys.stderr.write(err)
        return rc
    if svc == "kms" and op == "describe-key":
        key = args[args.index("--key-id") + 1]
        text = read(f"kms-describe-key-{key}.json")
        if text is None:
            return 254
        sys.stdout.write(text)
        return 0
    text = read(f"{svc}-{op}.json")
    sys.stdout.write(text if text is not None else "{}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
