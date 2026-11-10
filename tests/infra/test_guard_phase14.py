"""Phase 14A: the literal-source guard (tests/infra/terraform_source_guard.py) after the phase14-main change.

Two things changed in the infrastructure and the guard must keep up with both:
  * phase14_main.tf has seven Allow statements on Resource "*" whose actions have no resource-level scoping. Each is now a
    GlobalGrant allowlist entry (file + exact action set + justification + Service Authorization Reference page), and an
    unjustified new global grant must still fail.
  * the two permissions-boundary documents moved into deployer/boundaries/*.json.tftpl; the guard scanned only .tf and
    .tfvars, so the policy JSON was unscanned. The IAM categories now cover *.json.tftpl and environments/*.json.example.

Every case below runs the guard CLI on a SCRATCH git repository that holds copies of the real files, so the repository is never
mutated. The offline, stdlib-only guard needs no Terraform and no AWS.
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import terraform_source_guard as guard
from infra_support import REPO

GUARD = Path(guard.__file__).resolve()
PHASE14 = "infra/terraform/deployer/phase14_main.tf"
RUNTIME_TPL = "infra/terraform/deployer/boundaries/runtime.json.tftpl"
EMR_TPL = "infra/terraform/deployer/boundaries/emr-service.json.tftpl"
EXAMPLE = "infra/terraform/environments/emr-service-policy.json.example"
TUNNEL = "infra/terraform/modules/identity/neptune_tunnel.tf"
REAL = (PHASE14, RUNTIME_TPL, EMR_TPL, EXAMPLE)
REAL_W5 = REAL + (TUNNEL,)


def run_guard(files):
    """Write {relative path: text} into a fresh git repository, run the guard CLI, return (exit code, parsed report)."""
    with tempfile.TemporaryDirectory(prefix="sc-guard-") as tmp:
        root = Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        for path, text in files.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        done = subprocess.run([sys.executable, "-I", str(GUARD), "--repo-root", str(root)], capture_output=True, text=True)
        report = json.loads(done.stdout) if done.stdout.strip() else None
        return done.returncode, report, done.stderr


def real_files(paths=REAL):
    return {p: (REPO / p).read_text() for p in paths}


def categories(report):
    return sorted((f["path"], f["line"], f["category"]) for f in report["findings"])


def line_of(text, needle):
    return text[: text.index(needle)].count("\n") + 1


class RealTreeIsClean(unittest.TestCase):
    def test_repository_passes_the_guard_with_the_justified_allowlist(self):
        done = subprocess.run([sys.executable, "-I", str(GUARD), "--repo-root", str(REPO)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout[-1500:])
        self.assertEqual(json.loads(done.stdout)["findings"], [])

    def test_the_guards_own_self_test_passes(self):
        done = subprocess.run([sys.executable, "-I", str(GUARD), "--self-test"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr[-1500:])
        self.assertRegex(done.stderr, r"Ran \d+ tests")

    def test_copies_of_the_real_files_alone_are_clean_and_no_entry_is_stale(self):
        code, report, _ = run_guard(real_files())
        self.assertEqual((code, report["findings"]), (0, []))
        self.assertEqual(report["files"], 4)

    def test_the_policy_templates_and_the_environment_example_are_in_the_scanned_set(self):
        listed = subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "infra/terraform"], cwd=REPO
        ).decode().split("\0")
        scanned = {p for p in listed if guard.is_scanned(p)}
        for path in (RUNTIME_TPL, EMR_TPL, EXAMPLE):
            self.assertIn(path, scanned)
        # Every policy-JSON template and environments/*.json.example in the tree is covered, not only the three named above.
        every = {p for p in listed if p.endswith(".json.tftpl")} | {
            p for p in listed if re.fullmatch(r"infra/terraform/environments/[^/]+\.json\.example", p)}
        self.assertTrue(every <= scanned)

    def test_the_allowlist_has_exactly_the_ten_reviewed_statements(self):
        """Seven from 14A, plus (replan W5a/W5b) acm:RequestCertificate and the four ssmmessages ECS Exec actions in two files."""
        by_service = sorted(sorted({a.split(":")[0] for a in g.actions}) for g in guard.GLOBAL_RESOURCE_ALLOWLIST)
        self.assertEqual(by_service, [
            ["acm"], ["acm", "elasticloadbalancing"], ["application-autoscaling", "servicediscovery"], ["cloudwatch"],
            ["ecs"], ["ecs"], ["rds"], ["route53"], ["ssmmessages"], ["ssmmessages"]])
        self.assertEqual({g.path for g in guard.GLOBAL_RESOURCE_ALLOWLIST}, {PHASE14, RUNTIME_TPL, TUNNEL})
        sizes = sorted(len(g.actions) for g in guard.GLOBAL_RESOURCE_ALLOWLIST)
        self.assertEqual(sizes, [1, 1, 2, 3, 4, 4, 4, 9, 10, 10])
        for g in guard.GLOBAL_RESOURCE_ALLOWLIST:
            if g.path != PHASE14:
                self.assertFalse(g.requires_condition)  # the ssmmessages entries: no condition key applies to ECS tasks


class UnjustifiedGlobalGrantsStillFail(unittest.TestCase):
    """The guard's own meaning must survive the allowlist: a new unjustified global IAM grant fails."""

    def test_a_new_global_allow_in_the_allowlisted_file_fails(self):
        files = real_files()
        files[PHASE14] += '\nlocals {\n  rogue = { Statement = [{ Effect = "Allow", Action = ["ec2:TerminateInstances"], Resource = ["*"] }] }\n}\n'
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertEqual(categories(report), [(PHASE14, files[PHASE14].count("\n") - 1, "global-iam-resource")])

    def test_an_extra_action_added_to_an_allowlisted_statement_fails(self):
        files = real_files()
        needle = '"rds:DescribeGlobalClusters",'
        files[PHASE14] = files[PHASE14].replace(needle, needle + ' "rds:DeleteDBCluster",', 1)
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertIn("global-iam-resource", [c for _, _, c in categories(report)])
        # The reviewed entry no longer matches any statement, so it is reported as stale too.
        self.assertIn("stale-global-allowlist-entry", [c for _, _, c in categories(report)])

    def test_an_action_removed_from_an_allowlisted_statement_fails(self):
        files = real_files()
        files[PHASE14] = files[PHASE14].replace('"route53:GetChange", ', "", 1)
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertIn("global-iam-resource", [c for _, _, c in categories(report)])

    def test_the_same_statements_in_another_file_are_not_exempt(self):
        files = real_files()
        files["infra/terraform/deployer/renamed.tf"] = files.pop(PHASE14)
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        found = categories(report)
        self.assertEqual([c for _, _, c in found], ["global-iam-resource"] * 8)  # seven 14A statements + acm:RequestCertificate
        self.assertEqual({p for p, _, _ in found}, {"infra/terraform/deployer/renamed.tf"})

    def test_an_allowlisted_regional_statement_that_loses_its_condition_fails(self):
        files = real_files()
        text = files[PHASE14]
        start = text.index('Sid       = "CloudWatchReadNoResourceScoping"')
        old = "Condition = { StringEquals = local.c_region }"
        at = text.index(old, start)
        files[PHASE14] = text[:at] + text[at + len(old):]
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertEqual([c for _, _, c in categories(report)], ["unconditioned-allowlisted-global-grant"])

    def test_only_the_global_route_53_entry_is_exempt_from_the_condition_requirement(self):
        """Route 53 is a global service (no aws:RequestedRegion) and the ssmmessages ECS Exec channels carry no usable condition
        key for a Fargate task (replan W5); every other entry must keep a Condition."""
        for g in guard.GLOBAL_RESOURCE_ALLOWLIST:
            exempt = all(a.startswith(("route53:", "ssmmessages:")) for a in g.actions)
            self.assertEqual(g.requires_condition, not exempt, sorted(g.actions))

    def test_an_unused_allowlist_entry_is_reported_as_stale(self):
        files = real_files()
        text = files[PHASE14]
        start = text.index('Sid       = "EcsRegisterTaskDefinitionWithProjectTags"')
        old = '"ecs:RegisterTaskDefinition"'
        at = text.index(old, start)
        files[PHASE14] = text[:at] + '"ecs:RegisterTaskDefinition", "ecs:RunTask"' + text[at + len(old):]
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertEqual(sorted(c for _, _, c in categories(report)), ["global-iam-resource", "stale-global-allowlist-entry"])


class ReplanW5Grants(unittest.TestCase):
    """Replan W5a/W5b: acm:RequestCertificate (deployer) and the four ssmmessages ECS Exec actions (boundary and tunnel role)."""

    def test_real_copies_including_the_tunnel_role_are_clean_and_no_entry_is_stale(self):
        code, report, _ = run_guard(real_files(REAL_W5))
        self.assertEqual((code, report["findings"]), (0, []))
        self.assertEqual(report["files"], 5)

    def test_the_real_acm_statement_keeps_region_dns_validation_and_request_tags(self):
        text = real_files()[PHASE14]
        start = text.index('Sid       = "AcmRequestCertificateDnsValidationWithProjectTags"')
        old = 'Condition = { StringEquals = merge(local.c_region, local.c_req_main, { "acm:ValidationMethod" = "DNS" }) }'
        at = text.index(old, start)
        for name, new_condition in {
            "dns to email": old.replace('"DNS"', '"EMAIL"'),
            "validation method removed": old.replace(', { "acm:ValidationMethod" = "DNS" }', ""),
            "region removed": old.replace("local.c_region, ", ""),
            "request tags removed": old.replace("local.c_req_main, ", ""),
            "condition removed": "",
        }.items():
            with self.subTest(name):
                files = real_files()
                files[PHASE14] = text[:at] + new_condition + text[at + len(old):]
                code, report, _ = run_guard(files)
                self.assertEqual(code, 1)
                self.assertEqual(len(report["findings"]), 1, report)
                self.assertIn(categories(report)[0][2], ("weakened-allowlisted-global-grant", "unconditioned-allowlisted-global-grant"))

    def test_an_extra_acm_action_in_the_request_statement_fails(self):
        files = real_files()
        files[PHASE14] = files[PHASE14].replace('Action    = ["acm:RequestCertificate"]', 'Action    = ["acm:RequestCertificate", "acm:ExportCertificate"]', 1)
        self.assertNotEqual(files[PHASE14], real_files()[PHASE14])
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertIn("global-iam-resource", [c for _, _, c in categories(report)])

    def test_the_boundary_ecs_exec_statement_is_exact(self):
        text = real_files()[RUNTIME_TPL]
        old = '"ssmmessages:OpenDataChannel"'
        self.assertEqual(text.count(old), 1)
        cases = {
            "extra action": (old, old + ',\n        "ssm:StartSession"', "global-iam-resource"),
            "wildcard": (old, '"ssmmessages:*"', "wildcard-iam-action"),
            "action removed": (',\n        ' + old, "", "global-iam-resource"),
        }
        for name, (before, after, category) in cases.items():
            with self.subTest(name):
                files = real_files()
                self.assertEqual(files[RUNTIME_TPL].count(before), 1)
                files[RUNTIME_TPL] = text.replace(before, after, 1)
                code, report, _ = run_guard(files)
                self.assertEqual(code, 1)
                self.assertIn(category, [c for _, _, c in categories(report)])
                self.assertIn("stale-global-allowlist-entry", [c for _, _, c in categories(report)])

    def test_the_same_four_actions_in_a_new_policy_template_fail(self):
        files = real_files()
        files["infra/terraform/deployer/boundaries/other.json.tftpl"] = (
            '{"Version": "2012-10-17",\n "Statement": [\n'
            '  {"Effect": "Allow", "Action": ["ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel", '
            '"ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"], "Resource": ["*"]}\n ]}\n')
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertEqual(categories(report), [("infra/terraform/deployer/boundaries/other.json.tftpl", 3, "global-iam-resource")])

    def test_the_tunnel_role_policy_is_exact_through_its_local(self):
        text = real_files(REAL_W5)[TUNNEL]
        old = '"ssmmessages:OpenDataChannel"]'
        self.assertEqual(text.count(old), 1)
        for name, new_text in {
            "extra action": '"ssmmessages:OpenDataChannel", "s3:GetObject"]',
            "wildcard": '"ssmmessages:*"]',
        }.items():
            with self.subTest(name):
                files = real_files(REAL_W5)
                files[TUNNEL] = text.replace(old, new_text, 1)
                code, report, _ = run_guard(files)
                self.assertEqual(code, 1)
                self.assertIn("global-iam-resource", [c for _, _, c in categories(report)])

    def test_the_tunnel_policy_moved_to_another_file_fails(self):
        files = real_files(REAL_W5)
        files["infra/terraform/modules/identity/renamed_tunnel.tf"] = files.pop(TUNNEL)
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertEqual([c for _, _, c in categories(report)], ["global-iam-resource"])


class PolicyJsonTemplatesAreScanned(unittest.TestCase):
    def test_a_template_with_an_unjustified_global_grant_fails(self):
        files = real_files()
        files["infra/terraform/deployer/boundaries/rogue.json.tftpl"] = (
            '{"Version": "2012-10-17",\n "Statement": [\n'
            '  {"Effect": "Allow", "Action": ["iam:PassRole"], "Resource": ["*"]}\n ]}\n')
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertEqual(categories(report), [("infra/terraform/deployer/boundaries/rogue.json.tftpl", 3, "global-iam-resource")])

    def test_the_real_runtime_boundary_with_its_one_global_action_changed_fails(self):
        files = real_files()
        text = files[RUNTIME_TPL]
        old = '"ecr:GetAuthorizationToken"'
        self.assertEqual(text.count(old), 1)
        files[RUNTIME_TPL] = text.replace(old, '"ecr:BatchGetImage"')
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertEqual([(p, c) for p, _, c in categories(report)], [(RUNTIME_TPL, "global-iam-resource")])

    def test_a_service_wide_wildcard_action_added_to_the_real_template_fails(self):
        files = real_files()
        files[EMR_TPL] = files[EMR_TPL].replace('"ec2:TerminateInstances"', '"ec2:TerminateInstances",\n        "ec2:*"', 1)
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertEqual([(p, c) for p, _, c in categories(report)], [(EMR_TPL, "wildcard-iam-action")])

    def test_a_wildcard_account_or_region_in_a_template_arn_fails(self):
        files = real_files()
        files[RUNTIME_TPL] = files[RUNTIME_TPL].replace("arn:aws:sqs:${region}:${acct}:${mp}-*", "arn:aws:sqs:*:*:${mp}-*", 1)
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertEqual([(p, c) for p, _, c in categories(report)], [(RUNTIME_TPL, "global-iam-resource")])

    def test_an_environment_json_example_is_scanned_too(self):
        files = real_files()
        files[EXAMPLE] = files[EXAMPLE].replace('"ec2:CreateNetworkInterface"', '"*"', 1)
        code, report, _ = run_guard(files)
        self.assertEqual(code, 1)
        self.assertEqual([(p, c) for p, _, c in categories(report)], [(EXAMPLE, "wildcard-iam-action")])

    def test_a_json_example_outside_environments_is_not_scanned(self):
        files = real_files()
        files["infra/terraform/other/y.json.example"] = '{"Effect": "Allow", "Action": ["*"], "Resource": ["*"]}'
        code, report, _ = run_guard(files)
        self.assertEqual((code, report["findings"]), (0, []))

    def test_template_interpolations_are_not_wildcards(self):
        files = real_files()
        files["infra/terraform/deployer/boundaries/ok.json.tftpl"] = (
            '{"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": ["${arn}", "arn:aws:s3:::${mp}-${acct}-*/*"]},\n'
            ' {"Effect": "Allow", "Action": ["sqs:SendMessage"], "Resource": [${join(", ", [for q in queues : jsonencode(q)])}]}]}')
        code, report, _ = run_guard(files)
        self.assertEqual((code, report["findings"]), (0, []))

    def test_findings_in_a_template_do_not_echo_policy_content(self):
        files = real_files()
        files["infra/terraform/deployer/boundaries/rogue.json.tftpl"] = '{"Effect": "Allow", "Action": ["kms:Decrypt"], "Resource": ["*"]}'
        _, report, _ = run_guard(files)
        self.assertEqual(set(report["findings"][0]), {"path", "line", "category"})


if __name__ == "__main__":
    unittest.main()
