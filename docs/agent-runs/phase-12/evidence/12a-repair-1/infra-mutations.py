from pathlib import Path
import subprocess, json, hashlib, tempfile, shutil, difflib
repo = Path('/Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform')
binary = '/tmp/scholarchain-phase12a-infra-toolchain/terraform'
prefix = Path('/tmp/scholarchain-phase12a-repair1-infra')
original = json.loads(Path(str(prefix) + '-baseline-hashes.json').read_text())
files = [name.removeprefix('infra/terraform/') for name in original]
before = {name: hashlib.sha256((repo/name).read_bytes()).hexdigest() for name in files}
records=[]

def run(label, command, cwd):
    result=subprocess.run(command,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=Path(str(prefix)+'-'+label+'.log');log.write_text(result.stdout)
    records.append({'label':label,'command':command,'cwd':str(cwd),'exit_code':result.returncode,'log':str(log),'sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
    Path(str(prefix)+'-mutation-manifest.json').write_text(json.dumps(records,indent=2))
    print(label,'exit',result.returncode,flush=True)
    return result

for kind in ['data-map','rogue-resource']:
    scratch=Path(tempfile.mkdtemp(prefix='scholarchain-phase12a-repair1-infra-'+kind+'-',dir='/tmp'))
    for name in files:
        target=scratch/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(repo/name,target)
    (scratch/'.terraform').mkdir()
    (scratch/'.terraform/providers').symlink_to(repo/'.terraform/providers',target_is_directory=True)
    if kind=='data-map':
        path=scratch/'modules/network/main.tf'; old=path.read_text()
        needle='  default_routes = {\n';assert old.count(needle)==1
        injected='''    data_mutation = {
      route_table_id = aws_route_table.data.id
      gateway_id     = null
      nat_gateway_id = aws_nat_gateway.course.id
    }
'''
        new=old.replace(needle,needle+injected);path.write_text(new)
        diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='repaired/modules/network/main.tf',tofile='mutated/modules/network/main.tf'))
        expected='data subnets have no default route'
    else:
        name='modules/network/rogue.tf'
        new='''# Intentional negative mutation outside the repository.
resource "aws_route" "rogue_data_default" {
  route_table_id         = aws_route_table.data.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.course.id
}
'''
        (scratch/name).write_text(new)
        diff=''.join(difflib.unified_diff([],new.splitlines(True),fromfile='/dev/null',tofile='mutated/'+name))
        expected='single aws_route.default collection'
    Path(str(prefix)+'-mutation-'+kind+'.patch').write_text(diff)
    initialized=run('mutation-'+kind+'-init',[binary,'init','-backend=false','-input=false','-no-color'],scratch)
    assert initialized.returncode==0
    test=run('mutation-'+kind+'-test',[binary,'test','-no-color'],scratch)
    assert test.returncode==1 and expected in ' '.join(test.stdout.split()) and 'Failure! 12 passed, 1 failed.' in test.stdout
    print(kind,'negative assertion observed; scratch root',scratch,flush=True)

after={name:hashlib.sha256((repo/name).read_bytes()).hexdigest() for name in files}
assert before==after
Path(str(prefix)+'-mutation-source-unchanged.json').write_text(json.dumps({'repo_source_unchanged':True,'files_compared':len(files),'sha256':after},indent=2))
print('Repository41-file snapshot unchanged by isolated negative experiments.',flush=True)
