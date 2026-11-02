# Preliminary spike cost proposal (not a launch estimate)

Checked 2026-10-30. Ohio Linux m5.xlarge OnDemand price is USD 0.192 per instance-hour in AWS public EC2 pricing data; selected record retained in public/ec2-price-extract.json. The complete606,679-byte public catalog is retained as its 51 KiB gzip response beside the extract, with raw/decompressed hashes in the extract. Initial JSON decoding failed because the response was gzip-compressed; public/ec2-price-error.json preserves that failed interpretation. Decoding gzip recovered exactly one matching Ohio Linux m5.xlarge record. No account or paid Pricing/Cost Explorer API was called.

EMR surcharge USD 0.048 per m5.xlarge-hour and publicIPv4 USD 0.005 per address-hour are same-day retained public official rates from accepted12C; curated records/sourceURL/retrievaltime/sourcehash are copied to public/prior-12c-selected-rates.json without claiming a freshfetch.

Proposed two instances, each at most two hours total (NOT two hours per attempt):

- EC2:2*2*0.192=USD 0.768.
- EMR:2*2*0.048=USD 0.192.
- Compute subtotal:USD 0.960.

This subtotal EXCLUDES EBS root/data volumes and provisioned performance, network topology/NAT processing and any hourly minimums, TLS/artifact staging, S3 operations/storage/retention, publicIPv4 where used, external termination/watchdog costs, taxes and delayed/unreported charges. The spike has NO launch/network/storage resources yet; a final all-resource estimate would be invented. The proposed USD 10 is a ceiling for a future bounded run, not a proved cost fit or an enforceable AWS billing cutoff. Prices do not establish regional capacity/quota headroom.

Before a live approval, infra/deploy owners must produce exact resource counts/rates and conservative runtime including provisioning, bootstrap, job and shutdown; subtract nonoverlapping pending usage and existing reservations from the shared USD 200. The12C illustrative USD15 EMR reserve is replaced by/contains this spike allocation rather than added to it. Reconcile actual delayed charges after teardown. Do not poll the paid Cost Explorer API; a human console snapshot is sufficient when available.

Primary sources:
- https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ec2-ondemand-without-sec-sel/US%20East%20(Ohio)/Linux/index.json
- https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/ElasticMapReduce/current/us-east-2/index.json
- https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonVPC/current/us-east-2/index.json
- https://docs.aws.amazon.com/ec2/latest/instancetypes/gp.html (m5.xlarge: 4 vCPU / 16 GiB; two proposed nodes8vCPU total, livequota headroom unverified)
