"""Independent refusal-path tests for scripts/run-bounded-pipeline.sh (Subphase 13B, test-engineer).

Expectations come from scripts/README.md ("Subphase 13B"), the script's --help, plan sections 7.1-7.3a and 9 and the
user's Step 0 answers (G6 caps USD 3 per run / 3 runs / USD 2.52 cumulative since the 2026-11-09 caps = planned use decision, headroom floors, ceilings, approval record keys). Every refusal asserts the exit
code and the STEP marker / RESULT line, and that no cloud call happened before the refusal.
"""
import datetime
import json
import re
import unittest

import sc_support as S


class Base(unittest.TestCase):
    def fx(self, **kw):
        return S.Fixture(self, **kw)

    def assert_refused(self, run, code=3, step=None, no_aws=True, no_steps_printed=True):
        self.assertEqual(run.rc, code, run.describe())
        self.assertEqual(len(run.results()), 1, "exactly one RESULT line expected\n" + run.describe())
        self.assertEqual(run.status, "REFUSED", run.describe())
        if step is not None:
            self.assertIn("step=%s" % step, run.result, run.describe())
        if no_aws:
            self.assertEqual(run.calls, [], "a fake binary was called before the refusal: %s" % run.calls)
        if no_steps_printed:
            self.assertNotIn("STEP: step-stage-in", run.out, "the run printed steps although it was refused")


class PipelineCeilingRefusals(Base):
    """Plan section 9, Pipeline: 'Ceiling violation refuses'. Capacity, runtime and the Phase 4 config ceilings."""

    def test_capacity_above_four_instances_is_refused(self):
        # 1 primary + 4 core = 5 > PIPELINE_MAX_CAPACITY (4)
        fx = self.fx()
        self.assert_refused(fx.dry(core_count=4), step="plan")
        # 1 primary + 2 core + 2 task = 5 > 4
        self.assert_refused(fx.dry(core_count=2, max_task_count=2), step="plan")

    def test_capacity_exactly_four_is_accepted(self):
        fx = self.fx()
        run = fx.dry(core_count=2, max_task_count=1)
        self.assertEqual((run.rc, run.status), (0, "DRY-RUN"), run.describe())
        self.assertIn("max-capacity=4", run.out)

    def test_runtime_outside_ten_to_one_eighty_minutes_is_refused(self):
        fx = self.fx()
        for minutes in (181, 9, 0):
            with self.subTest(minutes=minutes):
                run = fx.dry(max_runtime_minutes=minutes, budget_usd=3)
                self.assertNotEqual(run.rc, 0, run.describe())
                self.assertIn(run.status, ("REFUSED",), run.describe())
                self.assertEqual(run.calls, [])

    def test_runtime_upper_bound_and_a_short_run_are_accepted(self):
        fx = self.fx()
        for minutes in (20, 180):
            with self.subTest(minutes=minutes):
                run = fx.dry(max_runtime_minutes=minutes, instance_type="m5.xlarge", core_count=1)
                self.assertEqual(run.rc, 0, run.describe())
                self.assertIn("max-runtime-minutes: %d" % minutes, run.out)

    def test_runtime_range_is_exactly_ten_to_one_eighty_minutes(self):
        """Resolved finding D1. --help and scripts/README.md: the accepted range is exactly 10 to 180 minutes; each step
        gets its weighted percent of the cap but at least 30 s (PIPELINE_MIN_STEP_SECONDS), which the smallest 5 percent
        share of a 10-minute run equals, so 10 is a real minimum and 9 is refused at step plan (exit 3). At 10 minutes
        (600 s) the six step timeouts must still sum to no more than the cap."""
        fx = self.fx()
        run = fx.dry(max_runtime_minutes=10)
        self.assertEqual((run.rc, run.status), (0, "DRY-RUN"), run.describe())
        timeouts = {m.group(1): int(m.group(2)) for m in
                    (re.match(r"STEP-TIMEOUT: (\S+) (\d+)s", l) for l in run.lines()) if m}
        self.assertEqual(sorted(timeouts), sorted(S.STEP_NAMES))
        self.assertLessEqual(sum(timeouts.values()), 10 * 60, "step timeouts may never exceed the hard runtime cap")
        self.assertGreaterEqual(min(timeouts.values()), 30)
        self.assertEqual(run.calls, [])
        refused = fx.dry(max_runtime_minutes=9)
        self.assertEqual((refused.rc, refused.status), (3, "REFUSED"), refused.describe())
        self.assertIn("step=plan", refused.result)
        self.assertEqual(refused.calls, [])
        above = fx.dry(max_runtime_minutes=181)
        self.assertEqual((above.rc, above.status), (3, "REFUSED"), above.describe())
        self.assertIn("step=plan", above.result)
        zero = fx.dry(max_runtime_minutes=0)  # refused too; the step that notices it (estimate or plan) is not part of the contract
        self.assertEqual((zero.rc, zero.status), (3, "REFUSED"), zero.describe())
        self.assertEqual(zero.calls, [])

    def test_each_phase4_config_ceiling_refuses_one_above_and_accepts_the_inclusive_value(self):
        for field, ceiling in S.CEILINGS.items():
            for value, accepted in ((ceiling, True), (ceiling + 1, False)):
                with self.subTest(field=field, value=value):
                    fx = self.fx()
                    cfg = dict(S.SAFE_PREP)
                    cfg[field] = value
                    S.Fixture.write_json(fx.repo / "inputs/prep.json", cfg)
                    fx.commit_all()
                    run = fx.dry()
                    if accepted:
                        self.assertEqual((run.rc, run.status), (0, "DRY-RUN"), run.describe())
                    else:
                        self.assert_refused(run, step="plan")

    def test_config_with_missing_or_non_numeric_ceiling_field_fails_closed(self):
        for label, mutate in (
            ("missing", lambda c: c.pop("reducerCount")),
            ("string", lambda c: c.__setitem__("reducerCount", "2")),
            ("bool", lambda c: c.__setitem__("reducerCount", True)),
            ("null", lambda c: c.__setitem__("maxRecordBytes", None)),
        ):
            with self.subTest(case=label):
                fx = self.fx()
                cfg = dict(S.SAFE_PREP)
                mutate(cfg)
                S.Fixture.write_json(fx.repo / "inputs/prep.json", cfg)
                self.assert_refused(fx.dry(), step="plan")

    def test_unreadable_hadoop_config_is_refused(self):
        fx = self.fx()
        (fx.repo / "inputs/prep.json").write_text("{ not json")
        self.assert_refused(fx.dry(), step="plan")

    def test_pinned_ceiling_values_are_the_phase4_numbers(self):
        fx = self.fx()
        run = fx.dry()
        line = run.grep(r"^PLAN: ceilings:")[0]
        for expected in ("maxLocalSampleRecords<=12000", "reducerCount<=8", "maxCandidateBlockSize<=256",
                         "maxCandidatePairsPerBlock<=4096", "maxAuthorTeamSize<=64", "maxRecordBytes<=8388608",
                         "maxXmlEntityExpansion<=8388608"):
            self.assertIn(expected, line)

    def test_only_the_sample_record_ceiling_differs_from_phase4_and_the_smoke_script_keeps_1000(self):
        """USD 25 replan: the pipeline's maxLocalSampleRecords ceiling is 12,000 (pipeline-specific); phase4-emr-smoke.sh keeps 1000 and
        the other six ceilings are equal in the smoke script, the committed config and the fixture constants."""
        smoke = dict(re.findall(r"^readonly (SMOKE_MAX_[A-Z_]+)=(\d+)$", (S.REPO / "scripts/phase4-emr-smoke.sh").read_text(), re.M))
        conf = dict(re.findall(r"^(PIPELINE_CEILING_[A-Z_]+)=(\d+)$", (S.REPO / "scripts/config/release.conf").read_text(), re.M))
        pairs = {  # fixture field: (smoke constant, pipeline pin)
            "maxLocalSampleRecords": ("SMOKE_MAX_LOCAL_SAMPLE_RECORDS", "PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS"),
            "reducerCount": ("SMOKE_MAX_REDUCER_COUNT", "PIPELINE_CEILING_REDUCER_COUNT"),
            "maxCandidateBlockSize": ("SMOKE_MAX_CANDIDATE_BLOCK_SIZE", "PIPELINE_CEILING_MAX_CANDIDATE_BLOCK_SIZE"),
            "maxCandidatePairsPerBlock": ("SMOKE_MAX_CANDIDATE_PAIRS_PER_BLOCK", "PIPELINE_CEILING_MAX_CANDIDATE_PAIRS_PER_BLOCK"),
            "maxAuthorTeamSize": ("SMOKE_MAX_AUTHOR_TEAM_SIZE", "PIPELINE_CEILING_MAX_AUTHOR_TEAM_SIZE"),
            "maxRecordBytes": ("SMOKE_MAX_RECORD_BYTES", "PIPELINE_CEILING_MAX_RECORD_BYTES"),
            "maxXmlEntityExpansion": ("SMOKE_MAX_XML_ENTITY_EXPANSION", "PIPELINE_CEILING_MAX_XML_ENTITY_EXPANSION"),
        }
        self.assertEqual(int(smoke["SMOKE_MAX_LOCAL_SAMPLE_RECORDS"]), 1000)
        self.assertEqual(int(conf["PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS"]), 12000)
        self.assertEqual(S.CEILINGS["maxLocalSampleRecords"], 12000)
        for field, (smoke_key, pin) in pairs.items():
            if field == "maxLocalSampleRecords":
                continue
            with self.subTest(field=field):
                self.assertEqual(int(conf[pin]), int(smoke[smoke_key]), "the six other ceilings stay equal to Phase 4")
                self.assertEqual(S.CEILINGS[field], int(smoke[smoke_key]))

    def test_environment_cannot_raise_a_pinned_cap(self):
        fx = self.fx()
        env = {"PIPELINE_MAX_CAPACITY": "100", "EMR_MAX_RUN_USD": "100", "PIPELINE_MAX_RUNTIME_MINUTES": "9999",
               "PIPELINE_CEILING_REDUCER_COUNT": "999"}
        run = fx.dry(extra_env=env, core_count=4)
        self.assert_refused(run, step="plan")
        self.assertIn("CONFIG-IGNORED", run.out)
        run = fx.dry(extra_env=env, max_runtime_minutes=181)
        self.assertEqual(run.rc, 3, run.describe())


class PipelineG6Refusals(Base):
    """Step 0 answer 4: USD 3 per run, 3 live runs, USD 2.52 cumulative (planned use 3 x 0.84; it was 3.00, and 9.50 before the USD 25 replan), estimate printed, unconfirmed pricing refuses."""

    def test_estimate_formula_is_instances_times_hourly_rate_times_runtime_plus_idle_tail_rounded_up(self):
        """13C finding B3, derived by hand from scripts/config/emr-pricing.conf (m5.xlarge EC2 0.192 + EMR 0.048 =
        0.240 USD per instance-hour; m5.2xlarge 0.384 + 0.096 = 0.480) and release.conf (idle cap 900 s):
        estimate = instances x hourly x (runtime_minutes x 60 + 900) / 3600, rounded UP to the cent."""
        fx = self.fx()
        # 2 instances x 0.240 x (3600 + 900) / 3600 = 0.48 x 1.25 = 0.60
        run = fx.dry()
        self.assertIn("ESTIMATE-USD: 0.60", run.out)
        # 2 x 0.240 x (660 + 900) / 3600 = 0.48 x 0.43333.. = 0.208 -> rounded UP to the cent = 0.21
        run = fx.dry(max_runtime_minutes=11)
        self.assertIn("ESTIMATE-USD: 0.21", run.out)
        # m5.2xlarge, 4 instances x 0.480 x (4500 + 900) / 3600 = 1.92 x 1.5 = 2.88
        run = fx.dry(instance_type="m5.2xlarge", core_count=3, max_runtime_minutes=75)
        self.assertEqual(run.rc, 0, run.describe())
        self.assertIn("ESTIMATE-USD: 2.88", run.out)
        # 3 x 0.240 x (5400 + 900) / 3600 = 0.72 x 1.75 = 1.26 (core 2, 90 minutes)
        run = fx.dry(core_count=2, max_runtime_minutes=90)
        self.assertIn("ESTIMATE-USD: 1.26", run.out)

    def test_the_idle_tail_is_part_of_the_estimate_and_follows_max_idle_seconds(self):
        """B3: with the default 900 s idle cap the estimate is 0.60 (not 0.48 = no tail). A tighter --max-idle-seconds
        shrinks the tail: 2 x 0.240 x (3600 + S) / 3600 -> S=60: 0.488 -> 0.49; S=300: 0.52; S=600: 0.56; S=900: 0.60."""
        fx = self.fx()
        for idle, want in ((60, "0.49"), (300, "0.52"), (600, "0.56"), (900, "0.60")):
            with self.subTest(idle=idle):
                self.assertIn("ESTIMATE-USD: %s" % want, fx.dry(max_idle_seconds=idle).out)
        self.assertNotIn("ESTIMATE-USD: 0.48", fx.dry().out, "the idle tail must not be dropped from the estimate")

    def test_idle_tail_changes_which_runs_pass_the_three_dollar_cap(self):
        """B3 boundary values (4 x m5.xlarge = 0.960 USD per hour, runtime in minutes M): the billed time is 60M + 900 s.
        M=171: 10260 + 900 = 11160 s -> 0.96 x 3.1 = 2.976 -> 2.98 (allowed).
        M=172: 11220 s -> 0.96 x 3.11666.. = 2.992 -> rounded UP to 3.00: exactly the cap, which is not above it (allowed).
        M=173: 11280 s -> 0.96 x 3.13333.. = 3.008 -> 3.01 (refused, although 173 minutes alone cost only 2.77).
        M=180 (the runtime maximum): 11700 s -> 0.96 x 3.25 = 3.12 (refused)."""
        fx = self.fx()
        for minutes, want in ((171, "2.98"), (172, "3.00")):
            with self.subTest(allowed=minutes):
                ok = fx.dry(core_count=3, max_runtime_minutes=minutes)
                self.assertEqual((ok.rc, ok.status), (0, "DRY-RUN"), ok.describe())
                self.assertIn("ESTIMATE-USD: %s" % want, ok.out)
        for minutes, want in ((173, "3.01"), (180, "3.12")):
            with self.subTest(refused=minutes):
                over = fx.dry(core_count=3, max_runtime_minutes=minutes)
                self.assert_refused(over)
                self.assertIn("G6", over.text)
                self.assertIn(want, over.text)

    def test_estimate_above_the_three_dollar_cap_is_refused_even_in_a_dry_run(self):
        fx = self.fx()
        # 4 x 0.48 x (7200 + 900) / 3600 = 1.92 x 2.25 = 4.32 > 3
        run = fx.dry(instance_type="m5.2xlarge", core_count=3, max_runtime_minutes=120, budget_usd=3)
        self.assert_refused(run)
        self.assertIn("G6", run.text)

    def test_declared_budget_above_cap_or_below_estimate_is_refused(self):
        fx = self.fx()
        self.assert_refused(fx.dry(budget_usd="3.01"))
        self.assert_refused(fx.dry(budget_usd="0.50"))  # estimate 0.60 (with the idle tail)
        self.assert_refused(fx.dry(budget_usd="0.59"))
        self.assertEqual(fx.dry(budget_usd="0.60").rc, 0, "a budget equal to the estimate is allowed")

    def test_fourth_run_is_refused_on_execute_and_reported_in_a_dry_run(self):
        fx = self.fx()
        fx.write_ledger(["0.10", "0.10", "0.10"])
        dry = fx.dry()
        self.assertEqual((dry.rc, dry.status), (0, "DRY-RUN"), dry.describe())
        self.assertIn("G6-STATUS: --execute would be refused", dry.out)
        run = fx.execute()
        self.assert_refused(run, step="g6-gate")
        self.assertIn("3", run.result)

    def test_two_recorded_runs_still_allow_a_third(self):
        fx = self.fx()
        fx.write_ledger(["0.10", "0.10"])
        run = fx.execute()
        self.assertEqual(run.rc, 0, run.describe())

    def test_cumulative_total_above_the_cap_is_refused_and_exactly_the_cap_is_allowed(self):
        """Phase 14B caps = planned use (user, 2026-11-09): EMR_CUMULATIVE_CAP_USD is 2.52 = 3 runs x 0.84 (it was 3.00, and 9.50
        before the USD 25 replan). The sum of the recorded estimates plus this run's estimate is refused only when ABOVE 2.52
        (inclusive boundary). Hand-derived:
        default run: 2 instances x 0.240 x (3600 + 900) / 3600 = 0.60;
        mid run: 3 instances x 0.240 x (5400 + 900) / 3600 = 1.26;
        big run: 4 x m5.2xlarge 0.480 x (4500 + 900) / 3600 = 2.88, which alone is above 2.52."""
        # default run (0.60): 0.96 + 0.96 + 0.60 = 2.52 exactly -> allowed; 0.96 + 0.97 + 0.60 = 2.53 -> refused
        exact = self.fx()
        exact.write_ledger(["0.96", "0.96"])
        run = exact.execute()
        self.assertEqual(run.rc, 0, run.describe())
        self.assertIn("LEDGER-RESERVED", run.out)
        over = self.fx()
        over.write_ledger(["0.96", "0.97"])
        run = over.execute()
        self.assert_refused(run, step="g6-gate")
        self.assertIn("cumulative", run.text)
        # a ledger that the 3.00 cap accepted (1.20 + 1.20 + 0.60 = 3.00) is refused under 2.52
        old_world = self.fx()
        old_world.write_ledger(["1.20", "1.20"])
        self.assert_refused(old_world.execute(), step="g6-gate")
        # mid run (1.26): 1.26 + 1.26 = 2.52 exactly -> allowed; 1.26 + 1.27 = 2.53 -> refused; an empty ledger is allowed (1.26 < 2.52)
        mid = dict(core_count=2, max_runtime_minutes=90)
        mid_groups = {"InstanceGroups": [
            {"InstanceGroupType": "MASTER", "InstanceType": "m5.xlarge", "RequestedInstanceCount": 1, "RunningInstanceCount": 1},
            {"InstanceGroupType": "CORE", "InstanceType": "m5.xlarge", "RequestedInstanceCount": 2, "RunningInstanceCount": 2}]}
        for ledger, allowed in (([], True), (["1.26"], True), (["1.27"], False)):
            with self.subTest(ledger=ledger, allowed=allowed):
                fx = self.fx()
                fx.update_scenario(groups=mid_groups)
                if ledger:
                    fx.write_ledger(ledger)
                run = fx.execute(pipeline_over=mid, capacity="3", runtime="90")
                if allowed:
                    self.assertEqual(run.rc, 0, run.describe())
                    self.assertIn("LEDGER-RESERVED", run.out)
                else:
                    self.assert_refused(run, step="g6-gate")
                    self.assertIn("cumulative", run.text)
        # big run (2.88) is within the per-run cap of 3.00 but above the cumulative 2.52, so even an empty ledger refuses it
        big = dict(instance_type="m5.2xlarge", core_count=3, max_runtime_minutes=75)
        big_groups = {"InstanceGroups": [
            {"InstanceGroupType": "MASTER", "InstanceType": "m5.2xlarge", "RequestedInstanceCount": 1, "RunningInstanceCount": 1},
            {"InstanceGroupType": "CORE", "InstanceType": "m5.2xlarge", "RequestedInstanceCount": 3, "RunningInstanceCount": 3}]}
        fx = self.fx()
        fx.update_scenario(groups=big_groups)
        run = fx.execute(pipeline_over=big, capacity="4", runtime="75")
        self.assert_refused(run, step="g6-gate")
        self.assertIn("cumulative", run.text)

    def test_unreadable_ledger_is_never_read_as_empty(self):
        fx = self.fx()
        path = fx.ledger_path
        path.parent.mkdir(parents=True)
        path.write_text("this is not json\n")
        self.assert_refused(fx.execute(), step="g6-gate")

    def test_unconfirmed_pricing_refuses_execute_before_any_cloud_call(self):
        fx = self.fx()
        args, _ = fx.exec_ready()
        fx.log.write_text("")
        run = fx.run("run-bounded-pipeline.sh", args, fx.exec_env(confirmed=False))
        self.assert_refused(run, step="g6-gate")
        self.assertIn("pricing", run.result.lower())

    def test_repository_pricing_file_is_read_as_is_and_cannot_be_replaced_without_the_test_config(self):
        """The committed scripts/config/emr-pricing.conf is the file the pipeline reads under the repository config. Its flag line
        is exactly true or false (the human sets it; the value is not asserted here, so the test holds in both states), a
        SCHOLARCHAIN_PRICING_FILE without the test-only SCHOLARCHAIN_CONFIG_FILE is ignored (announced), and a copy of the committed
        file with the flag rewritten to false refuses --execute at the g6-gate with a pricing reason."""
        fx = self.fx()
        committed = (S.REPO / "scripts/config/emr-pricing.conf").read_text()
        flags = re.findall(r"^EMR_PRICING_CONFIRMED_BY_HUMAN=(.*)$", committed, re.M)
        self.assertEqual(len(flags), 1, "exactly one EMR_PRICING_CONFIRMED_BY_HUMAN line expected")
        self.assertIn(flags[0], ("true", "false"))
        args, _ = fx.exec_ready()
        # (a) a false copy offered under the repository config is not honoured: announced and ignored, so the committed value decides
        fx.log.write_text("")
        false_copy = fx.pricing_file(confirmed=False)
        self.assertEqual(len(re.findall(r"^EMR_PRICING_CONFIRMED_BY_HUMAN=false$", false_copy.read_text(), re.M)), 1)
        ignored = fx.run("run-bounded-pipeline.sh", args, {"AWS_PROFILE": "test-profile", "SCHOLARCHAIN_PRICING_FILE": str(false_copy)})
        self.assertIn("PRICING-FILE-IGNORED", ignored.out, ignored.describe())
        self.assertNotIn("PRICING-FILE: using", ignored.out, ignored.describe())
        self.assertEqual(ignored.rc, 3, ignored.describe())
        self.assertEqual(ignored.calls, [], "a fake binary was called before the refusal: %s" % ignored.calls)
        if flags[0] == "false":
            self.assertIn("step=g6-gate", ignored.result, ignored.describe())
            self.assertIn("pricing", ignored.result.lower())
        else:
            self.assertNotIn("pricing", ignored.result.lower(), "the ignored false copy must not make the committed true file refuse as unconfirmed\n" + ignored.describe())
        # (b) a copy of the committed file with the flag false, through the documented test config, refuses at the g6-gate
        fx.log.write_text("")
        run = fx.run("run-bounded-pipeline.sh", args, fx.exec_env(confirmed=False))
        self.assert_refused(run, step="g6-gate")
        self.assertIn("pricing", run.result.lower())

    def test_environment_cannot_confirm_pricing_or_inject_rates(self):
        """Run against a copy of the committed pricing file with the flag rewritten to false (test config), so the outcome does not
        depend on the flag value the human has committed: the environment's true flag and a 0.0001 rate are ignored."""
        fx = self.fx()
        args, _ = fx.exec_ready()
        fx.log.write_text("")
        env = fx.exec_env(confirmed=False)
        env.update({"AWS_PROFILE": "p", "EMR_PRICING_CONFIRMED_BY_HUMAN": "true", "EMR_RATE_EC2_M5_XLARGE": "0.0001"})
        run = fx.run("run-bounded-pipeline.sh", args, env)
        self.assert_refused(run, step="g6-gate")
        self.assertIn("pricing", run.result.lower())
        self.assertIn("CONFIG-IGNORED", run.out)
        self.assertIn("EMR_PRICING_CONFIRMED_BY_HUMAN", run.out)
        self.assertIn("EMR_RATE_EC2_M5_XLARGE", run.out)
        self.assertIn("ESTIMATE-USD: 0.60", run.out)

    def test_missing_rate_is_never_zero(self):
        fx = self.fx()
        args, env = fx.exec_ready()
        env["SCHOLARCHAIN_PRICING_FILE"] = str(fx.pricing_file(True, drop=("EMR_RATE_EMR_M5_XLARGE",)))
        dry = fx.dry(extra_env=env)
        self.assertNotIn("ESTIMATE-USD: 0", dry.out)
        self.assertIn("ESTIMATE-USD: unavailable", dry.out)
        self.assertIn("G6-STATUS: --execute would be refused", dry.out)
        fx.log.write_text("")
        run = fx.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(run.calls, [])

    def test_instance_type_without_a_reviewed_rate_is_not_runnable(self):
        fx = self.fx()
        dry = fx.dry(instance_type="m5.4xlarge")
        self.assertNotEqual((dry.rc, dry.status), (0, "PASS"))
        self.assertEqual(dry.calls, [])

    def test_execute_without_a_profile_is_refused(self):
        fx = self.fx()
        args, env = fx.exec_ready()
        env.pop("AWS_PROFILE")
        fx.log.write_text("")
        run = fx.run("run-bounded-pipeline.sh", args, env)
        self.assert_refused(run)


class PipelineInputRefusals(Base):
    def test_artifact_without_sha256_is_refused(self):
        fx = self.fx()
        self.assert_refused(fx.dry(skip_artifacts=("hadoop-libjars",)), step="plan")
        self.assert_refused(fx.dry(skip_artifacts=("job-jar",)), step="plan")

    def test_malformed_datasets_manifest_is_refused(self):
        fx = self.fx()
        for label, body in (("not-json", "nope"), ("missing-source", json.dumps({"dblp": S.DATASETS["dblp"]})),
                            ("no-snapshot", json.dumps({k: {"retrieval": "2026-01-01"} for k in S.DATASETS}))):
            with self.subTest(case=label):
                (fx.repo / "inputs/datasets.json").write_text(body)
                self.assert_refused(fx.dry(), step="plan")

    def test_spark_property_file_departing_from_decision_12_10_is_refused(self):
        sabotage = {
            "authentication removed": ("spark.authenticate true\n", ""),
            "AES-CTR engine changed": ("spark.network.crypto.authEngineVersion 1\n", "spark.network.crypto.authEngineVersion 2\n"),
            "IO encryption removed": ("spark.io.encryption.enabled true\n", ""),
            "hadoop classpath populated": ("spark.yarn.populateHadoopClasspath false\n", "spark.yarn.populateHadoopClasspath true\n"),
            "yarn jars changed": ("spark.yarn.jars local:/opt/scholarchain-runtime/jars/*\n", "spark.yarn.jars local:/usr/lib/spark/jars/*\n"),
            "shuffle tracking removed": ("spark.dynamicAllocation.shuffleTracking.enabled true\n", ""),
        }
        for label, (old, new) in sabotage.items():
            with self.subTest(case=label):
                fx = self.fx()
                path = fx.repo / "scripts/config/spark-12-10.conf"
                text = path.read_text()
                self.assertIn(old, text, "the fixture config no longer has the line this test sabotages")
                path.write_text(text.replace(old, new))
                fx.commit_all()
                self.assert_refused(fx.dry(), step="plan")

    def test_lzo_codec_in_the_codec_list_is_refused(self):
        fx = self.fx()
        path = fx.repo / "scripts/config/spark-12-10.conf"
        text = path.read_text().replace("org.apache.hadoop.io.compress.SnappyCodec\n",
                                        "org.apache.hadoop.io.compress.SnappyCodec,com.hadoop.compression.lzo.LzoCodec\n")
        path.write_text(text)
        fx.commit_all()
        self.assert_refused(fx.dry(), step="plan")

    def test_usage_errors_exit_two(self):
        fx = self.fx()
        run = fx.dry(region="not a region!")
        self.assertEqual(run.rc, 2, run.describe())
        self.assertEqual(run.status, "REFUSED")
        run = fx.run("run-bounded-pipeline.sh", ["--no-such-flag"])
        self.assertEqual(run.rc, 2, run.describe())
        run = fx.dry(cluster_id=None, extra_env={"SCHOLARCHAIN_EMR_CLUSTER_ID": ""})
        self.assertEqual(run.rc, 2, run.describe())
        self.assertEqual(run.calls, [])

    def test_s3_prefix_must_have_a_bucket_and_key(self):
        fx = self.fx()
        self.assert_refused(fx.dry(input_prefix="s3://inbucket"), step="plan")
        self.assert_refused(fx.dry(output_prefix="file:///tmp/out"), step="plan")


class PipelineApprovalRefusals(Base):
    """Step 0 answer 5: same KEY=value format as 13A; every key must match; wrong action and extra keys refuse."""

    KEYS_THAT_MUST_MATCH = {
        "APPROVED_ACTION": "run-experiment",
        "APPROVED_COMMIT": "0123456789abcdef0123456789abcdef01234567",
        "APPROVED_ACCOUNT_SHA256": "b" * 64,
        "APPROVED_REGION": "us-west-2",
        "APPROVED_CLUSTER_ID": "j-OTHERCLUSTER",
        "APPROVED_RUN_CONFIG_SHA256": "c" * 64,
        "APPROVED_BUDGET_USD": "2",
        "APPROVED_MAX_CAPACITY": "3",
        "APPROVED_MAX_RUNTIME_MINUTES": "61",
        "APPROVED_TEARDOWN": "manual",
        "APPROVED_PRESPEND_SHA256": "d" * 64,
    }

    def test_each_mismatching_key_refuses_with_exit_3_and_a_step_marker(self):
        for key, bad in self.KEYS_THAT_MUST_MATCH.items():
            with self.subTest(key=key):
                fx = self.fx()
                run = fx.execute(approval_over={key: bad})
                self.assertEqual(run.rc, 3, run.describe())
                self.assertEqual(run.status, "REFUSED", run.describe())
                self.assertIn(S.last_step(run), ("approval-match", "approval-record", "prespend-receipt", "account-check"), run.describe())
                self.assertEqual(len(run.results()), 1)
                # nothing paid may have happened and no step may have been submitted
                self.assertEqual(S.count_calls(run.calls, "aws", "emr", "add-steps"), 0)
                self.assertEqual(fx.reservations(), [], "a ledger slot was reserved on a refused run")
                if key != "APPROVED_ACCOUNT_SHA256":
                    self.assertEqual(run.aws_verbs(), [], "a mismatch in %s must be caught before the first aws call" % key)

    def test_account_mismatch_is_detected_after_sts_and_before_the_cluster_is_described(self):
        fx = self.fx()
        run = fx.execute(approval_over={"APPROVED_ACCOUNT_SHA256": "b" * 64})
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(run.aws_verbs(), ["sts get-caller-identity"], run.describe())
        self.assertNotIn(S.ACCOUNT, run.text)

    def test_budget_is_compared_numerically(self):
        fx = self.fx()
        run = fx.execute(approval_over={"APPROVED_BUDGET_USD": "3.00"})
        self.assertEqual(run.rc, 0, run.describe())

    def test_missing_duplicate_extra_or_malformed_lines_refuse(self):
        for key in self.KEYS_THAT_MUST_MATCH:
            with self.subTest(missing=key):
                fx = self.fx()
                run = fx.execute(approval_drop=(key,))
                self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
                self.assertEqual(S.last_step(run), "approval-record", run.describe())
                self.assertEqual(run.calls, [])
        fx = self.fx()
        run = fx.execute(duplicate=("APPROVED_REGION",))
        self.assertEqual((run.rc, S.last_step(run)), (3, "approval-record"), run.describe())
        for label, transform in (
            ("quoted", lambda t: t.replace("APPROVED_REGION=us-east-2", 'APPROVED_REGION="us-east-2"')),
            ("space-around-equals", lambda t: t.replace("APPROVED_REGION=us-east-2", "APPROVED_REGION = us-east-2")),
            ("indented", lambda t: t.replace("APPROVED_REGION=us-east-2", "  APPROVED_REGION=us-east-2")),
            ("crlf", lambda t: t.replace("APPROVED_REGION=us-east-2\n", "APPROVED_REGION=us-east-2\r\n")),
        ):
            with self.subTest(malformed=label):
                fx = self.fx()
                run = fx.execute(raw_transform=transform)
                self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
                self.assertEqual(S.last_step(run), "approval-record", run.describe())
                self.assertEqual(run.calls, [])

    def test_unknown_approved_key_is_refused_as_an_extra_key(self):
        """Resolved finding O1. scripts/README.md: prose and headings in the record are ignored, but an unknown
        APPROVED_* key (for example a misspelt one) refuses with exit 3 at step approval-record before any aws call;
        extra keys are never ignored. Ordinary prose that merely mentions a key name is still ignored."""
        for line in ("APPROVED_UNKNOWN_KEY=1", "APPROVED_BUDGET_USDD=3", "APPROVED_REGIONS=us-east-2"):
            with self.subTest(line=line):
                fx = self.fx()
                run = fx.execute(extra_lines=(line,))
                self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
                self.assertEqual(S.last_step(run), "approval-record", run.describe())
                self.assertEqual(len(run.results()), 1)
                self.assertEqual(run.calls, [], "no aws call may precede an approval-record refusal")
                self.assertEqual(fx.reservations(), [])

    def test_prose_in_the_record_is_still_ignored(self):
        fx = self.fx()
        run = fx.execute(extra_lines=("The human reviewed this record on 2026-11-06.", "## Notes", "approved by the human architect"))
        self.assertEqual(run.rc, 0, run.describe())

    def test_missing_approval_file_refuses(self):
        fx = self.fx()
        args, env = fx.exec_ready()
        args[args.index("--approval") + 1] = str(fx.aux / "nonexistent.md")
        fx.log.write_text("")
        run = fx.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual((run.rc, S.last_step(run), run.status), (3, "approval-record", "REFUSED"), run.describe())
        self.assertEqual(run.calls, [])

    def test_experiment_record_cannot_authorise_a_pipeline_run(self):
        fx = self.fx()
        run = fx.execute(action="run-experiment", manifest_sha=S.HEX64)
        self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
        self.assertEqual(run.calls, [])
        # a record that is otherwise perfect but names the other action
        fx2 = self.fx()
        run2 = fx2.execute(approval_over={"APPROVED_ACTION": "run-experiment"})
        self.assertEqual((run2.rc, run2.status), (3, "REFUSED"), run2.describe())
        self.assertEqual(run2.calls, [])

    def test_manifest_key_is_refused_for_a_pipeline_record(self):
        fx = self.fx()
        run = fx.execute(manifest_sha=S.HEX64)
        self.assertEqual((run.rc, S.last_step(run)), (3, "approval-record"), run.describe())
        self.assertEqual(run.calls, [])

    def test_dirty_work_tree_refuses_before_the_record_is_read(self):
        fx = self.fx()
        args, env = fx.exec_ready()
        (fx.repo / "inputs/prep.json").write_text(json.dumps(S.SAFE_PREP) + "\n\n")  # tracked file modified
        fx.log.write_text("")
        run = fx.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual((run.rc, S.last_step(run), run.status), (3, "clean-tree", "REFUSED"), run.describe())
        self.assertEqual(run.calls, [])
        fx2 = self.fx()
        args, env = fx2.exec_ready()
        (fx2.repo / "untracked.txt").write_text("x")
        fx2.log.write_text("")
        run = fx2.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual((run.rc, S.last_step(run)), (3, "clean-tree"), run.describe())

    def test_only_the_literal_default_record_path_is_exempt_from_the_dirty_tree_refusal(self):
        fx = self.fx()
        args, env = fx.exec_ready()
        record = fx.aux / "approval.md"
        target = fx.repo / "docs/agent-runs/phase-15/human-gate.md"
        target.parent.mkdir(parents=True)
        target.write_text(record.read_text())
        args = [a for i, a in enumerate(args) if not (a == "--approval" or (i and args[i - 1] == "--approval"))]
        fx.log.write_text("")
        run = fx.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual(run.rc, 0, run.describe())
        # any other in-repo record path makes the tree dirty
        fx2 = self.fx()
        args, env = fx2.exec_ready()
        other = fx2.repo / "docs/agent-runs/phase-15/human-gate.md.bak"
        other.parent.mkdir(parents=True)
        other.write_text((fx2.aux / "approval.md").read_text())
        fx2.log.write_text("")
        run = fx2.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual((run.rc, S.last_step(run)), (3, "clean-tree"), run.describe())


class PipelinePrespendRefusals(Base):
    """Plan 7.3a / 13A receipt rules apply to the pipeline: missing or stale receipt refuses before any aws call."""

    def test_missing_receipt_refuses(self):
        fx = self.fx()
        args, env = fx.exec_ready()
        args[args.index("--prespend") + 1] = str(fx.aux / "no-receipt.json")
        fx.log.write_text("")
        run = fx.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual((run.rc, S.last_step(run), run.status), (3, "prespend-receipt", "REFUSED"), run.describe())
        self.assertEqual(run.calls, [])

    def test_receipt_edited_after_approval_refuses(self):
        fx = self.fx()
        args, env = fx.exec_ready()
        receipt = fx.aux / "prespend.json"
        body = json.loads(receipt.read_text())
        body["reserves_usd"] = 2.5
        receipt.write_text(json.dumps(body))
        fx.log.write_text("")
        run = fx.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual((run.rc, S.last_step(run)), (3, "prespend-receipt"), run.describe())
        self.assertEqual(run.calls, [])

    def test_stale_future_unmonitored_low_headroom_and_non_numeric_receipts_refuse(self):
        now = S.now_utc()
        cases = {
            "stale 25h": dict(snapshot_dt=now - datetime.timedelta(hours=25)),
            "future": dict(snapshot_dt=now + datetime.timedelta(hours=2)),
            "monitoring false": dict(monitoring_confirmed_active=False),
            "monitoring string": dict(monitoring_confirmed_active="true"),
            "headroom 2.99": dict(remaining_headroom_usd=2.99),
            "headroom 0": dict(remaining_headroom_usd=0),
            "headroom negative": dict(remaining_headroom_usd=-0.01),
            "headroom string": dict(remaining_headroom_usd="150"),
            "headroom null": dict(remaining_headroom_usd=None),
            "reserves missing": dict(reserves_usd=...),
            "allowance missing": dict(unreported_usage_allowance_usd=...),
            "spend missing": dict(reported_spend_usd=...),
            "anthropic spend missing": dict(anthropic_spend_to_date_usd=...),
            "voyage spend missing": dict(voyage_spend_to_date_usd=...),
            "anthropic spend negative": dict(anthropic_spend_to_date_usd=-0.01),
            "voyage spend negative": dict(voyage_spend_to_date_usd=-0.01),
            "headroom above the ceiling arithmetic": dict(remaining_headroom_usd=20.27),
        }
        for label, mods in cases.items():
            with self.subTest(case=label):
                fx = self.fx()
                run = fx.execute(prespend_mods=mods)
                self.assertEqual((run.rc, S.last_step(run), run.status), (3, "prespend-receipt", "REFUSED"), run.describe())
                self.assertEqual(run.calls, [], "no aws call may precede a failed pre-spend check")

    def test_headroom_exactly_three_and_snapshot_within_a_day_pass(self):
        """USD 25 replan: the pinned floor is 3 (it was 20); 3 is inclusive, 2.99 is refused (case above)."""
        fx = self.fx()
        run = fx.execute(prespend_mods=dict(remaining_headroom_usd=3, snapshot_dt=S.now_utc() - datetime.timedelta(hours=23)))
        self.assertEqual(run.rc, 0, run.describe())

    def test_a_headroom_the_old_floor_refused_now_passes_and_the_environment_cannot_move_the_floor(self):
        """headroom 3.01 and 19.99 (refused under the old 20 floor) pass; PRESPEND_MIN_HEADROOM_USD in the
        environment is a pinned key and cannot lower or raise the floor."""
        for headroom in (3.01, 19.99):
            with self.subTest(headroom=headroom):
                run = self.fx().execute(prespend_mods=dict(remaining_headroom_usd=headroom))
                self.assertEqual(run.rc, 0, run.describe())
        fx = self.fx()
        run = fx.execute(prespend_mods=dict(remaining_headroom_usd=2.99),
                         env_over={"PRESPEND_MIN_HEADROOM_USD": "0"})
        self.assertEqual((run.rc, S.last_step(run), run.status), (3, "prespend-receipt", "REFUSED"), run.describe())
        self.assertEqual(run.calls, [])

    def test_receipt_expiring_mid_run_stops_before_the_next_submission(self):
        fx = self.fx()
        future = S.utc(S.now_utc() + datetime.timedelta(hours=48))
        clock = S.Fixture.write_json(fx.aux / "clock.json", {"default": S.utc(S.now_utc()), "step-spark-class-origin": future})
        run = fx.execute(env_over={"SCHOLARCHAIN_TEST_CLOCK_FILE": str(clock)})
        self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
        self.assertIn("pre-spend receipt rejected before step-spark-class-origin", run.text)
        self.assertEqual(S.count_calls(run.calls, "aws", "emr", "add-steps"), 3, "only the three earlier steps may have been submitted")

    def test_test_clock_is_ignored_with_the_repository_config(self):
        fx = self.fx()
        clock = S.Fixture.write_json(fx.aux / "clock.json", {"default": "2000-01-01T00:00:00Z"})
        args, env = fx.exec_ready()
        env = {"AWS_PROFILE": "p", "SCHOLARCHAIN_TEST_CLOCK_FILE": str(clock)}
        fx.log.write_text("")
        run = fx.run("run-bounded-pipeline.sh", args, env)
        self.assertIn("CLOCK-IGNORED", run.out)


class PipelineClusterRefusals(Base):
    """Step 0 answer 8 / plan 7.2: the cluster must be WAITING/RUNNING with auto-termination set and only approved nodes."""

    def groups(self, master="m5.xlarge", core="m5.xlarge", core_count=1, task=None):
        gs = [{"InstanceGroupType": "MASTER", "InstanceType": master, "RequestedInstanceCount": 1, "RunningInstanceCount": 1},
              {"InstanceGroupType": "CORE", "InstanceType": core, "RequestedInstanceCount": core_count, "RunningInstanceCount": core_count}]
        if task:
            gs.append({"InstanceGroupType": "TASK", "InstanceType": "m5.xlarge", "RequestedInstanceCount": task, "RunningInstanceCount": task})
        return {"InstanceGroups": gs}

    def expect_cluster_refusal(self, scenario, **kw):
        fx = self.fx()
        fx.update_scenario(**scenario)
        run = fx.execute(**kw)
        self.assertEqual(run.rc, 4, run.describe())
        self.assertEqual(run.status, "FAIL", run.describe())
        self.assertEqual(S.last_step(run), "cluster-check", run.describe())
        self.assertEqual(S.count_calls(run.calls, "aws", "emr", "add-steps"), 0)
        self.assertEqual(fx.reservations(), [], "nothing may be reserved or paid before the cluster check passes")
        return run

    def test_cluster_not_waiting_or_running(self):
        for state in ("TERMINATED", "STARTING", "TERMINATING", "BOOTSTRAPPING"):
            with self.subTest(state=state):
                self.expect_cluster_refusal({"describe_cluster": {"Cluster": {"Id": "j-TESTCLUSTER", "Status": {"State": state}}}})

    def test_cluster_without_auto_termination_policy(self):
        self.expect_cluster_refusal({"policy": {}})
        self.expect_cluster_refusal({"policy": {"AutoTerminationPolicy": {}}})

    def test_idle_timeout_outside_sixty_to_cap(self):
        self.expect_cluster_refusal({"policy": {"AutoTerminationPolicy": {"IdleTimeout": 3601}}})
        self.expect_cluster_refusal({"policy": {"AutoTerminationPolicy": {"IdleTimeout": 59}}})

    def test_max_idle_seconds_flag_can_only_tighten(self):
        fx = self.fx()
        fx.update_scenario(policy={"AutoTerminationPolicy": {"IdleTimeout": 900}})
        run = fx.execute()
        self.assertEqual(run.rc, 0, run.describe())
        fx2 = self.fx()
        fx2.update_scenario(policy={"AutoTerminationPolicy": {"IdleTimeout": 900}})
        args, env = fx2.exec_ready(pipeline_over={"max_idle_seconds": 600})
        fx2.log.write_text("")
        run = fx2.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual((run.rc, S.last_step(run)), (4, "cluster-check"), run.describe())
        # values above the pinned cap are a usage error
        run = fx2.run("run-bounded-pipeline.sh", fx2.full_args(max_idle_seconds=7200), env)
        self.assertEqual(run.rc, 2, run.describe())

    def test_other_instance_type_or_more_nodes_than_approved(self):
        self.expect_cluster_refusal({"groups": self.groups(core="m5.2xlarge")})
        self.expect_cluster_refusal({"groups": self.groups(master="m5.2xlarge")})
        self.expect_cluster_refusal({"groups": self.groups(core_count=3)})
        self.expect_cluster_refusal({"groups": self.groups(task=1)})  # no task nodes approved

    def test_describe_cluster_without_instance_groups_refuses(self):
        # The groups come only from describe-cluster's Cluster.InstanceGroups (AWS CLI v2 has no list-instance-groups).
        cases = (("absent", "the cluster reports no instance groups"),
                 ({"InstanceGroups": []}, "the cluster reports no instance groups"),
                 ({"InstanceGroups": None}, "the cluster reports no instance groups"),
                 ({"InstanceGroups": ["MASTER"]}, "an instance group entry is not an object"))
        for groups, reason in cases:
            with self.subTest(groups=groups):
                run = self.expect_cluster_refusal({"groups": groups})
                self.assertIn(reason, run.text)
                self.assertNotIn("emr list-instance-groups", run.aws_verbs())

    def test_describe_cluster_returning_another_cluster_id(self):
        self.expect_cluster_refusal({"describe_cluster": {"Cluster": {"Id": "j-SOMEONEELSE", "Status": {"State": "WAITING"}}}})

    def test_aws_failures_before_anything_paid(self):
        fx = self.fx()
        fx.update_scenario(verbs={"emr get-auto-termination-policy": {"rc": 1, "stderr": "AccessDenied\n"}})
        run = fx.execute()
        self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
        self.assertEqual(S.count_calls(run.calls, "aws", "emr", "add-steps"), 0)
        fx = self.fx()
        fx.update_scenario(verbs={"sts get-caller-identity": {"rc": 1, "stderr": "ExpiredToken\n"}})
        run = fx.execute()
        self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
        self.assertEqual(run.aws_verbs(), ["sts get-caller-identity"])


if __name__ == "__main__":
    unittest.main()
