#!/usr/bin/env python3
"""Bounded initial budget execution. Authoring does not authorize live use.

CLI paths and pins are immutable. Tests inject a separate Policy in Python only;
there is no CLI environment/path/identity override or test mode.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

ACCOUNT = "530332961125"
PROFILE = "scholarchain-billing-deployer"
REGION = "us-east-2"
BUDGET = "scholarchain-project-budget"
ARN = f"arn:aws:budgets::{ACCOUNT}:budget/{BUDGET}"
CALLER = f"arn:aws:sts::{ACCOUNT}:assumed-role/{PROFILE}/scholarchain-billing-operator"
PRIMARY = Path("/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap")
BACKUPS = PRIMARY.with_name("billing-bootstrap-backups")
REPO = Path("/Users/danny/Documents/UIC/CS441/ScholarChain")
PROPOSAL = "docs/agent-runs/phase-12/evidence/12d-billing-apply-proposal/proposal.md"
HUMAN_RECORD = "docs/agent-runs/phase-12/billing-bootstrap-exception.md"
ACTIONS = {"p3-check", "apply", "backup", "readback", "post-freeze-scan", "preserve-partial"}
COST_TYPES = {"IncludeCredit": False, "IncludeRefund": False,
              "IncludeDiscount": True, "IncludeOtherSubscription": True,
              "IncludeRecurring": True, "IncludeSubscription": True,
              "IncludeSupport": True, "IncludeTax": True, "IncludeUpfront": True,
              "UseAmortized": False, "UseBlended": False}
TAGS = {"course": "CS441", "project": "scholarchain", "environment": "course",
        "owner": "danny", "expiration_date": "2027-01-01"}
MAX_BYTES = 8 * 1024 * 1024
READ_TIMEOUT_SECONDS = 60
APPLY_TIMEOUT_SECONDS = 300
APPLY_GRACE_SECONDS = 60
FORCED_REAP_SECONDS = 5
LOCAL_PRESERVATION_HEADROOM_SECONDS = 15


class Blocked(Exception):
    """Only fixed, non-sensitive codes may cross the public boundary."""


def require(condition, code):
    if not condition:
        raise Blocked(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def parse_json(data):
    try:
        return json.loads(data, object_pairs_hook=unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, TypeError):
        raise Blocked("INVALID_JSON") from None


def stamp():
    return datetime.now(timezone.utc)


def iso(moment):
    return moment.isoformat()


def date(value):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(dt.utcoffset() is not None, "TIMEZONE_REQUIRED")
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise Blocked("INVALID_TIME") from None


def secure_dir(path, uid):
    """Check every ancestor for symlinks; require leaf private and owned."""
    path = Path(path)
    for node in [path, *path.parents]:
        st = node.lstat()
        require(not stat.S_ISLNK(st.st_mode), "SYMLINK_DIRECTORY")
    st = path.lstat()
    require(stat.S_ISDIR(st.st_mode) and st.st_uid == uid
            and stat.S_IMODE(st.st_mode) == 0o700, "DIRECTORY_MODE_OWNER")


def file_meta(path, uid, mode=0o600):
    path = Path(path)
    secure_dir(path.parent, uid)
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and st.st_uid == uid
            and stat.S_IMODE(st.st_mode) == mode, "FILE_TYPE_MODE_OWNER")
    return st


def identity(st):
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def read_nofollow(path, limit=MAX_BYTES):
    """Bounded opaque byte read; never used for credentials or semantic state."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= limit,
                "FILE_TYPE_OR_SIZE")
        chunks = []
        while True:
            chunk = os.read(fd, min(65536, limit + 1 - sum(map(len, chunks))))
            if not chunk:
                break
            chunks.append(chunk)
            require(sum(map(len, chunks)) <= limit, "FILE_SIZE_LIMIT")
        require(identity(before) == identity(os.fstat(fd)), "FILE_CHANGED")
        require(identity(before) == identity(Path(path).lstat()), "FILE_REPLACED")
        return b"".join(chunks)
    finally:
        os.close(fd)


def hash_file(path):
    # Large provider binaries are streamed; no byte contents returned.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), "HASH_NOT_REGULAR")
        result = hashlib.sha256()
        while chunk := os.read(fd, 1024 * 1024):
            result.update(chunk)
        require(identity(before) == identity(os.fstat(fd))
                == identity(Path(path).lstat()), "FILE_CHANGED")
        return result.hexdigest()
    finally:
        os.close(fd)


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def create_file(path):
    return os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)


def save_json(path, value):
    fd = create_file(path)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode())
            out.flush()
            os.fsync(out.fileno())
        sync_dir(Path(path).parent)
    except BaseException:
        # Never delete partial evidence; exclusive names prohibit retry overwrite.
        raise


def opaque_copy(source, target, uid):
    """No parsing or content output. Exclusive copy plus two source hash checks."""
    secure_dir(Path(target).parent, uid)
    before = file_meta(source, uid)
    require(before.st_size > 0, "EMPTY_STATE")
    source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        require(identity(before) == identity(os.fstat(source_fd)), "COPY_SOURCE_RACE")
        output_fd = create_file(target)
        sha = hashlib.sha256()
        with os.fdopen(output_fd, "wb") as out:
            while chunk := os.read(source_fd, 65536):
                sha.update(chunk)
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        sync_dir(Path(target).parent)
        require(identity(before) == identity(os.fstat(source_fd))
                == identity(Path(source).lstat()), "COPY_SOURCE_CHANGED")
        expected = sha.hexdigest()
        require(hash_file(source) == expected == hash_file(target), "COPY_HASH_MISMATCH")
        require(identity(before) == identity(Path(source).lstat()), "COPY_SOURCE_CHANGED")
        file_meta(target, uid)
        return {"sha256": expected, "bytes": before.st_size, "equal": True,
                "fsync_completed": True}
    finally:
        os.close(source_fd)


@dataclass(frozen=True)
class Policy:
    primary: Path
    backups: Path
    repo: Path
    uid: int
    aws: Path
    pins: dict

    @property
    def config(self):
        return self.primary / "config"

    @property
    def terraform(self):
        return self.primary / "toolchain/terraform-1.13.5"

    @property
    def state(self):
        return self.primary / "billing.execution.tfstate"

    @property
    def plan(self):
        return self.primary / "billing.execution.tfplan"

    def env(self):
        # No inherited credentials, endpoint overrides, TF flags or developer settings.
        # One SDK attempt also prevents CLI retry loops; wrapper never retries commands.
        return {"HOME": "/Users/danny", "PATH": "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
                "TF_CLI_CONFIG_FILE": str(self.primary / "toolchain/terraform.tfrc"),
                "TF_DATA_DIR": str(self.primary / "tf-data"), "TF_IN_AUTOMATION": "1",
                "AWS_EC2_METADATA_DISABLED": "true", "AWS_PAGER": "",
                "AWS_PROFILE": PROFILE, "AWS_REGION": REGION, "AWS_DEFAULT_REGION": REGION,
                "AWS_SDK_LOAD_CONFIG": "1", "AWS_MAX_ATTEMPTS": "1"}

    def apply_argv(self):
        return [str(self.terraform), "apply", "-input=false", "-no-color", "-lock-timeout=30s",
                f"-state={self.state}", str(self.plan)]

    def aws_argv(self, operation, extra=()):
        return [str(self.aws), "budgets", operation, *extra,
                "--profile", PROFILE, "--region", REGION, "--output", "json", "--no-cli-pager"]


def production_policy():
    require(Path(__file__).resolve() == REPO / "scripts/billing/budget_execution.py",
            "WRAPPER_LOCATION")
    pins = parse_json((Path(__file__).with_name("reviewed-pins.json")).read_bytes())
    return Policy(PRIMARY, BACKUPS, REPO, 501, Path("/opt/homebrew/bin/aws"), pins)


def stop_apply(process):
    """One SIGINT to Terraform, bounded graceful wait, forced group kill last.

    SIGINT targets Terraform only, so its providers can finish through Terraform's
    graceful stop/persist path. Repeated user interrupts do not send a second
    Terraform SIGINT. A forced kill is an explicit uncertain-state incident.
    """
    receipt = {"sigint_sent": False, "grace_seconds": APPLY_GRACE_SECONDS,
               "graceful_exit": False, "forced_kill": False, "final_exit": None}
    code = process.poll()
    if code is not None:
        receipt.update(graceful_exit=True, final_exit=code)
        return receipt
    try:
        process.send_signal(signal.SIGINT)
        receipt["sigint_sent"] = True
    except ProcessLookupError:
        receipt["final_exit"] = process.poll()
        receipt["graceful_exit"] = receipt["final_exit"] is not None
        return receipt
    deadline = time.monotonic() + APPLY_GRACE_SECONDS
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            receipt.update(graceful_exit=True, final_exit=process.wait(timeout=remaining))
            return receipt
        except KeyboardInterrupt:
            # Keep the same deadline; a second keypress must not bypass persistence.
            continue
        except subprocess.TimeoutExpired:
            break
    code = process.poll()
    if code is None:
        receipt["forced_kill"] = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            code = process.wait(timeout=FORCED_REAP_SECONDS)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            # Unknown final state stays explicit; originals and logs are retained.
            code = process.poll()
    receipt["final_exit"] = code
    return receipt


class PrivateRunner:
    def __call__(self, argv, cwd, env, logs, label, timeout):
        outpath, errpath = logs / f"{label}.stdout", logs / f"{label}.stderr"
        outfd, errfd = create_file(outpath), create_file(errpath)
        is_apply = Path(argv[0]).name.startswith("terraform") and len(argv) > 1 and argv[1] == "apply"
        failure = None
        with os.fdopen(outfd, "wb") as out, os.fdopen(errfd, "wb") as err:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=True)
            try:
                code = process.wait(timeout=timeout)
            except BaseException as interruption:
                if is_apply:
                    termination = stop_apply(process)
                    save_json(logs / f"{label}.termination.json", termination)
                elif process.poll() is None:
                    # These are read-only AWS/offline capability child groups.
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=FORCED_REAP_SECONDS)
                failure = ("COMMAND_TIMEOUT_PARTIAL_POSSIBLE"
                           if isinstance(interruption, subprocess.TimeoutExpired)
                           else "COMMAND_INTERRUPTED_PARTIAL_POSSIBLE")
            finally:
                out.flush(); err.flush()
                os.fsync(out.fileno()); os.fsync(err.fileno())
        sync_dir(logs)
        if failure is not None:
            raise Blocked(failure)
        # Only bounded, private AWS responses are parsed. Terraform output stays opaque.
        if Path(argv[0]).name.startswith("terraform"):
            return code, b"", b""
        return code, read_nofollow(outpath), read_nofollow(errpath)


def absence(code, stdout, stderr):
    require(stdout.strip() == b"", "P3_UNEXPECTED_STDOUT")
    require(code == 254, "P3_NOT_SERVICE_ERROR")
    # Full-match a single AWS CLI service error, never HTTP status or substring matching.
    require(re.fullmatch(rb"\s*An error occurred \(NotFoundException\) when calling the DescribeBudget operation: [^\r\n]+\s*", stderr)
            is not None, "P3_NOT_EXACT_NOT_FOUND")
    require(not re.search(rb"AccessDenied|Expired|Throttl|SSL|TLS|connect|credential", stderr, re.I),
            "P3_MIXED_ERROR")


def expected_notification(threshold):
    return {"NotificationType": "ACTUAL", "ComparisonOperator": "GREATER_THAN",
            "Threshold": threshold, "ThresholdType": "PERCENTAGE"}


def utc_value(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value, timezone.utc)
    return date(value)


def sanitize_readback(budget, tags, notifications, subscriber_responses, recipient):
    """Return booleans/counts only, or a fixed error code; never echo input fields."""
    require(set(budget) == {"Budget"}, "BUDGET_RESPONSE_SHAPE")
    b = budget["Budget"]
    require(b.get("BudgetName") == BUDGET and b.get("BudgetType") == "COST"
            and b.get("TimeUnit") == "CUSTOM", "BUDGET_IDENTITY_TYPE")
    try:
        require(Decimal(b["BudgetLimit"]["Amount"]) == Decimal(200)
                and b["BudgetLimit"]["Unit"] == "USD", "BUDGET_AMOUNT")
    except (KeyError, InvalidOperation, TypeError):
        raise Blocked("BUDGET_AMOUNT") from None
    require(b.get("CostTypes") == COST_TYPES
            and all(type(v) is bool for v in b.get("CostTypes", {}).values()), "COST_TYPES")
    require(b.get("CostFilters", {}) == {} and b.get("FilterExpression", {}) == {}, "FILTER_PRESENT")
    # Explicit ShowFilterExpression request is mandatory; absent means no expression per API.
    require(utc_value(b.get("TimePeriod", {}).get("Start")) == date("2026-10-01T00:00:00Z")
            and utc_value(b.get("TimePeriod", {}).get("End")) == date("2027-01-01T00:00:00Z"),
            "BUDGET_DATE")
    require(set(tags) == {"ResourceTags"} and type(tags["ResourceTags"]) is list,
            "TAGS_RESPONSE_SHAPE")
    pairs = tags["ResourceTags"]
    require(len(pairs) == 5 and all(set(x) == {"Key", "Value"} for x in pairs)
            and {x["Key"]: x["Value"] for x in pairs} == TAGS, "TAGS_DRIFT")
    require(not notifications.get("NextToken") and set(notifications) <= {"Notifications", "NextToken"},
            "NOTIFICATIONS_PAGINATION_SHAPE")
    values = notifications.get("Notifications")
    require(type(values) is list and len(values) == 3, "NOTIFICATION_COUNT")
    seen = set()
    health = b.get("HealthStatus")
    # An unknown health result blocks completion; never publish raw service text.
    if health is not None:
        require(type(health) is dict and health.get("Status") == "HEALTHY", "BUDGET_HEALTH_UNVERIFIED")
    for n in values:
        require(set(n) <= {"NotificationType", "ComparisonOperator", "Threshold", "ThresholdType", "NotificationState"},
                "NOTIFICATION_SHAPE")
        t = n.get("Threshold")
        require(type(t) in (int, float) and t in (50, 80, 100) and t not in seen,
                "NOTIFICATION_THRESHOLD")
        require(all(n.get(k) == v for k, v in expected_notification(t).items()), "NOTIFICATION_DRIFT")
        seen.add(t)
        r = subscriber_responses[t]
        require(not r.get("NextToken") and set(r) <= {"Subscribers", "NextToken"}, "SUBSCRIBER_PAGINATION_SHAPE")
        subs = r.get("Subscribers")
        require(type(subs) is list and len(subs) == 1 and set(subs[0]) == {"SubscriptionType", "Address"}
                and subs[0]["SubscriptionType"] == "EMAIL" and subs[0]["Address"] == recipient,
                "SUBSCRIBER_DRIFT")
    return {"budget_fields_match": True, "cost_types_match": True, "tags_match": True,
            "dates_match": True, "account_request_matches": True, "filters_absent": True,
            "notification_count": 3, "email_subscribers_each": 1, "sns_subscribers": 0,
            "private_recipients_match": True, "health_reported": health is not None,
            "health_healthy_if_reported": health is not None,
            "delivery_verified": False, "phase12d_complete": False}


class Execution:
    def __init__(self, policy, runner=None, now=stamp):
        self.p = policy
        self.runner = runner or PrivateRunner()
        self.now = now
        self.gate = None
        self.op = None
        self.binding = None

    def load_gate(self, gate_path, gate_sha, operation):
        require(re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", operation) is not None, "OPERATION_ID")
        raw = read_nofollow(gate_path)
        require(digest(raw) == gate_sha, "GATE_HASH")
        g = parse_json(raw)
        required = {"operation", "plan_sha256", "proposal_sha256", "wrapper_files", "source_commit",
                    "human_record_sha256", "g1_affirmation", "actor_arn", "account", "profile", "region",
                    "window_start", "window_end", "timezone", "login_at", "human_sts_observed_at",
                    "human_sts", "permissions", "retention_accepted", "aws_cli_sha256",
                    "wrapper_review_approved", "ownership_reconciled", "public_packet_root"}
        require(set(g) == required, "GATE_SCHEMA")
        require(g["operation"] == operation and g["plan_sha256"] == self.p.pins["plan_sha256"]
                and g["proposal_sha256"] == self.p.pins["proposal_sha256"], "GATE_PLAN_BINDING")
        require(g["human_record_sha256"] == self.p.pins["human_record_sha256"]
                and type(g["g1_affirmation"]) is str and len(g["g1_affirmation"].strip()) >= 10,
                "G1_REQUIRED")
        require(g["actor_arn"] == CALLER and g["account"] == ACCOUNT and g["profile"] == PROFILE
                and g["region"] == REGION and g["human_sts"] == {"Account": ACCOUNT, "Arn": CALLER},
                "HUMAN_IDENTITY")
        require(set(g["permissions"]) == ACTIONS and g["retention_accepted"] is True
                and g["wrapper_review_approved"] is True and g["ownership_reconciled"] is True,
                "HUMAN_GATE_REQUIRED")
        require(g["timezone"] == "America/Chicago", "WINDOW_TIMEZONE")
        start, end, login, observed = map(date, (g["window_start"], g["window_end"], g["login_at"], g["human_sts_observed_at"]))
        now = self.now()
        require(start <= login <= observed <= now < end and (end-start).total_seconds() <= 3600
                and (now-login).total_seconds() < 3600, "SESSION_WINDOW")
        require(re.fullmatch(r"[0-9a-f]{40}", g["source_commit"]) is not None
                and re.fullmatch(r"[0-9a-f]{64}", g["aws_cli_sha256"]) is not None, "GATE_HASH_SCHEMA")
        packet_root = Path(g["public_packet_root"])
        require(not packet_root.is_absolute() and ".." not in packet_root.parts
                and str(packet_root).startswith("docs/agent-runs/phase-12/evidence/"), "GATE_PACKET_SCOPE")
        self.gate = g
        self.binding = {"gate_sha256": gate_sha, "operation": operation,
                        "plan_sha256": self.p.pins["plan_sha256"], "actor_arn": CALLER}
        self.op = self.p.primary / "operations" / operation
        return self

    def check_window(self):
        require(self.gate is not None and self.now() < date(self.gate["window_end"])
                and self.now() >= date(self.gate["human_sts_observed_at"]), "WINDOW_EXPIRED")

    def check_checkout(self, allow_packet=False, external_freeze=None):
        # Git output is public commit/status metadata, never credential/config data.
        env = {"PATH": "/usr/bin:/bin", "HOME": "/Users/danny"}
        def git(*args):
            result = subprocess.run(["/usr/bin/git", "-C", str(self.p.repo), *args], env=env,
                                    capture_output=True, stdin=subprocess.DEVNULL, timeout=10)
            require(result.returncode == 0, "GIT_CHECK_FAILED")
            return result.stdout
        require(git("rev-parse", "HEAD").decode().strip() == self.gate["source_commit"], "SOURCE_COMMIT")
        dirty = git("status", "--porcelain=v1", "-z", "--untracked-files=all")
        if dirty:
            require(allow_packet, "DIRTY_CHECKOUT")
            # Only the separately named, new public packet may be dirty for the final scan.
            # All scripts/frozen infra, tracked sources and other paths still must be unchanged.
            root = Path(self.gate["public_packet_root"])
            external = None
            if external_freeze is not None:
                require(Path(external_freeze).resolve().is_relative_to(self.p.repo.resolve()), "FREEZE_LOCATION")
                external = Path(external_freeze).resolve().relative_to(self.p.repo.resolve())
            for entry in dirty.split(b"\0"):
                if not entry:
                    continue
                require(len(entry) > 3 and entry[:2] in (b"??", b" M", b"A ", b"AM"), "DIRTY_PACKET_STATUS")
                path = Path(entry[3:].decode("utf-8", errors="strict"))
                require(path.is_relative_to(root) or path == external, "DIRTY_OUTSIDE_PACKET")
        files = self.gate["wrapper_files"]
        expected = sorted(str(x.relative_to(self.p.repo)) for x in (self.p.repo / "scripts/billing").rglob("*")
                          if x.is_file())
        require(type(files) is dict and sorted(files) == expected and expected, "WRAPPER_FILE_SET")
        for rel, sha in files.items():
            require(not Path(rel).is_absolute() and ".." not in Path(rel).parts, "WRAPPER_PATH")
            git("ls-files", "--error-unmatch", "--", rel)
            require(hash_file(self.p.repo / rel) == sha, "WRAPPER_HASH")
        require(hash_file(self.p.repo / PROPOSAL) == self.p.pins["proposal_sha256"]
                and hash_file(self.p.repo / HUMAN_RECORD) == self.p.pins["human_record_sha256"],
                "PROPOSAL_HUMAN_RECORD_HASH")
        course = (self.p.repo / "infra/terraform/environments/course.tfvars").read_text()
        require(re.search(r"(?m)^\s*enable_budget_resource\s*=\s*false\s*(?:#.*)?$", course)
                is not None, "MAIN_BUDGET_ENABLED")
        for row in self.p.pins["source_freeze"]:
            f = self.p.repo / row["path"]
            require(f.lstat().st_size == row["bytes"] and hash_file(f) == row["sha256"], "SOURCE_DRIFT")

    def check_files(self):
        p = self.p
        secure_dir(p.primary, p.uid); secure_dir(p.backups, p.uid)
        # Check every durable directory and data path. Only provider install links may point into mirror.
        mirror = p.primary / "toolchain/provider-mirror"
        for root in (p.primary, p.backups):
            for node in root.rglob("*"):
                st = node.lstat()
                if stat.S_ISLNK(st.st_mode):
                    require("providers" in node.parts and node.resolve().is_relative_to(mirror)
                            and node.resolve().exists(), "UNAPPROVED_SYMLINK")
                elif stat.S_ISDIR(st.st_mode):
                    secure_dir(node, p.uid)
                else:
                    require(stat.S_ISREG(st.st_mode) and st.st_uid == p.uid
                            and stat.S_IMODE(st.st_mode) in (0o600, 0o700), "DURABLE_MODE_OWNER")
        checks = [(p.plan, p.pins["plan_sha256"], 0o600),
                  (p.terraform, p.pins["terraform_sha256"], 0o700),
                  (p.primary / "toolchain/terraform.tfrc", p.pins["cli_config_sha256"], 0o600),
                  (p.primary / "approved-public-inputs.tfvars.json", p.pins["public_input_sha256"], 0o600),
                  (mirror / "registry.terraform.io/hashicorp/aws/6.44.0/darwin_arm64/terraform-provider-aws_v6.44.0_x5",
                   p.pins["provider_sha256"], 0o700)]
        for f, sha, mode in checks:
            file_meta(f, p.uid, mode)
            require(hash_file(f) == sha, "ARTIFACT_HASH")
        require(p.plan.lstat().st_size == p.pins["plan_bytes"], "PLAN_SIZE")
        for row in p.pins["config"]:
            f = p.primary / row["copy_relative"]
            require(file_meta(f, p.uid).st_size == row["bytes"] and hash_file(f) == row["sha256"], "CONFIG_DRIFT")
        # AWS CLI may be a package-manager symlink; freeze its resolved executable via human gate.
        require(p.aws.resolve().is_file() and hash_file(p.aws.resolve()) == self.gate["aws_cli_sha256"],
                "AWS_CLI_HASH")

    def no_state(self):
        for root in (self.p.primary, self.p.backups):
            for f in root.rglob("*"):
                name = f.name
                require(not (name.endswith(".tfstate") or ".tfstate." in name or name == "terraform.tfstate.d"
                             or name.endswith(".lock.info")), "PREEXISTING_STATE_OR_LOCK")

    @contextmanager
    def lease(self, mode):
        # Reservation files are persistent stage journals; no second attempt after any failure.
        secure_dir(self.op, self.p.uid)
        global_lock = self.p.primary / ".billing-wrapper-active.lock"
        global_fd = create_file(global_lock)
        lock_identity = identity(os.fstat(global_fd))
        os.close(global_fd)
        try:
            fd = create_file(self.op / f"{mode}.started")
            os.close(fd)
            yield
        finally:
            # Delete only our ephemeral concurrency lock, never Terraform lock/state files.
            if identity(global_lock.lstat()) == lock_identity:
                global_lock.unlink()
                sync_dir(self.p.primary)

    def command(self, argv, label):
        self.check_window()
        remaining = (date(self.gate["window_end"])-self.now()).total_seconds()
        if argv == self.p.apply_argv():
            # Separate mutation allowance; reserve graceful-stop/reap and local-copy
            # headroom inside the approved window before starting any apply process.
            reserve = APPLY_GRACE_SECONDS + FORCED_REAP_SECONDS + LOCAL_PRESERVATION_HEADROOM_SECONDS
            timeout = min(APPLY_TIMEOUT_SECONDS, remaining - reserve)
            require(timeout > 0, "APPLY_WINDOW_HEADROOM_REQUIRED")
        else:
            timeout = min(READ_TIMEOUT_SECONDS, remaining)
            require(timeout > 0, "WINDOW_EXPIRED")
        return self.runner(argv, self.p.config, self.p.env(), self.op, label, timeout)

    def capability(self):
        code, out, err = self.command(self.p.aws_argv("describe-budget", ["--generate-cli-skeleton", "input"]), "capability")
        require(code == 0 and not err.strip(), "CLI_CAPABILITY_FAILED")
        require("ShowFilterExpression" in parse_json(out), "CLI_SHOW_FILTER_UNSUPPORTED")

    def receipt(self, stage, result):
        value = {**self.binding, "stage": stage, "observed_at": iso(self.now()), "result": result}
        save_json(self.op / f"{stage}.receipt.json", value)
        return value

    def prior(self, stage):
        f = self.op / f"{stage}.receipt.json"
        file_meta(f, self.p.uid)
        value = parse_json(read_nofollow(f))
        require(all(value.get(k) == v for k, v in self.binding.items()) and value.get("stage") == stage,
                "PRIOR_RECEIPT_BINDING")
        require(date(value["observed_at"]) <= self.now(), "PRIOR_RECEIPT_TIME")
        return value

    def p3_check(self):
        self.check_checkout(); self.check_files(); self.no_state(); self.check_window()
        parent = self.p.primary / "operations"
        if not parent.exists():
            parent.mkdir(mode=0o700)
        secure_dir(parent, self.p.uid)
        self.op.mkdir(mode=0o700)  # Existing operation is not retried/reused.
        with self.lease("p3-check"):
            self.capability()
            argv = self.p.aws_argv("describe-budget", ["--account-id", ACCOUNT, "--budget-name", BUDGET,
                                                       "--show-filter-expression"])
            code, out, err = self.command(argv, "p3-describe-budget")
            absence(code, out, err)
            return self.receipt("p3-check", {"exact_name_absent": True, "account": ACCOUNT,
                                              "budget_name": BUDGET, "exit": code,
                                              "service_error": "NotFoundException"})

    def preserve(self, backup):
        candidates = [self.p.state, self.p.state.with_name(self.p.state.name + ".backup"),
                      self.p.primary / ".billing.execution.tfstate.lock.info",
                      self.p.config / "errored.tfstate", self.p.config / "terraform.tfstate",
                      self.p.config / "terraform.tfstate.backup", self.p.config / ".terraform.tfstate.lock.info"]
        # Preserve every explicitly scoped state/recovery/lock artifact, with collision-free names.
        for root in (self.p.primary,):
            for f in root.rglob("*"):
                if f.name.endswith(".tfstate") or ".tfstate." in f.name or f.name.endswith(".lock.info"):
                    if f not in candidates:
                        candidates.append(f)
        result = []
        for idx, source in enumerate(candidates):
            if source.exists() or source.is_symlink():
                try:
                    info = opaque_copy(source, backup / f"recovery-{idx:03d}.opaque", self.p.uid)
                    # Relative source path is fixed scoped metadata, never file contents.
                    result.append({"source": str(source.relative_to(self.p.primary)), **info})
                except (OSError, Blocked):
                    result.append({"source": str(source.relative_to(self.p.primary)), "preserved": False})
        save_json(backup / "preservation.receipt.json", {"artifacts": result, "incident_required": True})

    def apply(self):
        self.check_checkout(); self.check_files(); self.no_state(); self.check_window()
        previous = self.prior("p3-check")
        require(previous["result"].get("exact_name_absent") is True
                and (self.now()-date(previous["observed_at"])).total_seconds() <= 120, "STALE_P3")
        backup = self.p.backups / "initial-ab9f141e83058209"
        with self.lease("apply"):
            backup.mkdir(mode=0o700)  # Never overwrite or reuse a reserved operation directory.
            try:
                code, _, _ = self.command(self.p.apply_argv(), "apply")
                require(code == 0, "APPLY_FAILED_PARTIAL_POSSIBLE")
                # Local preservation is unconditional after process exit, even if the
                # human window ended while Terraform was finishing/persisting state.
                # Ensure there is exactly the expected resource-state path and no recovery/locks.
                found = [x for x in self.p.primary.rglob("*")
                         if x.name.endswith(".tfstate") or ".tfstate." in x.name or x.name.endswith(".lock.info")]
                require(found == [self.p.state], "UNEXPECTED_POST_APPLY_STATE")
                info = opaque_copy(self.p.state, backup / "billing.execution.tfstate", self.p.uid)
                save_json(backup / "backup.receipt.json", {**self.binding, **info})
            except BaseException:
                # After a failed or interrupted apply no further AWS calls are permitted.
                try:
                    self.preserve(backup)
                except BaseException:
                    pass  # Original error + fixed public incident message; originals never deleted.
                raise Blocked("APPLY_OR_BACKUP_FAILED_INCIDENT_REQUIRED") from None
            window_open = self.now() < date(self.gate["window_end"])
            result = self.receipt("apply", {"exit": 0, "backup": info, "backup_verified": True,
                                            "window_open_for_further_live": window_open})
            require(window_open, "WINDOW_EXPIRED_AFTER_BACKUP_NO_FURTHER_LIVE")
            return result

    def private_recipient(self):
        f = self.p.primary / "notification.private.tfvars.json"
        file_meta(f, self.p.uid)
        value = parse_json(read_nofollow(f))
        require(set(value) == {"budget_notification_emails"}, "PRIVATE_INPUT_SHAPE")
        values = value["budget_notification_emails"]
        require(type(values) is list and len(values) == 1 and type(values[0]) is str
                and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", values[0]) is not None,
                "PRIVATE_INPUT_SHAPE")
        return values[0]

    def query(self, operation, extra, label):
        code, out, err = self.command(self.p.aws_argv(operation, extra), label)
        require(code == 0 and not err.strip(), "READBACK_COMMAND_FAILED")
        value = parse_json(out)
        require(type(value) is dict and not value.get("NextToken"), "READBACK_TRUNCATED")
        return value

    def readback(self):
        self.check_checkout(); self.check_files(); self.check_window()
        previous = self.prior("apply")
        require(previous["result"].get("backup_verified") is True, "BACKUP_REQUIRED")
        # Revalidate opaque current/backup identity; no semantic state read.
        backup = self.p.backups / "initial-ab9f141e83058209/billing.execution.tfstate"
        file_meta(self.p.state, self.p.uid); file_meta(backup, self.p.uid)
        require(hash_file(self.p.state) == hash_file(backup) == previous["result"]["backup"]["sha256"],
                "STATE_BACKUP_DRIFT")
        with self.lease("readback"):
            common = ["--account-id", ACCOUNT, "--budget-name", BUDGET]
            b = self.query("describe-budget", common + ["--show-filter-expression"], "read-budget")
            t = self.query("list-tags-for-resource", ["--resource-arn", ARN], "read-tags")
            n = self.query("describe-notifications-for-budget", common + ["--max-results", "100", "--no-paginate"], "read-notifications")
            # One bounded page must be complete; do not issue unapproved pagination requests.
            subs = {}
            for threshold in (50, 80, 100):
                subs[threshold] = self.query("describe-subscribers-for-notification",
                    common + ["--notification", json.dumps(expected_notification(threshold), separators=(",", ":")),
                              "--max-results", "100", "--no-paginate"], f"read-subscribers-{threshold}")
            safe = sanitize_readback(b, t, n, subs, self.private_recipient())
            return self.receipt("readback", safe)

    def post_freeze_scan(self, manifest_path, manifest_sha):
        self.check_checkout(allow_packet=True, external_freeze=manifest_path); self.check_files(); self.check_window()
        self.prior("readback")
        raw = read_nofollow(manifest_path)
        require(digest(raw) == manifest_sha, "PUBLIC_FREEZE_HASH")
        freeze = parse_json(raw)
        require(set(freeze) == {"root", "files"} and type(freeze["files"]) is list and freeze["files"], "PUBLIC_FREEZE_SCHEMA")
        require(freeze["root"] == self.gate["public_packet_root"], "PUBLIC_FREEZE_GATE_SCOPE")
        root = Path(freeze["root"])
        require(not root.is_absolute() and ".." not in root.parts
                and str(root).startswith("docs/agent-runs/phase-12/evidence/"), "PUBLIC_FREEZE_ROOT")
        packet = self.p.repo / root
        require(packet.is_dir() and packet.resolve().is_relative_to(self.p.repo.resolve()), "PUBLIC_FREEZE_ROOT")
        require(not Path(manifest_path).resolve().is_relative_to(packet.resolve()), "FREEZE_MANIFEST_MUST_BE_OUTSIDE_PACKET")
        # The scan receipt is published outside the frozen packet. All existing packet
        # content, including manifests, is scanned; no arbitrary exclusion mechanism.
        actual = {str(f.relative_to(self.p.repo)) for f in packet.rglob("*") if f.is_file() or f.is_symlink()}
        require(actual == {x.get("path") for x in freeze["files"]}, "PUBLIC_FREEZE_INCOMPLETE")
        recipient = self.private_recipient().encode()
        reviewed = []
        seen = set()
        for row in freeze["files"]:
            require(set(row) == {"path", "sha256", "bytes"}, "PUBLIC_FREEZE_ENTRY")
            rel = Path(row["path"])
            require(not rel.is_absolute() and ".." not in rel.parts and rel.is_relative_to(root)
                    and str(rel) not in seen, "PUBLIC_SCAN_SCOPE")
            seen.add(str(rel))
            f = self.p.repo / rel
            require(f.resolve().is_relative_to(self.p.repo.resolve()) and not f.is_symlink(), "PUBLIC_SCAN_SYMLINK")
            data = read_nofollow(f)
            require(len(data) == row["bytes"] and digest(data) == row["sha256"], "PUBLIC_CONTENT_CHANGED_RESCAN")
            require(recipient.lower() not in data.lower(), "PUBLIC_RECIPIENT_FOUND")
            reviewed.append((f, row["sha256"]))
        # Recheck frozen bytes after scanning all files; a changed packet cannot reuse this receipt.
        require(all(hash_file(f) == sha for f, sha in reviewed), "PUBLIC_CONTENT_CHANGED_RESCAN")
        return {**self.binding, "stage": "post-freeze-scan", "observed_at": iso(self.now()),
                "public_manifest_sha256": manifest_sha, "files_scanned": len(reviewed), "matches": 0,
                "excluded": "Only this external fixed-schema receipt and the external freeze-input manifest; every existing packet file was scanned. Any packet addition or change requires a new frozen manifest and scan."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("p3-check", "apply", "readback", "post-freeze-scan"))
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--gate-sha256", required=True)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--public-manifest", type=Path)
    parser.add_argument("--public-manifest-sha256")
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        ex = Execution(production_policy()).load_gate(args.gate, args.gate_sha256, args.operation)
        if args.mode == "post-freeze-scan":
            require(args.public_manifest is not None and args.public_manifest_sha256, "PUBLIC_FREEZE_REQUIRED")
            result = ex.post_freeze_scan(args.public_manifest, args.public_manifest_sha256)
        else:
            require(args.public_manifest is None and args.public_manifest_sha256 is None, "UNEXPECTED_SCAN_OPTIONS")
            result = {"p3-check": ex.p3_check, "apply": ex.apply, "readback": ex.readback}[args.mode]()
        print(json.dumps(result, sort_keys=True))
        return 0
    except Blocked as error:
        # These exception messages are author-owned constants, never subprocess/private output.
        print(json.dumps({"status": "BLOCKED-ON", "code": str(error)}))
        return 2
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print(json.dumps({"status": "BLOCKED-ON", "code": "LOCAL_OR_SCHEMA_FAILURE_NO_RETRY"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
