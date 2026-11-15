"""Phase 14B repair round 3 (Anthropic API and Voyage AI), the scripts side, written independently by the test-engineer from the shared
contract and the instructor ruling in docs/agent-runs/phase-14/prompt.md, not from scripts/tests/test_providers.py.

Hand-derived expectations:
  * The pre-spend receipt carries three spend-to-date numbers (AWS reported_spend_usd, anthropic_spend_to_date_usd, voyage_spend_to_date_usd).
    Each is required and finite and at least 0 (0 is a value; missing, null, string, NaN and negative are refused).
  * For every stage that can spend, remaining_headroom_usd may not exceed 25 - (AWS + Anthropic + Voyage) - unreported allowance - reserves,
    with a cent of tolerance. Example: 25 - (4 + 1.5 + 0.25) - 1 - 5 = 13.25 (13.26 passes, 13.27 is refused). The ceiling is pinned
    at 25 in release.conf and no environment variable moves it.
  * The cost report lists AWS, Anthropic, Voyage AI in that order, then the combined total to the cent (4.10 + 0.81 + 0 = 4.91), accepts a USD 0
    item only with a usage note, accepts exactly those three items, and refuses negative, non-numeric and non-finite amounts.
  * No provider key value reaches script output: a sentinel key in the environment is absent from every output of the scripts.
  * cleanup lists both key containers as teardown targets and reminds the human, three times in the protocol, to revoke both keys.
"""
import datetime
import json
import math
import re
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path

import sc_support as S

VERIFY = S.REPO / "scripts/lib/verify.py"
COST_REPORT = S.REPO / "scripts/lib/cost_report.py"
RELEASE_CONF = S.REPO / "scripts/config/release.conf"
SENTINEL_ANTHROPIC = "sk-" + "ant-" + "SENTINEL" + "x9Qz" * 8
SENTINEL_VOYAGE = "pa-" + "SENTINEL" + "k7Lm" * 10
PROVIDER_ENV = {"SCHOLARCHAIN_ANTHROPIC_API_KEY": SENTINEL_ANTHROPIC, "SCHOLARCHAIN_VOYAGE_API_KEY": SENTINEL_VOYAGE}


def conf_values():
    return dict(re.findall(r"^([A-Z][A-Z0-9_]*)=(\S+)\s*$", RELEASE_CONF.read_text(), re.M))


def utc_hours_ago(hours):
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def receipt(**mods):
    body = {
        "schema": "scholarchain.prespend-receipt.v1", "monitoring_confirmed_active": True, "cost_snapshot_utc": utc_hours_ago(1),
        "reported_spend_usd": 4.0, "anthropic_spend_to_date_usd": 1.5, "voyage_spend_to_date_usd": 0.25,
        "unreported_usage_allowance_usd": 1.0, "reserves_usd": 5.0,
        "remaining_headroom_usd": 13.25,  # 25 - 5.75 - 1 - 5
    }
    for key, value in mods.items():
        if value is Ellipsis:
            body.pop(key, None)
        else:
            body[key] = value
    return body


def verify(document, *flags, text=None):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "r.json"
        path.write_text(text if text is not None else json.dumps(document))
        done = subprocess.run([sys.executable, "-I", str(VERIFY), "prespend", "--file", str(path), "--max-age-hours", "24", *flags],
                              capture_output=True, text=True, timeout=60, env={"PATH": "/usr/bin:/bin", **PROVIDER_ENV})
    return done.returncode, done.stdout + done.stderr


class ReceiptsNeedEveryProvidersSpend(unittest.TestCase):
    def test_the_hand_derived_receipt_passes_with_and_without_the_ceiling(self):
        for flags in (("--min-headroom", "3"), ("--min-headroom", "3", "--ceiling-usd", "25")):
            rc, out = verify(receipt(), *flags)
            self.assertEqual(rc, 0, out)

    def test_zero_spend_is_a_value_but_missing_null_string_nan_and_negative_are_refused(self):
        for key in ("anthropic_spend_to_date_usd", "voyage_spend_to_date_usd"):
            rc, out = verify(receipt(**{key: 0}), "--min-headroom", "3", "--ceiling-usd", "25")
            self.assertEqual(rc, 0, "%s = 0 must be accepted\n%s" % (key, out))
            for label, value in (("missing", ...), ("null", None), ("string", "0.5"), ("true", True), ("negative", -0.01), ("negative whole", -1), ("list", [0])):
                with self.subTest(field=key, value=label):
                    rc, out = verify(receipt(**{key: value}), "--min-headroom", "3", "--ceiling-usd", "25")
                    self.assertEqual(rc, 1, out)
                    self.assertIn("PRESPEND-CHECK-FAILED", out)
                    self.assertIn(key, out, "the finding names the field")
            for label, literal in (("NaN", "NaN"), ("Infinity", "Infinity"), ("-Infinity", "-Infinity")):
                with self.subTest(field=key, value=label):
                    text = json.dumps(receipt()).replace('"%s": 0.25' % key, '"%s": %s' % (key, literal)).replace('"%s": 1.5' % key, '"%s": %s' % (key, literal))
                    self.assertIn(literal, text)
                    rc, out = verify(None, "--min-headroom", "3", "--ceiling-usd", "25", text=text)
                    self.assertEqual(rc, 1, out)

    def test_the_no_floor_cleanup_mode_still_needs_both_provider_fields_but_compares_nothing(self):
        rc, out = verify(receipt(remaining_headroom_usd=-50), "--no-headroom-floor")
        self.assertEqual(rc, 0, out)
        for key in ("anthropic_spend_to_date_usd", "voyage_spend_to_date_usd"):
            for value in (..., None, -1, "1"):
                with self.subTest(field=key, value=value):
                    rc, out = verify(receipt(remaining_headroom_usd=-50, **{key: value}), "--no-headroom-floor")
                    self.assertEqual(rc, 1, out)

    def test_the_ceiling_arithmetic_is_25_minus_every_spend_minus_allowance_and_reserves(self):
        # allowed = 25 - (4 + 1.5 + 0.25) - 1 - 5 = 13.25; a cent of tolerance
        for headroom, expected in ((13.25, 0), (13.26, 0), (13.27, 1), (20, 1), (3, 0), (2.99, 1)):
            with self.subTest(headroom=headroom):
                rc, out = verify(receipt(remaining_headroom_usd=headroom), "--min-headroom", "3", "--ceiling-usd", "25")
                self.assertEqual(rc, expected, out)
                if expected and headroom > 13.26:
                    self.assertIn("exceeds the ceiling arithmetic", out)
                    self.assertIn("13.25", out, "the refusal states the derived limit")

    def test_each_provider_changes_the_limit_by_exactly_its_spend(self):
        cases = (
            (dict(reported_spend_usd=14.0), 3.25),       # 25 - (14 + 1.5 + 0.25) - 1 - 5
            (dict(anthropic_spend_to_date_usd=11.5), 3.25),  # 25 - (4 + 11.5 + 0.25) - 1 - 5
            (dict(voyage_spend_to_date_usd=10.25), 3.25),    # 25 - (4 + 1.5 + 10.25) - 1 - 5
            (dict(unreported_usage_allowance_usd=11.0), 3.25),
            (dict(reserves_usd=15.0), 3.25),
        )
        for mods, limit in cases:
            with self.subTest(mods=mods):
                self.assertEqual(verify(receipt(remaining_headroom_usd=limit, **mods), "--min-headroom", "3", "--ceiling-usd", "25")[0], 0)
                self.assertEqual(verify(receipt(remaining_headroom_usd=limit + 0.02, **mods), "--min-headroom", "3", "--ceiling-usd", "25")[0], 1)

    def test_a_headroom_that_leaves_a_provider_out_is_refused_and_a_safety_margin_is_not(self):
        # A human who forgot the Anthropic bill writes the headroom of an AWS-only world: 25 - 4 - 0.25 - 1 - 5 = 14.75 > 13.25.
        self.assertEqual(verify(receipt(remaining_headroom_usd=14.75), "--min-headroom", "3", "--ceiling-usd", "25")[0], 1)
        self.assertEqual(verify(receipt(remaining_headroom_usd=10.0), "--min-headroom", "3", "--ceiling-usd", "25")[0], 0, "less headroom is a margin")

    def test_without_a_ceiling_no_arithmetic_runs_and_a_bad_ceiling_is_a_usage_error(self):
        self.assertEqual(verify(receipt(remaining_headroom_usd=999), "--min-headroom", "3")[0], 0)
        for bad in ("0", "-1", "nan", "inf"):
            with self.subTest(ceiling=bad):
                self.assertEqual(verify(receipt(), "--min-headroom", "3", "--ceiling-usd", bad)[0], 2)

    def test_release_conf_pins_the_ceiling_at_25_and_the_floor_at_3(self):
        values = conf_values()
        self.assertEqual(D(values["PRESPEND_PROJECT_CEILING_USD"]), D(25))
        self.assertEqual(D(values["PRESPEND_MIN_HEADROOM_USD"]), D(3))
        self.assertEqual(len(re.findall(r"^PRESPEND_PROJECT_CEILING_USD=", RELEASE_CONF.read_text(), re.M)), 1)

    def test_the_receipt_output_never_contains_a_provider_key(self):
        for document in (receipt(), receipt(anthropic_spend_to_date_usd=-1)):
            rc, out = verify(document, "--min-headroom", "3", "--ceiling-usd", "25")
            self.assertNotIn("SENTINEL", out)


class CostReport(unittest.TestCase):
    """scripts/lib/cost_report.py: AWS, Anthropic and Voyage AI as separate items, then the combined total (instructor ruling 2026-11-09)."""

    ITEMS = {
        "aws": {"usd": 4.10, "usage": "ECS, Neptune, EMR, NAT and S3 as shown in Cost Explorer"},
        "anthropic": {"usd": 0.81, "usage": "claude-haiku-5-5: 115 answers, tokens as shown in the Anthropic Console"},
        "voyage": {"usd": 0, "usage": "voyage-4-lite: 3.1M tokens inside the 200M free tokens of the account"},
    }

    def document(self, **mods):
        doc = {"schema": "scholarchain.cost-report.v1", "as_of_utc": "2026-11-20T12:00:00Z", "ceiling_usd": 25,
               "items": json.loads(json.dumps(self.ITEMS))}
        for key, value in mods.items():
            if value is Ellipsis:
                doc.pop(key, None)
            else:
                doc[key] = value
        return doc

    def render(self, document=None, fmt="text", text=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "in.json"
            path.write_text(text if text is not None else json.dumps(document if document is not None else self.document()))
            done = subprocess.run([sys.executable, "-I", str(COST_REPORT), "render", "--input", str(path), "--format", fmt],
                                  capture_output=True, text=True, timeout=60, env={"PATH": "/usr/bin:/bin", **PROVIDER_ENV})
        return done.returncode, done.stdout, done.stderr

    def test_lists_aws_anthropic_voyage_in_order_then_the_combined_total(self):
        rc, out, err = self.render()
        self.assertEqual((rc, err), (0, ""))
        positions = [out.index(label) for label in ("AWS ", "Anthropic ", "Voyage AI ", "Combined ")]
        self.assertEqual(positions, sorted(positions), out)
        self.assertEqual(len(set(positions)), 4)
        self.assertRegex(out, r"AWS\s+USD\s+4\.10")
        self.assertRegex(out, r"Anthropic\s+USD\s+0\.81")
        self.assertRegex(out, r"Voyage AI\s+USD\s+0\.00")
        self.assertRegex(out, r"Combined\s+USD\s+4\.91")  # 4.10 + 0.81 + 0
        self.assertRegex(out, r"remaining USD 20\.09")    # 25 - 4.91

    def test_a_zero_item_keeps_its_usage_documentation_in_the_output(self):
        rc, out, _ = self.render()
        self.assertIn("voyage-4-lite: 3.1M tokens inside the 200M free tokens of the account", out)

    def test_json_format_keeps_the_same_order_and_exact_cents(self):
        rc, out, _ = self.render(fmt="json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual([i["provider"] for i in data["items"]], ["AWS", "Anthropic", "Voyage AI"])
        self.assertEqual([i["usd"] for i in data["items"]], ["4.10", "0.81", "0.00"])
        self.assertEqual((data["combined_total_usd"], data["remaining_usd"], data["over_ceiling"]), ("4.91", "20.09", False))

    def test_a_zero_item_without_a_usage_note_is_refused(self):
        for provider in ("aws", "anthropic", "voyage"):
            for usage in (..., "", "   ", None):
                with self.subTest(provider=provider, usage=usage):
                    doc = self.document()
                    doc["items"][provider]["usd"] = 0
                    if usage is Ellipsis:
                        doc["items"][provider].pop("usage")
                    else:
                        doc["items"][provider]["usage"] = usage
                    rc, out, _ = self.render(doc)
                    self.assertEqual(rc, 1, out)
                    self.assertIn("COST-REPORT-REFUSED", out)
                    self.assertNotIn("Combined", out, "a refused report prints no total")

    def test_a_nonzero_item_also_needs_its_usage(self):
        doc = self.document()
        doc["items"]["anthropic"].pop("usage")
        self.assertEqual(self.render(doc)[0], 1)

    def test_a_missing_or_extra_item_is_refused_so_no_charge_can_hide(self):
        for provider in ("aws", "anthropic", "voyage"):
            doc = self.document()
            del doc["items"][provider]
            with self.subTest(missing=provider):
                self.assertEqual(self.render(doc)[0], 1)
        doc = self.document()
        doc["items"]["openai"] = {"usd": 1, "usage": "unlisted provider"}
        rc, out, _ = self.render(doc)
        self.assertEqual(rc, 1)
        self.assertIn("openai", out)

    def test_negative_string_boolean_null_and_non_finite_amounts_are_refused(self):
        for label, value in (("negative", -0.01), ("string", "0.5"), ("true", True), ("null", None), ("list", [1]), ("too large", 1000001)):
            with self.subTest(amount=label):
                doc = self.document()
                doc["items"]["anthropic"]["usd"] = value
                self.assertEqual(self.render(doc)[0], 1)
        for literal in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(amount=literal):
                text = json.dumps(self.document()).replace('"usd": 0.81', '"usd": %s' % literal)
                self.assertEqual(self.render(text=text)[0], 1)

    def test_a_bad_timestamp_or_ceiling_is_refused(self):
        for mods in (dict(as_of_utc="yesterday"), dict(as_of_utc=...), dict(ceiling_usd=0), dict(ceiling_usd="25"), dict(ceiling_usd=...)):
            with self.subTest(mods=mods):
                self.assertEqual(self.render(self.document(**mods))[0], 1)

    def test_over_the_ceiling_is_reported_not_enforced(self):
        doc = self.document()
        doc["items"]["aws"]["usd"] = 24.50
        rc, out, _ = self.render(doc)  # 24.50 + 0.81 + 0 = 25.31
        self.assertEqual(rc, 0)
        self.assertRegex(out, r"Combined\s+USD\s+25\.31")
        self.assertIn("OVER THE CEILING", out)
        self.assertEqual(json.loads(self.render(doc, fmt="json")[1])["over_ceiling"], True)

    def test_the_total_is_exact_decimal_arithmetic(self):
        doc = self.document()
        doc["items"]["aws"]["usd"] = 0.10
        doc["items"]["anthropic"]["usd"] = 0.20
        doc["items"]["voyage"]["usd"] = 0.30
        rc, out, _ = self.render(doc)  # binary floats would give 0.6000000000000001
        self.assertRegex(out, r"Combined\s+USD\s+0\.60\b")

    def test_unreadable_or_non_object_input_is_refused_and_no_key_is_echoed(self):
        for text in ("not json", "[]", "", "null"):
            with self.subTest(text=text):
                rc, out, err = self.render(text=text)
                self.assertEqual(rc, 1, out + err)
                self.assertNotIn("SENTINEL", out + err)
        rc, out, err = self.render()
        self.assertNotIn("SENTINEL", out + err)


class NoKeyValueInAnyScriptOutput(unittest.TestCase):
    """Scripts run with sentinel provider keys in the environment: no output, and no logged file, contains a sentinel."""

    def run_script(self, fx, script, args):
        return fx.run(script, args, extra_env=PROVIDER_ENV, secrets=True)

    def assert_clean(self, run):
        self.assertNotIn("SENTINEL", run.text, run.describe())
        self.assertNotIn(SENTINEL_ANTHROPIC, run.text)
        self.assertNotIn(SENTINEL_VOYAGE, run.text)
        for call in run.calls:
            self.assertNotIn("SENTINEL", json.dumps(call), "a tool was called with a key value on its command line")

    def test_plan_cleanup_and_deploy_outputs_never_contain_a_key(self):
        fx = S.Fixture(self, infra=True)
        for script, args in (("plan.sh", ["--env", "course", "--region", "us-east-2"]),
                             ("cleanup.sh", ["--env", "course", "--region", "us-east-2"]),
                             ("deploy.sh", ["--stage", "base-apply", "--plan", "/nonexistent", "--region", "us-east-2", "--approval", str(fx.aux / "missing.md")])):
            with self.subTest(script=script):
                self.assert_clean(self.run_script(fx, script, args))

    def test_the_pipeline_dry_run_and_a_refused_receipt_never_contain_a_key(self):
        fx = S.Fixture(self, infra=True)
        self.assert_clean(fx.run("run-bounded-pipeline.sh", fx.full_args(), extra_env=PROVIDER_ENV))
        run = fx.execute(prespend_mods=dict(anthropic_spend_to_date_usd=...), env_over=PROVIDER_ENV)
        self.assertEqual((run.rc, run.status, S.last_step(run)), (3, "REFUSED", "prespend-receipt"), run.describe())
        self.assert_clean(run)
        self.assertIn("anthropic_spend_to_date_usd", run.text, "the refusal names the missing field")

    def test_cleanup_lists_both_key_containers_and_reminds_the_human_to_revoke_both_keys(self):
        fx = S.Fixture(self, infra=True)
        run = self.run_script(fx, "cleanup.sh", ["--env", "course", "--region", "us-east-2"])
        self.assertEqual((run.rc, run.status), (0, "DRY-RUN"), run.describe())
        reminders = run.grep(r"KEY-REVOCATION-REMINDER: ")
        self.assertGreaterEqual(len(reminders), 2, run.describe())
        text = "\n".join(reminders)
        for needle in ("scholarchain-course/anthropic-api-key", "scholarchain-course/voyage-api-key", "Anthropic", "Voyage"):
            self.assertIn(needle, text)
        self.assertRegex(text, r"(?i)does not revoke|NOT revoke")
        self.assertLess(run.steps().index("after-inventory"), max(i for i, l in enumerate(run.lines()) if "KEY-REVOCATION-REMINDER" in l) + 1)
        self.assert_clean(run)

    def test_the_cleanup_teardown_rules_name_both_key_containers_and_nothing_wider(self):
        rules = conf_values()["CLEANUP_TEARDOWN_ADDRESS_RULES"].split(",")
        self.assertIn("aws_secretsmanager_secret.anthropic", rules)
        self.assertIn("aws_secretsmanager_secret.voyage", rules)
        self.assertEqual([r for r in rules if r.startswith("aws_secretsmanager") and r not in ("aws_secretsmanager_secret.anthropic", "aws_secretsmanager_secret.voyage")], [])
        self.assertFalse([r for r in rules if "secret_version" in r])


class ReleaseConfMirrorsTheProviderContract(unittest.TestCase):
    def test_the_primary_providers_models_and_dimension_are_the_contract_values(self):
        values = conf_values()
        expected = {
            "SYNTHESIS_PROVIDER_DEFAULT": "anthropic", "EMBEDDING_PROVIDER_DEFAULT": "voyage",
            "ANTHROPIC_SYNTHESIS_MODEL_ID": "claude-haiku-5-5", "VOYAGE_EMBEDDING_MODEL_ID": "voyage-4-lite", "VOYAGE_OUTPUT_DIMENSION": "256",
            "BEDROCK_SYNTHESIS_MODEL_ID": "anthropic.claude-haiku-4-5-20251001-v1:0", "BEDROCK_EMBEDDING_MODEL_ID": "amazon.titan-embed-text-v2:0",
        }
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(values.get(key), value)

    def test_no_config_value_looks_like_a_key_and_no_key_setting_exists(self):
        text = RELEASE_CONF.read_text()
        self.assertFalse(re.search(r"(?m)^[A-Z_]*(API_KEY|SECRET_VALUE|KEY_VALUE)[A-Z_]*=", text))
        self.assertFalse(re.search(r"sk-ant-|(?<![A-Za-z0-9_-])pa-[A-Za-z0-9_-]{20,}", text))


if __name__ == "__main__":
    unittest.main()
