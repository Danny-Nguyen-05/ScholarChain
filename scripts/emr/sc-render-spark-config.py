# ScholarChain Phase 13C repair 1 (finding C1): renders the Spark job config from the approved template.
# Run by the spark-job EMR step (installed, sha256-verified copy). argv: template out hadoop-run er-run output-root checkpoint.
# Replaces exactly four path keys (each must exist in the template) and writes OUT exclusively (never overwrites).
import json
import sys

template, out, hadoop_run, er_run, output_root, checkpoint = sys.argv[1:7]
with open(template, encoding="utf-8") as handle:
    document = json.load(handle)
if not isinstance(document, dict):
    raise SystemExit("spark config template must be a JSON object")
overrides = {
    "hadoopRunRoot": hadoop_run,
    "entityResolutionRunRoot": er_run,
    "outputRoot": output_root,
    "checkpointDirectory": checkpoint,
}
for key in overrides:
    if key not in document:
        raise SystemExit("spark config template lacks the key %s" % key)
document.update(overrides)
with open(out, "x", encoding="utf-8") as handle:
    json.dump(document, handle, indent=2, sort_keys=True)
    handle.write("\n")
