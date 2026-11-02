# Preliminary spike cost proposal

> Updated during preparation repair round 1. Original bytes are preserved in `../12d-preparation-repair-1/original-notes/`. Earlier gates describe the pre-repair state; use the repair packet for current source and gate results.

Public Ohio Linux m5.xlarge pricing checked on October 30, 2026 is USD 0.192 per instance-hour. The selected record is in public/ec2-price-extract.json. The complete 606,679-byte catalog is retained as a compressed response, with raw and decompressed hashes. The initial UTF-8 decode failed because the response was gzip-compressed; public/ec2-price-error.json records that failure. Gzip decoding recovered one matching record. No account or paid pricing API was used.

The USD 0.048 EMR surcharge per m5.xlarge-hour and USD 0.005 public IPv4 address-hour rates were retained from the same day's accepted 12C public-price fetches. Their original source URLs, retrieval times and hashes are in public/prior-12c-selected-rates.json. They were not fetched again during this repair.

For two instances running at most two hours total, including provisioning and teardown:

- EC2: 2 × 2 × USD 0.192 = USD 0.768.
- EMR: 2 × 2 × USD 0.048 = USD 0.192.
- Compute subtotal: **USD 0.960**.

This subtotal excludes EBS, network/NAT processing and minimum charges, public IPv4 where used, TLS/artifact staging, S3 operations and retention, logs, KMS, deadline-controller resources, taxes and delayed charges. No runnable spike resource plan exists, so there is no verified all-in estimate or cost fit.

## Shared reserve consequence — F2

12C provisionally reserved **USD 15 for all EMR spikes and experiments**, including later Phase 13/15 work and the scale experiment. The former USD 10 spike proposal would consume USD 10 of that reserve, leaving **USD 15 − USD 10 = USD 5** for later EMR work.

The user has now selected a **USD 5 proposed spike cap**, leaving **USD 15 − USD 5 = USD 10** of the existing reserve if the spike spends its full cap. This is a planning suballocation inside the shared USD 200 before-credit ceiling, not an extra budget or execution approval. The reserve has not been replaced or increased.

The 12C upper-window scenario had only **USD 5.09 overall headroom**. Splitting the existing reserve differently does not increase that margin or prove the million-edge experiment fits. Later EMR runs require a **new allocation decision and an exact all-resource cost review**, using reported spending plus conservative nonoverlapping estimates of pending usage, retention and other commitments. Credits and a monthly reset do not increase the project ceiling.

Before a live run, price the exact resources, capacity, provisioning/bootstrap/job/shutdown time and uncertainty allowance against both the proposed USD 5 cap and the remaining shared budget. Use a human console snapshot when sufficient; no paid Cost Explorer query is authorized.

Primary pricing sources:
- https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ec2-ondemand-without-sec-sel/US%20East%20(Ohio)/Linux/index.json
- https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/ElasticMapReduce/current/us-east-2/index.json
- https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonVPC/current/us-east-2/index.json
- https://docs.aws.amazon.com/ec2/latest/instancetypes/gp.html

The proposed two m5.xlarge nodes require eight vCPUs in total. Live quota usage, regional capacity and release compatibility remain unverified.
