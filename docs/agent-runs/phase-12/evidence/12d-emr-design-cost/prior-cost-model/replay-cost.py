"""Public, deterministic proposal arithmetic. Reads saved public catalogs; no network/account access."""
from pathlib import Path
from decimal import Decimal, ROUND_CEILING
from fractions import Fraction
import gzip, json, hashlib, sys

ROOT = Path(__file__).resolve().parent
P = ROOT / 'public-prices'
D = Decimal

def digest(data):
    return hashlib.sha256(data).hexdigest()

def load(name):
    return json.loads(gzip.decompress((P / (name + '.response.gz')).read_bytes()))

fetch = {r['name']: r for r in json.loads((P / 'fetch-manifest.json').read_text())}
fetch.update({r['name']: r for r in json.loads((P / 'guard-services-fetch.json').read_text())})
fetch['ebs'] = json.loads((P / 'ebs-correct-fetch.json').read_text())
rates = {}

def catalog_rate(label, name, sku, unit, begin='0'):
    catalog = load(name)
    product = catalog['products'][sku]
    assert product['attributes']['regionCode'] == 'us-east-2'
    dims = [x for t in catalog['terms']['OnDemand'][sku].values()
            for x in t['priceDimensions'].values()
            if x['unit'] == unit and x['beginRange'] == begin]
    assert len(dims) == 1 and D(dims[0]['pricePerUnit']['USD']) > 0
    source = fetch[name]
    assert digest(gzip.decompress((P / (name + '.response.gz')).read_bytes())) == source['decoded_sha256']
    rates[label] = {'usd': dims[0]['pricePerUnit']['USD'], 'unit': unit,
                    'sku': sku, 'attributes': product['attributes'], 'dimension': dims[0],
                    'url': source['url'], 'retrieved_at': source['completed_at'],
                    'catalog_version': catalog['version'], 'publication_date': catalog['publicationDate'],
                    'source_decoded_sha256': source['decoded_sha256']}

for args in [
 ('emr_hour','emr','VXMPRBP5JU7WEE96','Hrs'),
 ('efs_gb_month','efs','R3JWPWRUN558WBDE','GB-Mo'),
 ('efs_read_gb','efs','VJW3RV7UAGE5H43T','GB'),
 ('efs_write_gb','efs','WPR45BR95CQVQZU2','GB'),
 ('ipv4_hour','vpc','8HFJK44D9234XNWA','Hrs'),
 ('endpoint_hour','vpc','P2Q7Y6KZKKFAHEVG','Hrs'),
 ('endpoint_gb','vpc','7FYQG974DNVUNVKW','GB'),
 ('s3_gb_month','s3','YPGKVRB2EKTVDJDT','GB-Mo'),
 ('s3_put','s3','GJKK9PMSTKPNGZS9','Requests'),
 ('s3_get','s3','DJEKB32FV4HNZJZY','Requests'),
 ('kms_key_month','kms','FEMX7ZQ4DJ6QE2KP','Keys'),
 ('kms_request','kms','9XXHSZC4PS7S6AY2','Requests'),
 ('log_ingest_gb','cloudwatch','5T6Z6V26DSR7SZ49','GB'),
 ('log_store_gb_month','cloudwatch','X7X4WD4A95NDR9U5','GB-Mo'),
 ('alarm_month','cloudwatch','28VSMYRVQXUWCTMA','Alarms'),
 ('lambda_request','lambda','ZEA64MMVK5QRB5TC','Request'),
 ('lambda_gb_second','lambda','3BYZH4NKJN8TJUQ6','Lambda-GB-Second'),
 ('scheduler_invocation','eventbridge','534HQFPF6VT4G9Y5','Invocations','14000000'),
 ('state_transition','states','PEWNRD5EMPQPHCAQ','StateTransitions'),
 ('sqs_request','sqs','9C8YFGPNBKF9HP9A','Requests'),
 ('sns_publish','sns','X7V4MHE7G6GM98JT','Requests','1000000'),
 ('sns_email','sns','GZME75EE8UXWS6VZ','Notifications','1000'),
]:
    catalog_rate(*args)

# The custom metric is an explicitly selected Ohio first paid tier, not a free allowance.
catalog_rate('metric_month','cloudwatch','XK7C3D2X45XTHURD','Metrics')

for label, name, key, unit in [
 ('ec2_hour','ec2-linux-ohio',None,'instance-hour'),
 ('ebs_gp3_gb_month','ebs','Storage General Purpose gp3 GB Mo','GB-month')
]:
    catalog = load(name)
    region = catalog['regions']['US East (Ohio)']
    if name == 'ec2-linux-ohio':
        selected = [x for x in region.values() if x.get('Instance Type') == 'm5.xlarge'
                    and x.get('Operating System') == 'Linux' and x.get('Pre Installed S/W') == 'NA']
        assert len(selected) == 1
        row = selected[0]
    else:
        row = region[key]
    source = fetch[name]
    assert digest(gzip.decompress((P / (name + '.response.gz')).read_bytes())) == source['decoded_sha256']
    rates[label] = {'usd': row['price'], 'unit': unit, 'selected_record': row,
                    'location': 'US East (Ohio)', 'url': source['url'],
                    'retrieved_at': source['completed_at'], 'manifest': catalog['manifest'],
                    'source_decoded_sha256': source['decoded_sha256']}

# These Ohio worked-example rates are explicit in the freshly retained official VPC HTML.
page = gzip.decompress((P / 'vpc-page.response.gz').read_bytes()).decode()
assert 'Ohio' in page and '$0.045' in page and '$0.09' in page
for label, value, unit in [('nat_hour','.045','gateway-hour'),('nat_gb','.045','GB'),
                           ('internet_out_gb','.09','GB')]:
    rates[label] = {'usd': value, 'unit': unit, 'url': fetch['vpc-page']['url'],
                    'retrieved_at': fetch['vpc-page']['completed_at'],
                    'source_decoded_sha256': fetch['vpc-page']['decoded_sha256'],
                    'basis': 'Published Ohio worked example, not an account quote or separate regional SKU.'}

base = {'nodes':2, 'cluster_hours':'2', 'ancillary_hours':'3', 'ebs_gb':'128',
        'efs_gb':'5', 'efs_read_gb':'5', 'efs_write_gb':'2',
        's3_gb':'1', 'retention_hours':'744', 'month_denominator_hours':'672',
        's3_put_requests':'10000', 's3_get_requests':'100000', 'kms_keys':'1',
        'kms_requests':'20000', 'logs_gb':'.25', 'alarms':'2', 'custom_metrics':'1',
        'nat_gb':'2', 'internet_out_gb':'1', 'lambda_invocations':'360',
        'lambda_gb':'.25', 'lambda_seconds':'30', 'scheduler_invocations':'360',
        'state_transitions':'200', 'sqs_requests':'1000', 'sns_notifications':'20',
        'tax_planning_fraction':'.25', 'uncertainty_reserve_usd':'.75'}

def model(name, changes):
    quantities = dict(base, **changes)
    q = {k:D(str(v)) for k,v in quantities.items()}
    assert all(v >= 0 for v in q.values())
    h = q['month_denominator_hours']
    lines = []
    def line(label, rate, quantity, formula):
        price=D(rates[rate]['usd']);cost=price*quantity
        assert abs(Fraction(price)*Fraction(quantity)-Fraction(cost)) < Fraction(1,10**22)
        lines.append({'component':label,'rate':rate,'quantity':str(quantity),
                      'formula':formula,'usd':str(cost)})
    line('EC2','ec2_hour',q['nodes']*q['cluster_hours'],'2 nodes * 2 hours')
    line('EMR surcharge','emr_hour',q['nodes']*q['cluster_hours'],'2 nodes * 2 hours')
    line('All root+data EBS','ebs_gp3_gb_month',q['ebs_gb']*q['ancillary_hours']/h,'128 GB * ancillary hours / 672; baseline IOPS/throughput only')
    line('NAT gateway','nat_hour',q['ancillary_hours'].to_integral_value(rounding=ROUND_CEILING),'one zonal gateway; each partial gateway hour rounded up')
    line('NAT processed data','nat_gb',q['nat_gb'],'proposed processed GB; S3 gateway traffic excluded')
    line('NAT public IPv4','ipv4_hour',q['ancillary_hours'].to_integral_value(rounding=ROUND_CEILING),'one EIP; conservatively round up hours')
    line('Regional EFS Standard','efs_gb_month',q['efs_gb']*q['ancillary_hours']/h,'GB * ancillary hours / 672')
    line('EFS elastic reads','efs_read_gb',q['efs_read_gb'],'metered GB INCLUDING operation minimums; not raw file bytes')
    line('EFS elastic writes','efs_write_gb',q['efs_write_gb'],'metered GB INCLUDING operation minimums; not raw file bytes')
    line('S3 Standard evidence retention','s3_gb_month',q['s3_gb']*q['retention_hours']/h,'all versions/artifacts/logs GB * retained hours / 672')
    line('S3 PUT/LIST incl control','s3_put',q['s3_put_requests'],'all artifact/log/controller PUT and LIST units')
    line('S3 GET incl control','s3_get',q['s3_get_requests'],'all artifact/log/controller GET and HEAD units')
    line('Retained CMK','kms_key_month',q['kms_keys']*q['retention_hours']/h,'key count * retained hours / 672; one nonrotated key version')
    line('KMS requests','kms_request',q['kms_requests'],'bill every proposed request; no free tier assumed')
    line('CloudWatch ingest','log_ingest_gb',q['logs_gb'],'all cluster/guard/controller log ingestion GB')
    line('CloudWatch retention','log_store_gb_month',q['logs_gb']*q['retention_hours']/h,'conservatively retain all uncompressed GB for retained hours / 672')
    line('CloudWatch standard alarms','alarm_month',q['alarms']*q['retention_hours']/h,'alarm count * retained hours / 672')
    line('Guard custom metric','metric_month',q['custom_metrics']*q['ancillary_hours']/h,'metric count * active hours / 672')
    line('Lambda watchdog+cleanup duration','lambda_gb_second',q['lambda_invocations']*q['lambda_gb']*q['lambda_seconds'],'all invocation GB-seconds incl cold starts/retries')
    line('Lambda invocations','lambda_request',q['lambda_invocations'],'all invocations incl retries')
    line('Scheduler invocations','scheduler_invocation',q['scheduler_invocations'],'use positive paid marginal tier; no entitlement deduction')
    line('StepFunctions Standard cleanup','state_transition',q['state_transitions'],'all transitions incl retries/catches; no Express workflow')
    line('SQS Standard DLQ','sqs_request',q['sqs_requests'],'64KiB request units incl sends/receives/deletes')
    line('SNS incident publish','sns_publish',q['sns_notifications'],'small standard messages; paid marginal tier')
    line('SNS incident email','sns_email',q['sns_notifications'],'paid marginal email deliveries; recipient/delivery unverified')
    line('Internet data out','internet_out_gb',q['internet_out_gb'],'proposed total egress; no free data allowance assumed')
    subtotal=sum(D(x['usd']) for x in lines)
    assert abs(sum(Fraction(x['usd']) for x in lines)-Fraction(subtotal)) < Fraction(1,10**22)
    tax=subtotal*q['tax_planning_fraction'];total=subtotal+tax+q['uncertainty_reserve_usd']
    return {'name':name,'quantities':quantities,'line_items':lines,'subtotal_usd':str(subtotal),
            'tax_planning_usd':str(tax),'uncertainty_reserve_usd':str(q['uncertainty_reserve_usd']),
            'modeled_total_usd':str(total),'display_total_usd':str(total.quantize(D('.01'),rounding=ROUND_CEILING)),
            'proposed_cap_usd':'5','modeled_headroom_usd':str(D(5)-total),
            'arithmetic_within_proposed_cap':total<=D(5),'launch_authorized':False}

result={'observed_prices_only':True,'quantities_are_proposals_not_measurements':True,
        'currency':'USD','account_spend_observed':False,'remaining_allowance_verified':False,
        'launch_cost_fit_verified':False,'launch_authorized':False,
        'month_conversion':'672-hour denominator is deliberately conservative planning arithmetic (28 days), not a claim about AWS invoice proration. Retention744h=31days. Exact dates/billing must be rechecked before approval.',
        'tax_conversion':'25% is a sensitivity allowance selected for this proposal, NOT observed tax jurisdiction/rate. Higher applicable taxes invalidate this modeled fit.',
        'rate_tiers':'Paid marginal rates are used even where free tiers exist; no credit, free-tier, prepaid commitment or monthly reset is deducted.',
        'unpriced_zero_choices':['No public node IPs, only one NAT EIP priced','No interface endpoints selected; NAT+S3 gateway route','No EFS IA/archive/backup/replication/provisioned throughput','No snapshots, extra EBS provisioned performance, Spot/task nodes','No EKS/Serverless/Bedrock/database resources','No extra shared course infrastructure assumed'],
        'unresolved':['Account-wide current and delayed spend/commitments (F4)','Exact planned resource quantities and provider defaults','Actual metered EFS I/O and network/log/request volumes','Dependency/artifact hashes and runtime archive size','Actual applicable taxes and support charges if any','Independent cluster/ancillary cleanup correctness and exact-ID binding','Retention decision and post-retention archival/cleanup authority','Region/quota/capacity, IAM effectiveness and custom runtime compatibility'],
        'scenarios':[model('bounded_nominal_proposal',{}),
                     model('io_and_log_sensitivity',{'efs_read_gb':'10','efs_write_gb':'5','logs_gb':'1'}),
                     model('retention_90_days',{'retention_hours':'2160'}),
                     model('ancillary_cleanup_delayed_24h',{'ancillary_hours':'24','lambda_invocations':'2880','scheduler_invocations':'2880','state_transitions':'1600'})]}
assert D(rates['ec2_hour']['usd'])==D('.192') and D(rates['emr_hour']['usd'])==D('.048')
assert D(result['scenarios'][0]['line_items'][0]['usd'])+D(result['scenarios'][0]['line_items'][1]['usd'])==D('.96')
assert result['scenarios'][0]['arithmetic_within_proposed_cap'] is True
assert all(D(s['modeled_total_usd'])>D(result['scenarios'][0]['modeled_total_usd']) for s in result['scenarios'][1:])
if sys.argv[1:]==['--record']:
    for name,data in [('selected-rates.json',rates),('cost-calculations.json',result)]:
        with (ROOT/name).open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
else:
    assert not sys.argv[1:]
    assert json.loads((ROOT/'selected-rates.json').read_text())==rates
    assert json.loads((ROOT/'cost-calculations.json').read_text())==result
print(json.dumps({'rates':len(rates),'scenarios':[{'name':s['name'],'usd':s['display_total_usd'],'within_cap':s['arithmetic_within_proposed_cap']} for s in result['scenarios']],'launch_authorized':False,'deterministic_replay':'recorded' if sys.argv[1:] else 'matched'},sort_keys=True))
