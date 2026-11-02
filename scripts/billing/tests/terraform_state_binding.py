#!/usr/bin/env python3
"""A1: real Terraform, credential-free isolated terraform_data feature check only."""
import hashlib
import importlib.util
import sys
import json
import os
from pathlib import Path
import subprocess
import tempfile

BINARY = Path('/tmp/scholarchain-phase12b-repair1-infra/terraform')
EXPECTED = '899b3c0ca0d2669ebd67be4bcd98e84bd9a914ce2fb3897ad0b86c98cbf3c962'
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('budget_execution_a1', Path(__file__).resolve().parents[1] / 'budget_execution.py')
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)


def run_test(output):
    raw = BINARY.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise RuntimeError('A1_BINARY_HASH_MISMATCH')
    # No durable path, AWS external provider, named profile or user HOME is used.
    scratch = Path(tempfile.mkdtemp(prefix='scholarchain A1 state binding ')).resolve()
    scratch.chmod(0o700)
    config = scratch / 'config'
    data = scratch / 'tf working data'
    home = scratch / 'empty home'
    for d in (config, data, home):
        d.mkdir(mode=0o700)
    state = scratch / 'billing.execution.tfstate'
    plan = scratch / 'billing.execution.tfplan'
    (scratch / 'toolchain').mkdir(mode=0o700)
    (scratch / 'toolchain/terraform-1.13.5').symlink_to(BINARY.resolve())
    policy = b.Policy(scratch, scratch / 'unused backups', scratch / 'unused repo', os.getuid(),
                      scratch / 'unused aws', {})
    tfrc = scratch / 'no-network.tfrc'
    tfrc.write_text('disable_checkpoint = true\nprovider_installation { filesystem_mirror { path = "'+str(scratch / 'empty mirror')+'" } }\n')
    (scratch / 'empty mirror').mkdir(mode=0o700)
    (config / 'main.tf').write_text('terraform { required_version = "= 1.13.5" }\nresource "terraform_data" "offline" { input = "public fixture only" }\n')
    env = {'HOME': str(home), 'PATH': '/usr/bin:/bin', 'TF_DATA_DIR': str(data),
           'TF_CLI_CONFIG_FILE': str(tfrc), 'TF_IN_AUTOMATION': '1',
           'CHECKPOINT_DISABLE': '1', 'AWS_EC2_METADATA_DISABLED': 'true',
           'AWS_CONFIG_FILE': '/dev/null', 'AWS_SHARED_CREDENTIALS_FILE': '/dev/null',
           'AWS_PAGER': ''}
    commands = []
    args = [
      ['init', '-backend=false', '-input=false', '-no-color'],
      ['plan', '-input=false', '-no-color', '-lock-timeout=30s', '-state='+str(state), '-out='+str(plan)],
      policy.apply_argv()[1:]]
    for number, argv in enumerate(args):
        if hashlib.sha256(BINARY.read_bytes()).hexdigest() != EXPECTED:
            raise RuntimeError('A1_BINARY_CHANGED_BEFORE_INVOCATION')
        actual_argv = policy.apply_argv() if number == 2 else [str(BINARY), *argv]
        # Exercise the wrapper's actual production PrivateRunner launch primitive and
        # the same Policy.apply_argv builder, with scratch-only Python injection.
        logs = scratch / ('private logs '+str(number))
        logs.mkdir(mode=0o700)
        code, _, _ = b.PrivateRunner()(actual_argv, config, env, logs, 'a1', 60)
        # Public evidence contains command/exits/log hashes, never raw state or logs.
        metadata = []
        for log in sorted(logs.iterdir()):
            metadata.append({'path':str(log),'bytes':log.stat().st_size,
                             'sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
        commands.append({'argv': actual_argv, 'cwd': str(config), 'environment': env,
                         'exit': code, 'private_log_metadata':metadata})
        if code:
            (output / 'a1-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
            raise RuntimeError('A1_OFFLINE_COMMAND_FAILED')
    checks = {
      'state_at_absolute_path_with_spaces': state.is_file() and state.stat().st_size > 0,
      'no_config_default_state': not (config / 'terraform.tfstate').exists(),
      'no_workspace_state_directory': not any(p.name == 'terraform.tfstate.d' for p in scratch.rglob('*')),
      'no_initial_backup': not any(p.name.endswith('.backup') for p in scratch.rglob('*')),
      'lock_removed': not any(p.name.endswith('.lock.info') for p in scratch.rglob('*')),
      'no_resource_state_in_tf_data_dir': not any('.tfstate' in p.name for p in data.rglob('*')),
      'only_expected_resource_state': [p for p in scratch.rglob('*.tfstate')] == [state],
    }
    (output / 'a1-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    receipt = {'binary_sha256': EXPECTED, 'scratch': str(scratch), 'checks': checks,
               'state_sha256': hashlib.sha256(state.read_bytes()).hexdigest(),
               'private_or_real_state': False, 'aws_calls': 0, 'commands': len(commands),
               'wrapper_apply_argv_builder_exercised':True, 'wrapper_private_runner_exercised':True,
               'retention':'Isolated public-fixture scratch state/plan/raw logs retained outside Git; no cleanup performed.'}
    (output / 'a1-result.json').write_text(json.dumps(receipt, indent=2)+'\n')
    if not all(checks.values()):
        raise RuntimeError('A1_ASSERTION_FAILED')
    return receipt


if __name__ == '__main__':
    os.umask(0o077)
    out = Path('/tmp/scholarchain-phase12d-billing-wrapper')
    out.mkdir(exist_ok=True, mode=0o700)
    print(json.dumps(run_test(out), sort_keys=True))
