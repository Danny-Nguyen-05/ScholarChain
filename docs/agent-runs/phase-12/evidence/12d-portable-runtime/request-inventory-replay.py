"""Offline conditional artifact-transfer arithmetic, not an AWS request limiter."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parent
PART=64*1024*1024

def transfer(size,consumers=2,attempts=1,read_strategy="whole_object"):
    if type(size) is not int or size<=0:raise ValueError('POSITIVE_BYTE_SIZE_REQUIRED')
    if type(consumers) is not int or consumers<0:raise ValueError('NONNEGATIVE_CONSUMERS_REQUIRED')
    if type(attempts) is not int or not 1<=attempts<=3:raise ValueError('ATTEMPT_SCENARIO_OUT_OF_RANGE')
    if read_strategy not in ['whole_object','64MiB_ranges']:raise ValueError('READ_STRATEGY_REQUIRED')
    parts=(size+PART-1)//PART if size>PART else 0
    upload=parts+2 if parts else 1
    # One post-upload HEAD and streaming audit GET; consumers use the explicit strategy.
    download_parts=(size+PART-1)//PART if read_strategy=='64MiB_ranges' else 1
    reads=2+consumers*(1+download_parts)
    return {'bytes':size,'read_strategy':read_strategy,'consumer_get_requests_each':download_parts,'multipart_parts':parts,'successful_upload_api_units':upload,
            'successful_get_head_units':reads,'conditional_upload_units':upload*attempts,
            'conditional_get_head_units':reads*attempts,'max_attempts_scenario':attempts}

def checks():
    assert transfer(1)['successful_upload_api_units']==1
    assert transfer(PART)['multipart_parts']==0
    assert transfer(PART+1)['multipart_parts']==2
    assert transfer(PART+1)['successful_upload_api_units']==4
    assert transfer(7*PART)['multipart_parts']==7
    assert transfer(1,0)['successful_get_head_units']==2
    assert transfer(1,2,3)['conditional_get_head_units']==18
    assert transfer(PART+1,2,3)['conditional_upload_units']==12
    assert transfer(PART+1,2,1,'64MiB_ranges')['successful_get_head_units']==8
    assert transfer(5*PART,2,3,'64MiB_ranges')['conditional_get_head_units']==42
    try:transfer(1,2,1,'unknown')
    except ValueError:pass
    else:raise AssertionError('unsupported read strategy accepted')
    for bad in [0,-1,False,'1',None]:
        try:transfer(bad)
        except ValueError:pass
        else:raise AssertionError('bad size accepted')
    for bad in [0,4,False]:
        try:transfer(1,2,bad)
        except ValueError:pass
        else:raise AssertionError('unbounded retry accepted')
    return {'boundary_and_invalid_input_checks':'passed','checks_are_local_only':True}

def build():
    inputs=json.loads((ROOT/'staging-object-inputs.json').read_text())
    rows=[]
    for obj in inputs['objects']:
        if obj['status']=='measured':
            path=Path(obj['local_path']);digest=hashlib.sha256();size=0
            with path.open('rb') as stream:
                for chunk in iter(lambda:stream.read(2*1024*1024),b''):
                    size+=len(chunk);digest.update(chunk)
            assert size==obj['bytes'] and digest.hexdigest()==obj['sha256']
        for attempts,strategy in [(1,'whole_object'),(3,'whole_object'),(1,'64MiB_ranges'),(3,'64MiB_ranges')]:
            rows.append({'object_id':obj['object_id'],'status':obj['status'],
                         'staging_variant':obj['staging_variant'],**transfer(obj['bytes'],obj['planned_consumers'],attempts,strategy)})
    variants={}
    for variant in ['single_runtime_archive','runtime_plus_optional_yarn_archive']:
        selected=[o for o in inputs['objects'] if o['staging_variant'] in ['both',variant]]
        variants[variant]={'unique_object_bytes_once':sum(o['bytes'] for o in selected),
            'measured_object_bytes':sum(o['bytes'] for o in selected if o['status']=='measured'),
            'unimplemented_reservation_bytes':sum(o['bytes'] for o in selected if o['status']!='measured'),
            'object_count':len(selected),'upload_api_units_one_success':sum(transfer(o['bytes'],o['planned_consumers'])['successful_upload_api_units'] for o in selected),
            'get_head_units_one_success':sum(transfer(o['bytes'],o['planned_consumers'])['successful_get_head_units'] for o in selected),
            'upload_api_units_three_attempt_scenario':sum(transfer(o['bytes'],o['planned_consumers'],3)['conditional_upload_units'] for o in selected),
            'get_head_units_three_attempt_scenario':sum(transfer(o['bytes'],o['planned_consumers'],3)['conditional_get_head_units'] for o in selected),
            'ranged_get_head_units_one_success':sum(transfer(o['bytes'],o['planned_consumers'],1,'64MiB_ranges')['conditional_get_head_units'] for o in selected),
            'ranged_get_head_units_three_attempt_scenario':sum(transfer(o['bytes'],o['planned_consumers'],3,'64MiB_ranges')['conditional_get_head_units'] for o in selected),
            'storage_bytes_times_three_whole_object_replays_sensitivity':3*sum(o['bytes'] for o in selected),
            'storage_complete':False,'request_total_complete':False,'selected':False}
    return {'objects':rows,'variants':variants,'transfer_assumptions':'64MiB multipart threshold/part size; one upload HEAD+streaming auditGET and one HEAD plus whole-objectGET or64MiB-rangeGETs per listed consumer; 1 and3 per-API attempts are scenarios, not implemented limits. No new whole-object restart assumed in request rows. Whole-object3x storage sensitivity is separate. Abort/list/copy/cleanup/provider/logging/KMS need additional inventory.',
        'whole_attempt_put_list_upper_bound':None,'whole_attempt_get_head_upper_bound':None,
        'whole_attempt_kms_upper_bound':None,'lower_request_candidate_selected':False,
        'lower_request_candidate_proven':False,'launch_cost_fit_verified':False,'launch_authorized':False,
        'unbounded_or_unimplemented':['EMR/bootstrap/dependency download and log object creation/rotation','Lease/heartbeat/guard/cleanup request implementation and failure branches','Multipart abort/list/ambiguous completion/replay handling and retention of versions','Archive size and integrity readback, retained logs and evidence','SDK/service retry and pagination limits, GET range sizes and repeated/speculative opens','SSE-KMS multipart/auxiliary operation counts and EFS/EBS grants','TLS input/metadata actual bytes and protected delivery','HDFS/YARN staging route and additional archive duplication']}

if __name__=='__main__':
    check=checks()
    if sys.argv[1:]==['--self-test']:print(json.dumps(check,sort_keys=True))
    else:
        assert not sys.argv[1:]
        result=build();print(json.dumps(result,indent=2,sort_keys=True))
