# EMR design costing — proposal, not an execution gate

The complete nominal model is **USD5.30**, exceeding the proposed USD5 allowance. It does not support launch of the current draft. A separately identified lower-request candidate models at **USD4.82**, but its request/I/O/retention quantities are unverified. No current account funds, regional capacity, exact isolated plan or spending authority has been established. The existing USD5 proposal is not raised.

The earlier USD4.88 figure is superseded. It allowed20000 KMS operations independently of100000 S3 GET and10000 PUT/LIST requests against proposed SSE-KMS objects. Without assuming bucket-key/caching savings, that is inconsistent. The current model allows one KMS operation per proposed S3 request unit plus20000 additional operations:130000 total. This is a coherent planning envelope, not proof that every service and multipart operation is bounded by it. Previous model/source bytes are preserved under prior-cost-model/; research-and-calculation-errata.md explains the correction. No account data prompted this change.

## Proposed footprint and lifetimes

- Same user-selected shape: one primary and one core m5.xlarge, Ohio, no task/Spot/scaling, one cluster attempt. Two hours total cluster lifetime includes startup, bootstrap, job and termination.
- Private nodes in one AZ; one zonal public NAT gateway/EIP in a separate public subnet, restricted S3 gateway endpoint, Regional EFS Standard/General Purpose/Elastic and one same-AZ mount target/access point. Interface endpoints are not selected in this model. Supporting network/EBS/EFS active target is3hours including setup/cleanup, conditional on the proposed independent cleanup workflow. This is not an observed or guaranteed lifetime.
- Four explicitly bounded gp3 volumes: two32GiB roots plus two32GiB data volumes,128GiB total, baseline3000IOPS/125MBps only. Actual Terraform defaults and release requirements must be reconciled; no unpriced default volumes, snapshots, performance add-ons or backup jobs may appear.
- EFS modeled at5GB stored,5GB metered reads and2GB metered writes. Include metadata/operation minimums; raw fixture/archive size cannot establish those metered amounts. No IA/archive, backup, replication or provisioned throughput is selected. Explicitly disable optional automatic backups in any later implementation or reprice them.
- One combined1GB S3 allowance including all object versions, artifacts, control state, logs and evidence;10000 PUT/LIST and100000 GET/HEAD units. Retain evidence and its one symmetric nonrotated CMK for31days;130000 KMS operations. Retention and eventual protected archival/cleanup require a human decision. No automatic deletion of grading originals is authorized here.
- All CloudWatch logs together0.25GB ingestion plus retained storage31days; two standard alarms31days and one guard custom metric3hours. No dashboards/extra metrics/agent defaults are silently free.
- Proposed guard/cleanup envelopes:360 Lambda invocations at256MiB and30seconds each including cold starts/retries,360 Scheduler invocations,200 Step Functions Standard transitions including retries/catches,1000 Standard SQS64KiB request units and20 small SNS publish/email deliveries. No free-tier deduction or delivery guarantee. The exact future workflow must reconcile these quantities.
- NAT processing2GB, internet data out1GB; S3 gateway traffic and same-AZ EFS traffic do not get charged again as NAT/cross-AZ traffic. No cross-AZ node placement is assumed. Any placement/topology change requires recalculation.

Every quantity above is a proposed limit to substantiate, not a measurement or an implemented enforcement mechanism. The nominal proposal is deliberately incomplete as a launch gate.

## Published rates and arithmetic

Current anonymous public AWS catalogs/pages were retrieved on2026-11-03. selected-rates.json retains28 chosen rates with region, unit, exact SKU/rate dimension or published worked-example basis, source URL, publication/retrieval times and hashes. public-prices/ retains compressed decoded responses and request records. These are public HTTPS requests; no Pricing account API, Cost Explorer query, profile or credentials were used.

Two-node EC2+EMR compute is2*2*(0.192+0.048)=**USD0.96**. The EMR surcharge is additional to EC2/EBS, not the entire cluster price. The official Ohio EC2/EMR records support those rates. Ohio gp3 is0.08/GB-month, Regional EFS Standard0.30/GB-month, Elastic read0.03/GB and write0.06/GB. The Ohio VPC worked example supplies NAT0.045/hour,0.045/GB and internet egress0.09/GB; the regional catalog supplies publicIPv4 at0.005/hour. Each partial NAT gateway hour rounds up. Full source bindings are in selected-rates.json, rather than treating generic web examples as exact regional catalog entries.

Monthly units use a deliberately conservative672-hour denominator (28days), with744hours of proposed retention. This is planning arithmetic, not an assertion about AWS invoice proration. Actual dated retention and service billing rules must be reconciled before execution. Positive paid marginal request rates are used even where published free tiers exist; account entitlement, credits, discounts and monthly-reset funds are not assumed.

The tax allowance is25% of the modeled subtotal, followed by an additionalUSD0.75 uncertainty reserve.25% is a sensitivity parameter, not an observed tax jurisdiction/rate; applicable higher tax/support obligations would invalidate the modeled result. All historical account costs and commitments belong in the separate F4 account-wide reconciliation, not in an assumed credit.

| Scenario | Total including tax allowance/reserve | Interpretation |
|---|---:|---|
| Nominal complete footprint, request/encryption coupling corrected | $5.30 | Exceeds proposed $5; no launch recommendation |
| EFS10GB reads/5GB writes and1GB logs | $6.21 | I/O/log sensitivity exceeds cap |
| Evidence/key/log/alarm retention90days | $8.54 | Retention is a material continuing liability |
| ancillary resources active 24 h total (21 h beyond nominal) | $7.52 | Cluster termination alone cannot bound full resource cost |
| Unselected lower-request candidate:1000 PUT/LIST,10000 GET/HEAD,31000 KMS | $4.82 | Conditional arithmetic fit only; request bounds still need proof |

Totals round upward to cents, with unrounded Decimal values and complete line items retained in cost-calculations.json. replay-cost.py reproduces selection and arithmetic from saved public data without network or account access; an independent Fraction calculation cross-checks multiplication/sums to substantially below one cent.

The lower-request candidate preserves nodes, network, EFS mode, lifetimes and all other quantities. It is an explicit option, not a quiet reduction of an approved estimate. A pinned staging/runtime/guard request inventory and service metering analysis would need to support its11000 S3 and31000 KMS units before it could replace the nominal envelope. Merely lowering a number until the total fits is not acceptance evidence. Regional Bursting is a separate unselected throughput alternative discussed by the infra owner; it has not been substituted into this model.

## Account-wide allowance and open proof

The proposedUSD5 is contained within the existingUSD15 all-EMR reserve/sharedUSD200 ceiling;USD10 would remain for later EMR ifUSD5 is spent. The prior12C upper-window marginUSD5.09 is historical modeling, not today's spend/balance. No budget reset or unused credits are inferred. A current conservative reconciliation must account for delayed/unreported charges, retained resources, pending commitments, taxes/support and any earlier live bootstrap resources. No account query was authorized or run in this proposal.

The prearmed termination guard and separate ancillary cleanup workflow are mandatory, but unimplemented. They must handle unknown resource IDs, tag visibility, protected lease binding, API errors, archive failures and exact-resource permissions. Neither an idle timeout nor a local command timeout establishes elapsed lifetime. If identity binding, cleanup or headroom cannot be demonstrated, stop before launching. No dollar cap can be guaranteed by the account budget alert.

Next is independent review of this design/cost proposal. The subsequent bounded offline work should pin the portable custom runtime and its request/artifact inventory, then author/test the isolated guard/resource configuration under its own work order. Account preflight, genuine isolated plan, source-controlled reviewed release, exact human execution gate and one remote attempt come later. There is no need for a login now.

## Primary source links

- [Ohio Linux EC2 public table](https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ec2-ondemand-without-sec-sel/US%20East%20%28Ohio%29/Linux/index.json)
- [Ohio EMR catalog](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/ElasticMapReduce/current/us-east-2/index.json)
- [Official EBS table](https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ebs.json) and [EBS pricing rules](https://aws.amazon.com/ebs/pricing/)
- [Ohio EFS catalog](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEFS/current/us-east-2/index.json) and [EFS metering/performance](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
- [VPC pricing and Ohio example](https://aws.amazon.com/vpc/pricing/)
- [KMS pricing/retention](https://aws.amazon.com/kms/pricing/)
- Remaining regional request/storage/controller rates: exact URLs and dimensions in selected-rates.json. Technical primary references are retained in infra/sources.json.
