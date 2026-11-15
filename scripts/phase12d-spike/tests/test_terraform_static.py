"""Static, text-level checks of the Terraform sources (stdlib only, no Terraform run)."""
import os
import re
import unittest

from helpers import SCRIPTS_DIR

ROOT = os.path.normpath(os.path.join(SCRIPTS_DIR, "..", ".."))
SPIKE = os.path.join(ROOT, "infra", "terraform", "spikes", "emr-spark-isolated")
DEPLOYER = os.path.join(ROOT, "infra", "terraform", "deployer")


def read_all(directory):
    text = ""
    for name in sorted(os.listdir(directory)):
        if name.endswith(".tf"):
            with open(os.path.join(directory, name)) as handle:
                text += handle.read() + "\n"
    return text


def strip_comments(text):
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def brace_blocks(code):
    """[(start, end)] of every balanced {...} in code, skipping the contents of double-quoted strings."""
    blocks, stack, i, n = [], [], 0, len(code)
    while i < n:
        c = code[i]
        if c == '"':
            i += 1
            while i < n and code[i] != '"':
                i += 2 if code[i] == "\\" else 1
        elif c == "{":
            stack.append(i)
        elif c == "}" and stack:
            blocks.append((stack.pop(), i + 1))
        i += 1
    return blocks


def enclosing_statement(code, position, blocks):
    """The smallest {...} block that contains position: the policy statement object around an Action line."""
    best = None
    for start, end in blocks:
        if start <= position < end and (best is None or end - start < best[1] - best[0]):
            best = (start, end)
    return code[best[0]: best[1]] if best else ""


def create_tags_problems(code):
    """Problems with the ec2:CreateTags statements of the deployer text (empty list = invariant holds).

    The invariant is strict: every statement whose Action is exactly ["ec2:CreateTags"] must carry an ec2:CreateAction condition, so that
    tags apply at creation only and an existing resource cannot be tagged into a tag-scoped statement. (Repair round 1, F2, removed the
    D6 named exception: the deployer no longer adopts the VPC default security group, so no CreateTags-only statement is exempt.)
    The statement is found by parsing its enclosing {...} block, never by a fixed character window.
    """
    problems = []
    blocks = brace_blocks(code)
    for match in re.finditer(r'Action\s*=\s*\[\s*"ec2:CreateTags"\s*\]', code):
        statement = enclosing_statement(code, match.start(), blocks)
        if "ec2:CreateAction" not in statement:
            sid = re.search(r'\bSid\s*=\s*"([^"]+)"', statement)
            problems.append("ec2:CreateTags statement %r has no ec2:CreateAction condition" % (sid.group(1) if sid else "?"))
    return problems


class DefaultSecurityGroupTests(unittest.TestCase):
    def test_default_security_group_is_not_managed(self):
        self.assertNotIn('"aws_default_security_group"', strip_comments(read_all(SPIKE)))

    def test_deployer_has_no_default_sg_adoption_statement(self):
        code = strip_comments(read_all(DEPLOYER))
        self.assertNotIn("DefaultSecurityGroupAdoption", code)

    def test_every_ec2_create_tags_has_a_create_action_condition(self):
        code = strip_comments(read_all(DEPLOYER))
        self.assertEqual(create_tags_problems(code), [])
        self.assertGreaterEqual(len(re.findall(r'Action\s*=\s*\[\s*"ec2:CreateTags"\s*\]', code)), 1, "the invariant must have something to check")

    def test_deployer_has_no_adopted_default_security_group_statement(self):
        code = strip_comments(read_all(DEPLOYER))
        self.assertNotIn("Ec2AdoptedDefaultSg", code)


class CreateTagsInvariantNegativeTests(unittest.TestCase):
    """In-memory mutations of the deployer text (the real files are never edited) must be rejected."""

    @classmethod
    def setUpClass(cls):
        cls.code = strip_comments(read_all(DEPLOYER))

    def test_the_unmutated_text_is_accepted(self):
        self.assertEqual(create_tags_problems(self.code), [])

    def test_a_create_tags_only_statement_without_create_action_is_rejected(self):
        extra = (
            '{ Sid = "Ec2TagAnythingNow" Effect = "Allow" Action = ["ec2:CreateTags"] '
            'Resource = ["${local.arn_ec2}:security-group/*"] Condition = { StringEquals = local.c_region } },\n'
        )
        index = self.code.index('Sid      = "Ec2TagOnCreateOnly"')
        brace = self.code.rindex("{", 0, index)
        problems = create_tags_problems(self.code[:brace] + extra + self.code[brace:])
        self.assertTrue(any("Ec2TagAnythingNow" in p for p in problems), problems)

    def test_the_old_adoption_statement_would_be_rejected(self):
        adoption = (
            '{ Sid = "Ec2AdoptedDefaultSgFirstTags" Effect = "Allow" Action = ["ec2:CreateTags"] '
            'Resource = ["${local.arn_ec2}:security-group/*"] Condition = { StringEquals = merge(local.c_region, local.c_req_main) } },\n'
        )
        problems = create_tags_problems(adoption + self.code)
        self.assertTrue(any("Ec2AdoptedDefaultSgFirstTags" in p for p in problems), problems)

    def test_a_neighbouring_statement_cannot_borrow_create_action_from_the_next_one(self):
        # a CreateTags-only statement placed directly before a statement that has ec2:CreateAction must still be rejected
        neighbour = (
            '{ Sid = "Ec2NeighbourWithoutCondition" Effect = "Allow" Action = ["ec2:CreateTags"] Resource = ["*"] },\n'
            '{ Sid = "Ec2NextHasIt" Effect = "Allow" Action = ["ec2:CreateTags"] Resource = ["*"] Condition = { StringEquals = { "ec2:CreateAction" = ["CreateVpc"] } } },\n'
        )
        problems = create_tags_problems(neighbour)
        self.assertTrue(any("Ec2NeighbourWithoutCondition" in p for p in problems), problems)
        self.assertFalse(any("Ec2NextHasIt" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
