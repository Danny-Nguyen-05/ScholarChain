"""Repair round 3 (Phase 14B): the Anthropic API and Voyage AI switch, seen from the scripts.

Hand-derived expectations (docs/agent-runs/phase-14/prompt.md, "Repair round 3 work order"):
  * the pre-spend receipt carries the spend to date of AWS, Anthropic and Voyage AI (numbers the human reads from the three
    consoles), every one required and numeric (0 is a value, missing is not), and the headroom arithmetic is
    ceiling - (AWS + Anthropic + Voyage) - unreported allowance - reserves; cleanup-prepare keeps its no-floor rule;
  * release.conf mirrors the Terraform defaults (providers, model ids, dimension) and keeps every cap unchanged;
  * cleanup destroys both key containers and reminds the human to revoke both keys at the providers;
  * the cost report lists AWS, Anthropic and Voyage separately, then the combined total, and a provider without a charge is USD 0
    with its usage documented;
  * no script holds a Bedrock quota precondition or a "first Haiku 4.5 playground call" step.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

from helpers import SCRIPTS_DIR

REPO = os.path.dirname(SCRIPTS_DIR)
VERIFY = os.path.join(SCRIPTS_DIR, "lib", "verify.py")
COST_REPORT = os.path.join(SCRIPTS_DIR, "lib", "cost_report.py")
TF = os.path.join(REPO, "infra", "terraform")


def run(script, args):
    return subprocess.run([sys.executable, "-I", script] + args, capture_output=True, text=True, timeout=60)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def conf():
    values = {}
    for line in read(os.path.join(SCRIPTS_DIR, "config", "release.conf")).splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]*)=(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


class PrespendProviderSpendTests(unittest.TestCase):
    def check(self, document, flags=("--min-headroom", "3"), text=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            with open(path, "w") as handle:
                handle.write(text if text is not None else json.dumps(document))
            result = run(VERIFY, ["prespend", "--file", path, "--max-age-hours", "24"] + list(flags))
            return result.returncode, result.stdout + result.stderr

    def base(self, **overrides):
        stamp = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        # 25 - (4 + 1.5 + 0.25) - 1 - 5 = 13.25
        doc = {
            "monitoring_confirmed_active": True,
            "cost_snapshot_utc": stamp,
            "reported_spend_usd": 4,
            "anthropic_spend_to_date_usd": 1.5,
            "voyage_spend_to_date_usd": 0.25,
            "unreported_usage_allowance_usd": 1,
            "reserves_usd": 5,
            "remaining_headroom_usd": 13.25,
        }
        doc.update(overrides)
        return doc

    def test_a_complete_receipt_passes_and_the_output_lists_every_provider_then_the_combined_spend(self):
        code, text = self.check(self.base())
        self.assertEqual(code, 0, text)
        self.assertIn("spend to date AWS 4.00 + Anthropic 1.50 + Voyage 0.25 = 5.75 USD", text)

    def test_zero_spend_of_a_provider_is_a_value_but_a_missing_null_or_non_numeric_field_is_refused(self):
        self.assertEqual(self.check(self.base(anthropic_spend_to_date_usd=0, voyage_spend_to_date_usd=0, remaining_headroom_usd=14.0))[0], 0)
        for field in ("anthropic_spend_to_date_usd", "voyage_spend_to_date_usd"):
            for label, value in (("missing", None), ("null", None), ("string", "0"), ("boolean", False), ("list", [0]), ("negative", -0.01)):
                with self.subTest(field=field, label=label):
                    doc = self.base()
                    if label == "missing":
                        del doc[field]
                    else:
                        doc[field] = value
                    code, text = self.check(doc)
                    self.assertEqual(code, 1, text)
                    self.assertIn("PRESPEND-CHECK-FAILED: %s" % field, text)

    def test_nan_and_infinity_in_a_provider_field_are_refused(self):
        for literal in ("NaN", "Infinity"):
            with self.subTest(literal):
                text = json.dumps(self.base()).replace('"voyage_spend_to_date_usd": 0.25', '"voyage_spend_to_date_usd": %s' % literal)
                code, out = self.check(None, text=text)
                self.assertEqual(code, 1, out)

    def test_cleanup_prepare_still_needs_both_provider_fields_but_compares_nothing(self):
        for field in ("anthropic_spend_to_date_usd", "voyage_spend_to_date_usd"):
            doc = self.base()
            del doc[field]
            self.assertEqual(self.check(doc, flags=("--no-headroom-floor",))[0], 1, field)
        # Overspent and with a headroom no arithmetic could support: the no-floor stage accepts it (cleanup is never blocked).
        doc = self.base(reported_spend_usd=30, remaining_headroom_usd=-20)
        code, text = self.check(doc, flags=("--no-headroom-floor", "--ceiling-usd", "25"))
        self.assertEqual(code, 0, text)
        self.assertIn("PRESPEND: cleanup-prepare has no headroom floor (remaining_headroom_usd=-20.00)", text)
        doc = self.base(remaining_headroom_usd=100)
        self.assertEqual(self.check(doc, flags=("--no-headroom-floor", "--ceiling-usd", "25"))[0], 0, "the ceiling arithmetic is not applied to cleanup-prepare")

    def test_the_headroom_arithmetic_includes_every_provider(self):
        flags = ("--min-headroom", "3", "--ceiling-usd", "25")
        code, text = self.check(self.base(), flags=flags)
        self.assertEqual(code, 0, text)
        # A smaller headroom (a safety margin) is fine; so is a cent of rounding.
        self.assertEqual(self.check(self.base(remaining_headroom_usd=10), flags=flags)[0], 0)
        self.assertEqual(self.check(self.base(remaining_headroom_usd=13.26), flags=flags)[0], 0)
        # More headroom than 25 - 5.75 - 1 - 5 = 13.25 is refused, and the message shows the arithmetic with every provider.
        code, text = self.check(self.base(remaining_headroom_usd=13.27), flags=flags)
        self.assertEqual(code, 1, text)
        self.assertIn("exceeds the ceiling arithmetic 13.25 = 25.0 - (AWS 4.00 + Anthropic 1.50 + Voyage 0.25) - unreported 1.00 - reserves 5.00", text)

    def test_a_headroom_that_leaves_anthropic_or_voyage_out_is_refused(self):
        flags = ("--min-headroom", "3", "--ceiling-usd", "25")
        without_anthropic = 25 - 4 - 0.25 - 1 - 5  # 14.75: forgot the 1.50 of Anthropic
        code, text = self.check(self.base(remaining_headroom_usd=without_anthropic), flags=flags)
        self.assertEqual(code, 1, text)
        self.assertIn("exceeds the ceiling arithmetic", text)
        without_voyage = 25 - 4 - 1.5 - 1 - 5 + 0.0  # 13.5: forgot the 0.25 of Voyage AI
        self.assertEqual(self.check(self.base(remaining_headroom_usd=without_voyage), flags=flags)[0], 1)

    def test_the_spending_floor_still_applies_after_the_arithmetic(self):
        flags = ("--min-headroom", "3", "--ceiling-usd", "25")
        code, text = self.check(self.base(remaining_headroom_usd=2.99), flags=flags)
        self.assertEqual(code, 1, text)
        self.assertIn("below the required 3.0 USD", text)

    def test_without_a_ceiling_argument_the_arithmetic_is_not_applied_and_a_bad_ceiling_is_a_usage_failure(self):
        self.assertEqual(self.check(self.base(remaining_headroom_usd=500))[0], 0, "no --ceiling-usd: only the pinned floor and the numeric fields apply")
        for bad in ("0", "-1", "nan", "inf"):
            with self.subTest(bad):
                code, text = self.check(self.base(), flags=("--min-headroom", "3", "--ceiling-usd", bad))
                self.assertEqual(code, 2, text)


class ConfigMirrorsTerraformTests(unittest.TestCase):
    def test_release_conf_provider_defaults_and_model_ids_equal_the_terraform_defaults(self):
        values = conf()
        variables = read(os.path.join(TF, "phase14b-variables.tf"))
        providers = read(os.path.join(TF, "phase14b-providers.tf"))
        synthesis_default = re.search(r'variable "synthesis_provider" \{.*?default\s*=\s*"([a-z]+)"', variables, re.S).group(1)
        embedding_default = re.search(r'variable "embedding_provider" \{.*?default\s*=\s*"([a-z]+)"', variables, re.S).group(1)
        self.assertEqual((values["SYNTHESIS_PROVIDER_DEFAULT"], values["EMBEDDING_PROVIDER_DEFAULT"]), ("anthropic", "voyage"))
        self.assertEqual((synthesis_default, embedding_default), ("anthropic", "voyage"))
        self.assertEqual(values["ANTHROPIC_SYNTHESIS_MODEL_ID"], re.search(r'anthropic_synthesis_model\s*=\s*"([^"]+)"', providers).group(1))
        self.assertEqual(values["VOYAGE_EMBEDDING_MODEL_ID"], re.search(r'voyage_embedding_model\s*=\s*"([^"]+)"', providers).group(1))
        self.assertEqual(values["BEDROCK_EMBEDDING_MODEL_ID"], re.search(r'bedrock_titan_embedding\s*=\s*"([^"]+)"', providers).group(1))
        self.assertEqual(values["ANTHROPIC_SYNTHESIS_MODEL_ID"], "claude-haiku-5-5")
        self.assertEqual(values["VOYAGE_EMBEDDING_MODEL_ID"], "voyage-4-lite")
        self.assertEqual(values["BEDROCK_SYNTHESIS_MODEL_ID"], "anthropic.claude-haiku-4-5-20251001-v1:0")
        self.assertEqual(values["BEDROCK_EMBEDDING_MODEL_ID"], "amazon.titan-embed-text-v2:0")
        self.assertEqual(values["VOYAGE_OUTPUT_DIMENSION"], re.search(r'variable "vector_dimension" \{.*?default\s*=\s*(\d+)', read(os.path.join(TF, "phase12b-variables.tf")), re.S).group(1))
        self.assertEqual(values["VOYAGE_OUTPUT_DIMENSION"], "256")

    def test_no_provider_key_or_secret_value_is_configured_anywhere_in_the_scripts_config(self):
        text = read(os.path.join(SCRIPTS_DIR, "config", "release.conf"))
        for line in text.splitlines():
            if line.startswith("#") or "=" not in line:
                continue
            key = line.split("=", 1)[0]
            self.assertFalse(re.search(r"(API_KEY|SECRET|TOKEN|PASSWORD)", key) and key not in ("TF_PRIVATE_VARS_ENV",), key)
        self.assertNotRegex(text, r"sk-ant-|pa-[A-Za-z0-9]{20}")

    def test_the_caps_are_unchanged_and_the_project_ceiling_is_pinned(self):
        values = conf()
        # Phase 15 P25 (user decision 2026-11-16, phase-15 prompt.md line 131): 4 runs; repair round (user decision 2026-11-16, "Raise cap to 3.53"): USD 3.53 cumulative (was 3.36); the per-run cap is unchanged.
        self.assertEqual((values["EMR_MAX_RUN_USD"], values["EMR_MAX_LIVE_RUNS"], values["EMR_CUMULATIVE_CAP_USD"]), ("3", "4", "3.53"))
        # Phase 15 "R-b option decision" (prompt.md): floor 2 / project <= 23.00 (the floor was 3).
        self.assertEqual((values["PRESPEND_MAX_AGE_HOURS"], values["PRESPEND_MIN_HEADROOM_USD"]), ("24", "2"))
        self.assertEqual(values["PRESPEND_PROJECT_CEILING_USD"], "25")
        pinned = re.search(r'SC_PINNED_KEYS="([^"]*)"', read(os.path.join(SCRIPTS_DIR, "lib", "common.sh"))).group(1).split()
        self.assertIn("PRESPEND_PROJECT_CEILING_USD", pinned, "no environment variable may widen the ceiling")

    def test_the_spending_callers_pass_the_ceiling_and_cleanup_prepare_does_not(self):
        deploy = read(os.path.join(SCRIPTS_DIR, "deploy.sh"))
        self.assertIn('CEILING_ARGS=(--ceiling-usd "${PRESPEND_PROJECT_CEILING_USD}")', deploy)
        self.assertRegex(deploy, r'if \[\[ "\$\{STAGE\}" != "cleanup-prepare" && -n "\$\{PRESPEND_PROJECT_CEILING_USD:-\}" \]\]')
        self.assertIn('"${HEADROOM_ARGS[@]}" ${CEILING_ARGS[@]+"${CEILING_ARGS[@]}"}', deploy)
        pipeline = read(os.path.join(SCRIPTS_DIR, "run-bounded-pipeline.sh"))
        self.assertIn('ceiling=(--ceiling-usd "${PRESPEND_PROJECT_CEILING_USD}")', pipeline)
        self.assertIn('--min-headroom "${PRESPEND_MIN_HEADROOM_USD}" ${ceiling[@]+"${ceiling[@]}"}', pipeline)


class ProviderCleanupRuleTests(unittest.TestCase):
    def test_both_key_containers_are_teardown_addresses_that_the_classifier_targets(self):
        rules = conf()["CLEANUP_TEARDOWN_ADDRESS_RULES"]
        with tempfile.TemporaryDirectory() as tmp:
            state = os.path.join(tmp, "state.txt")
            targets = os.path.join(tmp, "targets.txt")
            with open(state, "w") as handle:
                handle.write("aws_secretsmanager_secret.anthropic[0]\naws_secretsmanager_secret.voyage[0]\naws_secretsmanager_secret.other[0]\nmodule.foundation.aws_budgets_budget.course[0]\n")
            result = run(VERIFY, [
                "classify-state", "--state-file", state, "--targets-out", targets,
                "--teardown-addresses", rules, "--preserve-addresses", conf()["CLEANUP_PRESERVE_ADDRESS_RULES"], "--preserve-types", conf()["CLEANUP_PRESERVE_TYPE_RULES"],
            ])
            self.assertIn(result.returncode, (0, 1), result.stdout + result.stderr)
            text = result.stdout
            self.assertIn("aws_secretsmanager_secret.anthropic", text)
            self.assertIn("aws_secretsmanager_secret.voyage", text)
            self.assertRegex(text, r"NOT-TARGETED aws_secretsmanager_secret\.other\[0\]", "a secret that is not one of the two containers stays UNLISTED and is never destroyed")
            with open(targets) as handle:
                self.assertEqual(sorted(handle.read().split()), ["aws_secretsmanager_secret.anthropic", "aws_secretsmanager_secret.voyage"])

    def test_cleanup_prints_the_key_revocation_reminder_in_every_final_path(self):
        text = read(os.path.join(SCRIPTS_DIR, "cleanup.sh"))
        self.assertEqual(text.count("_revoke_keys_reminder\n"), 3, "dry run, the confirmation token and after the destroy apply")
        self.assertIn("does NOT revoke the keys", text)
        self.assertIn("Anthropic Console", text)
        self.assertIn("Voyage AI dashboard", text)
        self.assertNotRegex(text, r"(sk-ant|pa-)[A-Za-z0-9_-]{16}")


class NoBedrockPreconditionTests(unittest.TestCase):
    def test_no_script_holds_a_bedrock_quota_precondition_or_a_haiku_playground_step(self):
        offenders = []
        for root, dirs, files in os.walk(SCRIPTS_DIR):
            dirs[:] = [d for d in dirs if d not in ("tests", "__pycache__", "phase12d-spike")]
            for name in files:
                if name.endswith((".pyc", ".md")) or name == "reviewed-pins.json":
                    continue
                path = os.path.join(root, name)
                text = read(path)
                for needle in ("playground", "quota increase", "bedrock quota", "service quota", "ServiceQuotas", "service-quotas"):
                    if needle.lower() in text.lower():
                        offenders.append("%s: %s" % (os.path.relpath(path, REPO), needle))
        self.assertEqual(offenders, [])

    def test_no_script_calls_a_bedrock_api(self):
        offenders = []
        for root, dirs, files in os.walk(SCRIPTS_DIR):
            dirs[:] = [d for d in dirs if d not in ("tests", "__pycache__", "phase12d-spike")]
            for name in files:
                if not name.endswith((".sh", ".py")):
                    continue
                text = read(os.path.join(root, name))
                if re.search(r"aws\s+bedrock|bedrock-runtime|InvokeModel|converse", text, re.I):
                    offenders.append(os.path.relpath(os.path.join(root, name), REPO))
        self.assertEqual(offenders, [])


class CostReportTests(unittest.TestCase):
    def report(self, document, fmt="text", text=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "in.json")
            with open(path, "w") as handle:
                handle.write(text if text is not None else json.dumps(document))
            result = run(COST_REPORT, ["render", "--input", path, "--format", fmt])
            return result.returncode, result.stdout, result.stderr

    def base(self):
        return {
            "schema": "scholarchain.cost-report.v1",
            "as_of_utc": "2026-11-20T12:00:00Z",
            "ceiling_usd": 25,
            "items": {
                "aws": {"usd": 17.40, "usage": "ECS, Neptune, EMR, NAT and S3 as shown in Cost Explorer, tax included"},
                "anthropic": {"usd": 0.81, "usage": "claude-haiku-5-5: 115 answers"},
                "voyage": {"usd": 0, "usage": "voyage-4-lite: 3.1M tokens, inside the 200M free tokens"},
            },
        }

    def test_the_report_lists_aws_anthropic_and_voyage_separately_then_the_combined_total(self):
        code, out, err = self.report(self.base())
        self.assertEqual(code, 0, out + err)
        lines = out.splitlines()
        self.assertEqual(lines[0], "Project cost report as of 2026-11-20T12:00:00Z")
        item_lines = [l for l in lines if l.startswith(("AWS ", "Anthropic ", "Voyage AI ", "Combined "))]
        self.assertEqual([l.split()[0] for l in item_lines], ["AWS", "Anthropic", "Voyage", "Combined"])
        self.assertRegex(item_lines[0], r"^AWS\s+USD\s+17\.40\s+usage: ECS, Neptune")
        self.assertRegex(item_lines[1], r"^Anthropic\s+USD\s+0\.81\s+usage: claude-haiku-5-5: 115 answers")
        self.assertRegex(item_lines[2], r"^Voyage AI\s+USD\s+0\.00\s+usage: voyage-4-lite: 3\.1M tokens")
        self.assertRegex(item_lines[3], r"^Combined\s+USD\s+18\.21\b")
        self.assertIn("Project ceiling USD 25.00; remaining USD 6.79", out)
        self.assertNotIn("OVER THE CEILING", out)

    def test_a_provider_with_no_charge_is_usd_0_with_its_usage_and_a_zero_without_usage_is_refused(self):
        document = self.base()
        document["items"]["voyage"]["usage"] = "  "
        code, out, _err = self.report(document)
        self.assertEqual(code, 1)
        self.assertIn("COST-REPORT-REFUSED: voyage.usage is missing or empty (documented usage is required, also for USD 0)", out)
        document = self.base()
        del document["items"]["voyage"]["usage"]
        self.assertEqual(self.report(document)[0], 1)

    def test_every_item_is_required_and_no_other_item_is_accepted(self):
        for key in ("aws", "anthropic", "voyage"):
            document = self.base()
            del document["items"][key]
            code, out, _err = self.report(document)
            self.assertEqual(code, 1, key)
            self.assertIn("item %s is missing" % key, out)
        document = self.base()
        document["items"]["other"] = {"usd": 1, "usage": "hidden"}
        code, out, _err = self.report(document)
        self.assertEqual(code, 1)
        self.assertIn("unlisted item other", out)

    def test_amounts_must_be_finite_non_negative_json_numbers(self):
        for label, value in (("string", "1.00"), ("null", None), ("boolean", True), ("negative", -0.01), ("huge", 10 ** 9), ("list", [1])):
            with self.subTest(label):
                document = self.base()
                document["items"]["aws"]["usd"] = value
                code, out, _err = self.report(document)
                self.assertEqual(code, 1, out)
                self.assertIn("COST-REPORT-REFUSED: aws.usd", out)
        for literal in ("NaN", "Infinity"):
            with self.subTest(literal):
                text = json.dumps(self.base()).replace('"usd": 17.4', '"usd": %s' % literal)
                code, out, _err = self.report(None, text=text)
                self.assertEqual(code, 1, out)
                self.assertIn("not valid JSON", out)

    def test_the_total_is_exact_decimal_arithmetic_rounded_to_the_cent(self):
        document = self.base()
        document["items"]["aws"]["usd"] = 0.1
        document["items"]["anthropic"]["usd"] = 0.2
        document["items"]["voyage"]["usd"] = 0.004
        code, out, _err = self.report(document, fmt="json")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["combined_total_usd"], "0.30", "0.1 + 0.2 + 0.004 = 0.304 exactly, rounded to the cent, with no binary-float artifact")
        self.assertEqual([i["provider"] for i in payload["items"]], ["AWS", "Anthropic", "Voyage AI"])
        self.assertEqual([i["usd"] for i in payload["items"]], ["0.10", "0.20", "0.00"])
        self.assertEqual((payload["ceiling_usd"], payload["remaining_usd"], payload["over_ceiling"]), ("25.00", "24.70", False))

    def test_a_total_over_the_ceiling_is_reported_not_enforced(self):
        document = self.base()
        document["items"]["aws"]["usd"] = 25
        code, out, _err = self.report(document)
        self.assertEqual(code, 0)
        self.assertIn("remaining USD -0.81   OVER THE CEILING", out)

    def test_malformed_timestamp_ceiling_and_input_are_refused(self):
        for label, mutate in (
            ("timestamp", lambda d: d.update(as_of_utc="yesterday")),
            ("ceiling zero", lambda d: d.update(ceiling_usd=0)),
            ("ceiling missing", lambda d: d.pop("ceiling_usd")),
            ("items not an object", lambda d: d.update(items=[])),
            ("usage multi-line", lambda d: d["items"]["aws"].update(usage="a\nb")),
            ("usage too long", lambda d: d["items"]["aws"].update(usage="x" * 401)),
        ):
            with self.subTest(label):
                document = self.base()
                mutate(document)
                self.assertEqual(self.report(document)[0], 1)
        self.assertEqual(self.report(None, text="not json")[0], 1)
        self.assertEqual(self.report(None, text="[1]")[0], 1)
        result = run(COST_REPORT, ["render", "--input", "/nonexistent/input.json"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("input unreadable", result.stdout)

    def test_the_script_reads_no_credential_and_calls_no_service(self):
        text = read(COST_REPORT)
        for needle in ("boto3", "urllib", "http.client", "requests", "subprocess", "socket", "os.environ", "getenv"):
            self.assertNotIn(needle, text)


if __name__ == "__main__":
    unittest.main()
