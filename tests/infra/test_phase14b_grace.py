"""Phase 14B repair round 1 (review finding B1, user option (a)): the query-api health-check grace period and the explicit ALB
health-check timing.

Requirement (hand-derived from the user's decision; see phase14b_checks.py for the full list):
  * `health_check_grace_period_seconds` only where the load balancer attaches (query-api with a certificate), null elsewhere;
  * module grace variable default 300, whole seconds, validated; a validated ROOT variable (default 300) is passed to it as a
    plain var reference by the root `module "runtime"` call and documented (commented) in the example tfvars;
  * target group health_check: path "/readyz", matcher "200", explicit interval / timeout / healthy / unhealthy from validated
    module variables (defaults 30 / 5 / 3 / 3);
  * a guard refuses grace < healthy_threshold x interval (floor 90 s, 300 >= 90); timeout < interval is guarded on the target
    group; the deployment circuit breaker stays enabled with rollback.

Three groups:
  * RealTree: the checks on the real infra/terraform sources (read only).
  * CheckerSelfTest: a hand-written SYNTHETIC fixture (shaped like the requirement, not a copy of production) must pass, so the
    mutation cases cannot "fail" for a reason other than the mutation.
  * Mutations: each edit is made to an in-memory copy of the fixture AND of the real text (the repository is never written; every
    check takes text). Each must be reported with its specific check id.
Set SC_INFRA_EVIDENCE_FILE to keep a JSON-lines record of each mutation result.
"""
import re
import unittest

import hcl_text
import phase14b_checks as c
from infra_support import REPO, record_mutation

RUNTIME = REPO / "infra/terraform/modules/runtime"
ROOT = REPO / "infra/terraform"
EXAMPLE = ROOT / "environments/course.local.tfvars.example"

FIXTURE_COMPUTE = '''
locals {
  active_services       = { "query-api" = 1, "graph-service" = 1, "semantic-service" = 1, "embedding-worker" = 1 }
  # replan W5b: the caller's plan-time boolean wins; null keeps "HTTPS iff a certificate ARN is supplied"
  https                 = var.https_enabled != null ? var.https_enabled : var.certificate_arn != null
  load_balanced_service = local.https ? "query-api" : null
}
resource "aws_lb_target_group" "query" {
  count = 1
  name  = "x-query"
  health_check {
    path                = "/readyz"
    matcher             = "200"
    interval            = var.health_check_interval_seconds
    timeout             = var.health_check_timeout_seconds
    healthy_threshold   = var.health_check_healthy_threshold
    unhealthy_threshold = var.health_check_unhealthy_threshold
  }
  tags = var.tags
  lifecycle {
    precondition {
      condition     = var.health_check_timeout_seconds < var.health_check_interval_seconds
      error_message = "timeout must be smaller than the interval"
    }
  }
}
resource "aws_ecs_service" "service" {
  for_each                          = local.active_services
  name                              = each.key
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = each.key == local.load_balanced_service ? var.health_check_grace_period_seconds : null
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  dynamic "load_balancer" {
    for_each = each.key == local.load_balanced_service ? [each.key] : []
    content {
      container_name = each.key
    }
  }
  tags = var.tags
  lifecycle {
    ignore_changes = [desired_count]
    precondition {
      condition     = each.key != local.load_balanced_service || var.health_check_grace_period_seconds >= var.health_check_healthy_threshold * var.health_check_interval_seconds
      error_message = "grace must cover healthy_threshold x interval"
    }
  }
}
'''


def _fixture_variable(name, default, low, high):
    return '''
variable "%(n)s" {
  type    = number
  default = %(d)s
  validation {
    condition     = var.%(n)s >= %(lo)s && var.%(n)s <= %(hi)s && var.%(n)s == floor(var.%(n)s)
    error_message = "whole seconds from %(lo)s to %(hi)s"
  }
}
''' % {"n": name, "d": default, "lo": low, "hi": high}


FIXTURE_VARIABLES = ('variable "certificate_arn" { type = string }\nvariable "https_enabled" {\n  type    = bool\n  default = null\n}\n'
                     + _fixture_variable("health_check_grace_period_seconds", 300, 0, 3600)
                     + _fixture_variable("health_check_interval_seconds", 30, 5, 300)
                     + _fixture_variable("health_check_timeout_seconds", 5, 2, 120)
                     + _fixture_variable("health_check_healthy_threshold", 3, 2, 10)
                     + _fixture_variable("health_check_unhealthy_threshold", 3, 2, 10))

FIXTURE_ROOT = {
    "main.tf": 'locals {\n  runtime_deployed = var.runtime_enabled && var.image_revision != null\n'
               '  acm_validated    = var.api_domain_name != null && local.runtime_deployed\n'
               '  https_enabled    = var.https_certificate_arn != null || local.acm_validated\n}\n'
               'module "runtime" {\n  source = "./modules/runtime"\n  service_port = var.service_port\n'
               '  https_enabled = local.https_enabled\n'
               '  health_check_grace_period_seconds = var.query_health_check_grace_period_seconds\n}\n',
    "variables.tf": 'variable "service_port" {\n  type    = number\n  default = 8080\n}\n'
                    + _fixture_variable("query_health_check_grace_period_seconds", 300, 0, 3600),
}

FIXTURE_EXAMPLE = "# RUNTIME, optional\n# query_health_check_grace_period_seconds = 300\n"


def module_texts():
    return {p.name: hcl_text.strip_comments(p.read_text()) for p in sorted(RUNTIME.glob("*.tf"))}


def root_texts():
    return {p.name: hcl_text.strip_comments(p.read_text()) for p in sorted(ROOT.glob("*.tf"))}


def ids(problems):
    return {p[0] for p in problems}


def fmt(problems):
    return "\n".join("%s: %s" % p for p in problems)


class Sources:
    """compute / variables / root / example texts, either the fixture or the real tree, so one mutation runs on both.

    Real module and root texts are comment-stripped on load (line structure kept) so mutations can scan them safely; the example
    tfvars is kept raw because its comments are what the check reads."""

    def __init__(self, compute, variables, root, example, extra=None):
        self.compute, self.variables, self.root, self.example, self.extra = compute, variables, root, example, extra or {}

    @classmethod
    def fixture(cls):
        return cls(FIXTURE_COMPUTE, FIXTURE_VARIABLES, dict(FIXTURE_ROOT), FIXTURE_EXAMPLE)

    @classmethod
    def real(cls):
        mt = module_texts()
        extra = {k: v for k, v in mt.items() if k not in ("compute.tf", "variables.tf")}
        return cls(mt["compute.tf"], mt["variables.tf"], root_texts(), EXAMPLE.read_text(), extra)

    def modules(self):
        mods = dict(self.extra)
        mods["compute.tf"] = self.compute
        mods["variables.tf"] = self.variables
        return mods

    def problems(self):
        return c.check_all(self.compute, self.variables, self.modules(), self.root, self.example)

    def names(self):
        d = c.discover(self.compute, self.variables, self.modules(), self.root)
        assert d["grace"] and d["root"] and len(d["tg"]) == 4, "unmutated sources do not name every variable: %s" % d
        return d

    def but(self, **changes):
        s = Sources(self.compute, self.variables, self.root, self.example, self.extra)
        for k, v in changes.items():
            setattr(s, k, v)
        return s


# ----------------------------------------------------------------------------------------------- edit helpers
def _span(text, header_regex, what):
    m = re.search(header_regex, text, re.M)
    assert m, "mutation anchor not found: %s" % what
    return m.end(), hcl_text.matching_brace(text, m.end() - 1)


def edit_resource(text, rtype, name, fn):
    start, end = _span(text, r'^[ \t]*resource[ \t]+"%s"[ \t]+"%s"[ \t]*\{' % (rtype, name), "%s.%s" % (rtype, name))
    body = text[start:end]
    new = fn(body)
    assert new != body, "the mutation changed nothing in %s.%s" % (rtype, name)
    return text[:start] + new + text[end:]


def edit_variable(text, name, fn):
    start, end = _span(text, r'^[ \t]*variable[ \t]+"%s"[ \t]*\{' % re.escape(name), "variable %s" % name)
    body = text[start:end]
    new = fn(body)
    assert new != body, "the mutation changed nothing in variable %s" % name
    return text[:start] + new + text[end:]


def remove_variable(text, name):
    m = re.search(r'^[ \t]*variable[ \t]+"%s"[ \t]*\{' % re.escape(name), text, re.M)
    assert m, "variable %s not found" % name
    return text[:m.start()] + text[hcl_text.matching_brace(text, m.end() - 1) + 1:]


def edit_root_variable(root, name, fn):
    for fname, text in root.items():
        if re.search(r'^[ \t]*variable[ \t]+"%s"[ \t]*\{' % re.escape(name), text, re.M):
            out = dict(root)
            out[fname] = edit_variable(text, name, fn)
            return out
    raise AssertionError("root variable %s not declared in any root file" % name)


def edit_runtime_call(root, fn):
    for fname, text in root.items():
        m = re.search(r'^[ \t]*module[ \t]+"runtime"[ \t]*\{', text, re.M)
        if m:
            out = dict(root)
            start, end = m.end(), hcl_text.matching_brace(text, m.end() - 1)
            new = fn(text[start:end])
            assert new != text[start:end], "the mutation changed nothing in the runtime module call"
            out[fname] = text[:start] + new + text[end:]
            return out
    raise AssertionError('no module "runtime" call in the root')


def set_attr(body, attr, value):
    new, n = re.subn(r"^([ \t]*%s[ \t]*=[ \t]*).*$" % re.escape(attr), lambda m: m.group(1) + value, body, count=1, flags=re.M)
    assert n == 1, "attribute %s not found" % attr
    return new


def drop_attr(body, attr):
    new, n = re.subn(r"^[ \t]*%s[ \t]*=.*\n" % re.escape(attr), "", body, count=1, flags=re.M)
    assert n == 1, "attribute %s not found" % attr
    return new


def drop_nested(body, header_regex):
    m = re.search(header_regex + r"[ \t]*\{", body)
    assert m, "nested block %s not found" % header_regex
    end = hcl_text.matching_brace(body, m.end() - 1)
    return body[:m.start()] + body[end + 1:]


def sub_once(body, pattern, repl):
    new, n = re.subn(pattern, repl, body, count=1)
    assert n == 1, "mutation anchor not found: %r" % pattern
    return new


def grace_span(compute):
    """(start, end, value_start) of the whole `health_check_grace_period_seconds = ...` line(s) in the aws_ecs_service block."""
    clean_start = compute.index('resource "aws_ecs_service" "service"')
    m = re.compile(r"^[ \t]*" + c.ATTR + r"[ \t]*=[ \t]*", re.M).search(compute, clean_start)
    assert m, "the grace attribute is not in the text under mutation"
    return m.start(), hcl_text.value_end(compute, m.end()), m.end()


def set_grace_expression(compute, expression):
    start, end, _ = grace_span(compute)
    return compute[:start] + "  %s = %s" % (c.ATTR, expression) + compute[end:]


def grace_expression(compute):
    _, end, value_start = grace_span(compute)
    return compute[value_start:end].strip()


def replace_once(text, old, new):
    assert old in text, "mutation anchor not found: %r" % old
    return text.replace(old, new, 1)


def replace_local(text, name, expression):
    """Replace the one-line `name = ...` assignment of a local in `text`."""
    new, n = re.subn(r"(?m)^([ \t]*%s[ \t]*=[ \t]*).*$" % re.escape(name), lambda m: m.group(1) + expression, text, count=1)
    assert n == 1, "local %s not found" % name
    return new


def edit_root_locals(root, name, expression):
    for fname, text in root.items():
        if re.search(r"(?m)^[ \t]*%s[ \t]*=" % re.escape(name), text):
            out = dict(root)
            out[fname] = replace_local(text, name, expression)
            return out
    raise AssertionError("root local %s not found" % name)


class CheckerSelfTest(unittest.TestCase):
    def test_fixture_is_clean(self):
        self.assertEqual([], Sources.fixture().problems())

    def test_ternary_splitter_and_evaluator(self):
        self.assertEqual(("a == \"x\" && b", "var.v", "null"), c.split_ternary('a == "x" && b ? var.v : null'))
        self.assertEqual(("a", "[b ? 1 : 2]", "[]"), c.split_ternary("(a ? [b ? 1 : 2] : [])"))
        self.assertTrue(c.evaluate_cond('each.key == "query-api" && var.certificate_arn != null', "query-api", c.CERT))
        self.assertFalse(c.evaluate_cond('each.key == "query-api" && var.certificate_arn != null', "query-api", None))
        self.assertFalse(c.evaluate_cond('each.key == "query-api" && var.certificate_arn != null', "graph-service", c.CERT))
        self.assertTrue(c.evaluate_cond('each.key != "embedding-worker" || !(var.certificate_arn == null)', "x", c.CERT))
        with self.assertRaises(ValueError):
            c.evaluate_cond("__import__('os').system('x')", "query-api", None)
        with self.assertRaises(ValueError):
            c.evaluate_cond("var.something_else", "query-api", None)

    def test_https_enabled_ternary_and_the_scenario_grid(self):
        """Replan W5b: local.https = var.https_enabled != null ? var.https_enabled : var.certificate_arn != null."""
        https = 'each.key == ((var.https_enabled != null ? var.https_enabled : var.certificate_arn != null) ? "query-api" : null)'
        for cert in (None, c.CERT):
            for flag in c.HTTPS_VALUES:
                for key in c.SERVICES:
                    got = c.evaluate_cond(https, key, cert, {"var.https_enabled": flag})
                    self.assertEqual(got, c.expected_active(key, cert, flag), (key, cert, flag))
        # the hand-derived corners: an unknown-ARN certificate (cert None) with https true is load balanced; a certificate with false is not
        self.assertTrue(c.expected_active("query-api", None, True))
        self.assertFalse(c.expected_active("query-api", c.CERT, False))
        self.assertTrue(c.expected_active("query-api", c.CERT, None))
        self.assertFalse(c.expected_active("query-api", None, None))
        self.assertFalse(c.expected_active("graph-service", c.CERT, True))
        self.assertEqual(len(c.SCENARIOS), 6)

    def test_root_https_decision_is_evaluated_over_the_whole_grid(self):
        self.assertEqual([], c.check_root_https(dict(FIXTURE_ROOT)))
        self.assertEqual(c.ROOT_HTTPS_ABSENT, c.check_root_https({"main.tf": "# nothing"})[0][0])

    def test_numeric_evaluator(self):
        env = {"var.g": 300, "var.h": 3, "var.i": 30}
        self.assertTrue(c.evaluate_cond("var.g >= var.h * var.i", None, None, env))
        self.assertTrue(c.evaluate_cond("var.g - var.h * var.i >= 200", None, None, env))
        self.assertFalse(c.evaluate_cond("var.g >= var.h * var.i", None, None, {"var.g": 89, "var.h": 3, "var.i": 30}))
        self.assertFalse(c.evaluate_cond("var.g == floor(var.g)", None, None, {"var.g": 300.5}))
        self.assertTrue(c.evaluate_cond("var.g == floor(var.g) && var.g >= 0", None, None, {"var.g": 300}))
        self.assertFalse(c.evaluate_cond("var.g >= 0", None, None, {"var.g": -1}))
        with self.assertRaises(ValueError):
            c.evaluate_cond("var.g >= var.unknown", None, None, env)

    def test_top_level_ignores_nested_blocks(self):
        body = c.block(FIXTURE_COMPUTE, "aws_ecs_service", "service")
        self.assertIsNone(c.attribute_value(c.top_level(body), "enable"))
        self.assertEqual("true", c.attribute_value(body, "enable"))
        self.assertIsNotNone(c.attribute_value(c.top_level(body), c.ATTR))

    def test_inline_condition_is_accepted(self):
        """The shared local is not required: the same condition written inline in both places is an equivalent rewrite."""
        inline = 'each.key == "query-api" && (var.https_enabled != null ? var.https_enabled : var.certificate_arn != null)'
        compute = FIXTURE_COMPUTE.replace("each.key == local.load_balanced_service ? ", inline + " ? ")
        compute = compute.replace("each.key != local.load_balanced_service ||", "!(%s) ||" % inline)
        self.assertNotIn("local.load_balanced_service ?", compute.split("locals {")[1].split("}")[1])
        self.assertEqual([], Sources.fixture().but(compute=compute).problems())


class RealTree(unittest.TestCase):
    """Read-only checks of the real sources. Fail until infra-engineer's change is present."""

    @classmethod
    def setUpClass(cls):
        cls.src = Sources.real()

    def test_all_checks_hold(self):
        self.assertEqual([], self.src.problems(), "\n" + fmt(self.src.problems()))

    def test_grace_only_on_load_balanced_service(self):
        problems, var = c.check_grace_in_service(self.src.compute, self.src.modules())
        self.assertEqual([], problems, "\n" + fmt(problems))
        self.assertIsNotNone(var)

    def test_module_grace_variable_default_300_validated(self):
        var = self.src.names()["grace"]
        body = c.variable_block(self.src.variables, var)
        self.assertEqual([], c.check_variable(body, var, "300", "grace"))

    def test_root_variable_default_300_passed_as_plain_reference(self):
        grace = self.src.names()["grace"]
        self.assertEqual([], c.check_root(self.src.root, grace, self.src.example), "root wiring")
        main = c.runtime_module_body(self.src.root)
        self.assertRegex(c.attribute_value(main, grace), r"^var\.[A-Za-z_][A-Za-z0-9_]*$")

    def test_example_tfvars_documents_the_root_variable_commented(self):
        root_var = self.src.names()["root"]
        self.assertRegex(self.src.example, r"(?m)^[ \t]*#+[ \t]*%s[ \t]*=[ \t]*300[ \t]*$" % re.escape(root_var))
        self.assertNotRegex(self.src.example, r"(?m)^[ \t]*%s[ \t]*=" % re.escape(root_var))

    def test_target_group_explicit_timing_from_validated_variables(self):
        problems, names = c.check_target_group(self.src.compute, self.src.variables, self.src.modules())
        self.assertEqual([], problems, "\n" + fmt(problems))
        self.assertEqual({"interval", "timeout", "healthy_threshold", "unhealthy_threshold"}, set(names))

    def test_module_defaults_are_30_5_3_3_300(self):
        names = self.src.names()
        d = c.defaults_of(self.src.variables, names["tg"], names["grace"])
        self.assertEqual({"grace": 300, "interval": 30, "healthy": 3, "unhealthy": 3}, d)
        timeout = c.variable_block(self.src.variables, names["tg"]["timeout"])
        self.assertEqual("5", c.attribute_value(c.top_level(timeout), "default"))

    def test_hand_derived_arithmetic(self):
        """3 x 30 = 90 s to become unhealthy; 3 x 30 = 90 s to recover; 300 >= 90 and 300 - 90 = 210 >= 200 for peers."""
        names = self.src.names()
        d = c.defaults_of(self.src.variables, names["tg"], names["grace"])
        self.assertEqual(90, d["unhealthy"] * d["interval"])
        self.assertEqual(90, d["healthy"] * d["interval"])
        self.assertGreaterEqual(d["grace"], d["healthy"] * d["interval"])
        self.assertGreaterEqual(d["grace"] - d["healthy"] * d["interval"], 200)
        self.assertEqual([], c.check_arithmetic(self.src.variables, names["tg"], names["grace"]))

    def test_grace_guard_precondition_on_service(self):
        names = self.src.names()
        self.assertEqual([], c.check_grace_guard(self.src.compute, self.src.modules(), names["grace"], names["tg"]))

    def test_timeout_guard_precondition_on_target_group(self):
        problems, _ = c.check_target_group(self.src.compute, self.src.variables, self.src.modules())
        self.assertNotIn(c.TG_GUARD_MISSING, ids(problems))
        self.assertNotIn(c.TG_GUARD_WRONG, ids(problems))

    def test_target_group_path_and_matcher(self):
        problems, _ = c.check_target_group(self.src.compute, self.src.variables, self.src.modules())
        self.assertFalse(ids(problems) & {c.TG_PATH, c.TG_MATCHER, c.TG_MISSING})

    def test_circuit_breaker_still_enabled_with_rollback(self):
        self.assertEqual([], c.check_circuit_breaker(self.src.compute))

    def test_other_modules_do_not_set_grace(self):
        """Only the one service resource sets the argument; no second ECS service resource appears in the runtime module."""
        for name, text in self.src.extra.items():
            for rtype, rname, body in hcl_text.resource_blocks(text):
                if rtype == "aws_ecs_service":
                    self.fail("%s declares a second aws_ecs_service.%s" % (name, rname))
        self.assertEqual(1, len([1 for t, n, _ in hcl_text.resource_blocks(self.src.compute) if t == "aws_ecs_service"]))


def _mutations():
    """(name, expected check ids (any one suffices), function Sources -> Sources). Each is a real edit and asserts its anchor."""

    def lb_condition(src):
        m = re.search(r'dynamic[ \t]+"load_balancer"[ \t]*\{\s*for_each[ \t]*=[ \t]*([^\n]*?)[ \t]*\?[ \t]*\[each\.key\]', src.compute)
        assert m, "load_balancer for_each not in the expected `cond ? [each.key] : []` shape"
        return m.group(1)

    def with_compute(src, text):
        return src.but(compute=text)

    # --- grace attribute on the service
    def all_services(src):
        return with_compute(src, set_grace_expression(src.compute, "var.%s" % src.names()["grace"]))

    def literal(value):
        return lambda src: with_compute(src, set_grace_expression(src.compute, "%s ? %s : null" % (lb_condition(src), value)))

    def cond_missing_cert(src):
        return with_compute(src, set_grace_expression(src.compute, 'each.key == "query-api" ? var.%s : null' % src.names()["grace"]))

    def cond_wrong_service(src):
        return with_compute(src, set_grace_expression(
            src.compute, 'each.key == "graph-service" && var.certificate_arn != null ? var.%s : null' % src.names()["grace"]))

    def cond_also_others(src):
        return with_compute(src, set_grace_expression(
            src.compute, 'each.key != "embedding-worker" && var.certificate_arn != null ? var.%s : null' % src.names()["grace"]))

    def false_branch_zero(src):
        return with_compute(src, set_grace_expression(src.compute, "%s ? var.%s : 0" % (lb_condition(src), src.names()["grace"])))

    def attribute_removed(src):
        start, end, _ = grace_span(src.compute)
        return with_compute(src, src.compute[:start] + src.compute[end + 1:])

    def inside_nested_block(src):
        start, end, _ = grace_span(src.compute)
        expr = grace_expression(src.compute)
        text = src.compute[:start] + src.compute[end + 1:]
        return with_compute(src, replace_once(text, "deployment_circuit_breaker {", "deployment_circuit_breaker {\n    %s = %s" % (c.ATTR, expr)))

    def lb_condition_widened(src):
        cond = lb_condition(src)
        m = re.fullmatch(r"each\.key == local\.([A-Za-z_][A-Za-z0-9_]*)", cond.strip())
        if m:
            rx = re.compile(r"^([ \t]*%s[ \t]*=[ \t]*).*$" % re.escape(m.group(1)), re.M)
            assert rx.search(src.compute), "local %s is not defined in compute.tf" % m.group(1)
            return with_compute(src, rx.sub(r'\g<1>var.certificate_arn != null ? "graph-service" : null', src.compute, count=1))
        return with_compute(src, replace_once(src.compute, cond, 'each.key != "embedding-worker" && var.certificate_arn != null'))

    # --- module variables
    def module_var(role, fn):
        def run(src):
            n = src.names()
            name = n["grace"] if role == "grace" else n["tg"][role]
            return src.but(variables=edit_variable(src.variables, name, fn))
        return run

    def set_default(value):
        return lambda body: sub_once(body, r"(?m)^([ \t]*default[ \t]*=[ \t]*)[0-9.]+", lambda m: m.group(1) + str(value))

    def remove_default(body):
        return drop_attr(body, "default")

    def remove_validation(body):
        return drop_nested(body, r"\bvalidation")

    def drop_whole_check(body):
        return sub_once(body, r"[ \t]*&&[ \t]*var\.[A-Za-z_]+[ \t]*==[ \t]*floor\(var\.[A-Za-z_]+\)", "")

    def drop_lower_bound(body):
        return sub_once(body, r"var\.([A-Za-z_]+)[ \t]*>=[ \t]*[0-9]+[ \t]*&&[ \t]*", "")

    def variable_removed(src):
        n = src.names()["grace"]
        return src.but(variables=remove_variable(src.variables, n))

    # --- root wiring
    def root_var(fn):
        return lambda src: src.but(root=edit_root_variable(src.root, src.names()["root"], fn))

    def root_not_passed(src):
        g = src.names()["grace"]
        return src.but(root=edit_runtime_call(src.root, lambda body: drop_attr(body, g)))

    def root_literal(src):
        g = src.names()["grace"]
        return src.but(root=edit_runtime_call(src.root, lambda body: set_attr(body, g, "300")))

    def root_other_variable(src):
        g = src.names()["grace"]
        return src.but(root=edit_runtime_call(src.root, lambda body: set_attr(body, g, "var.service_port")))

    def root_variable_removed(src):
        n = src.names()["root"]
        out = {}
        for fname, text in src.root.items():
            out[fname] = remove_variable(text, n) if re.search(r'^[ \t]*variable[ \t]+"%s"' % re.escape(n), text, re.M) else text
        assert out != src.root, "root variable not found"
        return src.but(root=out)

    def example_removed(src):
        n = src.names()["root"]
        text, k = re.subn(r"(?m)^[ \t]*#+[ \t]*%s[ \t]*=.*\n" % re.escape(n), "", src.example)
        assert k >= 1, "example line not found"
        return src.but(example=text)

    def example_uncommented(src):
        n = src.names()["root"]
        text, k = re.subn(r"(?m)^[ \t]*#+[ \t]*(%s[ \t]*=)" % re.escape(n), r"\1", src.example)
        assert k >= 1, "example line not found"
        return src.but(example=text)

    # --- replan W5b: the HTTPS decision
    def root_https(expression):
        return lambda src: src.but(root=edit_runtime_call(src.root, lambda body: set_attr(body, "https_enabled", expression)))

    def root_https_dropped(src):
        return src.but(root=edit_runtime_call(src.root, lambda body: drop_attr(body, "https_enabled")))

    def root_acm_validated_ignores_runtime(src):
        return src.but(root=edit_root_locals(src.root, "acm_validated", "var.api_domain_name != null"))

    def root_https_ignores_external_certificate(src):
        return src.but(root=edit_root_locals(src.root, "https_enabled", "local.acm_validated"))

    def module_https_ignores_flag(src):
        return with_compute(src, replace_local(src.compute, "https", "var.certificate_arn != null"))

    def module_https_without_fallback(src):
        return with_compute(src, replace_local(src.compute, "https", "var.https_enabled != null ? var.https_enabled : false"))

    def module_https_flag_only(src):
        return with_compute(src, replace_local(src.compute, "https", "var.https_enabled == true"))

    # --- target group
    def tg_edit(fn):
        return lambda src: with_compute(src, edit_resource(src.compute, "aws_lb_target_group", "query", fn))

    def path_changed(src):
        return with_compute(src, replace_once(src.compute, '"/readyz"', '"/healthz"'))

    def matcher_changed(src):
        return with_compute(src, edit_resource(src.compute, "aws_lb_target_group", "query", lambda b: set_attr(b, "matcher", '"200-399"')))

    # --- guards
    def svc_edit(fn):
        return lambda src: with_compute(src, edit_resource(src.compute, "aws_ecs_service", "service", fn))

    def guard_removed(body):
        return drop_nested(body, r"\bprecondition")

    def guard_trivially_true(src):
        return with_compute(src, edit_resource(src.compute, "aws_ecs_service", "service",
                                               lambda b: sub_once(b, r"(?s)(precondition[ \t]*\{\s*condition[ \t]*=[ \t]*)[^\n]*", r"\g<1>true")))

    def guard_one_interval(src):
        t = src.names()["tg"]
        pat = r"var\.%s[ \t]*\*[ \t]*var\.%s" % (t["healthy_threshold"], t["interval"])
        return with_compute(src, edit_resource(src.compute, "aws_ecs_service", "service",
                                               lambda b: sub_once(b, pat, "var.%s" % t["interval"])))

    def guard_strict(src):
        g, t = src.names()["grace"], src.names()["tg"]
        pat = r"(var\.%s[ \t]*)>=([ \t]*var\.%s)" % (g, t["healthy_threshold"])
        return with_compute(src, edit_resource(src.compute, "aws_ecs_service", "service", lambda b: sub_once(b, pat, r"\1>\2")))

    def guard_blocks_other_services(src):
        return with_compute(src, edit_resource(
            src.compute, "aws_ecs_service", "service",
            lambda b: sub_once(b, r"each\.key[ \t]*!=[ \t]*local\.[A-Za-z_]+[ \t]*\|\|[ \t]*", "")))

    def tg_guard_removed(body):
        return drop_nested(body, r"\bprecondition")

    def tg_guard_nonstrict(src):
        t = src.names()["tg"]
        pat = r"(var\.%s[ \t]*)<(?!=)([ \t]*var\.%s)" % (t["timeout"], t["interval"])
        return with_compute(src, edit_resource(src.compute, "aws_lb_target_group", "query", lambda b: sub_once(b, pat, r"\1<=\2")))

    # --- circuit breaker
    def breaker_rollback_off(src):
        return with_compute(src, edit_resource(src.compute, "aws_ecs_service", "service",
                                               lambda b: sub_once(b, r"(rollback[ \t]*=[ \t]*)true", r"\1false")))

    def breaker_disabled(src):
        return with_compute(src, edit_resource(src.compute, "aws_ecs_service", "service",
                                               lambda b: sub_once(b, r"(\benable[ \t]*=[ \t]*)true", r"\1false")))

    out = [
        ("grace applied to every service (no condition)", {c.NOT_CONDITIONAL}, all_services),
        ("grace is a bare literal 300 instead of the variable", {c.LITERAL, c.NOT_VARIABLE}, literal(300)),
        ("grace is a bare literal 120 instead of the variable", {c.LITERAL, c.NOT_VARIABLE}, literal(120)),
        ("grace condition drops the certificate test", {c.WRONG_CONDITION}, cond_missing_cert),
        ("grace condition names the wrong service", {c.WRONG_CONDITION}, cond_wrong_service),
        ("grace condition also covers graph-service and semantic-service", {c.WRONG_CONDITION}, cond_also_others),
        ("grace false branch is 0 instead of null", {c.NOT_NULL_ELSE}, false_branch_zero),
        ("grace attribute removed", {c.ABSENT}, attribute_removed),
        ("grace attribute moved into a nested block", {c.NOT_TOP_LEVEL, c.ABSENT}, inside_nested_block),
        ("load-balancer condition widened (grace follows it)", {c.LB_CONDITION_CHANGED}, lb_condition_widened),
        ("module grace default changed to 120", {c.vid("grace", "default")}, module_var("grace", set_default(120))),
        ("module grace default removed", {c.vid("grace", "default")}, module_var("grace", remove_default)),
        ("module grace validation block removed", {c.vid("grace", "validation-missing")}, module_var("grace", remove_validation)),
        ("module grace validation accepts fractions (whole-seconds test dropped)", {c.vid("grace", "validation-lax")},
         module_var("grace", drop_whole_check)),
        ("module grace validation accepts negatives (lower bound dropped)", {c.vid("grace", "validation-lax")},
         module_var("grace", drop_lower_bound)),
        ("module grace variable declaration removed", {c.vid("grace", "undeclared")}, variable_removed),
        ("root grace default changed to 120", {c.vid("root-grace", "default")}, root_var(set_default(120))),
        ("root grace default removed", {c.vid("root-grace", "default")}, root_var(remove_default)),
        ("root grace validation block removed", {c.vid("root-grace", "validation-missing")}, root_var(remove_validation)),
        ("root grace validation accepts fractions", {c.vid("root-grace", "validation-lax")}, root_var(drop_whole_check)),
        ("root grace variable declaration removed", {c.vid("root-grace", "undeclared")}, root_variable_removed),
        ("root module call does not pass the grace variable", {c.ROOT_NOT_PASSED}, root_not_passed),
        ("root module call passes a literal 300", {c.ROOT_LITERAL}, root_literal),
        ("root module call passes another root variable (service_port)", {c.vid("root-grace", "default")}, root_other_variable),
        ("example tfvars no longer documents the root variable", {c.EXAMPLE_MISSING}, example_removed),
        ("example tfvars sets the root variable uncommented", {c.EXAMPLE_ACTIVE}, example_uncommented),
        ("root passes a literal https_enabled = true", {c.ROOT_HTTPS_WRONG}, root_https("true")),
        ("root passes https_enabled from the external certificate only (ACM ignored)", {c.ROOT_HTTPS_WRONG},
         root_https("var.https_certificate_arn != null")),
        ("root passes https_enabled from a resource attribute (unknown at plan time)", {c.ROOT_HTTPS_WRONG},
         root_https("aws_acm_certificate_validation.api[0].certificate_arn != null")),
        ("root does not pass https_enabled", {c.ROOT_HTTPS_ABSENT}, root_https_dropped),
        ("root treats a managed certificate as validated without the runtime", {c.ROOT_HTTPS_WRONG}, root_acm_validated_ignores_runtime),
        ("root https decision ignores the external certificate", {c.ROOT_HTTPS_WRONG}, root_https_ignores_external_certificate),
        ("module HTTPS ignores the caller's boolean", {c.LB_CONDITION_CHANGED}, module_https_ignores_flag),
        ("module HTTPS drops the certificate fallback", {c.LB_CONDITION_CHANGED}, module_https_without_fallback),
        ("module HTTPS follows only a true flag", {c.LB_CONDITION_CHANGED}, module_https_flag_only),
        ("target-group path changed to /healthz", {c.TG_PATH}, path_changed),
        ("target-group matcher changed to 200-399", {c.TG_MATCHER}, matcher_changed),
        ("circuit-breaker rollback turned off", {c.BREAKER}, breaker_rollback_off),
        ("circuit breaker disabled", {c.BREAKER}, breaker_disabled),
        ("guard precondition removed from the service", {c.GUARD_MISSING}, svc_edit(guard_removed)),
        ("guard precondition is always true", {c.GUARD_WRONG}, guard_trivially_true),
        ("guard weakened to 1 x interval", {c.GUARD_WRONG}, guard_one_interval),
        ("guard made strict (> instead of >=)", {c.GUARD_WRONG}, guard_strict),
        ("guard also blocks services that carry no grace", {c.GUARD_WRONG}, guard_blocks_other_services),
        ("timeout < interval precondition removed from the target group", {c.TG_GUARD_MISSING}, tg_edit(tg_guard_removed)),
        ("timeout < interval precondition weakened to <=", {c.TG_GUARD_WRONG}, tg_guard_nonstrict),
    ]
    for attr, role, var_default in (("interval", "interval", 60), ("timeout", "timeout", 10), ("healthy_threshold", "healthy_threshold", 5),
                                    ("unhealthy_threshold", "unhealthy_threshold", 2)):
        label = c.TG_PREFIX[attr]
        out += [
            ("target-group %s is a literal instead of a variable" % attr, {c.tg_literal(attr)},
             tg_edit(lambda b, a=attr: sub_once(b, r"(?m)^([ \t]*%s[ \t]*=[ \t]*).*$" % a, r"\g<1>%s" % TG_LITERALS[a]))),
            ("target-group %s attribute removed" % attr, {c.tg_absent(attr)}, tg_edit(lambda b, a=attr: drop_attr(b, a))),
            ("module %s default changed to %s" % (attr, var_default), {c.vid(label, "default")}, module_var(role, set_default(var_default))),
            ("module %s validation block removed" % attr, {c.vid(label, "validation-missing")}, module_var(role, remove_validation)),
            ("module %s validation accepts fractions" % attr, {c.vid(label, "validation-lax")}, module_var(role, drop_whole_check)),
        ]
    return out


TG_LITERALS = {"interval": "30", "timeout": "5", "healthy_threshold": "3", "unhealthy_threshold": "3"}


class Mutations(unittest.TestCase):
    """Run every mutation on the synthetic fixture and on the real tree; each must be caught with its own check id."""

    def _run(self, label, source_factory):
        base = source_factory()
        self.assertEqual([], base.problems(), "the unmutated %s must be clean first:\n%s" % (label, fmt(base.problems())))
        for name, expected, mutate in _mutations():
            with self.subTest(source=label, mutation=name):
                mutated = mutate(source_factory())
                found = ids(mutated.problems())
                caught = bool(found & expected)
                record_mutation("phase14b-r1/%s/%s" % (label, name), {"expected": sorted(expected), "found": sorted(found), "caught": caught})
                self.assertTrue(caught, "mutation %r was not caught as %s (found %s)" % (name, sorted(expected), sorted(found)))

    def test_mutation_count(self):
        self.assertGreaterEqual(len(_mutations()), 15)

    def test_mutations_on_fixture(self):
        self._run("fixture", Sources.fixture)

    def test_mutations_on_real_tree(self):
        self._run("real", Sources.real)


if __name__ == "__main__":
    unittest.main()
