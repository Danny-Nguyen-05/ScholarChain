"""Static (text-only, no Terraform needed) source checks and the scanner they rely on.

Item 12: `aws_default_security_group` is absent from the spike root (a re-added one is detected). The main root's
network module manages its default security group on purpose ("closed": Terraform revokes every rule); that is the
reviewed policy there, so for the main root the check is that the one default security group has no rules.
"""
import re
import unittest
from pathlib import Path

import hcl_text
from infra_support import REPO

SPIKE_ROOT = REPO / "infra/terraform/spikes/emr-spark-isolated"
NETWORK_MODULE = REPO / "infra/terraform/modules/network"


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


def main_default_sg_problems(texts):
    """The main root manages exactly one default security group and it declares no ingress or egress rule."""
    blocks = [b for b in default_sg_blocks(texts) if b[1] == "aws_default_security_group"]
    problems = []
    if len(blocks) != 1:
        problems.append("expected exactly one aws_default_security_group, found %d" % len(blocks))
    for f, t, n, body in blocks:
        # Nested rule blocks or attributes would re-open the group; an empty body of rules keeps it closed.
        if declares_rule(body):
            problems.append("%s.%s in %s declares ingress/egress rules (the default group must stay closed)" % (t, n, f))
    return problems


def declares_rule(body):
    return re.search(r"^[ \t]*(ingress|egress)[ \t]*(\{|=)", body, re.M) is not None


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
    def test_the_main_root_manages_one_default_group_and_keeps_it_closed(self):
        self.assertEqual(main_default_sg_problems(tf_texts(NETWORK_MODULE)), [])

    def test_adding_an_ingress_rule_to_the_main_default_group_is_detected(self):
        texts = tf_texts(NETWORK_MODULE)
        texts["main.tf"] = texts["main.tf"].replace(
            'resource "aws_default_security_group" "closed" {',
            'resource "aws_default_security_group" "closed" {\n  ingress {\n    protocol  = "-1"\n    self      = true\n    from_port = 0\n    to_port   = 0\n  }', 1)
        problems = main_default_sg_problems(texts)
        self.assertEqual(len(problems), 1)
        self.assertIn("must stay closed", problems[0])

    def test_removing_the_main_default_group_or_duplicating_it_is_detected(self):
        texts = tf_texts(NETWORK_MODULE)
        removed = dict(texts, **{"main.tf": texts["main.tf"].replace('resource "aws_default_security_group" "closed"', 'resource "aws_security_group" "closed"', 1)})
        self.assertEqual(len(main_default_sg_problems(removed)), 1)
        duplicated = dict(texts, **{"zz.tf": 'resource "aws_default_security_group" "second" {\n  vpc_id = aws_vpc.course.id\n}\n'})
        self.assertEqual(len(main_default_sg_problems(duplicated)), 1)


if __name__ == "__main__":
    unittest.main()
