"""Retained dry runs of run-experiment.sh in a TEMP repository (fixture manifest committed there). Not part of the repo."""
import os
import shutil
import subprocess
import sys
import tempfile

REAL = "/Users/danny/Documents/UIC/CS441/ScholarChain"
OUT = sys.argv[1]
tmp = tempfile.mkdtemp(prefix="sc-exp-dry-")
repo = os.path.join(tmp, "repo")
os.makedirs(repo)


def git(*a):
    return subprocess.run(["git", "-C", repo, "-c", "user.name=T", "-c", "user.email=t@example.invalid"] + list(a), check=True, capture_output=True, text=True).stdout


git("init", "-q")


def put(rel, src=None, text=None):
    path = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if src:
        shutil.copy(src, path)
    else:
        open(path, "w").write(text)


put(".gitignore", text="target/\n")
put("scripts/config/spark-12-10.conf", src=REAL + "/scripts/config/spark-12-10.conf")
put("scripts/config/emr-pricing.conf", src=REAL + "/scripts/config/emr-pricing.conf")
F = REAL + "/scripts/tests/fixtures"
put("fixture-inputs/prep-config.json", src=F + "/pipeline/prep-config.json")
put("fixture-inputs/datasets.json", src=F + "/pipeline/datasets.json")
put("experiments/fixture/manifest.json", src=F + "/experiment/valid-manifest.json")
put("docs/agent-runs/phase-04/xml-repair-logback.xml", text="<configuration/>\n")
git("add", "-A")
git("commit", "-q", "-m", "fixture")
env = {"PATH": "/usr/bin:/bin:/opt/homebrew/bin", "HOME": tmp, "LC_ALL": "C", "SCHOLARCHAIN_REPO_ROOT": repo}


def run(label, *args):
    done = subprocess.run(["bash", REAL + "/scripts/run-experiment.sh"] + list(args), env=env, capture_output=True, text=True, cwd=tmp)
    shown = " ".join(args).replace(repo, "<repo>")
    text = "$ scripts/run-experiment.sh %s\nexit=%d\n----- stdout\n%s----- stderr\n%s" % (shown, done.returncode, done.stdout.replace(repo, "<repo>"), done.stderr.replace(repo, "<repo>"))
    open(os.path.join(OUT, label + ".txt"), "w").write(text)
    print(label, "exit", done.returncode)


manifest = os.path.join(repo, "experiments/fixture/manifest.json")
run("experiment-dry-run-committed", "--manifest", manifest, "--cluster-id", "j-ABC123DEF456")
put("experiments/fixture/untracked.json", src=F + "/experiment/valid-manifest.json")
run("experiment-refused-untracked", "--manifest", os.path.join(repo, "experiments/fixture/untracked.json"), "--cluster-id", "j-ABC123DEF456")
open(manifest, "a").write("\n")
run("experiment-refused-modified", "--manifest", manifest, "--cluster-id", "j-ABC123DEF456")
git("checkout", "--", "experiments/fixture/manifest.json")
for name in ("missing-budget", "missing-teardown"):
    put("experiments/fixture/%s.json" % name, src=F + "/experiment/%s.json" % name)
git("add", "-A")
git("commit", "-q", "-m", "more fixtures")
for name in ("missing-budget", "missing-teardown"):
    run("experiment-refused-" + name, "--manifest", os.path.join(repo, "experiments/fixture/%s.json" % name), "--cluster-id", "j-ABC123DEF456")
shutil.rmtree(tmp, ignore_errors=True)
