# ScholarChain Phase 13C repair 1 (finding C1): the Phase 4 ceiling check for the Hadoop prep config.
# ONE program, two users: scripts/lib/pipeline.py runs it locally at plan time, and the hadoop-prep EMR step runs this installed,
# sha256-verified copy on the primary node. argv: prep-config.json then the seven ceilings in the order of FIELDS below.
# Exit 0 = every field present, numeric and <= its ceiling; exit 1 = refusal (message on stderr).
import json
import sys

FIELDS = (
    "maxLocalSampleRecords",
    "reducerCount",
    "maxCandidateBlockSize",
    "maxCandidatePairsPerBlock",
    "maxAuthorTeamSize",
    "maxRecordBytes",
    "maxXmlEntityExpansion",
)


def fail(message):
    sys.stderr.write("bounded-pipeline: %s\n" % (message,))
    raise SystemExit(1)


def reject_non_finite(token):
    raise ValueError("non-finite JSON number: %s" % (token,))


def json_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value == float("inf") or value == float("-inf"):
            return None
        return value
    return None


if len(sys.argv) != 2 + len(FIELDS):
    fail("ceiling check expected a config path and %d ceilings" % (len(FIELDS),))
limits = []
for field, raw in zip(FIELDS, sys.argv[2:]):
    if not raw.isdigit():
        fail("ceiling for %s is not an integer" % (field,))
    limits.append(int(raw))
try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        data = json.load(handle, parse_constant=reject_non_finite)
except Exception as error:
    fail("prep config is not valid JSON: %s" % (error,))
if not isinstance(data, dict):
    fail("prep config root must be a JSON object")
for field, limit in zip(FIELDS, limits):
    if field not in data:
        fail("missing numeric field: %s" % (field,))
    number = json_number(data[field])
    if number is None:
        fail("%s must be a JSON number" % (field,))
    if number > limit:
        fail("%s %s exceeds ceiling %s" % (field, number, limit))
