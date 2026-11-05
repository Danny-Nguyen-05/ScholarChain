import hashlib,json,os
base='/Users/danny/Documents/UIC/CS441/ScholarChain/target/phase12d-spike-offline'
rows=[]
for dp,dn,fs in os.walk(base):
    rel=os.path.relpath(dp,base);top=rel.split(os.sep)
    if top[0]=='run' and len(top)>=2 and top[1]=='ex1': continue
    if len(top)>=3 and top[0]=='run' and top[2] in('worker','shared','logs'): continue
    for f in sorted(fs):
        p=os.path.join(dp,f)
        if f=='manifest.json' and dp==base: continue
        rows.append({'path':os.path.relpath(p,base),'bytes':os.path.getsize(p),'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest()})
rows.sort(key=lambda r:r['path'])
json.dump({'root':base,'excluded':['run/ex1 (extracted runtime, inputs, outputs, checkpoints)','run/*/worker','run/*/shared','run/*/logs (raw; raw sha256 of each is in run/*/result.json)'],'files':rows},open(base+'/manifest.json','w'),indent=1)
print(len(rows))
