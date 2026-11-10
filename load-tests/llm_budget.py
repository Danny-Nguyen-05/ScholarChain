#!/usr/bin/env python3
"""Per-bucket claude-haiku-5-5 (Anthropic API) answer budget, shared by EVERY step that calls the LLM (python3 -I; stdlib only).

The USD 1.33 cap of the course session is split into answer BUCKETS (pinned in experiments/manifests/llm-allocation.json):
14c (Phase 14C smoke query), 15b (load test), 16b (live evaluation) and 17 (demo and final smoke). Each bucket is a HARD STOP:
once it is used up that step makes no more LLM calls. The overall cap is the backstop (at the claude-haiku-5-5 estimate the
115 answers cost about USD 0.157, so the bucket counts bind first and USD 1.33 is a conservative upper bound). Nothing rolls over automatically; moving
spare answers from one bucket to another needs the user's approval file (transfer).

  init                                       create the append-only ledger once (refuses if it exists)
  status                                     per-bucket size / used / remaining, the total and the cap
  reserve  --bucket B --answers N            REQUIRED before any LLM-calling command; refuses (exit 3) if bucket used + N > bucket size
                                             or if the ledger total + N answers would exceed the shared cap; else appends a line
  release  --bucket B --answers N            give back reserved answers that were not used (cannot go below zero)
  transfer --from X --to Y --answers N --approval FILE
                                             moves N unused answers of bucket X to Y; refuses unless FILE exists and holds the exact line
                                             APPROVED_LLM_TRANSFER=X->Y:N (and that approval was not already applied)
  adjust   --usd U --source S [--note T]     add spend that was observed outside the buckets (for example from the AWS bill); counts only
                                             against the total cap

Cost per answer is an ESTIMATE derived from load-tests/config/load-profile.v1.json (pinned claude-haiku-5-5 rates x token plan); it
is not metered; the Anthropic console, the Voyage console and the AWS bill are the costs of record, reported as separate items and
then combined (cost_report below). Embeddings (Voyage voyage-4-lite) have their own USD 0.30 cap and token counter in the profile. The ledger is a local JSONL file OUTSIDE the repository (default
~/.scholarchain/llm-ledger/haiku-ledger.jsonl) so `sbt clean` cannot erase it; every read and write holds an flock.
A bucket reservation is trusted bookkeeping: the tool cannot see calls made by other programs.

Exit codes: 0 ok, 2 usage, 3 refused (nothing written), 5 I/O error.
"""
import argparse
import collections
import datetime
import decimal
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_PROFILE = os.path.join(HERE, "config", "load-profile.v1.json")
DEFAULT_ALLOCATION = os.path.join(REPO, "experiments", "manifests", "llm-allocation.json")
DEFAULT_LEDGER = "~/.scholarchain/llm-ledger/haiku-ledger.jsonl"
ALLOCATION_SCHEMA = "scholarchain.llm-allocation.v2"
BUCKET_NAME = re.compile(r"^[a-z0-9]{1,8}$")
D = decimal.Decimal
MICRO = D("0.000001")


class Refused(Exception):
    """A rule was violated; nothing was written (exit 3)."""


def utc_stamp():
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (now.microsecond // 1000)


def jdump(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def money(value):
    return format(value.quantize(MICRO, rounding=decimal.ROUND_UP), "f")


def parse_decimal(text, label, allow_zero=True):
    try:
        value = D(str(text))
    except (decimal.InvalidOperation, ValueError):
        raise Refused("%s is not a decimal number" % label)
    if not value.is_finite() or value < 0 or (value == 0 and not allow_zero):
        raise Refused("%s must be a finite, non-negative number" % label)
    return value


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_profile(path=DEFAULT_PROFILE):
    try:
        with open(path, encoding="utf-8") as handle:
            profile = json.load(handle)
    except (OSError, ValueError):
        raise Refused("the load profile %s is missing or not valid JSON" % path)
    if profile.get("schema") != "scholarchain.load-profile.v1":
        raise Refused("the load profile schema must be scholarchain.load-profile.v1")
    return profile


def cost_per_answer(profile):
    llm = profile["llm"]
    tokens = llm["tokens_per_answer"]
    tin = D(tokens["planner_input"] + tokens["synthesis_input"])
    tout = D(tokens["planner_output"] + tokens["synthesis_output"])
    cost = (tin * parse_decimal(llm["pricing"]["input_usd_per_million_tokens"], "input rate")
            + tout * parse_decimal(llm["pricing"]["output_usd_per_million_tokens"], "output rate")) / D(1000000)
    return (cost * parse_decimal(llm.get("cost_multiplier", "1"), "cost_multiplier", allow_zero=False)).quantize(MICRO, rounding=decimal.ROUND_UP)


def embedding_cost(profile, tokens, prior_tokens=0):
    """USD for `tokens` new Voyage tokens after `prior_tokens` already used on the account: the first free_tokens are free, the rest cost
    usd_per_million_tokens per 1M (rounded up to a micro-dollar). Raises Refused for a negative or non-integer count."""
    emb = profile["embeddings"]
    if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in (tokens, prior_tokens)):
        raise Refused("embedding token counts must be non-negative integers")
    free = emb["free_tokens"]
    billable = max(0, prior_tokens + tokens - free) - max(0, prior_tokens - free)
    return (D(billable) * parse_decimal(emb["usd_per_million_tokens"], "embedding rate") / D(1000000)).quantize(MICRO, rounding=decimal.ROUND_UP)


def cost_report(profile, answers, embedding_tokens=None, prior_embedding_tokens=0, aws_usd=None):
    """The experiment cost report: AWS, Anthropic and Voyage as separate items, then the combined total.

    Anthropic is the estimate answers x cost_per_answer (not metered). Voyage is embedding_cost() when the tokens are known; with no
    token count it is reported as USD 0 with the usage marked 'not metered' (the first 200M tokens are free). AWS is never estimated
    here: pass aws_usd (from the AWS bill) or leave None, and the combined total then says it excludes AWS."""
    unit = cost_per_answer(profile)
    tokens = profile["llm"]["tokens_per_answer"]
    anthropic_usd = (unit * answers).quantize(MICRO, rounding=decimal.ROUND_UP)
    voyage_usd = D(0) if embedding_tokens is None else embedding_cost(profile, embedding_tokens, prior_embedding_tokens)
    aws = None if aws_usd is None else parse_decimal(aws_usd, "aws_usd")
    combined = anthropic_usd + voyage_usd + (aws or D(0))
    return {
        "aws": {"usd": None if aws is None else money(aws), "usage": "taken from the AWS bill and the pre-spend receipts; not metered here"},
        "anthropic": {"model": "claude-haiku-5-5", "usd": money(anthropic_usd), "answers": answers,
                      "input_tokens_estimate": answers * (tokens["planner_input"] + tokens["synthesis_input"]),
                      "output_tokens_estimate": answers * (tokens["planner_output"] + tokens["synthesis_output"]),
                      "usage": "estimated from pinned tokens and rates; the Anthropic console is the record" if answers else "no answers sent: USD 0"},
        "voyage": {"model": profile["embeddings"]["model"], "usd": money(voyage_usd), "tokens": embedding_tokens,
                   "usage": ("%d tokens counted; the first %d account tokens are free" % (embedding_tokens, profile["embeddings"]["free_tokens"]))
                   if embedding_tokens is not None else "tokens not metered here; the first %d account tokens are free so the charge is USD 0 while the account stays under that" % profile["embeddings"]["free_tokens"]},
        "combined_usd": money(combined),
        "combined_scope": "aws + anthropic + voyage" if aws is not None else "anthropic + voyage only (AWS not included: take it from the bill)",
    }


def load_allocation(path=DEFAULT_ALLOCATION):
    """Returns ({bucket: answers}, sha256 of the file, shared cap Decimal). The allocation file is the pinned source of bucket sizes."""
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
        doc = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        raise Refused("the allocation file %s is missing or not valid JSON" % path)
    if doc.get("schema") != ALLOCATION_SCHEMA or not isinstance(doc.get("buckets"), dict) or not doc["buckets"]:
        raise Refused("the allocation file must have schema %s and a non-empty buckets object" % ALLOCATION_SCHEMA)
    sizes = {}
    for name, entry in doc["buckets"].items():
        answers = entry.get("answers") if isinstance(entry, dict) else None
        if not BUCKET_NAME.match(name) or isinstance(answers, bool) or not isinstance(answers, int) or answers < 0:
            raise Refused("allocation bucket %r needs a name matching %s and a non-negative integer answers" % (name, BUCKET_NAME.pattern))
        sizes[name] = answers
    return sizes, hashlib.sha256(raw).hexdigest(), parse_decimal(doc.get("shared_cap_usd"), "allocation shared_cap_usd")


def expand(path):
    return os.path.abspath(os.path.expanduser(path))


class Budget:
    def __init__(self, ledger_path=None, allocation_path=DEFAULT_ALLOCATION, profile_path=DEFAULT_PROFILE):
        self.profile = load_profile(profile_path)
        self.unit = cost_per_answer(self.profile)
        self.cap = parse_decimal(self.profile["llm"]["shared_cap_usd"], "shared cap")
        self.ledger_path = expand(ledger_path or self.profile["llm"].get("ledger_default_path", DEFAULT_LEDGER))
        self.base_sizes, self.alloc_sha, alloc_cap = load_allocation(allocation_path)
        if alloc_cap != self.cap:
            raise Refused("the allocation shared_cap_usd %s differs from the pinned profile cap %s" % (money(alloc_cap), money(self.cap)))
        if sum(self.base_sizes.values()) * self.unit > self.cap:
            raise Refused("the allocation (%d answers x %s USD) exceeds the shared cap %s USD" % (sum(self.base_sizes.values()), money(self.unit), money(self.cap)))

    # -------------------------------------------------------------------------------------------------- file access
    def init(self, who):
        os.makedirs(os.path.dirname(self.ledger_path), mode=0o700, exist_ok=True)
        try:
            fd = os.open(self.ledger_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            raise Refused("the ledger %s already exists: a script never resets the spend record" % self.ledger_path)
        with os.fdopen(fd, "wb") as handle:
            handle.write((jdump({"event": "init", "at": utc_stamp(), "by": who, "alloc_sha256": self.alloc_sha, "unit_usd": money(self.unit)}) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())

    def _open(self):
        try:
            return os.open(self.ledger_path, os.O_RDWR | os.O_APPEND | os.O_NOFOLLOW)
        except FileNotFoundError:
            raise Refused("the LLM ledger %s does not exist: create it once with `llm_budget.py init` (an absent ledger is never read as zero)" % self.ledger_path)
        except OSError:
            raise Refused("the LLM ledger %s cannot be opened" % self.ledger_path)

    def _state(self, fd):
        os.lseek(fd, 0, os.SEEK_SET)
        data = b""
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            data += chunk
        used = collections.OrderedDict((name, 0) for name in self.base_sizes)
        moved = collections.OrderedDict((name, 0) for name in self.base_sizes)
        usd = D(0)
        extra = D(0)
        init_sha = None
        approvals = set()
        for number, line in enumerate(data.decode("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                event = entry["event"]
                if event == "init":
                    init_sha = entry.get("alloc_sha256")
                elif event in ("reserve", "answer", "release"):
                    bucket, answers, unit = entry["bucket"], entry["answers"], D(str(entry["unit_usd"]))
                    if bucket not in used or isinstance(answers, bool) or not isinstance(answers, int) or answers < 1 or not unit.is_finite() or unit < 0:
                        raise ValueError
                    sign = -1 if event == "release" else 1
                    used[bucket] += sign * answers
                    usd += sign * answers * unit
                    if used[bucket] < 0:
                        raise ValueError
                elif event == "transfer":
                    src, dst, answers = entry["from"], entry["to"], entry["answers"]
                    if src not in used or dst not in used or isinstance(answers, bool) or not isinstance(answers, int) or answers < 1:
                        raise ValueError
                    moved[src] -= answers
                    moved[dst] += answers
                    approvals.add((entry["approval_sha256"], entry["approval_line"]))
                elif event == "adjust":
                    value = D(str(entry["usd"]))
                    if not value.is_finite() or value < 0:
                        raise ValueError
                    extra += value
                    usd += value
                else:
                    raise ValueError
            except (ValueError, KeyError, TypeError, decimal.InvalidOperation):
                raise Refused("ledger line %d is not a valid entry: refusing to guess" % number)
        sizes = {name: self.base_sizes[name] + moved[name] for name in self.base_sizes}
        for name, size in sizes.items():
            if size < 0:
                raise Refused("the ledger moves more answers out of bucket %s than it holds" % name)
        return {"used": used, "sizes": sizes, "usd": usd, "extra_usd": extra, "init_alloc_sha256": init_sha, "approvals": approvals,
                "answers": sum(used.values())}

    def state(self):
        fd = self._open()
        try:
            fcntl.flock(fd, fcntl.LOCK_SH)
            return self._state(fd)
        finally:
            os.close(fd)

    def _append(self, fd, entry):
        os.write(fd, (jdump(dict(entry, at=utc_stamp())) + "\n").encode("utf-8"))
        os.fsync(fd)

    # ------------------------------------------------------------------------------------------------ operations
    def try_charge(self, bucket, answers, entry=None, event="reserve", run_usd_spent=D(0), run_usd_limit=None):
        """Atomically (flock) check and append. Returns (True, '') or (False, reason) with reason bucket-cap, ledger-cap or run-cap."""
        fd = self._open()
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            st = self._state(fd)
            if bucket not in st["sizes"]:
                raise Refused("unknown bucket %r (buckets: %s)" % (bucket, ", ".join(st["sizes"])))
            cost = self.unit * answers
            if st["used"][bucket] + answers > st["sizes"][bucket]:
                return False, "bucket-cap"
            if st["usd"] + cost > self.cap:
                return False, "ledger-cap"
            if run_usd_limit is not None and run_usd_spent + cost > run_usd_limit:
                return False, "run-cap"
            self._append(fd, dict(entry or {}, event=event, bucket=bucket, answers=answers, unit_usd=money(self.unit)))
            return True, ""
        finally:
            os.close(fd)

    def reserve(self, bucket, answers, note="", who=""):
        if answers < 1:
            raise Refused("--answers must be at least 1")
        ok, why = self.try_charge(bucket, answers, {"note": note[:200], "by": who[:80]})
        if not ok:
            st = self.state()
            if why == "bucket-cap":
                raise Refused("bucket %s: used %d + requested %d > size %d (remaining %d)" % (bucket, st["used"][bucket], answers, st["sizes"][bucket], st["sizes"][bucket] - st["used"][bucket]))
            raise Refused("ledger total %s USD + %d answers x %s USD > shared cap %s USD" % (money(st["usd"]), answers, money(self.unit), money(self.cap)))

    def release(self, bucket, answers, note="", who=""):
        fd = self._open()
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            st = self._state(fd)
            if bucket not in st["used"]:
                raise Refused("unknown bucket %r" % bucket)
            if answers < 1 or answers > st["used"][bucket]:
                raise Refused("bucket %s: cannot release %d answers, only %d are recorded as used" % (bucket, answers, st["used"][bucket]))
            self._append(fd, {"event": "release", "bucket": bucket, "answers": answers, "unit_usd": money(self.unit), "note": note[:200], "by": who[:80]})
        finally:
            os.close(fd)

    def transfer(self, src, dst, answers, approval):
        line = "APPROVED_LLM_TRANSFER=%s->%s:%d" % (src, dst, answers)
        if src == dst or answers < 1:
            raise Refused("a transfer needs two different buckets and at least 1 answer")
        path = os.path.abspath(approval)
        try:
            mode = os.lstat(path).st_mode
            if not stat.S_ISREG(mode):
                raise OSError
            with open(path, "rb") as handle:
                raw = handle.read(65537)
        except OSError:
            raise Refused("the approval file %s does not exist or is not a regular file" % approval)
        if len(raw) > 65536 or line not in [row.strip() for row in raw.decode("utf-8", "replace").splitlines()]:
            raise Refused("the approval file has no line exactly: %s" % line)
        approval_sha = hashlib.sha256(raw).hexdigest()
        fd = self._open()
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            st = self._state(fd)
            for name in (src, dst):
                if name not in st["sizes"]:
                    raise Refused("unknown bucket %r" % name)
            if (approval_sha, line) in st["approvals"]:
                raise Refused("this approval line was already applied: write a new approval for another transfer")
            spare = st["sizes"][src] - st["used"][src]
            if answers > spare:
                raise Refused("bucket %s has only %d unused answers, cannot move %d" % (src, spare, answers))
            self._append(fd, {"event": "transfer", "from": src, "to": dst, "answers": answers, "approval_sha256": approval_sha, "approval_line": line})
        finally:
            os.close(fd)

    def adjust(self, usd, source, note=""):
        value = parse_decimal(usd, "--usd", allow_zero=False)
        fd = self._open()
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            self._state(fd)
            self._append(fd, {"event": "adjust", "usd": money(value), "source": source[:80], "note": note[:200]})
        finally:
            os.close(fd)

    def status_lines(self):
        st = self.state()
        lines = []
        for name in st["sizes"]:
            used, size = st["used"][name], st["sizes"][name]
            lines.append("BUCKET %s size=%d used=%d remaining=%d est_usd_used=%s" % (name, size, used, size - used, money(self.unit * used)))
        lines.append("TOTAL answers_used=%d usd_used=%s (incl. adjust %s) shared_cap_usd=%s remaining_usd=%s unit_usd=%s" % (
            st["answers"], money(st["usd"]), money(st["extra_usd"]), money(self.cap), money(self.cap - st["usd"]), money(self.unit)))
        if st["init_alloc_sha256"] and st["init_alloc_sha256"] != self.alloc_sha:
            lines.append("ALLOCATION-CHANGED: llm-allocation.json differs from the file the ledger was created with; confirm the bucket sizes with the user")
        return lines


# ----------------------------------------------------------------------------------------------------------------- CLI
def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    def common(p, top):
        # accepted before or after the subcommand
        default = (lambda value: value) if top else (lambda value: argparse.SUPPRESS)
        p.add_argument("--ledger", default=default(None))
        p.add_argument("--allocation", default=default(DEFAULT_ALLOCATION))
        p.add_argument("--profile", default=default(DEFAULT_PROFILE))

    common(parser, True)
    sub = parser.add_subparsers(dest="cmd", required=True)
    common(sub.add_parser("init"), False)
    common(sub.add_parser("status"), False)
    for name in ("reserve", "release"):
        p = sub.add_parser(name)
        common(p, False)
        p.add_argument("--bucket", required=True)
        p.add_argument("--answers", type=int, required=True)
        p.add_argument("--note", default="")
    p = sub.add_parser("transfer")
    common(p, False)
    p.add_argument("--from", dest="src", required=True)
    p.add_argument("--to", dest="dst", required=True)
    p.add_argument("--answers", type=int, required=True)
    p.add_argument("--approval", required=True)
    p = sub.add_parser("adjust")
    common(p, False)
    p.add_argument("--usd", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--note", default="")
    return parser


def main(argv, out=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    who = os.environ.get("USER", "unknown")
    try:
        budget = Budget(args.ledger, args.allocation, args.profile)
        if args.cmd == "init":
            budget.init(who)
            out.write("RESULT: LEDGER-CREATED %s\n" % budget.ledger_path)
        elif args.cmd == "status":
            for line in budget.status_lines():
                out.write(line + "\n")
        elif args.cmd == "reserve":
            budget.reserve(args.bucket, args.answers, args.note, who)
            out.write("RESULT: RESERVED bucket=%s answers=%d est_usd=%s\n" % (args.bucket, args.answers, money(budget.unit * args.answers)))
            for line in budget.status_lines():
                if line.startswith("BUCKET %s " % args.bucket) or line.startswith("TOTAL"):
                    out.write(line + "\n")
        elif args.cmd == "release":
            budget.release(args.bucket, args.answers, args.note, who)
            out.write("RESULT: RELEASED bucket=%s answers=%d\n" % (args.bucket, args.answers))
        elif args.cmd == "transfer":
            budget.transfer(args.src, args.dst, args.answers, args.approval)
            out.write("RESULT: TRANSFERRED %d answers %s -> %s\n" % (args.answers, args.src, args.dst))
        else:
            budget.adjust(args.usd, args.source, args.note)
            out.write("RESULT: ADJUSTED usd=%s source=%s\n" % (money(parse_decimal(args.usd, "--usd")), args.source[:80]))
        return 0
    except Refused as error:
        sys.stderr.write("REFUSED: %s\n" % error)
        return 3
    except OSError as error:
        sys.stderr.write("I/O-ERROR: %s\n" % type(error).__name__)
        return 5


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
