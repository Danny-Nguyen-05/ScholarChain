"""Resume only final public scan/inventory after the disclosed fixture-path assertion."""
from pathlib import Path
import datetime,hashlib,json,re,subprocess
R=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
P=R/'docs/agent-runs/phase-12';E=P/'evidence/12d-billing-durable-plan'
NOW=datetime.datetime.now(datetime.timezone.utc).isoformat()
PLAN_SHA='ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=R)
previous=set((E/'preflight-status.log.txt').read_text().splitlines())
notes=json.loads((E/'coordinator-preparation-notes.json').read_text())
notes['final_public_scan_erratum']={'first_assembly_exit':1,'stage':'Public conventional-address fixture path allowlist','cause':'Three known reserved-fixture references in public runner/patch source were omitted from the allowed paths; no private recipient match or live-plan failure.','correction':'Inspect counts/domains only; all matches example.invalid, six exact known fixture source/reference paths allowed. Resume only final scan/inventory, no repeated report append/setup/test/plan.','all_public_nonfixture_matches':0}
write('coordinator-preparation-notes.json',notes)
source=(E/'assemble-final.py').read_text()
tail=source[source.index('# Conventional address scan'):]
exec(compile(tail,'assemble-final.py:public-scan-tail','exec'))
