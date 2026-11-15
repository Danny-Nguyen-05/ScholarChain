"""Phase 14B replan, workstreams W5b (API certificate, Neptune tunnel) and W4 (full purge at cleanup), plus the W5a-3 deployer grant:
independent tests written from the user's decisions (docs/agent-runs/phase-14/prompt.md, "Replan decisions" 4 and 5, "14C decisions"
1, "Answers" 4), not from the implementation.

Evidence types, all offline and read-only on the repository:
  * REAL offline `terraform plan` (real AWS provider, fake credentials, closed proxy) of a scratch copy of the main root with the
    variable sets of a base stage and a runtime stage (main_root_shape.py), and of the deployer root;
  * a mock-provider apply of a scratch wrapper around modules/runtime, where the real provider leaves the container definitions
    unknown (they embed ECR URLs that only exist after apply);
  * text checks of the sources and of scripts/config/release.conf.
"""
import json
import re
import unittest

import hcl_text
import main_root_shape as M
import phase14b_checks as c
import runtime_shape_checks as R
from infra_support import REPO, TfTree
import account_scan as scan

EXT_CERT = "arn:aws:acm:us-east-2:111122223333:certificate/00000000-0000-0000-0000-000000000001"
ROOT = REPO / "infra/terraform"
TUNNEL_ACTIONS = {"ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel",
                  "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"}


def root_texts():
    return {p.name: hcl_text.strip_comments(p.read_text()) for p in sorted(ROOT.glob("*.tf"))}


def text_of(result):
    return re.sub(r"\s+", " ", result.stdout + result.stderr)


class Plans:
    """One MainPlans per test class (plans are cached per variable set)."""

    @classmethod
    def open(cls):
        cls.mp = M.MainPlans()
        cls.addClassCleanup(cls.mp.close)


class AcmCertificate(Plans, unittest.TestCase):
    """Plans are made once per class, but a plan that FAILS does not abort the class: each test that needs it fails on its own with
    the plan error, so a mutant is caught by a test assertion and never only by setUpClass."""

    SETS = {
        "base": lambda: dict(api_domain_name=M.DOMAIN),
        "runtime": lambda: dict(api_domain_name=M.DOMAIN, **M.RUNTIME_VARS),
        "image_only": lambda: dict(api_domain_name=M.DOMAIN, image_revision=M.IMAGE),
        "external": lambda: dict(https_certificate_arn=EXT_CERT, **M.RUNTIME_VARS),
        "none": lambda: dict(),
    }

    @classmethod
    def setUpClass(cls):
        cls.open()
        cls.plans, cls.errors = {}, {}
        for name, variables in cls.SETS.items():
            try:
                cls.plans[name] = cls.mp.plan(**variables())
            except AssertionError as error:
                cls.plans[name], cls.errors[name] = None, str(error)[-900:]

    def _get(self, name):
        if self.plans[name] is None:
            self.fail("the %s-stage plan failed:\n%s" % (name, self.errors[name]))
        return self.plans[name]

    base = property(lambda self: self._get("base"))
    runtime = property(lambda self: self._get("runtime"))
    image_only = property(lambda self: self._get("image_only"))
    external = property(lambda self: self._get("external"))
    none = property(lambda self: self._get("none"))

    def test_the_base_stage_plan_succeeds_and_contains_exactly_one_api_certificate(self):
        """Direct assertion (not a side effect of setUpClass): base-apply requests the certificate whenever api_domain_name is set."""
        plan = self.base
        certificates = sorted(a for a in M.resources(plan) if a.startswith("aws_acm_certificate."))
        self.assertEqual(certificates, ["aws_acm_certificate.api[0]"], "exactly one aws_acm_certificate.api in the base-stage plan")

    # --- base stage: the certificate exists, nothing waits for validation
    def test_base_apply_creates_one_dns_validated_certificate_for_the_domain(self):
        certs = M.resources(self.base, "aws_acm_certificate")
        self.assertEqual(list(certs), ["aws_acm_certificate.api[0]"])
        cert = M.after(self.base, "aws_acm_certificate.api[0]")
        self.assertEqual((cert["domain_name"], cert["validation_method"]), (M.DOMAIN, "DNS"))

    def test_base_apply_has_no_validation_resource_and_no_listener(self):
        self.assertEqual(M.resources(self.base, "aws_acm_certificate_validation"), {})
        self.assertEqual(M.resources(self.base, "aws_lb_listener"), {})
        self.assertEqual(M.resources(self.base, "aws_lb"), {})

    def test_a_domain_alone_with_an_image_revision_but_no_runtime_still_waits_for_nothing(self):
        self.assertEqual(M.resources(self.image_only, "aws_acm_certificate_validation"), {})
        self.assertEqual(len(M.resources(self.image_only, "aws_acm_certificate")), 1)
        self.assertEqual(M.resources(self.image_only, "aws_lb_listener"), {})

    def test_the_certificate_tags_satisfy_the_deployer_acm_tag_conditions(self):
        """The deployer allows RequestCertificate only with request tags project and environment equal to the stack's, and
        AddTagsToCertificate only with tag keys from main_tag_keys."""
        tags = M.after(self.base, "aws_acm_certificate.api[0]")["tags"]
        key = M.after(self.base, "module.identity.aws_kms_key.data")["tags"]
        for name in ("project", "environment"):
            self.assertEqual(tags[name], key[name], name)
        self.assertEqual(tags["environment"], "course")
        deployer_default = re.search(r'variable "main_tag_keys"[^{]*\{.*?default\s*=\s*\[(.*?)\]', (ROOT / "deployer/variables.tf").read_text(), re.S)
        allowed = set(re.findall(r'"([^"]+)"', deployer_default.group(1)))
        self.assertLessEqual(set(tags), allowed, "tag keys outside the deployer's main_tag_keys: %s" % sorted(set(tags) - allowed))
        self.assertEqual(M.after(self.base, "aws_acm_certificate.api[0]")["tags_all"], tags)

    def test_the_validation_record_and_the_alb_name_are_outputs(self):
        names = M.output_names(self.base)
        self.assertLessEqual({"acm_validation_records", "alb_dns_name", "acm_certificate_arn"}, names)
        record = self.base["output_changes"]["acm_validation_records"]
        self.assertEqual([r["domain_name"] for r in record["after"]], [M.DOMAIN])
        self.assertTrue(all(record["after_unknown"][0][k] for k in ("name", "type", "value")), "CNAME name, type and value come from ACM at apply")
        self.assertIsNone(self.base["output_changes"]["alb_dns_name"]["after"], "no ALB before the runtime")
        self.assertTrue(self.runtime["output_changes"]["alb_dns_name"]["after_unknown"], "the ALB DNS name exists after the runtime apply")

    def test_without_a_domain_there_is_no_certificate_and_no_record(self):
        self.assertEqual(M.resources(self.none, "aws_acm_certificate"), {})
        self.assertEqual(self.none["output_changes"]["acm_validation_records"]["after"], [])

    # --- runtime stage: validation, then the listener
    def test_runtime_apply_adds_exactly_one_validation_with_the_default_timeout_and_no_fqdn_list(self):
        validations = M.resources(self.runtime, "aws_acm_certificate_validation")
        self.assertEqual(list(validations), ["aws_acm_certificate_validation.api[0]"])
        after = M.after(self.runtime, "aws_acm_certificate_validation.api[0]")
        self.assertEqual(after["timeouts"], {"create": "15m"})
        self.assertIsNone(after["validation_record_fqdns"], "the DNS record lives at Cloudflare, outside Terraform")
        self.assertEqual(len(M.resources(self.runtime, "aws_acm_certificate")), 1)

    def test_the_https_listener_exists_only_with_the_runtime_and_gets_its_certificate_at_apply(self):
        listener = M.after(self.runtime, "module.runtime.aws_lb_listener.https[0]")
        self.assertEqual((listener["port"], listener["protocol"]), (443, "HTTPS"))
        self.assertTrue(M.unknown(self.runtime, "module.runtime.aws_lb_listener.https[0]")["certificate_arn"],
                        "the validated ARN is known only after the validation: it must not be a plan-time constant")

    def test_a_custom_validation_timeout_reaches_the_resource(self):
        plan = self.mp.plan(api_domain_name=M.DOMAIN, acm_validation_timeout="30m", **M.RUNTIME_VARS)
        self.assertEqual(M.after(plan, "aws_acm_certificate_validation.api[0]")["timeouts"], {"create": "30m"})

    # --- the external certificate keeps working and excludes the managed one
    def test_an_external_certificate_creates_no_acm_resource_and_the_listener_uses_it(self):
        self.assertEqual(M.resources(self.external, "aws_acm_certificate"), {})
        self.assertEqual(M.resources(self.external, "aws_acm_certificate_validation"), {})
        listener = M.after(self.external, "module.runtime.aws_lb_listener.https[0]")
        self.assertEqual(listener["certificate_arn"], EXT_CERT)
        self.assertEqual(self.external["output_changes"]["acm_validation_records"]["after"], [])

    def test_exactly_one_certificate_source_is_allowed(self):
        done = self.mp.attempt(api_domain_name=M.DOMAIN, https_certificate_arn=EXT_CERT, **M.RUNTIME_VARS)
        self.assertNotEqual(done.returncode, 0)
        self.assertRegex(text_of(done), r"(?i)exactly one")

    def test_invalid_domain_names_are_refused(self):
        for bad in ("example.invalid", "API.example.invalid", "*.example.invalid", "api.example.invalid.", "api..example.invalid",
                    "-api.example.invalid", "api.example.invalid:443", "api_x.example.invalid", "api.example.invalid/path", ""):
            with self.subTest(domain=bad):
                self.assertNotEqual(self.mp.attempt(api_domain_name=bad).returncode, 0, bad)
        for good in ("api.example.invalid", "a.b.example.invalid", "api-1.example.invalid"):
            with self.subTest(domain=good):
                done = self.mp.attempt(api_domain_name=good)
                self.assertEqual(done.returncode, 0, done.stdout[-600:] + done.stderr[-600:])

    def test_invalid_validation_timeouts_are_refused(self):
        for bad in ("0m", "61m", "15", "15s", "1h", "-5m", "1.5m", ""):
            with self.subTest(timeout=bad):
                self.assertNotEqual(self.mp.attempt(api_domain_name=M.DOMAIN, acm_validation_timeout=bad).returncode, 0, bad)
        for good in ("1m", "15m", "60m"):
            with self.subTest(timeout=good):
                self.assertEqual(self.mp.attempt(api_domain_name=M.DOMAIN, acm_validation_timeout=good).returncode, 0, good)

    def test_the_runtime_with_a_managed_certificate_still_needs_approved_ingress(self):
        vars_ = dict(M.RUNTIME_VARS, public_ingress_cidrs=[])
        done = self.mp.attempt(api_domain_name=M.DOMAIN, **vars_)
        self.assertNotEqual(done.returncode, 0)
        self.assertRegex(text_of(done), r"(?i)ingress")

    # --- structure of the source (what a plan cannot show)
    def test_the_listener_uses_the_validation_attribute_never_the_raw_certificate(self):
        texts = root_texts()
        expr = c.resolve_locals(c.attribute_value(c.runtime_module_body(texts), "certificate_arn"), c.locals_of(texts))
        self.assertIn("aws_acm_certificate_validation.api", expr)
        self.assertNotIn("aws_acm_certificate.api", expr, "an unvalidated certificate ARN must never reach the listener")

    def test_resource_counts_follow_the_staging_over_the_whole_input_grid(self):
        texts = root_texts()
        known = c.locals_of(texts)
        body = {}
        for text in texts.values():
            for rtype, name, b in hcl_text.resource_blocks(text):
                body[(rtype, name)] = b
        cert_count = c.resolve_locals(c.attribute_value(body[("aws_acm_certificate", "api")], "count"), known)
        valid_count = c.resolve_locals(c.attribute_value(body[("aws_acm_certificate_validation", "api")], "count"), known)
        self.assertNotIn("aws_acm_certificate", c.attribute_value(body[("aws_acm_certificate_validation", "api")], "count") or "")
        for domain in (None, M.DOMAIN):
            for runtime in (False, True):
                for image in (None, "rev1"):
                    scope = {"var.api_domain_name": domain, "var.runtime_enabled": runtime, "var.image_revision": image}
                    self.assertEqual(c.evaluate_cond(cert_count, None, None, scope), 1 if domain else 0, scope)
                    self.assertEqual(c.evaluate_cond(valid_count, None, None, scope),
                                     1 if domain and runtime and image else 0, "validation only with runtime and image: %s" % scope)


class RepositoryHasNoRealDomain(unittest.TestCase):
    """The real hostname is a private tfvars value only (user answer 2). Only *.example.invalid or a placeholder may be committed."""

    ASSIGNMENT = re.compile(r"""api_domain_name\s*=\s*["']([^"']*)["']""")

    def offenders(self, files):
        found = []
        for path, text in files.items():
            for line_no, line in enumerate(text.splitlines(), 1):
                for value in self.ASSIGNMENT.findall(line):
                    host = re.sub(r"[:/].*$", "", value).rstrip(".")  # refusal fixtures use ports, trailing dots and the bare reserved name
                    if not (host.endswith("example.invalid") or ("<" in value and ">" in value) or value == ""):
                        found.append((path, line_no))
        return found

    def test_no_file_assigns_a_real_api_domain(self):
        files = {}
        names = scan._git("ls-files", "-z", "--cached", "--others", "--exclude-standard").decode("utf-8", "replace").split("\0")
        for name in names:
            if not name or scan.EXCLUDED.match(name) or name.startswith(("target/", "modules/")) or name == "tests/infra/test_w5b_w4_14b.py":
                continue
            path = REPO / name
            try:
                if path.is_file() and not path.is_symlink() and path.stat().st_size < 2_000_000:
                    files[name] = path.read_text()
            except (UnicodeDecodeError, OSError):
                continue
        self.assertGreater(len(files), 100)
        self.assertEqual(self.offenders(files), [])

    def test_the_scan_flags_a_real_looking_domain_and_accepts_the_placeholders(self):
        real = "api_domain_name = \"api." + "scholars" + ".dev\""
        for text in (real, "api_domain_name='x." + "example" + ".com'", "api_domain_name = \"api.corp." + "io\""):
            self.assertEqual(self.offenders({"x.tfvars": text}), [(("x.tfvars"), 1)], text)
        for ok in ('api_domain_name = "api.example.invalid"', '# api_domain_name        = "api.example.invalid"', 'api_domain_name = "<api>.<your-domain>"', '| `api_domain_name = "api.<domain>"`, x',
                   "api_domain_name = null"):
            self.assertEqual(self.offenders({"x.tfvars": ok}), [], ok)

    def test_the_example_tfvars_documents_the_domain_commented_with_the_invalid_tld(self):
        text = (ROOT / "environments/course.local.tfvars.example").read_text()
        active = re.findall(r"(?m)^\s*api_domain_name\s*=", text)
        self.assertEqual(active, [], "the example must not set the domain uncommented")
        self.assertRegex(text, r'(?m)^#\s*api_domain_name\s*=\s*"[a-z0-9.-]+\.example\.invalid"')


class NeptuneTunnel(Plans, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.open()
        cls.off = cls.mp.plan(api_domain_name=M.DOMAIN, **M.RUNTIME_VARS)
        cls.on = cls.mp.plan(api_domain_name=M.DOMAIN, neptune_tunnel_enabled=True, **M.RUNTIME_VARS)
        cls.no_runtime = cls.mp.plan(neptune_tunnel_enabled=True)

    def tunnel_addresses(self, plan):
        return sorted(a for a in M.resources(plan) if "tunnel" in a)

    def test_the_tunnel_is_absent_by_default(self):
        self.assertEqual(self.tunnel_addresses(self.off), [])
        self.assertIsNone(self.off["output_changes"]["neptune_tunnel"]["after"])

    def test_the_tunnel_needs_the_deployed_runtime_even_when_requested(self):
        self.assertEqual(self.tunnel_addresses(self.no_runtime), [])

    def test_when_enabled_exactly_the_task_role_its_policy_and_the_task_definition_exist(self):
        self.assertEqual(self.tunnel_addresses(self.on), [
            "module.identity.aws_iam_role.neptune_tunnel_task[0]", "module.identity.aws_iam_role_policy.neptune_tunnel_task[0]",
            "module.runtime.aws_ecs_task_definition.neptune_tunnel[0]"])

    def test_the_task_role_name_boundary_trust_and_exact_four_actions(self):
        role = M.after(self.on, "module.identity.aws_iam_role.neptune_tunnel_task[0]")
        self.assertEqual(role["name"], "scholarchain-course-neptune-tunnel-task")
        peers = {a: rc["change"]["after"] for a, rc in M.resources(self.on, "aws_iam_role").items()
                 if a.startswith("module.identity.aws_iam_role.task[")}
        self.assertTrue(peers)
        self.assertEqual({p["permissions_boundary"] for p in peers.values()}, {role["permissions_boundary"]},
                         "the tunnel role carries the runtime permissions boundary the task roles carry")
        self.assertTrue(role["permissions_boundary"].endswith(":policy/scholarchain-course-permissions-boundary"))
        trust = json.loads(role["assume_role_policy"])["Statement"]
        self.assertEqual([s["Principal"] for s in trust], [{"Service": "ecs-tasks.amazonaws.com"}])
        policy = json.loads(M.after(self.on, "module.identity.aws_iam_role_policy.neptune_tunnel_task[0]")["policy"])
        allow = [s for s in policy["Statement"] if s["Effect"] == "Allow"]
        self.assertEqual(len(policy["Statement"]), 1)
        self.assertEqual(set(allow[0]["Action"]), TUNNEL_ACTIONS)
        self.assertEqual(len(allow[0]["Action"]), 4)
        self.assertEqual(allow[0]["Resource"], "*")

    def test_the_task_definition_family_fargate_size_and_roles(self):
        td = M.after(self.on, "module.runtime.aws_ecs_task_definition.neptune_tunnel[0]")
        self.assertEqual(td["family"], "scholarchain-course-neptune-tunnel")
        self.assertEqual((td["cpu"], td["memory"], td["network_mode"]), ("256", "512", "awsvpc"))
        self.assertEqual(td["requires_compatibilities"], ["FARGATE"])
        unknown = M.unknown(self.on, "module.runtime.aws_ecs_task_definition.neptune_tunnel[0]")
        self.assertTrue(unknown["task_role_arn"] and unknown["container_definitions"])

    def test_no_ecs_service_exists_for_the_tunnel(self):
        for plan in (self.off, self.on):
            services = sorted(M.after(plan, a)["name"] for a in M.resources(plan, "aws_ecs_service"))
            self.assertEqual(services, ["embedding-worker", "graph-service", "query-api", "semantic-service"])
        self.assertEqual(set(M.resources(self.on, "aws_ecs_service")) , set(M.resources(self.off, "aws_ecs_service")))

    def test_outputs_for_the_writer_endpoint_port_cluster_resource_id_and_the_run_task_block(self):
        self.assertLessEqual({"neptune_writer_endpoint", "neptune_port", "neptune_cluster_resource_id", "neptune_tunnel"}, M.output_names(self.on))
        changes = self.on["output_changes"]
        self.assertEqual(changes["neptune_port"]["after"], 8182)
        self.assertTrue(changes["neptune_writer_endpoint"]["after_unknown"] and changes["neptune_cluster_resource_id"]["after_unknown"])
        block = changes["neptune_tunnel"]["after"]
        self.assertEqual((block["cluster_name"], block["family"], block["container_name"]),
                         ("scholarchain-course", "scholarchain-course-neptune-tunnel", "neptune-tunnel"))
        self.assertEqual(len(block["subnet_ids"]), 2)
        self.assertTrue(changes["neptune_tunnel"]["after_unknown"]["security_group_id"] and changes["neptune_tunnel"]["after_unknown"]["task_definition_arn"])

    def test_the_outputs_are_null_while_neptune_is_disabled(self):
        base = self.mp.plan()
        for name in ("neptune_writer_endpoint", "neptune_port", "neptune_cluster_resource_id", "neptune_tunnel"):
            self.assertIsNone(base["output_changes"][name]["after"], name)


class TunnelContainer(unittest.TestCase):
    """The container definition (mock apply of a scratch wrapper around modules/runtime)."""

    ROLE = "arn:aws:iam::111122223333:role/scholarchain-course-neptune-tunnel-task"

    @classmethod
    def setUpClass(cls):
        tree = R.ModuleTree("runtime", R.RUNTIME_VALUES, {"neptune_tunnel_enabled": True, "neptune_tunnel_task_role_arn": cls.ROLE},
                            snapshot="runtime_module_snapshot.tftest.hcl")
        cls.addClassCleanup(tree.close)
        state = tree.state_json()
        cls.resources = {r["address"][len("module.m."):]: r["values"] for r in state["root_module"]["child_modules"][0]["resources"]}
        cls.td = cls.resources["aws_ecs_task_definition.neptune_tunnel[0]"]
        cls.container = json.loads(cls.td["container_definitions"])

    def test_one_container_with_a_sleep_entrypoint_below_the_operator_session_limit(self):
        self.assertEqual(len(self.container), 1)
        c0 = self.container[0]
        self.assertEqual(c0["name"], "neptune-tunnel")
        self.assertEqual(c0["entryPoint"], ["sleep"])
        self.assertEqual(len(c0["command"]), 1)
        self.assertTrue(c0["command"][0].isdigit() and 0 < int(c0["command"][0]) <= 14400, "it exits by itself within the 4 h session")
        self.assertTrue(c0["essential"])

    def test_init_process_enabled_for_ecs_exec(self):
        self.assertIs(self.container[0]["linuxParameters"]["initProcessEnabled"], True)

    def test_the_graph_service_image_at_the_pushed_revision_and_the_graph_service_execution_role(self):
        self.assertEqual(self.container[0]["image"], "111122223333.dkr.ecr.us-east-2.amazonaws.com/scholarchain-course/graph-service:rev1")
        self.assertEqual(self.td["execution_role_arn"], R.RUNTIME_VALUES["execution_roles"]["graph-service"])
        self.assertEqual(self.td["task_role_arn"], self.ROLE)

    def test_no_environment_secrets_or_ports(self):
        for key in ("environment", "secrets", "portMappings", "environmentFiles", "mountPoints", "volumesFrom"):
            self.assertNotIn(key, self.container[0], key)
        self.assertEqual([v.get("name") for v in self.td.get("volume") or []], [], "no volumes either")

    def test_logs_go_to_the_graph_service_group_with_their_own_stream_prefix(self):
        options = self.container[0]["logConfiguration"]["options"]
        self.assertEqual(options["awslogs-group"], R.RUNTIME_VALUES["log_groups"]["graph-service"])
        self.assertEqual(options["awslogs-stream-prefix"], "neptune-tunnel")

    def test_fargate_size_and_family(self):
        self.assertEqual((self.td["family"], self.td["cpu"], self.td["memory"]), ("scholarchain-course-neptune-tunnel", "256", "512"))
        self.assertEqual(self.td["requires_compatibilities"], ["FARGATE"])

    def test_the_four_services_are_unchanged_by_the_tunnel(self):
        for service in R.SERVICES:
            td = self.resources['aws_ecs_task_definition.service["%s"]' % service]
            containers = json.loads(td["container_definitions"])
            self.assertEqual(len(containers), 1)
            self.assertIs(containers[0]["readonlyRootFilesystem"], True)
            self.assertNotIn("entryPoint", containers[0])
            self.assertTrue(containers[0]["portMappings"])
        services = [a for a in self.resources if a.startswith("aws_ecs_service.")]
        self.assertEqual(len(services), 4)

    def test_the_task_definition_without_a_task_role_is_refused(self):
        tree = R.ModuleTree("runtime", R.RUNTIME_VALUES, {"neptune_tunnel_enabled": True, "neptune_tunnel_task_role_arn": None})
        try:
            tree.init()
            done = tree.tf("plan", "-no-color", "-input=false")
            self.assertNotEqual(done.returncode, 0)
            self.assertRegex(text_of(done), r"(?i)tunnel")
        finally:
            tree.close()

    def test_the_tunnel_is_absent_from_the_module_unless_requested(self):
        tree = R.ModuleTree("runtime", R.RUNTIME_VALUES)
        try:
            self.assertEqual([a for a in tree.planned() if "tunnel" in a], [])
        finally:
            tree.close()


class CleanupPurge(Plans, unittest.TestCase):
    """W4 (user decision 5): the session ends with a full purge; only the Terraform state backend is preserved."""

    DATALAKE_BUCKETS = ("raw", "curated", "graph", "rag", "artifacts", "logs", "reports")

    @classmethod
    def setUpClass(cls):
        cls.open()
        cls.normal = cls.mp.plan(api_domain_name=M.DOMAIN, neptune_tunnel_enabled=True, **M.RUNTIME_VARS)
        cls.cleanup = cls.mp.plan(api_domain_name=M.DOMAIN, neptune_tunnel_enabled=True, cleanup_mode=True, **M.RUNTIME_VARS)
        conf = (REPO / "scripts/config/release.conf").read_text()
        cls.conf = dict(re.findall(r"^([A-Z_]+)=(\S+)\s*$", conf, re.M))

    def rules(self, key):
        return [x for x in re.split(r"[,\s]+", self.conf[key]) if x]

    # --- no prevent_destroy on anything of the purge scope
    def test_no_prevent_destroy_on_the_buckets_the_vector_bucket_or_the_indexes(self):
        for rel in ("modules/datalake/main.tf", "modules/s3vectors/main.tf"):
            clean = hcl_text.strip_comments((ROOT / rel).read_text())
            blocks = hcl_text.resource_blocks(clean)
            self.assertTrue([b for b in blocks if b[0] in ("aws_s3_bucket", "aws_s3vectors_vector_bucket", "aws_s3vectors_index")])
            for rtype, name, body in blocks:
                self.assertNotRegex(body, r"\bprevent_destroy\s*=", "%s.%s in %s" % (rtype, name, rel))
            self.assertNotRegex(clean, r"\bprevent_destroy\s*=", rel)

    def test_prevent_destroy_survives_only_in_the_preserved_state_backend_and_the_budget(self):
        holders = set()
        for path in ROOT.rglob("*.tf"):
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith(("spikes/", "tests/")) or "/.terraform/" in "/" + rel:
                continue
            if re.search(r"\bprevent_destroy\s*=", hcl_text.strip_comments(path.read_text())):
                holders.add(rel)
        self.assertEqual(holders, {"billing-bootstrap/main.tf", "modules/foundation/bootstrap/main.tf"})

    # --- force_destroy follows cleanup_mode and nothing else
    def test_force_destroy_is_false_by_default_and_true_only_in_cleanup_mode(self):
        for label, plan, expected in (("default", self.normal, False), ("cleanup_mode", self.cleanup, True)):
            buckets = {a: rc["change"]["after"] for a, rc in M.resources(plan, "aws_s3_bucket").items() if a.startswith("module.datalake.")}
            self.assertEqual(sorted(a.split('"')[1] for a in buckets), sorted(self.DATALAKE_BUCKETS), label)
            for a, after in buckets.items():
                self.assertIs(after["force_destroy"], expected, "%s %s" % (label, a))
            vector = M.after(plan, "module.s3vectors.aws_s3vectors_vector_bucket.embeddings")
            self.assertIs(vector["force_destroy"], expected, label)

    def test_cleanup_mode_does_not_turn_anything_else_destructive_on(self):
        names = {a for a, rc in M.resources(self.cleanup, "aws_s3_bucket").items()}
        names |= set(M.resources(self.cleanup, "aws_s3vectors_vector_bucket"))
        for a, rc in M.resources(self.cleanup).items():
            if a in names:
                continue
            self.assertNotIn(rc["change"]["after"].get("force_destroy"), (True,), a)

    def test_the_kms_key_is_scheduled_for_deletion_not_kept(self):
        key = M.after(self.normal, "module.identity.aws_kms_key.data")
        self.assertTrue(7 <= key["deletion_window_in_days"] <= 30)
        self.assertEqual(M.after(self.normal, "module.identity.aws_kms_alias.data")["name"], "alias/scholarchain-course-data")

    # --- the pinned classification of scripts/config/release.conf
    def test_teardown_includes_the_purge_scope(self):
        teardown = self.rules("CLEANUP_TEARDOWN_ADDRESS_RULES")
        for needed in ("module.datalake.", "module.s3vectors.", "module.identity.aws_kms_key.data", "module.identity.aws_kms_alias.data",
                       "module.observability.aws_cloudwatch_log_group.", "aws_acm_certificate.api", "aws_acm_certificate_validation.api",
                       "module.identity.aws_iam_role.neptune_tunnel_task", "module.identity.aws_iam_role.deployment"):
            self.assertIn(needed, teardown)

    def test_only_the_state_backend_is_preserved(self):
        self.assertEqual(self.rules("CLEANUP_PRESERVE"), ["terraform-state"])
        self.assertEqual(self.rules("CLEANUP_PRESERVE_ADDRESS_RULES"), ["module.foundation."])
        types = self.rules("CLEANUP_PRESERVE_TYPE_RULES")
        for forbidden in ("aws_s3_bucket", "aws_s3vectors_", "aws_kms_", "aws_cloudwatch_log_group", "aws_acm_", "aws_iam_role"):
            self.assertFalse([t for t in types if forbidden.startswith(t) or t.startswith(forbidden)], "%s must not be preserved" % forbidden)
        self.assertTrue(set(types) <= {"aws_s3_object"})
        for rule in self.rules("CLEANUP_TEARDOWN_ADDRESS_RULES"):
            self.assertFalse(rule.startswith("module.foundation"), "the preserved module must not be a teardown rule")

    def test_the_protection_rules_cover_the_buckets_that_force_destroy_unlocks(self):
        protection = self.rules("CLEANUP_PROTECTION_RULES")
        for needed in ("aws_s3_bucket:force_destroy=false", "aws_s3vectors_vector_bucket:force_destroy=false"):
            self.assertIn(needed, protection)
        allowed = self.conf["CLEANUP_PREPARE_ALLOWED_ATTRS"]
        self.assertRegex(allowed, r"aws_s3_bucket:force_destroy(,|$)")
        self.assertRegex(allowed, r"aws_s3vectors_vector_bucket:force_destroy(,|$)")

    def test_every_cloud_resource_of_the_full_plan_is_classified_by_the_pinned_rules(self):
        """Mirrors scripts/lib/verify.py's rule semantics (PRESERVE wins; an entry ending in '.' is a prefix; [index] removed). An
        UNLISTED cloud resource would be left behind by the purge. terraform_data guards hold no cloud object."""
        preserve_types, preserve_addresses = self.rules("CLEANUP_PRESERVE_TYPE_RULES"), self.rules("CLEANUP_PRESERVE_ADDRESS_RULES")
        teardown = self.rules("CLEANUP_TEARDOWN_ADDRESS_RULES")

        def hit(base, pattern):
            return base == pattern or (pattern.endswith(".") and base.startswith(pattern))

        unlisted, teardown_count = [], 0
        for address, rc in M.resources(self.cleanup).items():
            base = re.sub(r"\[[^\]]*\]", "", address)
            if rc["type"] == "terraform_data":
                continue
            if any(rc["type"].startswith(t) for t in preserve_types) or any(hit(base, p) for p in preserve_addresses):
                continue
            if any(hit(base, p) for p in teardown):
                teardown_count += 1
                continue
            unlisted.append(base)
        self.assertEqual(sorted(set(unlisted)), [])
        self.assertGreater(teardown_count, 100)

    def test_a_resource_of_every_purged_kind_is_in_the_full_plan(self):
        kinds = {rc["type"] for rc in M.resources(self.cleanup).values()}
        for needed in ("aws_s3_bucket", "aws_s3vectors_vector_bucket", "aws_s3vectors_index", "aws_kms_key", "aws_kms_alias", "aws_cloudwatch_log_group",
                       "aws_acm_certificate", "aws_acm_certificate_validation", "aws_iam_role"):
            self.assertIn(needed, kinds)


class DeployerDeleteGrant(unittest.TestCase):
    """W5a-3, python parity of the five points: the deployer may delete objects in the project buckets (needed by force_destroy), once,
    narrowly, and holds no vector-level S3 Vectors action."""

    BUCKET_PATTERN = "arn:aws:s3:::scholarchain-course-111122223333-*/*"
    VECTOR_LEVEL = ("PutVectors", "GetVectors", "QueryVectors", "ListVectors", "DeleteVectors")

    @classmethod
    def setUpClass(cls):
        with TfTree("deployer14") as tree:
            plan = tree.plan_json()
        cls.statements = []
        for rc in plan["resource_changes"]:
            if rc["address"].startswith("aws_iam_policy.permission_set["):
                doc = json.loads(rc["change"]["after"]["policy"])
                cls.statements += [(rc["address"], s) for s in (doc["Statement"] if isinstance(doc["Statement"], list) else [doc["Statement"]])]

    def actions(self, statement):
        a = statement.get("Action", [])
        return [a] if isinstance(a, str) else list(a)

    def test_1_the_object_delete_actions_appear_in_exactly_one_allow_statement(self):
        holders = [s for _, s in self.statements if s["Effect"] == "Allow" and any(x in ("s3:DeleteObject", "s3:DeleteObjectVersion") for x in self.actions(s))]
        self.assertEqual(len(holders), 1)
        for action in ("s3:DeleteObject", "s3:DeleteObjectVersion"):
            self.assertEqual(sum(self.actions(s).count(action) for _, s in self.statements if s["Effect"] == "Allow"), 1, action)

    def test_2_that_statement_holds_exactly_those_two_actions(self):
        holder = next(s for _, s in self.statements if "s3:DeleteObject" in self.actions(s))
        self.assertEqual(sorted(self.actions(holder)), ["s3:DeleteObject", "s3:DeleteObjectVersion"])

    def test_3_on_the_project_bucket_object_pattern_only(self):
        holder = next(s for _, s in self.statements if "s3:DeleteObject" in self.actions(s))
        resources = holder["Resource"] if isinstance(holder["Resource"], list) else [holder["Resource"]]
        self.assertEqual(resources, [self.BUCKET_PATTERN])

    def test_4_with_the_region_condition(self):
        holder = next(s for _, s in self.statements if "s3:DeleteObject" in self.actions(s))
        self.assertEqual(holder["Condition"], {"StringEquals": {"aws:RequestedRegion": "us-east-2"}})

    def test_5_no_vector_level_s3vectors_action_is_granted_and_no_s3_wildcard(self):
        for address, s in self.statements:
            for action in self.actions(s):
                self.assertNotRegex(action, r"^s3vectors:(%s)$" % "|".join(self.VECTOR_LEVEL), "%s grants %s" % (address, action))
                self.assertNotIn(action, ("s3:*", "s3vectors:*", "*"), address)
        granted = {a for _, s in self.statements if s["Effect"] == "Allow" for a in self.actions(s) if a.startswith("s3vectors:")}
        self.assertTrue(granted, "the S3 Vectors bucket and index actions themselves are still granted")
        self.assertIn("s3vectors:DeleteIndex", granted)
        self.assertIn("s3vectors:DeleteVectorBucket", granted)


if __name__ == "__main__":
    unittest.main()
