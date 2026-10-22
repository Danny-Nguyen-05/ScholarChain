"""Bounded local read of the Phase 6C repair smoke counter table."""

from pathlib import Path
import os
import subprocess
import sys


if len(sys.argv) != 2:
    raise SystemExit("usage: inspect_counters.py COUNTERS_PARQUET_DIR")

evidence = Path(__file__).resolve().parent
classpath = (evidence / "test-classpath.txt").read_text().splitlines()[-1]
classes = Path("/private/tmp/phase6c-counter-inspect")
classes.mkdir(exist_ok=True)
jdk = Path("/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin")
subprocess.run(
    [str(jdk / "javac"), "-cp", classpath, "-d", str(classes), str(evidence / "CounterInspect.java")],
    check=True,
)
modules = [
    "java.base/java.lang", "java.base/java.lang.invoke", "java.base/java.lang.reflect",
    "java.base/java.io", "java.base/java.net", "java.base/java.nio",
    "java.base/java.util", "java.base/java.util.concurrent",
    "java.base/java.util.concurrent.atomic", "java.base/jdk.internal.ref",
    "java.base/sun.nio.ch", "java.base/sun.nio.cs", "java.base/sun.security.action",
    "java.base/sun.util.calendar", "java.security.jgss/sun.security.krb5",
]
command = [
    str(jdk / "java"), "-Xmx2g", "-Dspark.ui.enabled=false",
    "-Djava.net.preferIPv4Stack=true",
    *(f"--add-opens={module}=ALL-UNNAMED" for module in modules),
    "-cp", f"{classes}:{classpath}", "CounterInspect", sys.argv[1],
]
environment = dict(os.environ, SPARK_LOCAL_IP="127.0.0.1")
result = subprocess.run(command, env=environment, check=False)
raise SystemExit(result.returncode)
