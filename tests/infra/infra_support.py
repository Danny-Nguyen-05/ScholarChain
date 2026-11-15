"""Support for the independent Phase 13C infrastructure tests (test-engineer, tests/infra/**).

What this module does
  * builds a SCRATCH COPY of one Terraform root (the working tree, so uncommitted edits are included) under a
    temporary directory, never touching the repository: every mutation case edits only that copy;
  * runs `terraform init` offline from the provider binaries the check.sh terraform gate already installed in the
    repository root (`-plugin-dir`, `-lockfile=readonly`), with an isolated TF_DATA_DIR;
  * produces two machine-readable views of the copy:
      - PLAN JSON: a real `terraform plan` with the real AWS provider in a no-network configuration (fake static
        credentials, skip_* flags, a black-holed HTTPS proxy so any accidental network call fails fast). This is the
        provider's own computed view, so `tags_all`, exact resources and static attribute values are real;
      - STATE JSON: the post-apply state of a mock_provider run (`terraform test -json -verbose`), used for values
        that only exist after apply (IAM policies that embed resource ARNs, resource-to-resource attachments);
  * runs the root's EXISTING `terraform test` suite on the copy, for the mutation matrix.

No AWS call is possible: the plan uses fake credentials and a closed proxy, the state view uses mock providers.
A root that was not initialised by the terraform gate makes the tests FAIL with a clear message (never skip).

Expectations in the test modules are hand-derived from the root READMEs, the Phase 12 review findings and the
Phase 13 plan; the Terraform sources are not re-implemented here.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import hcl_text

REPO = Path(os.environ.get("SCHOLARCHAIN_REPO_ROOT") or Path(__file__).resolve().parents[2])
HERE = Path(__file__).resolve().parent
TFTESTS = HERE / "tftests"
TF_BIN = os.environ.get("TERRAFORM_BIN") or "terraform"
REQUIRED_TF_VERSION = "1.13.5"
BLACKHOLE_PROXY = "http://127.0.0.1:9"  # the discard port: nothing listens, so any network attempt fails fast
EVIDENCE_FILE = os.environ.get("SC_INFRA_EVIDENCE_FILE")  # optional JSON-lines sink for mutation results

# Layout of each root inside its scratch copy. Relative paths in the root (../../../../scripts, ../../../../docs)
# must resolve, so the few repository files the root reads are copied at the same relative positions.
ROOTS = {
    "spike": {
        "rel": "infra/terraform/spikes/emr-spark-isolated",
        "extras": [
            "scripts/phase12d-spike/emr",
            "docs/agent-runs/phase-12/evidence/12d-portable-runtime/g1-upstream-inputs.tgz",
            "docs/agent-runs/phase-12/evidence/12d-portable-runtime/build/relocated-g1-config.json",
        ],
        "vars": {
            "account_id": "111122223333",
            "owner": "example-owner",
            "expiration_date": "2026-11-04",
            "permissions_boundary_arn": "arn:aws:iam::111122223333:policy/scholarchain-spike-emr-boundary",
            "deployer_role_arn": "arn:aws:iam::111122223333:role/scholarchain-deployer",
            "runtime_tgz_path": "tests/fixtures/runtime-fixture.bin",
            "runtime_tgz_sha256": "3cdbba1642f4fa67dee2a3d68b95263c0155f21e6c05735ce428ecac875ab782",
            "inputs_tgz_path": "../../../../docs/agent-runs/phase-12/evidence/12d-portable-runtime/g1-upstream-inputs.tgz",
            "g1_config_template_path": "../../../../docs/agent-runs/phase-12/evidence/12d-portable-runtime/build/relocated-g1-config.json",
        },
        "snapshot": "spike_snapshot.tftest.hcl",
    },
    "deployer": {
        "rel": "infra/terraform/deployer",
        "extras": [],
        "vars": {
            "account_id": "111122223333",
            "operator_principal_arn": "arn:aws:iam::111122223333:user/example-operator",
            "owner": "example-owner",
            # Decision 14-6 changed the deployer default to ["phase14-main"]. The Phase 13 suites (test_deployer_hardening,
            # test_iam_items_13c) are the retained spike-era evidence and assert spike-emr names, tags and bounds, so they
            # pin the set explicitly. The phase14-main checks (test_phase14_main.py) use the "deployer14" root below.
            "enabled_permission_sets": '["spike-emr"]',
        },
        "snapshot": "deployer_snapshot.tftest.hcl",
    },
}

# The main root is only used for its installed providers and lock file (the EMR module wrapper plans against them).
ROOTS["main"] = {"rel": "infra/terraform", "extras": [], "vars": {}, "snapshot": None}

# Phase 14A (decision 14-6): the deployer root with its DEFAULT permission set (phase14-main), no enabled_permission_sets override.
ROOTS["deployer14"] = {
    "rel": "infra/terraform/deployer",
    "extras": [],
    "vars": {
        "account_id": "111122223333",
        "operator_principal_arn": "arn:aws:iam::111122223333:user/example-operator",
        "owner": "example-owner",
    },
    "snapshot": None,  # plan view only: the snapshot file pins spike-emr for the Phase 13 suites
}

# Phase 14A: the MAIN root planned offline with the real provider (the root declares no data source, so a plan needs no AWS
# call). The provider block reads a named profile, which the offline override must null; all values are synthetic.
ROOTS["main14"] = {
    "rel": "infra/terraform",
    "extras": [],
    "vars": {
        "aws_account_id": "111122223333",
        "aws_region": "us-east-2",
        "aws_profile": "offline-placeholder-profile",
        "availability_zones": '["us-east-2a", "us-east-2b"]',
        "deployment_trusted_principal_arn": "arn:aws:iam::111122223333:role/example-architect",
        "budget_limit_usd": "50",
    },
    "snapshot": None,
    "override_profile_null": True,
}

# Phase 14B replan (W5a): the deployer root with its default set and the three operator roles ENABLED (synthetic run prefix).
ROOTS["deployer14ops"] = {
    "rel": "infra/terraform/deployer",
    "extras": [],
    "vars": {
        "account_id": "111122223333",
        "operator_principal_arn": "arn:aws:iam::111122223333:user/example-operator",
        "owner": "example-owner",
        "operator_roles_enabled": "true",
        "operator_run_prefix": "run-20261115",
    },
    "snapshot": None,
}

# Phase 14B replan (W3): the billing-bootstrap root (the account-level AWS Budget), planned offline with the real provider. Synthetic
# account ID and profile; the provider block's profile and allowed_account_ids are nulled in the scratch override.
ROOTS["billing"] = {
    "rel": "infra/terraform/billing-bootstrap",
    "extras": [],
    "vars": {
        "aws_account_id": "111122223333",
        "aws_profile": "offline-placeholder-profile",
        "aws_region": "us-east-2",
        "budget_name": "synthetic-project-budget",
        "enable_budget": "true",
        "budget_notification_emails": '["synthetic@example.invalid"]',
        "project_period_start_utc": "2026-10-01_00:00",
        "project_period_end_utc": "2027-01-01_00:00",
    },
    "snapshot": None,
    "override_profile_null": True,
}

OFFLINE_PROVIDER_OVERRIDE = """\
# Written by tests/infra/infra_support.py into a SCRATCH copy only. Terraform merges *_override.tf files into the
# provider block, so the root's own configuration is planned unchanged except that the provider cannot reach AWS.
provider "aws" {
  access_key                  = "offline"
  secret_key                  = "offline"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  allowed_account_ids         = null
}
"""

COPY_IGNORE = shutil.ignore_patterns(
    ".terraform", "*.tfstate", "*.tfstate.*", "*.tfplan", "*.plan", "plan.json", "crash.log", "crash.*.log",
    "*.tfvars", "*.tfvars.json", "__pycache__",
)


class InfraNotReady(AssertionError):
    """A precondition (terraform 1.13.5, initialised providers) is missing: a FAILURE, never a skip."""


class MutationAnchorMissing(AssertionError):
    """A mutation could not find its anchor text: the Terraform source moved; update the mutation, do not skip it."""


# ---------------------------------------------------------------------------------------------------------------
# environment
# ---------------------------------------------------------------------------------------------------------------

def tf_env(data_dir):
    """A closed environment: no ambient AWS or Terraform settings, no profile, no config files, closed proxy."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("AWS_", "TF_")) and "proxy" not in k.lower()}
    env.update({
        "AWS_EC2_METADATA_DISABLED": "true",
        "AWS_CONFIG_FILE": "/dev/null",
        "AWS_SHARED_CREDENTIALS_FILE": "/dev/null",
        "TF_IN_AUTOMATION": "1",
        "TF_INPUT": "0",
        "CHECKPOINT_DISABLE": "1",
        "TF_DATA_DIR": str(data_dir),
        "HTTPS_PROXY": BLACKHOLE_PROXY,
        "HTTP_PROXY": BLACKHOLE_PROXY,
        "https_proxy": BLACKHOLE_PROXY,
        "http_proxy": BLACKHOLE_PROXY,
        "NO_PROXY": "",
        "no_proxy": "",
    })
    return env


def run(cmd, cwd, env, timeout=600):
    return subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout)


def terraform_version():
    try:
        out = subprocess.run([TF_BIN, "version", "-json"], capture_output=True, text=True, timeout=60,
                             env={k: v for k, v in os.environ.items() if not k.upper().startswith("TF_")}).stdout
        return json.loads(out)["terraform_version"]
    except Exception as exc:  # noqa: BLE001
        return "unavailable (%s)" % type(exc).__name__


def require_toolchain(root_kind):
    """Fail (not skip) with an actionable message unless terraform 1.13.5 and the root's providers are present."""
    version = terraform_version()
    if version != REQUIRED_TF_VERSION:
        raise InfraNotReady("terraform %s is required on PATH or in TERRAFORM_BIN; found %s" % (REQUIRED_TF_VERSION, version))
    providers = REPO / ROOTS[root_kind]["rel"] / ".terraform" / "providers"
    if not providers.is_dir():
        raise InfraNotReady(
            "root %s is not initialised (no %s). These tests reuse the providers that the check.sh terraform gate "
            "installs; run `scripts/check.sh --only terraform` (or `terraform init -backend=false` in that root) "
            "first. This is a failure, not a skip." % (ROOTS[root_kind]["rel"], providers))
    return providers


# ---------------------------------------------------------------------------------------------------------------
# scratch tree
# ---------------------------------------------------------------------------------------------------------------

class TfTree:
    """A scratch copy of one Terraform root. Never the repository."""

    def __init__(self, kind):
        self.kind = kind
        self.spec = ROOTS[kind]
        self.providers = require_toolchain(kind)
        self.base = Path(tempfile.mkdtemp(prefix="sc-infra-%s-" % kind))
        self.data_dir = self.base / "tfdata"
        self.data_dir.mkdir()
        self.root = self.base / self.spec["rel"]
        shutil.copytree(REPO / self.spec["rel"], self.root, ignore=COPY_IGNORE)
        for extra in self.spec["extras"]:
            src, dst = REPO / extra, self.base / extra
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst, ignore=COPY_IGNORE)
            else:
                shutil.copyfile(src, dst)
        override = OFFLINE_PROVIDER_OVERRIDE
        if self.spec.get("override_profile_null"):
            override = override.replace("  allowed_account_ids         = null\n", "  allowed_account_ids         = null\n  profile                     = null\n")
        (self.root / "zz_offline_override.tf").write_text(override)
        self._plan = None
        self._state = None
        self._initialised = False
        assert not str(self.root).startswith(str(REPO) + os.sep), "scratch tree must live outside the repository"

    # -- lifecycle ------------------------------------------------------------------------------------------

    def close(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- mutation helpers (edit only the scratch copy) -------------------------------------------------------

    def read(self, name):
        return (self.root / name).read_text()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        self._plan = self._state = None

    def add_file(self, name, text):
        if (self.root / name).exists():
            raise AssertionError("mutation file already exists: " + name)
        self.write(name, text)

    def replace(self, name, old, new, count=1):
        text = self.read(name)
        if old not in text:
            raise MutationAnchorMissing("anchor not found in %s (the source moved; update the mutation): %r" % (name, old))
        self.write(name, text.replace(old, new, count))

    def regex_sub(self, name, pattern, repl, count=1, flags=re.M):
        text = self.read(name)
        new, n = re.subn(pattern, repl, text, count=count, flags=flags)
        if n == 0:
            raise MutationAnchorMissing("pattern not found in %s (the source moved; update the mutation): %r" % (name, pattern))
        self.write(name, new)

    def replace_after(self, name, anchor, old, new):
        """Replace the first `old` that appears after `anchor` (scopes an edit to one statement)."""
        text = self.read(name)
        a = text.find(anchor)
        if a < 0:
            raise MutationAnchorMissing("anchor not found in %s (the source moved; update the mutation): %r" % (name, anchor))
        b = text.find(old, a)
        if b < 0:
            raise MutationAnchorMissing("%r not found after anchor %r in %s (the source moved; update the mutation)" % (old, anchor, name))
        self.write(name, text[:b] + new + text[b + len(old):])

    def strip_attribute_after(self, name, anchor, attribute):
        """Delete `attribute = <value>` (balanced, possibly multi-line) that first follows `anchor` in the file."""
        try:
            self.write(name, hcl_text.strip_attribute_after(self.read(name), anchor, attribute))
        except KeyError as exc:
            raise MutationAnchorMissing("%s in %s (the source moved; update the mutation)" % (exc.args[0], name))

    # -- terraform --------------------------------------------------------------------------------------------

    def tf(self, *args, timeout=600):
        return run([TF_BIN] + list(args), self.root, tf_env(self.data_dir), timeout=timeout)

    def init(self):
        if self._initialised:
            return
        done = self.tf("init", "-backend=false", "-input=false", "-lockfile=readonly", "-no-color",
                       "-plugin-dir=" + str(self.providers))
        if done.returncode != 0:
            raise InfraNotReady("offline terraform init failed in the scratch copy:\n" + done.stdout[-1500:] + done.stderr[-1500:])
        self._initialised = True

    def _var_args(self):
        args = []
        for key, value in self.spec["vars"].items():
            args += ["-var", "%s=%s" % (key, value)]
        return args

    def plan_json(self):
        """The provider's real offline plan of the copy, as parsed `terraform show -json` output (cached)."""
        if self._plan is None:
            self.init()
            planfile = self.base / "offline.tfplan"
            done = self.tf("plan", "-no-color", "-input=false", "-out=" + str(planfile), *self._var_args())
            if done.returncode != 0:
                raise AssertionError("offline terraform plan failed on the scratch copy (a mutation must still plan; "
                                     "the failure is in the harness or the source):\n" + done.stdout[-2500:] + done.stderr[-1500:])
            shown = self.tf("show", "-json", "-no-color", str(planfile))
            if shown.returncode != 0:
                raise AssertionError("terraform show -json failed:\n" + shown.stderr[-1500:])
            self._plan = json.loads(shown.stdout)
        return self._plan

    def plan_attempt(self, extra_vars=None, json_vars=None):
        """Run an offline plan with extra or overriding -var values and return the CompletedProcess (not cached):
        used to prove that a variable validation REFUSES a value. json_vars are passed as JSON text."""
        self.init()
        merged = dict(self.spec["vars"])
        args = []
        for key, value in merged.items():
            if key not in (extra_vars or {}) and key not in (json_vars or {}):
                args += ["-var", "%s=%s" % (key, value)]
        for key, value in (extra_vars or {}).items():
            args += ["-var", "%s=%s" % (key, value)]
        for key, value in (json_vars or {}).items():
            args += ["-var", "%s=%s" % (key, json.dumps(value))]
        return self.tf("plan", "-no-color", "-input=false", *args)

    def _snapshot_name(self):
        return "tests/zz_" + self.spec["snapshot"]

    def state_json(self):
        """Post-apply state of a mock_provider run (`snapshot` run block), as the `values` dict (cached)."""
        if self._state is None:
            self.init()
            target = self.root / self._snapshot_name()
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(TFTESTS / self.spec["snapshot"], target)
            try:
                done = self.tf("test", "-no-color", "-json", "-verbose", "-filter=" + self._snapshot_name())
            finally:
                target.unlink()
            state = None
            for line in done.stdout.splitlines():
                try:
                    message = json.loads(line)
                except ValueError:
                    continue
                if message.get("type") == "test_state" and message.get("@testrun") == "snapshot":
                    state = message["test_state"]
            if done.returncode != 0 or state is None:
                raise AssertionError("mock snapshot run failed on the scratch copy:\n" + done.stdout[-2500:] + done.stderr[-1500:])
            self._state = state
        return self._state

    def existing_tests(self):
        """Run the root's own committed `terraform test` files on the copy (not mine): a CompletedProcess."""
        self.init()
        filters = ["-filter=tests/" + p.name for p in sorted((self.root / "tests").glob("*.tftest.hcl")) if not p.name.startswith("zz_")]
        return self.tf("test", "-no-color", *filters)


# ---------------------------------------------------------------------------------------------------------------
# plan / state accessors
# ---------------------------------------------------------------------------------------------------------------

def managed_changes(plan):
    """address -> resource_change for managed resources (the plan's complete resource inventory)."""
    return {rc["address"]: rc for rc in plan.get("resource_changes", []) if rc.get("mode") == "managed"}


def after(plan, address):
    return managed_changes(plan)[address]["change"]["after"]


def config_resources(plan):
    return {r["address"]: r for r in plan["configuration"]["root_module"].get("resources", [])}


def config_refs(plan, address, attribute):
    expr = config_resources(plan)[address].get("expressions", {}).get(attribute, {})
    return expr.get("references", [])


def state_resources(state):
    """address -> values for the root module of a state document (no module is expected in these roots)."""
    return {r["address"]: r["values"] for r in state["root_module"].get("resources", [])}


def policy_statements(doc):
    """The statements of an IAM policy document (JSON text or dict) as a list of dicts."""
    if isinstance(doc, str):
        doc = json.loads(doc)
    statements = doc["Statement"]
    return [statements] if isinstance(statements, dict) else list(statements)


def as_list(value):
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def condition_pairs(statement):
    """Flatten a statement's Condition to [(operator, key, value-or-list)]."""
    pairs = []
    for operator, block in (statement.get("Condition") or {}).items():
        for key, value in block.items():
            pairs.append((operator, key, value))
    return pairs


def record_mutation(name, payload):
    """Append one JSON line to $SC_INFRA_EVIDENCE_FILE (when set) so the run keeps raw mutation evidence."""
    if not EVIDENCE_FILE:
        return
    with open(EVIDENCE_FILE, "a") as handle:
        handle.write(json.dumps(dict(payload, mutation=name), sort_keys=True) + "\n")


def tail(text, n=400):
    return text[-n:] if text else ""


class InfraTestCase(unittest.TestCase):
    """Base class: helper to assert a mutation is caught by a named check."""

    def assertCaught(self, failing, expected_checks, mutation):
        missing = [c for c in expected_checks if c not in failing]
        self.assertFalse(missing, "mutation %r was NOT caught by %s; checks that did fire: %s" % (mutation, missing, sorted(failing)))


if __name__ == "__main__":
    sys.exit("support module; run: python3 -m unittest discover -s tests/infra -v")


EMR_WRAPPER_VERSIONS = '''terraform {
  required_version = "= 1.13.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.44.0"
    }
  }
}
'''

EMR_WRAPPER_MAIN = '''provider "aws" {
  region = "us-east-2"
}

module "emr" {
  source = "./modules/emr"

  name_prefix             = "scholarchain-course"
  config                  = jsondecode(<<-EOT
%(config)s
  EOT
  )
  kms_key_arn             = "arn:aws:kms:us-east-2:111122223333:key/11111111-2222-3333-4444-555555555555"
  log_bucket              = "scholarchain-course-111122223333-logs"
  artifacts_bucket        = "scholarchain-course-111122223333-artifacts"
  aws_region              = "us-east-2"
  aws_account_id          = "111122223333"
  vpc_id                  = "vpc-0123456789abcdef0"
  subnet_id               = "subnet-0123456789abcdef0"
  security_group_id       = "sg-0123456789abcdef0"
  service_access_group_id = "sg-0123456789abcdef1"
  instance_profile_arn    = "arn:aws:iam::111122223333:instance-profile/emr-ec2"
  instance_role_arn       = "arn:aws:iam::111122223333:role/emr-ec2"
  instance_role_name      = "emr-ec2"
  service_role_arn        = "arn:aws:iam::111122223333:role/emr-service"
  tags = {
    course      = "CS441"
    project     = "ScholarChain"
    environment = "course"
    owner       = "example-owner"
  }
}
'''

EMR_BUCKET = "scholarchain-course-111122223333-artifacts"
EMR_DEFAULT_CONFIG = {
    "enabled": True,
    "runtime_reference": "phase12d-portable-runtime",
    "runtime_verified": True,
    "bootstrap_uri": "s3://%s/emr/bootstrap.sh" % EMR_BUCKET,
    "bootstrap_sha256": "a" * 64,
    "runtime_archive_uri": "s3://%s/emr/scholarchain-runtime.tgz" % EMR_BUCKET,
    "job_jar_uri": "s3://%s/emr/scholarchain-job.jar" % EMR_BUCKET,
    "job_jar_sha256": "b" * 64,
    "extra_artifacts": [{"uri": "s3://%s/emr/pipeline-step.sh" % EMR_BUCKET, "sha256": "c" * 64,
                         "dest": "/opt/scholarchain-spike/bin/pipeline-step.sh"}],
}


class EmrModuleTree(TfTree):
    """A scratch ROOT that calls a scratch COPY of infra/terraform/modules/emr with fixed synthetic inputs, so the module can
    be planned (real provider, no network) and applied against mocks without the 100-resource main root. Providers and the
    lock file come from the main root's terraform-gate init. Mutations edit `modules/emr/*.tf` of the copy."""

    def __init__(self, config=None):
        self.kind = "emrmodule"
        self.spec = {"rel": "wrapper", "extras": [], "vars": {}, "snapshot": "emr_module_snapshot.tftest.hcl"}
        self.providers = require_toolchain("main")
        self.base = Path(tempfile.mkdtemp(prefix="sc-infra-emrmodule-"))
        self.data_dir = self.base / "tfdata"
        self.data_dir.mkdir()
        self.root = self.base / "wrapper"
        self.root.mkdir()
        shutil.copytree(REPO / "infra/terraform/modules/emr", self.root / "modules" / "emr", ignore=COPY_IGNORE)
        shutil.copyfile(REPO / "infra/terraform/.terraform.lock.hcl", self.root / ".terraform.lock.hcl")
        merged = dict(EMR_DEFAULT_CONFIG)
        merged.update(config or {})
        self.config = merged
        (self.root / "versions.tf").write_text(EMR_WRAPPER_VERSIONS)
        (self.root / "main.tf").write_text(EMR_WRAPPER_MAIN % {"config": json.dumps(merged, indent=2)})
        (self.root / "zz_offline_override.tf").write_text(OFFLINE_PROVIDER_OVERRIDE)
        self._plan = None
        self._state = None
        self._initialised = False

    def existing_tests(self):
        """The module's own committed tests live in the main root (infra/terraform/tests/phase13c.tftest.hcl) and need the
        whole root; they are not run on the wrapper."""
        raise NotImplementedError("the module has no tests of its own; the main root's tests are not run on the wrapper")
