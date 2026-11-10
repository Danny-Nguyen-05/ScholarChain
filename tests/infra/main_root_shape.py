"""Support for the Phase 14B replan W5b/W4 tests (test-engineer, tests/infra/**): the MAIN root planned offline (real provider, fake
credentials, closed proxy; infra_support.ROOTS["main14"]) with the variable sets of a base stage and a runtime stage.

All identifiers are synthetic (account 111122223333, example.invalid names). Nothing is applied and no AWS call is made.
"""
import json

from infra_support import TF_BIN, TfTree, run, tf_env

ACCT = "111122223333"
REGION = "us-east-2"
DOMAIN = "api.example.invalid"
SERVICES = ("query-api", "graph-service", "semantic-service", "embedding-worker")
IMAGE = "a" * 40


def _secret(name):
    return "arn:aws:secretsmanager:%s:%s:secret:synthetic-%s-AbCdEf" % (REGION, ACCT, name)


def bindings():
    keys = {
        "query-api": ("SCHOLARCHAIN_API_KEY_SHA256", "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256", "SCHOLARCHAIN_INTERNAL_TOKEN"),
        "graph-service": ("SCHOLARCHAIN_GRAPH_CURSOR_KEY", "SCHOLARCHAIN_API_KEY_SHA256", "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256"),
        "semantic-service": ("SCHOLARCHAIN_API_KEY_SHA256", "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256"),
        "embedding-worker": ("SCHOLARCHAIN_API_KEY_SHA256", "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256"),
    }
    return {s: {k: _secret(s + "-" + k.lower()) for k in ks} for s, ks in keys.items()}


# Variables of a runtime-deployed plan. Values given as Python objects are passed as JSON (HCL-compatible) text.
RUNTIME_VARS = {
    "runtime_enabled": True,
    "runtime_composition_verified": True,
    "embedding_model_version": "synthetic-pinned-version",
    "synthesis_model_id": "anthropic.claude-synthetic-test-v1:0",
    "image_revision": IMAGE,
    "neptune_enabled": True,
    "neptune_engine_version": "1.4.6.3",
    "neptune_parameter_family": "neptune1.4",
    "service_secret_bindings": bindings(),
    "public_ingress_cidrs": ["192.0.2.0/24"],
}


class MainPlans:
    """A scratch copy of the main root that can be planned several times with different variables (plans are cached per variable set)."""

    def __init__(self):
        self.tree = TfTree("main14")
        self.cache = {}

    def close(self):
        self.tree.close()

    def plan(self, **variables):
        """Parsed `terraform show -json` of an offline plan with these extra variables (None removes a default-set variable)."""
        key = json.dumps(variables, sort_keys=True, default=str)
        if key not in self.cache:
            self.cache[key] = self._plan(variables)
        return self.cache[key]

    def attempt(self, **variables):
        """The CompletedProcess of an offline plan (used to prove that a value is REFUSED); never cached."""
        self.tree.init()
        return self.tree.tf("plan", "-no-color", "-input=false", *self._args(variables))

    def _args(self, variables):
        merged = dict(self.tree.spec["vars"])
        merged.update(variables)
        args = []
        for k, v in merged.items():
            if v is None:
                continue
            text = v if isinstance(v, str) else json.dumps(v)
            args += ["-var", "%s=%s" % (k, text)]
        return args

    def _plan(self, variables):
        self.tree.init()
        out = self.tree.base / "shape.tfplan"
        done = self.tree.tf("plan", "-no-color", "-input=false", "-out=" + str(out), *self._args(variables))
        if done.returncode != 0:
            raise AssertionError("offline plan failed for %s:\n%s" % (sorted(variables), (done.stdout + done.stderr)[-2500:]))
        shown = self.tree.tf("show", "-json", "-no-color", str(out))
        if shown.returncode != 0:
            raise AssertionError("terraform show -json failed:\n" + shown.stderr[-1500:])
        return json.loads(shown.stdout)


def resources(plan, rtype=None):
    """address -> resource_change for managed resources (optionally of one type)."""
    return {rc["address"]: rc for rc in plan.get("resource_changes", []) if rc.get("mode") == "managed" and (rtype is None or rc["type"] == rtype)}


def after(plan, address):
    return resources(plan)[address]["change"]["after"]


def unknown(plan, address):
    return resources(plan)[address]["change"].get("after_unknown", {})


def output_names(plan):
    return set(plan["configuration"]["root_module"].get("outputs", {}))
