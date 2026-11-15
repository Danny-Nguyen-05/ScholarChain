"""Phase 14B pre-session item 4: scripts/lib/emr_service_policy.py renders emr_service_policy_json from
infra/terraform/environments/emr-service-policy.json.example and checks it like the Terraform validator does.

Hand-derived expectations, temp directories only, no AWS, no tfvars read. The account id is assembled from parts so no
12-digit literal is stored in this file.
"""
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest

from helpers import REAL_REPO, SCRIPTS_DIR

TOOL = os.path.join(SCRIPTS_DIR, "lib", "emr_service_policy.py")
EXAMPLE = os.path.join(REAL_REPO, "infra", "terraform", "environments", "emr-service-policy.json.example")
ACCOUNT = "".join(["4444", "5555", "6666"])  # synthetic
SIDS = [
    "CreateInTaggedNetwork", "CreateEMRTaggedInstancesAndVolumes", "ResourcesToLaunchEC2", "ManageEMRTaggedResources",
    "ManageTagsOnEMRTaggedResources", "CreateNetworkInterfaceNeededForPrivateSubnet", "TagOnCreateTaggedEMRResources",
    "ListActionsForEC2Resources", "CreateDefaultSecurityGroupWithEMRTags", "CreateDefaultSecurityGroupInVPCWithEMRTags",
    "TagOnCreateDefaultSecurityGroupWithEMRTags", "ManageSecurityGroups", "PassTheProjectInstanceRoleToEC2",
]


def run(args, env=None):
    base = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    base.update(env or {})
    return subprocess.run([sys.executable, "-I", TOOL] + args, capture_output=True, text=True, timeout=60, env=base)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-emrpol-")
        self.addCleanup(subprocess.run, ["rm", "-rf", self.tmp])
        self.out = os.path.join(self.tmp, "policy.tfvars")

    def render(self, extra=None, env=None, fmt="tfvars"):
        args = ["render", "--region", "us-east-2", "--environment", "course", "--out", self.out, "--format", fmt] + (extra or ["--account-env", "ACCT"])
        return run(args, env if env is not None else {"ACCT": ACCOUNT})


class RenderTests(Base):
    def test_the_example_has_the_reviewed_thirteen_statements_and_exactly_three_placeholder_kinds(self):
        with open(EXAMPLE, encoding="utf-8") as handle:
            text = handle.read()
        document = json.loads(text.replace("<region>", "r").replace("<12-digit-account-id>", "a").replace("<environment>", "e"))
        self.assertEqual([s["Sid"] for s in document["Statement"]], SIDS)
        leftovers = set(__import__("re").findall(r"<[^>]*>", text)) - {"<region>", "<12-digit-account-id>", "<environment>"}
        self.assertEqual(leftovers, set())

    def test_render_writes_a_private_tfvars_assignment_that_is_valid_json_with_the_13_statements(self):
        done = self.render()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("RESULT: PASS rendered and checked", done.stdout)
        self.assertNotIn(ACCOUNT, done.stdout + done.stderr, "the summary must not print the account id")
        with open(self.out, encoding="utf-8") as handle:
            text = handle.read()
        self.assertTrue(text.startswith("emr_service_policy_json = <<-EOT\n") and text.endswith("\nEOT\n"))
        document = json.loads(text[len("emr_service_policy_json = <<-EOT\n"):-len("EOT\n")])
        self.assertEqual([s["Sid"] for s in document["Statement"]], SIDS)
        self.assertEqual(document["Version"], "2012-10-17")
        self.assertIn("arn:aws:ec2:us-east-2:%s:subnet/*" % ACCOUNT, text)
        self.assertIn("arn:aws:iam::%s:role/scholarchain-course-emr-ec2" % ACCOUNT, text)
        self.assertNotIn("<", text.split("<<-EOT", 1)[1])
        self.assertEqual(stat.S_IMODE(os.stat(self.out).st_mode), 0o600)
        self.assertIn("sha256=" + hashlib.sha256(text.encode()).hexdigest(), done.stdout)

    def test_json_format_is_the_bare_document(self):
        done = self.render(fmt="json")
        self.assertEqual(done.returncode, 0, done.stderr)
        with open(self.out, encoding="utf-8") as handle:
            self.assertEqual(len(json.load(handle)["Statement"]), 13)

    def test_render_matches_the_substitution_the_terraform_tests_perform(self):
        # infra/terraform/tests/phase14a.tftest.hcl replaces the same three placeholders with replace(); the document must be identical.
        done = self.render(fmt="json")
        self.assertEqual(done.returncode, 0, done.stderr)
        with open(EXAMPLE, encoding="utf-8") as handle:
            direct = handle.read().replace("<region>", "us-east-2").replace("<12-digit-account-id>", ACCOUNT).replace("<environment>", "course")
        with open(self.out, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), json.loads(direct))

    def test_render_refuses_a_bad_account_region_environment_and_an_existing_or_symlinked_output(self):
        for env in ({"ACCT": "12345"}, {"ACCT": ACCOUNT + "0"}, {"ACCT": "abcdefghijkl"}, {}):
            with self.subTest(env=env):
                done = self.render(env=env)
                self.assertEqual(done.returncode, 2)
                self.assertFalse(os.path.exists(self.out))
        done = run(["render", "--region", "US EAST", "--environment", "course", "--account-id", ACCOUNT, "--out", self.out])
        self.assertEqual(done.returncode, 2)
        done = run(["render", "--region", "us-east-2", "--environment", "Course;", "--account-id", ACCOUNT, "--out", self.out])
        self.assertEqual(done.returncode, 2)
        self.assertEqual(self.render().returncode, 0)
        before = open(self.out, "rb").read()
        again = self.render()
        self.assertEqual(again.returncode, 2, "an existing output file is never overwritten")
        self.assertEqual(open(self.out, "rb").read(), before)
        link = os.path.join(self.tmp, "link.tfvars")
        os.symlink(os.path.join(self.tmp, "elsewhere"), link)
        done = run(["render", "--region", "us-east-2", "--environment", "course", "--account-id", ACCOUNT, "--out", link])
        self.assertEqual(done.returncode, 2)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "elsewhere")))


class CheckTests(Base):
    def rendered(self):
        if os.path.exists(self.out):
            os.unlink(self.out)
        self.assertEqual(self.render(fmt="json").returncode, 0)
        with open(self.out, encoding="utf-8") as handle:
            return json.load(handle)

    def check(self, document, extra=None):
        path = os.path.join(self.tmp, "candidate.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        return run(["check", "--file", path] + (extra if extra is not None else ["--region", "us-east-2", "--environment", "course"]))

    def test_the_rendered_policy_passes_every_check_and_the_account_is_masked(self):
        done = run(["check", "--file", self.out, "--region", "us-east-2", "--environment", "course"]) if self.render().returncode == 0 else None
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("RESULT: PASS", done.stdout)
        self.assertNotIn("FAIL:", done.stdout)
        self.assertNotIn(ACCOUNT, done.stdout)

    def mutate(self, change):
        document = self.rendered()
        change(document)
        return self.check(document)

    def test_each_defect_is_reported_and_exits_1(self):
        cases = {
            "a wildcard action": lambda d: d["Statement"][3]["Action"].__setitem__(2, "ec2:Terminate*"),
            "star resource on a write action": lambda d: d["Statement"][3].__setitem__("Resource", ["*"]),
            "a wildcard region in an ARN": lambda d: d["Statement"][0]["Resource"].__setitem__(0, "arn:aws:ec2:*:%s:subnet/*" % ACCOUNT),
            "a wrong region": lambda d: d["Statement"][0]["Resource"].__setitem__(0, "arn:aws:ec2:us-west-2:%s:subnet/*" % ACCOUNT),
            "a different account in one ARN": lambda d: d["Statement"][1]["Resource"].__setitem__(0, "arn:aws:ec2:us-east-2:%s:instance/*" % "".join(["7777", "8888", "9999"])),
            "a missing statement": lambda d: d["Statement"].pop(),
            "an extra statement": lambda d: d["Statement"].append(dict(d["Statement"][0], Sid="Extra")),
            "a deny statement": lambda d: d["Statement"][0].__setitem__("Effect", "Deny"),
            "a second PassRole": lambda d: d["Statement"][0]["Action"].append("iam:PassRole"),
            "PassRole to another service": lambda d: d["Statement"][-1]["Condition"]["StringEquals"].__setitem__("iam:PassedToService", "lambda.amazonaws.com"),
            "PassRole of another role": lambda d: d["Statement"][-1].__setitem__("Resource", ["arn:aws:iam::%s:role/other" % ACCOUNT]),
            "a left-over placeholder": lambda d: d["Statement"][0]["Resource"].__setitem__(0, "arn:aws:ec2:us-east-2:<12-digit-account-id>:subnet/*"),
            "the wrong Version": lambda d: d.__setitem__("Version", "2008-10-17"),
        }
        for name, change in cases.items():
            with self.subTest(name):
                done = self.mutate(change)
                self.assertEqual(done.returncode, 1, name + "\n" + done.stdout)
                self.assertIn("FAIL:", done.stdout)
                self.assertIn("RESULT: FAIL", done.stdout)

    def test_invalid_json_and_a_missing_file(self):
        path = os.path.join(self.tmp, "broken.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{ not json")
        done = run(["check", "--file", path])
        self.assertEqual(done.returncode, 1)
        self.assertIn("not valid JSON", done.stdout)
        done = run(["check", "--file", os.path.join(self.tmp, "absent.json")])
        self.assertEqual(done.returncode, 2)

    def test_the_tfvars_heredoc_and_the_bare_json_give_the_same_verdict(self):
        self.assertEqual(self.render().returncode, 0)
        heredoc = run(["check", "--file", self.out])
        os.unlink(self.out)
        self.assertEqual(self.render(fmt="json").returncode, 0)
        bare = run(["check", "--file", self.out])
        self.assertEqual((heredoc.returncode, heredoc.stdout), (bare.returncode, bare.stdout))
        self.assertEqual(heredoc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
