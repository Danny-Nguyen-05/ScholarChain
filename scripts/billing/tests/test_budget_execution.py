#!/usr/bin/env python3
"""Credential-free features; every child process here is a local stub."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('budget_execution', ROOT / 'budget_execution.py')
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
FIXTURE_ADDRESS = 'synthetic@example.invalid'
NOW = datetime(2026, 11, 1, 21, 0, tzinfo=timezone.utc)

STUB = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
root=pathlib.Path.cwd().parent
scenario=json.loads((root/'scenario.json').read_text())
with open(root/'calls.jsonl','a') as journal:
 journal.write(json.dumps({'argv':sys.argv,'env':dict(os.environ),'cwd':str(pathlib.Path.cwd())})+'\n')
if pathlib.Path(sys.argv[0]).name.startswith('terraform'):
 state=pathlib.Path(next(x.split('=',1)[1] for x in sys.argv if x.startswith('-state=')))
 if scenario.get('terraform_fail'):
  state.write_bytes(b'opaque partial state')
  state.chmod(0o600)
  for path in [state.with_name(state.name+'.backup'),root/'config/errored.tfstate',root/'.billing.execution.tfstate.lock.info']:
   path.write_bytes(b'opaque recovery fixture');path.chmod(0o600)
  sys.exit(1)
 state.write_bytes(b'opaque completed fixture state');state.chmod(0o600)
 print('no private output should be published')
 sys.exit(0)
if '--generate-cli-skeleton' in sys.argv:
 print(json.dumps({} if scenario.get('unsupported') else {'ShowFilterExpression':True}))
 sys.exit(0)
operation=sys.argv[2]
if operation=='describe-budget' and not (root/'billing.execution.tfstate').exists():
 outcome=scenario.get('p3','absent')
 if outcome=='exists':print(json.dumps({'Budget':{}}));sys.exit(0)
 if outcome=='blank':sys.exit(254)
 if outcome=='malformed':print('{malformed');sys.exit(0)
 if outcome=='network':print('Could not connect to the endpoint URL',file=sys.stderr);sys.exit(255)
 error={'absent':'NotFoundException','denied':'AccessDeniedException','expired':'ExpiredTokenException','throttled':'ThrottlingException'}.get(outcome,'NotFoundException')
 message='Specified budget does not exist.'
 if outcome=='mixed':message+=' AccessDenied credentials.'
 op='DescribeBudgets' if outcome=='wrong-operation' else 'DescribeBudget'
 prefix='aws: [ERROR]: ' if scenario.get('p3_header')=='observed-zero' else ''
 annotation=' (reached max retries: 0)' if scenario.get('p3_header')=='observed-zero' else ''
 if scenario.get('p3_leading_lf'):print('',file=sys.stderr)
 print(prefix+'An error occurred ('+error+') when calling the '+op+' operation'+annotation+': '+message,file=sys.stderr)
 sys.exit(254)
responses=scenario['responses']
if operation=='describe-subscribers-for-notification':
 threshold=json.loads(sys.argv[sys.argv.index('--notification')+1])['Threshold']
 print(json.dumps(responses['subscribers'][str(threshold)]));sys.exit(0)
print(json.dumps(responses[operation]))
'''


def fixture_responses():
    return {'describe-budget': {'Budget': {'BudgetName': b.BUDGET, 'BudgetType':'COST',
             'TimeUnit':'CUSTOM','BudgetLimit':{'Amount':'200','Unit':'USD'},
             'TimePeriod':{'Start':'2026-10-01T00:00:00Z','End':'2027-01-01T00:00:00Z'},
             'CostTypes':dict(b.COST_TYPES),'CostFilters':{},'FilterExpression':{},
             'HealthStatus':{'Status':'HEALTHY'}}},
            'list-tags-for-resource':{'ResourceTags':[{'Key':k,'Value':v} for k,v in b.TAGS.items()]},
            'describe-notifications-for-budget':{'Notifications':[b.expected_notification(x) for x in (50,80,100)]},
            'subscribers':{str(x):{'Subscribers':[{'SubscriptionType':'EMAIL','Address':FIXTURE_ADDRESS}]} for x in (50,80,100)}}


def modern_budget_fixture():
    budget = copy.deepcopy(fixture_responses()['describe-budget']['Budget'])
    del budget['CostTypes']
    del budget['CostFilters']
    budget['Metrics'] = ['UnblendedCost']
    budget['FilterExpression'] = {'Not': {'Dimensions': {
        'Key': 'RECORD_TYPE', 'Values': ['Credit', 'Refund']}}}
    return budget


class CostScopeFeatures(unittest.TestCase):
    def validate(self, budget):
        responses = fixture_responses()
        responses['describe-budget']['Budget'] = budget
        return b.sanitize_readback(responses['describe-budget'], responses['list-tags-for-resource'],
            responses['describe-notifications-for-budget'],
            {int(k): v for k, v in responses['subscribers'].items()}, FIXTURE_ADDRESS)

    def test_legacy_and_modern_scope_have_truthful_safe_receipt_fields(self):
        legacy = fixture_responses()['describe-budget']['Budget']
        for budget in (legacy, modern_budget_fixture()):
            with self.subTest(legacy='CostTypes' in budget):
                result = self.validate(budget)
                self.assertTrue(result['cost_scope_match'])
                self.assertTrue(result['scope_filters_absent'])
                self.assertNotIn('cost_types_match', result)
                self.assertNotIn('filters_absent', result)
                self.assertNotIn(FIXTURE_ADDRESS, json.dumps(result))

    def test_billing_view_must_be_absent_for_legacy_and_modern(self):
        views = (None, '', f'arn:aws:billing::{b.ACCOUNT}:billingview/primary',
                 f'arn:aws:billing::{b.ACCOUNT}:billingview/custom-synthetic',
                 'arn:aws:billing::123456789012:billingview/primary',
                 'malformed-view', False, 0, [], {})
        for factory in (lambda: copy.deepcopy(fixture_responses()['describe-budget']['Budget']),
                        modern_budget_fixture):
            absent = factory()
            self.assertNotIn('BillingViewArn', absent)
            self.assertTrue(self.validate(absent)['scope_filters_absent'])
            for view in views:
                with self.subTest(legacy='CostTypes' in absent, view=view):
                    budget = factory(); budget['BillingViewArn'] = view
                    with self.assertRaisesRegex(b.Blocked, 'BILLING_VIEW_PRESENT'):
                        b.validate_cost_scope(budget)
                    with self.assertRaisesRegex(b.Blocked, 'BILLING_VIEW_PRESENT') as error:
                        self.validate(budget)
                    if type(view) is str and view:
                        self.assertNotIn(view, str(error.exception))

    def test_auto_adjust_and_planned_limits_are_forbidden_on_presence(self):
        dynamic = {'AutoAdjustType': 'HISTORICAL',
                   'HistoricalOptions': {'BudgetAdjustmentPeriod': 3}}
        planned = {'1793491200': {'Amount': '350', 'Unit': 'USD'}}
        for legacy in (False, True):
            for key, realistic, code in (('AutoAdjustData', dynamic, 'AUTO_ADJUST_PRESENT'),
                                         ('PlannedBudgetLimits', planned, 'PLANNED_LIMITS_PRESENT')):
                for value in (realistic, None, {}, [], '', False, 0):
                    with self.subTest(legacy=legacy, key=key, value=value):
                        budget = (copy.deepcopy(fixture_responses()['describe-budget']['Budget'])
                                  if legacy else modern_budget_fixture())
                        budget[key] = value
                        with self.assertRaisesRegex(b.Blocked, code): self.validate(budget)

    def test_documented_observational_metadata_is_accepted_without_emission(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                budget = (copy.deepcopy(fixture_responses()['describe-budget']['Budget'])
                          if legacy else modern_budget_fixture())
                budget.update(CalculatedSpend={'ActualSpend': {'Amount': '17.25', 'Unit': 'USD'},
                                               'ForecastedSpend': {'Amount': '28.75', 'Unit': 'USD'}},
                              LastUpdatedTime=1793491200)
                result = self.validate(budget)
                self.assertTrue(result['cost_scope_match'])
                output = json.dumps(result)
                for private_value in ('17.25', '28.75', '1793491200', FIXTURE_ADDRESS):
                    self.assertNotIn(private_value, output)

    def test_unknown_budget_keys_and_wrong_budget_container_fail_closed(self):
        for legacy in (False, True):
            for key in ('UnknownBudgetField', 'NewScopeFilter', 'billingViewArn', 'PlannedBudgetLimit'):
                with self.subTest(legacy=legacy, key=key):
                    budget = (copy.deepcopy(fixture_responses()['describe-budget']['Budget'])
                              if legacy else modern_budget_fixture())
                    budget[key] = {'private': FIXTURE_ADDRESS}
                    with self.assertRaisesRegex(b.Blocked, 'BUDGET_FIELD_UNSUPPORTED') as error:
                        self.validate(budget)
                    self.assertNotIn(FIXTURE_ADDRESS, str(error.exception))
        for budget in (None, [], False, 'synthetic-budget'):
            with self.subTest(container=budget):
                with self.assertRaisesRegex(b.Blocked, 'BUDGET_RESPONSE_SHAPE'):
                    self.validate(budget)

    def test_only_documented_value_order_is_normalized(self):
        budget = modern_budget_fixture()
        budget['FilterExpression']['Not']['Dimensions']['Values'].reverse()
        self.assertTrue(self.validate(budget)['cost_scope_match'])
        budget['FilterExpression']['Not']['Dimensions']['MatchOptions'] = ['EQUALS']
        with self.assertRaisesRegex(b.Blocked, 'FILTER_PRESENT'):
            self.validate(budget)

    def test_missing_or_untyped_cost_scope_never_implies_expected_flags(self):
        for value in (None, {}, [], False, dict(b.COST_TYPES, IncludeCredit=0),
                      dict(b.COST_TYPES, Unknown=True)):
            with self.subTest(value=value):
                budget = modern_budget_fixture(); budget['CostTypes'] = value
                with self.assertRaisesRegex(b.Blocked, 'COST_TYPES'):
                    self.validate(budget)
        budget = modern_budget_fixture(); del budget['Metrics']
        with self.assertRaisesRegex(b.Blocked, 'COST_SCOPE_UNVERIFIED'):
            self.validate(budget)
        budget = modern_budget_fixture(); del budget['FilterExpression']
        with self.assertRaisesRegex(b.Blocked, 'COST_SCOPE_UNVERIFIED'):
            self.validate(budget)

    def test_wrong_unknown_duplicate_or_untyped_metrics_are_rejected(self):
        values = (None, 'UnblendedCost', [], ['NetUnblendedCost'], ['BlendedCost'],
                  ['AmortizedCost'], ['UNKNOWN'], ['UnblendedCost', 'UnblendedCost'],
                  ['UnblendedCost', 'NetUnblendedCost'], [True], [{}])
        for metrics in values:
            for legacy in (False, True):
                with self.subTest(metrics=metrics, legacy=legacy):
                    budget = modern_budget_fixture() if not legacy else fixture_responses()['describe-budget']['Budget']
                    budget['Metrics'] = metrics
                    with self.assertRaisesRegex(b.Blocked, 'COST_METRIC'):
                        self.validate(budget)

    def test_extra_scope_filters_and_expression_shapes_are_rejected(self):
        candidate = modern_budget_fixture()['FilterExpression']
        expressions = (None, [], False, {}, {'And': [candidate]}, {'Or': [candidate]},
            {'Not': {'Not': candidate}}, {'Not': {'Dimensions': {'Key': 'SERVICE', 'Values': ['Credit', 'Refund']}}},
            dict(candidate, Tags={'Key': 'project'}), dict(candidate, Unknown=True),
            {'Not': dict(candidate['Not'], DimensionsExtra={})},
            {'Not': {'Dimensions': []}}, {'Not': {'Tags': {'Key': 'project'}}})
        for expression in expressions:
            with self.subTest(expression=expression):
                budget = modern_budget_fixture(); budget['FilterExpression'] = expression
                with self.assertRaises(b.Blocked): self.validate(budget)
        for filters in (None, [], False, {'Service': ['synthetic-service']}, {'Unknown': []}):
            with self.subTest(filters=filters):
                budget = modern_budget_fixture(); budget['CostFilters'] = filters
                with self.assertRaisesRegex(b.Blocked, 'FILTER_PRESENT'):
                    self.validate(budget)

    def test_exclusion_values_cannot_hide_duplicates_or_other_charge_types(self):
        values = (None, 'Credit', [], ['Credit'], ['Refund'], ['Credit', 'Credit'],
                  ['Credit', 'Refund', 'Tax'], ['Credit', 'Tax'], ['credit', 'Refund'],
                  [False, 'Refund'], [{'Credit': True}, 'Refund'])
        for excluded in values:
            with self.subTest(excluded=excluded):
                budget = modern_budget_fixture()
                budget['FilterExpression']['Not']['Dimensions']['Values'] = excluded
                with self.assertRaisesRegex(b.Blocked, 'FILTER_PRESENT'):
                    self.validate(budget)

    def test_dual_representations_must_agree_in_every_legacy_flag(self):
        budget = modern_budget_fixture(); budget['CostTypes'] = dict(b.COST_TYPES)
        self.assertTrue(self.validate(budget)['cost_scope_match'])
        for key, expected in b.COST_TYPES.items():
            with self.subTest(key=key):
                conflicting = copy.deepcopy(budget)
                conflicting['CostTypes'][key] = not expected
                with self.assertRaisesRegex(b.Blocked, 'COST_TYPES'):
                    self.validate(conflicting)

    def test_new_representation_preserves_amount_date_tag_and_privacy_guards(self):
        for name, mutate in (
            ('amount', lambda r: r['describe-budget']['Budget']['BudgetLimit'].update(Amount='201')),
            ('date', lambda r: r['describe-budget']['Budget']['TimePeriod'].update(End='2027-01-02T00:00:00Z')),
            ('tag', lambda r: r['list-tags-for-resource']['ResourceTags'][0].update(Value='wrong')),
            ('alert', lambda r: r['describe-notifications-for-budget']['Notifications'][0].update(Threshold=60)),
            ('recipient', lambda r: r['subscribers']['50']['Subscribers'][0].update(Address='other@example.invalid')),
            ('health', lambda r: r['describe-budget']['Budget']['HealthStatus'].update(Status='UNHEALTHY'))):
            with self.subTest(name=name):
                responses = fixture_responses(); responses['describe-budget']['Budget'] = modern_budget_fixture()
                mutate(responses)
                with self.assertRaises(b.Blocked) as error:
                    b.sanitize_readback(responses['describe-budget'], responses['list-tags-for-resource'],
                        responses['describe-notifications-for-budget'],
                        {int(k): v for k, v in responses['subscribers'].items()}, FIXTURE_ADDRESS)
                self.assertNotIn(FIXTURE_ADDRESS, str(error.exception))
                self.assertNotIn(b.digest(FIXTURE_ADDRESS.encode()), str(error.exception))


class Features(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='billing wrapper test ')
        self.root=Path(self.temp.name).resolve();self.root.chmod(0o700)
        self.primary=self.root/'primary with space';self.backups=self.root/'backups';self.repo=self.root/'repo'
        for d in (self.primary,self.backups,self.repo):d.mkdir(mode=0o700)
        for rel in ('config','config/tests','toolchain','tf-data','offline-tf-data',
                    'toolchain/provider-mirror','toolchain/provider-mirror/registry.terraform.io',
                    'toolchain/provider-mirror/registry.terraform.io/hashicorp',
                    'toolchain/provider-mirror/registry.terraform.io/hashicorp/aws',
                    'toolchain/provider-mirror/registry.terraform.io/hashicorp/aws/6.44.0',
                    'toolchain/provider-mirror/registry.terraform.io/hashicorp/aws/6.44.0/darwin_arm64'):
            (self.primary/rel).mkdir(mode=0o700)
        self.write(self.primary/'toolchain/terraform-1.13.5',STUB,0o700)
        self.aws=self.primary/'toolchain/aws-stub';self.write(self.aws,STUB,0o700)
        self.write(self.primary/'toolchain/terraform.tfrc','public fixture')
        self.write(self.primary/'approved-public-inputs.tfvars.json','{}')
        self.write(self.primary/'billing.execution.tfplan','public fake plan')
        provider=self.primary/'toolchain/provider-mirror/registry.terraform.io/hashicorp/aws/6.44.0/darwin_arm64/terraform-provider-aws_v6.44.0_x5'
        self.write(provider,'provider fixture',0o700)
        self.write(self.primary/'config/main.tf','public config fixture')
        self.pins={'plan_sha256':b.hash_file(self.primary/'billing.execution.tfplan'),
                   'plan_bytes':(self.primary/'billing.execution.tfplan').stat().st_size,
                   'terraform_sha256':b.hash_file(self.primary/'toolchain/terraform-1.13.5'),
                   'provider_sha256':b.hash_file(provider),
                   'cli_config_sha256':b.hash_file(self.primary/'toolchain/terraform.tfrc'),
                   'public_input_sha256':b.hash_file(self.primary/'approved-public-inputs.tfvars.json'),
                   'proposal_sha256':'1'*64,'human_record_sha256':'2'*64,
                   'config':[{'copy_relative':'config/main.tf','sha256':b.hash_file(self.primary/'config/main.tf'),'bytes':21}],
                   'source_freeze':[]}
        self.pins['config'][0]['bytes']=(self.primary/'config/main.tf').stat().st_size
        self.policy=b.Policy(self.primary,self.backups,self.repo,os.getuid(),self.aws,self.pins)
        self.scenario={'responses':fixture_responses()};self.scenario_file=self.primary/'scenario.json';self.save_scenario()
        self.gate={'operation':'initial','plan_sha256':self.pins['plan_sha256'],
            'proposal_sha256':self.pins['proposal_sha256'],'wrapper_files':{'scripts/billing/budget_execution.py':'3'*64},
            'source_commit':'a'*40,'human_record_sha256':self.pins['human_record_sha256'],
            'g1_affirmation':'A human statement fixture, no real approval.',
            'actor_arn':b.CALLER,'account':b.ACCOUNT,'profile':b.PROFILE,'region':b.REGION,
            'window_start':b.iso(NOW-timedelta(minutes=5)), 'window_end':b.iso(NOW+timedelta(minutes=30)),
            'timezone':'America/Chicago','login_at':b.iso(NOW-timedelta(minutes=4)),
            'human_sts_observed_at':b.iso(NOW-timedelta(minutes=3)),
            'human_sts':{'Account':b.ACCOUNT,'Arn':b.CALLER},'permissions':sorted(b.ACTIONS),
            'retention_accepted':True,'wrapper_review_approved':True,'ownership_reconciled':True,
            'aws_cli_sha256':b.hash_file(self.aws),'public_packet_root':'docs/agent-runs/phase-12/evidence/fixture'}
        self.gate_path=self.root/'human-gate-fixture.json'
        self.ex=self.execution()

    def tearDown(self):self.temp.cleanup()

    def write(self,path,value,mode=0o600):
        path.write_text(value);path.chmod(mode)

    def save_scenario(self):self.write(self.scenario_file,json.dumps(self.scenario))

    def calls(self):
        p=self.primary/'calls.jsonl'
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

    def p3_apply(self):self.ex.p3_check();return self.ex.apply()

    def test_apply_exact_argv_env_and_space_paths(self):
        self.p3_apply();calls=self.calls();last=calls[-1]
        self.assertEqual(last['argv'],self.policy.apply_argv())
        self.assertEqual(last['cwd'],str(self.policy.config))
        # Python interpreter adds LC_CTYPE on macOS; other inherited secrets absent.
        self.assertEqual({k:v for k,v in last['env'].items() if k not in ('LC_CTYPE','__CF_USER_TEXT_ENCODING')},self.policy.env())
        self.assertNotIn('AWS_ACCESS_KEY_ID',last['env'])
        self.assertEqual(len([x for x in calls if x['argv'][1]=='apply']),1)
        self.assertFalse((self.primary/'.billing-wrapper-active.lock').exists())

    def test_full_readback_safe_only(self):
        self.p3_apply();safe=self.ex.readback();text=json.dumps(safe)
        self.assertNotIn(FIXTURE_ADDRESS,text);self.assertNotIn(b.digest(FIXTURE_ADDRESS.encode()),text)
        self.assertTrue(safe['result']['private_recipients_match'])
        self.assertEqual(safe['result']['notification_count'],3)
        self.assertEqual(len(self.calls()),9) # capability, P3, apply, six read requests

    def test_opaque_backup_hash_modes_fsync(self):
        self.ex.p3_check()
        with mock.patch.object(b.os,'fsync',wraps=os.fsync) as fsync:
            receipt=self.ex.apply()
        target=self.backups/'initial-ab9f141e83058209/billing.execution.tfstate'
        self.assertEqual(b.hash_file(target),b.hash_file(self.policy.state))
        self.assertEqual(stat.S_IMODE(target.stat().st_mode),0o600)
        self.assertGreaterEqual(fsync.call_count,4)
        self.assertTrue(receipt['result']['backup']['fsync_completed'])

    def test_plan_hash_rejected_before_process(self):
        self.write(self.policy.plan,'changed')
        with self.assertRaises(b.Blocked):self.ex.p3_check()
        self.assertEqual(self.calls(),[])

    def test_plan_mode_rejected_before_process(self):
        self.policy.plan.chmod(0o644)
        with self.assertRaises(b.Blocked):self.ex.p3_check()
        self.assertEqual(self.calls(),[])

    def test_owner_mismatch_rejected_before_process(self):
        with self.assertRaises(b.Blocked):b.file_meta(self.policy.plan,os.getuid()+1)
        self.assertEqual(self.calls(),[])

    def test_plan_size_mismatch_rejected(self):
        self.pins['plan_bytes']+=1
        with self.assertRaisesRegex(b.Blocked,'PLAN_SIZE'):self.ex.p3_check()
        self.assertEqual(self.calls(),[])

    def test_preexisting_state_and_recovery_stop(self):
        for rel in ('billing.execution.tfstate','config/errored.tfstate','tf-data/terraform.tfstate',
                    'config/terraform.tfstate.d','billing.execution.tfstate.backup',
                    '.billing.execution.tfstate.lock.info'):
            with self.subTest(rel=rel):
                path=self.primary/rel;self.write(path,'opaque fixture')
                with self.assertRaises(b.Blocked):self.ex.no_state()
                path.unlink()
        self.assertEqual(self.calls(),[])

    def test_p3_error_classification_no_retry(self):
        for outcome in ('denied','expired','throttled','malformed','blank','exists','mixed','network','wrong-operation'):
            with self.subTest(outcome=outcome):
                self.scenario['p3']=outcome;self.save_scenario()
                self.gate['operation']='op-'+outcome
                self.write(self.gate_path,json.dumps(self.gate))
                ex=b.Execution(self.policy,now=lambda:NOW).load_gate(self.gate_path,b.hash_file(self.gate_path),self.gate['operation'])
                ex.check_checkout=lambda *args,**kwargs:None
                before=len(self.calls())
                with self.assertRaises(b.Blocked):ex.p3_check()
                self.assertEqual(len(self.calls())-before,2)
                with self.assertRaises(FileExistsError):ex.p3_check()
                self.assertEqual(len(self.calls())-before,2)

    def test_exact_notfound_accepted_only_known_operation(self):
        self.ex.p3_check()
        self.assertTrue(self.ex.prior('p3-check')['result']['exact_name_absent'])
        for code,out,err in [(1,b'',b'NotFoundException'),(254,b'{}',b'NotFoundException'),
                             (254,b'',b'HTTP400 NotFoundException')]:
            with self.subTest(code=code,out=out):
                with self.assertRaises(b.Blocked):b.absence(code,out,err)

    def test_missing_filter_option_stops_before_live_request(self):
        self.scenario['unsupported']=True;self.save_scenario()
        with self.assertRaisesRegex(b.Blocked,'CLI_SHOW_FILTER_UNSUPPORTED'):self.ex.p3_check()
        self.assertEqual(len(self.calls()),1)

    def test_p3_observed_zero_retry_header_accepts_without_retry(self):
        self.scenario['p3_header']='observed-zero';self.scenario['p3_leading_lf']=True;self.save_scenario()
        self.ex.p3_check()
        self.assertTrue(self.ex.prior('p3-check')['result']['exact_name_absent'])
        self.assertEqual(len(self.calls()),2)  # One offline capability + one exact request.
        with self.assertRaises(FileExistsError):self.ex.p3_check()
        self.assertEqual(len(self.calls()),2)

    def test_p3_accepts_exactly_legacy_and_observed_headers(self):
        legacy=b'An error occurred (NotFoundException) when calling the DescribeBudget operation'
        observed=b'aws: [ERROR]: '+legacy+b' (reached max retries: 0)'
        for header in (legacy,observed):
            with self.subTest(accepted_header=header):
                b.absence(254,b'',header+b': Public fixture budget does not exist.\n')
        rejected=[b'aws: [ERROR]: '+legacy,legacy+b' (reached max retries: 0)',
                  b'unknown: '+observed,b'aws: [WARNING]: '+legacy+b' (reached max retries: 0)']
        rejected += [b'aws: [ERROR]: '+legacy+b' (reached max retries: '+count+b')'
                     for count in (b'1',b'2',b'01',b'00',b'-1',b'0.0',b'unknown')]
        for header in rejected:
            with self.subTest(rejected_header=header):
                with self.assertRaisesRegex(b.Blocked,'P3_NOT_EXACT_NOT_FOUND'):
                    b.absence(254,b'',header+b': Public fixture only.\n')

    def test_p3_only_observed_optional_leading_lf_layout(self):
        legacy=b'An error occurred (NotFoundException) when calling the DescribeBudget operation'
        observed=b'aws: [ERROR]: '+legacy+b' (reached max retries: 0)'
        for header in (legacy,observed):
            message=header+b': Public fixture budget does not exist.'
            for leading in (b'',b'\n'):
                for trailing in (b'',b'\n',b'\r\n'):
                    with self.subTest(header=header,leading=leading,trailing=trailing):
                        b.absence(254,b'',leading+message+trailing)
            for leading in (b'\n\n',b'\r\n',b'\r',b'\n\r\n',b' \n'):
                with self.subTest(rejected_leading=leading):
                    with self.assertRaisesRegex(b.Blocked,'P3_NOT_EXACT_NOT_FOUND'):
                        b.absence(254,b'',leading+message+b'\n')
            for leading in (b'',b'\n'):
                for trailing in (b'\n\n',b'\r\n\n',b'\n\r\n',b'\r',b'\r\r\n'):
                    with self.subTest(leading=leading,rejected_trailing=trailing):
                        with self.assertRaisesRegex(b.Blocked,'P3_NOT_EXACT_NOT_FOUND'):
                            b.absence(254,b'',leading+message+trailing)
            for body in (b'AccessDenied credentials.',b'ExpiredToken fixture.',b'TLS connect fixture.',
                         b'Public fixture.\nAnother line.',b'\x1b[31mPublic fixture.',b' \t'):
                with self.subTest(rejected_body=body):
                    with self.assertRaises(b.Blocked):b.absence(254,b'',b'\n'+header+b': '+body+b'\n')

    def test_p3_observed_header_preserves_all_error_guards(self):
        header=b'aws: [ERROR]: An error occurred (NotFoundException) when calling the DescribeBudget operation (reached max retries: 0): '
        cases=[(1,b'',header+b'Public fixture.\n'),(254,b'{}',header+b'Public fixture.\n'),
               (254,b'',header.replace(b'NotFoundException',b'AccessDeniedException')+b'Public fixture.\n'),
               (254,b'',header.replace(b'DescribeBudget',b'DescribeBudgets')+b'Public fixture.\n')]
        cases += [(254,b'',header+body) for body in
                  (b'',b'\n',b' \t\n',b'Public fixture.\nAnother line.\n',b'Public fixture.\n\n',
                   b'\x1b[31mPublic fixture.\x1b[0m\n',b'AccessDenied credentials.\n',
                   b'ExpiredToken fixture.\n',b'Throttling fixture.\n',b'TLS connect fixture.\n')]
        for code,out,err in cases:
            with self.subTest(code=code,out=out,err=err):
                with self.assertRaises(b.Blocked):b.absence(code,out,err)

    def test_p3_observed_denial_and_wrong_operation_never_retry(self):
        self.scenario['p3_header']='observed-zero'
        for outcome in ('denied','expired','throttled','mixed','wrong-operation'):
            with self.subTest(outcome=outcome):
                self.scenario['p3']=outcome;self.save_scenario()
                self.gate['operation']='new-format-'+outcome
                self.write(self.gate_path,json.dumps(self.gate))
                ex=b.Execution(self.policy,now=lambda:NOW).load_gate(self.gate_path,b.hash_file(self.gate_path),self.gate['operation'])
                ex.check_checkout=lambda *args,**kwargs:None
                before=len(self.calls())
                with self.assertRaises(b.Blocked):ex.p3_check()
                self.assertEqual(len(self.calls())-before,2)
                with self.assertRaises(FileExistsError):ex.p3_check()
                self.assertEqual(len(self.calls())-before,2)

    def test_apply_fail_preserves_all_recovery_including_errored(self):
        self.ex.p3_check();self.scenario['terraform_fail']=True;self.save_scenario()
        with self.assertRaisesRegex(b.Blocked,'INCIDENT_REQUIRED'):self.ex.apply()
        receipt=json.loads((self.backups/'initial-ab9f141e83058209/preservation.receipt.json').read_text())
        names={x['source'] for x in receipt['artifacts']}
        self.assertIn('config/errored.tfstate',names)
        self.assertIn('billing.execution.tfstate.backup',names)
        self.assertIn('.billing.execution.tfstate.lock.info',names)
        self.assertTrue(all(x.get('equal') for x in receipt['artifacts']))
        self.assertTrue((self.policy.config/'errored.tfstate').exists())
        with self.assertRaises(b.Blocked):self.ex.apply()
        self.assertEqual(len(self.calls()),3)

    def test_backup_fsync_failure_stops_no_readback_no_retry(self):
        self.ex.p3_check()
        original=b.opaque_copy
        def fail_copy(*args,**kwargs):
            with mock.patch.object(b.os,'fsync',side_effect=OSError('fixture disk failure')):
                return original(*args,**kwargs)
        with mock.patch.object(b,'opaque_copy',side_effect=fail_copy):
            with self.assertRaisesRegex(b.Blocked,'INCIDENT_REQUIRED'):self.ex.apply()
        self.assertFalse((self.ex.op/'apply.receipt.json').exists())
        with self.assertRaises((b.Blocked,OSError)):self.ex.readback()
        self.assertEqual(len(self.calls()),3)

    def test_backup_never_overwrites(self):
        self.ex.p3_check()
        (self.backups/'initial-ab9f141e83058209').mkdir(mode=0o700)
        with self.assertRaises(FileExistsError):self.ex.apply()
        self.assertEqual(len(self.calls()),2)

    def test_symlink_copy_rejected(self):
        source=self.root/'source';self.write(source,'state fixture')
        linked=self.root/'linked';linked.symlink_to(source)
        with self.assertRaises(b.Blocked):b.opaque_copy(linked,self.backups/'out',os.getuid())
        self.assertFalse((self.backups/'out').exists())

    def test_copy_changed_source_rejected(self):
        source=self.root/'source';self.write(source,'state fixture')
        original=b.hash_file
        with mock.patch.object(b,'hash_file',side_effect=lambda path:'0'*64 if Path(path)==source else original(path)):
            with self.assertRaises(b.Blocked):b.opaque_copy(source,self.backups/'out',os.getuid())

    def test_gate_denies_wrong_identity_window_scope_binding(self):
        cases=[('actor_arn','wrong'),('account','000000000000'),('plan_sha256','0'*64),
               ('permissions',['apply']),('window_end',b.iso(NOW-timedelta(seconds=1))),
               ('g1_affirmation',''),('wrapper_review_approved',False),('ownership_reconciled',False)]
        for field,value in cases:
            with self.subTest(field=field):
                gate=copy.deepcopy(self.gate);gate[field]=value
                self.write(self.gate_path,json.dumps(gate))
                with self.assertRaises(b.Blocked):b.Execution(self.policy,now=lambda:NOW).load_gate(self.gate_path,b.hash_file(self.gate_path),'initial')
        self.assertEqual(self.calls(),[])

    def test_gate_hash_tamper_fails(self):
        with self.assertRaisesRegex(b.Blocked,'GATE_HASH'):b.Execution(self.policy).load_gate(self.gate_path,'0'*64,'initial')

    def test_replayed_apply_readback_stages_fail_before_process(self):
        self.p3_apply();before=len(self.calls())
        with self.assertRaises(b.Blocked):self.ex.apply()
        self.assertEqual(len(self.calls()),before)
        self.ex.readback();before=len(self.calls())
        with self.assertRaises(FileExistsError):self.ex.readback()
        self.assertEqual(len(self.calls()),before)

    def test_p3_receipt_stale_and_cross_gate_binding_stop(self):
        self.ex.p3_check()
        self.ex.now=lambda:NOW+timedelta(minutes=3)
        with self.assertRaisesRegex(b.Blocked,'STALE_P3'):self.ex.apply()
        self.ex.now=lambda:NOW
        self.ex.binding['gate_sha256']='f'*64
        with self.assertRaisesRegex(b.Blocked,'PRIOR_RECEIPT_BINDING'):self.ex.apply()
        self.assertEqual(len(self.calls()),2)

    def test_readback_needs_backup_receipt_and_unchanged_state(self):
        self.ex.p3_check()
        with self.assertRaises((b.Blocked,OSError)):self.ex.readback()
        self.ex.apply();self.write(self.policy.state,'changed state fixture')
        with self.assertRaisesRegex(b.Blocked,'STATE_BACKUP_DRIFT'):self.ex.readback()
        self.assertEqual(len(self.calls()),3)

    def test_readback_matrix_sanitizer_no_private_emission(self):
        cases={
          'extra_notification':lambda r:r['describe-notifications-for-budget']['Notifications'].append(b.expected_notification(60)),
          'sns':lambda r:r['subscribers']['50']['Subscribers'][0].update(SubscriptionType='SNS'),
          'cost_types':lambda r:r['describe-budget']['Budget']['CostTypes'].update(IncludeCredit=True),
          'filter':lambda r:r['describe-budget']['Budget'].update(FilterExpression={'Tags':{'Key':'project'}}),
          'tag':lambda r:r['list-tags-for-resource']['ResourceTags'][0].update(Value='wrong'),
          'date':lambda r:r['describe-budget']['Budget']['TimePeriod'].update(End='2027-01-02T00:00:00Z'),
          'address':lambda r:r['subscribers']['80']['Subscribers'][0].update(Address='other@example.invalid'),
          'pagination':lambda r:r['subscribers']['100'].update(NextToken='more'),
          'unhealthy':lambda r:r['describe-budget']['Budget']['HealthStatus'].update(Status='UNHEALTHY')}
        for name,mutate in cases.items():
            with self.subTest(name=name):
                r=fixture_responses();mutate(r)
                with self.assertRaises(b.Blocked) as error:
                    b.sanitize_readback(r['describe-budget'],r['list-tags-for-resource'],r['describe-notifications-for-budget'],{int(k):v for k,v in r['subscribers'].items()},FIXTURE_ADDRESS)
                self.assertNotIn(FIXTURE_ADDRESS,str(error.exception))
                self.assertNotIn(b.digest(FIXTURE_ADDRESS.encode()),str(error.exception))

    def test_readback_command_mismatch_does_not_retry(self):
        self.p3_apply();self.scenario['responses']['describe-budget']['Budget']['CostTypes']['IncludeTax']=False;self.save_scenario()
        with self.assertRaisesRegex(b.Blocked,'COST_TYPES'):self.ex.readback()
        self.assertEqual(len(self.calls()),9)
        with self.assertRaises(FileExistsError):self.ex.readback()
        self.assertEqual(len(self.calls()),9)

    def test_modern_readback_uses_existing_bounded_requests_and_preserves_replay_guard(self):
        self.p3_apply()
        self.scenario['responses']['describe-budget']['Budget'] = modern_budget_fixture()
        self.save_scenario()
        result = self.ex.readback()['result']
        self.assertTrue(result['cost_scope_match'])
        self.assertTrue(result['scope_filters_absent'])
        self.assertEqual(len(self.calls()), 9)
        with self.assertRaises(FileExistsError): self.ex.readback()
        self.assertEqual(len(self.calls()), 9)

    def test_readback_rejects_billing_view_without_receipt_or_replay(self):
        self.p3_apply()
        budget = modern_budget_fixture()
        budget['BillingViewArn'] = f'arn:aws:billing::{b.ACCOUNT}:billingview/custom-synthetic'
        self.scenario['responses']['describe-budget']['Budget'] = budget
        self.save_scenario()
        with self.assertRaisesRegex(b.Blocked, 'BILLING_VIEW_PRESENT'):
            self.ex.readback()
        self.assertFalse((self.ex.op/'readback.receipt.json').exists())
        self.assertEqual(len(self.calls()), 9)
        with self.assertRaises(FileExistsError): self.ex.readback()
        self.assertEqual(len(self.calls()), 9)

    def test_postfreeze_scan_complete_snapshot_and_rerun(self):
        self.p3_apply();self.ex.readback()
        packet=self.repo/'docs/agent-runs/phase-12/evidence/fixture'
        packet.mkdir(parents=True);f=packet/'handoff.md';self.write(f,'public text')
        manifest=self.root/'freeze.json'
        def freeze():
            rows=[{'path':str(x.relative_to(self.repo)),'bytes':x.stat().st_size,'sha256':b.hash_file(x)} for x in packet.rglob('*') if x.is_file()]
            self.write(manifest,json.dumps({'root':str(packet.relative_to(self.repo)),'files':rows}))
            return b.hash_file(manifest)
        checksum=freeze();safe=self.ex.post_freeze_scan(manifest,checksum)
        self.assertEqual(safe['matches'],0);self.assertEqual(safe['files_scanned'],1)
        self.write(f,'modified public text')
        with self.assertRaisesRegex(b.Blocked,'RESCAN'):self.ex.post_freeze_scan(manifest,checksum)
        checksum=freeze();self.assertEqual(self.ex.post_freeze_scan(manifest,checksum)['matches'],0)
        self.write(packet/'extra.md','new content')
        with self.assertRaisesRegex(b.Blocked,'INCOMPLETE'):self.ex.post_freeze_scan(manifest,checksum)
        checksum=freeze();self.assertEqual(self.ex.post_freeze_scan(manifest,checksum)['files_scanned'],2)
        self.write(f,FIXTURE_ADDRESS)
        checksum=freeze()
        with self.assertRaisesRegex(b.Blocked,'PUBLIC_RECIPIENT_FOUND'):self.ex.post_freeze_scan(manifest,checksum)

    def test_private_recipient_not_in_cli_or_logs_receipts(self):
        self.p3_apply();self.ex.readback()
        for call in self.calls():self.assertNotIn(FIXTURE_ADDRESS,json.dumps(call['argv']))
        for f in self.ex.op.glob('*.receipt.json'):
            self.assertNotIn(FIXTURE_ADDRESS,f.read_text())
            self.assertNotIn(b.digest(FIXTURE_ADDRESS.encode()),f.read_text())

    def test_cli_rejects_dangerous_mode_and_root_overrides(self):
        with mock.patch.object(b,'production_policy',side_effect=AssertionError('must not be reached')):
            for args in (['destroy'],['apply','--primary','/tmp/x'],['test-mode']):
                with self.subTest(args=args),mock.patch('sys.stderr',new=io.StringIO()):
                    with self.assertRaises(SystemExit):b.main(args)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(b.Blocked,'DUPLICATE'):b.parse_json(b'{"a":1,"a":2}')

    def test_global_operation_lock_stops_parallel_command(self):
        self.ex.p3_check()
        self.write(self.primary/'.billing-wrapper-active.lock','occupied')
        with self.assertRaises(FileExistsError):self.ex.apply()
        self.assertEqual(len(self.calls()),2)

    def test_dirty_checkout_blocks(self):
        completed=mock.Mock(returncode=0,stdout=b'a'*40+b'\n')
        dirty=mock.Mock(returncode=0,stdout=b' M changed\n')
        with mock.patch.object(b.subprocess,'run',side_effect=[completed,dirty]):
            with self.assertRaisesRegex(b.Blocked,'DIRTY_CHECKOUT'):b.Execution.check_checkout(self.ex)

    def test_wrong_checkout_commit_blocks(self):
        with mock.patch.object(b.subprocess,'run',return_value=mock.Mock(returncode=0,stdout=b'wrong\n')):
            with self.assertRaisesRegex(b.Blocked,'SOURCE_COMMIT'):b.Execution.check_checkout(self.ex)

    def test_no_prior_receipt_modes_do_not_call_aws(self):
        operations=self.primary/'operations';operations.mkdir(mode=0o700)
        self.ex.op.mkdir(mode=0o700)
        for method in (self.ex.apply,self.ex.readback):
            with self.subTest(method=method.__name__):
                with self.assertRaises((b.Blocked,OSError)):method()
        self.assertEqual(self.calls(),[])

    def test_expired_window_does_not_call_aws(self):
        self.ex.now=lambda:NOW+timedelta(hours=2)
        with self.assertRaisesRegex(b.Blocked,'WINDOW_EXPIRED'):self.ex.p3_check()
        self.assertEqual(self.calls(),[])

    def test_scan_bounded_dirty_packet_only(self):
        script=self.repo/'scripts/billing/budget_execution.py'
        script.parent.mkdir(parents=True);self.write(script,'public script fixture')
        proposal=self.repo/b.PROPOSAL;proposal.parent.mkdir(parents=True);self.write(proposal,'proposal fixture')
        human=self.repo/b.HUMAN_RECORD;self.write(human,'human fixture')
        course=self.repo/'infra/terraform/environments/course.tfvars';course.parent.mkdir(parents=True)
        self.write(course,'enable_budget_resource = false\n')
        self.gate['wrapper_files']={'scripts/billing/budget_execution.py':b.hash_file(script)}
        self.pins['proposal_sha256']=b.hash_file(proposal)
        self.pins['human_record_sha256']=b.hash_file(human)
        self.gate['proposal_sha256']=self.pins['proposal_sha256']
        self.gate['human_record_sha256']=self.pins['human_record_sha256']
        self.ex=self.execution()
        def git_result(dirty):
            return [mock.Mock(returncode=0,stdout=b'a'*40+b'\n'),mock.Mock(returncode=0,stdout=dirty),mock.Mock(returncode=0,stdout=b'')]
        dirty=b'?? docs/agent-runs/phase-12/evidence/fixture/handoff.md\0'
        with mock.patch.object(b.subprocess,'run',side_effect=git_result(dirty)):
            b.Execution.check_checkout(self.ex,allow_packet=True)
        with mock.patch.object(b.subprocess,'run',side_effect=git_result(dirty)):
            with self.assertRaisesRegex(b.Blocked,'DIRTY_CHECKOUT'):b.Execution.check_checkout(self.ex)
        with mock.patch.object(b.subprocess,'run',side_effect=git_result(b' M scripts/billing/budget_execution.py\0')):
            with self.assertRaisesRegex(b.Blocked,'DIRTY_OUTSIDE_PACKET'):b.Execution.check_checkout(self.ex,allow_packet=True)

    def test_scan_scope_bound_to_gate(self):
        self.p3_apply();self.ex.readback()
        manifest=self.root/'freeze.json'
        self.write(manifest,json.dumps({'root':'docs/agent-runs/phase-12/evidence/wrong','files':[{}]}))
        with self.assertRaisesRegex(b.Blocked,'PUBLIC_FREEZE_GATE_SCOPE'):self.ex.post_freeze_scan(manifest,b.hash_file(manifest))

    def test_timeout_kills_child_group_and_stops(self):
        logs=self.primary/'logs';logs.mkdir(mode=0o700)
        process=mock.Mock(pid=54321)
        process.wait.side_effect=[b.subprocess.TimeoutExpired('fixture',1),0]
        process.poll.return_value=None
        with mock.patch.object(b.subprocess,'Popen',return_value=process),mock.patch.object(b.os,'killpg') as kill:
            with self.assertRaisesRegex(b.Blocked,'COMMAND_TIMEOUT'):b.PrivateRunner()([str(self.aws)],self.policy.config,self.policy.env(),logs,'timeout',1)
        kill.assert_called_once_with(54321,b.signal.SIGKILL)

    def test_apply_timeout_sigint_first_graceful_exit_without_group_kill(self):
        logs=self.primary/'grace logs';logs.mkdir(mode=0o700)
        process=mock.Mock(pid=54321);process.poll.return_value=None
        process.wait.side_effect=[b.subprocess.TimeoutExpired('fixture',1),0]
        with mock.patch.object(b.subprocess,'Popen',return_value=process),mock.patch.object(b.os,'killpg') as kill:
            with self.assertRaisesRegex(b.Blocked,'COMMAND_TIMEOUT'):
                b.PrivateRunner()(self.policy.apply_argv(),self.policy.config,self.policy.env(),logs,'graceful',1)
        process.send_signal.assert_called_once_with(b.signal.SIGINT)
        kill.assert_not_called()
        receipt=json.loads((logs/'graceful.termination.json').read_text())
        self.assertTrue(receipt['graceful_exit']);self.assertFalse(receipt['forced_kill'])
        self.assertLessEqual(process.wait.call_args_list[1].kwargs['timeout'],b.APPLY_GRACE_SECONDS)

    def test_apply_forced_kill_only_after_sigint_and_grace_timeout(self):
        logs=self.primary/'forced logs';logs.mkdir(mode=0o700)
        process=mock.Mock(pid=54321);process.poll.return_value=None
        events=[]
        def wait(**kwargs):
            events.append(('wait',kwargs['timeout']))
            if len([x for x in events if x[0]=='wait']) < 3:
                raise b.subprocess.TimeoutExpired('fixture',kwargs['timeout'])
            return -9
        process.wait.side_effect=wait
        process.send_signal.side_effect=lambda sig:events.append(('signal',sig))
        with mock.patch.object(b.subprocess,'Popen',return_value=process),mock.patch.object(b.os,'killpg',side_effect=lambda pid,sig:events.append(('kill',sig))):
            with self.assertRaisesRegex(b.Blocked,'COMMAND_TIMEOUT'):
                b.PrivateRunner()(self.policy.apply_argv(),self.policy.config,self.policy.env(),logs,'forced',1)
        self.assertEqual([x for x in events if x[0] in ('signal','kill')],[('signal',b.signal.SIGINT),('kill',b.signal.SIGKILL)])
        self.assertEqual([x[0] for x in events],['wait','signal','wait','kill','wait'])
        receipt=json.loads((logs/'forced.termination.json').read_text())
        self.assertTrue(receipt['forced_kill']);self.assertFalse(receipt['graceful_exit'])
        self.assertEqual(receipt['final_exit'],-9)

    def test_keyboard_interrupt_waits_gracefully_and_never_resends_sigint(self):
        logs=self.primary/'interrupt logs';logs.mkdir(mode=0o700)
        process=mock.Mock(pid=54321);process.poll.return_value=None
        process.wait.side_effect=[KeyboardInterrupt(),KeyboardInterrupt(),0]
        with mock.patch.object(b.subprocess,'Popen',return_value=process),mock.patch.object(b.os,'killpg') as kill:
            with self.assertRaisesRegex(b.Blocked,'COMMAND_INTERRUPTED'):
                b.PrivateRunner()(self.policy.apply_argv(),self.policy.config,self.policy.env(),logs,'interrupt',10)
        process.send_signal.assert_called_once_with(b.signal.SIGINT)
        kill.assert_not_called()
        self.assertEqual(process.wait.call_count,3)

    def test_apply_timeout_separate_and_reserves_window_headroom(self):
        calls=[]
        self.ex.runner=lambda *args:calls.append(args) or (0,b'',b'')
        self.ex.command(self.policy.apply_argv(),'apply')
        self.assertEqual(calls[-1][-1],b.APPLY_TIMEOUT_SECONDS)
        self.ex.command(self.policy.aws_argv('describe-budget'),'read')
        self.assertEqual(calls[-1][-1],b.READ_TIMEOUT_SECONDS)
        self.ex.gate['window_end']=b.iso(NOW+timedelta(seconds=90))
        self.ex.command(self.policy.apply_argv(),'apply')
        reserve=b.APPLY_GRACE_SECONDS+b.FORCED_REAP_SECONDS+b.LOCAL_PRESERVATION_HEADROOM_SECONDS
        self.assertEqual(calls[-1][-1],90-reserve)
        before=len(calls);self.ex.gate['window_end']=b.iso(NOW+timedelta(seconds=reserve))
        with self.assertRaisesRegex(b.Blocked,'HEADROOM_REQUIRED'):self.ex.command(self.policy.apply_argv(),'apply')
        self.assertEqual(len(calls),before)

    def test_success_at_window_edge_has_normal_backup_then_blocks_live(self):
        self.ex.p3_check();real_runner=self.ex.runner
        def window_edge(*args):
            result=real_runner(*args)
            self.ex.now=lambda:NOW+timedelta(minutes=31)
            return result
        self.ex.runner=window_edge
        with self.assertRaisesRegex(b.Blocked,'WINDOW_EXPIRED_AFTER_BACKUP'):
            self.ex.apply()
        backup=self.backups/'initial-ab9f141e83058209/billing.execution.tfstate'
        self.assertEqual(b.hash_file(backup),b.hash_file(self.policy.state))
        receipt=json.loads((self.ex.op/'apply.receipt.json').read_text())
        self.assertTrue(receipt['result']['backup_verified'])
        self.assertFalse(receipt['result']['window_open_for_further_live'])
        with self.assertRaisesRegex(b.Blocked,'WINDOW_EXPIRED'):self.ex.readback()
        self.assertEqual(len(self.calls()),3)

    def test_failed_apply_at_window_edge_preserves_partial_state(self):
        self.ex.p3_check();self.scenario['terraform_fail']=True;self.save_scenario()
        real_runner=self.ex.runner
        def window_edge(*args):
            result=real_runner(*args);self.ex.now=lambda:NOW+timedelta(minutes=31);return result
        self.ex.runner=window_edge
        with self.assertRaisesRegex(b.Blocked,'INCIDENT_REQUIRED'):self.ex.apply()
        receipt=json.loads((self.backups/'initial-ab9f141e83058209/preservation.receipt.json').read_text())
        self.assertIn('config/errored.tfstate',{x['source'] for x in receipt['artifacts']})
        self.assertTrue(all(x.get('equal') for x in receipt['artifacts']))
        self.assertEqual(len(self.calls()),3)

    def signal_fixture_launcher(self, ready):
        real_popen=b.subprocess.Popen
        def launch(*args,**kwargs):
            process=real_popen(*args,**kwargs)
            try:
                deadline=b.time.monotonic()+5
                while not ready.exists():
                    self.assertIsNone(process.poll(),'Signal fixture exited before readiness')
                    self.assertLess(b.time.monotonic(),deadline,'Signal fixture readiness timeout')
                    b.time.sleep(0.005)
                return process
            except BaseException:
                if process.poll() is None:
                    b.os.killpg(process.pid,b.signal.SIGKILL)
                    process.wait(timeout=5)
                raise
        return launch

    def test_real_local_child_sigint_persists_fixture_before_exit(self):
        # This is a Python signal fixture named terraform, never real Terraform/AWS.
        child=self.primary/'toolchain/terraform-signal-fixture'
        state=self.primary/'signal-fixture-state'
        ready=self.primary/'grace-fixture-ready'
        self.write(child,"#!/usr/bin/env python3\nimport pathlib,signal,time\np=pathlib.Path("+repr(str(state))+")\ndef stop(sig,frame):\n p.write_bytes(b'opaque gracefully persisted fixture');p.chmod(0o600)\n raise SystemExit(0)\nsignal.signal(signal.SIGINT,stop)\npathlib.Path("+repr(str(ready))+").write_text('ready')\nwhile True: time.sleep(0.01)\n",0o700)
        logs=self.primary/'real signal logs';logs.mkdir(mode=0o700)
        with mock.patch.object(b.subprocess,'Popen',side_effect=self.signal_fixture_launcher(ready)):
            with self.assertRaisesRegex(b.Blocked,'COMMAND_TIMEOUT'):
                b.PrivateRunner()([str(child),'apply'],self.policy.config,self.policy.env(),logs,'real-grace',0.2)
        self.assertTrue(state.exists())
        receipt=json.loads((logs/'real-grace.termination.json').read_text())
        self.assertTrue(receipt['graceful_exit']);self.assertFalse(receipt['forced_kill'])

    def test_real_local_child_forced_path_keeps_sigint_marker(self):
        child=self.primary/'toolchain/terraform-unresponsive-fixture'
        marker=self.primary/'sigint-marker'
        ready=self.primary/'force-fixture-ready'
        self.write(child,"#!/usr/bin/env python3\nimport pathlib,signal,time\np=pathlib.Path("+repr(str(marker))+")\ndef stop(sig,frame):\n p.write_bytes(b'opaque SIGINT observed');p.chmod(0o600)\nsignal.signal(signal.SIGINT,stop)\npathlib.Path("+repr(str(ready))+").write_text('ready')\nwhile True: time.sleep(0.01)\n",0o700)
        logs=self.primary/'real force logs';logs.mkdir(mode=0o700)
        with mock.patch.object(b.subprocess,'Popen',side_effect=self.signal_fixture_launcher(ready)):
            with mock.patch.object(b,'APPLY_GRACE_SECONDS',0.05):
                with self.assertRaisesRegex(b.Blocked,'COMMAND_TIMEOUT'):
                    b.PrivateRunner()([str(child),'apply'],self.policy.config,self.policy.env(),logs,'real-force',0.2)
        self.assertTrue(marker.exists())
        receipt=json.loads((logs/'real-force.termination.json').read_text())
        self.assertTrue(receipt['sigint_sent']);self.assertTrue(receipt['forced_kill'])
        self.assertEqual(receipt['final_exit'],-9)

    def test_interrupt_after_partial_write_preserves_without_retry(self):
        self.ex.p3_check()
        def interrupted(*args):
            self.write(self.policy.state,'opaque partial fixture')
            self.write(self.policy.config/'errored.tfstate','opaque recovery fixture')
            raise b.Blocked('COMMAND_INTERRUPTED_PARTIAL_POSSIBLE')
        self.ex.runner=interrupted
        with self.assertRaisesRegex(b.Blocked,'INCIDENT_REQUIRED'):self.ex.apply()
        backup=self.backups/'initial-ab9f141e83058209/preservation.receipt.json'
        result=json.loads(backup.read_text())
        self.assertEqual({x['source'] for x in result['artifacts']},{'billing.execution.tfstate','config/errored.tfstate'})
        self.assertTrue(all(x.get('equal') for x in result['artifacts']))
        with self.assertRaises(b.Blocked):self.ex.apply()
        self.assertEqual(len(self.calls()),2)

    def test_public_cli_failure_never_prints_private_stub_output(self):
        self.ex.p3_check();self.scenario['terraform_fail']=True;self.save_scenario()
        out=io.StringIO()
        with mock.patch.object(b,'production_policy',return_value=self.policy),mock.patch.object(b.Execution,'check_checkout',return_value=None),mock.patch.object(b,'stamp',return_value=NOW),mock.patch('sys.stdout',new=out):
            # Bind a production-default now factory for the injected safe fixture.
            with mock.patch.object(b.Execution,'check_window',return_value=None):
                self.assertEqual(b.main(['readback','--gate',str(self.gate_path),'--gate-sha256',b.hash_file(self.gate_path),'--operation','initial']),2)
        self.assertNotIn(FIXTURE_ADDRESS,out.getvalue())
        self.assertNotIn('Traceback',out.getvalue())

    def test_recipient_private_fixture(self):
        # This test also ensures the private-input format is one address only.
        self.write(self.primary/'notification.private.tfvars.json',json.dumps({'budget_notification_emails':[FIXTURE_ADDRESS]}))
        self.assertEqual(self.ex.private_recipient(),FIXTURE_ADDRESS)

    def execution(self):
        self.write(self.gate_path,json.dumps(self.gate))
        # Reserved local synthetic input only; real durable/private input is never accessed.
        self.write(self.primary/'notification.private.tfvars.json',json.dumps({'budget_notification_emails':[FIXTURE_ADDRESS]}))
        ex=b.Execution(self.policy,now=lambda:NOW).load_gate(self.gate_path,b.hash_file(self.gate_path),'initial')
        ex.check_checkout=lambda *args,**kwargs:None
        return ex


if __name__=='__main__':
    os.umask(0o077)
    unittest.main(verbosity=2)
