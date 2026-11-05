from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
root=Path(__file__).resolve().parent
manifest=json.loads((root/'fetch-manifest.json').read_text())
selection={
 'neptune_ncu_hour':('AmazonNeptune','QC8EC7ZYDYBWBU3T',0),
 'neptune_storage_gb_month':('AmazonNeptune','6V74JSENRBJPG93S',0),
 'neptune_io_request':('AmazonNeptune','6URG58RTY9NXZCYD',0),
 'neptune_extra_backup_gb_month':('AmazonNeptune','HF6X772NY7ZUV593',0),
 'fargate_vcpu_hour':('AmazonECS','UGSJ89BUWB7SMJ6A',0),
 'fargate_gib_hour':('AmazonECS','HH5EE3ZFWSFKGKWM',0),
 'fargate_extra_ephemeral_gb_hour':('AmazonECS','WMTNJTQ9TGJXSFMD',0),
 'ipv4_address_hour':('AmazonVPC','8HFJK44D9234XNWA',0),
 'interface_endpoint_az_hour':('AmazonVPC','P2Q7Y6KZKKFAHEVG',0),
 'alb_hour':('AWSELB','HCVPZW9WEWSJKJWJ',0),
 'alb_lcu_hour':('AWSELB','S3YDM2U7G69S4W5C',0),
 'kms_key_month':('awskms','FEMX7ZQ4DJ6QE2KP',0),
 'kms_request':('awskms','9XXHSZC4PS7S6AY2',0),
 'cloudwatch_dashboard_month':('AmazonCloudWatch-global','8AWBXE5MPQY58BK4',0),
 'cloudwatch_alarm_metric_month':('AmazonCloudWatch','28VSMYRVQXUWCTMA',0),
 'cloudwatch_custom_metric_month':('AmazonCloudWatch','XK7C3D2X45XTHURD',0),
 'cloudwatch_log_ingest_gb':('AmazonCloudWatch','5T6Z6V26DSR7SZ49',0),
 'cloudwatch_log_storage_gb_month':('AmazonCloudWatch','X7X4WD4A95NDR9U5',0),
 'secret_month':('AWSSecretsManager','HHK3AZN6HN5CFDJM',0),
 'secret_api_request':('AWSSecretsManager','DYZUZWKV5HMGF5A9',0),
 'ddb_read_request_unit':('AmazonDynamoDB','SGMZJPDKSWXTY4VE',0),
 'ddb_write_request_unit':('AmazonDynamoDB','GGQSXTNTRBHRVS56',0),
 'ddb_storage_gb_month':('AmazonDynamoDB','GAHPNMT39TQ47AGG',1),
 'ddb_pitr_gb_month':('AmazonDynamoDB','SU36MES57K2M6EHQ',0),
 's3_storage_gb_month':('AmazonS3','YPGKVRB2EKTVDJDT',0),
 's3_put_request':('AmazonS3','GJKK9PMSTKPNGZS9',0),
 's3_get_request':('AmazonS3','DJEKB32FV4HNZJZY',0),
 'vector_storage_gb_month':('AmazonS3','DGQAYZ94M98HQY77',0),
 'vector_put_gb':('AmazonS3','QUAQMNUMK6J55Y4H',0),
 'vector_query_request':('AmazonS3','UX4H9YPUSP929HF4',0),
 'vector_query_processed_gb_tier1':('AmazonS3','EHQCKQFCGZYFW8SD',0),
 'vector_query_returned_gb':('AmazonS3','MDS2AY42EMRU72QN',0),
 'vector_tier1_api_request':('AmazonS3','4558H4264VCE5SZJ',0),
 'sqs_standard_request':('AWSQueueService','9C8YFGPNBKF9HP9A',0),
 'sfn_standard_transition':('AmazonStates','PEWNRD5EMPQPHCAQ',0),
 'cloudmap_resource_month':('AWSCloudMap','MRXRZ96N867Z6Z52',0),
 'cloudmap_api_request':('AWSCloudMap','XCK55FWSY36JXPWF',0),
 'route53_hosted_zone_month':('AmazonRoute53-global','KVPGEJE88UW8S779',0),
 'ecr_storage_gb_month':('AmazonECR','NA4VZMZUEQGMXP2Y',0),
 'titan_v2_per_1000_input_tokens':('AmazonBedrock','73TWNPGDKBFY3XAT',0),
 'emr_m5_xlarge_surcharge_hour':('ElasticMapReduce','VXMPRBP5JU7WEE96',0),
 'emr_m5_2xlarge_surcharge_hour':('ElasticMapReduce','E9HZ236MUUBMR8U2',0),
}
rates={};curated=[]
existing = {x['rate_name']: x for x in json.loads((root/'curated-price-evidence.json').read_text())} if (root/'curated-price-evidence.json').exists() else {}
for name,(service,sku,idx) in selection.items():
 if not (root/f'{service}.json').exists():
  assert name in existing, f'Missing curated rate: {name}'
  rates[name]=existing[name]['usd'];curated.append(existing[name]);continue
 d=json.loads((root/f'{service}.json').read_text());p=d['products'][sku]
 dims=[r for t in d['terms']['OnDemand'][sku].values() for r in t['priceDimensions'].values()]
 r=dims[idx]; rates[name]=float(r['pricePerUnit']['USD'])
 source=next(x for x in reversed(manifest) if x['service']==service and 'sha256' in x)
 curated.append({'rate_name':name,'usd':rates[name],'unit':r['unit'],'sku':sku,'attributes':p['attributes'],'rate_dimension':r,'source_url':source['url'],'source_sha256':source['sha256'],'retrieved_utc':source['retrieved_utc'],'catalog_version':d.get('version'),'publication_date':d.get('publicationDate')})
rates.update(nat_gateway_hour=.045,nat_processed_gb=.045,cost_explorer_primary_view_api_request=.01)
curated += [{'rate_name':'nat_gateway_hour','usd':.045,'unit':'hour','source_url':'https://aws.amazon.com/vpc/pricing/','source_basis':'Ohio worked pricing example, checked through web tool 2026-10-30'}, {'rate_name':'nat_processed_gb','usd':.045,'unit':'GB','source_url':'https://aws.amazon.com/vpc/pricing/','source_basis':'Ohio worked pricing example, checked through web tool 2026-10-30'},{'rate_name':'cost_explorer_primary_view_api_request','usd':.01,'unit':'request/page','source_url':'https://aws.amazon.com/aws-cost-management/aws-cost-explorer/pricing/','source_basis':'Official public pricing page checked through web tool 2026-10-30'}]
for entry in curated:
 if 'rate_dimension' in entry: entry['rate_dimension'].pop('description',None)
(root/'curated-price-evidence.json').write_text(json.dumps(curated,indent=2)+'\n')
windows=[{'name':'base','start_cst':'2026-11-15T00:00:00-06:00','end_cst':'2026-11-24T23:00:00-06:00','hours':239},{'name':'upper_duration','start_cst':'2026-11-11T00:00:00-06:00','end_cst':'2026-11-24T23:00:00-06:00','hours':335}]
# Non-zero variable usage is an explicit illustrative workload, never an observed run or an approval.
assumptions={'pricing_month_hours':720,'full_month_fixed_allowance':{'one_kms_key':1,'one_dashboard':3,'five_standard_alarm_metric_equivalents':.5,'one_private_hosted_zone':.5},'nat_processed_gb':10,'s3_gb_including_versions':10,'s3_puts':20000,'s3_gets':100000,'ecr_gb':4,'ddb_total_gb_including_gsi':1,'ddb_read_units':100000,'ddb_write_units':100000,'log_ingested_gb':1,'max_log_storage_gb':1,'active_custom_and_container_metric_equivalents':80,'secrets_count':4,'secret_api_requests':10000,'kms_requests':100000,'vector_storage_gb':.1,'vector_put_gb':.1,'vector_query_requests':10000,'vector_query_processed_gb_total':10000,'vector_query_returned_gb_total':1,'vector_tier1_control_requests':1000,'sqs_requests':100000,'sfn_transitions':10000,'titan_v2_input_tokens':10000000,'neptune_storage_gb':1,'neptune_io_requests':1000000,'neptune_extra_backup_gb':1,'alb_lcu_average':1,'alb_public_ipv4_minimum':2,'http_cloudmap_resources_min':3,'http_cloudmap_resources_max':6,'cloudmap_api_requests':10000,'additional_full_month_s3_retention_gb':10,'additional_full_month_vector_retention_gb':.1,'additional_full_month_kms_key':1,'additional_full_month_ecr_retention_gb':4,'emr_all_spikes_experiments_provisional_reserve':15,'synthesis_9c_15_16_provisional_reserve':20,'unreported_usage_tax_and_other_uncertainty_reserve':20}
results=[]
for w in windows:
 h=w['hours'];m=h/720
 assert (datetime.fromisoformat(w['end_cst'])-datetime.fromisoformat(w['start_cst'])).total_seconds()/3600==h
 a=assumptions
 fixed_primary={'nat_gateway':h*rates['nat_gateway_hour'],'nat_eip':h*rates['ipv4_address_hour'],'full_month_key_dashboard_alarm_zone_allowance':sum(a['full_month_fixed_allowance'].values())}
 primary_illustrative={'nat_data':10*rates['nat_processed_gb'],'s3_storage':10*m*rates['s3_storage_gb_month'],'s3_requests':20000*rates['s3_put_request']+100000*rates['s3_get_request'],'ecr_storage':4*m*rates['ecr_storage_gb_month'],'ddb_storage_pitr':m*(rates['ddb_storage_gb_month']+rates['ddb_pitr_gb_month']),'ddb_requests':100000*(rates['ddb_read_request_unit']+rates['ddb_write_request_unit']),'log_ingest_storage':rates['cloudwatch_log_ingest_gb']+m*rates['cloudwatch_log_storage_gb_month'],'kms_requests':100000*rates['kms_request'],'vector_workload':.1*m*rates['vector_storage_gb_month']+.1*rates['vector_put_gb']+10000*rates['vector_query_request']+10000*rates['vector_query_processed_gb_tier1']+rates['vector_query_returned_gb']+1000*rates['vector_tier1_api_request'],'sqs':100000*rates['sqs_standard_request'],'sfn':10000*rates['sfn_standard_transition']}
 active_variables={'80_metric_equivalents':80*m*rates['cloudwatch_custom_metric_month'],'four_secrets_full_month_allowance':4*rates['secret_month'],'secret_requests':10000*rates['secret_api_request'],'cloudmap_api':10000*rates['cloudmap_api_request'],'neptune_storage_io_extra_backup':m*(rates['neptune_storage_gb_month']+rates['neptune_extra_backup_gb_month'])+1000000*rates['neptune_io_request'],'titan_10m_tokens':10000000/1000*rates['titan_v2_per_1000_input_tokens']}
 activated={}
 for label,ncu,tasks,cm_resources in [('minimum',1,4,3),('sustained_authored_maximum',2.5,10,6)]:
  fixed_active={'neptune_compute':ncu*h*rates['neptune_ncu_hour'],'fargate_compute':tasks*h*(.5*rates['fargate_vcpu_hour']+rates['fargate_gib_hour']),'alb_plus_one_lcu_plus_two_ipv4':h*(rates['alb_hour']+rates['alb_lcu_hour']+2*rates['ipv4_address_hour']),'cloudmap_resource_full_month_allowance':cm_resources*rates['cloudmap_resource_month']}
  base_subtotal=sum(fixed_primary.values())+sum(fixed_active.values())
  workload_subtotal=sum(primary_illustrative.values())+sum(active_variables.values())
  retention=10*rates['s3_storage_gb_month']+.1*rates['vector_storage_gb_month']+rates['kms_key_month']+4*rates['ecr_storage_gb_month']
  reserves=15+20+20
  activated[label]={'ncu':ncu,'fargate_tasks':tasks,'fixed_active':fixed_active,'fixed_primary_plus_active_subtotal':base_subtotal,'illustrative_usage_total':workload_subtotal,'one_extra_month_retention_allowance':retention,'unpriced_approved_run_and_uncertainty_reserves':{'emr':15,'synthesis':20,'unreported_tax_other':20},'total_with_illustrative_usage_retention_and_reserves':base_subtotal+workload_subtotal+retention+reserves,'headroom_against_200':200-(base_subtotal+workload_subtotal+retention+reserves),'within_200_under_assumptions':base_subtotal+workload_subtotal+retention+reserves<=200}
 results.append({'window':w,'primary_fixed_allowance':fixed_primary,'primary_zero_workload_subtotal':sum(fixed_primary.values()),'primary_illustrative_usage':primary_illustrative,'primary_with_illustrative_usage':sum(fixed_primary.values())+sum(primary_illustrative.values()),'active_illustrative_usage':active_variables,'activated':activated,'one_additional_interface_service_two_az_cost_excluding_data':h*2*rates['interface_endpoint_az_hour']})
output={'calculated_utc':datetime.now(timezone.utc).isoformat(),'region':'us-east-2','currency':'USD','budget_before_credits':200,'actual_spend_verified':False,'rates':rates,'assumptions':assumptions,'results':results,'caveats':['No costs are observed account charges. No AWS account or paid API was queried.','Full-month key/dashboard/alarm/zone allowances are conservative reservations; actual prorating/free allowances may reduce bills. Other storage/metric estimates use720h/month for comparison; actual calendar proration can differ.','Fixed primary shape has Neptune/EMR/runtime disabled but still creates NAT/EIP, Cloud Map private namespace, dashboard/alarms, CMK and empty stores.','Illustrative workload counts are modeling assumptions, not approved live caps or feature readiness.','Unknown actual baseline spend, tax, transfer volume, LCU/load/IP scaling, telemetry cardinality, runtime/synthesis model, EMR compatibility and unreported billing prevent a verified fit.','EMR reserve is provisional, not a priced runtime: EMR m5.xlarge surcharge0.048/h plus EC2 price and EBS. Underlying EC2/EBS prices were not independently revalidated in this research.','All retained S3 evidence/key access dependencies must remain until instructor archival requirements are met.']}
if (root/'plan-reference.json').exists():
 output['observed_plan_reference']=json.loads((root/'plan-reference.json').read_text())
(root/'cost-calculations.json').write_text(json.dumps(output,indent=2)+'\n')
for r in results:
 print(r['window']['name'],r['window']['hours'],'primary_empty',round(r['primary_zero_workload_subtotal'],2),'primary_usage',round(r['primary_with_illustrative_usage'],2))
 for name,x in r['activated'].items():print(name,'fixed',round(x['fixed_primary_plus_active_subtotal'],2),'total',round(x['total_with_illustrative_usage_retention_and_reserves'],2),'headroom',round(x['headroom_against_200'],2))
