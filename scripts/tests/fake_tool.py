#!/usr/bin/env python3
"""Fake aws, terraform, docker and sbt for the Phase 13 script tests.

Invoked as: python3 -I fake_tool.py <tool> <args...> (through tiny wrapper scripts on PATH).
Every invocation appends one line to $FAKE_LOG: "<tool>\t<args joined by a space>\tprofile=<set|unset>".
Only argv and whether AWS_PROFILE was set are logged: no environment values, so no secret can leak
through the log. Behaviour is driven by FAKE_* environment variables (see the branches below).
No network access, no real credentials, no real cloud call.
"""
import hashlib
import time
import json
import os
import sys


def emit_canary():
    """FAKE_EMIT: text a real tool might echo (for example a variable value) on stderr."""
    text = os.environ.get("FAKE_EMIT")
    if text:
        sys.stderr.write(text + "\n")


def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def digest_for(repo, tag):
    """Deterministic registry digest of repo:tag; FAKE_IMAGE_DIGEST forces one value."""
    return os.environ.get("FAKE_IMAGE_DIGEST") or "sha256:" + sha256_text("digest:%s:%s" % (repo, tag))


def log(tool, args):
    path = os.environ.get("FAKE_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("%s\t%s\tprofile=%s\n" % (tool, " ".join(args), "set" if os.environ.get("AWS_PROFILE") else "unset"))


def chdir_log(sub, chdir):
    """Record the top-level file names of the directory terraform runs in (and the state binding it carries), so a
    test can prove WHICH source Terraform loaded: a materialized archive, never the work tree."""
    path = os.environ.get("FAKE_LOG")
    if not path or not chdir:
        return
    names = sorted(os.listdir(chdir)) if os.path.isdir(chdir) else []
    binding = ""
    binding_file = os.path.join(chdir, "zz_scholarchain_state_binding.tf")
    if os.path.isfile(binding_file):
        with open(binding_file, encoding="utf-8") as handle:
            for line in handle:
                if line.strip().startswith("path ="):
                    binding = line.split("=", 1)[1].strip().strip('"')
    with open(path + ".chdir", "a", encoding="utf-8") as handle:
        handle.write("%s\t%s\t%s\t%s\n" % (sub, chdir, ",".join(names), binding))


def strip_chdir(args):
    chdir = None
    rest = []
    for arg in args:
        if arg.startswith("-chdir="):
            chdir = arg[len("-chdir=") :]
        else:
            rest.append(arg)
    return chdir, rest


def terraform(args):
    chdir, rest = strip_chdir(args)
    if rest[:1] == ["version"]:
        print(json.dumps({"terraform_version": os.environ.get("FAKE_TF_VERSION", "1.13.5"), "platform": "fake"}))
        return 0
    sub = rest[0] if rest else ""
    chdir_log(sub, chdir)
    if sub == "init":
        return int(os.environ.get("FAKE_TF_INIT_RC", "0"))
    if sub == "plan":
        bump_during_plan = os.environ.get("FAKE_PLAN_BUMP_STATE")
        if bump_during_plan and os.path.isfile(bump_during_plan):  # another operator changes the state mid-plan
            with open(bump_during_plan, encoding="utf-8") as handle:
                document = json.load(handle)
            document["serial"] = int(document.get("serial", 0)) + 1
            with open(bump_during_plan, "w", encoding="utf-8") as handle:
                json.dump(document, handle)
        for arg in rest:
            if arg.startswith("-out="):
                with open(arg[5:], "w", encoding="utf-8") as handle:
                    handle.write("fake-plan\n" + os.environ.get("FAKE_PLAN_SALT", "") + "\n")
        print(os.environ.get("FAKE_PLAN_STDOUT", "Plan: 1 to add, 0 to change, 0 to destroy."))
        emit_canary()
        return int(os.environ.get("FAKE_TF_PLAN_RC", "0"))
    if sub == "show" and rest == ["show", "-json"]:  # the CURRENT STATE (no plan file argument)
        source = os.environ.get("FAKE_STATE_JSON")
        if source:
            with open(source, encoding="utf-8") as handle:
                sys.stdout.write(handle.read())
        else:
            print(json.dumps({"format_version": "1.0"}))
        return int(os.environ.get("FAKE_TF_STATE_SHOW_RC", "0"))
    if sub == "show":
        target = rest[-1] if len(rest) > 1 else ""
        replace = os.environ.get("FAKE_REPLACE_FILE")
        if replace:  # simulate the ORIGINAL plan file being swapped after it was verified
            with open(replace, "wb") as handle:
                handle.write(b"replaced-after-verification\n")
        if os.environ.get("FAKE_TAMPER_ARG") and target:  # simulate the verified copy itself being altered
            os.chmod(target, 0o600)
            with open(target, "ab") as handle:
                handle.write(b"tampered\n")
        bump_on_show = os.environ.get("FAKE_SHOW_BUMP_STATE")
        if bump_on_show and os.path.isfile(bump_on_show):  # the state changes between verification and apply
            with open(bump_on_show, encoding="utf-8") as handle:
                document = json.load(handle)
            document["serial"] = int(document.get("serial", 0)) + 1
            with open(bump_on_show, "w", encoding="utf-8") as handle:
                json.dump(document, handle)
        if "-json" in rest:
            source = os.environ.get("FAKE_SHOW_JSON")
            if source:
                with open(source, encoding="utf-8") as handle:
                    sys.stdout.write(handle.read())
            else:
                print(json.dumps({"resource_changes": []}))
        else:
            source = os.environ.get("FAKE_SHOW_TEXT")
            if source:
                with open(source, encoding="utf-8") as handle:
                    sys.stdout.write(handle.read())
            else:
                print("Terraform will perform the following actions:\n# fake_resource.example will be created")
        return 0
    if sub == "apply":
        plan_arg = rest[-1]
        replace_archive = os.environ.get("FAKE_APPLY_REPLACE_FILE")
        if replace_archive and os.path.isfile(replace_archive):  # same size, different bytes
            size = os.path.getsize(replace_archive)
            with open(replace_archive, "wb") as handle:
                handle.write(b"X" * size)
        replace_glob = os.environ.get("FAKE_APPLY_REPLACE_GLOB")
        if replace_glob:  # a file the script made (for example the private archive copy) is altered, same size
            import glob

            for match in glob.glob(replace_glob):
                size = os.path.getsize(match)
                os.chmod(match, 0o600)
                with open(match, "wb") as handle:
                    handle.write(b"Y" * size)
        bump = os.environ.get("FAKE_APPLY_BUMP_STATE")
        if bump and os.path.isfile(bump):  # a real apply changes the state's serial
            with open(bump, encoding="utf-8") as handle:
                document = json.load(handle)
            document["serial"] = int(document.get("serial", 0)) + 1
            with open(bump, "w", encoding="utf-8") as handle:
                json.dump(document, handle)
        if os.environ.get("FAKE_LOG") and os.path.isfile(plan_arg):
            with open(plan_arg, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
            with open(os.environ["FAKE_LOG"] + ".applied", "a", encoding="utf-8") as handle:
                handle.write("%s\t%s\n" % (plan_arg, digest))
        return int(os.environ.get("FAKE_TF_APPLY_RC", "0"))
    if sub == "state":
        listing = os.environ.get("FAKE_STATE_LIST", "")
        if listing:
            print(listing.replace(";", "\n"))
        return int(os.environ.get("FAKE_TF_STATE_RC", "0"))
    if sub in ("fmt", "validate", "test"):
        return int(os.environ.get("FAKE_TF_%s_RC" % sub.upper(), "0"))
    return 0


def flag_value(args, flag):
    for index, arg in enumerate(args):
        if arg == flag and index + 1 < len(args):
            return args[index + 1]
    return ""


def b64_sha256(data):
    import base64

    return base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")


def s3_store(op, args):
    """Fake `aws s3api list-objects-v2|get-object-attributes|put-object|head-object` over a directory (FAKE_S3_DIR).

    Objects live at $FAKE_S3_DIR/<bucket>/<key>; their S3 metadata at $FAKE_S3_DIR/.meta/<bucket>/<key>.json
    ({"ChecksumSHA256": <base64 or null>, "VersionId": ...}). Knobs: FAKE_S3_PUT_FAIL_KEY (put-object exits 255 for that key),
    FAKE_S3_CORRUPT_KEY (the stored checksum of that key is wrong after put), FAKE_S3_NO_IF_NONE_MATCH (an old CLI that
    does not know --if-none-match), FAKE_S3_LIST_RC (list-objects-v2 exit code). No network, no credentials."""
    root = os.environ["FAKE_S3_DIR"]
    bucket = flag_value(args, "--bucket")
    key = flag_value(args, "--key")
    obj = os.path.join(root, bucket, key)
    meta = os.path.join(root, ".meta", bucket, key + ".json")
    if op == "list-objects-v2":
        if os.environ.get("FAKE_S3_LIST_RC"):
            sys.stderr.write("fake list failure\n")
            return int(os.environ["FAKE_S3_LIST_RC"])
        prefix = flag_value(args, "--prefix")
        base = os.path.join(root, bucket)
        contents = []
        for current, _dirs, files in os.walk(base):
            for name in files:
                full = os.path.join(current, name)
                rel = os.path.relpath(full, base).replace(os.sep, "/")
                if rel.startswith(prefix):
                    contents.append({"Key": rel, "Size": os.path.getsize(full)})
        if contents:  # the real CLI prints nothing for an empty listing
            print(json.dumps({"Contents": sorted(contents, key=lambda c: c["Key"])}))
        return 0
    if op == "put-object":
        if os.environ.get("FAKE_S3_NO_IF_NONE_MATCH") and "--if-none-match" in args:
            sys.stderr.write("\nUnknown options: --if-none-match, *\n")
            return 252
        if os.environ.get("FAKE_S3_PUT_FAIL_KEY") == key:
            sys.stderr.write("fake connection reset\n")
            return 255
        if flag_value(args, "--checksum-algorithm") != "SHA256":
            sys.stderr.write("fake: put-object without --checksum-algorithm SHA256\n")
            return 252
        if os.path.exists(obj):
            sys.stderr.write("\nAn error occurred (PreconditionFailed) when calling the PutObject operation: At least one of the pre-conditions you specified did not hold\n")
            return 254
        with open(flag_value(args, "--body"), "rb") as handle:
            data = handle.read()
        real = b64_sha256(data)
        if flag_value(args, "--checksum-sha256") != real:
            sys.stderr.write("\nAn error occurred (BadDigest) when calling the PutObject operation: The SHA256 you specified did not match the calculated checksum.\n")
            return 254
        os.makedirs(os.path.dirname(obj), exist_ok=True)
        os.makedirs(os.path.dirname(meta), exist_ok=True)
        with open(obj, "wb") as handle:
            handle.write(data)
        stored = b64_sha256(b"tampered") if os.environ.get("FAKE_S3_CORRUPT_KEY") == key else real
        version = "ver-" + hashlib.sha256(key.encode()).hexdigest()[:10]
        with open(meta, "w", encoding="utf-8") as handle:
            json.dump({"ChecksumSHA256": stored, "VersionId": version}, handle)
        print(json.dumps({"ETag": '"%s"' % hashlib.md5(data).hexdigest(), "ChecksumSHA256": real, "VersionId": version}))
        return 0
    if op in ("get-object-attributes", "head-object"):
        if not os.path.isfile(obj):
            sys.stderr.write("\nAn error occurred (404) when calling the %s operation: Not Found\n" % ("HeadObject" if op == "head-object" else "GetObjectAttributes"))
            return 254
        info = {}
        if os.path.isfile(meta):
            with open(meta, encoding="utf-8") as handle:
                info = json.load(handle)
        size = os.path.getsize(obj)
        checksum = info.get("ChecksumSHA256")
        if op == "get-object-attributes":
            body = {"ObjectSize": size}
            if checksum:
                body["Checksum"] = {"ChecksumSHA256": checksum}
        else:
            body = {"ContentLength": size, "VersionId": info.get("VersionId")}
            if checksum and flag_value(args, "--checksum-mode") == "ENABLED":
                body["ChecksumSHA256"] = checksum
        print(json.dumps(body))
        return 0
    return 0


SERVICE_NAMES = ("query-api", "graph-service", "semantic-service", "embedding-worker")


def aws(args):
    emit_canary()
    cleaned, skip = [], False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg in ("--region", "--query", "--output", "--repository-name", "--repository-names", "--task-definition", "--cluster"):
            skip = True
            continue
        cleaned.append(arg)
    svc, op = (cleaned + ["", ""])[:2]
    # 13C (finding B1): FAKE_AWS_HANG=cp hangs `aws s3 cp` (the copies of stage-in and copy-out) until it is killed.
    if svc == "s3" and op == os.environ.get("FAKE_AWS_HANG", "-"):
        if os.environ.get("FAKE_AWS_IGNORE_TERM"):
            # a stuck copy that ignores SIGTERM: only SIGKILL ends it; its pid is recorded for the test
            import signal

            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if os.environ.get("FAKE_AWS_PIDFILE"):
            with open(os.environ["FAKE_AWS_PIDFILE"], "w", encoding="utf-8") as handle:
                handle.write(str(os.getpid()))
        time.sleep(600)
    account = os.environ.get("FAKE_ACCOUNT_ID", "123456789012")
    if (svc, op) == ("sts", "get-caller-identity"):
        if os.environ.get("FAKE_STS_RC"):
            sys.stderr.write("fake sts failure\n")
            return int(os.environ["FAKE_STS_RC"])
        if flag_value(args, "--query") == "Arn":  # upload-slice.sh checks that the caller is an operator-loader session
            print(os.environ.get("FAKE_STS_ARN", "arn:aws:sts::%s:assumed-role/scholarchain-course-operator-loader/fake-session" % account))
            return 0
        print(account)
        return 0
    if svc == "s3api" and os.environ.get("FAKE_S3_DIR"):  # a stateful bucket on disk (upload-slice.sh tests)
        return s3_store(op, args)
    if svc == "emr":
        return emr(op, args)
    if (svc, op) == ("s3", "ls"):  # `aws s3 ls --recursive --summarize` as the stage-in body reads it
        print("Total Objects: 1")
        print("   Total Size: %s" % os.environ.get("FAKE_S3_TOTAL", "1024"))
        return 0
    if (svc, op) == ("ecr", "describe-repositories"):
        return int(os.environ.get("FAKE_ECR_REPO_RC", "0"))
    if (svc, op) == ("ecr", "describe-images"):
        repo = flag_value(args, "--repository-name")
        tag = flag_value(args, "--image-ids").replace("imageTag=", "")
        print(digest_for(repo, tag))
        return 0
    if (svc, op) == ("ecr", "get-login-password"):
        print("FAKE-REGISTRY-PASSWORD-0123456789")
        return 0
    if (svc, op) == ("ecs", "describe-services"):
        names = os.environ.get("FAKE_ECS_SERVICES")
        wanted = names.split(",") if names is not None else list(SERVICE_NAMES)
        for name in wanted:
            if name:
                print("%s\tarn:aws:ecs:us-east-2:%s:task-definition/scholarchain-course-%s:7" % (name, account, name))
        return 0
    if (svc, op) == ("ecs", "describe-task-definition"):
        arn = flag_value(args, "--task-definition")
        name = arn.split("task-definition/scholarchain-course-")[-1].rsplit(":", 1)[0]
        tag = os.environ.get("FAKE_ECS_TAG", "unset-tag")
        if os.environ.get("FAKE_ECS_STALE_SERVICE") == name:
            tag = "0" * 40
        repo_service = "query-api" if os.environ.get("FAKE_ECS_SWAP_SERVICE") == name else name
        print("%s.dkr.ecr.us-east-2.amazonaws.com/scholarchain-course/%s:%s" % (account, repo_service, tag))
        return 0
    if svc == "s3" and op == "cp":
        src = cleaned[2] if len(cleaned) > 2 else ""
        recorded = ""
        if os.path.isfile(src):
            with open(src, "rb") as handle:
                recorded = hashlib.sha256(handle.read()).hexdigest()
        metadata = flag_value(args, "--metadata")
        if os.environ.get("FAKE_LOG"):
            with open(os.environ["FAKE_LOG"] + ".uploads", "a", encoding="utf-8") as handle:
                handle.write("%s\t%s\t%s\n" % (src, recorded, metadata))
        return 0
    if (svc, op) == ("s3api", "head-object"):
        print(os.environ.get("FAKE_HEAD_OBJECT", ""))
        return 0
    if (svc, op) == ("s3api", "get-object-attributes"):  # the part list of a multipart object: "<n>\t<size>\t<b64 sha256>"
        print(os.environ.get("FAKE_OBJECT_PARTS", ""))
        return 0
    if (svc, op) == ("resourcegroupstaggingapi", "get-resources"):
        print(os.environ.get("FAKE_TAG_JSON", json.dumps({"ResourceTagMappingList": []})))
        return 0
    return 0


def emr(op, args):
    """Fake `aws emr ...` for the Subphase 13B tests. Read-only calls print JSON; add-steps records the exact --steps
    JSON in $FAKE_LOG.steps and returns s-FAKE<n>; describe-step state comes from FAKE_EMR_STEP_STATE_<n> (or
    FAKE_EMR_STEP_STATE, default COMPLETED)."""
    cluster = flag_value(args, "--cluster-id")
    if op == "list-instance-groups":  # AWS CLI v2 has no such command; the pipeline must never call it
        print("aws: error: argument operation: Found invalid choice 'list-instance-groups'", file=sys.stderr)
        return 252
    if op == "describe-cluster":
        # Like the CLI v2 customization, embed the ListInstanceGroups result as Cluster.InstanceGroups.
        default = [
            {"InstanceGroupType": "MASTER", "InstanceType": "m5.xlarge", "RequestedInstanceCount": 1, "RunningInstanceCount": 1},
            {"InstanceGroupType": "CORE", "InstanceType": "m5.xlarge", "RequestedInstanceCount": 1, "RunningInstanceCount": 1},
            {"InstanceGroupType": "TASK", "InstanceType": "m5.xlarge", "RequestedInstanceCount": 0, "RunningInstanceCount": 0},
        ]
        cluster_doc = {"Id": os.environ.get("FAKE_EMR_CLUSTER_ID", cluster), "Status": {"State": os.environ.get("FAKE_EMR_STATE", "WAITING")}}
        if os.environ.get("FAKE_EMR_GROUPS") != "absent":
            cluster_doc["InstanceGroups"] = json.loads(os.environ["FAKE_EMR_GROUPS"]) if os.environ.get("FAKE_EMR_GROUPS") else default
        print(json.dumps({"Cluster": cluster_doc}))
        return 0
    if op == "get-auto-termination-policy":
        idle = os.environ.get("FAKE_EMR_IDLE", "900")
        print(json.dumps({} if idle == "none" else {"AutoTerminationPolicy": {"IdleTimeout": int(idle)}}))
        return 0
    if op == "add-steps":
        path = os.environ.get("FAKE_LOG", "") + ".steps"
        count = 0
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                count = sum(1 for _ in handle)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(flag_value(args, "--steps") + "\n")
        print("s-FAKE%d" % (count + 1))
        return int(os.environ.get("FAKE_EMR_ADD_RC", "0"))
    if op == "describe-step":
        number = flag_value(args, "--step-id").replace("s-FAKE", "")
        print(os.environ.get("FAKE_EMR_STEP_STATE_" + number) or os.environ.get("FAKE_EMR_STEP_STATE", "COMPLETED"))
        return 0
    return 0


def docker(args):
    emit_canary()
    if args[:1] == ["info"]:
        rc = int(os.environ.get("FAKE_DOCKER_INFO_RC", "0"))
        if rc:
            sys.stderr.write("Cannot connect to the Docker daemon (fake)\n")
        return rc
    if args[:1] == ["version"]:
        print("29.5.3")
        return 0
    if args[:2] == ["buildx", "version"]:
        print("github.com/docker/buildx v0.99.0 (fake)")
        return 0
    if args[:2] == ["buildx", "build"]:
        return int(os.environ.get("FAKE_DOCKER_BUILD_RC", "0"))
    if args[:2] == ["image", "inspect"]:
        image = args[2] if len(args) > 2 else ""
        print(json.dumps([{"Id": fake_image_id(image), "Os": "linux", "Architecture": os.environ.get("FAKE_IMAGE_ARCH", "amd64")}]))
        return 0
    if args[:1] == ["push"]:
        remote = args[1] if len(args) > 1 else ""
        repo_tag = remote.split("/", 1)[-1]
        repo, _, tag = repo_tag.rpartition(":")
        digest = os.environ.get("FAKE_PUSH_DIGEST") or digest_for(repo, tag)
        print("%s: digest: %s size: 1234" % (tag, digest))
        return 0
    return 0


def fake_image_id(image):
    """Local image ID of a tag; FAKE_IMAGE_REPLACED=<substring> models a tag that was replaced."""
    replaced = os.environ.get("FAKE_IMAGE_REPLACED")
    salt = "-replaced" if replaced and replaced in image else ""
    return "sha256:" + sha256_text(image + salt)


def sbt(args):
    emit_canary()
    # JAVA_HOME and SBT_OPTS are not secrets; record them so tests can assert the JDK 17 environment.
    if os.environ.get("FAKE_LOG"):
        with open(os.environ["FAKE_LOG"] + ".sbtenv", "a", encoding="utf-8") as handle:
            handle.write("JAVA_HOME=%s SBT_OPTS=%s\n" % (os.environ.get("JAVA_HOME", ""), os.environ.get("SBT_OPTS", "")))
    if "packageRelease" in args:
        rc = int(os.environ.get("FAKE_SBT_PACKAGE_RC", "0"))
        if rc:
            return rc
        for rel, data in (
            ("modules/hadoop/target/scala-3.3.4/hadoop-submit_3-0.1.0-SNAPSHOT.jar", b"submit"),
            ("modules/hadoop/target/scala-3.3.4/hadoop-dependency-bundle_3-0.1.0-SNAPSHOT.jar", b"bundle"),
            ("modules/spark/target/spark-job_3-0.1.0-SNAPSHOT.jar", b"spark"),
            ("modules/entity-resolution/target/er-job_3-0.1.0-SNAPSHOT.jar", b"erjob"),
            ("modules/services/target/distribution/services.jar", b"services"),
            ("modules/services/target/distribution/lib/dep.jar", b"dep"),
            ("modules/services/target/distribution/prompts/runtime/p.txt", b"p"),
            ("modules/services/target/distribution/prompts/schemas/s.json", b"{}"),
        ):
            os.makedirs(os.path.dirname(rel), exist_ok=True)
            with open(rel, "wb") as handle:
                handle.write(data)
        return 0
    return int(os.environ.get("FAKE_SBT_RC", "0"))


TOOLS = {"terraform": terraform, "aws": aws, "docker": docker, "sbt": sbt}

if __name__ == "__main__":
    tool, args = sys.argv[1], sys.argv[2:]
    log(tool, args)
    sys.exit(TOOLS[tool](args))
