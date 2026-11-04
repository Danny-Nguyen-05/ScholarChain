#!/usr/bin/env python3
"""Offline cost replay for the simplified Phase 12D spike shape.

Uses only the reviewed public rates in ../12d-emr-design-cost/selected-rates.json
(retrieved 2026-11-03). No network or account access. Quantities are planning
bounds, not measurements. The reviewed conventions are kept: a 672-hour month
(conservative), a 25% tax allowance, a USD 0.75 reserve, and totals rounded up
to the cent.
"""
import json
import sys
from decimal import ROUND_CEILING, Decimal as D
from pathlib import Path

HERE = Path(__file__).resolve().parent
RATES = json.loads((HERE.parent / "12d-emr-design-cost" / "selected-rates.json").read_text())
R = {k: D(v["usd"]) for k, v in RATES.items()}
MONTH_H = D(672)
TAX = D("0.25")
RESERVE = D("0.75")
CAP = D(10)

NODES = 2
CLUSTER_H = D(2)                 # hard maximum cluster lifetime
EBS_GB = D(128)                  # 4 x 32 GiB gp3 (2 root + 2 data)
EFS_STORED_GB = D(5)
EFS_READ_GB, EFS_WRITE_GB = D(5), D(2)
S3_GB = D(1)
S3_PUT, S3_GET = D(1000), D(10000)   # request-bound ceilings (asserted by scripts/phase12d-spike tests)
KMS_REQ = S3_PUT + S3_GET + D(20000)  # reviewed coupling: one per S3 request + 20000 extra
NAT_GB, OUT_GB = D(2), D(1)


def lines(ancillary_h: D) -> dict:
    return {
        "ec2_compute": NODES * CLUSTER_H * R["ec2_hour"],
        "emr_surcharge": NODES * CLUSTER_H * R["emr_hour"],
        "ebs_gp3": EBS_GB * R["ebs_gp3_gb_month"] * CLUSTER_H / MONTH_H,
        "nat_hours": ancillary_h.to_integral_value(ROUND_CEILING) * R["nat_hour"],
        "public_ipv4": ancillary_h * R["ipv4_hour"],
        "nat_data": NAT_GB * R["nat_gb"],
        "internet_out": OUT_GB * R["internet_out_gb"],
        "efs_storage": EFS_STORED_GB * R["efs_gb_month"] * ancillary_h / MONTH_H,
        "efs_io": EFS_READ_GB * R["efs_read_gb"] + EFS_WRITE_GB * R["efs_write_gb"],
        "s3_storage": S3_GB * R["s3_gb_month"] * ancillary_h / MONTH_H,
        "s3_requests": S3_PUT * R["s3_put"] + S3_GET * R["s3_get"],
        "kms_key_full_month": R["kms_key_month"],  # conservative: whole month even if deleted early
        "kms_requests": KMS_REQ * R["kms_request"],
    }


def total(ls: dict) -> dict:
    sub = sum(ls.values())
    tot = (sub * (1 + TAX) + RESERVE).quantize(D("0.01"), ROUND_CEILING)
    return {"subtotal": str(sub), "total_with_tax_and_reserve": str(tot), "within_cap": tot <= CAP}


def per_day_leftover() -> dict:
    """Cost per extra 24 h if `terraform destroy` is not run after the cluster ends."""
    d = {
        "nat_gateway_24h": 24 * R["nat_hour"],
        "public_ipv4_24h": 24 * R["ipv4_hour"],
        "efs_storage_5gb_24h": EFS_STORED_GB * R["efs_gb_month"] * 24 / MONTH_H,
        "s3_storage_1gb_24h": S3_GB * R["s3_gb_month"] * 24 / MONTH_H,
        "kms_key": D(0),  # already counted as a full month above
    }
    sub = sum(d.values())
    return {"lines": {k: str(v) for k, v in d.items()}, "subtotal": str(sub),
            "with_tax": str((sub * (1 + TAX)).quantize(D("0.01"), ROUND_CEILING))}


def main() -> int:
    out = {"rates_source": "../12d-emr-design-cost/selected-rates.json", "cap_usd": str(CAP), "scenarios": {}}
    for name, h in [("nominal_ancillary_3h", D(3)), ("ancillary_24h", D(24)), ("ancillary_72h", D(72))]:
        ls = lines(h)
        out["scenarios"][name] = {"ancillary_hours": str(h), "lines": {k: str(v) for k, v in ls.items()}, **total(ls)}
    out["per_extra_day_if_not_destroyed"] = per_day_leftover()
    json.dump(out, sys.stdout, indent=1, default=str)
    print()
    return 0 if out["scenarios"]["ancillary_72h"]["within_cap"] else 1


if __name__ == "__main__":
    sys.exit(main())
