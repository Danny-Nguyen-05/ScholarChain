"""Shared helpers for the Phase 13 script tests: temp git repos, fake executables on PATH, runners.

No network, no real AWS call, no credentials. Fake binaries log argv (never environment values).
"""
import base64
import datetime
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(TESTS_DIR)
REAL_REPO = os.path.dirname(SCRIPTS_DIR)
FAKE_TOOL = os.path.join(TESTS_DIR, "fake_tool.py")

FAKE_ACCOUNT = "123456789012"
FAKE_SECRET = "FAKE/SECRET+KEY-0123456789abcdefghijklmnop"
FAKE_TOKEN = "FAKE-SESSION-TOKEN-ZZZZ9999yyyyXXXX8888"
FAKE_PASSWORD = "FAKE-REGISTRY-PASSWORD-0123456789"
REGION = "us-east-2"
ENVIRONMENT = "course"
PROJECT = "scholarchain"
STATE_LINEAGE = "aaaabbbb-cccc-dddd-eeee-ffff00001111"
STATE_SERIAL = 7
SERVICES = ("query-api", "graph-service", "semantic-service", "embedding-worker")
SHA_A = "a" * 64
MUTATING = ("apply", "push", "login", "destroy", "get-login-password")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def b64_sha256(data):
    """What S3 reports as ChecksumSHA256 for a single-part object: base64 of the RAW sha256 digest."""
    return base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")


def head_object_text(data, checksum=None, size=None, sha=None):
    """The text `aws s3api head-object --query [ContentLength,Metadata.sha256,ChecksumSHA256]` prints for an upload of `data`."""
    return "%d\t%s\t%s" % (len(data) if size is None else size, sha or sha256_bytes(data), checksum or b64_sha256(data))


MISSING = object()


def fake_image_id(image):
    """Hand-derived local image ID the fake docker reports: sha256 of the tag string."""
    return "sha256:" + hashlib.sha256(image.encode()).hexdigest()


def registry_digest(service, tag):
    """Hand-derived registry digest the fake aws and docker agree on for scholarchain-course/<service>:<tag>."""
    return "sha256:" + hashlib.sha256(("digest:scholarchain-course/%s:%s" % (service, tag)).encode()).hexdigest()


def utc_hours_ago(hours):
    when = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def account_hash(account=FAKE_ACCOUNT):
    """Hand-derived: sha256 of the 12-digit string with no trailing newline."""
    return hashlib.sha256(account.encode("ascii")).hexdigest()


def write_exec(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid"] + list(args),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


# ---- realistic live-state resource lists (T1, repair round 4) -----------------------------------------------------
# Hand-written from infra/terraform/main.tf, phase12b.tf and the modules: module path, mode, type, name and instances,
# with index keys as Terraform writes them (none for a single resource, an integer for count, a string for for_each).
# The attributes are synthetic placeholders (no real ARN, account or secret); the scripts never read attributes.
AWS_PROVIDER = 'provider["registry.terraform.io/hashicorp/aws"]'
STATE_ATTRIBUTE_CANARY = "CANARY-STATE-ATTRIBUTE-5519"


def state_resource(module, rtype, name, keys=(None,)):
    instances = []
    for key in keys:
        instance = {"schema_version": 0, "attributes": {"id": "synthetic-%s-%s" % (name, key), "note": STATE_ATTRIBUTE_CANARY}}
        if key is not None:
            instance["index_key"] = key
        instances.append(instance)
    return {"module": module, "mode": "managed", "type": rtype, "name": name, "provider": AWS_PROVIDER, "instances": instances}


def post_base_apply_resources():
    """The state after the FIRST base apply (runtime disabled, image_revision = null). module.runtime then holds only
    what modules/runtime declares WITHOUT a count or for_each gated on image_revision: the ECS cluster, the service-
    discovery namespace and the four ECR repositories (repositories.tf for_each = local.services). No ECS service,
    task definition, load balancer, target group, listener, service-discovery service or autoscaling resource.
    The other modules are a representative sample of what a base apply creates."""
    return [
        state_resource("module.runtime", "aws_ecs_cluster", "course"),
        state_resource("module.runtime", "aws_service_discovery_private_dns_namespace", "course"),
        state_resource("module.runtime", "aws_ecr_repository", "service", SERVICES),
        state_resource("module.network", "aws_vpc", "course"),
        state_resource("module.network", "aws_subnet", "public", ("0", "1")),
        state_resource("module.network", "aws_subnet", "application", ("0", "1")),
        state_resource("module.network", "aws_nat_gateway", "course"),
        state_resource("module.network", "aws_security_group", "role", ("alb", "query-api", "graph-service", "semantic-service", "embedding-worker", "neptune", "endpoints", "emr")),
        state_resource("module.identity", "aws_kms_key", "data"),
        state_resource("module.identity", "aws_kms_alias", "data"),
        state_resource("module.identity", "aws_iam_role", "task", SERVICES),
        state_resource("module.identity", "aws_iam_role", "execution", SERVICES),
        state_resource("module.datalake", "aws_s3_bucket", "zone", ("raw", "curated", "graph", "rag", "artifacts", "logs", "reports")),
        state_resource("module.dynamodb", "aws_dynamodb_table", "table", ("RunLedger", "EntityLinkCache", "QuerySession")),
        state_resource("module.messaging", "aws_sqs_queue", "embedding"),
        state_resource("module.messaging", "aws_sqs_queue", "dead_letter"),
        state_resource("module.s3vectors", "aws_s3vectors_vector_bucket", "embeddings"),
        state_resource("module.observability", "aws_cloudwatch_log_group", "service", SERVICES),
        state_resource("module.observability", "aws_cloudwatch_metric_alarm", "queue_age"),
        state_resource(None, "terraform_data", "configuration_guard"),
    ]


HTTP_SERVICES = tuple(s for s in SERVICES if s != "embedding-worker")


def deployed_runtime_resources(listener=True, services=SERVICES, load_balancer=True, target_group=True):
    """The resources modules/runtime/compute.tf adds when the runtime is deployed (image_revision set): the gated set.
    The keyword arguments drop parts of it to model an incomplete (partial) runtime."""
    resources = [
        state_resource("module.runtime", "aws_ecs_task_definition", "service", services),
        state_resource("module.runtime", "aws_service_discovery_service", "http", [s for s in HTTP_SERVICES if s in services]),
        state_resource("module.runtime", "aws_appautoscaling_target", "service", services),
    ]
    if services:
        resources.append(state_resource("module.runtime", "aws_ecs_service", "service", services))
    if load_balancer:
        resources.append(state_resource("module.runtime", "aws_lb", "query", (0,)))
    if target_group:
        resources.append(state_resource("module.runtime", "aws_lb_target_group", "query", (0,)))
    if listener:
        resources.append(state_resource("module.runtime", "aws_lb_listener", "https", (0,)))
    return resources


def live_after_runtime_apply_resources(**parts):
    """A realistic state with the runtime deployed: the post-base-apply resources plus the gated runtime set."""
    return post_base_apply_resources() + deployed_runtime_resources(**parts)


class Result:
    def __init__(self, completed):
        self.rc = completed.returncode
        self.stdout = completed.stdout
        self.stderr = completed.stderr
        self.out = completed.stdout + completed.stderr

    def steps(self):
        return [line[len("STEP: ") :] for line in self.stdout.splitlines() if line.startswith("STEP: ")]

    def result_line(self):
        lines = [line for line in self.stdout.splitlines() if line.startswith("RESULT: ")]
        return lines[-1] if lines else ""


class Fixture(unittest.TestCase):
    """A temp git repo with the files the scripts read, fake executables, and a call log."""

    maxDiff = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-p13-test-")
        self.addCleanup(self._remove_tmp)
        self.repo = os.path.join(self.tmp, "repo")
        self.bin = os.path.join(self.tmp, "bin")
        self.log = os.path.join(self.tmp, "calls.log")
        self.timeout_log = os.path.join(self.tmp, "timeout.log")
        self.jdk = os.path.join(self.tmp, "jdk17")
        open(self.log, "w").close()
        open(self.timeout_log, "w").close()
        os.makedirs(self.bin)
        for tool in ("aws", "terraform", "docker", "sbt"):
            write_exec(os.path.join(self.bin, tool), '#!/bin/bash\nexec python3 -I "%s" %s "$@"\n' % (FAKE_TOOL, tool))
        os.makedirs(os.path.join(self.jdk, "bin"))
        write_exec(os.path.join(self.jdk, "bin", "java"), '#!/bin/bash\necho \'openjdk version "17.0.9" 2023-10-17\' >&2\n')
        self.build_repo()

    def _remove_tmp(self):
        # Materialized Terraform sources are read-only trees: restore write permission before removing.
        subprocess.run(["chmod", "-R", "u+w", self.tmp], capture_output=True)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- repository fixture -------------------------------------------------------------------
    def write(self, rel, text="", mode=None):
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        if mode:
            os.chmod(path, mode)
        return path

    def build_repo(self):
        os.makedirs(self.repo)
        git(self.repo, "init", "-q")
        self.write(".gitignore", "target/\n*.tfstate\n*.tfstate.backup\noverride.tf\noverride.tf.json\n*_override.tf\n*_override.tf.json\n")
        shutil.copy(os.path.join(REAL_REPO, "Dockerfile"), os.path.join(self.repo, "Dockerfile"))
        self.write("infra/terraform/modules/runtime/compute.tf", 'runtime_platform {\n  cpu_architecture = "X86_64"\n}\n')
        self.write("infra/terraform/environments/course.tfvars", 'environment = "course"\n')
        self.write("infra/terraform/versions.tf", "# root\n")
        self.write("infra/terraform/deployer/versions.tf", "# deployer\n")
        self.write("docs/agent-runs/phase-04/xml-repair-logback.xml", "<configuration/>\n")
        self.write("project/build.properties", "sbt.version=1.10.7\n")
        self.commit("fixture")
        self.write_state()  # ignored: the live local state file of the fixture stack

    # ---- the live local state file (ignored by git) -----------------------------------------------
    STATE_REL = "infra/terraform/terraform.tfstate"

    def state_path(self):
        return os.path.join(self.repo, self.STATE_REL)

    def write_state(self, lineage=STATE_LINEAGE, serial=STATE_SERIAL, extra=None):
        document = {"version": 4, "terraform_version": "1.13.5", "serial": serial, "lineage": lineage, "outputs": {}, "resources": []}
        if extra:
            document.update(extra)
        path = self.state_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        return path

    def state_identity(self):
        """Hand-written reader (independent of the scripts): lineage, serial and the sha256 of the file bytes."""
        with open(self.state_path(), "rb") as handle:
            data = handle.read()
        document = json.loads(data)
        return {"present": True, "lineage": document["lineage"], "serial": document["serial"], "sha256": sha256_bytes(data)}

    def tree_sha(self, commit=None):
        """The source_tree_sha256 the scripts compute for a commit: git archive of the Terraform root, the generated
        backend binding to the live state file, then state_bind.py tree-hash."""
        commit = commit or self.head()
        dest = tempfile.mkdtemp(prefix="sc-tree-", dir=self.tmp)
        archive = subprocess.run(["git", "-C", self.repo, "archive", "--format=tar", commit, "infra/terraform"], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", dest], input=archive, check=True)
        root = os.path.join(dest, "infra", "terraform")
        lib = os.path.join(SCRIPTS_DIR, "lib", "state_bind.py")
        subprocess.run([sys.executable, "-I", lib, "write-binding", "--root", root, "--state", os.path.realpath(self.state_path())], check=True, capture_output=True)
        return subprocess.run([sys.executable, "-I", lib, "tree-hash", "--root", root], check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, message="change"):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", message)
        return self.head()

    def head(self):
        return git(self.repo, "rev-parse", "HEAD")

    def use_config(self, **overrides):
        """Point the scripts at a fixture copy of release.conf (SCHOLARCHAIN_CONFIG_FILE, the documented
        test-only mechanism); pinned settings cannot be changed through environment variables."""
        with open(os.path.join(SCRIPTS_DIR, "config", "release.conf"), encoding="utf-8") as handle:
            text = handle.read()
        for key, value in overrides.items():
            text, count = re.subn(r"^%s=.*$" % key, lambda _m, k=key, v=value: "%s=%s" % (k, v), text, flags=re.M)
            assert count == 1, key
        path = os.path.join(self.tmp, "fixture-release.conf")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.config_file = path
        return path

    # ---- environment and runners --------------------------------------------------------------
    def env(self, **extra):
        path = [self.bin, os.path.dirname(sys.executable)]
        shellcheck = shutil.which("shellcheck")
        if shellcheck:
            path.append(os.path.dirname(shellcheck))
        path += ["/usr/bin", "/bin", "/usr/sbin", "/sbin"]
        env = {
            "PATH": ":".join(path),
            "HOME": self.tmp,
            "TMPDIR": self.tmp,
            "LC_ALL": "C",
            "SCHOLARCHAIN_REPO_ROOT": self.repo,
            "FAKE_LOG": self.log,
            "SCHOLARCHAIN_TIMEOUT_LOG": self.timeout_log,
            "JAVA_HOME": self.jdk,
            "FAKE_ACCOUNT_ID": FAKE_ACCOUNT,
            "AWS_SECRET_ACCESS_KEY": FAKE_SECRET,
            "AWS_SESSION_TOKEN": FAKE_TOKEN,
            "AWS_ACCESS_KEY_ID": "AKIAFAKEFAKEFAKEFAKE",
        }
        if getattr(self, "config_file", None):
            env["SCHOLARCHAIN_CONFIG_FILE"] = self.config_file
        env.update(extra)
        return {k: v for k, v in env.items() if v is not None}

    def run_script(self, name, *args, **extra_env):
        completed = subprocess.run(
            ["bash", os.path.join(SCRIPTS_DIR, name)] + list(args),
            env=self.env(**extra_env),
            capture_output=True,
            text=True,
            timeout=300,
            cwd=self.tmp,
        )
        return Result(completed)

    def calls(self, tool=None):
        entries = []
        with open(self.log, encoding="utf-8") as handle:
            for line in handle:
                name, args, _profile = line.rstrip("\n").split("\t")
                entries.append((name, args))
        if tool:
            entries = [e for e in entries if e[0] == tool]
        return entries

    def raw_calls(self):
        with open(self.log, encoding="utf-8") as handle:
            return [line.rstrip("\n").split("\t") for line in handle]

    def sbt_env_lines(self):
        path = self.log + ".sbtenv"
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as handle:
            return [line.rstrip("\n") for line in handle]

    def mutating_calls(self):
        """Calls that would change cloud state or push/apply; terraform version/plan/show/init are not."""
        found = []
        for name, args in self.calls():
            words = args.split()
            if name == "terraform" and ("apply" in words or "destroy" in words or "-destroy" in words):
                found.append((name, args))
            elif name == "docker" and words[:1] in (["push"], ["login"]):
                found.append((name, args))
            elif name == "aws" and words[:2] in (["ecr", "get-login-password"], ["s3", "cp"]):
                found.append((name, args))
        return found

    def timeout_helper_lines(self):
        with open(self.timeout_log, encoding="utf-8") as handle:
            return [line.rstrip("\n") for line in handle]

    # ---- approval records, plans, manifests ---------------------------------------------------
    def make_plan(self, content=b"fake-plan-bytes\n", name="plan.tfplan"):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as handle:
            handle.write(content)
        return path, sha256_bytes(content)

    def approval_text(self, plan_sha=None, commit=None, account=None, region=REGION, omit=(), extra="", prespend_sha=None, stage="runtime-apply", receipt_sha=None, environment=ENVIRONMENT):
        """A synthetic approval record. A push record names NO plan: its plan and receipt lines are absent."""
        values = {
            "APPROVED_STAGE": stage,
            "APPROVED_COMMIT": commit or self.head(),
            "APPROVED_ACCOUNT_SHA256": account or account_hash(),
            "APPROVED_REGION": region,
            "APPROVED_ENVIRONMENT": environment,
            "APPROVED_PRESPEND_SHA256": prespend_sha or SHA_A,
        }
        if stage != "push":
            values["APPROVED_PLAN_SHA256"] = plan_sha or SHA_A
            values["APPROVED_RECEIPT_SHA256"] = receipt_sha or SHA_A
        lines = ["# Synthetic approval record for tests", "Some prose that mentions APPROVED_PLAN_SHA256 mid-line only."]
        for key, value in values.items():
            if key not in omit:
                lines.append("%s=%s" % (key, value))
        return "\n".join(lines) + "\n" + extra

    def write_approval(self, text, name="human-gate.md"):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def write_release_manifest(self, **overrides):
        commit = overrides.pop("commit", self.head())
        manifest = {
            "schema": "scholarchain.release-manifest.v1",
            "commit": commit,
            "dirty": False,
            "status": "complete",
            "image_tag": commit,
            "image_platform": "linux/amd64",
            "ecs_architecture": "linux/amd64",
            "arch_gate": {"passed": True, "detail": "synthetic"},
            "images": [
                {"service": s, "image": "scholarchain-%s:%s" % (s, commit), "status": "built", "os_arch": "linux/amd64", "local_image_id": fake_image_id("scholarchain-%s:%s" % (s, commit))}
                for s in SERVICES
            ],
        }
        manifest.update(overrides)
        path = os.path.join(self.repo, "target", "release", self.head(), "release-manifest.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle)
        return path

    def write_deploy_manifest(self, revision=None, digests=None):
        revision = revision or ("c" * 40)
        manifest = {
            "schema": "scholarchain.deploy-manifest.v1",
            "image_revision": revision,
            "images": [
                {"service": s, "repository": "scholarchain-course/%s" % s, "tag": revision, "registry_digest": (digests or {}).get(s, "sha256:" + SHA_A)}
                for s in SERVICES
            ],
        }
        path = os.path.join(self.tmp, "previous-deploy-manifest.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle)
        return path

    def write_show_json(self, changes, account=FAKE_ACCOUNT, region=REGION, image_revision=None, name="show.json", text=None, environment=ENVIRONMENT, project=PROJECT, extra_changes=None):
        """A `terraform show -json` fixture: planned variables, the aws provider region reference and changes.
        `extra_changes` are full resource_change dicts (with before/after) appended after `changes`."""
        variables = {"aws_account_id": {"value": account}, "aws_region": {"value": region}, "environment": {"value": environment}, "project": {"value": project}}
        if image_revision:
            variables["image_revision"] = {"value": image_revision}
        document = {
            "format_version": "1.2",
            "variables": variables,
            "configuration": {"provider_config": {"aws": {"name": "aws", "expressions": {"region": {"references": ["var.aws_region", "var.aws_region"]}}}}},
            "resource_changes": [{"address": a, "type": t, "change": {"actions": acts}} for a, t, acts in changes] + list(extra_changes or []),
        }
        if text:
            document["_note"] = text
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        return path

    # ---- pre-spend and plan receipts ----------------------------------------------------------
    def write_prespend(self, name="prespend.json", **overrides):
        document = {
            "schema": "scholarchain.prespend-receipt.v1",
            "monitoring_confirmed_active": True,
            "cost_snapshot_utc": utc_hours_ago(1),
            "reported_spend_usd": 5,
            "anthropic_spend_to_date_usd": 0.5,
            "voyage_spend_to_date_usd": 0,
            "unreported_usage_allowance_usd": 1,
            "reserves_usd": 6,
            # 25 - (5 + 0.5 + 0) - 1 - 6 = 12.5: the most the ceiling arithmetic allows (PRESPEND_PROJECT_CEILING_USD = 25)
            "remaining_headroom_usd": 12.5,
        }
        for key, value in overrides.items():
            if value is MISSING:
                document.pop(key, None)
            else:
                document[key] = value
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        with open(path, "rb") as handle:
            return path, sha256_bytes(handle.read())

    def write_plan_receipt(self, plan_path, plan_sha, **overrides):
        receipt = {
            "schema": "scholarchain.plan-receipt.v2",
            "purpose": "deploy-plan",
            "created_utc": utc_hours_ago(0),
            "env": ENVIRONMENT,
            "commit": self.head(),
            "scripts_commit": self.head(),
            "clean": True,
            "region": REGION,
            "account_sha256": account_hash(),
            "terraform_version": "1.13.5",
            "planned_environment": ENVIRONMENT,
            "planned_project": PROJECT,
            "source_tree_sha256": self.tree_sha(self._tree_commit(overrides)),
            "state": self.state_identity(),
            "image_revision": None,
            "plan_sha256": plan_sha,
            "actions": [],  # a real receipt always lists every non-no-op action (address, type, "+"-joined actions)
        }
        for key, value in overrides.items():
            if value is MISSING:
                receipt.pop(key, None)
            else:
                receipt[key] = value
        path = plan_path + ".receipt.json"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(receipt, handle)
        return path

    def _tree_commit(self, overrides):
        """The commit whose source the receipt describes: the overridden commit when it exists, else HEAD."""
        candidate = overrides.get("commit")
        if isinstance(candidate, str):
            probe = subprocess.run(["git", "-C", self.repo, "cat-file", "-e", candidate + "^{commit}"], capture_output=True)
            if probe.returncode == 0:
                return candidate
        return self.head()

    def receipt_sha(self, plan_path):
        with open(plan_path + ".receipt.json", "rb") as handle:
            return sha256_bytes(handle.read())

    def write_push_record(self, commit=None, digests=None, **overrides):
        """A synthetic push record (hand-written schema) for the four repositories of this commit."""
        commit = commit or self.head()
        record = {
            "schema": "scholarchain.push-record.v1",
            "commit": commit,
            "account_sha256": account_hash(),
            "region": REGION,
            "environment": ENVIRONMENT,
            "run_id": "fixture-run",
            "pushed_utc": utc_hours_ago(0),
            "images": [
                {
                    "service": s,
                    "repository": "scholarchain-course/%s" % s,
                    "tag": commit,
                    "pushed_digest": (digests or {}).get(s) or registry_digest(s, commit),
                    "local_image_id": fake_image_id("scholarchain-%s:%s" % (s, commit)),
                }
                for s in SERVICES
            ],
        }
        for key, value in overrides.items():
            if value is MISSING:
                record.pop(key, None)
            else:
                record[key] = value
        path = os.path.join(self.repo, "target", "release", self.head(), "push-record.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(record, handle)
        return path

    @staticmethod
    def plan_file_of(result):
        """The plan path plan.sh printed as `PLAN-FILE: <path>` (a fresh run directory per run)."""
        for line in result.stdout.splitlines():
            if line.startswith("PLAN-FILE: "):
                return line[len("PLAN-FILE: "):]
        raise AssertionError("no PLAN-FILE line in: " + result.stdout[-400:])

    def install_git_wrapper(self, mode):
        """A `git` earlier on PATH that breaks only `status`: mode "fail" exits 128, "garbage" prints junk."""
        real = shutil.which("git")
        body = '#!/bin/bash\nfor a in "$@"; do\n  if [ "$a" = status ]; then\n'
        body += '    echo "fatal: simulated failure" >&2; exit 128\n' if mode == "fail" else '    printf "garbage-without-structure"; exit 0\n'
        body += '  fi\ndone\nexec "%s" "$@"\n' % real
        write_exec(os.path.join(self.bin, "git"), body)
