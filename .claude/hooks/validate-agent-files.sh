#!/usr/bin/env bash
set -euo pipefail
root=${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
if [[ -f "$root/.claude/settings.json" ]]; then jq empty "$root/.claude/settings.json"; fi
if [[ -f "$root/.mcp.json" ]]; then jq empty "$root/.mcp.json"; fi
if [[ -f "$root/.claude/ownership-audit.json" ]]; then jq empty "$root/.claude/ownership-audit.json"; fi
for hook in "$root"/.claude/hooks/*.sh; do
  [[ -e "$hook" ]] || continue
  bash -n "$hook"
  [[ -x "$hook" ]] || { echo "Agent validation failed: $hook is not executable" >&2; exit 2; }
done
if ! python3 - "$root" <<'PY'
from pathlib import Path
from fnmatch import fnmatchcase
import json, re, sys
root=Path(sys.argv[1])
files=sorted((root/'.claude/agents').glob('*.md'))
names=[]
required=['name', 'description', 'tools']
for path in files:
    content=path.read_text()
    match=re.match(r'\A---\n(.*?)\n---\n', content, re.S)
    if not match:
        raise SystemExit(f'{path}: missing YAML frontmatter')
    fields={}
    for line in match.group(1).splitlines():
        if ':' not in line:
            raise SystemExit(f'{path}: malformed frontmatter line')
        key,value=line.split(':',1)
        fields[key.strip()]=value.strip()
    for key in required:
        if not fields.get(key):
            raise SystemExit(f'{path}: missing {key}')
    name=fields['name']
    if name != path.stem or not re.fullmatch(r'[a-z][a-z0-9-]*',name):
        raise SystemExit(f'{path}: invalid or mismatched name')
    names.append(name)
    tools={item.strip() for item in fields['tools'].split(',')}
    if name=='code-reviewer' and tools != {'Read','Grep','Glob'}:
        raise SystemExit('code-reviewer must have only Read, Grep, Glob')
    if name=='test-engineer' and not {'Write','Edit'} <= tools:
        raise SystemExit('test-engineer must have test authoring tools')
if len(names)!=len(set(names)):
    raise SystemExit('duplicate agent names')
expected={'factory-engineer','build-engineer','domain-engineer','dataset-engineer','hadoop-engineer','entity-resolution-engineer','spark-engineer','storage-engineer','rag-engineer','service-engineer','test-engineer','code-reviewer','infra-engineer','deploy-engineer','experiment-engineer','documentation-engineer','incident-responder','dependency-updater'}
if set(names)!=expected:
    raise SystemExit(f'agent catalog mismatch: missing={expected-set(names)}, extra={set(names)-expected}')
audit=json.loads((root/'.claude/ownership-audit.json').read_text())
settings=json.loads((root/'.claude/settings.json').read_text())
if not settings.get('permissions',{}).get('allow') or not settings.get('permissions',{}).get('deny'):
    raise SystemExit('settings permission allow/deny lists are required')
hooks=settings.get('hooks',{})
for event,script in [('PreToolUse','guard-dangerous.sh'),('PostToolUse','format-scala.sh'),('PostToolUse','validate-agent-files.sh'),('Stop','verify-tests-ran.sh')]:
    commands=[h.get('command','') for group in hooks.get(event,[]) for h in group.get('hooks',[])]
    if not any(script in command for command in commands):
        raise SystemExit(f'{event} missing {script}')
if set(audit['patterns']) != expected or set(audit['routes'].values()) != expected:
    raise SystemExit('ownership patterns or lifecycle routes omit an agent')
doc=(root/'docs/agents.md').read_text()
table=doc.split('## Artifact ownership',1)[1].split('## Lifecycle routing',1)[0]
table_names=re.findall(r'^\| `([a-z][a-z0-9-]+)` \|', table, re.M)
if len(table_names)!=len(expected) or set(table_names)!=expected:
    raise SystemExit('docs/agents.md ownership table is missing or duplicating roles')
for path,want in audit['samples'].items():
    owners=[]
    for owner,patterns in audit['patterns'].items():
        if any(fnmatchcase(path,p) for p in patterns) and not any(fnmatchcase(path,p) for p in audit.get('exclusions',{}).get(owner,[])):
            owners.append(owner)
    if owners != [want]:
        raise SystemExit(f'ownership collision/orphan at {path}: expected {want}, got {owners}')
for owner in expected:
    if f'`{owner}`' not in doc:
        raise SystemExit(f'docs/agents.md missing route for {owner}')
print(f'Validated {len(names)} unique agents, reviewer fence, {len(audit["samples"])} representative ownership paths and {len(audit["routes"])} routes')
PY
then
  exit 2
fi
