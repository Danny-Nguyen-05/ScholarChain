# 6A preflight observations

- Initial branch: `main`; HEAD and base SHA: `03493882399e9020e6892c9f97e0ec8919365215`.
- Initial `git status --short` and `git ls-files --others --exclude-standard`: empty. The user answered yes to creating `phase-6`; `git switch -c phase-6` then succeeded. The first sandboxed branch attempt failed because `.git/refs/heads/phase-6.lock` was not writable; approved retry succeeded.
- JDK command: `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java -version`. Exit 0. Output: `openjdk version "17.0.20.1" 2026-08-18`, Homebrew build `17.0.20.1+0`.
- Baseline command: `env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch check > /private/tmp/scholarchain-phase6a-baseline.txt 2>&1` in the repository root. The first sandboxed invocation exited 1 because it could not open `/Users/danny/.sbt/boot/sbt.boot.lock`; the approved retry exited 0. The retained successful output is `baseline-check.txt` in this directory.
- Successful baseline: `sbt check` reported 129 + 64 + 39 + 233 + 4 = **469 tests**, zero failed, and `[success] Total time: 412 s (06:52)`. `/usr/bin/time` reported `real 413.74` seconds.
- The expected `checkProbeInjectFailure` message inside a passing build-verification self-test is not a baseline failure.
