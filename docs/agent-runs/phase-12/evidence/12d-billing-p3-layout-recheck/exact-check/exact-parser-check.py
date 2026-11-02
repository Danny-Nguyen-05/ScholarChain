"""One authorized saved-stderr evaluation; never emits or retains input bytes."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import stat
import sys

sys.dont_write_bytecode = True
SOURCE = Path('/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/budget_execution.py')
EXPECTED = '297830d412cefd53dc4938c06dc1b654b7188fcaa977cf10902123715f39c3fd'
SAVED = Path('/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/operations/billing-20261101-2030/p3-describe-budget.stderr')
OUTPUT = Path('/tmp/scholarchain-phase12d-p3-layout-check/result.json')
LIMIT = 65536
ALLOWED_CODES = {'P3_UNEXPECTED_STDOUT', 'P3_NOT_SERVICE_ERROR',
                 'P3_NOT_EXACT_NOT_FOUND', 'P3_MIXED_ERROR'}


def signature(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def bucket(count):
    return count if count < 2 else '>1'


def leading_newlines(raw):
    # Count contiguous raw LF or CRLF sequences starting at byte zero.
    # Spaces/tabs are never stripped or skipped.
    position = count = 0
    while position < len(raw):
        if raw[position:position + 2] == b'\r\n':
            position += 2
        elif raw[position:position + 1] == b'\n':
            position += 1
        else:
            break
        count += 1
    return bucket(count)


def trailing_newlines(raw):
    # Count contiguous raw LF or CRLF sequences ending at the last byte.
    # No strip/rstrip operation is used.
    position, count = len(raw), 0
    while position:
        if position >= 2 and raw[position - 2:position] == b'\r\n':
            position -= 2
        elif raw[position - 1:position] == b'\n':
            position -= 1
        else:
            break
        count += 1
    return bucket(count)


source_before = SOURCE.stat()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
spec = importlib.util.spec_from_file_location('billing_f1_exact_parser_check', SOURCE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
assert signature(source_before) == signature(SOURCE.stat())
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
# No Policy/Execution object or production mode is instantiated or invoked.
before = SAVED.lstat()
assert stat.S_ISREG(before.st_mode) and before.st_uid == 501
assert stat.S_IMODE(before.st_mode) == 0o600 and before.st_nlink == 1
assert before.st_size <= LIMIT
fd = os.open(SAVED, os.O_RDONLY | os.O_NOFOLLOW)
try:
    assert signature(before) == signature(os.fstat(fd))
    raw = os.read(fd, LIMIT + 1)  # The one bounded saved-stderr content read.
    assert len(raw) == before.st_size and len(raw) <= LIMIT
    assert signature(before) == signature(os.fstat(fd)) == signature(SAVED.lstat())
finally:
    os.close(fd)

leading = leading_newlines(raw)
trailing = trailing_newlines(raw)
crlf = b'\r\n' in raw
accepted, blocked_code = True, None
try:
    module.absence(254, b'', raw)  # Exactly one call, with original unstripped bytes.
except module.Blocked as error:
    code = str(error)
    assert code in ALLOWED_CODES
    accepted, blocked_code = False, code

result = {'accepted': accepted, 'blocked_code': blocked_code,
          'leading_newline_count': leading, 'trailing_newline_count': trailing,
          'crlf_present': crlf}
with OUTPUT.open('x') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(json.dumps(result))
