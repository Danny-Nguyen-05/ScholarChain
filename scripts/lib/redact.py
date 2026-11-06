#!/usr/bin/env python3
"""Redact sensitive text (stdlib only; run with python3 -I).

Usage:
  redact.py [--values-file FILE]                 stdin -> stdout, redacted
  redact.py --extract-private-vars FILE          print the quoted string values of a private tfvars
                                                 file, one per line (so callers can register them as
                                                 secrets); the values are never echoed elsewhere
  redact.py [--values-file FILE] --append-to FILE [--root DIR]
                                                 append the redacted text to FILE instead of stdout. The
                                                 leaf is opened with O_NOFOLLOW (a symlink is refused). With
                                                 --root DIR (the repository root) FILE must already exist and
                                                 is opened without O_CREAT below an O_NOFOLLOW directory
                                                 chain (see safeio.py); without --root it is created 0600.

What is redacted
  * every value listed in --values-file ("S<TAB>value" -> <redacted>, "A<TAB>value" -> <acct>)
  * the value of every environment variable whose NAME contains SECRET, TOKEN, PASSWORD,
    ACCESS_KEY, CREDENTIAL or PRIVATE_VARS (value length >= 4) -> <redacted>
  * any standalone 12-digit run (an AWS account ID, including inside ECR registry hosts)
    -> <acct>; runs bounded by letters or digits are left alone so 64-hex checksums survive

The module is also imported by timeout.py (loaded by file path, because python3 -I does not put the
script directory on sys.path).
"""
import os
import re
import sys

SECRET_NAME = re.compile(r"(SECRET|TOKEN|PASSWORD|ACCESS_KEY|CREDENTIAL|PRIVATE_VARS)")
ACCOUNT_RE = re.compile(r"(?<![0-9A-Za-z])[0-9]{12}(?![0-9A-Za-z])")
QUOTED = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
MIN_VALUE_LEN = 4
MIN_PRIVATE_VALUE_LEN = 6


def load_values(path):
    """Return [(kind, value)] from a values file ("S\\tvalue" or "A\\tvalue"); [] when absent."""
    values = []
    if not path:
        return values
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.rstrip("\n")
                if len(line) > 2 and line[1] == "\t" and line[0] in ("S", "A"):
                    values.append((line[0], line[2:]))
    except OSError:
        return []
    return values


def env_secret_values(environ=None):
    environ = os.environ if environ is None else environ
    found = []
    for name, value in environ.items():
        if SECRET_NAME.search(name) and len(value) >= MIN_VALUE_LEN:
            found.append(value)
    return found


def redact(text, values=(), environ=None):
    replacements = []
    for kind, value in values:
        if len(value) >= 3:
            replacements.append((value, "<acct>" if kind == "A" else "<redacted>"))
    for value in env_secret_values(environ):
        replacements.append((value, "<redacted>"))
    # Longest first so a value that contains another one is replaced whole.
    replacements.sort(key=lambda pair: len(pair[0]), reverse=True)
    for value, label in replacements:
        text = text.replace(value, label)
    return ACCOUNT_RE.sub("<acct>", text)


def private_values(path):
    """Quoted string values (length >= 6) found anywhere in a private tfvars file."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    found = []
    for match in QUOTED.finditer(text):
        value = match.group(1)
        if ACCOUNT_RE.fullmatch(value):
            continue  # a bare 12-digit account ID is handled by the bounded account rule, which spares checksums
        if len(value) >= MIN_PRIVATE_VALUE_LEN and "\n" not in value and value not in found:
            found.append(value)
    return found


def _append(path, root, text):
    """Append TEXT to PATH; refuses a symlink; returns an exit code."""
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("sc_safeio", os.path.join(here, "safeio.py"))
        safeio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(safeio)
    except Exception:  # noqa: BLE001
        sys.stderr.write("redact.py: safeio.py cannot be loaded\n")
        return 2
    try:
        if root:
            handle = safeio.open_append_existing(root, path)
        else:
            handle = os.fdopen(safeio.open_leaf_nofollow(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT), "ab")
    except (safeio.Refused, OSError) as error:
        sys.stderr.write("redact.py: cannot append to the log (%s)\n" % (error if isinstance(error, safeio.Refused) else type(error).__name__))
        return 1
    with handle:
        handle.write(text.encode("utf-8"))
    return 0


def main(argv):
    values_file = None
    extract = None
    append_to = None
    root = None
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--values-file" and index + 1 < len(argv):
            values_file = argv[index + 1]
            index += 2
        elif arg == "--extract-private-vars" and index + 1 < len(argv):
            extract = argv[index + 1]
            index += 2
        elif arg == "--append-to" and index + 1 < len(argv):
            append_to = argv[index + 1]
            index += 2
        elif arg == "--root" and index + 1 < len(argv):
            root = argv[index + 1]
            index += 2
        else:
            sys.stderr.write("redact.py: unknown or incomplete argument: %s\n" % arg)
            return 2
    if extract is not None:
        try:
            for value in private_values(extract):
                sys.stdout.write(value + "\n")
        except OSError:
            return 1
        return 0
    values = load_values(values_file)
    data = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    if append_to is not None:
        return _append(append_to, root, redact(data, values))
    sys.stdout.write(redact(data, values))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
