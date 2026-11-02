from pathlib import Path
BASE=Path('/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap')
SAFE=Path('/tmp/scholarchain-phase12d-billing-durable-plan-handoff/safe')
p=BASE/'run.py';text=p.read_text()
needle=" summary={'sanitized_at_utc':now()"
insert=''' # Compare plan-derived subscriber values in-process only. Never read private input.
 subscribers={v for n in a.get('notification',[]) for v in n.get('subscriber_email_addresses',[])}
 assert len(subscribers)==1 and all(isinstance(v,str) and v for v in subscribers)
 gitpaths=subprocess.run(['/usr/bin/git','ls-files','-co','--exclude-standard','-z'],cwd=ROOT,env={'HOME':'/Users/danny','PATH':'/usr/bin:/bin'},stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.split(b'\\0')
 matches=[];scanned=0;excluded=0
 for raw in sorted(set(gitpaths)):
  if not raw:continue
  rel=Path(os.fsdecode(raw));parts=[v.lower() for v in rel.parts]
  deny=any(v in {'.git','.aws','.ssh','.codex','.agents','.env','node_modules','target'} or v.startswith('.env.') or 'credential' in v or v in {'secrets','secret','private-keys'} for v in parts)
  allow=rel.parts[0] in {'docs','infra'} and rel.suffix.lower() in {'.md','.json','.txt','.tf','.hcl','.py','.sh','.csv','.log'}
  target=ROOT/rel
  if deny or not allow or target.is_symlink() or not target.is_file():excluded+=1;continue
  content=target.read_bytes();scanned+=1
  if any(v.encode() in content for v in subscribers):matches.append(str(rel))
 write(SAFE/'recipient-privacy-scan.json',{'timestamp_utc':now(),'scope':'Git-visible docs/ and infra/ public text, including all current phase evidence; excluded credentials/secrets/environment/private-key directories and binary/other source paths. Does not read private input.','files_scanned':scanned,'paths_excluded':excluded,'matching_file_count':len(matches),'matching_filenames':matches,'recipient_source':'new protected plan JSON notification subscribers, in-process only; no address values or private-value hashes returned','known_public_fixture':'synthetic@example.invalid in unchanged mock tests is a public fixture, not considered recipient absent proof by itself','private_input_contents_read_or_hashed':False})
 assert not matches
'''
assert text.count(needle)==1
text=text.replace(needle,insert+needle)
p.write_text(text);p.chmod(0o700);(SAFE/'run.py').write_text(text)
compile(text,str(p),'exec')
print('Public runner privacy comparison added; syntax compiled without execution.')
