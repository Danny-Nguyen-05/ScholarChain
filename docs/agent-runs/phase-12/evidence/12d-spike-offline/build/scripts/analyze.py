import json,gzip,re,glob,os,sys
from pathlib import Path
base=Path('/Users/danny/Documents/UIC/CS441/ScholarChain/target/phase12d-spike-offline');run=base/'run'
rt='/Users/danny/Documents/UIC/CS441/ScholarChain/target/phase12d-spike-offline/run/ex1/scholarchain-runtime/'
def rd(p):return gzip.open(p,'rb').read().decode('utf8','replace')
out={}
PAT=r'\[class,load\] (scala\.Predef\$|scala\.collection\.immutable\.List|org\.apache\.spark\.SparkContext) source: '
rx=re.compile(PAT)
for name in('c-classload-probe-v1','c-classload-probe-v2'):
    d=run/name;res=json.load(open(d/'result.json'));e={'grep_regex':PAT,'roles':{},'total_log_lines':0,'total_raw_bytes':0,'total_gz_bytes':0,'per_file':[]}
    for lf in res['log_files']:
        text=rd(d/lf['gz']);lines=text.split('\n')
        e['total_log_lines']+=lf['lines'];e['total_raw_bytes']+=lf['bytes'];e['total_gz_bytes']+=os.path.getsize(d/lf['gz'])
        e['per_file'].append({'file':lf['source'],'lines':lf['lines'],'raw_bytes':lf['bytes'],'gz_bytes':os.path.getsize(d/lf['gz'])})
        cl=[l for l in lines if '[class,load]' in l]
        if not cl:continue
        role='driver' if 'driver' in lf['source'] else 'executor-'+lf['source'].split('/')[2]+'-'+lf['source'].split('/')[1][-4:]
        m=[l.replace(rt,'<RUNTIME>/') for l in cl if rx.search(l)]
        # scala.* / org.apache.spark.* classes with source not under runtime jars dir 2.13 libs
        scala_cls=[l for l in cl if re.search(r'\] scala\.',l) and 'source: file:' in l]
        non_ok=[l.replace(rt,'<RUNTIME>/') for l in scala_cls if 'scala-library-2.13.14.jar' not in l and 'scala-reflect-2.13.14.jar' not in l and 'scholarchain-job.jar' not in l and 'scala-collection-compat' not in l and 'scala-parallel' not in l and 'scala-xml' not in l and 'scala-parser' not in l]
        e['roles'][role]={'class_load_lines':len(cl),'matched_lines':m,'scala_class_loads_from_file_source':len(scala_cls),'scala_loads_from_unexpected_source':non_ok[:5],'lines_mentioning__2.12':sum('2.12' in l for l in cl)}
    out[name]=e
# comparison / pipeline stats
for name in('b-compare-v1','b-compare-v1-run2'):
    r=json.load(open(run/name/'results/comparison.json'))
    out[name]={'tablesCompared':r['tablesCompared'],'allExactRowsMatch':r['allExactRowsMatch'],'tables_exact_match':sum(t['exactSchemaAndRowsMatch'] for t in r['tables']),'table_count':len(r['tables']),'provenanceNormalization':r['provenanceNormalization'],'rowCounts_sum':sum(int(t['rowCount']) for t in r['tables'])}
# auth evidence
for name in('a-probe-v2','a-probe-v1','b-g1-pipeline-v1','b-g1-pipeline-v1-run2','b-g1-pipeline-v2','b-g1-pipeline-v2-rerun'):
    d=run/name;res=json.load(open(d/'result.json'));ev={'files':{}}
    for lf in res['log_files']:
        t=rd(d/lf['gz']);ls=t.split('\n')
        ev['files'][lf['source']]={'lines':lf['lines'],'bytes':lf['bytes'],'gz_bytes':os.path.getsize(d/lf['gz']),
         'authentication_enabled_lines':sum('SecurityManager: authentication enabled' in l for l in ls),
         'AuthRpcHandler_challenges':sum('AuthRpcHandler: Received new auth challenge' in l for l in ls),
         'AuthRpcHandler_success':sum('AuthRpcHandler: Authorization successful' in l for l in ls),
         'crypto_flags_in_executor_cmd':sorted(set(re.findall(r'"-D(spark\.(?:authenticate|network\.crypto\.[A-Za-z]+|io\.encryption\.[a-z]+))=([a-z0-9]+)"',t)))}
    ev['exit']=res['exit'];ev['seconds']=res['seconds'];ev['total_lines']=sum(v['lines'] for v in ev['files'].values());ev['total_raw_bytes']=sum(v['bytes'] for v in ev['files'].values());ev['total_gz_bytes']=sum(v['gz_bytes'] for v in ev['files'].values())
    # task counts per executor for pipelines
    ev['tasks_finished_by_executor']={}
    for lf in res['log_files']:
        if 'worker' in lf['source'] and lf['source'].endswith('stderr'):
            ev['tasks_finished_by_executor'][lf['source']]=rd(d/lf['gz']).count('Finished task ')
    out['auth-'+name]=ev
json.dump(out,open(base/'analysis.json','w'),indent=1)
print(json.dumps({k:v for k,v in out.items() if not k.startswith('auth-')},indent=1)[:6000])
