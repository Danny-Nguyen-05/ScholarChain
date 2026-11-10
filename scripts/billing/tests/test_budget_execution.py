#!/usr/bin/env python3
"""Credential-free features; every child process here is a local stub."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
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
 if sys.argv[1]=='show':
  print(json.dumps(scenario.get('plan_json',{})));sys.exit(scenario.get('show_exit',0))
 state=pathlib.Path(next(x.split('=',1)[1] for x in sys.argv if x.startswith('-state=')))
 if scenario.get('terraform_fail'):
  state.write_bytes(b'opaque partial state')
  state.chmod(0o600)
  for path in [state.with_name(state.name+'.backup'),root/'config/errored.tfstate',root/'.billing.execution.tfstate.lock.info']:
   path.write_bytes(b'opaque recovery fixture');path.chmod(0o600)
  sys.exit(1)
 if scenario.get('write_tf_backup') and state.exists():
  backup=state.with_name(state.name+'.backup');backup.write_bytes(b'unrelated bytes' if scenario.get('bad_tf_backup') else state.read_bytes());backup.chmod(0o600)
 if not scenario.get('apply_keeps_state'):
  state.write_bytes(b'opaque completed fixture state');state.chmod(0o600)
 (root/'applied').write_text('1')
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
responses=scenario['responses_after'] if ((root/'applied').exists() and 'responses_after' in scenario) else scenario['responses']
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


class NotificationReadCompatibility(unittest.TestCase):
    def validate(self, responses):
        return b.sanitize_readback(responses['describe-budget'], responses['list-tags-for-resource'],
            responses['describe-notifications-for-budget'],
            {int(k):v for k,v in responses['subscribers'].items()}, FIXTURE_ADDRESS)

    def test_absent_percentage_all_mixed_and_ordered_are_supported(self):
        for omitted in ((), (0,), (0, 1, 2)):
            for order in ((0,1,2),(2,0,1)):
                with self.subTest(omitted=omitted,order=order):
                    responses=fixture_responses()
                    notices=responses['describe-notifications-for-budget']['Notifications']
                    for index in omitted: del notices[index]['ThresholdType']
                    responses['describe-notifications-for-budget']['Notifications']=[notices[index] for index in order]
                    result=self.validate(responses)
                    self.assertEqual(result['notification_count'],3)
                    self.assertTrue(result['private_recipients_match'])
                    self.assertNotIn(FIXTURE_ADDRESS,json.dumps(result))
                    self.assertNotIn(b.digest(FIXTURE_ADDRESS.encode()),json.dumps(result))

    def test_present_invalid_threshold_type_never_defaults_to_percentage(self):
        for value in ('ABSOLUTE_VALUE','',None,False,0,[],{},'percentage','UNKNOWN'):
            with self.subTest(value=value):
                responses=fixture_responses();responses['describe-notifications-for-budget']['Notifications'][0]['ThresholdType']=value
                with self.assertRaisesRegex(b.Blocked,'NOTIFICATION_DRIFT'):self.validate(responses)

    def test_missing_percentage_keeps_operator_kind_threshold_shape_guards(self):
        cases=(('ComparisonOperator','LESS_THAN','NOTIFICATION_DRIFT'),('ComparisonOperator',None,'NOTIFICATION_DRIFT'),
               ('NotificationType','FORECASTED','NOTIFICATION_DRIFT'),('NotificationType',None,'NOTIFICATION_DRIFT'),
               ('Threshold',True,'NOTIFICATION_THRESHOLD'),('Threshold','50','NOTIFICATION_THRESHOLD'),
               ('Threshold',60,'NOTIFICATION_THRESHOLD'),('Unknown',FIXTURE_ADDRESS,'NOTIFICATION_SHAPE'))
        for key,value,code in cases:
            with self.subTest(key=key,value=value):
                responses=fixture_responses();notices=responses['describe-notifications-for-budget']['Notifications']
                for notice in notices:del notice['ThresholdType']
                notices[0][key]=value
                with self.assertRaisesRegex(b.Blocked,code) as error:self.validate(responses)
                self.assertNotIn(FIXTURE_ADDRESS,str(error.exception))
        responses=fixture_responses();notices=responses['describe-notifications-for-budget']['Notifications']
        for notice in notices:del notice['ThresholdType']
        notices[1]['Threshold']=notices[0]['Threshold']
        with self.assertRaisesRegex(b.Blocked,'NOTIFICATION_THRESHOLD'):self.validate(responses)
        notices.pop()
        with self.assertRaisesRegex(b.Blocked,'NOTIFICATION_COUNT'):self.validate(responses)

    def test_absent_percentage_never_weakens_subscriber_or_alarm_privacy(self):
        responses=fixture_responses()
        for notice in responses['describe-notifications-for-budget']['Notifications']:
            del notice['ThresholdType'];notice['NotificationState']='ALARM'
        result=self.validate(responses);self.assertNotIn('ALARM',json.dumps(result))
        responses['subscribers']['50']['Subscribers'][0]['Address']='wrong@example.invalid'
        with self.assertRaisesRegex(b.Blocked,'SUBSCRIBER_DRIFT'):self.validate(responses)


class Harness(unittest.TestCase):
    """Shared fixture: stub terraform/aws, private temp tree, create-flow gate."""
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

    def execution(self):
        self.write(self.gate_path,json.dumps(self.gate))
        # Reserved local synthetic input only; real durable/private input is never accessed.
        self.write(self.primary/'notification.private.tfvars.json',json.dumps({'budget_notification_emails':[FIXTURE_ADDRESS]}))
        ex=b.Execution(self.policy,now=lambda:NOW).load_gate(self.gate_path,b.hash_file(self.gate_path),'initial')
        ex.check_checkout=lambda *args,**kwargs:None
        return ex


class Features(Harness):
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


OTHER = 'other@example.invalid'  # synthetic reserved-domain fixture, never a real recipient


def usd25_responses():
    """Hand-derived USD 25 shape: amount 25, three ACTUAL ABSOLUTE_VALUE alerts at 10, 15, 20."""
    responses = fixture_responses()
    responses['describe-budget']['Budget']['BudgetLimit']['Amount'] = '25.0'
    responses['describe-notifications-for-budget']['Notifications'] = [
        b.expected_notification(x, 'ABSOLUTE_VALUE') for x in (10, 15, 20)]
    responses['subscribers'] = {str(x): {'Subscribers': [{'SubscriptionType': 'EMAIL', 'Address': FIXTURE_ADDRESS}]}
                                for x in (10, 15, 20)}
    return responses


def read_args(responses):
    return (responses['describe-budget'], responses['list-tags-for-resource'],
            responses['describe-notifications-for-budget'],
            {int(k): v for k, v in responses['subscribers'].items()}, FIXTURE_ADDRESS)


def plan_json(actions=('update',), after_over=None, before_over=None, notification='masked', extra=None):
    """Synthetic `show -json` plan; `variables` holds the private fixture recipient on purpose."""
    before = {'account_id': b.ACCOUNT, 'name': b.BUDGET, 'budget_type': 'COST', 'limit_amount': '200.0',
              'limit_unit': 'USD', 'time_unit': 'CUSTOM', 'time_period_start': '2026-10-01_00:00',
              'time_period_end': '2027-01-01_00:00', 'tags': dict(b.TAGS), 'tags_all': dict(b.TAGS),
              'cost_types': [{'include_credit': False, 'include_refund': False}], 'cost_filter': [],
              'filter_expression': []}
    after = {**before, 'limit_amount': '25', **(after_over or {})}
    before.update(before_over or {})
    change = {'actions': list(actions), 'before': before, 'after': after}
    if notification == 'masked':
        change['after_sensitive'] = {'notification': True}
    elif notification == 'visible':
        after['notification'] = [{'comparison_operator': 'GREATER_THAN', 'threshold': t,
                                  'threshold_type': 'ABSOLUTE_VALUE', 'notification_type': 'ACTUAL'}
                                 for t in (10, 15, 20)]
    elif notification != 'absent':
        after['notification'] = notification
    entry = {'address': b.MODIFY_ADDRESS, 'mode': 'managed', 'type': 'aws_budgets_budget', 'name': 'project',
             'index': 0, 'provider_name': 'registry.terraform.io/hashicorp/aws', 'change': change}
    plan = {'format_version': '1.2', 'terraform_version': '1.13.5', 'errored': False,
            'variables': {'budget_notification_emails': {'value': [FIXTURE_ADDRESS]}},
            'resource_changes': [entry]}
    plan.update(extra or {})
    return plan


def other_resource_entry():
    return {'address': 'aws_iam_role.other', 'mode': 'managed', 'type': 'aws_iam_role',
            'provider_name': 'registry.terraform.io/hashicorp/aws',
            'change': {'actions': ['create'], 'before': None, 'after': {}}}


class ModifyShapeFeatures(unittest.TestCase):
    """The single shape switch: initial (200, PERCENTAGE 50/80/100) versus usd25 (25, ABSOLUTE_VALUE 10/15/20)."""
    def test_usd25_shape_constants_are_hand_derived(self):
        self.assertEqual((b.USD25_SHAPE.amount, b.USD25_SHAPE.threshold_type, b.USD25_SHAPE.thresholds),
                         (25, 'ABSOLUTE_VALUE', (10, 15, 20)))
        self.assertEqual((b.INITIAL_SHAPE.amount, b.INITIAL_SHAPE.threshold_type, b.INITIAL_SHAPE.thresholds),
                         (200, 'PERCENTAGE', (50, 80, 100)))
        self.assertLess(max(b.USD25_SHAPE.thresholds), b.USD25_SHAPE.amount)

    def test_new_shape_passes_usd25_and_fails_the_default_initial_shape(self):
        result = b.sanitize_readback(*read_args(usd25_responses()), shape=b.USD25_SHAPE)
        self.assertEqual(result['notification_count'], 3)
        self.assertTrue(result['private_recipients_match'])
        self.assertNotIn(FIXTURE_ADDRESS, json.dumps(result))
        with self.assertRaisesRegex(b.Blocked, 'BUDGET_AMOUNT'):
            b.sanitize_readback(*read_args(usd25_responses()))

    def test_old_shape_fails_usd25_and_passes_initial(self):
        self.assertTrue(b.sanitize_readback(*read_args(fixture_responses()))['tags_match'])
        with self.assertRaisesRegex(b.Blocked, 'BUDGET_AMOUNT'):
            b.sanitize_readback(*read_args(fixture_responses()), shape=b.USD25_SHAPE)

    def test_usd25_amount_alone_with_old_alerts_fails(self):
        responses = fixture_responses(); responses['describe-budget']['Budget']['BudgetLimit']['Amount'] = '25'
        with self.assertRaisesRegex(b.Blocked, 'NOTIFICATION_THRESHOLD'):
            b.sanitize_readback(*read_args(responses), shape=b.USD25_SHAPE)

    def test_usd25_alert_mutations_each_fail_closed(self):
        def alert(index, **fields): return lambda r: r['describe-notifications-for-budget']['Notifications'][index].update(fields)
        cases = {
            'threshold_25': (alert(2, Threshold=25), 'NOTIFICATION_THRESHOLD'),
            'threshold_50_legacy': (alert(0, Threshold=50), 'NOTIFICATION_THRESHOLD'),
            'duplicate_threshold': (alert(1, Threshold=10), 'NOTIFICATION_THRESHOLD'),
            'percentage_type_left': (alert(0, ThresholdType='PERCENTAGE'), 'NOTIFICATION_DRIFT'),
            'type_omitted': (lambda r: r['describe-notifications-for-budget']['Notifications'][0].pop('ThresholdType'), 'NOTIFICATION_DRIFT'),
            'forecasted': (alert(1, NotificationType='FORECASTED'), 'NOTIFICATION_DRIFT'),
            'less_than': (alert(2, ComparisonOperator='LESS_THAN'), 'NOTIFICATION_DRIFT'),
            'only_two_alerts': (lambda r: r['describe-notifications-for-budget']['Notifications'].pop(), 'NOTIFICATION_COUNT'),
            'four_alerts': (lambda r: r['describe-notifications-for-budget']['Notifications'].append(b.expected_notification(5, 'ABSOLUTE_VALUE')), 'NOTIFICATION_COUNT'),
            'amount_200': (lambda r: r['describe-budget']['Budget']['BudgetLimit'].update(Amount='200'), 'BUDGET_AMOUNT'),
            'amount_26': (lambda r: r['describe-budget']['Budget']['BudgetLimit'].update(Amount='26'), 'BUDGET_AMOUNT'),
            'wrong_recipient': (lambda r: r['subscribers']['15']['Subscribers'][0].update(Address=OTHER), 'SUBSCRIBER_DRIFT'),
            'sns_subscriber': (lambda r: r['subscribers']['20']['Subscribers'][0].update(SubscriptionType='SNS'), 'SUBSCRIBER_DRIFT'),
            'tag_drift': (lambda r: r['list-tags-for-resource']['ResourceTags'][0].update(Value='wrong'), 'TAGS_DRIFT'),
            'date_drift': (lambda r: r['describe-budget']['Budget']['TimePeriod'].update(End='2027-01-02T00:00:00Z'), 'BUDGET_DATE'),
        }
        for name, (mutate, code) in cases.items():
            with self.subTest(name=name):
                responses = usd25_responses(); mutate(responses)
                with self.assertRaisesRegex(b.Blocked, code) as error:
                    b.sanitize_readback(*read_args(responses), shape=b.USD25_SHAPE)
                self.assertNotIn(FIXTURE_ADDRESS, str(error.exception))

    def test_initial_shape_still_rejects_absolute_value_alerts(self):
        responses = fixture_responses()
        responses['describe-notifications-for-budget']['Notifications'][0]['ThresholdType'] = 'ABSOLUTE_VALUE'
        with self.assertRaisesRegex(b.Blocked, 'NOTIFICATION_DRIFT'):
            b.sanitize_readback(*read_args(responses))

    def test_detect_shape_classifies_or_refuses_partial_states(self):
        old, new = fixture_responses(), usd25_responses()
        self.assertIs(b.detect_shape(old['describe-budget'], old['describe-notifications-for-budget']), b.INITIAL_SHAPE)
        self.assertIs(b.detect_shape(new['describe-budget'], new['describe-notifications-for-budget']), b.USD25_SHAPE)
        # An omitted ThresholdType means PERCENTAGE for the old shape only.
        omitted = fixture_responses()
        for n in omitted['describe-notifications-for-budget']['Notifications']: del n['ThresholdType']
        self.assertIs(b.detect_shape(omitted['describe-budget'], omitted['describe-notifications-for-budget']), b.INITIAL_SHAPE)
        omitted = usd25_responses()
        for n in omitted['describe-notifications-for-budget']['Notifications']: del n['ThresholdType']
        with self.assertRaisesRegex(b.Blocked, 'LIVE_STATE_UNEXPECTED'):
            b.detect_shape(omitted['describe-budget'], omitted['describe-notifications-for-budget'])
        with self.assertRaisesRegex(b.Blocked, 'LIVE_STATE_UNEXPECTED'):
            b.detect_shape(new['describe-budget'], new['describe-notifications-for-budget'], b.INITIAL_SHAPE)
        mixed = [(new['describe-budget'], old['describe-notifications-for-budget']),
                 (old['describe-budget'], new['describe-notifications-for-budget']),
                 ({'Budget': {'BudgetLimit': {'Amount': '100'}}}, old['describe-notifications-for-budget']),
                 ({'Budget': {}}, old['describe-notifications-for-budget']),
                 (old['describe-budget'], {'Notifications': old['describe-notifications-for-budget']['Notifications'][:2]}),
                 (old['describe-budget'], {'Notifications': 'x'}), ({}, {})]
        for budget, notifications in mixed:
            with self.subTest(budget=budget, notifications=notifications):
                with self.assertRaisesRegex(b.Blocked, 'LIVE_STATE_UNEXPECTED'):
                    b.detect_shape(budget, notifications)

    def test_committed_template_holds_a_placeholder_and_no_account_id_or_address(self):
        text = (ROOT/'modify-public-inputs.template.json').read_text()
        inputs = json.loads(text)
        self.assertEqual(inputs.pop('aws_account_id'), '<acct>')
        self.assertEqual(inputs.pop('budget_limit_usd'), 25)
        self.assertEqual(inputs, {'aws_profile': b.PROFILE, 'aws_region': b.REGION, 'budget_name': b.BUDGET,
            'project_period_start_utc': '2026-10-01_00:00', 'project_period_end_utc': '2027-01-01_00:00',
            'enable_budget': True, 'resource_tags': {k: b.TAGS[k] for k in ('course', 'project', 'environment', 'owner')}})
        self.assertNotRegex(text, r'[0-9]{12}'); self.assertNotIn('@', text)
        self.assertFalse((ROOT/'modify-public-inputs.json').exists())

    def test_documented_render_command_substitutes_only_the_account_and_prints_the_hash(self):
        readme = (ROOT/'README.md').read_text()
        match = re.search(r"python3 -I -c '(.*?)' scripts/billing/modify-public-inputs\.template\.json", readme, re.S)
        self.assertIsNotNone(match)
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch)/'rendered.json'
            run = lambda acct: subprocess.run([sys.executable, '-I', '-c', match.group(1), str(ROOT/'modify-public-inputs.template.json'), str(out)],
                                              capture_output=True, text=True, env={'ACCT': acct, 'PATH': '/usr/bin:/bin'})
            for bad in ('', '12345', '11112222333x', '1111222233334', '<acct>'):
                with self.subTest(bad=bad):
                    self.assertNotEqual(run(bad).returncode, 0); self.assertFalse(out.exists())
            result = run('111122223333')
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), b.hash_file(out))
            self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o600)
            rendered = json.loads(out.read_text()); template = json.loads((ROOT/'modify-public-inputs.template.json').read_text())
            self.assertEqual(rendered.pop('aws_account_id'), '111122223333'); template.pop('aws_account_id')
            self.assertEqual(rendered, template)
            self.assertNotEqual(run('111122223333').returncode, 0)  # exclusive create: never overwrites

    def test_initial_state_constants_match_the_verifier_pins(self):
        spec = importlib.util.spec_from_file_location('verification_pins', ROOT / 'budget_verification.py')
        v = importlib.util.module_from_spec(spec); sys.modules[spec.name] = v; spec.loader.exec_module(v)
        self.assertEqual((b.INITIAL_STATE_SHA256, b.INITIAL_STATE_BYTES), (v.STATE_SHA, v.STATE_BYTES))
        self.assertEqual(b.INITIAL_STATE_SHA256, '271fe888595b6d71eedb649b7cdb87686ded0b3cbb1e2b9a19f76d7575be3f67')


class ModifyPlanFeatures(unittest.TestCase):
    """Only an in-place update of aws_budgets_budget.project[0] from 200 to 25 is acceptable."""
    def check(self, plan): return b.check_modify_plan(plan)

    def test_in_place_update_is_accepted_masked_or_visible(self):
        for notification, visible in (('masked', False), ('visible', True)):
            with self.subTest(notification=notification):
                result = self.check(plan_json(notification=notification))
                self.assertEqual(result, {'address': 'aws_budgets_budget.project[0]', 'actions': ['update'],
                                          'notifications_visible': visible, 'amount_before': 200, 'amount_after': 25})
                self.assertNotIn(FIXTURE_ADDRESS, json.dumps(result))

    def test_decimal_amount_spellings_and_plan_time_formats_are_tolerated(self):
        plan = plan_json(after_over={'limit_amount': '25.00'}, before_over={'limit_amount': '200'})
        self.assertEqual(self.check(plan)['amount_after'], 25)
        times = {'time_period_start': '2026-10-01T00:00:00Z', 'time_period_end': '2027-01-01T00:00:00Z'}
        self.assertTrue(self.check(plan_json(after_over=times, before_over=times)))

    def test_create_delete_replace_and_noop_are_refused(self):
        cases = (('create',), ('delete',), ('delete', 'create'), ('create', 'delete'), ('no-op',), ('read',),
                 ('update', 'delete'), (), ('update', 'update'))
        expected = {('create',): 'PLAN_CREATE', ('delete',): 'PLAN_DELETE', ('delete', 'create'): 'PLAN_REPLACE',
                    ('create', 'delete'): 'PLAN_REPLACE', ('update', 'delete'): 'PLAN_DELETE'}
        for actions in cases:
            with self.subTest(actions=actions):
                with self.assertRaisesRegex(b.Blocked, expected.get(actions, 'PLAN_NOT_IN_PLACE_UPDATE')):
                    self.check(plan_json(actions))

    def test_replacement_markers_refuse_even_with_an_update_action(self):
        plan = plan_json(); plan['resource_changes'][0]['change']['replace_paths'] = [['name']]
        with self.assertRaisesRegex(b.Blocked, 'PLAN_REPLACE'): self.check(plan)
        plan = plan_json(); plan['resource_changes'][0]['action_reason'] = 'replace_because_cannot_update'
        with self.assertRaisesRegex(b.Blocked, 'PLAN_REPLACE'): self.check(plan)

    def test_any_other_resource_or_address_is_refused(self):
        extra = plan_json(); extra['resource_changes'].append(other_resource_entry())
        noop = plan_json()
        noop['resource_changes'].append({'address': 'aws_s3_bucket.x', 'mode': 'managed', 'type': 'aws_s3_bucket',
                                         'provider_name': 'registry.terraform.io/hashicorp/aws',
                                         'change': {'actions': ['no-op'], 'before': {}, 'after': {}}})
        for name, plan in (('extra_create', extra), ('extra_noop', noop),
                           ('no_changes', plan_json(extra={'resource_changes': []})),
                           ('missing', {'terraform_version': '1.13.5'})):
            with self.subTest(name=name):
                with self.assertRaisesRegex(b.Blocked, 'PLAN_NOT_SINGLE_RESOURCE'): self.check(plan)
        for key, value in (('address', 'aws_budgets_budget.project'), ('address', 'aws_budgets_budget.other[0]'),
                           ('type', 'aws_iam_role'), ('mode', 'data'), ('provider_name', 'registry.terraform.io/other/aws')):
            with self.subTest(key=key, value=value):
                plan = plan_json(); plan['resource_changes'][0][key] = value
                with self.assertRaisesRegex(b.Blocked, 'PLAN_NOT_BILLING_RESOURCE'): self.check(plan)

    def test_wrong_amounts_and_extra_attribute_changes_are_refused(self):
        for after, before in (({'limit_amount': '26'}, None), ({'limit_amount': '200'}, None), ({'limit_amount': '24'}, None),
                              (None, {'limit_amount': '100'}), ({'limit_amount': 'abc'}, None), ({'limit_amount': None}, None)):
            with self.subTest(after=after, before=before):
                with self.assertRaisesRegex(b.Blocked, 'PLAN_AMOUNT'): self.check(plan_json(after_over=after, before_over=before))
        changed = {'tags': dict(b.TAGS, owner='other'), 'time_period_end': '2027-02-01_00:00', 'name': 'other',
                   'cost_types': [{'include_credit': True}], 'budget_type': 'USAGE', 'limit_unit': 'GB',
                   'time_unit': 'MONTHLY', 'cost_filter': [{'name': 'Service'}], 'account_id': '111122223333'}
        for key, value in changed.items():
            with self.subTest(changed=key):
                with self.assertRaisesRegex(b.Blocked, 'PLAN_UNEXPECTED_ATTRIBUTE_CHANGE'):
                    self.check(plan_json(after_over={key: value}))

    def test_identity_date_and_tag_constants_are_enforced_when_unchanged(self):
        for key, value in (('name', 'other'), ('account_id', '111122223333'), ('budget_type', 'USAGE'),
                           ('limit_unit', 'GB'), ('time_unit', 'MONTHLY')):
            with self.subTest(key=key):
                with self.assertRaisesRegex(b.Blocked, 'PLAN_BUDGET_IDENTITY'):
                    self.check(plan_json(after_over={key: value}, before_over={key: value}))
        end = '2027-02-01_00:00'
        with self.assertRaisesRegex(b.Blocked, 'PLAN_BUDGET_DATE'):
            self.check(plan_json(after_over={'time_period_end': end}, before_over={'time_period_end': end}))
        tags = dict(b.TAGS, owner='other')
        with self.assertRaisesRegex(b.Blocked, 'PLAN_TAGS'):
            self.check(plan_json(after_over={'tags': tags}, before_over={'tags': tags}))

    def test_alert_blocks_must_be_masked_or_exactly_the_usd25_set(self):
        def visible(**kw):
            return [dict({'comparison_operator': 'GREATER_THAN', 'threshold': t, 'threshold_type': 'ABSOLUTE_VALUE',
                          'notification_type': 'ACTUAL'}, **kw) for t in (10, 15, 20)]
        bad = {'percentage_type': visible(threshold_type='PERCENTAGE'), 'forecasted': visible(notification_type='FORECASTED'),
               'less_than': visible(comparison_operator='LESS_THAN'),
               'old_thresholds': [dict(n, threshold=t) for n, t in zip(visible(), (50, 80, 100))],
               'top_threshold_25': [dict(n, threshold=t) for n, t in zip(visible(), (10, 15, 25))],
               'two_alerts': visible()[:2], 'empty': [], 'not_dicts': ['x', 'y', 'z']}
        for name, alerts in bad.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(b.Blocked, 'PLAN_NOTIFICATIONS'):
                    self.check(plan_json(notification=alerts))
        with self.assertRaisesRegex(b.Blocked, 'PLAN_NOTIFICATIONS'):  # absent and not marked sensitive
            self.check(plan_json(notification='absent'))

    def test_toolchain_and_error_flags_are_enforced_and_variables_never_echoed(self):
        for extra in ({'terraform_version': '1.14.0'}, {'terraform_version': None}):
            with self.assertRaisesRegex(b.Blocked, 'PLAN_TERRAFORM_VERSION'): self.check(plan_json(extra=extra))
        for extra in ({'errored': True}, {'deferred_changes': [{'reason': 'x'}]}):
            with self.assertRaisesRegex(b.Blocked, 'PLAN_ERRORED'): self.check(plan_json(extra=extra))
        for plan in (None, [], 'x'):
            with self.assertRaises(b.Blocked): self.check(plan)
        with self.assertRaises(b.Blocked) as error: self.check(plan_json(('delete', 'create')))
        self.assertNotIn(FIXTURE_ADDRESS, str(error.exception))


class ModifyFeatures(Harness):
    def setUp(self):
        super().setUp()
        self.initial = b'initial fixture state, opaque'
        for name, value in (('INITIAL_STATE_SHA256', b.digest(self.initial)), ('INITIAL_STATE_BYTES', len(self.initial))):
            patch = mock.patch.object(b, name, value); patch.start(); self.addCleanup(patch.stop)
        (self.primary/'operations').mkdir(mode=0o700)  # exists since Phase 12D
        self.write(self.primary/'billing.execution.tfstate', self.initial.decode())
        (self.backups/'initial-ab9f141e83058209').mkdir(mode=0o700)
        self.write(self.backups/b.INITIAL_BACKUP_RELATIVE, self.initial.decode())
        self.write(self.primary/'billing.modify.tfplan', 'public fake modify plan')
        (self.repo/'scripts/billing').mkdir(parents=True)
        shutil.copy(ROOT/'modify-public-inputs.template.json', self.repo/'scripts/billing/modify-public-inputs.template.json')
        self.render_inputs()
        self.pins['modify'] = {'plan_sha256': b.hash_file(self.primary/'billing.modify.tfplan'),
            'plan_bytes': (self.primary/'billing.modify.tfplan').stat().st_size,
            'public_input_sha256': b.hash_file(self.primary/'approved-public-inputs.modify.tfvars.json'),
            'config': [dict(self.pins['config'][0])]}
        self.scenario.update(plan_json=plan_json(), responses=fixture_responses(), responses_after=usd25_responses(),
                             write_tf_backup=True)
        self.save_scenario()
        self.record = 'docs/agent-runs/phase-14/budget-modify-human-gate.md'
        self.mgate = {'operation': 'modify-fixture', 'option': 'M', 'plan_sha256': self.pins['modify']['plan_sha256'],
            'proposal_sha256': self.pins['proposal_sha256'], 'wrapper_files': {'scripts/billing/budget_execution.py': '3'*64},
            'source_commit': 'a'*40, 'human_record_sha256': self.pins['human_record_sha256'],
            'g1_affirmation': 'A human statement fixture, no real approval.', 'actor_arn': b.CALLER,
            'account': b.ACCOUNT, 'profile': b.PROFILE, 'region': b.REGION,
            'window_start': b.iso(NOW-timedelta(minutes=5)), 'window_end': b.iso(NOW+timedelta(minutes=30)),
            'timezone': 'America/Chicago', 'login_at': b.iso(NOW-timedelta(minutes=4)),
            'human_sts_observed_at': b.iso(NOW-timedelta(minutes=3)), 'human_sts': {'Account': b.ACCOUNT, 'Arn': b.CALLER},
            'permissions': sorted(b.MODIFY_ACTIONS), 'retention_accepted': True, 'modify_review_approved': True,
            'state_backup_confirmed': True, 'aws_cli_sha256': b.hash_file(self.aws),
            'public_packet_root': 'docs/agent-runs/phase-14/evidence/14b/budget-modify-fixture',
            'modify_record_path': self.record, 'modify_record_sha256': '4'*64,
            'prior_state_sha256': b.INITIAL_STATE_SHA256, 'prior_state_bytes': b.INITIAL_STATE_BYTES}
        self.mex = self.modify_execution()

    def modify_execution(self, gate=None):
        gate = gate or self.mgate
        self.write(self.gate_path, json.dumps(gate))
        ex = b.Execution(self.policy, now=lambda: NOW)
        ex.load_modify_gate(self.gate_path, b.hash_file(self.gate_path), gate['operation'])
        ex.check_checkout = lambda *args, **kwargs: None
        ex.check_modify_record = lambda: None
        return ex

    def fresh(self):
        self.tearDown(); self.setUp()

    def render_inputs(self, **changes):
        """Render the private inputs from the committed template, as the documented human command does."""
        rendered = json.loads((self.repo/'scripts/billing/modify-public-inputs.template.json').read_text())
        rendered['aws_account_id'] = b.ACCOUNT  # the ID comes from the code constant, never from a literal here
        rendered.update(changes)
        path = self.primary/'approved-public-inputs.modify.tfvars.json'
        if path.exists(): path.unlink()
        self.write(path, json.dumps(rendered, indent=2) + '\n')
        if 'modify' in self.pins: self.pins['modify']['public_input_sha256'] = b.hash_file(path)

    def terraform_calls(self): return [c['argv'][1] for c in self.calls() if Path(c['argv'][0]).name.startswith('terraform')]
    def aws_ops(self): return [c['argv'][2] for c in self.calls() if not Path(c['argv'][0]).name.startswith('terraform')]
    def backup_dir(self): return self.backups/'modify-fixture'

    def test_in_place_update_succeeds_and_verifies_the_new_shape(self):
        receipt = self.mex.modify(); result = receipt['result']
        self.assertTrue(result['applied']); self.assertFalse(result['already_at_target'])
        self.assertEqual(result['plan']['actions'], ['update'])
        self.assertEqual(result['verify']['notification_count'], 3)
        self.assertTrue(result['verify']['private_recipients_match'])
        calls = self.calls()
        self.assertEqual(len(calls), 14)  # show + six pre reads + apply + six post reads
        self.assertEqual(calls[0]['argv'], self.policy.show_argv())
        self.assertEqual(calls[7]['argv'], self.policy.modify_apply_argv())
        self.assertEqual(self.terraform_calls(), ['show', 'apply'])
        self.assertEqual(self.aws_ops()[:6], ['describe-budget', 'list-tags-for-resource', 'describe-notifications-for-budget']+['describe-subscribers-for-notification']*3)
        def selectors(rows): return [(x['Threshold'], x['ThresholdType']) for x in
                                     (json.loads(c['argv'][c['argv'].index('--notification')+1]) for c in rows if '--notification' in c['argv'])]
        self.assertEqual(selectors(calls[:7]), [(50, 'PERCENTAGE'), (80, 'PERCENTAGE'), (100, 'PERCENTAGE')])
        self.assertEqual(selectors(calls[8:]), [(10, 'ABSOLUTE_VALUE'), (15, 'ABSOLUTE_VALUE'), (20, 'ABSOLUTE_VALUE')])
        self.assertEqual({k: v for k, v in calls[7]['env'].items() if k not in ('LC_CTYPE', '__CF_USER_TEXT_ENCODING')}, self.policy.env())
        self.assertEqual(calls[7]['cwd'], str(self.policy.config))
        self.assertNotIn('AWS_ACCESS_KEY_ID', calls[7]['env'])
        self.assertFalse((self.primary/'.billing-wrapper-active.lock').exists())
        for stage in ('modify-apply', 'modify'):
            self.assertTrue((self.mex.op/f'{stage}.receipt.json').exists())
        text = json.dumps(receipt)
        self.assertNotIn(FIXTURE_ADDRESS, text); self.assertNotIn(b.digest(FIXTURE_ADDRESS.encode()), text)

    def test_versioned_pre_and_post_state_backups_are_opaque_private_and_exact(self):
        receipt = self.mex.modify()['result']
        pre, post = self.backup_dir()/'pre-apply.billing.execution.tfstate', self.backup_dir()/'post-apply.billing.execution.tfstate'
        self.assertEqual(b.hash_file(pre), b.INITIAL_STATE_SHA256)
        self.assertEqual(b.hash_file(post), b.hash_file(self.policy.state))
        self.assertNotEqual(b.hash_file(post), b.INITIAL_STATE_SHA256)
        self.assertEqual((receipt['pre_backup']['sha256'], receipt['post_backup']['sha256']), (b.hash_file(pre), b.hash_file(post)))
        self.assertTrue(receipt['pre_backup']['equal'] and receipt['post_backup']['fsync_completed'])
        for path in (pre, post):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.backup_dir().stat().st_mode), 0o700)
        # The Phase 12D initial backup is untouched.
        self.assertEqual(b.hash_file(self.backups/b.INITIAL_BACKUP_RELATIVE), b.INITIAL_STATE_SHA256)

    def test_pre_apply_backup_precedes_apply(self):
        order = []
        original_copy, original_command = b.opaque_copy, b.Execution.command
        with mock.patch.object(b, 'opaque_copy', side_effect=lambda *a, **k: (order.append('copy'), original_copy(*a, **k))[1]), \
             mock.patch.object(b.Execution, 'command', autospec=True, side_effect=lambda ex, argv, label: (order.append(label), original_command(ex, argv, label))[1]):
            self.mex.modify()
        self.assertLess(order.index('copy'), order.index('modify-apply'))
        self.assertEqual(order.count('copy'), 2)

    def test_already_at_target_applies_nothing(self):
        self.scenario['responses'] = usd25_responses(); self.save_scenario()
        result = self.mex.modify()['result']
        self.assertEqual((result['applied'], result['already_at_target']), (False, True))
        self.assertEqual(self.terraform_calls(), ['show'])
        self.assertEqual(len(self.calls()), 7)
        self.assertFalse(self.backup_dir().exists())
        self.assertEqual(b.hash_file(self.policy.state), b.INITIAL_STATE_SHA256)

    def test_unexpected_live_state_refuses_before_any_backup_or_apply(self):
        def amount(value): return lambda r: r['describe-budget']['Budget']['BudgetLimit'].update(Amount=value)
        cases = {
            'amount_100': (amount('100'), 'LIVE_STATE_UNEXPECTED'),
            'amount_25_old_alerts': (amount('25'), 'LIVE_STATE_UNEXPECTED'),
            'amount_200_new_alerts': (lambda r: r['describe-notifications-for-budget'].update(
                Notifications=usd25_responses()['describe-notifications-for-budget']['Notifications']), 'LIVE_STATE_UNEXPECTED'),
            'two_old_alerts': (lambda r: r['describe-notifications-for-budget']['Notifications'].pop(), 'LIVE_STATE_UNEXPECTED'),
            'old_alert_threshold_changed': (lambda r: r['describe-notifications-for-budget']['Notifications'][0].update(Threshold=60), 'LIVE_STATE_UNEXPECTED'),
            'credits_included': (lambda r: r['describe-budget']['Budget']['CostTypes'].update(IncludeCredit=True), 'COST_TYPES'),
            'wrong_recipient': (lambda r: r['subscribers']['50']['Subscribers'][0].update(Address=OTHER), 'SUBSCRIBER_DRIFT'),
            'tag_drift': (lambda r: r['list-tags-for-resource']['ResourceTags'][0].update(Value='wrong'), 'TAGS_DRIFT'),
            'unhealthy': (lambda r: r['describe-budget']['Budget']['HealthStatus'].update(Status='UNHEALTHY'), 'BUDGET_HEALTH_UNVERIFIED'),
        }
        for name, (mutate, code) in cases.items():
            with self.subTest(name=name):
                ex = self.modify_execution({**self.mgate, 'operation': f'modify-live-{name}'})
                responses = fixture_responses(); mutate(responses)
                self.scenario['responses'] = responses; self.save_scenario()
                with self.assertRaisesRegex(b.Blocked, code) as error: ex.modify()
                self.assertNotIn(FIXTURE_ADDRESS, str(error.exception))
                self.assertNotIn('apply', self.terraform_calls())
                self.assertFalse((self.backups/f'modify-live-{name}').exists())
                self.assertEqual(b.hash_file(self.policy.state), b.INITIAL_STATE_SHA256)

    def test_non_update_plans_and_other_resources_refuse_after_exactly_one_show(self):
        extra = plan_json(); extra['resource_changes'].append(other_resource_entry())
        cases = {'create': (plan_json(('create',)), 'PLAN_CREATE'), 'delete': (plan_json(('delete',)), 'PLAN_DELETE'),
                 'replace': (plan_json(('delete', 'create')), 'PLAN_REPLACE'), 'create_before_destroy': (plan_json(('create', 'delete')), 'PLAN_REPLACE'),
                 'noop': (plan_json(('no-op',)), 'PLAN_NOT_IN_PLACE_UPDATE'), 'non_billing': (extra, 'PLAN_NOT_SINGLE_RESOURCE'),
                 'amount_26': (plan_json(after_over={'limit_amount': '26'}), 'PLAN_AMOUNT'), 'show_fails': (None, 'PLAN_SHOW_FAILED')}
        for name, (plan, code) in cases.items():
            with self.subTest(name=name):
                ex = self.modify_execution({**self.mgate, 'operation': f'modify-plan-{name}'})
                if plan is None: self.scenario['show_exit'] = 1
                else: self.scenario.pop('show_exit', None); self.scenario['plan_json'] = plan
                self.save_scenario(); before = len(self.calls())
                with self.assertRaisesRegex(b.Blocked, code): ex.modify()
                self.assertEqual(len(self.calls())-before, 1)  # only the offline show ran: no AWS call, no apply
                self.assertNotIn('apply', self.terraform_calls())
                self.assertFalse((self.backups/f'modify-plan-{name}').exists())

    def test_unapproved_plan_inputs_config_or_toolchain_refuse_before_any_process(self):
        cases = {'plan_bytes_changed': lambda: self.write(self.primary/'billing.modify.tfplan', 'changed'),
                 'inputs_changed': lambda: self.write(self.primary/'approved-public-inputs.modify.tfvars.json', '{"budget_limit_usd": 200}'),
                 'plan_mode': lambda: (self.primary/'billing.modify.tfplan').chmod(0o644),
                 'plan_missing': lambda: (self.primary/'billing.modify.tfplan').unlink(),
                 'config_drift': lambda: self.write(self.primary/'config/main.tf', 'edited config copy'),
                 'config_extra_file': lambda: self.write(self.primary/'config/override.tf', 'resource "x" "y" {}'),
                 'terraform_binary_changed': lambda: self.write(self.primary/'toolchain/terraform-1.13.5', STUB+'\n#', 0o700)}
        for name, damage in cases.items():
            with self.subTest(name=name):
                damage()
                with self.assertRaises((b.Blocked, OSError)): self.mex.modify()
                self.assertEqual(self.calls(), [])
                self.assertFalse(self.mex.op.exists())
                self.fresh()

    def test_same_size_plan_with_other_bytes_fails_the_hash_not_only_the_size(self):
        original = (self.primary/'billing.modify.tfplan').read_bytes()
        other = original[:-1] + (b'4' if original[-1:] != b'4' else b'5')
        self.assertEqual(len(other), len(original))
        self.write(self.primary/'billing.modify.tfplan', other.decode())
        with self.assertRaisesRegex(b.Blocked, 'ARTIFACT_HASH'): self.mex.modify()
        self.assertEqual(self.calls(), [])
        self.fresh()
        self.write(self.primary/'approved-public-inputs.modify.tfvars.json', '{"budget_limit_usd": 2500}')  # inputs file: other bytes, no size pin
        with self.assertRaisesRegex(b.Blocked, 'ARTIFACT_HASH'): self.mex.modify()
        self.assertEqual(self.calls(), [])

    def test_rendered_inputs_must_match_the_template_and_the_live_account(self):
        template = json.loads((self.repo/'scripts/billing/modify-public-inputs.template.json').read_text())
        cases = {'account_other': ({'aws_account_id': '111122223333'}, 'MODIFY_INPUTS_ACCOUNT'),
                 'account_short': ({'aws_account_id': '12345'}, 'MODIFY_INPUTS_ACCOUNT'),
                 'account_placeholder': ({'aws_account_id': '<acct>'}, 'MODIFY_INPUTS_ACCOUNT'),
                 'account_not_string': ({'aws_account_id': int(b.ACCOUNT)}, 'MODIFY_INPUTS_ACCOUNT'),
                 'amount_200': ({'budget_limit_usd': 200}, 'MODIFY_INPUTS_DRIFT'),
                 'amount_float': ({'budget_limit_usd': 25.0}, 'MODIFY_INPUTS_DRIFT'),
                 'budget_disabled': ({'enable_budget': False}, 'MODIFY_INPUTS_DRIFT'),
                 'other_name': ({'budget_name': 'other'}, 'MODIFY_INPUTS_DRIFT'),
                 'other_end': ({'project_period_end_utc': '2027-02-01_00:00'}, 'MODIFY_INPUTS_DRIFT'),
                 'other_tag': ({'resource_tags': dict(template['resource_tags'], owner='other')}, 'MODIFY_INPUTS_DRIFT'),
                 'extra_key': ({'extra': 1}, 'MODIFY_INPUTS_SHAPE')}
        for name, (changes, code) in cases.items():
            with self.subTest(name=name):
                self.render_inputs(**changes)  # the pin follows the file, so only the content checks can refuse
                with self.assertRaisesRegex(b.Blocked, code): self.mex.modify()
                self.assertEqual(self.calls(), [])
        self.render_inputs()
        rendered = json.loads((self.primary/'approved-public-inputs.modify.tfvars.json').read_text()); del rendered['aws_profile']
        self.write(self.primary/'approved-public-inputs.modify.tfvars.json', json.dumps(rendered)); self.pins['modify']['public_input_sha256'] = b.hash_file(self.primary/'approved-public-inputs.modify.tfvars.json')
        with self.assertRaisesRegex(b.Blocked, 'MODIFY_INPUTS_SHAPE'): self.mex.modify()
        self.render_inputs()
        (self.repo/'scripts/billing/modify-public-inputs.template.json').write_text('{"aws_account_id": "<acct>"}')
        with self.assertRaisesRegex(b.Blocked, 'MODIFY_INPUTS_SHAPE'): self.mex.modify()
        self.assertEqual(self.calls(), [])

    def test_plan_size_and_pins_are_enforced(self):
        self.pins['modify']['plan_bytes'] += 1
        with self.assertRaisesRegex(b.Blocked, 'PLAN_SIZE'): self.mex.modify()
        self.assertEqual(self.calls(), [])
        for mutate, code in ((lambda p: p.pop('modify'), 'MODIFY_PINS_MISSING'),
                             (lambda p: p['modify'].pop('plan_sha256'), 'MODIFY_PINS_MISSING'),
                             (lambda p: p['modify'].update(plan_sha256='nothex'), 'MODIFY_PINS_MISSING'),
                             (lambda p: p['modify'].update(config=[]), 'MODIFY_PINS_MISSING'),
                             (lambda p: p['modify'].update(plan_sha256=p['plan_sha256']), 'MODIFY_PLAN_IS_CREATE_PLAN')):
            with self.subTest(code=code):
                saved = copy.deepcopy(self.pins)
                mutate(self.pins)
                with self.assertRaisesRegex(b.Blocked, code):
                    b.Execution(self.policy, now=lambda: NOW).load_modify_gate(self.gate_path, b.hash_file(self.gate_path), 'modify-fixture')
                self.pins.clear(); self.pins.update(saved)

    def test_state_must_still_be_the_phase_12d_state(self):
        cases = {'state_changed': lambda: self.write(self.policy.state, 'edited state'),
                 'backup_changed': lambda: self.write(self.backups/b.INITIAL_BACKUP_RELATIVE, 'edited backup'),
                 'state_missing': lambda: self.policy.state.unlink(),
                 'terraform_backup_present': lambda: self.write(self.primary/'billing.execution.tfstate.backup', 'x'),
                 'lock_file_present': lambda: self.write(self.primary/'.billing.execution.tfstate.lock.info', 'x'),
                 'errored_state_present': lambda: self.write(self.primary/'config/errored.tfstate', 'x')}
        for name, damage in cases.items():
            with self.subTest(name=name):
                damage()
                with self.assertRaises((b.Blocked, OSError)): self.mex.modify()
                self.assertEqual(self.calls(), [])
                self.fresh()

    def test_gate_refuses_wrong_operation_option_identity_window_permissions_and_state(self):
        cases = [('operation', 'initial'), ('operation', 'modify-'), ('option', 'B'), ('plan_sha256', '0'*64),
                 ('actor_arn', 'wrong'), ('account', '000000000000'), ('permissions', sorted(b.ACTIONS)),
                 ('permissions', sorted(b.MODIFY_ACTIONS)[:-1]), ('window_end', b.iso(NOW-timedelta(seconds=1))),
                 ('g1_affirmation', ''), ('modify_review_approved', False), ('state_backup_confirmed', False),
                 ('retention_accepted', False), ('prior_state_sha256', '0'*64), ('prior_state_bytes', 1),
                 ('public_packet_root', 'docs/agent-runs/phase-12/evidence/fixture'),
                 ('modify_record_path', 'docs/agent-runs/phase-12/billing-bootstrap-exception.md'),
                 ('modify_record_path', 'docs/agent-runs/phase-14/evidence/14b/self.md'),
                 ('modify_record_path', '../escape.md'), ('modify_record_sha256', 'nothex'), ('source_commit', 'nothex'),
                 ('proposal_sha256', '0'*64), ('human_record_sha256', '0'*64), ('timezone', 'UTC')]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                gate = {**self.mgate, field: value}
                self.write(self.gate_path, json.dumps(gate))
                operation = value if field == 'operation' else 'modify-fixture'
                with self.assertRaises(b.Blocked):
                    b.Execution(self.policy, now=lambda: NOW).load_modify_gate(self.gate_path, b.hash_file(self.gate_path), operation)
        gate = {**self.mgate, 'surprise': 1}
        self.write(self.gate_path, json.dumps(gate))
        with self.assertRaisesRegex(b.Blocked, 'GATE_SCHEMA'):
            b.Execution(self.policy, now=lambda: NOW).load_modify_gate(self.gate_path, b.hash_file(self.gate_path), 'modify-fixture')
        gate = dict(self.mgate); del gate['option']
        self.write(self.gate_path, json.dumps(gate))
        with self.assertRaisesRegex(b.Blocked, 'GATE_SCHEMA'):
            b.Execution(self.policy, now=lambda: NOW).load_modify_gate(self.gate_path, b.hash_file(self.gate_path), 'modify-fixture')
        with self.assertRaisesRegex(b.Blocked, 'GATE_HASH'):
            b.Execution(self.policy, now=lambda: NOW).load_modify_gate(self.gate_path, '0'*64, 'modify-fixture')
        self.assertEqual(self.calls(), [])

    def test_create_gate_cannot_authorize_modify_and_modify_gate_cannot_authorize_create(self):
        self.write(self.gate_path, json.dumps(self.gate))
        with self.assertRaises(b.Blocked):
            b.Execution(self.policy, now=lambda: NOW).load_modify_gate(self.gate_path, b.hash_file(self.gate_path), 'initial')
        with self.assertRaisesRegex(b.Blocked, 'GATE_SCHEMA'):
            b.Execution(self.policy, now=lambda: NOW).load_modify_gate(self.gate_path, b.hash_file(self.gate_path), 'modify-fixture')
        self.write(self.gate_path, json.dumps(self.mgate))
        with self.assertRaisesRegex(b.Blocked, 'GATE_SCHEMA'):
            b.Execution(self.policy, now=lambda: NOW).load_gate(self.gate_path, b.hash_file(self.gate_path), 'modify-fixture')
        # A create-flow Execution cannot call modify without a modify gate.
        with self.assertRaisesRegex(b.Blocked, 'MODIFY_GATE_REQUIRED'): self.ex.modify()
        self.assertEqual(self.calls(), [])

    def test_modify_is_single_use(self):
        self.mex.modify(); before = len(self.calls())
        with self.assertRaisesRegex(b.Blocked, 'STATE_NOT_INITIAL'): self.modify_execution().modify()
        self.assertEqual(len(self.calls()), before)
        with self.assertRaises(FileExistsError): self.mex.op.mkdir(mode=0o700)

    def test_window_expiry_after_backup_stops_further_live_requests(self):
        clock = [NOW]
        self.mex.now = lambda: clock[0]
        original = b.Execution.command
        def command(ex, argv, label):
            result = original(ex, argv, label)
            if label == 'modify-apply': clock[0] = NOW + timedelta(minutes=31)
            return result
        with mock.patch.object(b.Execution, 'command', autospec=True, side_effect=command):
            with self.assertRaisesRegex(b.Blocked, 'WINDOW_EXPIRED_AFTER_BACKUP_NO_FURTHER_LIVE'): self.mex.modify()
        self.assertTrue((self.backup_dir()/'post-apply.billing.execution.tfstate').exists())
        self.assertTrue((self.mex.op/'modify-apply.receipt.json').exists())
        self.assertFalse((self.mex.op/'modify.receipt.json').exists())
        self.assertEqual(self.terraform_calls(), ['show', 'apply'])
        self.assertEqual(len(self.calls()), 8)

    def test_apply_failure_preserves_recovery_artifacts_and_stops_without_retry(self):
        self.scenario['terraform_fail'] = True; self.save_scenario()
        with self.assertRaisesRegex(b.Blocked, 'MODIFY_APPLY_OR_BACKUP_FAILED_INCIDENT_REQUIRED'): self.mex.modify()
        self.assertEqual(len(self.calls()), 8)  # show, six pre reads, failed apply; no post read, no retry
        receipt = json.loads((self.backup_dir()/'preservation.receipt.json').read_text())
        names = {x['source'] for x in receipt['artifacts']}
        self.assertIn('billing.execution.tfstate', names); self.assertIn('config/errored.tfstate', names)
        self.assertTrue(receipt['incident_required'])
        self.assertTrue((self.backup_dir()/'pre-apply.billing.execution.tfstate').exists())
        self.assertFalse((self.mex.op/'modify.receipt.json').exists())
        # A retry is refused by the leftover recovery files (and, past them, by the consumed operation).
        with self.assertRaises(b.Blocked): self.mex.modify()
        self.assertEqual(len(self.calls()), 8)
        with self.assertRaises(FileExistsError): self.mex.op.mkdir(mode=0o700)

    def test_unchanged_state_or_foreign_terraform_backup_after_apply_is_an_incident(self):
        for flag, operation in (('apply_keeps_state', 'modify-same-state'), ('bad_tf_backup', 'modify-bad-backup')):
            with self.subTest(flag=flag):
                ex = self.modify_execution({**self.mgate, 'operation': operation})
                self.scenario[flag] = True; self.save_scenario()
                with self.assertRaisesRegex(b.Blocked, 'INCIDENT_REQUIRED'): ex.modify()
                self.assertFalse((ex.op/'modify.receipt.json').exists())
                self.assertTrue((self.backups/operation/'preservation.receipt.json').exists())
                self.fresh()

    def test_applied_but_old_shape_still_live_fails_the_post_verify_and_keeps_backups(self):
        self.scenario['responses_after'] = fixture_responses(); self.save_scenario()
        with self.assertRaisesRegex(b.Blocked, 'APPLIED_BUT_POST_VERIFY_FAILED:LIVE_STATE_UNEXPECTED'): self.mex.modify()
        self.assertTrue((self.mex.op/'modify-apply.receipt.json').exists())
        self.assertFalse((self.mex.op/'modify.receipt.json').exists())
        self.assertTrue((self.backup_dir()/'post-apply.billing.execution.tfstate').exists())

    def test_post_verify_requires_the_exact_usd25_shape(self):
        broken = usd25_responses(); broken['describe-notifications-for-budget']['Notifications'][2]['Threshold'] = 25
        self.scenario['responses_after'] = broken; self.save_scenario()
        with self.assertRaisesRegex(b.Blocked, 'APPLIED_BUT_POST_VERIFY_FAILED:LIVE_STATE_UNEXPECTED'): self.mex.modify()
        self.assertFalse((self.mex.op/'modify.receipt.json').exists())

    def test_terraform_is_only_ever_show_or_apply_of_the_modify_plan(self):
        self.mex.modify()
        for call in self.calls():
            if Path(call['argv'][0]).name.startswith('terraform'):
                self.assertIn(call['argv'][1], ('show', 'apply'))
                self.assertEqual(call['argv'][-1], str(self.policy.modify_plan))
                for banned in ('destroy', 'import', '-auto-approve', '-replace', '-target', 'plan', 'state', '-refresh=false'):
                    self.assertNotIn(banned, call['argv'])
            else:
                self.assertIn(call['argv'][2], ('describe-budget', 'list-tags-for-resource', 'describe-notifications-for-budget', 'describe-subscribers-for-notification'))

    def test_human_record_must_be_a_committed_file_with_the_gated_hash(self):
        def git(*args):
            return subprocess.run(['/usr/bin/git', '-C', str(self.repo), *args], check=True, capture_output=True,
                                  env={'PATH': '/usr/bin:/bin', 'HOME': str(self.root), 'GIT_CONFIG_GLOBAL': '/dev/null'})
        git('init', '-q')
        ex = b.Execution(self.policy, now=lambda: NOW)
        record = self.repo/self.record; record.parent.mkdir(parents=True); record.write_text('human gate record fixture')
        self.write(self.gate_path, json.dumps({**self.mgate, 'modify_record_sha256': b.hash_file(record)}))
        ex.load_modify_gate(self.gate_path, b.hash_file(self.gate_path), 'modify-fixture')
        with self.assertRaisesRegex(b.Blocked, 'MODIFY_RECORD_UNTRACKED'): ex.check_modify_record()
        git('add', '.'); git('-c', 'user.name=Fixture', '-c', 'user.email=fixture-no-address', 'commit', '-qm', 'fixture')
        ex.check_modify_record()
        record.write_text('edited after the gate was written')
        with self.assertRaisesRegex(b.Blocked, 'MODIFY_RECORD_HASH'): ex.check_modify_record()
        record.unlink()
        with self.assertRaisesRegex(b.Blocked, 'MODIFY_RECORD_MISSING'): ex.check_modify_record()

    def test_cli_modify_prints_only_fixed_public_fields_and_refuses_scan_options(self):
        argv = ['modify', '--gate', str(self.gate_path), '--gate-sha256', b.hash_file(self.gate_path), '--operation', 'modify-fixture']
        out = io.StringIO()
        with mock.patch.object(b, 'production_policy', return_value=self.policy), \
             mock.patch.object(b.Execution.__init__, '__defaults__', (None, lambda: NOW)), \
             mock.patch.object(b.Execution, 'check_checkout', return_value=None), \
             mock.patch.object(b.Execution, 'check_modify_record', return_value=None), mock.patch('sys.stdout', new=out):
            self.assertEqual(b.main(argv), 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload['stage'], 'modify'); self.assertTrue(payload['result']['applied'])
        self.assertNotIn(FIXTURE_ADDRESS, out.getvalue()); self.assertNotIn('Traceback', out.getvalue())
        out = io.StringIO()
        with mock.patch.object(b, 'production_policy', return_value=self.policy), mock.patch('sys.stdout', new=out):
            self.assertEqual(b.main(argv + ['--public-manifest', 'x', '--public-manifest-sha256', '0'*64]), 2)
        self.assertIn('UNEXPECTED_SCAN_OPTIONS', out.getvalue())

    def test_show_output_is_the_only_terraform_stdout_ever_returned(self):
        logs = self.primary/'runner logs'; logs.mkdir(mode=0o700)
        code, out, _ = b.PrivateRunner()(self.policy.show_argv(), self.policy.config, self.policy.env(), logs, 'show', 30)
        self.assertEqual(code, 0); self.assertIn(b'resource_changes', out)
        code, out, _ = b.PrivateRunner()(self.policy.modify_apply_argv(), self.policy.config, self.policy.env(), logs, 'apply', 30)
        self.assertEqual((code, out), (0, b''))

    def test_cli_exposes_modify_as_the_only_new_mode(self):
        with mock.patch('sys.stderr', new=io.StringIO()), self.assertRaises(SystemExit):
            b.main(['plan', '--gate', 'x', '--gate-sha256', 'x', '--operation', 'x'])
        with mock.patch('sys.stderr', new=io.StringIO()), self.assertRaises(SystemExit):
            b.main(['destroy', '--gate', 'x', '--gate-sha256', 'x', '--operation', 'x'])


if __name__=='__main__':
    os.umask(0o077)
    unittest.main(verbosity=2)
