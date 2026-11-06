#!/usr/bin/env python3
"""Run one unittest suite and print an exact, machine-readable summary (stdlib only; python3 -I).

  suite_run.py --start-dir DIR [--pattern 'test_*.py'] [--require-class module.Class,...] [--enforce-required]

The tests run through unittest's own TextTestRunner, so its normal report ("Ran N tests in ...", OK or FAILED) is
unchanged. Afterwards, on stdout:

  SUITE-SUMMARY ran=N executed=E skipped_tests=M skipped_classes=K failures=F errors=X
  SUITE-SKIPPED-CLASS <setUpClass description> :: <reason>      one per class-level skip
  SUITE-SKIPPED-TEST <test id> :: <reason>                       one per method-level skip
  SUITE-REQUIRED <module.Class> executed=N skipped=M status=ok|SKIPPED|MISSING

unittest's "Ran N" counts the tests that were collected and started: a class-level skip (SkipTest in setUpClass) adds
ONE skip but no test to "Ran", while a method-level skip adds one of each. So the number of tests that really
EXECUTED is Ran minus the METHOD-level skips only (a "Ran - skipped" calculation undercounts after a class skip), and
the skipped classes are listed separately.

--require-class names classes whose tests must run (the real-Terraform proofs): one that is skipped (at class or method
level) or has no executed test is reported SKIPPED or MISSING. With --enforce-required that also fails the run:
"SUITE-REQUIRED-FAILED: ..." is printed and the exit code is 3 (1 when a test failed, 0 otherwise).
"""
import argparse
import re
import sys
import unittest


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed_by_class = {}
        self.skipped_by_class = {}

    @staticmethod
    def _key(test):
        return type(test).__module__ + "." + type(test).__qualname__

    def _executed(self, test):
        if isinstance(test, unittest.TestCase):
            key = self._key(test)
            self.executed_by_class[key] = self.executed_by_class.get(key, 0) + 1

    def addSuccess(self, test):
        super().addSuccess(test)
        self._executed(test)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._executed(test)

    def addError(self, test, err):
        super().addError(test, err)
        self._executed(test)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._executed(test)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._executed(test)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        if isinstance(test, unittest.TestCase):
            key = self._key(test)
            self.skipped_by_class[key] = self.skipped_by_class.get(key, 0) + 1


def describe(holder):
    return str(getattr(holder, "description", holder))


def one_line(text):
    return " ".join(str(text).split())[:200]


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-dir", required=True)
    parser.add_argument("--pattern", default="test_*.py")
    parser.add_argument("--require-class", default="")
    parser.add_argument("--enforce-required", action="store_true")
    args = parser.parse_args(argv)

    suite = unittest.TestLoader().discover(args.start_dir, pattern=args.pattern)
    runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=1, resultclass=Result)
    result = runner.run(suite)

    method_skips = [(test, reason) for test, reason in result.skipped if isinstance(test, unittest.TestCase)]
    class_skips = [(test, reason) for test, reason in result.skipped if not isinstance(test, unittest.TestCase)]
    executed = result.testsRun - len(method_skips)
    print(
        "SUITE-SUMMARY ran=%d executed=%d skipped_tests=%d skipped_classes=%d failures=%d errors=%d"
        % (result.testsRun, executed, len(method_skips), len(class_skips), len(result.failures), len(result.errors))
    )
    for holder, reason in class_skips:
        print("SUITE-SKIPPED-CLASS %s :: %s" % (describe(holder), one_line(reason)))
    for test, reason in method_skips:
        print("SUITE-SKIPPED-TEST %s :: %s" % (test.id(), one_line(reason)))

    problems = []
    for name in [item for item in re.split(r"[,\s]+", args.require_class) if item]:
        skipped = result.skipped_by_class.get(name, 0) + sum(1 for holder, _reason in class_skips if "(%s)" % name in describe(holder))
        ran = result.executed_by_class.get(name, 0)
        if skipped:
            status = "SKIPPED"
        elif ran == 0:
            status = "MISSING"
        else:
            status = "ok"
        print("SUITE-REQUIRED %s executed=%d skipped=%d status=%s" % (name, ran, skipped, status))
        if status != "ok":
            problems.append("%s %s" % (name, status))
    if problems and args.enforce_required:
        print("SUITE-REQUIRED-FAILED: a required real-Terraform test class did not run (%s); a skip is not a pass" % "; ".join(problems))
    if not result.wasSuccessful():
        return 1
    if problems and args.enforce_required:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
