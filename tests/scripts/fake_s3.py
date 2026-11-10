"""A fake `aws` (sts + a directory-backed s3api) for the upload tests, written by the test-engineer. It behaves like S3 and records
every call in SC_FAKE_LOG; it does NOT police the caller's flags (the tests assert on the recorded argv)."""
import base64
import textwrap

FAKE_AWS = textwrap.dedent('''\
    #!/usr/bin/env python3
    """Fake aws for the upload tests: sts + a directory-backed s3api. Configuration: FAKE_DIR/config.json."""
    import base64, hashlib, json, os, sys
    argv = sys.argv[1:]
    fake = os.environ["FAKE_DIR"]
    cfg = json.load(open(os.path.join(fake, "config.json")))
    with open(os.environ["SC_FAKE_LOG"], "a") as log:
        log.write(json.dumps({"tool": "aws", "argv": argv, "profile": os.environ.get("AWS_PROFILE")}) + "\\n")
    objects = os.path.join(fake, "objects")
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    def path(key):
        return os.path.join(objects, key.replace("/", "__SLASH__"))
    def meta(key):
        with open(path(key) + ".meta") as h:
            return json.load(h)
    def exists(key):
        return os.path.exists(path(key))
    def err(code, text):
        sys.stderr.write("An error occurred (%s) when calling the operation: %s\\n" % (code, text))
        sys.exit(255)
    if argv[:2] == ["sts", "get-caller-identity"]:
        q = opt("--query")
        print(cfg["account"] if q == "Account" else cfg["arn"])
        sys.exit(0)
    if argv[0] != "s3api":
        err("Unsupported", "unsupported command")
    op = argv[1]
    key = opt("--key")
    if op == "list-objects-v2":
        prefix = opt("--prefix", "")
        found = []
        for name in sorted(os.listdir(objects)) if os.path.isdir(objects) else []:
            if name.endswith(".meta"):
                continue
            k = name.replace("__SLASH__", "/")
            if k.startswith(prefix):
                found.append({"Key": k, "Size": os.path.getsize(os.path.join(objects, name))})
        print(json.dumps({"Contents": found} if found else {}))
    elif op == "put-object":
        if cfg.get("put_fail_key") == key:
            err("InternalError", "injected failure")
        # The fake behaves like S3 and does NOT police the caller: the flags are only recorded (SC_FAKE_LOG) for the tests to assert.
        body = open(opt("--body"), "rb").read()
        digest = base64.b64encode(hashlib.sha256(body).digest()).decode()
        declared = opt("--checksum-sha256")
        if declared is not None and digest != declared:
            err("BadDigest", "the declared SHA-256 does not match the body")
        os.makedirs(objects, exist_ok=True)
        if key == cfg.get("race_key") and not exists(key):  # a concurrent writer creates the key just before this put
            open(path(key), "wb").write(b"concurrent writer")
            json.dump({"sha": "AAAA", "version": "v-race"}, open(path(key) + ".meta", "w"))
        if exists(key) and opt("--if-none-match") == "*":
            err("PreconditionFailed", "At least one of the pre-conditions you specified did not hold")
        os.makedirs(objects, exist_ok=True)
        stored = body if key not in cfg.get("corrupt_keys", []) else body + b"x"
        open(path(key), "wb").write(stored)
        bad = key in cfg.get("corrupt_keys", []) or key in cfg.get("badsum_keys", [])
        json.dump({"sha": digest if not bad else base64.b64encode(b"\\x01" * 32).decode(), "version": "v-" + hashlib.md5(key.encode()).hexdigest()[:6]},
                  open(path(key) + ".meta", "w"))
        print(json.dumps({"ETag": "\\"x\\"", "ChecksumSHA256": digest, "VersionId": meta(key)["version"]}))
    elif op == "get-object-attributes":
        if not exists(key):
            err("404", "Not Found")
        m = meta(key)
        out = {"ObjectSize": os.path.getsize(path(key))}
        if key not in cfg.get("no_checksum_keys", []):
            out["Checksum"] = {"ChecksumSHA256": m["sha"]}
        print(json.dumps(out))
    elif op == "head-object":
        if not exists(key):
            err("404", "Not Found")
        m = meta(key)
        print(json.dumps({"ContentLength": os.path.getsize(path(key)), "ChecksumSHA256": m["sha"], "VersionId": m["version"]}))
    else:
        err("Unsupported", op)
''')


def b64(digest_hex):
    return base64.b64encode(bytes.fromhex(digest_hex)).decode()
