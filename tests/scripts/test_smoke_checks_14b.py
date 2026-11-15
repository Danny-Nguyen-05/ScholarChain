"""scripts/smoke-test.sh --checks (replan: the ALB/HTTPS pass definition runs health-only first), written independently by the
test-engineer from the requirement:

  * --checks LIST selects a subset of the six checks, which ALWAYS run in the canonical order healthz, readyz, query, evidence,
    idempotency, error-path, whatever order was typed;
  * a health-only selection (healthz and/or readyz) needs no API key: none is required, read or sent;
  * evidence and idempotency read the state of query, so naming either without query is a usage error (exit 2) and nothing is requested;
  * an unknown, duplicated or malformed name is a usage error; no --checks means all six;
  * a partial run says so in its single RESULT line ("only N of 6 checks ran ... not the full smoke test") and the full set says
    "all 6 checks passed"; a failing selected check still fails with exit 4 and its marker last.

The server is the loopback stub of test_smoke.py (the same contract); no other network is used.
"""
import unittest

import sc_support as S
from test_smoke import KEY, STEPS, Stub

ORDER = ["healthz", "readyz", "query", "evidence", "idempotency", "error-path"]


class Base(unittest.TestCase):
    def start(self, **behave):
        fx = S.Fixture(self)
        stub = Stub(**behave)
        self.addCleanup(stub.stop)
        return fx, stub

    def smoke(self, fx, stub, checks=None, key=True, extra=()):
        args = ["--url", stub.url] + (["--checks", checks] if checks is not None else []) + list(extra)
        env = {"SCHOLARCHAIN_SMOKE_API_KEY": KEY} if key else {}
        return fx.run("smoke-test.sh", args, env, timeout=120)

    def ran(self, run):
        return [s[len("smoke-"):] for s in run.steps() if s.startswith("smoke-") and s != "smoke-complete"]

    def paths(self, stub):
        return [(r["method"], r["path"]) for r in stub.requests]


class CanonicalOrder(Base):
    def test_the_default_runs_all_six_in_order_and_says_so(self):
        fx, stub = self.start()
        run = self.smoke(fx, stub)
        self.assertEqual((run.rc, run.status), (0, "PASS"), run.describe())
        self.assertEqual(self.ran(run), ORDER)
        self.assertIn("all 6 checks passed", run.result)
        self.assertNotIn("not the full smoke", run.result)

    def test_any_typed_order_runs_in_the_canonical_order(self):
        for typed in ("error-path,query,healthz", "query,error-path", "readyz,healthz", "idempotency,evidence,query", "error-path,idempotency,evidence,query,readyz,healthz"):
            with self.subTest(typed=typed):
                fx, stub = self.start()
                run = self.smoke(fx, stub, typed)
                self.assertEqual(run.rc, 0, run.describe())
                self.assertEqual(self.ran(run), [c for c in ORDER if c in typed.split(",")])
                self.assertEqual(len(run.results()), 1)

    def test_naming_all_six_is_the_full_smoke_in_any_order(self):
        fx, stub = self.start()
        run = self.smoke(fx, stub, "error-path,idempotency,evidence,query,readyz,healthz")
        self.assertEqual(self.ran(run), ORDER)
        self.assertIn("all 6 checks passed", run.result)
        self.assertNotIn("not the full smoke", run.result)

    def test_the_step_markers_are_the_documented_ones(self):
        self.assertEqual(STEPS, ["smoke-" + c for c in ORDER])


class HealthOnly(Base):
    def test_healthz_and_readyz_need_no_key_and_send_no_credentials(self):
        fx, stub = self.start()
        run = self.smoke(fx, stub, "healthz,readyz", key=False)
        self.assertEqual((run.rc, run.status), (0, "PASS"), run.describe())
        self.assertEqual(self.ran(run), ["healthz", "readyz"])
        self.assertEqual(self.paths(stub), [("GET", "/healthz"), ("GET", "/readyz")])
        self.assertTrue(all(r["auth"] is None for r in stub.requests), "no credential may be sent to a health probe")

    def test_a_key_in_the_environment_is_not_used_for_a_health_only_run(self):
        fx, stub = self.start()
        run = self.smoke(fx, stub, "healthz", key=True)
        self.assertEqual(run.rc, 0, run.describe())
        self.assertEqual(self.paths(stub), [("GET", "/healthz")])
        self.assertTrue(all(r["auth"] is None for r in stub.requests))
        self.assertNotIn(KEY, run.text)

    def test_every_other_check_still_needs_the_key(self):
        for checks in ("error-path", "healthz,error-path", "query", "healthz,readyz,query"):
            with self.subTest(checks=checks):
                fx, stub = self.start()
                run = self.smoke(fx, stub, checks, key=False)
                self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
                self.assertEqual(stub.requests, [], "nothing is requested before the key is found")

    def test_health_plus_error_path_is_a_valid_partial_run(self):
        fx, stub = self.start()
        run = self.smoke(fx, stub, "healthz,readyz,error-path")
        self.assertEqual(run.rc, 0, run.describe())
        self.assertEqual(self.ran(run), ["healthz", "readyz", "error-path"])
        posts = [r for r in stub.requests if r["method"] == "POST"]
        self.assertTrue(posts and all(p["auth"] != "Bearer " + KEY for p in posts), "the 401 path sends no valid key")


class Dependencies(Base):
    def test_evidence_and_idempotency_without_query_are_a_usage_error(self):
        for checks in ("evidence", "idempotency", "healthz,evidence", "readyz,idempotency,error-path", "evidence,idempotency"):
            with self.subTest(checks=checks):
                fx, stub = self.start()
                run = self.smoke(fx, stub, checks)
                self.assertEqual(run.rc, 2, run.describe())
                self.assertEqual(stub.requests, [], "a usage error requests nothing")
                self.assertEqual(run.calls, [])

    def test_with_query_they_are_accepted(self):
        for checks in ("query,evidence", "query,idempotency", "query,evidence,idempotency"):
            with self.subTest(checks=checks):
                fx, stub = self.start()
                run = self.smoke(fx, stub, checks)
                self.assertEqual(run.rc, 0, run.describe())
                self.assertEqual(self.ran(run), [c for c in ORDER if c in checks.split(",")])

    def test_unknown_duplicate_and_malformed_names_are_usage_errors(self):
        for checks in ("bogus", "healthz,bogus", "healthz,healthz", "healthz,,readyz", ",healthz", "healthz,", "HEALTHZ", "healthz readyz", "healthz;readyz", ""):
            with self.subTest(checks=checks):
                fx, stub = self.start()
                run = self.smoke(fx, stub, checks)
                if checks == "":
                    self.assertEqual(run.rc, 0, "an empty list means the default, all six (the option is simply unset)")
                    continue
                self.assertEqual(run.rc, 2, run.describe())
                self.assertEqual(stub.requests, [])


class PartialRunIsNeverMistakenForTheFullSmoke(Base):
    def test_the_single_result_line_names_the_count_the_checks_and_that_it_is_partial(self):
        fx, stub = self.start()
        run = self.smoke(fx, stub, "healthz,readyz", key=False)
        self.assertEqual(len(run.results()), 1, run.describe())
        self.assertTrue(run.lines()[-1].startswith("RESULT: PASS"))
        self.assertIn("only 2 of 6 checks ran", run.result)
        self.assertIn("healthz readyz", run.result)
        self.assertIn("not the full smoke test", run.result)
        self.assertNotIn("all 6", run.result)

    def test_every_partial_size_reports_its_own_count(self):
        sets = {"healthz": 1, "healthz,readyz": 2, "healthz,readyz,query": 3, "healthz,readyz,query,evidence": 4,
                "healthz,readyz,query,evidence,idempotency": 5}
        for checks, n in sets.items():
            with self.subTest(checks=checks):
                fx, stub = self.start()
                run = self.smoke(fx, stub, checks)
                self.assertEqual(run.rc, 0, run.describe())
                self.assertIn("only %d of 6 checks ran" % n, run.result)
                self.assertIn("not the full smoke test", run.result)

    def test_a_failing_selected_check_fails_with_exit_4_and_its_marker_last(self):
        fx, stub = self.start(health_status=500)
        run = self.smoke(fx, stub, "healthz,readyz", key=False)
        self.assertEqual(run.rc, 4, run.describe())
        self.assertEqual(run.steps()[-1], "smoke-healthz")
        self.assertEqual(len(run.results()), 1)
        self.assertNotIn("smoke-readyz", run.steps(), "the run stops at the first failure")

    def test_the_key_is_never_printed_in_a_partial_run(self):
        fx, stub = self.start()
        run = self.smoke(fx, stub, "healthz,query,error-path")
        self.assertEqual(run.rc, 0, run.describe())
        self.assertNotIn(KEY, run.text)
        self.assertEqual(run.calls, [], "the smoke test calls no cloud tool")


if __name__ == "__main__":
    unittest.main()
