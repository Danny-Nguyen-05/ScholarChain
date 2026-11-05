"""Shared test helpers: PATH shims that record calls; no AWS, no network."""
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(TESTS_DIR)
EMR_DIR = os.path.join(SCRIPTS_DIR, "emr")


def write_exec(path, text):
    with open(path, "w") as handle:
        handle.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class ShimTestCase(unittest.TestCase):
    """Creates tmp dirs, a shim bin dir, and an ordered call log."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-spike-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.bin = os.path.join(self.tmp, "bin")
        self.fake_dir = os.path.join(self.tmp, "fake-aws")
        os.makedirs(self.bin)
        os.makedirs(self.fake_dir)
        self.order_log = os.path.join(self.tmp, "order.log")
        self.aws_log = os.path.join(self.tmp, "aws.log")
        open(self.order_log, "w").close()
        open(self.aws_log, "w").close()
        py = os.path.join(TESTS_DIR, "fake_aws.py")
        write_exec(os.path.join(self.bin, "aws"), f'#!/bin/bash\nexec python3 -I "{py}" "$@"\n')

    def add_shim(self, name, body):
        """A shim that logs `name args...` to the order log and then runs body."""
        write_exec(
            os.path.join(self.bin, name),
            '#!/bin/bash\n'
            f'echo "{name} $*" >> "$SHIM_ORDER_LOG"\n' + body + "\n",
        )

    def env(self, **extra):
        env = {
            "PATH": self.bin + ":/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": self.tmp,
            "FAKE_AWS_DIR": self.fake_dir,
            "FAKE_AWS_LOG": self.aws_log,
            "SHIM_ORDER_LOG": self.order_log,
            "LC_ALL": "C",
        }
        env.update(extra)
        return env

    def run_script(self, script, args, **env):
        return subprocess.run(
            ["bash", script] + list(args),
            env=self.env(**env), capture_output=True, text=True, timeout=120,
        )

    def order(self):
        with open(self.order_log) as handle:
            return [l.rstrip("\n") for l in handle if l.strip()]

    def put(self, rel, data, mode="w"):
        path = os.path.join(self.fake_dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, mode) as handle:
            handle.write(data)
        return path
