"""timeout.py: whole-process-group kill, exit codes, logging. Hand-derived expectations."""
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest

HELPER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib", "timeout.py")


def run_helper(args, **kwargs):
    return subprocess.run([sys.executable, "-I", HELPER] + args, capture_output=True, text=True, timeout=60, **kwargs)


def pid_gone(pid, wait=5.0):
    deadline = time.time() + wait
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        # A killed, unreaped child can linger as a zombie for a moment: treat 'Z' as gone.
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
        if state.startswith("Z") or not state:
            return True
        time.sleep(0.1)
    return False


class TimeoutHelperTest(unittest.TestCase):
    def test_grandchild_is_killed_with_the_group_and_exit_is_124(self):
        with tempfile.TemporaryDirectory() as tmp:
            pidfile = os.path.join(tmp, "grandchild.pid")
            script = "sleep 300 & echo $! > '%s'; wait" % pidfile
            started = time.time()
            result = run_helper(["--seconds", "1", "--grace", "1", "--", "bash", "-c", script])
            self.assertEqual(result.returncode, 124)
            self.assertLess(time.time() - started, 15)
            with open(pidfile) as handle:
                grandchild = int(handle.read().strip())
            self.assertTrue(pid_gone(grandchild), "grandchild sleep %d survived the group kill" % grandchild)

    def test_sigterm_ignoring_child_is_killed_with_sigkill_after_grace(self):
        with tempfile.TemporaryDirectory() as tmp:
            pidfile = os.path.join(tmp, "stubborn.pid")
            script = "trap '' TERM; sleep 300 & echo $! > '%s'; while true; do sleep 1; done" % pidfile
            result = run_helper(["--seconds", "1", "--grace", "1", "--", "bash", "-c", script])
            self.assertEqual(result.returncode, 124)
            with open(pidfile) as handle:
                grandchild = int(handle.read().strip())
            self.assertTrue(pid_gone(grandchild))

    def test_child_exit_codes_propagate(self):
        for code in (0, 1, 7, 42):
            result = run_helper(["--seconds", "10", "--", "bash", "-c", "exit %d" % code])
            self.assertEqual(result.returncode, code)

    def test_missing_command_returns_127(self):
        result = run_helper(["--seconds", "5", "--", "/nonexistent/definitely-not-a-command"])
        self.assertEqual(result.returncode, 127)

    def test_signal_death_returns_128_plus_signal(self):
        result = run_helper(["--seconds", "10", "--", "bash", "-c", "kill -KILL $$"])
        self.assertEqual(result.returncode, 128 + signal.SIGKILL)

    def test_output_capture_and_separate_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            combined = os.path.join(tmp, "out.txt")
            data = os.path.join(tmp, "data.txt")
            result = run_helper(
                ["--seconds", "10", "--output", combined, "--stdout", data, "--", "bash", "-c", "echo to-stdout; echo to-stderr >&2"]
            )
            self.assertEqual(result.returncode, 0)
            with open(data) as handle:
                self.assertEqual(handle.read(), "to-stdout\n")
            with open(combined) as handle:
                self.assertEqual(handle.read(), "to-stderr\n")
            self.assertEqual(oct(os.stat(data).st_mode & 0o777), "0o600")

    def test_helper_invocation_log_records_timeout_and_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "t.log")
            env = dict(os.environ, SCHOLARCHAIN_TIMEOUT_LOG=log)
            run_helper(["--seconds", "9", "--", "true"], env=env)
            with open(log) as handle:
                self.assertEqual(handle.read(), "timeout=9 true\n")

    def test_usage_error_without_command(self):
        self.assertEqual(run_helper(["--seconds", "5"]).returncode, 2)

    def test_non_finite_or_non_positive_limits_are_rejected_before_any_child_is_spawned(self):
        """N1: nan, inf, zero and negative limits exit 2 and never start the command."""
        for seconds in ("nan", "inf", "-inf", "0", "-5", "NaN", "Infinity"):
            for flag in ("--seconds", "--grace"):
                with self.subTest("%s %s" % (flag, seconds)):
                    with tempfile.TemporaryDirectory() as tmp:
                        marker = os.path.join(tmp, "started")
                        args = ["--seconds", "5", "--grace", "1"]
                        args[args.index(flag) + 1] = seconds
                        result = run_helper(args + ["--", "bash", "-c", "touch '%s'" % marker])
                        if flag == "--grace" and seconds in ("0",):
                            self.assertEqual(result.returncode, 0)  # a zero grace period is legal
                            continue
                        self.assertEqual(result.returncode, 2, "%s %s: %s" % (flag, seconds, result.stderr))
                        self.assertFalse(os.path.exists(marker), "the child must not be spawned")

    def test_helper_invocation_log_is_redacted_before_it_is_written(self):
        """F4: account-bearing registry hosts, secret environment values and registered values never reach the trace."""
        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "t.log")
            values = os.path.join(tmp, "values")
            with open(values, "w") as handle:
                handle.write("S\tREGISTERED-PRIVATE-VALUE-5521\nA\t777788889999\n")
            env = dict(os.environ, SCHOLARCHAIN_TIMEOUT_LOG=log, SC_REDACT_FILE=values, FAKE_API_TOKEN="ENV-SECRET-TOKEN-VALUE-3319")
            run_helper(
                ["--seconds", "9", "--", "echo", "123456789012.dkr.ecr.us-east-2.amazonaws.com/repo:tag", "REGISTERED-PRIVATE-VALUE-5521", "ENV-SECRET-TOKEN-VALUE-3319", "777788889999", "sha-" + "a" * 8 + "123456789012" + "b" * 8],
                env=env,
            )
            with open(log) as handle:
                text = handle.read()
        self.assertEqual(
            text,
            "timeout=9 echo <acct>.dkr.ecr.us-east-2.amazonaws.com/repo:tag <redacted> <redacted> <acct> sha-aaaaaaaa123456789012bbbbbbbb\n",
            "hand-derived: the host account, the registered and env secrets and the standalone account become placeholders; a digit run inside a hex-like token is untouched",
        )

    def test_trace_is_not_written_when_the_redactor_cannot_be_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = os.path.join(tmp, "lib")
            os.makedirs(lib)
            with open(HELPER) as source, open(os.path.join(lib, "timeout.py"), "w") as copy:
                copy.write(source.read())  # a copy WITHOUT redact.py next to it
            log = os.path.join(tmp, "t.log")
            result = subprocess.run(
                [sys.executable, "-I", os.path.join(lib, "timeout.py"), "--seconds", "5", "--", "true"],
                capture_output=True, text=True, timeout=60, env=dict(os.environ, SCHOLARCHAIN_TIMEOUT_LOG=log),
            )
            self.assertEqual(result.returncode, 0)
            self.assertFalse(os.path.exists(log), "no redactor means no raw argv is persisted")


if __name__ == "__main__":
    unittest.main()
