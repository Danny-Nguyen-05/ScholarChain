import json
import subprocess
import time
import urllib.error
import urllib.request

artifacts = [
    ('query-api', 'QueryApiMain'),
    ('graph-service', 'GraphServiceMain'),
    ('semantic-service', 'SemanticServiceMain'),
    ('embedding-worker', 'EmbeddingWorkerMain'),
]

def command(*arguments):
    return subprocess.check_output(arguments, text=True).strip()

for artifact, main in artifacts:
    tag = f'scholarchain-{artifact}:local'
    image_id = command('docker', 'image', 'inspect', '--format', '{{.Id}}', tag)
    user = command('docker', 'image', 'inspect', '--format', '{{.Config.User}}', tag)
    assert user == 'scholarchain', (tag, user)
    container = None
    try:
        container = command('docker', 'run', '--rm', '-d', '-p', '127.0.0.1::8080',
            '-e', 'SCHOLARCHAIN_HTTP_HOST=0.0.0.0',
            '-e', 'SCHOLARCHAIN_API_KEY_SHA256=' + '1' * 64,
            '-e', 'SCHOLARCHAIN_INTERNAL_TOKEN_SHA256=' + '2' * 64, tag)
        address = command('docker', 'port', container, '8080/tcp')
        selected = command('docker', 'exec', container, 'sh', '-c', 'printf %s "$SCHOLARCHAIN_MAIN_CLASS"')
        assert selected == f'edu.uic.cs441.scholarchain.services.{main}', selected
        deadline = time.monotonic() + 30
        while True:
            try:
                with urllib.request.urlopen(f'http://{address}/healthz', timeout=1) as response:
                    assert response.status == 200
                    assert json.load(response)['status'] == 'alive'
                break
            except (urllib.error.URLError, TimeoutError, OSError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.2)
        try:
            urllib.request.urlopen(f'http://{address}/readyz', timeout=2)
            raise AssertionError('Foundation readiness unexpectedly succeeded')
        except urllib.error.HTTPError as response:
            assert response.code == 503
        print(json.dumps({'image': tag, 'imageId': image_id, 'user': user, 'mainClass': selected, 'healthz': 200, 'readyz': 503}), flush=True)
    finally:
        if container is not None:
            command('docker', 'stop', '-t', '3', container)
            remaining = command('docker', 'ps', '-aq', '--filter', f'id={container}')
            assert remaining == '', remaining
            print(json.dumps({'image': tag, 'cleanup': 'removed created container'}), flush=True)
print('Docker foundation smoke: 4 images passed; all created containers removed.', flush=True)
