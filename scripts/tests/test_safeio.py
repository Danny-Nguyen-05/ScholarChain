"""R2: scripts/lib/safeio.py, timeout.py --stdout-new / trace and redact.py --append-to never write through a symlink,
never overwrite, never truncate (hand-derived expectations, temp directories only)."""
import os
import subprocess
import sys
import tempfile
import unittest

from helpers import SCRIPTS_DIR

SAFEIO = os.path.join(SCRIPTS_DIR, "lib", "safeio.py")
TIMEOUT = os.path.join(SCRIPTS_DIR, "lib", "timeout.py")
REDACT = os.path.join(SCRIPTS_DIR, "lib", "redact.py")


def run(script, args, **kwargs):
    return subprocess.run([sys.executable, "-I", script] + args, capture_output=True, text=True, timeout=60, **kwargs)


class SafeioBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-safeio-")
        self.addCleanup(subprocess.run, ["rm", "-rf", self.tmp])
        self.root = os.path.realpath(os.path.join(self.tmp, "repo"))
        self.plans = os.path.join(self.root, "target", "plans")
        os.makedirs(self.plans)
        self.canary = os.path.join(self.tmp, "canary.txt")
        with open(self.canary, "w") as handle:
            handle.write("CANARY\n")

    def canary_ok(self):
        with open(self.canary) as handle:
            self.assertEqual(handle.read(), "CANARY\n")

    def check_new(self, *paths, labels=None):
        args = ["check-new", "--root", self.root]
        for index, path in enumerate(paths):
            args += ["--entry", (labels or {}).get(path, "out%d" % index), "target/plans", self.plans, path]
        return run(SAFEIO, args)


class CheckNewTests(SafeioBase):
    def test_a_fresh_path_inside_the_directory_is_accepted_and_nothing_is_created(self):
        path = os.path.join(self.plans, "run1", "x.tfplan")
        result = self.check_new(path)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout.strip(), path)
        self.assertFalse(os.path.exists(os.path.dirname(path)))

    def test_an_existing_path_a_symlink_and_a_dangling_symlink_are_refused(self):
        existing = os.path.join(self.plans, "exists.txt")
        open(existing, "w").close()
        link = os.path.join(self.plans, "link.txt")
        os.symlink(self.canary, link)
        dangling = os.path.join(self.plans, "dangling.txt")
        os.symlink(os.path.join(self.tmp, "nowhere"), dangling)
        for path in (existing, link, dangling):
            with self.subTest(path):
                result = self.check_new(path)
                self.assertEqual(result.returncode, 1)
                self.assertRegex(result.stdout, "SAFEIO-REFUSED: .*(already exists|symlink)")
        self.canary_ok()

    def test_outside_dotdot_and_a_symlinked_directory_component_are_refused(self):
        os.symlink(self.tmp, os.path.join(self.plans, "sub"))
        cases = {
            "outside the repository": os.path.join(self.tmp, "x"),
            "inside the repository but outside the directory": os.path.join(self.root, "x"),
            "dotdot": os.path.join(self.plans, "..", "x"),
            "symlinked directory": os.path.join(self.plans, "sub", "x"),
        }
        for label, path in cases.items():
            with self.subTest(label):
                result = self.check_new(path)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertRegex(result.stdout, "must live inside target/plans|symlink")

    def test_colliding_outputs_are_refused(self):
        a = os.path.join(self.plans, "a.json")
        cases = {
            "identical paths": (a, a),
            "case aliases": (a, os.path.join(self.plans, "A.JSON")),
            "dot segments": (a, os.path.join(self.plans, ".", "a.json")),
            "a file that is the directory of another": (a, os.path.join(a, "inside.txt")),
        }
        for label, paths in cases.items():
            with self.subTest(label):
                result = self.check_new(*paths)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("collide", result.stdout)

    def test_an_alias_of_the_repository_root_is_accepted(self):
        alias = os.path.join(self.tmp, "alias")
        os.symlink(self.root, alias)
        path = os.path.join(alias, "target", "plans", "ok.txt")
        result = self.check_new(path)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout.strip(), os.path.join(self.plans, "ok.txt"), "the confined path is the alias-resolved one")


class CreateTests(SafeioBase):
    def test_fresh_dir_is_0700_and_a_second_creation_is_refused(self):
        path = os.path.join(self.plans, "RUN-1")
        args = ["fresh-dir", "--root", self.root, "--within-name", "target/plans", "--within", self.plans, "--path", path]
        self.assertEqual(run(SAFEIO, args).returncode, 0)
        self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o700")
        again = run(SAFEIO, args)
        self.assertEqual(again.returncode, 1)
        self.assertIn("never reused", again.stdout)

    def test_write_new_creates_0600_and_never_overwrites_or_follows_a_link(self):
        path = os.path.join(self.plans, "out.txt")
        first = run(SAFEIO, ["write-new", "--root", self.root, path], input="payload\n")
        self.assertEqual(first.returncode, 0, first.stdout)
        with open(path) as handle:
            self.assertEqual(handle.read(), "payload\n")
        self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o600")
        second = run(SAFEIO, ["write-new", "--root", self.root, path], input="OVERWRITE\n")
        self.assertEqual(second.returncode, 1)
        with open(path) as handle:
            self.assertEqual(handle.read(), "payload\n", "no O_TRUNC on an existing file")
        link = os.path.join(self.plans, "link.txt")
        os.symlink(self.canary, link)
        third = run(SAFEIO, ["write-new", "--root", self.root, link], input="THROUGH-LINK\n")
        self.assertEqual(third.returncode, 1)
        self.canary_ok()

    def test_a_directory_swapped_for_a_symlink_after_the_check_is_refused_at_open_time(self):
        """The check passed for a real directory; the directory is then replaced by a link: the O_NOFOLLOW walk refuses it."""
        sub = os.path.join(self.plans, "swap")
        os.makedirs(sub)
        os.rmdir(sub)
        os.symlink(self.tmp, sub)
        result = run(SAFEIO, ["write-new", "--root", self.root, os.path.join(sub, "x.txt")], input="x")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "x.txt")))

    def test_ensure_dir_creates_parents_0700_and_refuses_a_symlinked_component(self):
        deep = os.path.join(self.plans, "a", "b")
        args = ["ensure-dir", "--root", self.root, "--within-name", "target/plans", "--within", self.plans, "--path", deep]
        self.assertEqual(run(SAFEIO, args).returncode, 0)
        self.assertEqual(oct(os.stat(deep).st_mode & 0o777), "0o700")
        os.symlink(self.tmp, os.path.join(self.plans, "evil"))
        refused = run(SAFEIO, ["ensure-dir", "--root", self.root, "--within-name", "target/plans", "--within", self.plans, "--path", os.path.join(self.plans, "evil", "c")])
        self.assertEqual(refused.returncode, 1)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "c")))

    def test_check_file_accepts_only_a_real_regular_file_inside_the_directory(self):
        good = os.path.join(self.plans, "p.tfplan")
        open(good, "w").close()
        link = os.path.join(self.plans, "l.tfplan")
        os.symlink(good, link)
        base = ["check-file", "--root", self.root, "--within-name", "target/plans", "--within", self.plans]
        self.assertEqual(run(SAFEIO, base + [good]).returncode, 0)
        self.assertEqual(run(SAFEIO, base + [link]).returncode, 1)
        self.assertEqual(run(SAFEIO, base + [os.path.join(self.plans, "absent")]).returncode, 1)
        self.assertEqual(run(SAFEIO, base + [os.path.join(self.tmp, "canary.txt")]).returncode, 1)


class HelperOutputTests(SafeioBase):
    def test_stdout_new_creates_exclusively_and_leaves_an_existing_file_and_a_link_target_untouched(self):
        path = os.path.join(self.plans, "capture.json")
        ok = run(TIMEOUT, ["--seconds", "10", "--stdout-new", path, "--root", self.root, "--", "echo", "hello"])
        self.assertEqual(ok.returncode, 0, ok.stderr)
        with open(path) as handle:
            self.assertEqual(handle.read(), "hello\n")
        self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o600")
        again = run(TIMEOUT, ["--seconds", "10", "--stdout-new", path, "--root", self.root, "--", "echo", "SECOND"])
        self.assertEqual(again.returncode, 2, again.stderr)
        with open(path) as handle:
            self.assertEqual(handle.read(), "hello\n")
        link = os.path.join(self.plans, "capture-link.json")
        os.symlink(self.canary, link)
        marker = os.path.join(self.tmp, "started")
        linked = run(TIMEOUT, ["--seconds", "10", "--stdout-new", link, "--root", self.root, "--", "bash", "-c", "touch '%s'; echo X" % marker])
        self.assertEqual(linked.returncode, 2, linked.stderr)
        self.assertFalse(os.path.exists(marker), "the command was not started")
        self.canary_ok()

    def test_stdout_new_needs_a_root(self):
        result = run(TIMEOUT, ["--seconds", "5", "--stdout-new", os.path.join(self.plans, "x"), "--", "true"])
        self.assertEqual(result.returncode, 2)

    def test_the_legacy_stdout_and_output_options_refuse_a_symlink_leaf(self):
        link = os.path.join(self.tmp, "stdout-link")
        os.symlink(self.canary, link)
        result = run(TIMEOUT, ["--seconds", "5", "--stdout", link, "--", "echo", "X"])
        self.assertEqual(result.returncode, 2, result.stderr)
        result = run(TIMEOUT, ["--seconds", "5", "--output", link, "--", "echo", "X"])
        self.assertEqual(result.returncode, 2, result.stderr)
        self.canary_ok()

    def test_a_symlinked_trace_file_stops_the_helper_before_the_command_and_the_target_is_untouched(self):
        link = os.path.join(self.tmp, "trace-link")
        os.symlink(self.canary, link)
        marker = os.path.join(self.tmp, "started2")
        result = run(TIMEOUT, ["--seconds", "5", "--", "bash", "-c", "touch '%s'" % marker], env=dict(os.environ, SCHOLARCHAIN_TIMEOUT_LOG=link))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(os.path.exists(marker))
        self.canary_ok()

    def test_redact_append_to_requires_an_existing_log_refuses_links_and_appends(self):
        log = os.path.join(self.plans, "run.log")
        missing = run(REDACT, ["--append-to", log, "--root", self.root], input="x\n")
        self.assertEqual(missing.returncode, 1, "a confined log is created exclusively beforehand, never by the append")
        self.assertFalse(os.path.exists(log))
        self.assertEqual(run(SAFEIO, ["create-new", "--root", self.root, log]).returncode, 0)
        self.assertEqual(run(REDACT, ["--append-to", log, "--root", self.root], input="one 123456789012\n").returncode, 0)
        self.assertEqual(run(REDACT, ["--append-to", log, "--root", self.root], input="two\n").returncode, 0)
        with open(log) as handle:
            self.assertEqual(handle.read(), "one <acct>\ntwo\n")
        link = os.path.join(self.plans, "linked.log")
        os.symlink(self.canary, link)
        refused = run(REDACT, ["--append-to", link, "--root", self.root], input="THROUGH\n")
        self.assertEqual(refused.returncode, 1)
        unconfined = run(REDACT, ["--append-to", link], input="THROUGH\n")
        self.assertEqual(unconfined.returncode, 1)
        self.canary_ok()


if __name__ == "__main__":
    unittest.main()
