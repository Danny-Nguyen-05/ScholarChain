# Subphase 10A command evidence

Working directory: /Users/danny/Documents/UIC/CS441/ScholarChain.
Exact owner command blocks and all observed exits are retained in build-owner-report.md, service-owner-report.md and test-owner-report.md. Full source logs remain under /tmp; log-index.json binds their hashes to lean retained output. Every sbt invocation used this environment:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

## Root full gate (result recorded in check-result.json after completion)

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version
sbt -batch check > /tmp/phase10a-check-1.log 2>&1
phase10a_check_result=$?
tail -65 /tmp/phase10a-check-1.log
exit "$phase10a_check_result"
```

Native escalation was required because the sbt cache lies outside the writable workspace. Root’s java-version output is separately retained; no ordinary sandbox failure was repeated for this final gate after the owner gates had already established that cache restriction.

## Docker Desktop startup

```bash
open -a Docker
```

Native escalation approved; exit0. No live AWS, provider, deployment, image push or repository commit command was run. Docker version/build/smoke results and initial failures are in the build owner report and retained outputs.

## Supplemental service YAML evidence returned by its owner

```bash
git status --short modules/services && python3 - <<'PY'
from pathlib import Path
import yaml
p=Path('modules/services/src/main/resources/openapi/scholarchain.v1.yaml')
x=yaml.safe_load(p.read_text())
assert x['openapi']=='3.0.3'
assert set(x['paths'])=={'/healthz','/readyz','/metrics','/v1/query','/v1/jobs/{jobId}','/v1/jobs/{jobId}/result'}
print('OpenAPI YAML parsed; six paths match the10A surface')
PY
```

Exit1: ModuleNotFoundError: No module named 'yaml'. No installation attempted.

```bash
ruby -ryaml -e 'x = YAML.load_file("modules/services/src/main/resources/openapi/scholarchain.v1.yaml"); abort "wrong schema" unless x["openapi"] == "3.0.3"; abort "wrong paths" unless x["paths"].size == 6; puts "OpenAPI YAML parsed; six paths match the 10A surface"'
```

Exit0: OpenAPI YAML parsed; six paths match the 10A surface. Syntax/basic surface validation only; no claim of complete OpenAPI semantic validation.

## Root distribution validation

```bash
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile
import json
p=Path('modules/services/target/distribution')
libs=sorted((p/'lib').glob('*.jar'))
names=['QueryApiMain','GraphServiceMain','SemanticServiceMain','EmbeddingWorkerMain']
with ZipFile(p/'services.jar') as jar:
 entries=set(jar.namelist())
 assert all('edu/uic/cs441/scholarchain/services/'+n+'.class' in entries for n in names)
 assert 'openapi/scholarchain.v1.yaml' in entries
assert libs
assert not any(f.name.startswith('spark-') for f in libs)
result={'dependencyJars':len(libs),'sparkDependencyJars':0,'allFourMainsPresent':True,'openApiResourcePresent':True}
Path('docs/agent-runs/phase-10/evidence/10a/distribution-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
PY
```

Exit0. Result:199 dependency JARs,0 Spark dependency JARs,all four mains and OpenAPI resource present.

## Preflight and final source audit

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git diff --check
```

Observed preflight results in preflight.json. git diff --check passed before final full gate; final repeat is recorded in final-validation.json. Source-file hashes bind the pre-gate frozen source to the final handoff. Owner reports name exact failed attempts and fixes; successful final counts do not erase prior failures.
