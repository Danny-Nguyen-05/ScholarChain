"""Static checks for the Phase 14B query-api health-check repair (review 1 finding B1, user option (a)).

Requirement (the user's decision, hand-derived; the checks come from it, not from the implementation):
  1. `aws_ecs_service.service` in modules/runtime/compute.tf sets `health_check_grace_period_seconds` ONLY where the
     `dynamic "load_balancer"` block attaches (query-api with a certificate; one shared condition) and yields null elsewhere
     (ECS rejects the argument on a service without a load balancer).
  2. The module grace variable has default 300 (whole seconds, number, validated). The value is a variable, not a literal.
  3. A validated ROOT variable (default 300, whole seconds) exists and the root `module "runtime"` call passes it to the module
     grace variable as a plain `var.<name>` reference (a literal at the root is a failure), so the human can tune it in the
     private tfvars without a commit. `environments/course.local.tfvars.example` documents it as a commented line.
  4. The target group `aws_lb_target_group.query` health_check has path "/readyz", matcher "200" and EXPLICIT interval, timeout,
     healthy_threshold and unhealthy_threshold, each a `var.<name>` reference (never a literal), whose module defaults are
     interval 30, timeout 5, healthy 3, unhealthy 3, each type number with a validation block that rejects negative,
     fractional and beyond-int32 values.
  5. A guard (a lifecycle precondition on aws_ecs_service.service) refuses a load-balanced grace smaller than
     healthy_threshold x interval (a target marked unhealthy must be able to recover inside the grace); it must not block the
     services that carry no grace. A precondition on the target group requires timeout < interval.
  6. deployment_circuit_breaker stays enable = true, rollback = true.
  7. Arithmetic from the defaults: unhealthy after 3 x 30 = 90 s; recovery needs 3 x 30 = 90 s; default grace 300 >= 90 with
     at least 200 s (300 - 90 = 210) left for peer readiness.

Stdlib only; no Terraform and no AWS. Every check takes TEXT (never a path), so a test can feed a mutated copy held in memory and
the repository is never written. A check returns `(check_id, detail)` pairs; an empty list means it holds.

Conditions are checked by EVALUATING them (a small translator for numbers, strings, `each.key`, `var.<name>`, `floor()`,
arithmetic, comparison, `==`, `!=`, `&&`, `||`, `!` and the ternary), after resolving `local.<name>`, so an equivalent rewrite
passes and a weakened condition fails.
"""
import math
import re

import hcl_text

SERVICES = ("query-api", "graph-service", "semantic-service", "embedding-worker")
ATTR = "health_check_grace_period_seconds"
CERT = "arn:aws:acm:us-east-2:000000000000:certificate/synthetic"
GRACE_DEFAULT = "300"
TG_ATTRS = {"interval": "30", "timeout": "5", "healthy_threshold": "3", "unhealthy_threshold": "3"}
TG_PREFIX = {"interval": "tg-interval", "timeout": "tg-timeout", "healthy_threshold": "tg-healthy",
             "unhealthy_threshold": "tg-unhealthy"}
INT32_PLUS_ONE = 2147483648

# check ids
NO_SERVICE = "ecs-service-block-missing"
ABSENT = "grace-attribute-absent"
NOT_TOP_LEVEL = "grace-attribute-not-top-level"
LITERAL = "grace-literal-in-resource"
NOT_CONDITIONAL = "grace-expression-not-conditional"
NOT_VARIABLE = "grace-value-not-a-variable"
NOT_NULL_ELSE = "grace-false-branch-not-null"
UNEVALUABLE = "grace-condition-not-evaluable"
LB_UNEVALUABLE = "load-balancer-condition-not-evaluable"
WRONG_CONDITION = "grace-condition-differs-from-load-balancer"
LB_CONDITION_CHANGED = "load-balancer-condition-not-query-api-with-certificate"
ROOT_NOT_PASSED = "root-module-call-does-not-pass-grace"
ROOT_LITERAL = "root-passes-grace-not-a-plain-var-reference"
EXAMPLE_MISSING = "example-tfvars-does-not-document-root-variable"
EXAMPLE_ACTIVE = "example-tfvars-sets-root-variable-uncommented"
TG_MISSING = "target-group-missing"
TG_PATH = "target-group-health-path-not-readyz"
TG_MATCHER = "target-group-health-matcher-not-200"
BREAKER = "circuit-breaker-not-enabled-with-rollback"
GUARD_MISSING = "grace-guard-precondition-missing"
GUARD_WRONG = "grace-guard-precondition-wrong"
TG_GUARD_MISSING = "tg-timeout-guard-precondition-missing"
TG_GUARD_WRONG = "tg-timeout-guard-precondition-wrong"
ARITHMETIC = "default-arithmetic-violated"
ROOT_HTTPS_ABSENT = "root-does-not-pass-https-enabled"
ROOT_HTTPS_WRONG = "root-https-enabled-is-not-the-plan-time-https-decision"


def vid(prefix, kind):
    """Check id of a variable check: kind in undeclared, default, type, validation-missing, validation-lax, validation-rejects-default."""
    return "%s-var-%s" % (prefix, kind)


def tg_absent(attr):
    return "tg-%s-absent" % attr


def tg_literal(attr):
    return "tg-%s-not-a-variable" % attr


# ----------------------------------------------------------------------------------------------- text scanning
def block(text, rtype, name):
    for t, n, body in hcl_text.resource_blocks(text):
        if (t, n) == (rtype, name):
            return body
    return None


def top_level(body):
    """The body with every nested `{...}` blanked (newlines kept), so only the resource's own attributes remain."""
    out, i, depth = [], 0, 0
    while i < len(body):
        c = body[i]
        if c == '"':
            j = hcl_text._skip_string(body, i)
            seg = body[i:j]
            out.append(seg if depth == 0 else re.sub(r"[^\n]", " ", seg))
            i = j
            continue
        if body.startswith("<<", i):
            j = hcl_text._skip_heredoc(body, i)
            if j is not None:
                seg = body[i:j]
                out.append(seg if depth == 0 else re.sub(r"[^\n]", " ", seg))
                i = j
                continue
        if c == "{":
            depth += 1
            out.append(c if depth == 1 else " ")
        elif c == "}":
            out.append(c if depth == 1 else " ")
            depth -= 1
        else:
            out.append(c if depth == 0 or c == "\n" else " ")
        i += 1
    return "".join(out)


def attribute_value(text, attribute):
    """The normalised value text of `attribute = value` anywhere in text (first match), or None."""
    m = re.search(r"^[ \t]*" + re.escape(attribute) + r"[ \t]*=[ \t]*", text, re.M)
    if not m:
        return None
    return " ".join(text[m.end():hcl_text.value_end(text, m.end())].split())


def sub_block(body, header):
    """Body text of the first nested `header {` block inside body, or None. `header` is a regex."""
    m = re.search(header + r"[ \t]*\{", body)
    if not m:
        return None
    return body[m.end():hcl_text.matching_brace(body, m.end() - 1)]


def preconditions(body):
    """[(condition, error_message)] of the lifecycle preconditions inside a resource body."""
    lifecycle = sub_block(body, r"\blifecycle")
    out = []
    if lifecycle is None:
        return out
    for p in re.finditer(r"\bprecondition[ \t]*\{", lifecycle):
        pb = lifecycle[p.end():hcl_text.matching_brace(lifecycle, p.end() - 1)]
        out.append((attribute_value(pb, "condition"), attribute_value(pb, "error_message")))
    return out


def split_ternary(expr):
    """(cond, a, b) for a top-level `cond ? a : b`, else None. Quotes, brackets and parentheses are respected."""
    expr = expr.strip()
    while expr.startswith("(") and _closes_at_end(expr):
        expr = expr[1:-1].strip()
    depth, q_at, i = 0, None, 0
    while i < len(expr):
        c = expr[i]
        if c == '"':
            i = hcl_text._skip_string(expr, i)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "?" and depth == 0 and q_at is None:
            q_at = i
        elif c == ":" and depth == 0 and q_at is not None:
            return expr[:q_at].strip(), expr[q_at + 1:i].strip(), expr[i + 1:].strip()
        i += 1
    return None


def _closes_at_end(expr):
    depth, i = 0, 0
    while i < len(expr):
        c = expr[i]
        if c == '"':
            i = hcl_text._skip_string(expr, i)
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i == len(expr) - 1
        i += 1
    return False


def locals_of(texts):
    """{name: normalised expression} from every `locals { ... }` block of the given {file: text} sources."""
    found = {}
    for text in texts.values():
        clean = hcl_text.strip_comments(text)
        for m in re.finditer(r"^[ \t]*locals[ \t]*\{", clean, re.M):
            body = clean[m.end():hcl_text.matching_brace(clean, m.end() - 1)]
            for a in re.finditer(r"^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*", body, re.M):
                if body[:a.start()].count("{") + body[:a.start()].count("[") + body[:a.start()].count("(") != \
                        body[:a.start()].count("}") + body[:a.start()].count("]") + body[:a.start()].count(")"):
                    continue
                found[a.group(1)] = " ".join(body[a.end():hcl_text.value_end(body, a.end())].split())
    return found


def resolve_locals(expr, known):
    for _ in range(6):
        new = re.sub(r"\blocal\.([A-Za-z_][A-Za-z0-9_]*)", lambda m: "(%s)" % known.get(m.group(1), m.group(0)), expr)
        if new == expr:
            return new
        expr = new
    return expr


# ------------------------------------------------------------------------------------------------- evaluator
_LEX = re.compile(r'\s*(?:("(?:[^"\\]|\\.)*")|(&&|\|\||==|!=|>=|<=)|(\d+(?:\.\d+)?)|([A-Za-z_][A-Za-z0-9_.]*)|([!?:()<>+\-*/%,]))')


def _lex(src):
    out, i = [], 0
    src = src.rstrip()
    while i < len(src):
        m = _LEX.match(src, i)
        if not m:
            raise ValueError("unsupported syntax near %r" % src[i:i + 12])
        if m.group(1) is not None:
            out.append(("str", m.group(1)))
        elif m.group(2) is not None:
            out.append(("op", m.group(2)))
        elif m.group(3) is not None:
            out.append(("num", m.group(3)))
        elif m.group(4) is not None:
            out.append(("name", m.group(4)))
        else:
            out.append(("op", m.group(5)))
        i = m.end()
    return out


def evaluate_cond(cond, key, cert, env=None):
    """Evaluate a small Terraform expression. `env` maps dotted names (e.g. "var.x") to values. Anything unsupported or unknown
    raises ValueError."""
    toks = _lex(cond)
    pos = [0]
    names = {"each.key": key, "var.certificate_arn": cert, "var.enabled": True, "var.image_revision": "rev",
             "var.https_enabled": None, "null": None, "true": True, "false": False}
    names.update(env or {})

    def peek():
        return toks[pos[0]][1] if pos[0] < len(toks) else None

    def peek_kind():
        return toks[pos[0]][0] if pos[0] < len(toks) else None

    def take(expected=None):
        if pos[0] >= len(toks):
            raise ValueError("expected %r, found end" % (expected,))
        kind, t = toks[pos[0]]
        if expected is not None and t != expected:
            raise ValueError("expected %r, found %r" % (expected, t))
        pos[0] += 1
        return kind, t

    def ternary():
        v = disjunction()
        if peek_kind() == "op" and peek() == "?":
            take()
            a = ternary()
            take(":")
            b = ternary()
            return a if v else b
        return v

    def disjunction():
        v = conjunction()
        while peek_kind() == "op" and peek() == "||":
            take()
            r = conjunction()
            v = bool(v) or bool(r)
        return v

    def conjunction():
        v = equality()
        while peek_kind() == "op" and peek() == "&&":
            take()
            r = equality()
            v = bool(v) and bool(r)
        return v

    def equality():
        v = comparison()
        while peek_kind() == "op" and peek() in ("==", "!="):
            op = take()[1]
            r = comparison()
            v = (v == r) if op == "==" else (v != r)
        return v

    def comparison():
        v = additive()
        while peek_kind() == "op" and peek() in ("<", "<=", ">", ">="):
            op = take()[1]
            r = additive()
            try:
                v = {"<": v < r, "<=": v <= r, ">": v > r, ">=": v >= r}[op]
            except TypeError:
                raise ValueError("cannot compare %r %s %r" % (v, op, r))
        return v

    def additive():
        v = multiplicative()
        while peek_kind() == "op" and peek() in ("+", "-"):
            op = take()[1]
            r = multiplicative()
            try:
                v = v + r if op == "+" else v - r
            except TypeError:
                raise ValueError("cannot add/subtract %r %r" % (v, r))
        return v

    def multiplicative():
        v = unary()
        while peek_kind() == "op" and peek() in ("*", "/", "%"):
            op = take()[1]
            r = unary()
            try:
                v = v * r if op == "*" else (v / r if op == "/" else v % r)
            except (TypeError, ZeroDivisionError):
                raise ValueError("cannot apply %s to %r %r" % (op, v, r))
        return v

    def unary():
        if peek_kind() == "op" and peek() == "!":
            take()
            return not unary()
        if peek_kind() == "op" and peek() == "-":
            take()
            return -unary()
        return primary()

    def primary():
        kind, t = take()
        if kind == "op" and t == "(":
            v = ternary()
            take(")")
            return v
        if kind == "str":
            return t[1:-1]
        if kind == "num":
            return float(t) if "." in t else int(t)
        if kind == "name":
            if t == "floor" and peek() == "(":
                take("(")
                v = ternary()
                take(")")
                try:
                    return math.floor(v)
                except TypeError:
                    raise ValueError("floor of %r" % (v,))
            if t in names:
                return names[t]
        raise ValueError("unsupported term %r" % t)

    v = ternary()
    if pos[0] != len(toks):
        raise ValueError("unexpected %r" % (toks[pos[0]][1],))
    return v


# ------------------------------------------------------------------------------------------------------ checks
# Replan W5b: the caller may pass a plan-time boolean `https_enabled` (an ACM certificate created in the same apply has an ARN that
# is unknown at plan time). null keeps the earlier rule "HTTPS iff a certificate ARN is supplied"; true/false decides by itself.
HTTPS_VALUES = (None, True, False)
SCENARIOS = [(cert, https) for cert in (None, CERT) for https in HTTPS_VALUES]


def https_on(cert, https):
    return https if https is not None else cert is not None


def expected_active(key, cert, https=None):
    """query-api is load balanced exactly when HTTPS is on; nothing else ever is."""
    return key == "query-api" and https_on(cert, https)


def scenario_env(https):
    return {"var.https_enabled": https}


def check_grace_in_service(compute_text, module_texts):
    """The attribute exists, is conditional on the load-balancer condition, yields null elsewhere, and names a variable.

    Returns (problems, variable_name or None)."""
    body = block(compute_text, "aws_ecs_service", "service")
    if body is None:
        return [(NO_SERVICE, "resource aws_ecs_service.service not found")], None
    if attribute_value(body, ATTR) is None:
        return [(ABSENT, "%s is not set in aws_ecs_service.service" % ATTR)], None
    if attribute_value(top_level(body), ATTR) is None:
        return [(NOT_TOP_LEVEL, "%s is set only inside a nested block" % ATTR)], None
    problems = []
    raw = attribute_value(top_level(body), ATTR)
    known = locals_of(module_texts)
    expr = resolve_locals(raw, known)
    if re.search(r"\b\d+\b", re.sub(r'"[^"]*"', "", raw)):
        problems.append((LITERAL, "a numeric literal appears in the %s expression: %s" % (ATTR, raw)))
    parts = split_ternary(expr)
    if parts is None:
        problems.append((NOT_CONDITIONAL, "expression is not `condition ? value : null`: %s" % raw))
        return problems, None
    cond, yes, no = parts
    var = None
    m = re.fullmatch(r"\(*\s*var\.([A-Za-z_][A-Za-z0-9_]*)\s*\)*", yes)
    if m:
        var = m.group(1)
    else:
        problems.append((NOT_VARIABLE, "the value branch is not a variable reference: %s" % yes))
    if no.strip("() ") != "null":
        problems.append((NOT_NULL_ELSE, "the false branch is %r, not null" % no))
    lb_body = sub_block(body, r'dynamic[ \t]+"load_balancer"')
    lb_for = attribute_value(top_level(lb_body), "for_each") if lb_body is not None else None
    lb_parts = split_ternary(resolve_locals(lb_for, known)) if lb_for else None
    if lb_parts is None:
        problems.append((LB_UNEVALUABLE, "dynamic load_balancer for_each is not `condition ? [...] : []`: %s" % lb_for))
        return problems, var
    lb_cond = lb_parts[0]
    for key in SERVICES:
        for cert, https in SCENARIOS:
            scope = scenario_env(https)
            where = "%s, certificate=%s, https_enabled=%s" % (key, cert is not None, https)
            try:
                lb_on = bool(evaluate_cond(lb_cond, key, cert, scope))
            except ValueError as e:
                problems.append((LB_UNEVALUABLE, "%s (%s)" % (e, lb_cond)))
                return problems, var
            if lb_on != expected_active(key, cert, https):
                problems.append((LB_CONDITION_CHANGED, "load_balancer active=%s for %s" % (lb_on, where)))
            try:
                grace_on = bool(evaluate_cond(cond, key, cert, scope))
            except ValueError as e:
                problems.append((UNEVALUABLE, "%s (%s)" % (e, cond)))
                return problems, var
            if grace_on != lb_on:
                problems.append((WRONG_CONDITION, "%s for %s: grace applied=%s but load balancer attached=%s"
                                 % (ATTR, where, grace_on, lb_on)))
    return problems, var


def variable_block(variables_text, name):
    clean = hcl_text.strip_comments(variables_text)
    m = re.search(r'^[ \t]*variable[ \t]+"%s"[ \t]*\{' % re.escape(name), clean, re.M)
    if not m:
        return None
    return clean[m.end():hcl_text.matching_brace(clean, m.end() - 1)]


def variable_block_in(texts, name):
    """First declaration of variable `name` among {file: text}."""
    for text in texts.values():
        body = variable_block(text, name)
        if body is not None:
            return body
    return None


def _number(text):
    try:
        return float(text) if "." in text else int(text)
    except (TypeError, ValueError):
        return None


def check_variable(body, name, expected_default, prefix):
    """The variable body: default == expected_default, type number, and validation blocks that accept the default and reject
    a negative value, a fractional value and a value beyond int32."""
    if body is None:
        return [(vid(prefix, "undeclared"), "variable %r is not declared" % name)]
    problems = []
    top = top_level(body)
    default = attribute_value(top, "default")
    if default != expected_default:
        problems.append((vid(prefix, "default"), "default is %r, expected %s" % (default, expected_default)))
    if attribute_value(top, "type") != "number":
        problems.append((vid(prefix, "type"), "type is %r, expected number" % attribute_value(top, "type")))
    conds, pos = [], 0
    while True:
        v = re.compile(r"\bvalidation[ \t]*\{").search(body, pos)
        if not v:
            break
        end = hcl_text.matching_brace(body, v.end() - 1)
        vb = body[v.end():end]
        pos = end
        cond = attribute_value(vb, "condition")
        if not cond or ("var.%s" % name) not in cond or attribute_value(vb, "error_message") is None:
            problems.append((vid(prefix, "validation-missing"), "a validation block does not test var.%s with an error_message" % name))
        else:
            conds.append(cond)
    if not conds:
        if not any(p[0] == vid(prefix, "validation-missing") for p in problems):
            problems.append((vid(prefix, "validation-missing"), "no validation block"))
        return problems
    base = _number(expected_default)
    if base is None:
        return problems

    def accepted(value):
        return all(bool(evaluate_cond(c, None, None, {"var.%s" % name: value})) for c in conds)

    try:
        if not accepted(base):
            problems.append((vid(prefix, "validation-rejects-default"), "validation rejects the default %s" % expected_default))
        for value, label in ((-1, "a negative value"), (base + 0.5, "a fractional value"), (INT32_PLUS_ONE, "a value beyond int32")):
            if accepted(value):
                problems.append((vid(prefix, "validation-lax"), "validation accepts %s (%s)" % (label, value)))
    except ValueError as e:
        problems.append((vid(prefix, "validation-lax"), "validation not evaluable: %s" % e))
    return problems


def runtime_module_body(root_texts):
    for text in root_texts.values():
        clean = hcl_text.strip_comments(text)
        m = re.search(r'^[ \t]*module[ \t]+"runtime"[ \t]*\{', clean, re.M)
        if m:
            return clean[m.end():hcl_text.matching_brace(clean, m.end() - 1)]
    return None


def root_variable_name(root_texts, modvar):
    """Name X when the root runtime module call has `<modvar> = var.X`, else None."""
    body = runtime_module_body(root_texts)
    passed = attribute_value(body, modvar) if body is not None else None
    m = re.fullmatch(r"var\.([A-Za-z_][A-Za-z0-9_]*)", passed or "")
    return m.group(1) if m else None


def check_root(root_texts, modvar, example_text):
    """The root passes the module grace variable as a plain var reference; that root variable is validated with default 300;
    the example tfvars documents it as a commented line."""
    body = runtime_module_body(root_texts)
    if body is None:
        return [(ROOT_NOT_PASSED, 'no module "runtime" call in the root')]
    passed = attribute_value(body, modvar)
    if passed is None:
        return [(ROOT_NOT_PASSED, "the root module call does not set %s" % modvar)]
    ref = re.fullmatch(r"var\.([A-Za-z_][A-Za-z0-9_]*)", passed)
    if not ref:
        return [(ROOT_LITERAL, "the root passes %s = %s (not a plain var reference)" % (modvar, passed))]
    name = ref.group(1)
    problems = check_variable(variable_block_in(root_texts, name), name, GRACE_DEFAULT, "root-grace")
    commented = re.search(r"^[ \t]*#+[ \t]*%s[ \t]*=[ \t]*%s[ \t]*$" % (re.escape(name), GRACE_DEFAULT), example_text, re.M)
    active = re.search(r"^[ \t]*%s[ \t]*=" % re.escape(name), example_text, re.M)
    if active:
        problems.append((EXAMPLE_ACTIVE, "environments example sets %s without a comment" % name))
    elif not commented:
        problems.append((EXAMPLE_MISSING, "environments example has no commented `# %s = %s` line" % (name, GRACE_DEFAULT)))
    return problems


def check_root_https(root_texts):
    """Replan W5b: the root runtime module call passes `https_enabled` as a PLAN-TIME boolean. By the user's decisions it is true
    exactly when an external certificate ARN is supplied, or when the managed ACM certificate will be validated in the same apply
    (api_domain_name set AND the runtime deployed: runtime_enabled with an image_revision). The expression is evaluated over the
    whole grid of those four inputs after resolving `local.*`; it must never read a resource attribute (unknown at plan time)."""
    body = runtime_module_body(root_texts)
    if body is None:
        return [(ROOT_HTTPS_ABSENT, 'no module "runtime" call in the root')]
    passed = attribute_value(body, "https_enabled")
    if passed is None:
        return [(ROOT_HTTPS_ABSENT, "the root module call does not set https_enabled")]
    expr = resolve_locals(passed, locals_of(root_texts))
    if re.search(r"\baws_[a-z0-9_]+\.", expr):
        return [(ROOT_HTTPS_WRONG, "https_enabled depends on a resource attribute (unknown at plan time): %s" % passed)]
    problems = []
    for cert in (None, CERT):
        for domain in (None, "api.example.invalid"):
            for runtime in (False, True):
                for image in (None, "rev1"):
                    scope = {"var.https_certificate_arn": cert, "var.api_domain_name": domain, "var.runtime_enabled": runtime,
                             "var.image_revision": image}
                    expected = cert is not None or (domain is not None and runtime and image is not None)
                    try:
                        got = evaluate_cond(expr, None, None, scope)
                    except ValueError as e:
                        return problems + [(ROOT_HTTPS_WRONG, "not evaluable: %s (%s)" % (e, passed))]
                    if got is not expected:
                        problems.append((ROOT_HTTPS_WRONG, "certificate=%s domain=%s runtime_enabled=%s image=%s: https_enabled=%r, expected %r"
                                         % (cert is not None, domain is not None, runtime, image is not None, got, expected)))
    return problems[:4]


def check_target_group(compute_text, variables_text, module_texts):
    """Path, matcher, explicit timing attributes as variable references, their variables, and the timeout < interval guard.

    Returns (problems, {attr: variable name})."""
    body = block(compute_text, "aws_lb_target_group", "query")
    if body is None:
        return [(TG_MISSING, "resource aws_lb_target_group.query not found")], {}
    hc = sub_block(body, r"\bhealth_check")
    if hc is None:
        return [(TG_PATH, "no health_check block")], {}
    problems, names = [], {}
    path = attribute_value(hc, "path")
    if path != '"/readyz"':
        problems.append((TG_PATH, "path is %s" % path))
    matcher = attribute_value(hc, "matcher")
    if matcher != '"200"':
        problems.append((TG_MATCHER, "matcher is %s" % matcher))
    for attr, default in TG_ATTRS.items():
        value = attribute_value(top_level(hc), attr)
        if value is None:
            problems.append((tg_absent(attr), "health_check does not set %s explicitly" % attr))
            continue
        m = re.fullmatch(r"var\.([A-Za-z_][A-Za-z0-9_]*)", value)
        if not m:
            problems.append((tg_literal(attr), "%s = %s is not a plain var reference" % (attr, value)))
            continue
        names[attr] = m.group(1)
        problems += check_variable(variable_block(variables_text, m.group(1)), m.group(1), default, TG_PREFIX[attr])
    if "timeout" in names and "interval" in names:
        problems += check_timeout_guard(body, names, module_texts)
    return problems, names


def _env(**values):
    return {"var.%s" % k: v for k, v in values.items()}


def check_timeout_guard(tg_body, names, module_texts):
    """A precondition on the target group that holds exactly when timeout < interval."""
    pres = preconditions(tg_body)
    if not pres:
        return [(TG_GUARD_MISSING, "aws_lb_target_group.query has no lifecycle precondition")]
    known = locals_of(module_texts)
    grid = [(5, 30, True), (29, 30, True), (30, 30, False), (31, 30, False), (5, 5, False), (4, 5, True), (2, 3, True), (3, 3, False)]
    last = []
    for cond, msg in pres:
        wrong = []
        if not cond or not msg:
            wrong.append("no condition or error_message")
        else:
            expr = resolve_locals(cond, known)
            for timeout, interval, expect in grid:
                env = _env(**{names["timeout"]: timeout, names["interval"]: interval})
                try:
                    got = bool(evaluate_cond(expr, None, None, env))
                except ValueError as e:
                    wrong.append("not evaluable: %s" % e)
                    break
                if got != expect:
                    wrong.append("timeout=%s interval=%s: precondition %s, expected %s" % (timeout, interval, got, expect))
        if not wrong:
            return []
        last = wrong
    return [(TG_GUARD_WRONG, "; ".join(last[:3]))]


def check_grace_guard(compute_text, module_texts, grace_var, names):
    """A precondition on aws_ecs_service.service: refuse a load-balanced grace below healthy_threshold x interval, and never
    block a service without a grace (graph-service, semantic-service, embedding-worker, or any service without a certificate)."""
    body = block(compute_text, "aws_ecs_service", "service")
    if body is None:
        return [(NO_SERVICE, "resource aws_ecs_service.service not found")]
    if "healthy_threshold" not in names or "interval" not in names:
        return [(GUARD_WRONG, "the target-group threshold or interval variable is unknown, so the guard cannot be evaluated")]
    pres = preconditions(body)
    if not pres:
        return [(GUARD_MISSING, "aws_ecs_service.service has no lifecycle precondition")]
    known = locals_of(module_texts)
    grid = [(300, 3, 30, True), (90, 3, 30, True), (89, 3, 30, False), (30, 3, 30, False), (0, 3, 30, False),
            (299, 10, 30, False), (300, 10, 30, True), (899, 3, 300, False), (900, 3, 300, True), (100, 2, 5, True),
            (9, 2, 5, False), (10, 2, 5, True)]
    last = []
    for cond, msg in pres:
        wrong = []
        if not cond or not msg:
            wrong.append("no condition or error_message")
        else:
            expr = resolve_locals(cond, known)
            for key in SERVICES:
                for cert, https in SCENARIOS:
                    for grace, healthy, interval, ok in grid:
                        expect = ok if expected_active(key, cert, https) else True
                        scope = _env(**{grace_var: grace, names["healthy_threshold"]: healthy, names["interval"]: interval})
                        scope.update(scenario_env(https))
                        try:
                            got = bool(evaluate_cond(expr, key, cert, scope))
                        except ValueError as e:
                            wrong.append("not evaluable: %s" % e)
                            break
                        if got != expect:
                            wrong.append("%s certificate=%s https_enabled=%s grace=%s healthy=%s interval=%s: precondition %s, expected %s"
                                         % (key, cert is not None, https, grace, healthy, interval, got, expect))
                    if wrong and wrong[-1].startswith("not evaluable"):
                        break
                if wrong and wrong[-1].startswith("not evaluable"):
                    break
        if not wrong:
            return []
        last = wrong
    return [(GUARD_WRONG, "; ".join(last[:3]))]


def check_circuit_breaker(compute_text):
    body = block(compute_text, "aws_ecs_service", "service")
    cb = sub_block(body or "", r"\bdeployment_circuit_breaker")
    if cb is None:
        return [(BREAKER, "no deployment_circuit_breaker block")]
    if attribute_value(cb, "enable") == "true" and attribute_value(cb, "rollback") == "true":
        return []
    return [(BREAKER, "enable=%s rollback=%s" % (attribute_value(cb, "enable"), attribute_value(cb, "rollback")))]


def defaults_of(variables_text, names, grace_var):
    """{role: int default} for grace, interval, healthy_threshold, unhealthy_threshold (None when unreadable)."""
    out = {}
    for role, var in (("grace", grace_var), ("interval", names.get("interval")), ("healthy", names.get("healthy_threshold")),
                      ("unhealthy", names.get("unhealthy_threshold"))):
        body = variable_block(variables_text, var) if var else None
        out[role] = _number(attribute_value(top_level(body), "default")) if body else None
    return out


def check_arithmetic(variables_text, names, grace_var):
    """From the module defaults: unhealthy after unhealthy x interval, recovery needs healthy x interval, the default grace
    covers recovery and leaves at least 200 s for peer readiness. With 3 / 30 / 3 / 300: 90 s, 90 s, 300 >= 90, 210 >= 200."""
    d = defaults_of(variables_text, names, grace_var)
    if any(v is None for v in d.values()):
        return [(ARITHMETIC, "a default is unreadable: %s" % d)]
    unhealthy_after, recovery = d["unhealthy"] * d["interval"], d["healthy"] * d["interval"]
    problems = []
    if (unhealthy_after, recovery) != (90, 90):
        problems.append((ARITHMETIC, "unhealthy after %s s and recovery %s s, expected 90 and 90" % (unhealthy_after, recovery)))
    if d["grace"] < recovery:
        problems.append((ARITHMETIC, "default grace %s s is below the %s s recovery time" % (d["grace"], recovery)))
    if d["grace"] - recovery < 200:
        problems.append((ARITHMETIC, "default grace %s s leaves %s s (< 200 s) for peer readiness" % (d["grace"], d["grace"] - recovery)))
    return problems


def discover(compute_text, variables_text, module_texts, root_texts):
    """{"grace": module variable, "root": root variable, "tg": {attr: variable}} as the sources currently name them."""
    _, grace = check_grace_in_service(compute_text, module_texts)
    _, tg = check_target_group(compute_text, variables_text, module_texts)
    return {"grace": grace, "root": root_variable_name(root_texts, grace) if grace else None, "tg": tg}


def check_all(compute_text, variables_text, module_texts, root_texts, example_text):
    """Every check; `module_texts` must contain compute_text under some name so local resolution sees it."""
    problems, grace_var = check_grace_in_service(compute_text, module_texts)
    tg_problems, names = check_target_group(compute_text, variables_text, module_texts)
    problems += tg_problems
    if grace_var is not None:
        problems += check_variable(variable_block(variables_text, grace_var), grace_var, GRACE_DEFAULT, "grace")
        problems += check_root(root_texts, grace_var, example_text)
        problems += check_grace_guard(compute_text, module_texts, grace_var, names)
        problems += check_arithmetic(variables_text, names, grace_var)
    problems += check_circuit_breaker(compute_text)
    problems += check_root_https(root_texts)
    seen, unique = set(), []
    for p in problems:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique
