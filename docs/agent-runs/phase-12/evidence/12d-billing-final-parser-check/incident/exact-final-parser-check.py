"""Single authorized L1 final-parser evaluation; prescribed two-field output only."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import stat
import sys

sys.dont_write_bytecode = True
SOURCE = Path('/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/billing/budget_execution.py')
EXPECTED = 'a31852d14e80d970e2338f8a5d94320ea3ca3b89ec759584689d8331d446080b'
SAVED = Path('/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/operations/billing-20261101-2030/p3-describe-budget.stderr')
OUTPUT = Path('/tmp/scholarchain-phase12d-final-parser-check/result.json')
LIMIT = 65536
ALLOWED = {'P3_UNEXPECTED_STDOUT', 'P3_NOT_SERVICE_ERROR',
           'P3_NOT_EXACT_NOT_FOUND', 'P3_MIXED_ERROR'}


def signature(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


source_before = SOURCE.stat()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
spec = importlib.util.spec_from_file_location('billing_l1_exact_final_parser_check', SOURCE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
assert signature(source_before) == signature(SOURCE.stat())
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
# Import definitions only: no Policy, Execution, production mode or live call.
before = SAVED.lstat()
assert stat.S_ISREG(before.st_mode) and before.st_uid == 501
assert stat.S_IMODE(before.st_mode) == 0o600 and before.st_nlink == 1
assert before.st_size <= LIMIT
fd = os.open(SAVED, os.O_RDONLY | os.O_NOFOLLOW)
try:
    assert signature(before) == signature(os.fstat(fd))
    raw = os.read(fd, LIMIT + 1)  # Sole bounded saved-stderr content read.
    assert len(raw) == before.st_size and len(raw) <= LIMIT
    assert signature(before) == signature(os.fstat(fd)) == signature(SAVED.lstat())
finally:
    os.close(fd)

accepted, blocked_code = True, None
try:
    module.absence(254, b'', raw)  # Sole call, using unmodified/unstripped bytes.
except module.Blocked as error:
    code = str(error)
    assert code in ALLOWED
    accepted, blocked_code = False, code

result = {'accepted': accepted, 'blocked_code': blocked_code}
with OUTPUT.open('x') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(json.dumps(result))
