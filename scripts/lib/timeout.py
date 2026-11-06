#!/usr/bin/env python3
"""Run a command in its own process group and bound its wall-clock time.

Usage:
  timeout.py --seconds N [--grace G] [--output FILE] [--stdout FILE] [--stdin FILE] -- CMD [ARG...]

The child is started in a NEW session (and therefore a new process group). When N seconds
elapse, SIGTERM goes to the whole group, then SIGKILL after G seconds (default 10) if any
member is still alive. This also stops grandchildren the command spawned.

Exit codes: 124 the command timed out; 127 the command could not be started;
128+N the child (or this helper) was ended by signal N; otherwise the child's own exit code.

Output handling: with --output FILE the child's stdout and stderr are appended to FILE
(mode 0600). With --stdout FILE as well, only stderr goes to --output and stdout goes to
the --stdout file (mode 0600, truncated). With neither, the child inherits this process's
streams. --stdin FILE feeds that file to the child's standard input.

Every output opened here refuses a symlink at the leaf (O_NOFOLLOW). --stdout-new FILE (with --root DIR, the
repository root) is the confined form for outputs that must never overwrite anything: the file must NOT exist, is
created with O_CREAT | O_EXCL | O_NOFOLLOW below an O_NOFOLLOW directory chain (see safeio.py), and is never
truncated. The trace file named by SCHOLARCHAIN_TIMEOUT_LOG is appended to with O_NOFOLLOW: a symlink there makes
the helper exit 2 before any child is spawned.

When SCHOLARCHAIN_TIMEOUT_LOG names a file, one line "timeout=<N> <argv...>" is appended
before the command starts, so tests and audits can prove a command went through this helper.
The line is REDACTED first (account IDs and registry hosts become <acct>, secret-named
environment values and the values listed in the file named by SC_REDACT_FILE become <redacted>);
if the redactor cannot be loaded nothing is written, so raw argv is never persisted.

A non-finite or non-positive --seconds (nan, inf, 0, negative), or a non-finite or negative
--grace, is rejected with exit 2 BEFORE any child is spawned.
"""
import argparse
import importlib.util
import math
import os
import signal
import subprocess
import sys
import time

EXIT_TIMEOUT = 124
EXIT_NOT_STARTED = 127


def _load_module(name, filename):
    """Load a sibling module by file path (python3 -I keeps the script directory off sys.path)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001 - module missing or broken
        return None


def _load_redactor():
    return _load_module("sc_redact", "redact.py")


def _trace(path, seconds, command):
    redactor = _load_redactor()
    if redactor is None:
        return
    line = "timeout=%s %s" % (int(seconds), " ".join(command))
    line = redactor.redact(line, redactor.load_values(os.environ.get("SC_REDACT_FILE")))
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)  # a symlink raises ELOOP
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _open_private(path, flags):
    """Open an output (leaf symlinks refused); stdout/output files here are private temp files or new outputs."""
    return os.fdopen(os.open(path, flags | os.O_CREAT | os.O_NOFOLLOW, 0o600), "ab" if flags & os.O_APPEND else "wb")


def _killpg(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass
    except PermissionError:
        pass


def _group_alive(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def main(argv):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--grace", type=float, default=10.0)
    parser.add_argument("--output")
    parser.add_argument("--stdout")
    parser.add_argument("--stdout-new")
    parser.add_argument("--root")
    parser.add_argument("--stdin")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not (math.isfinite(args.seconds) and math.isfinite(args.grace)):
        sys.stderr.write("timeout.py: --seconds and --grace must be finite numbers\n")
        return 2
    if not command or args.seconds <= 0 or args.grace < 0:
        sys.stderr.write("timeout.py: need --seconds > 0 and a command after --\n")
        return 2

    if args.stdout and args.stdout_new:
        sys.stderr.write("timeout.py: --stdout and --stdout-new are mutually exclusive\n")
        return 2
    safeio = None
    if args.stdout_new:
        if not args.root:
            sys.stderr.write("timeout.py: --stdout-new needs --root (the repository root)\n")
            return 2
        safeio = _load_module("sc_safeio", "safeio.py")
        if safeio is None:
            sys.stderr.write("timeout.py: safeio.py cannot be loaded; refusing to open a confined output\n")
            return 2

    log_path = os.environ.get("SCHOLARCHAIN_TIMEOUT_LOG")
    if log_path:
        try:
            _trace(log_path, args.seconds, command)
        except OSError as error:
            sys.stderr.write("timeout.py: cannot append to the trace file (%s); refusing to run\n" % type(error).__name__)
            return 2

    out_handle = err_handle = stdin_handle = None
    opened = []
    try:
        try:
            if args.output:
                out_handle = _open_private(args.output, os.O_WRONLY | os.O_APPEND)
                opened.append(out_handle)
            if args.stdout or args.stdout_new:
                err_handle = out_handle
                if args.stdout_new:
                    out_handle = safeio.open_new(args.root, args.stdout_new)
                else:
                    out_handle = _open_private(args.stdout, os.O_WRONLY | os.O_TRUNC)
                opened.append(out_handle)
            elif out_handle is not None:
                err_handle = out_handle
            if args.stdin:
                stdin_handle = open(args.stdin, "rb")
                opened.append(stdin_handle)
        except Exception as error:  # noqa: BLE001 - a refused or unopenable output: nothing is spawned
            reason = str(error) if safeio is not None and isinstance(error, safeio.Refused) else type(error).__name__
            sys.stderr.write("timeout.py: cannot open an output (%s); the command was not started\n" % reason)
            return 2
        try:
            child = subprocess.Popen(
                command,
                stdin=stdin_handle,
                stdout=out_handle,
                stderr=subprocess.STDOUT if (err_handle is out_handle and out_handle is not None) else err_handle,
                start_new_session=True,
            )
        except OSError as error:
            sys.stderr.write("timeout.py: cannot start %s: %s\n" % (command[0], error))
            return EXIT_NOT_STARTED

        pgid = child.pid  # new session => group id equals child pid
        forwarded = {"sig": None}

        def forward(signum, _frame):
            forwarded["sig"] = signum
            _killpg(pgid, signal.SIGTERM)

        signal.signal(signal.SIGTERM, forward)
        signal.signal(signal.SIGINT, forward)

        try:
            code = child.wait(timeout=args.seconds)
        except subprocess.TimeoutExpired:
            _killpg(pgid, signal.SIGTERM)
            deadline = time.monotonic() + args.grace
            while time.monotonic() < deadline and _group_alive(pgid):
                try:
                    child.wait(timeout=0.05)
                except subprocess.TimeoutExpired:
                    pass
            if _group_alive(pgid):
                _killpg(pgid, signal.SIGKILL)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            sys.stderr.write("timeout.py: timed out after %ss: %s\n" % (int(args.seconds), command[0]))
            return EXIT_TIMEOUT
        if forwarded["sig"] is not None:
            # We were asked to stop: make sure nothing from the group lingers.
            time.sleep(0.05)
            if _group_alive(pgid):
                _killpg(pgid, signal.SIGKILL)
            return 128 + forwarded["sig"]
        if code < 0:
            return 128 + (-code)
        return code
    finally:
        for handle in opened:
            try:
                handle.close()
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
