"""R1 route-ownership assertion (infra/terraform/tests/phase12b.tftest.hcl) stays effective.

Uses the real terraform 1.13.5 on a temp fixture (mock providers, no AWS call): the clean fixture passes; a
route or route-table resource outside modules/network/ and outside spikes/ makes the run fail with the R1
message; the same resource under spikes/ is accepted; a VALID route inside modules/network/ is accepted and
the run must SUCCEED (a skip is not a pass). The real tree is never modified.

F10: the fixture is built ONLY from `git ls-files infra/terraform` (tracked sources; the working-tree bytes of
tracked files, so the repaired test file is included). Ignored or untracked local files (private tfvars,
raw plan JSON, state, plan binaries, .terraform) are never copied. Terraform working metadata is isolated in a
temp TF_DATA_DIR. Providers come only from a read-only -plugin-dir that points at the provider binaries (never a
symlink of the whole .terraform directory) or from a network init; if neither works the provider-dependent
tests are reported as SKIPPED, not passed.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from helpers import REAL_REPO

TF_REL = "infra/terraform"
# N3: the Terraform executable honours TERRAFORM_BIN (as the scripts do); otherwise the one on PATH. With
# TERRAFORM_BIN set and no terraform on PATH the provider-backed cases still run (they do not skip).
TF_BIN = os.environ.get("TERRAFORM_BIN") or "terraform"
R1 = "R1 requires every authored route and route-table resource to stay inside"
BASE_ENV = {
    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    "HOME": os.environ.get("HOME", "/"),  # tfenv resolves the pinned version from HOME
    "AWS_EC2_METADATA_DISABLED": "true",
    "AWS_CONFIG_FILE": "/dev/null",
    "AWS_SHARED_CREDENTIALS_FILE": "/dev/null",
    "TF_IN_AUTOMATION": "1",
    "TF_INPUT": "0",
    "CHECKPOINT_DISABLE": "1",
}
VALID_INSIDE_ROUTE = (
    'resource "aws_route" "inside_only_for_the_r1_test" {\n'
    "  route_table_id         = aws_route_table.public.id\n"
    '  destination_cidr_block = "192.0.2.0/24"\n'
    "  gateway_id             = aws_internet_gateway.course.id\n"
    "}\n"
)


def tracked_paths(repo, rel):
    """Repository-relative paths git tracks under rel (NUL-delimited, so odd names are safe)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    completed = subprocess.run(["git", "-C", repo, "ls-files", "-z", "--", rel], capture_output=True, env=env)
    if completed.returncode != 0:
        raise unittest.SkipTest("not a git work tree: the tracked-source fixture cannot be built (skipped, not passed)")
    return [p for p in completed.stdout.decode("utf-8", errors="surrogateescape").split("\0") if p]


def build_fixture(repo, rel, dest):
    """Copy ONLY tracked sources of repo/rel into dest/<basename(rel)>; returns the fixture root."""
    root = os.path.join(dest, os.path.basename(rel))
    for path in tracked_paths(repo, rel):
        source = os.path.join(repo, path)
        if not os.path.isfile(source):
            continue  # tracked but deleted in the working tree
        target = os.path.join(dest, os.path.relpath(path, os.path.dirname(rel)))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(source, target)
    return root


def provider_plugin_dir():
    """The installed provider binaries (a read-only plugin directory), or None."""
    candidate = os.path.join(REAL_REPO, TF_REL, ".terraform", "providers")
    return candidate if os.path.isdir(candidate) else None


def terraform_version():
    try:
        out = subprocess.run([TF_BIN, "version", "-json"], capture_output=True, text=True, env=BASE_ENV, timeout=60).stdout
        return json.loads(out)["terraform_version"]
    except Exception:  # noqa: BLE001
        return None


class FixtureBuilderTests(unittest.TestCase):
    """The fixture holds tracked sources only; synthetic ignored private files are absent (no terraform needed)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-r1-builder-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(os.path.join(self.repo, "infra", "terraform", "modules", "network"))
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        subprocess.run(["git", "-C", self.repo, "init", "-q"], check=True, env=env)
        self.write(".gitignore", "*.local.tfvars\nplan.json\n.terraform/\n*.tfstate*\n*.tfplan\n")
        self.write("infra/terraform/main.tf", "# tracked\n")
        self.write("infra/terraform/modules/network/main.tf", "# tracked module\n")
        self.write("infra/terraform/tests/phase12b.tftest.hcl", "# committed version\n")
        subprocess.run(["git", "-C", self.repo, "add", "-A"], check=True, env=env)
        subprocess.run(
            ["git", "-C", self.repo, "-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "x"], check=True, env=env
        )
        # Local, ignored or untracked material under the Terraform root.
        self.write("infra/terraform/zz.local.tfvars", 'aws_account_id = "123456789012"\n')
        self.write("infra/terraform/plan.json", '{"variables": {"secret": "x"}}\n')
        self.write("infra/terraform/.terraform/providers/x", "provider\n")
        self.write("infra/terraform/terraform.tfstate", "{}\n")
        self.write("infra/terraform/course.tfplan", "plan\n")
        self.write("infra/terraform/untracked-new.tf", "# untracked but not ignored\n")
        # The repaired test file: a tracked file modified in the working tree.
        self.write("infra/terraform/tests/phase12b.tftest.hcl", "# repaired working-tree version\n")

    def write(self, rel, text):
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write(text)

    def files_of(self, root):
        found = []
        for base, _dirs, names in os.walk(root):
            for name in names:
                found.append(os.path.relpath(os.path.join(base, name), root))
        return sorted(found)

    def test_only_tracked_sources_are_copied(self):
        dest = os.path.join(self.tmp, "fixture")
        os.makedirs(dest)
        root = build_fixture(self.repo, TF_REL, dest)
        self.assertEqual(self.files_of(root), ["main.tf", "modules/network/main.tf", "tests/phase12b.tftest.hcl"])

    def test_synthetic_ignored_private_files_are_absent_from_the_fixture(self):
        dest = os.path.join(self.tmp, "fixture")
        os.makedirs(dest)
        root = build_fixture(self.repo, TF_REL, dest)
        for absent in ("zz.local.tfvars", "plan.json", ".terraform", "terraform.tfstate", "course.tfplan", "untracked-new.tf"):
            self.assertFalse(os.path.exists(os.path.join(root, absent)), absent)

    def test_the_repaired_working_tree_test_file_content_is_used(self):
        dest = os.path.join(self.tmp, "fixture")
        os.makedirs(dest)
        root = build_fixture(self.repo, TF_REL, dest)
        with open(os.path.join(root, "tests", "phase12b.tftest.hcl")) as handle:
            self.assertEqual(handle.read(), "# repaired working-tree version\n")

    def test_a_fixture_of_the_real_repository_holds_only_tracked_files(self):
        dest = tempfile.mkdtemp(prefix="sc-r1-real-")
        self.addCleanup(shutil.rmtree, dest, ignore_errors=True)
        root = build_fixture(REAL_REPO, TF_REL, dest)
        tracked = {os.path.relpath(p, TF_REL) for p in tracked_paths(REAL_REPO, TF_REL)}
        copied = set(self.files_of(root))
        self.assertTrue(copied)
        self.assertTrue(copied <= tracked, "copied but not tracked: %s" % sorted(copied - tracked)[:5])
        for name in copied:
            self.assertFalse(name.endswith(".local.tfvars"), name)
            self.assertNotIn(".terraform/", name + "/")
            self.assertFalse(name.endswith((".tfstate", ".tfplan", "plan.json")), name)


class RouteOwnershipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if terraform_version() != "1.13.5":
            raise unittest.SkipTest("terraform 1.13.5 not available")

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-r1-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.data_dir = os.path.join(self.tmp, "tfdata")
        os.makedirs(self.data_dir)
        self.root = build_fixture(REAL_REPO, TF_REL, self.tmp)
        plugins = provider_plugin_dir()
        args = ["init", "-backend=false", "-input=false", "-lockfile=readonly"]
        if plugins:
            args.append("-plugin-dir=" + plugins)  # provider binaries only, read-only use; no symlinked .terraform
        init = self.tf(*args)
        if init.returncode != 0:
            self.skipTest("providers unavailable (no local provider directory and no network init): " + init.stderr[-200:])

    def tf(self, *args):
        env = dict(BASE_ENV, TF_DATA_DIR=self.data_dir)
        return subprocess.run([TF_BIN, "-chdir=" + self.root] + list(args), capture_output=True, text=True, env=env, timeout=900)

    def r1(self):
        return self.tf("test", "-no-color", "-filter=tests/phase12b.tftest.hcl")

    def add(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write(text)

    def test_the_fixture_is_isolated_from_the_real_checkout(self):
        self.assertFalse(os.path.exists(os.path.join(self.root, ".terraform")), "no .terraform in the fixture source")
        self.assertTrue(os.listdir(self.data_dir), "working metadata lives in the isolated TF_DATA_DIR")
        self.assertFalse(os.path.islink(self.data_dir))
        self.assertNotEqual(os.path.realpath(self.data_dir), os.path.realpath(os.path.join(REAL_REPO, TF_REL, ".terraform")))

    def test_clean_fixture_passes(self):
        result = self.r1()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("dashboard_metric_shapes_and_route_ownership", result.stdout)

    def test_stray_route_outside_network_module_still_fails_r1(self):
        for rel, body in (
            ("stray/route.tf", 'resource "aws_route" "stray" {}\n'),
            ("modules/other/rt.tf", 'resource "aws_route_table" "stray" {}\n'),
            ("stray2/assoc.tf", 'resource "aws_route_table_association" "stray" {}\n'),
        ):
            with self.subTest(rel):
                self.add(rel, body)
                result = self.r1()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(R1, result.stdout + result.stderr)
                os.remove(os.path.join(self.root, rel))
        self.assertEqual(self.r1().returncode, 0, "back to clean")

    def test_route_resource_under_spikes_is_accepted(self):
        self.add("spikes/another-spike/network.tf", 'resource "aws_route" "spike_only" {}\n')
        result = self.r1()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_valid_route_inside_modules_network_is_accepted_and_the_run_succeeds(self):
        """A skip is not a pass: this asserts a SUCCESSFUL terraform test run with a valid in-module route."""
        self.add("modules/network/extra_routes.tf", VALID_INSIDE_ROUTE)
        result = self.r1()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn(R1, result.stdout + result.stderr)
        self.assertIn("dashboard_metric_shapes_and_route_ownership", result.stdout)
        self.assertRegex(result.stdout, r"Success!\s+\d+ passed, 0 failed")

    def test_synthetic_ignored_private_files_added_next_to_the_real_checkout_do_not_reach_a_new_fixture(self):
        """Fixture rebuilt from a throwaway git checkout that holds ignored private files: they are absent."""
        scratch = tempfile.mkdtemp(prefix="sc-r1-scratch-")
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        repo = os.path.join(scratch, "repo")
        os.makedirs(os.path.join(repo, TF_REL))
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        subprocess.run(["git", "-C", repo, "init", "-q"], check=True, env=env)
        with open(os.path.join(repo, ".gitignore"), "w") as handle:
            handle.write("*.local.tfvars\nplan.json\n")
        with open(os.path.join(repo, TF_REL, "main.tf"), "w") as handle:
            handle.write("# tracked\n")
        subprocess.run(["git", "-C", repo, "add", "-A"], check=True, env=env)
        for name in ("zz.local.tfvars", "plan.json"):
            with open(os.path.join(repo, TF_REL, name), "w") as handle:
                handle.write("private\n")
        dest = os.path.join(scratch, "fixture")
        os.makedirs(dest)
        root = build_fixture(repo, TF_REL, dest)
        self.assertEqual(sorted(os.listdir(root)), ["main.tf"])


if __name__ == "__main__":
    unittest.main()
