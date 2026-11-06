# ScholarChain Phase 13C repair 1 (finding C1): the driver AND executor class-origin verifier (decision 12-10).
# ONE program, two users: `scripts/lib/pipeline.py verify-class-origin` runs it locally (tests, review) and the
# spark-class-origin and spark-job EMR steps run this installed, sha256-verified copy on the primary node.
# argv: probe-json spark-version scala-version jar-dir job-jar job-sha256. Exit 0 = CLASS-ORIGIN-OK; exit 1 = CLASS-ORIGIN-FAILED.
# Fails CLOSED: any missing, unreadable or differing report is a failure.
import json
import os
import sys


def fail(message):
    sys.stderr.write("CLASS-ORIGIN-FAILED: %s\n" % (message,))
    raise SystemExit(1)


if len(sys.argv) != 7:
    fail("expected: probe-json spark-version scala-version jar-dir job-jar job-sha256")
probe, spark_v, scala_v, jar_dir, job_jar, job_sha = sys.argv[1:7]
try:
    with open(probe, encoding="utf-8") as handle:
        doc = json.load(handle)
except Exception as error:
    fail("probe result unreadable: %s" % type(error).__name__)
if not isinstance(doc, dict) or doc.get("schemaVersion") != "scholarchain.phase12-readiness.v1" or doc.get("stage") != "probe":
    fail("not a Phase 12 readiness probe result")
if doc.get("externalExecutorVerified") is not True or doc.get("distributedRequired") is not True:
    fail("the executor was not verified outside the driver process")
driver = doc.get("driver")
tasks = doc.get("taskProcesses")
if not isinstance(driver, dict) or not isinstance(tasks, list) or not tasks:
    fail("the driver or executor report is missing")
need = ("spark", "scala-library", "scala-reflect", "scala3-library")
reports = [("driver", driver)] + [("executor-%s" % t.get("executorId"), t) for t in tasks if isinstance(t, dict)]
parsed = {}
prefix = jar_dir.rstrip("/") + "/"
for role, report in reports:
    if not str(report.get("javaVersion", "")).startswith("17."):
        fail("%s runs Java %s, not 17" % (role, report.get("javaVersion")))
    if role != "driver" and report.get("executorId") in (None, "driver", "unavailable"):
        fail("%s is not an executor process" % role)
    libs = {}
    for lib in report.get("libraries") or []:
        if isinstance(lib, dict):
            libs[lib.get("component")] = lib
    for component in need:
        if component not in libs:
            fail("%s report lacks %s" % (role, component))
    if libs["spark"].get("runtimeVersion") != spark_v:
        fail("%s Spark version %s differs from the required %s" % (role, libs["spark"].get("runtimeVersion"), spark_v))
    if libs["scala-library"].get("runtimeVersion") != scala_v:
        fail("%s Scala library version %s differs from the packaged job's %s" % (role, libs["scala-library"].get("runtimeVersion"), scala_v))
    for component in ("spark", "scala-library", "scala-reflect"):
        origin = str(libs[component].get("origin"))
        if not origin.startswith(prefix):
            fail("%s loaded %s from %s, outside the runtime jar directory %s" % (role, component, origin, jar_dir))
    if not os.path.basename(str(libs["spark"]["origin"])).endswith("-%s.jar" % spark_v):
        fail("%s Spark origin %s is not a %s jar" % (role, libs["spark"]["origin"], spark_v))
    if os.path.basename(str(libs["scala-library"]["origin"])) != "scala-library-%s.jar" % scala_v:
        fail("%s Scala library origin %s is not scala-library-%s.jar" % (role, libs["scala-library"]["origin"], scala_v))
    s3 = libs["scala3-library"]
    if s3.get("origin") != job_jar or s3.get("codeSourceSha256") != job_sha:
        fail("%s scala3-library is not loaded from the packaged job jar with the approved sha256" % role)
    parsed[role] = libs
base = parsed["driver"]
for role, libs in parsed.items():
    for component in need:
        for field in ("origin", "classSha256", "codeSourceSha256"):
            if libs[component].get(field) != base[component].get(field):
                fail("%s differs between the driver and %s for %s" % (field, role, component))
print("CLASS-ORIGIN-OK: the driver and %d executor report(s) agree on Spark %s, Scala %s and the packaged job jar" % (len(tasks), spark_v, scala_v))
