"""Phase 15 P2: every `aws` call in the infra-engineer's deployment scripts uses an operation and options that the real AWS CLI
v2 (2.35.4, the version Session 1 ran) accepts. Session 1 lost time to two fakes that were more lenient than the CLI
(7ecc572: `aws emr list-instance-groups` does not exist in CLI v2; b6dc94d: add-steps takes the CLI CUSTOM_JAR shape).

1. Static (always runs): the call sites of scripts/deploy.sh, plan.sh, upload-slice.sh and run-bounded-pipeline.sh are parsed
   (continuation lines joined; comments skipped). Every (service, operation) must be in the pinned table below and every
   long option must be a pinned input parameter of that operation or a global option. A new call, or a new option, fails
   here until its shape is reviewed and pinned.
2. Offline real-CLI check (runs when `aws` reports aws-cli/2.35.4; otherwise skipped): the pinned parameters are compared with
   `aws <svc> <op> --generate-cli-skeleton input` (API operations) or the offline `help` synopsis (CLI customizations), with
   every AWS_* variable removed and AWS_CONFIG_FILE / AWS_SHARED_CREDENTIALS_FILE set to /dev/null. Neither command contacts
   AWS: the skeleton is generated from the bundled service model and help is rendered locally.
No cloud call, no credentials, no state.
"""
import json
import os
import re
import shutil
import subprocess
import unittest

from helpers import SCRIPTS_DIR

OWNED = ("deploy.sh", "plan.sh", "upload-slice.sh", "run-bounded-pipeline.sh")
GLOBAL = {"region", "query", "output", "profile", "no-paginate", "no-cli-pager"}
CLI_VERSION = "2.35.4"

# Pinned from the offline skeletons / help of AWS CLI 2.35.4 (only the parameters the scripts use; the real check below
# proves each one still exists). "kind" says how the real CLI is asked: skeleton (API operation) or help (customization).
PINNED = {
    ("sts", "get-caller-identity"): ("skeleton", set()),
    ("s3api", "list-objects-v2"): ("skeleton", {"bucket", "prefix"}),
    ("s3api", "get-object-attributes"): ("skeleton", {"bucket", "key", "object-attributes", "max-parts"}),
    ("s3api", "put-object"): ("skeleton", {"bucket", "key", "body", "checksum-algorithm", "checksum-sha256", "if-none-match"}),
    ("s3api", "head-object"): ("skeleton", {"bucket", "key", "checksum-mode"}),
    ("ecr", "describe-images"): ("skeleton", {"repository-name", "image-ids"}),
    ("ecr", "describe-repositories"): ("skeleton", {"repository-names"}),
    ("ecs", "describe-services"): ("skeleton", {"cluster", "services"}),
    ("ecs", "describe-task-definition"): ("skeleton", {"task-definition"}),
    ("emr", "get-auto-termination-policy"): ("skeleton", {"cluster-id"}),
    ("emr", "cancel-steps"): ("skeleton", {"cluster-id", "step-ids", "step-cancellation-option"}),
    ("emr", "describe-step"): ("skeleton", {"cluster-id", "step-id"}),
    # CLI customizations: no skeleton without the API call's required arguments, so their help synopsis is used.
    ("emr", "describe-cluster"): ("help", {"cluster-id"}),
    ("emr", "add-steps"): ("help", {"cluster-id", "steps"}),
    ("ecr", "get-login-password"): ("help", set()),
    ("s3", "cp"): ("help", {"only-show-errors", "checksum-algorithm", "metadata"}),
}
# Operations the CLI v2 does not have: a call to one of these must never appear (7ecc572).
ABSENT = {("emr", "list-instance-groups")}
# AWS CLI service names (a call to any of them is checked; prose such as "aws command failed" is not a call).
SERVICES = sorted({svc for svc, _op in PINNED} | {svc for svc, _op in ABSENT} | {
    "ec2", "iam", "dynamodb", "s3vectors", "logs", "cloudwatch", "resourcegroupstaggingapi", "secretsmanager", "elbv2", "neptune",
    "efs", "acm", "route53", "sqs", "stepfunctions", "kms", "budgets", "ce", "application-autoscaling", "servicediscovery",
    "cloudtrail", "ssm", "ecr-public", "events", "lambda"})
CALL = re.compile(r"(?<![A-Za-z0-9_./-])aws (%s) ([a-z0-9-]+)" % "|".join(re.escape(s) for s in SERVICES))


def norm(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def logical_lines(path):
    """(first physical line number, text) with backslash continuations joined; whole-line comments dropped."""
    out, buffer, start = [], "", None
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if buffer == "" and line.lstrip().startswith("#"):
                continue
            start = start or number
            stripped = line.rstrip("\n")
            if stripped.endswith("\\"):
                buffer += stripped[:-1] + " "
                continue
            out.append((start, buffer + stripped))
            buffer, start = "", None
    if buffer:
        out.append((start, buffer))
    return out


def call_sites():
    """[(script:line, service, operation, [long options])] for every `aws <svc> <op>` in the owned scripts."""
    sites = []
    for name in OWNED:
        for number, text in logical_lines(os.path.join(SCRIPTS_DIR, name)):
            for match in CALL.finditer(text):
                rest = re.split(r"\|\||\||;|\)\"|\$\(", text[match.end():])[0]
                flags = re.findall(r"(?<![A-Za-z0-9-])--([a-z0-9][a-z0-9-]*)", rest)
                sites.append(("%s:%d" % (name, number), match.group(1), match.group(2), flags))
    return sites


def clean_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("AWS_")}
    env.update({"AWS_CONFIG_FILE": os.devnull, "AWS_SHARED_CREDENTIALS_FILE": os.devnull, "AWS_EC2_METADATA_DISABLED": "true",
                "AWS_PAGER": "", "PAGER": "cat", "MANPAGER": "cat"})
    return env


class StaticCallShapeTests(unittest.TestCase):
    def setUp(self):
        self.sites = call_sites()

    def test_the_parser_finds_the_known_calls(self):
        found = {(svc, op) for _s, svc, op, _f in self.sites}
        for needed in (("emr", "add-steps"), ("emr", "describe-cluster"), ("s3api", "put-object"), ("ecs", "describe-services"), ("s3", "cp")):
            self.assertIn(needed, found)
        self.assertGreaterEqual(len(self.sites), 30)

    def test_every_call_is_a_pinned_operation_with_pinned_options_only(self):
        problems = []
        for site, svc, op, flags in self.sites:
            if (svc, op) in ABSENT:
                problems.append("%s: aws %s %s does not exist in AWS CLI v2" % (site, svc, op))
                continue
            if (svc, op) not in PINNED:
                problems.append("%s: aws %s %s is not in the reviewed table (pin its shape first)" % (site, svc, op))
                continue
            allowed = {norm(f) for f in PINNED[(svc, op)][1] | GLOBAL}
            unknown = [f for f in flags if norm(f) not in allowed]
            if unknown:
                problems.append("%s: aws %s %s with unpinned option(s) %s" % (site, svc, op, ", ".join("--" + f for f in unknown)))
        self.assertEqual(problems, [])

    def test_the_add_steps_value_is_the_cli_custom_jar_shape(self):
        import sys

        sys.path.insert(0, os.path.join(SCRIPTS_DIR, "lib"))
        import pipeline  # noqa: E402

        steps = json.loads(pipeline.step_json("hadoop-prep", "run-1", ["bash", "-c", "true"]))
        self.assertEqual(set(steps[0]), {"Type", "Name", "ActionOnFailure", "Jar", "Args"})
        self.assertEqual((steps[0]["Type"], steps[0]["Jar"]), ("CUSTOM_JAR", "command-runner.jar"))


def aws_cli():
    exe = shutil.which("aws")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60, env=clean_env())
    except (OSError, subprocess.SubprocessError):
        return None
    return exe if (out.stdout + out.stderr).startswith("aws-cli/%s " % CLI_VERSION) else None


class RealCliOfflineShapeTests(unittest.TestCase):
    """Offline only: --generate-cli-skeleton and help never send a request."""

    def setUp(self):
        self.aws = aws_cli()
        if not self.aws:
            self.skipTest("aws-cli/%s is not on PATH" % CLI_VERSION)

    def run_aws(self, *args):
        return subprocess.run([self.aws] + list(args), capture_output=True, text=True, timeout=120, env=clean_env())

    def test_the_pinned_parameters_exist_in_the_real_cli(self):
        problems = []
        for (svc, op), (kind, params) in sorted(PINNED.items()):
            if kind == "skeleton":
                done = self.run_aws(svc, op, "--generate-cli-skeleton", "input")
                if done.returncode != 0:
                    problems.append("%s %s: skeleton exit %d" % (svc, op, done.returncode))
                    continue
                keys = {norm(k) for k in json.loads(done.stdout or "{}")}
                missing = sorted(p for p in params if norm(p) not in keys)
            else:
                done = self.run_aws(svc, op, "help")
                text = done.stdout
                if done.returncode != 0 or "SYNOPSIS" not in re.sub(r".\x08", "", text):
                    problems.append("%s %s: help exit %d" % (svc, op, done.returncode))
                    continue
                synopsis = re.sub(r".\x08", "", text)
                missing = sorted(p for p in params if "--" + p not in synopsis)
            if missing:
                problems.append("%s %s: the real CLI has no %s" % (svc, op, ", ".join(missing)))
        self.assertEqual(problems, [])

    def test_the_operations_known_to_be_absent_are_rejected_by_the_real_cli(self):
        for svc, op in sorted(ABSENT):
            done = self.run_aws(svc, op, "--generate-cli-skeleton", "input")
            self.assertEqual(done.returncode, 252, done.stdout + done.stderr)
            self.assertIn("invalid choice", done.stderr)


if __name__ == "__main__":
    unittest.main()
