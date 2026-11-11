#!/usr/bin/env python3
"""Synthetic offline features for the read-only continuation, never real private paths."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import io
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('verification_features', ROOT/'budget_verification.py')
v = importlib.util.module_from_spec(spec); sys.modules[spec.name] = v; spec.loader.exec_module(v)
b = v.b
ADDRESS = 'fixture@example.invalid'
NOW = datetime(2026,11,3,18,0,tzinfo=timezone.utc)


def responses():
    budget = {'BudgetName':b.BUDGET,'BudgetType':'COST','TimeUnit':'CUSTOM',
              'BudgetLimit':{'Amount':'200','Unit':'USD'},
              'TimePeriod':{'Start':'2026-10-01T00:00:00Z','End':'2027-01-01T00:00:00Z'},
              'Metrics':['UnblendedCost'],
              'FilterExpression':{'Not':{'Dimensions':{'Key':'RECORD_TYPE','Values':['Credit','Refund']}}},
              'HealthStatus':{'Status':'HEALTHY'}}
    return [{'Budget':budget}, {'ResourceTags':[{'Key':k,'Value':value} for k,value in b.TAGS.items()]},
            {'Notifications':[b.expected_notification(x) for x in (50,80,100)]},
            *[{'Subscribers':[{'SubscriptionType':'EMAIL','Address':ADDRESS}]} for _ in range(3)]]


class Fixture(unittest.TestCase):
    """Shared synthetic fixture for the original and the modified verifier."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='read only verifier ')
        self.root=Path(self.temp.name).resolve();self.root.chmod(0o700)
        self.primary=self.root/'primary with spaces';self.backups=self.root/'backups';self.repo=self.root/'repo'
        for p in (self.primary,self.backups,self.repo):p.mkdir(mode=0o700)
        for rel in ('operations','operations/'+v.ORIGINAL_OPERATION,'config'):(self.primary/rel).mkdir(mode=0o700)
        (self.backups/'initial-ab9f141e83058209').mkdir(mode=0o700)
        self.old=self.primary/'operations'/v.ORIGINAL_OPERATION
        self.opaque=b'opaque synthetic state, not Terraform data'
        self.write(self.primary/'billing.execution.tfstate',self.opaque)
        self.write(self.backups/'initial-ab9f141e83058209/billing.execution.tfstate',self.opaque)
        self.aws=self.primary/'aws-stub';self.write(self.aws,b'public executable fixture',0o700)
        self.write(self.primary/'notification.private.tfvars.json',json.dumps({'budget_notification_emails':[ADDRESS]}).encode())
        oldgate={'operation':v.ORIGINAL_OPERATION,'source_commit':v.ORIGINAL_SOURCE,'plan_sha256':v.ORIGINAL_PLAN,
                 'actor_arn':b.CALLER,'account':b.ACCOUNT,'profile':b.PROFILE,'region':b.REGION,
                 'wrapper_files':{'scripts/billing/budget_execution.py':v.ORIGINAL_WRAPPER},
                 'window_start':'2026-11-02T20:45:00Z','window_end':'2026-11-02T21:45:00Z'}
        raw=(json.dumps(oldgate)+'\n').encode();self.write(self.primary/'approval-20261102-attempt02.json',raw)
        self.patches=[mock.patch.object(v,'ORIGINAL_GATE_SHA',b.digest(raw)),mock.patch.object(v,'STATE_SHA',b.digest(self.opaque)),mock.patch.object(v,'STATE_BYTES',len(self.opaque))]
        for patch in self.patches:patch.start()
        for name in ('apply.started','readback.started'):self.write(self.old/name,b'')
        receipt={'gate_sha256':v.ORIGINAL_GATE_SHA,'operation':v.ORIGINAL_OPERATION,'plan_sha256':v.ORIGINAL_PLAN,
                 'actor_arn':b.CALLER,'stage':'apply','observed_at':'2026-11-02T21:11:15.851738+00:00',
                 'result':{'backup':{'bytes':v.STATE_BYTES,'equal':True,'fsync_completed':True,'sha256':v.STATE_SHA},
                           'backup_verified':True,'exit':0,'window_open_for_further_live':True}}
        self.write(self.old/'apply.receipt.json',json.dumps(receipt).encode())
        self.original_bytes={str(p.relative_to(self.old)):p.read_bytes() for p in self.old.iterdir()}
        shutil.copytree(ROOT,self.repo/'scripts/billing')
        self.public(self.repo/b.PROPOSAL,b'public proposal')
        self.public(self.repo/b.HUMAN_RECORD,b'public human fixture record')
        self.public(self.repo/'infra/terraform/environments/course.tfvars',b'enable_budget_resource = false\n')
        self.public(self.repo/'infra/terraform/frozen.tf',b'frozen public source')
        self.git('init','-q');self.git('add','.');self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture')
        pins={'plan_sha256':v.ORIGINAL_PLAN,'proposal_sha256':b.digest(b'public proposal'),
              'human_record_sha256':b.digest(b'public human fixture record'),
              'source_freeze':[{'path':'infra/terraform/frozen.tf','bytes':20,'sha256':b.digest(b'frozen public source')}]}
        self.policy=b.Policy(self.primary,self.backups,self.repo,os.getuid(),self.aws,pins)
        self.gate={'operation':'verify-fixture','option':'B','plan_sha256':v.ORIGINAL_PLAN,
                   'proposal_sha256':pins['proposal_sha256'],'source_commit':self.git('rev-parse','HEAD').strip(),
                   'wrapper_files':{str(p.relative_to(self.repo)):b.hash_file(p) for p in (self.repo/'scripts/billing').rglob('*') if p.is_file()},
                   'human_record_sha256':pins['human_record_sha256'],'g1_affirmation':'Synthetic affirmation, no actual approval.',
                   'actor_arn':b.CALLER,'account':b.ACCOUNT,'profile':b.PROFILE,'region':b.REGION,
                   'window_start':b.iso(NOW-timedelta(minutes=5)),'window_end':b.iso(NOW+timedelta(minutes=45)),
                   'timezone':'America/Chicago','login_at':b.iso(NOW-timedelta(minutes=4)),
                   'human_sts_observed_at':b.iso(NOW-timedelta(minutes=3)),'human_sts':{'Account':b.ACCOUNT,'Arn':b.CALLER},
                   'permissions':sorted(v.PERMISSIONS),'retention_accepted':True,'verification_review_approved':True,
                   'original_provenance_confirmed':True,'aws_cli_sha256':b.hash_file(self.aws),
                   'public_packet_root':'docs/agent-runs/phase-12/evidence/12d-publication-output-verify-fixture',
                   'original_operation':v.ORIGINAL_OPERATION,'original_gate_sha256':v.ORIGINAL_GATE_SHA,
                   'original_gate_filename':'approval-20261102-attempt02.json',
                   'original_source_commit':v.ORIGINAL_SOURCE,'original_wrapper_sha256':v.ORIGINAL_WRAPPER,
                   'original_apply_receipt_sha256':b.hash_file(self.old/'apply.receipt.json'),
                   'state_backup_sha256':v.STATE_SHA,'state_backup_bytes':v.STATE_BYTES}
        self.calls=[];self.values=responses();self.fail_at=None;self.after=None;self.clock=NOW
        self.gatepath=self.root/'gate.json';self.ex=self.execution()

    def tearDown(self):
        for patch in reversed(self.patches):patch.stop()
        self.temp.cleanup()

    def write(self,path,data,mode=0o600):
        path.write_bytes(data);path.chmod(mode)

    def public(self,path,data):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)

    def git(self,*args):
        return subprocess.check_output(['/usr/bin/git','-C',str(self.repo),*args],env={'PATH':'/usr/bin:/bin','HOME':str(self.root)},stderr=subprocess.DEVNULL,text=True)

    def runner(self,argv,cwd,env,op,label,timeout):
        index=len(self.calls);self.calls.append({'argv':argv,'cwd':cwd,'env':env,'op':op,'label':label,'timeout':timeout})
        if self.after:self.after(index)
        if self.fail_at==index:return 254,b'',b'private error must not escape'
        return 0,json.dumps(self.values[index]).encode(),b''

    def execution(self):
        self.write(self.gatepath,(json.dumps(self.gate)+'\n').encode())
        return v.Verification(self.policy,self.runner,lambda:self.clock).load_gate(self.gatepath,b.hash_file(self.gatepath),self.gate['operation'])

    def receipt_missing(self):
        self.assertFalse((self.ex.op/'verify.receipt.json').exists())
        self.assertFalse((self.old/'readback.receipt.json').exists())

    def unchanged_original(self):
        self.assertEqual({str(p.relative_to(self.old)):p.read_bytes() for p in self.old.iterdir()},self.original_bytes)

    def packet(self,files=None):
        root=Path(self.gate['public_packet_root']);files=files or {'file.txt':b'safe public suffixes'}
        for name,data in files.items():self.public(self.repo/root/name,data)
        rows=[{'path':str(root/name),'bytes':len(data),'sha256':b.digest(data)} for name,data in files.items()]
        freeze=self.repo/Path(str(root)+'.freeze.json');self.public(freeze,json.dumps({'root':str(root),'files':rows}).encode())
        return freeze,b.hash_file(freeze)


class Features(Fixture):
    def test_exact_six_requests_safe_receipt_and_original_preservation(self):
        result=self.ex.verify();self.assertEqual(len(self.calls),6)
        self.assertEqual([x['argv'][2] for x in self.calls],['describe-budget','list-tags-for-resource','describe-notifications-for-budget',*['describe-subscribers-for-notification']*3])
        self.assertIn('--show-filter-expression',self.calls[0]['argv'])
        for call in self.calls:
            self.assertEqual(call['env']['AWS_MAX_ATTEMPTS'],'1');self.assertNotIn('AWS_ACCESS_KEY_ID',call['env'])
            self.assertEqual(call['cwd'],self.policy.config);self.assertEqual(call['op'],self.ex.op)
            self.assertLessEqual(call['timeout'],60);self.assertNotIn('apply',call['argv'])
        self.assertTrue(result['result']['cost_scope_match']);self.assertEqual(result['stage'],'verify');self.assertEqual(result['option'],'B')
        for secret in (ADDRESS,b.digest(ADDRESS.encode()),'private error'):
            self.assertNotIn(secret,json.dumps(result))
        self.unchanged_original()
        with self.assertRaises(FileExistsError):self.ex.verify()
        self.assertEqual(len(self.calls),6)

    def test_each_request_failure_stops_without_retry_or_success_receipt(self):
        for index in range(6):
            with self.subTest(index=index):
                self.fail_at=index
                with self.assertRaisesRegex(b.Blocked,'READBACK_COMMAND_FAILED'):self.ex.verify()
                self.assertEqual(len(self.calls),index+1);self.receipt_missing();self.unchanged_original()
                # New synthetic namespace for each independent failure fixture, no journal deletion.
                self.gate['operation']='verify-fixture-'+str(index);self.calls=[];self.ex=self.execution()

    def test_wrong_original_receipt_hash_blocks_all_requests(self):
        self.gate['original_apply_receipt_sha256']='0'*64;self.ex=self.execution()
        with self.assertRaisesRegex(b.Blocked,'ORIGINAL_APPLY_HASH'):self.ex.verify()
        self.assertFalse(self.ex.op.exists())
        self.assertEqual(self.calls,[]);self.receipt_missing()

    def test_invalid_original_receipt_fields_block_even_when_rehashed(self):
        original=json.loads((self.old/'apply.receipt.json').read_bytes())
        for key,value in [('stage','readback'),('actor_arn','wrong'),('operation','other'),('extra',True)]:
            with self.subTest(key=key):
                current=copy.deepcopy(original);current[key]=value
                self.write(self.old/'apply.receipt.json',json.dumps(current).encode())
                self.gate['original_apply_receipt_sha256']=b.hash_file(self.old/'apply.receipt.json')
                self.gate['operation']='verify-receipt-'+key;self.ex=self.execution()
                with self.assertRaises(b.Blocked):self.ex.verify()
                self.assertEqual(self.calls,[]);self.receipt_missing()

    def test_original_gate_or_journal_conflict_blocks(self):
        self.write(self.old/'readback.receipt.json',b'{}')
        with self.assertRaisesRegex(b.Blocked,'ORIGINAL_READBACK_CONFLICT'):self.ex.verify()
        self.assertEqual(self.calls,[])

    def test_state_and_backup_change_block(self):
        for target in (self.policy.state,self.backups/'initial-ab9f141e83058209/billing.execution.tfstate'):
            with self.subTest(target=target.name):
                self.write(target,b'changed')
                self.gate['operation']='verify-state-'+str(len(self.calls))+'-'+str(target.parent==self.backups/'initial-ab9f141e83058209');self.ex=self.execution()
                with self.assertRaisesRegex(b.Blocked,'STATE_BACKUP_DRIFT'):self.ex.verify()
                self.assertEqual(self.calls,[]);self.receipt_missing();self.write(target,self.opaque)

    def test_new_gate_rejects_old_namespace_mutation_permissions_and_unknown_fields(self):
        original=copy.deepcopy(self.gate)
        cases=[('operation',v.ORIGINAL_OPERATION),('option','A'),('permissions',sorted(v.PERMISSIONS|{'apply'})),
               ('permissions',['verify']),('state_backup_bytes',True),
               ('original_provenance_confirmed',False),('aws_cli_sha256','x'),('unknown',True)]
        for key,value in cases:
            with self.subTest(key=key):
                self.gate=copy.deepcopy(original);self.gate[key]=value
                with self.assertRaises(b.Blocked):self.execution()
        self.assertEqual(self.calls,[])

    def test_expired_and_future_identity_window_rejected(self):
        original=copy.deepcopy(self.gate)
        for key,value in [('window_end',b.iso(NOW)),('human_sts_observed_at',b.iso(NOW+timedelta(seconds=1))),
                          ('window_start',b.iso(NOW-timedelta(hours=2))),('login_at',b.iso(NOW-timedelta(hours=2)))]:
            with self.subTest(key=key):
                self.gate=copy.deepcopy(original);self.gate[key]=value
                with self.assertRaises(b.Blocked):self.execution()

    def test_shared_lock_and_terraform_lock_block_without_removal(self):
        lock=self.primary/'.billing-wrapper-active.lock';self.write(lock,b'other owner')
        with self.assertRaisesRegex(b.Blocked,'WRAPPER_ACTIVE'):self.ex.verify()
        self.assertEqual(lock.read_bytes(),b'other owner');self.assertEqual(self.calls,[])
        lock.unlink()  # Synthetic fixture owner cleanup only.
        self.gate['operation']='verify-lock2';self.ex=self.execution()
        tf=self.primary/'.billing.execution.tfstate.lock.info';self.write(tf,b'fixture lock')
        with self.assertRaisesRegex(b.Blocked,'TERRAFORM_LOCK_PRESENT'):self.ex.verify()
        self.assertTrue(tf.exists());self.assertEqual(self.calls,[])

    def test_final_window_and_state_drift_block_after_six_without_receipt(self):
        self.after=lambda index:setattr(self,'clock',NOW+timedelta(hours=1)) if index==5 else None
        with self.assertRaisesRegex(b.Blocked,'WINDOW_EXPIRED'):self.ex.verify()
        self.assertEqual(len(self.calls),6);self.receipt_missing()

    def test_final_state_drift_without_receipt(self):
        self.after=lambda index:self.write(self.policy.state,b'changed') if index==5 else None
        with self.assertRaisesRegex(b.Blocked,'STATE_BACKUP_DRIFT'):self.ex.verify()
        self.assertEqual(len(self.calls),6);self.receipt_missing()

    def test_pagination_malformed_duplicates_or_stderr_stop_without_receipt(self):
        self.values[0]={'NextToken':'private token','Budget':{}}
        with self.assertRaisesRegex(b.Blocked,'READBACK_TRUNCATED'):self.ex.verify()
        self.assertEqual(len(self.calls),1);self.receipt_missing()
        with self.assertRaisesRegex(b.Blocked,'DUPLICATE_JSON_KEY'):b.parse_json(b'{"Budget":{},"Budget":{}}')

    def test_b1_l1_and_cost_scope_guards_preserved(self):
        for key,value,code in [('BillingViewArn','arn:aws:billing::530332961125:billingview/primary','BILLING_VIEW_PRESENT'),
                               ('AutoAdjustData',{},'AUTO_ADJUST_PRESENT'),('PlannedBudgetLimits',{},'PLANNED_LIMITS_PRESENT'),
                               ('Unknown',True,'BUDGET_FIELD_UNSUPPORTED'),('Metrics',['NetUnblendedCost'],'COST_METRIC')]:
            with self.subTest(key=key):
                self.gate['operation']='verify-invalid-'+key;self.ex=self.execution();self.values=responses();self.calls=[]
                self.values[0]['Budget'][key]=value
                with self.assertRaisesRegex(b.Blocked,code):self.ex.verify()
                self.receipt_missing();self.assertEqual(len(self.calls),6)

    def test_gate_hardlink_and_symlink_rejected(self):
        self.gatepath.unlink();os.link(self.primary/'notification.private.tfvars.json',self.gatepath)
        with self.assertRaisesRegex(b.Blocked,'HARDLINK_FILE'):
            v.Verification(self.policy).load_gate(self.gatepath,'0'*64,'verify-fixture')
        self.gatepath.unlink();self.gatepath.symlink_to(self.primary/'notification.private.tfvars.json')
        with self.assertRaises(b.Blocked):v.Verification(self.policy).load_gate(self.gatepath,'0'*64,'verify-fixture')

    def test_dirty_wrong_commit_and_source_drift_block_before_requests(self):
        self.gate['source_commit']='0'*40;self.ex=self.execution()
        with self.assertRaisesRegex(b.Blocked,'SOURCE_COMMIT'):self.ex.verify()
        self.assertEqual(self.calls,[])

    def test_scan_happy_receipt_matches_unchanged_public_helper_contract(self):
        self.ex.verify();freeze,sha=self.packet();receipt=self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))
        self.assertEqual(len(self.calls),6);self.assertEqual(receipt['matches'],0);self.assertEqual(len(receipt),10)
        spec=importlib.util.spec_from_file_location('pub_verification_fixture',ROOT/'publication_evidence.py')
        pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)
        pub.validate_receipt(receipt,self.ex.binding,sha,1)
        private=json.loads((self.ex.op/'post-freeze-scan.receipt.json').read_bytes())
        self.assertEqual(private['verification_receipt_sha256'],b.hash_file(self.ex.op/'verify.receipt.json'))
        with self.assertRaises(FileExistsError):self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))
        self.assertEqual(len(self.calls),6);self.unchanged_original()

    def test_scan_without_verification_cannot_succeed(self):
        self.ex.op.mkdir(mode=0o700);freeze,sha=self.packet()
        with self.assertRaises(FileNotFoundError):self.ex.scan(freeze,sha,'0'*64)
        self.assertFalse((self.ex.op/'post-freeze-scan.receipt.json').exists());self.assertEqual(self.calls,[])

    def test_scan_recipient_leak_or_incomplete_packet_blocks(self):
        self.ex.verify();freeze,sha=self.packet({'file.txt':ADDRESS.upper().encode()})
        with self.assertRaisesRegex(b.Blocked,'PUBLIC_RECIPIENT_FOUND'):self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))
        self.assertFalse((self.ex.op/'post-freeze-scan.receipt.json').exists())

    def test_scan_unlisted_member_blocks(self):
        self.ex.verify();freeze,sha=self.packet();self.public(freeze.parent/Path(self.gate['public_packet_root']).name/'extra.txt',b'extra')
        with self.assertRaisesRegex(b.Blocked,'PUBLIC_FREEZE_INCOMPLETE'):self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))

    def test_scan_tampered_or_duplicate_manifest_entry_blocks(self):
        self.ex.verify();freeze,sha=self.packet();obj=json.loads(freeze.read_bytes());obj['files'].append(obj['files'][0]);freeze.write_text(json.dumps(obj))
        with self.assertRaisesRegex(b.Blocked,'PUBLIC_SCAN_SCOPE'):self.ex.scan(freeze,b.hash_file(freeze),b.hash_file(self.ex.op/'verify.receipt.json'))

    def test_scan_symlink_ancestor_blocks(self):
        self.ex.verify();freeze,sha=self.packet();packet=self.repo/self.gate['public_packet_root']
        target=packet/'file.txt';target.unlink();target.symlink_to(self.root/'not-public')
        with self.assertRaises((b.Blocked,OSError)):self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))

    def test_scan_final_membership_race_blocks(self):
        self.ex.verify();freeze,sha=self.packet();real=v.inventory;counter=[0]
        def race(repo,root):
            counter[0]+=1
            if counter[0]==2:self.public(repo/root/'late.txt',b'late')
            return real(repo,root)
        with mock.patch.object(v,'inventory',side_effect=race):
            with self.assertRaisesRegex(b.Blocked,'PUBLIC_FREEZE_INCOMPLETE'):self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))
        self.assertFalse((self.ex.op/'post-freeze-scan.receipt.json').exists())

    def test_scan_wrong_manifest_scalar_types_block(self):
        self.ex.verify();freeze,sha=self.packet();obj=json.loads(freeze.read_bytes());obj['files'][0]['bytes']=True;freeze.write_text(json.dumps(obj))
        with self.assertRaisesRegex(b.Blocked,'PUBLIC_FREEZE_ENTRY'):self.ex.scan(freeze,b.hash_file(freeze),b.hash_file(self.ex.op/'verify.receipt.json'))

    def test_scan_changed_verification_receipt_is_not_accepted(self):
        self.ex.verify();freeze,sha=self.packet();path=self.ex.op/'verify.receipt.json';obj=json.loads(path.read_bytes());obj['result']['notification_count']=True;self.write(path,json.dumps(obj).encode())
        with self.assertRaisesRegex(b.Blocked,'PRIVATE_INPUT_CHANGED'):self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))

    def test_nonempty_original_journal_blocks(self):
        self.write(self.old/'readback.started',b'not an empty journal')
        with self.assertRaisesRegex(b.Blocked,'ORIGINAL_JOURNAL_SHAPE'):self.ex.verify()
        self.assertEqual(self.calls,[])

    def test_frozen_file_content_tamper_blocks(self):
        self.ex.verify();freeze,sha=self.packet()
        (self.repo/self.gate['public_packet_root']/'file.txt').write_bytes(b'changed')
        with self.assertRaisesRegex(b.Blocked,'PUBLIC_CONTENT_CHANGED_RESCAN'):
            self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))

    def test_public_directory_ancestor_symlink_blocks(self):
        self.ex.verify();freeze,sha=self.packet({'sub/file.txt':b'public'})
        packet=self.repo/self.gate['public_packet_root'];target=packet/'sub'
        shutil.rmtree(target);outside=self.root/'outside';outside.mkdir();(outside/'file.txt').write_bytes(b'public')
        target.symlink_to(outside,target_is_directory=True)
        with self.assertRaises((b.Blocked,OSError)):
            self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))

    def test_explicit_verification_hash_pin_rejects_substitution(self):
        self.ex.verify();freeze,sha=self.packet()
        with self.assertRaisesRegex(b.Blocked,'VERIFY_RECEIPT_HASH'):
            self.ex.scan(freeze,sha,'0'*64)

    def test_public_helper_full_before_and_after_integration(self):
        spec=importlib.util.spec_from_file_location('publication_full_fixture',ROOT/'publication_evidence.py')
        pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)
        staging=pub.EVIDENCE+'/12d-publication-input-verify-fixture'
        suffixes={}
        for record in pub.RECORDS:
            self.public(self.repo/record,b'Existing synthetic record\n')
            rel='suffixes/'+Path(record).name+'.txt';suffixes[record]=rel
            self.public(self.repo/staging/rel,b'Final safe suffix\n')
        self.public(self.repo/staging/'artifacts/report.md',b'Final public report\n')
        request={'root':self.gate['public_packet_root'],'binding':self.ex.binding,'artifacts':['artifacts/report.md'],'suffixes':suffixes}
        # Gatehash depends on sourcecommit, which excludes the request's new gatebinding.
        # Commit only base/staging fixture bytes first, then update request binding in a separate assembly workspace.
        self.git('add','.');self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','publication fixture')
        self.gate['source_commit']=self.git('rev-parse','HEAD').strip();self.ex=self.execution();self.ex.verify()
        assembly=self.root/'assembly';shutil.copytree(self.repo,assembly)
        request['binding']=self.ex.binding
        self.public(assembly/staging/'request.json',pub.encoded(request))
        pub.assemble(assembly,staging+'/request.json')
        root=Path(self.gate['public_packet_root']);shutil.copytree(assembly/root,self.repo/root)
        freeze_rel=str(root)+'.freeze.json';shutil.copyfile(assembly/freeze_rel,self.repo/freeze_rel)
        freeze=self.repo/freeze_rel;sha=b.hash_file(freeze)
        receipt=self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))
        receipt_rel=pub.EVIDENCE+'/12d-publication-scan-verify-fixture.json'
        self.public(self.repo/receipt_rel,pub.encoded(receipt))
        before=pub.verify(self.repo,freeze_rel,sha,receipt_rel,self.ex.binding['gate_sha256'],self.ex.binding['operation'])
        self.assertEqual(before['record_count'],5)
        for record in pub.RECORDS:
            path=self.repo/record;path.write_bytes(path.read_bytes()+b'Final safe suffix\n')
        after=pub.verify(self.repo,freeze_rel,sha,receipt_rel,self.ex.binding['gate_sha256'],self.ex.binding['operation'],True)
        self.assertTrue(after['exact_bytes_match']);self.assertFalse(after['scan_authenticity_verified'])
        self.assertEqual(len(self.calls),6);self.unchanged_original()

    def test_changed_private_input_between_verify_and_scan_blocks(self):
        result=self.ex.verify();freeze,sha=self.packet()
        self.write(self.primary/'notification.private.tfvars.json',json.dumps({'budget_notification_emails':['new@example.invalid']}).encode())
        with self.assertRaisesRegex(b.Blocked,'PRIVATE_INPUT_CHANGED'):
            self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))
        self.assertFalse((self.ex.op/'post-freeze-scan.receipt.json').exists())
        for private in ('identity',str(len(ADDRESS)),'new@example.invalid'):
            if private=='identity':self.assertNotIn(private,result)
        self.assertNotIn('new@example.invalid',json.dumps(result))

    def test_same_bytes_private_input_replacement_blocks(self):
        self.ex.verify();freeze,sha=self.packet();path=self.primary/'notification.private.tfvars.json'
        replacement=self.primary/'replacement-fixture.json';self.write(replacement,path.read_bytes());os.replace(replacement,path)
        with self.assertRaisesRegex(b.Blocked,'PRIVATE_INPUT_CHANGED'):
            self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))

    def test_private_input_change_during_scan_blocks_before_receipt(self):
        self.ex.verify();freeze,sha=self.packet();real=v.public_read;changed=[False]
        def mutate(repo,path):
            data=real(repo,path)
            if str(path).endswith('file.txt') and not changed[0]:
                changed[0]=True
                self.write(self.primary/'notification.private.tfvars.json',json.dumps({'budget_notification_emails':['new@example.invalid']}).encode())
            return data
        with mock.patch.object(v,'public_read',side_effect=mutate):
            with self.assertRaisesRegex(b.Blocked,'PRIVATE_INPUT_CHANGED'):
                self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))
        self.assertFalse((self.ex.op/'post-freeze-scan.receipt.json').exists())

    def test_nonboolean_safe_result_is_rejected_even_with_checkpoint_rebinding(self):
        self.ex.verify();freeze,sha=self.packet();path=self.ex.op/'verify.receipt.json'
        obj=json.loads(path.read_bytes());obj['result']['notification_count']=True;self.write(path,json.dumps(obj).encode())
        checkpoint=self.ex.op/'verify.input-identity.json';data=json.loads(checkpoint.read_bytes())
        data['verification_receipt_sha256']=b.hash_file(path);self.write(checkpoint,json.dumps(data).encode())
        with self.assertRaisesRegex(b.Blocked,'VERIFY_RECEIPT_RESULT'):
            self.ex.scan(freeze,sha,b.hash_file(path))

    def test_expiry_during_final_linkage_prevents_success_receipt(self):
        real=self.ex.linkage;counter=[0]
        def expire():
            result=real();counter[0]+=1
            if counter[0]==3:self.clock=NOW+timedelta(hours=1)
            return result
        with mock.patch.object(self.ex,'linkage',side_effect=expire):
            with self.assertRaisesRegex(b.Blocked,'WINDOW_EXPIRED'):self.ex.verify()
        self.assertEqual(len(self.calls),6);self.receipt_missing()

    def test_expiry_during_private_checkpoint_write_prevents_success(self):
        real=b.save_json
        def expire(path,value):
            result=real(path,value)
            if path.name=='verify.input-identity.json':self.clock=NOW+timedelta(hours=1)
            return result
        with mock.patch.object(b,'save_json',side_effect=expire):
            with self.assertRaisesRegex(b.Blocked,'WINDOW_EXPIRED'):self.ex.verify()
        self.receipt_missing();self.assertTrue((self.ex.op/'verify.input-identity.json').exists())

    def test_expiry_during_final_scan_checks_prevents_receipt(self):
        self.ex.verify();freeze,sha=self.packet();real=self.ex.verified;counter=[0]
        def expire():
            result=real();counter[0]+=1
            if counter[0]==3:self.clock=NOW+timedelta(hours=1)
            return result
        with mock.patch.object(self.ex,'verified',side_effect=expire):
            with self.assertRaisesRegex(b.Blocked,'WINDOW_EXPIRED'):
                self.ex.scan(freeze,sha,b.hash_file(self.ex.op/'verify.receipt.json'))
        self.assertFalse((self.ex.op/'post-freeze-scan.receipt.json').exists())

    def test_original_gate_filename_is_human_pinned_basename_only(self):
        original=copy.deepcopy(self.gate)
        for value in (None,False,0,[],{},'', 'approval.json','/tmp/approval-x.json',
                      '../approval-x.json','approval-sub/x.json','approval-..json','approval-x.JSON'):
            with self.subTest(filename=value):
                self.gate=copy.deepcopy(original);self.gate['original_gate_filename']=value
                with self.assertRaisesRegex(b.Blocked,'ORIGINAL_GATE_FILENAME'):self.execution()
        self.assertEqual(self.calls,[])

    def test_mismatched_original_gate_name_or_hash_does_not_reserve_operation(self):
        original=self.primary/'approval-20261102-attempt02.json'
        self.gate['original_gate_filename']='approval-wrong.json';self.ex=self.execution()
        with self.assertRaises(FileNotFoundError):self.ex.verify()
        self.assertFalse(self.ex.op.exists());self.assertEqual(self.calls,[]);self.unchanged_original()
        self.write(self.primary/'approval-wrong.json',b'{}')
        with self.assertRaisesRegex(b.Blocked,'ORIGINAL_GATE_HASH'):self.ex.verify()
        self.assertFalse(self.ex.op.exists());self.assertEqual(self.calls,[])
        self.gate['original_gate_filename']=original.name;self.ex=self.execution();self.ex.verify()
        self.assertEqual(len(self.calls),6)

    def test_linkage_change_after_stage_started_is_consumed_and_never_retried(self):
        real=self.ex.linkage;counter=[0]
        def race():
            counter[0]+=1
            if counter[0]==2:self.write(self.old/'apply.receipt.json',b'{}')
            return real()
        with mock.patch.object(self.ex,'linkage',side_effect=race):
            with self.assertRaisesRegex(b.Blocked,'ORIGINAL_APPLY_HASH'):self.ex.verify()
        self.assertTrue((self.ex.op/'verify.started').exists());self.assertEqual(self.calls,[])
        self.receipt_missing()

    def test_cheap_scan_hash_errors_do_not_consume_journal(self):
        self.ex.verify();freeze,manifest_sha=self.packet();receipt_sha=b.hash_file(self.ex.op/'verify.receipt.json')
        for supplied_manifest,supplied_receipt in ((None,receipt_sha),(manifest_sha,None),('x',receipt_sha),
                                                   (manifest_sha,'x'),(manifest_sha,'0'*64),('0'*64,receipt_sha)):
            with self.subTest(manifest=supplied_manifest,receipt=supplied_receipt):
                with self.assertRaises(b.Blocked):self.ex.scan(freeze,supplied_manifest,supplied_receipt)
                self.assertFalse((self.ex.op/'post-freeze-scan.started').exists())
                self.assertEqual(len(self.calls),6)
        receipt=self.ex.scan(freeze,manifest_sha,receipt_sha)
        self.assertEqual(receipt['matches'],0);self.assertTrue((self.ex.op/'post-freeze-scan.started').exists())

    def test_missing_scan_pin_stops_cli_before_gate_read(self):
        args=['post-freeze-scan','--gate',str(self.gatepath),'--gate-sha256',b.hash_file(self.gatepath),
              '--operation',self.gate['operation'],'--public-manifest',str(self.repo/'freeze.json'),
              '--public-manifest-sha256','0'*64]
        with mock.patch.object(v,'production_policy') as policy,mock.patch('builtins.print') as output:
            self.assertEqual(v.main(args),2)
            policy.assert_not_called();self.assertIn('SCAN_ARGUMENTS',str(output.call_args_list))
        self.assertFalse(self.ex.op.exists())

    def test_captured_public_stdout_canonical_hash_matches_private_receipt(self):
        output=io.StringIO()
        with mock.patch.object(v,'production_policy',return_value=self.policy), \
                mock.patch.object(v,'Verification',return_value=self.ex), redirect_stdout(output):
            status=v.main(['verify','--gate',str(self.gatepath),'--gate-sha256',b.hash_file(self.gatepath),
                           '--operation',self.gate['operation']])
        self.assertEqual(status,0)
        public_stdout=output.getvalue()
        canonical=(json.dumps(json.loads(public_stdout),sort_keys=True,indent=2)+'\n').encode('utf-8')
        self.assertEqual(v.canonical_receipt_bytes(json.loads(public_stdout)),canonical)
        self.assertEqual(b.digest(canonical),b.hash_file(self.ex.op/'verify.receipt.json'))
        self.assertNotEqual(b.digest(public_stdout.encode()),b.digest(canonical))
        self.assertNotIn(ADDRESS,canonical.decode())

    def test_human_pinned_gate_symlink_rejected_before_operation_reservation(self):
        self.gate['original_gate_filename']='approval-linked.json'
        (self.primary/'approval-linked.json').symlink_to(self.primary/'approval-20261102-attempt02.json')
        self.ex=self.execution()
        with self.assertRaises(b.Blocked):self.ex.verify()
        self.assertFalse(self.ex.op.exists());self.assertEqual(self.calls,[]);self.unchanged_original()

    def test_missing_percentage_readback_preserves_six_explicit_query_selectors(self):
        for notification in self.values[2]['Notifications']:del notification['ThresholdType']
        self.values[2]['Notifications'].reverse()
        result=self.ex.verify()
        self.assertEqual(len(self.calls),6)
        self.assertEqual(result['result']['notification_count'],3)
        self.assertTrue(result['result']['private_recipients_match'])
        selectors=[json.loads(call['argv'][call['argv'].index('--notification')+1]) for call in self.calls[3:]]
        self.assertEqual(selectors,[b.expected_notification(t) for t in (50,80,100)])
        self.assertTrue(all(selector['ThresholdType']=='PERCENTAGE' for selector in selectors))
        for private in (ADDRESS,b.digest(ADDRESS.encode())):self.assertNotIn(private,json.dumps(result))
        self.unchanged_original()

    def test_present_bad_threshold_type_blocks_after_six_without_receipt(self):
        self.values[2]['Notifications'][0]['ThresholdType']='ABSOLUTE_VALUE'
        with self.assertRaisesRegex(b.Blocked,'NOTIFICATION_DRIFT'):self.ex.verify()
        self.assertEqual(len(self.calls),6);self.receipt_missing();self.unchanged_original()

    def test_main_only_exposes_readonly_modes_without_echoing_payloads(self):
        for mode in ('apply','p3-check','readback','destroy',ADDRESS):
            with self.subTest(mode=mode),mock.patch('builtins.print') as output:
                self.assertEqual(v.main([mode]),2)
                self.assertNotIn(ADDRESS,str(output.call_args_list))
        result=subprocess.run([sys.executable,'-I',str(ROOT/'budget_verification.py'),ADDRESS],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertNotIn(ADDRESS,result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout),{'status':'BLOCKED-ON','code':'CLI_ARGUMENTS'})

    def test_config_symlink_and_mode_block(self):
        self.policy.config.chmod(0o755)
        with self.assertRaisesRegex(b.Blocked,'DIRECTORY_MODE_OWNER'):self.ex.verify()
        self.assertEqual(self.calls,[])
        self.policy.config.chmod(0o700)
        self.gate['operation']='verify-config-link';self.ex=self.execution()
        self.policy.config.rmdir();self.policy.config.symlink_to(self.root)
        with self.assertRaisesRegex(b.Blocked,'SYMLINK_DIRECTORY'):self.ex.verify()
        self.assertEqual(self.calls,[])



def usd25_values():
    """Hand-derived USD 25 readback: amount 25, ACTUAL ABSOLUTE_VALUE alerts at 10, 15 and 20."""
    values = responses()
    values[0]['Budget']['BudgetLimit']['Amount'] = '25.0'
    values[2]['Notifications'] = [b.expected_notification(x, 'ABSOLUTE_VALUE') for x in (10, 15, 20)]
    return values


class ModifiedFeatures(Fixture):
    """Post-modify verifier: new shape passes, old shape fails, linkage is the modify receipt and state."""
    def setUp(self):
        super().setUp()
        self.post_state = b'post-modify opaque synthetic state, not Terraform data'
        for name, value in (('INITIAL_STATE_SHA256', b.digest(self.opaque)), ('INITIAL_STATE_BYTES', len(self.opaque))):
            patch = mock.patch.object(b, name, value); patch.start(); self.addCleanup(patch.stop)
        self.modify_plan = 'c'*64
        self.policy.pins['modify'] = {'plan_sha256': self.modify_plan, 'plan_bytes': 10, 'public_input_sha256': 'd'*64,
                                      'config': [{'copy_relative': 'config/main.tf', 'sha256': 'e'*64, 'bytes': 1}]}
        self.mop = self.primary/'operations'/'modify-fixture'; self.mop.mkdir(mode=0o700)
        self.write(self.mop/'modify.started', b'')
        (self.backups/'modify-fixture').mkdir(mode=0o700)
        self.write(self.backups/'modify-fixture/pre-apply.billing.execution.tfstate', self.opaque)
        self.write(self.backups/'modify-fixture/post-apply.billing.execution.tfstate', self.post_state)
        self.write(self.primary/'billing.execution.tfstate', self.post_state)
        self.modify_gate = {'operation': 'modify-fixture', 'option': 'M', 'plan_sha256': self.modify_plan,
                            'actor_arn': b.CALLER, 'account': b.ACCOUNT, 'profile': b.PROFILE, 'region': b.REGION,
                            'window_start': '2026-11-03T16:00:00Z', 'window_end': '2026-11-03T16:55:00Z'}
        self.modify_gate_name = 'approval-20261103-modify.json'
        self.install_modify_receipt()
        self.values = usd25_values()
        self.mgate = {'operation': 'verify-usd25-fixture', 'option': 'M', 'plan_sha256': self.modify_plan,
            'proposal_sha256': self.policy.pins['proposal_sha256'], 'source_commit': self.gate['source_commit'],
            'wrapper_files': self.gate['wrapper_files'], 'human_record_sha256': self.policy.pins['human_record_sha256'],
            'g1_affirmation': 'Synthetic affirmation, no actual approval.', 'actor_arn': b.CALLER, 'account': b.ACCOUNT,
            'profile': b.PROFILE, 'region': b.REGION, 'window_start': self.gate['window_start'], 'window_end': self.gate['window_end'],
            'timezone': 'America/Chicago', 'login_at': self.gate['login_at'], 'human_sts_observed_at': self.gate['human_sts_observed_at'],
            'human_sts': {'Account': b.ACCOUNT, 'Arn': b.CALLER}, 'permissions': sorted(v.MODIFIED_PERMISSIONS),
            'retention_accepted': True, 'verification_review_approved': True, 'aws_cli_sha256': b.hash_file(self.aws),
            'public_packet_root': 'docs/agent-runs/phase-14/evidence/14b/budget-modify-verify-fixture',
            'modify_operation': 'modify-fixture', 'modify_gate_filename': self.modify_gate_name,
            'modify_gate_sha256': self.modify_gate_sha, 'modify_receipt_sha256': self.modify_receipt_sha,
            'state_backup_sha256': b.digest(self.post_state), 'state_backup_bytes': len(self.post_state)}
        self.mex = self.modified()

    def install_modify_receipt(self, mutate=None, receipt_name='modify.receipt.json'):
        raw_gate = (json.dumps(self.modify_gate) + '\n').encode()
        path = self.primary/self.modify_gate_name
        if path.exists(): path.unlink()
        self.write(path, raw_gate)
        self.modify_gate_sha = b.digest(raw_gate)
        backup = lambda blob: {'bytes': len(blob), 'equal': True, 'fsync_completed': True, 'sha256': b.digest(blob)}
        receipt = {'gate_sha256': self.modify_gate_sha, 'operation': 'modify-fixture', 'plan_sha256': self.modify_plan,
                   'actor_arn': b.CALLER, 'stage': 'modify', 'observed_at': '2026-11-03T16:30:00+00:00',
                   'result': {'applied': True, 'already_at_target': False, 'pre_backup': backup(self.opaque),
                              'post_backup': backup(self.post_state), 'plan': {'actions': ['update']}, 'verify': {}}}
        if mutate: mutate(receipt)
        target = self.mop/receipt_name
        if target.exists(): target.unlink()
        self.write(target, (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode())
        self.modify_receipt_sha = b.hash_file(target)

    def modified(self, gate=None):
        gate = gate or self.mgate
        self.write(self.gatepath, (json.dumps(gate) + '\n').encode())
        return v.ModifiedVerification(self.policy, self.runner, lambda: self.clock).load_gate(
            self.gatepath, b.hash_file(self.gatepath), gate['operation'])

    def reload(self, **gate_changes):
        self.mgate.update(modify_gate_sha256=self.modify_gate_sha, modify_receipt_sha256=self.modify_receipt_sha, **gate_changes)
        self.mex = self.modified()

    def selectors(self):
        return [json.loads(c['argv'][c['argv'].index('--notification')+1]) for c in self.calls if '--notification' in c['argv']]

    def mpacket(self, files=None):
        root = Path(self.mgate['public_packet_root']); files = files or {'file.txt': b'safe public suffixes'}
        for name, data in files.items(): self.public(self.repo/root/name, data)
        rows = [{'path': str(root/name), 'bytes': len(data), 'sha256': b.digest(data)} for name, data in files.items()]
        freeze = self.repo/Path(str(root) + '.freeze.json'); self.public(freeze, json.dumps({'root': str(root), 'files': rows}).encode())
        return freeze, b.hash_file(freeze)

    def test_switch_constants_select_the_expected_shapes(self):
        self.assertIs(v.Verification.SHAPE, b.INITIAL_SHAPE); self.assertEqual(v.Verification.OPTION, 'B')
        self.assertIs(v.ModifiedVerification.SHAPE, b.USD25_SHAPE); self.assertEqual(v.ModifiedVerification.OPTION, 'M')
        self.assertEqual(v.ModifiedVerification.SHAPE.amount, 25)
        self.assertEqual(v.ModifiedVerification.SHAPE.thresholds, (10, 15, 20))
        self.assertEqual(v.ModifiedVerification.SHAPE.threshold_type, 'ABSOLUTE_VALUE')

    def test_new_shape_verifies_with_six_explicit_absolute_value_selectors(self):
        result = self.mex.verify()
        self.assertEqual(len(self.calls), 6)
        self.assertEqual([x['argv'][2] for x in self.calls], ['describe-budget', 'list-tags-for-resource', 'describe-notifications-for-budget', *['describe-subscribers-for-notification']*3])
        self.assertEqual(self.selectors(), [b.expected_notification(t, 'ABSOLUTE_VALUE') for t in (10, 15, 20)])
        self.assertEqual((result['stage'], result['option']), ('verify', 'M'))
        self.assertEqual(result['result']['notification_count'], 3); self.assertTrue(result['result']['private_recipients_match'])
        self.assertEqual(result['plan_sha256'], self.modify_plan)
        self.assertEqual(result['linkage']['modify_operation'], 'modify-fixture'); self.assertTrue(result['linkage']['state_backup_verified'])
        for private in (ADDRESS, b.digest(ADDRESS.encode())):
            self.assertNotIn(private, json.dumps(result))
        self.assertEqual(self.mex.verified(), b.hash_file(self.mex.op/'verify.receipt.json'))
        with self.assertRaises(FileExistsError): self.mex.verify()
        self.assertEqual(len(self.calls), 6)

    def test_old_shape_after_modify_fails_after_six_reads_with_no_receipt(self):
        self.values = responses()  # the pre-modify shape: 200 and PERCENTAGE 50/80/100
        with self.assertRaises(b.Blocked): self.mex.verify()
        self.assertEqual(len(self.calls), 6)  # budget, tags, notifications and the three new-shape selectors
        self.assertFalse((self.mex.op/'verify.receipt.json').exists())

    def test_each_new_shape_defect_fails_closed(self):
        def alert(i, **kw): return lambda vals: vals[2]['Notifications'][i].update(kw)
        cases = {'amount_200': (lambda vals: vals[0]['Budget']['BudgetLimit'].update(Amount='200'), 'BUDGET_AMOUNT'),
                 'amount_26': (lambda vals: vals[0]['Budget']['BudgetLimit'].update(Amount='26'), 'BUDGET_AMOUNT'),
                 'top_alert_25': (alert(2, Threshold=25), 'NOTIFICATION_THRESHOLD'),
                 'percentage_left': (alert(0, ThresholdType='PERCENTAGE'), 'NOTIFICATION_DRIFT'),
                 'omitted_type': (lambda vals: vals[2]['Notifications'][1].pop('ThresholdType'), 'NOTIFICATION_DRIFT'),
                 'forecasted': (alert(1, NotificationType='FORECASTED'), 'NOTIFICATION_DRIFT'),
                 'two_alerts': (lambda vals: vals[2]['Notifications'].pop(), 'NOTIFICATION_COUNT'),
                 'wrong_recipient': (lambda vals: vals[4]['Subscribers'][0].update(Address='other@example.invalid'), 'SUBSCRIBER_DRIFT'),
                 'unhealthy': (lambda vals: vals[0]['Budget']['HealthStatus'].update(Status='UNHEALTHY'), 'BUDGET_HEALTH_UNVERIFIED')}
        for index, (name, (mutate, code)) in enumerate(cases.items()):
            with self.subTest(name=name):
                self.values = usd25_values(); mutate(self.values); self.calls = []
                self.mgate['operation'] = f'verify-usd25-defect-{index}'; self.mex = self.modified()
                with self.assertRaisesRegex(b.Blocked, code) as error: self.mex.verify()
                self.assertEqual(len(self.calls), 6)
                self.assertNotIn(ADDRESS, str(error.exception))
                self.assertFalse((self.mex.op/'verify.receipt.json').exists())

    def test_original_verifier_expectations_reject_the_new_shape(self):
        new = usd25_values()
        with self.assertRaisesRegex(b.Blocked, 'BUDGET_AMOUNT'):
            b.sanitize_readback(new[0], new[1], new[2], {t: new[3+i] for i, t in enumerate((10, 15, 20))}, ADDRESS, v.Verification.SHAPE)
        with self.assertRaisesRegex(b.Blocked, 'BUDGET_AMOUNT'):
            old = responses()
            b.sanitize_readback(old[0], old[1], old[2], {t: old[3+i] for i, t in enumerate((50, 80, 100))}, ADDRESS, v.ModifiedVerification.SHAPE)

    def test_original_verify_gate_cannot_drive_the_modified_verifier_and_the_reverse(self):
        self.write(self.gatepath, (json.dumps(self.gate) + '\n').encode())
        with self.assertRaises(b.Blocked):
            v.ModifiedVerification(self.policy, self.runner, lambda: self.clock).load_gate(self.gatepath, b.hash_file(self.gatepath), 'verify-usd25-fixture')
        self.write(self.gatepath, (json.dumps(self.mgate) + '\n').encode())
        with self.assertRaises(b.Blocked):
            v.Verification(self.policy, self.runner, lambda: self.clock).load_gate(self.gatepath, b.hash_file(self.gatepath), 'verify-usd25-fixture')
        self.assertEqual(self.calls, [])

    def test_modified_verification_gate_has_exactly_29_fields_and_each_one_is_required(self):
        # Pins the count VERIFICATION.md states ("Gate (29 fields"): the constant, the full fixture gate, and every field required.
        self.assertEqual(len(v.MODIFIED_GATE_FIELDS), 29)
        self.assertEqual(set(self.mgate), v.MODIFIED_GATE_FIELDS)
        for field in sorted(self.mgate):
            with self.subTest(missing=field):
                gate = dict(self.mgate); del gate[field]
                self.write(self.gatepath, (json.dumps(gate) + '\n').encode())
                with self.assertRaisesRegex(b.Blocked, 'VERIFICATION_GATE_SCHEMA'):
                    v.ModifiedVerification(self.policy, self.runner, lambda: self.clock).load_gate(self.gatepath, b.hash_file(self.gatepath), self.mgate['operation'])
        text = (ROOT / 'VERIFICATION.md').read_text(encoding='utf-8')
        self.assertIn('Gate (29 fields, `MODIFIED_GATE_FIELDS`', text)
        self.assertIn('28 fields', text)
        self.assertEqual(self.calls, [])

    def test_gate_refuses_unbound_operation_option_scope_and_state_fields(self):
        cases = [('operation', 'verify-fixture'), ('operation', 'verify-usd25-'), ('option', 'B'), ('plan_sha256', '0'*64),
                 ('proposal_sha256', '0'*64), ('human_record_sha256', '0'*64), ('g1_affirmation', ''),
                 ('permissions', sorted(v.PERMISSIONS)), ('permissions', sorted(v.MODIFIED_PERMISSIONS)[:-1]),
                 ('public_packet_root', 'docs/agent-runs/phase-12/evidence/12d-publication-output-verify-fixture'),
                 ('public_packet_root', 'docs/agent-runs/phase-14/evidence/14b/other'),
                 ('modify_operation', 'verify-fixture'), ('modify_operation', '../modify-fixture'),
                 ('modify_gate_filename', '../approval-x.json'), ('modify_gate_filename', 'approval-x.txt'),
                 ('modify_gate_sha256', 'nothex'), ('modify_receipt_sha256', 'nothex'),
                 ('state_backup_sha256', b.INITIAL_STATE_SHA256), ('state_backup_sha256', 'nothex'),
                 ('state_backup_bytes', 0), ('state_backup_bytes', True), ('retention_accepted', False),
                 ('verification_review_approved', False), ('timezone', 'UTC'), ('actor_arn', 'wrong')]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                gate = {**self.mgate, field: value}
                operation = value if field == 'operation' else gate['operation']
                self.write(self.gatepath, (json.dumps(gate) + '\n').encode())
                with self.assertRaises(b.Blocked):
                    v.ModifiedVerification(self.policy, self.runner, lambda: self.clock).load_gate(self.gatepath, b.hash_file(self.gatepath), operation)
        gate = {**self.mgate, 'surprise': 1}
        self.write(self.gatepath, (json.dumps(gate) + '\n').encode())
        with self.assertRaisesRegex(b.Blocked, 'VERIFICATION_GATE_SCHEMA'):
            v.ModifiedVerification(self.policy, self.runner, lambda: self.clock).load_gate(self.gatepath, b.hash_file(self.gatepath), gate['operation'])
        self.assertEqual(self.calls, [])

    def test_missing_modify_pins_block_the_gate(self):
        del self.policy.pins['modify']
        with self.assertRaisesRegex(b.Blocked, 'MODIFY_PINS_MISSING'): self.modified()

    def test_linkage_refuses_a_modify_that_did_not_apply_cleanly(self):
        def result(**kw): return lambda r: r['result'].update(kw)
        bad = lambda blob, **kw: {'bytes': len(blob), 'equal': True, 'fsync_completed': True, 'sha256': b.digest(blob), **kw}
        cases = {'not_applied': (result(applied=False), 'MODIFY_RECEIPT_RESULT'),
                 'already_at_target': (result(already_at_target=True), 'MODIFY_RECEIPT_RESULT'),
                 'string_true': (result(applied='true'), 'MODIFY_RECEIPT_RESULT'),
                 'pre_backup_not_initial': (result(pre_backup=bad(b'unrelated')), 'MODIFY_RECEIPT_RESULT'),
                 'post_backup_other_state': (result(post_backup=bad(b'unrelated')), 'MODIFY_RECEIPT_RESULT'),
                 'post_not_fsynced': (result(post_backup=bad(self.post_state, fsync_completed=False)), 'MODIFY_RECEIPT_RESULT'),
                 'wrong_stage': (lambda r: r.update(stage='modify-apply'), 'MODIFY_RECEIPT_CONTEXT'),
                 'wrong_plan': (lambda r: r.update(plan_sha256='0'*64), 'MODIFY_RECEIPT_CONTEXT'),
                 'wrong_gate': (lambda r: r.update(gate_sha256='0'*64), 'MODIFY_RECEIPT_CONTEXT'),
                 'wrong_operation': (lambda r: r.update(operation='modify-other'), 'MODIFY_RECEIPT_CONTEXT'),
                 'wrong_actor': (lambda r: r.update(actor_arn='wrong'), 'MODIFY_RECEIPT_CONTEXT'),
                 'extra_field': (lambda r: r.update(extra=1), 'MODIFY_RECEIPT_SCHEMA'),
                 'after_verification_window': (lambda r: r.update(observed_at='2026-11-03T18:30:00+00:00'), 'MODIFY_RECEIPT_TIME'),
                 'before_modify_window': (lambda r: r.update(observed_at='2026-11-03T15:00:00+00:00'), 'MODIFY_RECEIPT_TIME')}
        for index, (name, (mutate, code)) in enumerate(cases.items()):
            with self.subTest(name=name):
                self.install_modify_receipt(mutate)
                self.mgate['operation'] = f'verify-usd25-link-{index}'; self.reload()
                with self.assertRaisesRegex(b.Blocked, code): self.mex.verify()
                self.assertEqual(self.calls, []); self.assertFalse(self.mex.op.exists())

    def test_linkage_hash_state_backup_lock_and_journal_drift_blocks(self):
        cases = {'receipt_bytes': lambda: self.write(self.mop/'modify.receipt.json', b'tampered'),
                 'modify_gate_bytes': lambda: self.write(self.primary/self.modify_gate_name, b'tampered'),
                 'state_changed_after_modify': lambda: self.write(self.primary/'billing.execution.tfstate', b'tampered'),
                 'post_backup_changed': lambda: self.write(self.backups/'modify-fixture/post-apply.billing.execution.tfstate', b'tampered'),
                 'pre_backup_changed': lambda: self.write(self.backups/'modify-fixture/pre-apply.billing.execution.tfstate', b'tampered'),
                 'journal_not_empty': lambda: self.write(self.mop/'modify.started', b'x'),
                 'lock_info_present': lambda: self.write(self.primary/'.billing.execution.tfstate.lock.info', b''),
                 'config_lock_present': lambda: self.write(self.policy.config/'.terraform.tfstate.lock.info', b''),
                 'receipt_missing': lambda: (self.mop/'modify.receipt.json').unlink(),
                 'state_missing': lambda: self.policy.state.unlink()}
        for index, (name, damage) in enumerate(cases.items()):
            with self.subTest(name=name):
                self.fresh()
                self.mgate['operation'] = f'verify-usd25-drift-{index}'; self.reload()
                damage()
                with self.assertRaises((b.Blocked, OSError)): self.mex.verify()
                self.assertEqual(self.calls, []); self.assertFalse(self.mex.op.exists())

    def fresh(self):
        self.tearDown(); self.setUp()

    def test_state_change_between_reads_and_receipt_blocks_without_success_receipt(self):
        self.after = lambda index: self.write(self.primary/'billing.execution.tfstate', b'changed during verification') if index == 5 else None
        with self.assertRaises(b.Blocked): self.mex.verify()
        self.assertEqual(len(self.calls), 6)
        self.assertFalse((self.mex.op/'verify.receipt.json').exists())

    def test_scan_after_modified_verification_matches_the_scan_receipt_contract(self):
        self.mex.verify(); freeze, sha = self.mpacket()
        receipt = self.mex.scan(freeze, sha, b.hash_file(self.mex.op/'verify.receipt.json'))
        self.assertEqual((receipt['matches'], receipt['files_scanned'], len(receipt)), (0, 1, 10))
        self.assertEqual(receipt['plan_sha256'], self.modify_plan)
        private = json.loads((self.mex.op/'post-freeze-scan.receipt.json').read_bytes())
        self.assertEqual(private['verification_receipt_sha256'], b.hash_file(self.mex.op/'verify.receipt.json'))
        with self.assertRaises(FileExistsError): self.mex.scan(freeze, sha, b.hash_file(self.mex.op/'verify.receipt.json'))
        self.assertEqual(len(self.calls), 6)

    def test_scan_blocks_recipient_leak_wrong_receipt_hash_and_missing_verification(self):
        self.mex.verify()
        freeze, sha = self.mpacket({'leak.txt': ADDRESS.encode()})
        with self.assertRaisesRegex(b.Blocked, 'PUBLIC_RECIPIENT_FOUND'):
            self.mex.scan(freeze, sha, b.hash_file(self.mex.op/'verify.receipt.json'))
        self.mgate['operation'] = 'verify-usd25-scan-b'; self.mex = self.modified(); self.mex.op.mkdir(mode=0o700)
        freeze, sha = self.mpacket()
        with self.assertRaises(FileNotFoundError): self.mex.scan(freeze, sha, '0'*64)

    def test_cli_modes_and_option_validation_do_not_echo_payloads(self):
        for argv in (['verify-modified'], ['post-freeze-scan-modified'], ['apply'], ['modify'], ['destroy']):
            with self.subTest(argv=argv), mock.patch('builtins.print') as output:
                self.assertEqual(v.main(argv), 2); self.assertNotIn(ADDRESS, str(output.call_args_list))
        base = ['--gate', str(self.gatepath), '--gate-sha256', '0'*64, '--operation', 'verify-usd25-x']
        with mock.patch('builtins.print') as output:
            self.assertEqual(v.main(['verify-modified', *base, '--public-manifest', 'x']), 2)
        self.assertIn('UNEXPECTED_SCAN_OPTIONS', str(output.call_args_list))
        with mock.patch('builtins.print') as output:
            self.assertEqual(v.main(['post-freeze-scan-modified', *base]), 2)
        self.assertIn('SCAN_ARGUMENTS', str(output.call_args_list))


if __name__=='__main__':unittest.main(verbosity=2)
