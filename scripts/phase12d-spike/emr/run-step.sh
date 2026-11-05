#!/usr/bin/env bash
# Usage: run-step.sh <timeout-seconds> <command> [args...]
# Sets the custom-runtime environment (never the stock EMR Spark one) and runs
# the command under `timeout` with a 60 second kill-after.
# JAVA_HOME is the Java 17 the bootstrap resolved on this node (file written by bootstrap.sh).
# Injectable for tests: SC_RUNTIME_DEST, SC_JAVA_HOME, SC_JAVA_HOME_FILE, SC_HADOOP_CONF_DIR.
set -euo pipefail
[ $# -ge 2 ] || { echo "usage: run-step.sh <timeout-seconds> <command> [args...]" >&2; exit 64; }
secs="$1"; shift
case "$secs" in ''|*[!0-9]*) echo "timeout must be an integer" >&2; exit 64 ;; esac

RUNTIME="${SC_RUNTIME_DEST:-/opt/scholarchain-runtime}"
JAVA_HOME_FILE="${SC_JAVA_HOME_FILE:-/opt/scholarchain-spike/java-home}"
if [ -n "${SC_JAVA_HOME:-}" ]; then
  export JAVA_HOME="$SC_JAVA_HOME"
elif [ -r "$JAVA_HOME_FILE" ] && [ -n "$(head -n1 "$JAVA_HOME_FILE")" ]; then
  JAVA_HOME="$(head -n1 "$JAVA_HOME_FILE")"; export JAVA_HOME
else
  echo "no resolved JAVA_HOME ($JAVA_HOME_FILE missing); the bootstrap did not complete" >&2; exit 4
fi
export SPARK_HOME="$RUNTIME"
export SPARK_CONF_DIR="$RUNTIME/conf"
export SPARK_SCALA_VERSION=2.13
export HADOOP_CONF_DIR="${SC_HADOOP_CONF_DIR:-/etc/hadoop/conf}"
export YARN_CONF_DIR="$HADOOP_CONF_DIR"
export PATH="$JAVA_HOME/bin:${PATH:-/usr/local/bin:/usr/bin:/bin}"
unset CLASSPATH SPARK_DIST_CLASSPATH HADOOP_CLASSPATH SPARK_CLASSPATH || true

exec timeout --kill-after=60 "$secs" "$@"
