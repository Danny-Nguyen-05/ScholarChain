from pathlib import Path
import urllib.request,hashlib,zipfile,json,datetime,subprocess,os
r=Path('/tmp/scholarchain-phase12b-repair1-infra');repo=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--','infra/terraform'],cwd=repo,text=True).splitlines()
(r/'pre-repair-source.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in paths}},indent=2)+'\n')
(r/'pre-repair-copies').mkdir(exist_ok=True)
for p in ['README.md','modules/identity/main.tf','tests/phase12b.tftest.hcl']:
 d=r/'pre-repair-copies'/p;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes((repo/'infra/terraform'/p).read_bytes())
retained=repo/'docs/agent-runs/phase-12/evidence/12a/terraform-1.13.5-official-checksums.txt'
expected=[line.split()[0] for line in retained.read_text().splitlines() if line.endswith('terraform_1.13.5_darwin_arm64.zip')][0]
url='https://releases.hashicorp.com/terraform/1.13.5/terraform_1.13.5_darwin_arm64.zip';raw=urllib.request.urlopen(url,timeout=45).read();actual=hashlib.sha256(raw).hexdigest();assert actual==expected
(r/'terraform_1.13.5_darwin_arm64.zip').write_bytes(raw)
with zipfile.ZipFile(r/'terraform_1.13.5_darwin_arm64.zip') as z:z.extract('terraform',r)
(r/'terraform').chmod(0o755)
origin=repo/'infra/terraform/.terraform/providers/registry.terraform.io/hashicorp/aws/6.44.0/darwin_arm64';mirror=r/'mirror/registry.terraform.io/hashicorp/aws/6.44.0/darwin_arm64';mirror.mkdir(parents=True,exist_ok=True)
pins=json.loads((repo/'docs/agent-runs/phase-12/evidence/12b/infra/mirror-provenance.json').read_text())
for name,digest in pins['package_files'].items():
 src=origin/name;assert hashlib.sha256(src.read_bytes()).hexdigest()==digest;os.link(src,mirror/name)
(r/'terraformrc').write_text('provider_installation {\n filesystem_mirror {\n path = "/tmp/scholarchain-phase12b-repair1-infra/mirror"\n include = ["registry.terraform.io/hashicorp/aws"]\n }\n}\n')
(r/'toolchain-provenance.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'download_url':url,'zip_sha256':actual,'retained_checksums':str(retained),'verified_against_retained_sha256':True,'terraform_binary':str(r/'terraform'),'binary_sha256':hashlib.sha256((r/'terraform').read_bytes()).hexdigest(),'provider_package':pins['package_files'],'provider_source':str(origin),'mirror':str(mirror),'cli_config':str(r/'terraformrc'),'signature_verification':'No new detached signature verification; exact official ZIP SHA verified against retained official checksums.'},indent=2)+'\n')
print('Verified Terraform ZIP',actual,'and full installed provider package')
