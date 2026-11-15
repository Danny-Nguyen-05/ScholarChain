"""Static (text-only, no Terraform needed) source checks and the scanner they rely on.

Item 12: `aws_default_security_group` is absent from the spike root (a re-added one is detected). The main root's
network module used to manage its default security group ("closed"); 14A repair round 1 (review F2, user-ordered
narrowing) removed it, so the main root now leaves the VPC default group unmanaged exactly like the spike, and the check
for the main root is that NO aws_default_security_group exists anywhere in the root or its modules.
"""
import re
import unittest
from pathlib import Path

import hcl_text
from infra_support import REPO

SPIKE_ROOT = REPO / "infra/terraform/spikes/emr-spark-isolated"
NETWORK_MODULE = REPO / "infra/terraform/modules/network"
MAIN_ROOT = REPO / "infra/terraform"


def tf_texts(directory):
    return {p.name: p.read_text() for p in sorted(Path(directory).glob("*.tf"))}


def default_sg_blocks(texts):
    """[(file, type, name, body)] of every aws_default_* resource in the given {file: text} sources."""
    found = []
    for name, text in texts.items():
        for rtype, rname, body in hcl_text.resource_blocks(text):
            if rtype.startswith("aws_default_"):
                found.append((name, rtype, rname, body))
    return found


def spike_default_sg_problems(texts):
    return ["%s declares %s.%s" % (f, t, n) for f, t, n, _ in default_sg_blocks(texts)]


def main_root_texts():
    """{relative path: text} of every .tf file of the main root and of its modules (the spikes are separate roots)."""
    texts = {p.relative_to(MAIN_ROOT).as_posix(): p.read_text() for p in sorted(MAIN_ROOT.glob("*.tf"))}
    for p in sorted((MAIN_ROOT / "modules").glob("*/*.tf")):
        texts[p.relative_to(MAIN_ROOT).as_posix()] = p.read_text()
    return texts


def main_default_sg_problems(texts):
    """Review F2 narrowing: the main root must not manage the VPC default security group at all. Adopting it needed
    tag-on-adoption statements in the deployer role that reached every security group in the region."""
    return ["%s declares %s.%s" % (f, t, n) for f, t, n, _ in default_sg_blocks(texts) if t == "aws_default_security_group"]


class ScannerSelfCheck(unittest.TestCase):
    """The scanner behind the mutation edits is itself tested, so a mutation cannot silently be a no-op."""

    def test_resource_blocks_ignore_comments_and_nested_braces(self):
        text = '''# resource "aws_default_security_group" "commented" {}
/* resource "aws_default_security_group" "block_comment" {} */
resource "aws_vpc" "v" {
  tags = { Name = "${var.a["b"]}-x" }
}
resource "aws_default_security_group" "d" {
  vpc_id = aws_vpc.v.id
}
'''
        self.assertEqual([(t, n) for t, n, _ in hcl_text.resource_blocks(text)], [("aws_vpc", "v"), ("aws_default_security_group", "d")])

    def test_strip_attribute_removes_a_balanced_multiline_value_only(self):
        text = 'a = {\n  Sid = "x"\n  Condition = {\n    k = { "a}" = "b" }\n  }\n  Other = 1\n}\n'
        out = hcl_text.strip_attribute_after(text, '"x"', "Condition")
        self.assertEqual(out, 'a = {\n  Sid = "x"\n  Other = 1\n}\n')

    def test_missing_anchor_is_an_error_not_a_silent_noop(self):
        with self.assertRaises(KeyError):
            hcl_text.strip_attribute_after("a = 1\n", '"nope"', "Condition")


class Item12SpikeDefaultSecurityGroup(unittest.TestCase):
    def test_the_spike_root_declares_no_default_resource(self):
        texts = tf_texts(SPIKE_ROOT)
        self.assertGreaterEqual(len(texts), 8)
        self.assertEqual(spike_default_sg_problems(texts), [])

    def test_re_adding_the_default_security_group_to_the_spike_is_detected(self):
        texts = tf_texts(SPIKE_ROOT)
        texts["zz_mutation.tf"] = 'resource "aws_default_security_group" "readded" {\n  vpc_id = aws_vpc.spike.id\n}\n'
        self.assertEqual(spike_default_sg_problems(texts), ["zz_mutation.tf declares aws_default_security_group.readded"])

    def test_re_adding_it_in_an_existing_file_is_detected(self):
        texts = tf_texts(SPIKE_ROOT)
        texts["network.tf"] += '\nresource "aws_default_security_group" "d" {\n  vpc_id = aws_vpc.spike.id\n}\n'
        self.assertEqual(len(spike_default_sg_problems(texts)), 1)

    def test_the_explanatory_comment_alone_is_not_a_resource(self):
        self.assertIn("default security group", (SPIKE_ROOT / "network.tf").read_text())
        self.assertEqual(spike_default_sg_problems({"network.tf": (SPIKE_ROOT / "network.tf").read_text()}), [])


class Item12MainRootDefaultSecurityGroup(unittest.TestCase):
    def test_the_main_root_and_its_modules_declare_no_default_security_group(self):
        texts = main_root_texts()
        self.assertIn("modules/network/main.tf", texts)
        self.assertGreaterEqual(len(texts), 20)
        self.assertEqual(main_default_sg_problems(texts), [])

    def test_the_explanation_of_why_it_is_unmanaged_is_still_in_the_network_module(self):
        self.assertIn("default security group", (NETWORK_MODULE / "main.tf").read_text().lower())

    def test_re_adding_the_main_default_group_in_the_network_module_is_detected(self):
        texts = main_root_texts()
        texts["modules/network/main.tf"] += '\nresource "aws_default_security_group" "closed" {\n  vpc_id = aws_vpc.course.id\n}\n'
        self.assertEqual(main_default_sg_problems(texts), ["modules/network/main.tf declares aws_default_security_group.closed"])

    def test_re_adding_it_with_an_ingress_rule_is_detected(self):
        texts = main_root_texts()
        texts["modules/network/main.tf"] += (
            '\nresource "aws_default_security_group" "closed" {\n  vpc_id = aws_vpc.course.id\n'
            '  ingress {\n    protocol  = "-1"\n    self      = true\n    from_port = 0\n    to_port   = 0\n  }\n}\n')
        self.assertEqual(len(main_default_sg_problems(texts)), 1)

    def test_re_adding_it_in_another_module_or_the_root_is_detected(self):
        for where in ("modules/emr/zz_mutation.tf", "zz_mutation.tf"):
            with self.subTest(where=where):
                texts = dict(main_root_texts(), **{where: 'resource "aws_default_security_group" "second" {\n  vpc_id = "vpc-1"\n}\n'})
                self.assertEqual(main_default_sg_problems(texts), ["%s declares aws_default_security_group.second" % where])

    def test_an_ordinary_security_group_is_not_mistaken_for_the_default_group(self):
        texts = dict(main_root_texts(), **{"zz.tf": 'resource "aws_security_group" "closed" {\n  vpc_id = "vpc-1"\n}\n'})
        self.assertEqual(main_default_sg_problems(texts), [])


if __name__ == "__main__":
    unittest.main()
