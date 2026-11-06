import csv, sys
rows = csv.reader(sys.stdin)
header = None
for row in rows:
    if len(row) > 10 and row[0] == "SKU":
        header = row
        break
idx = {name: i for i, name in enumerate(header)}
want = ("m5.xlarge", "m5.2xlarge")
for row in rows:
    if len(row) < len(header):
        continue
    if (row[idx["TermType"]] == "OnDemand" and row[idx["Instance Type"]] in want
            and row[idx["Operating System"]] == "Linux" and row[idx["Tenancy"]] == "Shared"
            and row[idx["Pre Installed S/W"]] == "NA" and row[idx["CapacityStatus"]] == "Used"
            and row[idx["License Model"]] == "No License required"):
        print(row[idx["Instance Type"]], row[idx["PricePerUnit"]], row[idx["Unit"]], row[idx["Location"]], row[idx["Product Family"]], row[idx["Effective Date"]] if "Effective Date" in idx else "")
