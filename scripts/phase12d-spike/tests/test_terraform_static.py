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


class DefaultSecurityGroupTests(unittest.TestCase):
    def test_default_security_group_is_not_managed(self):
        self.assertNotIn('"aws_default_security_group"', strip_comments(read_all(SPIKE)))

    def test_deployer_has_no_default_sg_adoption_statement(self):
        code = strip_comments(read_all(DEPLOYER))
        self.assertNotIn("DefaultSecurityGroupAdoption", code)

    def test_every_ec2_create_tags_has_a_create_action_condition(self):
        code = strip_comments(read_all(DEPLOYER))
        for match in re.finditer(r'Action\s*=\s*\[\s*"ec2:CreateTags"\s*\]', code):
            window = code[match.start(): match.start() + 700]
            self.assertIn("ec2:CreateAction", window)


if __name__ == "__main__":
    unittest.main()
