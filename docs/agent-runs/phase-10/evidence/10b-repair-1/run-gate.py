"""Replay a local deterministic gate and retain metadata; no cloud/provider operations."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

name, *command = sys.argv[1:]
root = Path.cwd()
evidence = root / 'docs/agent-runs/phase-10/evidence/10b-repair-1'
log = Path('/tmp') / ('phase10b-r1-' + name + '.log')
env = os.environ.copy()
env['JAVA_HOME'] = '/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home'
env['PATH'] = env['JAVA_HOME'] + '/bin:' + env['PATH']
env['SBT_OPTS'] = '-Dlogback.configurationFile=' + str(root / 'docs/agent-runs/phase-04/xml-repair-logback.xml')
paths = subprocess.check_output(['git', 'ls-files', '-co', '--exclude-standard', 'modules/services', 'tests', 'build.sbt', 'project', 'Dockerfile', 'Dockerfile.dockerignore'], text=True).splitlines()
hashes = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sorted(set(paths)) if Path(p).is_file()}
(evidence / (name + '-sources.json')).write_text(json.dumps(hashes, indent=2) + '\n')
start = time.monotonic()
with log.open('wb') as output:
    result = subprocess.run(command, env=env, stdout=output, stderr=subprocess.STDOUT)
metadata = {'command': shlex.join(command), 'workingDirectory': str(root), 'environment': {k: env[k] for k in ['JAVA_HOME', 'SBT_OPTS']}, 'PATHPrefix': env['JAVA_HOME'] + '/bin', 'exitCode': result.returncode, 'elapsedSeconds': round(time.monotonic() - start, 3), 'log': str(log), 'sha256': hashlib.sha256(log.read_bytes()).hexdigest(), 'sourceHashes': name + '-sources.json'}
(evidence / (name + '-result.json')).write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
print('\n'.join(log.read_text(errors='replace').splitlines()[-70:]))
sys.exit(result.returncode)
