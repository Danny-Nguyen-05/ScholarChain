# Local Docker validation

All four images rebuilt from the current packaged application. Application JAR and all four versioned prompt/schema assets matched distribution hashes inside every image. Each main refused missing configuration with exit 2. All four images ran as UID 999, with authenticated metrics, process health independent of readiness, and correct selected main class.

Eight role/mode startup cases passed. Default unconfigured mode: health 200, ready 503. Explicit offline-synthetic mode: health 200, ready 200. The packaged query returned verified fixture publication count 3, replayed identical body (200), rejected changed body (409), and served evidence collection/item/explain (200).

Successful command: `DOCKER_CONFIG=/tmp/phase10b-docker-config DOCKER_HOST=unix:///Users/danny/.docker/run/docker.sock python3 /tmp/phase10b-docker.py` (exit 0, 13.530 seconds). Empty temporary Docker authentication configuration bypassed a stalled credential helper. Existing credentials were never read or copied.

Attempt 1 was retained: Docker build was cancelled (exit 130) after its credential helper stalled; harness exit 1, 165.960 seconds. Only this task's processes were cancelled. No daemon restart or other-work interruption.

Exact Docker argv/exit/duration, image IDs, asset/JAR hashes and eight-container cleanup are in `phase10b-docker-result.json`. Full raw log `/tmp/phase10b-docker.log`, SHA-256 91d9058c6cda4dc03402be99a0590045337baca6cb9945a5731b4828522f008a. Prior raw log `/tmp/phase10b-docker-attempt-1.log`, SHA-256 c5f8606a1a24af356befe3a9bf4df642276c9c1639e29b74c5b8440b074ba1ae.

The local placeholders in the smoke harness are deliberately public synthetic values. No registry push, cloud resource change or provider call occurred.


## Actual packaged downstream composition

`DOCKER_CONFIG=/tmp/phase10b-docker-config DOCKER_HOST=unix:///Users/danny/.docker/run/docker.sock python3 /tmp/phase10b-docker-remote.py` passed (exit 0, 2.805 seconds). Three packaged mains communicated on an isolated internal Docker network: configured query-api called graph/semantic via actual HTTP and returned verified fixture count 3. Both dependency CLOSED gauges and propagated trace IDs were observed. Stopping graph left query liveness 200 while readiness returned typed 503 NOT_READY with the supplied trace in 0.577 seconds. All three containers and the network were removed.

The first three integration harness attempts are retained separately: host port lookup was inappropriate for the isolated internal network; startup curl stderr/status parsing needed a retry; an assertion expected a more specific log template than the implementation emits. The final harness checks actual correlated successful non-health requests. Internal/new routes currently log the safe route label `unmatched`, a disclosed observability limitation. No production source or assertion of required behavior changed to bypass these harness issues.

Full result/commands: `phase10b-docker-remote-result.json`. Raw log `/tmp/phase10b-docker-remote.log`, SHA-256 a5601dac901791a372748e4559ff3e734ecd792d383a9bea1a7a8b8c6485cd93. Earlier harness scripts, result JSON and log hashes are retained alongside the successful evidence.

## Optional field wire types

A bounded packaged HTTP probe (`option-probe.json`, exit 0, 0.999 seconds) confirmed nullable evidence fields are null and explain.reason is a string, matching the OpenAPI nullable types. A suspected legacy Option serialization issue was ruled out without source changes. Its probe container was removed.
