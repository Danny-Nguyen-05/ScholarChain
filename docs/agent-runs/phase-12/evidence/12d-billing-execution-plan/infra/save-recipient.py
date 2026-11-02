from pathlib import Path
import getpass, json, os, re, sys, warnings
if not sys.stdin.isatty():
    raise SystemExit("Run this helper directly in an interactive Terminal; nothing saved.")
warnings.simplefilter("error", getpass.GetPassWarning)
p=Path("/tmp/scholarchain-phase12d-billing-execution-plan/notification.private.tfvars.json")
address=getpass.getpass("Budget notification email (hidden): ").strip()
if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",address):
    raise SystemExit("Email format not accepted; nothing saved.")
confirm=getpass.getpass("Repeat notification email (hidden): ").strip()
if address != confirm:
    raise SystemExit("Entries differ; nothing saved.")
fd=os.open(p, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
with os.fdopen(fd,"w") as out:
    json.dump({"budget_notification_emails":[address]},out)
    out.write("\n")
print("Private notification input saved successfully.")
