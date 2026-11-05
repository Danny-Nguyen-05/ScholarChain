from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, signal, subprocess, sys, time

os.umask(0o077)
repo = Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
root = repo / 'target/phase12d-readiness-20261103'
runtime = root / 'runtime'
manifest = json.loads((runtime / 'runtime-manifest.json').read_text())
job = Path(manifest['job_jar']['path'])
job_sha = manifest['job_jar']['sha256']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(job) == job_sha
cp = (runtime / 'driver-classpath.txt').read_text().strip()
assert cp.split(os.pathsep)[0] == str(job)
assert all(Path(p).is_file() and Path(p).suffix == '.jar' for p in cp.split(os.pathsep))
java_home = '/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home'
env = {'HOME': '/Users/danny', 'USER': 'danny', 'LOGNAME': 'danny',
       'PATH': java_home + '/bin:/usr/bin:/bin', 'JAVA_HOME': java_home,
       'TMPDIR': '/private/tmp', 'LANG': 'en_US.UTF-8',
       'SPARK_LOCAL_IP': '127.0.0.1', 'SPARK_LOCAL_HOSTNAME': '127.0.0.1',
       'AWS_EC2_METADATA_DISABLED': 'true'}
modules = ['java.base/java.lang', 'java.base/java.lang.invoke', 'java.base/java.lang.reflect',
           'java.base/java.io', 'java.base/java.net', 'java.base/java.nio', 'java.base/java.util',
           'java.base/java.util.concurrent', 'java.base/java.util.concurrent.atomic',
           'java.base/jdk.internal.ref', 'java.base/sun.nio.ch', 'java.base/sun.nio.cs',
           'java.base/sun.security.action', 'java.base/sun.util.calendar',
           'java.security.jgss/sun.security.krb5']
common = [java_home + '/bin/java', '-Xmx2g'] + ['--add-opens=' + m + '=ALL-UNNAMED' for m in modules] + [
    '-Djava.net.preferIPv4Stack=true', '-Dspark.ui.enabled=false', '-Dspark.master=local[2]',
    '-Dspark.driver.host=127.0.0.1', '-Dspark.driver.bindAddress=127.0.0.1',
    '-Dspark.hadoop.fs.defaultFS=file:///', '-Dspark.task.maxFailures=1', '-cp', cp]
stage = sys.argv[1]
assert stage in ('baseline-a', 'baseline-b', 'compare', 'probe-local', 'probe-local-negative')
attempt = sys.argv[2] if len(sys.argv) == 3 else 'attempt1'
assert attempt in ('attempt1', 'attempt2')
run_label = stage + '-' + attempt
timeout = 600
expected_exit = 0
output = None
def completed(label):
    config = json.loads((root / 'config' / ('spark-g1-' + label + '.json')).read_text())
    candidates = list(Path(config['outputRoot']).glob('*/_SCHOLARCHAIN_SPARK_COMPLETE'))
    assert len(candidates) == 1, (label, candidates)
    return candidates[0].parent
if stage.startswith('baseline-'):
    label = stage[-1]
    config = root / 'config' / ('spark-g1-' + label + '.json')
    config_data = json.loads(config.read_text())
    destination = Path(config_data['outputRoot'])
    assert not destination.exists(), 'Refuse run reuse or overwrite'
    cmd = common + ['edu.uic.cs441.scholarchain.spark.Phase6Main', str(config)]
elif stage == 'compare':
    output = root / 'baseline' / 'exact-comparison.json'
    assert not output.exists()
    cmd = common + ['edu.uic.cs441.scholarchain.spark.Phase12Readiness', 'compare',
                    str(completed('a')), str(completed('b')), str(output)]
else:
    timeout = 180
    shared = root / 'probe' / stage
    shared.mkdir(mode=0o700)
    output = root / 'probe' / (stage + '.json')
    assert not output.exists()
    negative = stage.endswith('negative')
    expected_exit = 2 if negative else 0
    cmd = common + ['edu.uic.cs441.scholarchain.spark.Phase12Readiness', 'probe', str(shared),
                    str(output), 'distributed' if negative else 'local']
logs = root / 'logs'
command_path = logs / (run_label + '-command.json')
with command_path.open('x') as f:
    json.dump({'stage': stage, 'command': cmd, 'cwd': str(repo), 'environment': env,
               'job_jar_sha256': job_sha, 'timeout_seconds': timeout,
               'expected_exit': expected_exit, 'started_at': datetime.now(timezone.utc).isoformat()},
              f, indent=2, sort_keys=True)
    f.write('\n')
started = time.monotonic()
actions = []
timed_out = False
with (logs / (run_label + '.stdout.txt')).open('xb') as out, (logs / (run_label + '.stderr.txt')).open('xb') as err:
    process = subprocess.Popen(cmd, cwd=repo, env=env, stdout=out, stderr=err, start_new_session=True)
    try:
        code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        for sig, grace in ((signal.SIGINT, 15), (signal.SIGTERM, 10), (signal.SIGKILL, 5)):
            try:
                os.killpg(process.pid, sig)
                actions.append(signal.Signals(sig).name + ' to owned process group')
            except ProcessLookupError:
                break
            try:
                process.wait(timeout=grace)
                break
            except subprocess.TimeoutExpired:
                pass
        process.wait()
        code = 124
result = {'stage': stage, 'attempt': attempt, 'exit': code, 'expected_exit': expected_exit, 'timed_out': timed_out,
          'seconds': round(time.monotonic() - started, 3), 'cleanup': actions,
          'job_jar_sha256_before': job_sha, 'job_jar_sha256_after': sha(job),
          'completed_at': datetime.now(timezone.utc).isoformat(), 'AWS_calls': 0}
if output is not None:
    result['output_exists'] = output.is_file()
    if output.is_file():
        result['output_sha256'] = sha(output)
if code == 0 and stage.startswith('baseline-'):
    run = completed(stage[-1])
    result['completed_run'] = str(run)
    data = json.loads((run / 'run-metadata.json').read_text())
    result['run_id'] = data['runId']
    result['code_version'] = data['codeVersion']
    result['table_count'] = len(data['tables'])
    assert result['table_count'] == 28
if code == 0 and stage == 'compare':
    data = json.loads(output.read_text())
    assert data['tablesCompared'] == 28 and data['allExactRowsMatch'] is True
    assert data['provenanceNormalization'] == 'none' and data['cloudCompatibilityVerified'] is False
if stage == 'probe-local' and code == 0:
    data = json.loads(output.read_text())
    assert data['driverToTaskAndBackVerified'] is True and data['externalExecutorVerified'] is False
if stage == 'probe-local-negative' and code == expected_exit:
    assert not output.exists()
assert result['job_jar_sha256_after'] == job_sha
with (logs / (run_label + '-result.json')).open('x') as f:
    json.dump(result, f, indent=2, sort_keys=True)
    f.write('\n')
print(json.dumps(result, sort_keys=True))
print('\n'.join((logs / (run_label + '.stdout.txt')).read_text(errors='replace').splitlines()[-4:]))
if code != expected_exit:
    print('\n'.join((logs / (run_label + '.stderr.txt')).read_text(errors='replace').splitlines()[-30:]))
sys.exit(0 if code == expected_exit and not timed_out else 1)
