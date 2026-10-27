# F6 residual acceptance

| Requirement | Observed evidence |
| --- | --- |
| Work budget strictly below transport deadline | All allowlisted graphGETs carry explicit min(validrequested/defaultcap,T-ceil(T*P/100)), reservePdefault25 configurable1–99. DefaultT5000 gives3750ms work. Overflow-safe math and impossible split refusal tested. |
| Equal default-style budgets, absent caller timeout | RealGraphApi300ms/proxy300ms and interruptible blocking snapshot; four consecutive public requests, exactly4snapshot executions, caller-traced nonretryable504marker, CLOSED before readiness, ready200 and later success. |
| Explicit caller near transport cap | Same actual300/300 setup withtimeoutMs300; same4request assertions pass. |
| All operations consume budget | Unit wire-recording allnode/neighbors/metrics/paths budgets225/225/1; real blockednode,metrics,path calls yieldmarker onceeach. |
| Stable cursor | RealHTTPsignedcursor pagination/replay passes for omitted/explicitfullcallerbudget; forwarding depends onlyconfig/caller, no elapsed-time mutation. |
| Outages remain faults | Previous refusal, silent/no-response timeout, unready503 and strictmarker guards passed in targeted/fullgates. |
| Config and invalid inputs | Nondefault50percent/configcap demonstrates envwiring; invalid0/100reserve,cap0,tinyimpossiblesplits/caller0/-1/nonnumeric/abovecap refused. LongMax arithmetic constructs safely. |
| Current images and consistent harness | Four currentJAR/assets-verified images,eight bootcases;actual3mains graphcap500/proxy500 withreserve25 plusstopgraphhealth200/ready503 pass. |

Independent pre-fix red3run/1pass/2fail proves omitted and explicit equal-cap defect. Module red4/4failed behaviorally. Exactredsource/pre-gatehashes retained; independentnewtestidenticalredtogreen. Finalmodule5tests includes additionalconfigcase/expandedallopsguards, explicitlyreported. Existingtwoindependenttest-double wrappers receivedbudgetoverloads only; originalassertionsremain.

Final targeted services36/36in6suites and independent10A/B44/44in8suites; finalfull1216/1216in149suites,exit0,JDK17.0.20.1. See commands.md/check-summary.json and DockerresultJSON for exacttimings/hashes.

No otherfindingimplemented. F9externalCLOSED; F7,F8,F10–F16carried. F16livebackendreadiness is expressly unmodified.
