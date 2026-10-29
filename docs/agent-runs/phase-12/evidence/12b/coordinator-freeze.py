from pathlib import Path
import json,datetime,subprocess,hashlib,re
root=Path('/Users/danny/Documents/UIC/CS441/ScholarChain')
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--','infra/terraform'],cwd=root,text=True).splitlines()
records={}; route_locations=[]
for name in sorted(set(paths)):
 p=root/name
 assert p.is_file(),name
 assert p.name!='.env' and not p.name.endswith('.local.tfvars') and '.terraform' not in p.relative_to(root/'infra/terraform').parts,name
 assert '.tfstate' not in p.name and p.suffix not in ['.pem','.key','.tfplan'],name
 raw=p.read_bytes(); st=p.stat(); records[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns}
 if p.suffix=='.tf':
  for match in re.finditer(r'resource\s+"(aws_route|aws_route_table|aws_route_table_association|aws_default_route_table)"\s+"([^"]+)"',raw.decode()):
   route_locations.append({'path':name,'type':match.group(1),'name':match.group(2)})
assert all(x['path'].startswith('infra/terraform/modules/network/') for x in route_locations),route_locations
payload={'frozen_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base_sha':'a83f62e9af56058a170075f98c4e027d039567ec','branch':'phase-12','scope':'All git-visible infra/terraform files, including lock, README, tests and course configuration; ignored provider cache/state/plans/local tfvars excluded without reading.','file_count':len(records),'route_declarations':route_locations,'all_routes_within_network_module':True,'files':records}
p=root/'docs/agent-runs/phase-12/evidence/12b/infra-source-freeze.json';p.write_text(json.dumps(payload,indent=2)+'\n')
print(json.dumps({'freeze_path':str(p),'frozen_at_utc':payload['frozen_at_utc'],'file_count':len(records),'route_declarations':len(route_locations)}))
