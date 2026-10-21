# ScholarChain AI review drafts — batch 06 (tasks 101–120)

> **Status: AI_SUGGESTIONS_PENDING_HUMAN_REVIEW.** These are AI-generated suggestions from a session-reported `claude-opus-5-5` model (not independently verified). They are not human reviews or gold labels. Record your own decision in each task's decision box; an empty box means not reviewed.

Queue: `review-queue:05c5817f62a70d378829be361b9c9169fc9af18448f7c83c245f1d65bbca6175`  
Work tasks: 1 · Researcher tasks: 19

Rows marked `>> … <<` in the raw data and the 'Name as written' row identify the mention being compared. OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider hypotheses. Lines in _italics_ starting with 'helper:' are exact-string comparisons computed by a script to help reading; they are not judgments.

---
## Task 101 — Researcher

- **pairId:** `resolution-pair:1b7df06d4ac0ebf5bc2b79330f06bb639c70b8b42df351b1270d523808474c35`
- **evidenceHash:** `aaa46489517f9b2efe37f912dce4550f6eec194c70e497f601381d6b08391981`
- **Question:** do mention A `mention:openalex:W3198515637#3` and B `mention:openalex:W4289533977#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3198515637#3 | mention:openalex:W4289533977#4 |
| Name as written | Jianliang Xu | Jianliang Xu |
| Author position | 3 of 4 | 4 of 6 |
| ORCID on mention | 0000-0001-9404-5848 (OpenAlex-supplied) | 0000-0001-9404-5848 (OpenAlex-supplied) |
| OpenAlex author ID | A5008564713 | A5008564713 |
| Affiliation | ROR 0145fw131 | ROR 0145fw131 |
| Work title | SlimChain | vChain+: Optimizing Verifiable Blockchain Boolean Range Queries |
| Year | 2021 | 2022 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210210321 |
| DOI | 10.14778/3476249.3476283 | 10.1109/icde53745.2022.00190 |
| Coauthors | Cheng Xu, Ce Zhang, Jian Pei | Haixin Wang, Cheng Xu, Ce Zhang, Zhe Peng, Jian Pei |

_helper: shared coauthor normalizedNames = ['ce zhang', 'cheng xu', 'jian pei']_
_helper: target-mention ROR A=['0145fw131'] B=['0145fw131'] shared=['0145fw131']_

**AI-proposed label: `same`**

**Note:** Both "Jianliang Xu" mentions share three coauthors (Ce Zhang, Cheng Xu, Jian Pei), the same ROR 0145fw131, and verifiable-blockchain-query topics ("SlimChain" 2021; "vChain+: Optimizing Verifiable Blockchain Boolean Range Queries" 2022).

**Supporting evidence:**
- Name exact match: A author#3, B author#4
- Three shared coauthors: Ce Zhang, Cheng Xu, Jian Pei
- enrichment ror=0145fw131 on both target mentions
- Topic continuity: blockchain query systems
- Same OpenAlex-supplied observedOrcid 0000-0001-9404-5848 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- All hints OpenAlex-derived

<details><summary>Evidence references</summary>

- A `work` `er-evidence:211e4e51b6ffcf680947ff3d349488dc074dbfb17a649ed3860360c0f8ba02dd` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:180`
- A `enrichment` `er-evidence:83a5d5a1bc3df0f7a60e929886ba3d4b7abf4556d462dff591f9cb4d2fbc2afe` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1939`
- B `enrichment` `er-evidence:3ffe1453432b12409469d16952e2322950e5250da360f7f92092b63e41a90a51` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1413`
- B `work` `er-evidence:b6787ca62ab1597b17753759c6552915679ef79e7f125146f635154ec72f1c0a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:132`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 102 — Researcher

- **pairId:** `resolution-pair:e8ccef9b2e587aa7d50e9db60fdf4653d482b36ee8661a239697cd859ec173b8`
- **evidenceHash:** `ef45327924d23ce0f7a7eea9ee241b10d25dd4575dae3676171611ae63e24b01`
- **Question:** do mention A `mention:openalex:W4366492480#6` and B `mention:openalex:W4366502978#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4366492480#6 | mention:openalex:W4366502978#2 |
| Name as written | Ziniu Wu | Ziniu Wu |
| Author position | 6 of 7 | 2 of 8 |
| ORCID on mention | 0000-0002-4405-0865 (OpenAlex-supplied) | 0000-0002-4405-0865 (OpenAlex-supplied) |
| OpenAlex author ID | A5002733135 | A5002733135 |
| Affiliation | ROR 042nb2s44 | ROR 042nb2s44; ROR 01e85r662 |
| Work title | Lero: A Learning-to-Rank Query Optimizer | Robust Query Driven Cardinality Estimation under Changing Workloads |
| Year | 2023 | 2023 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210226185 |
| DOI | 10.14778/3583140.3583160 | 10.14778/3583140.3583164 |
| Coauthors | Rong Zhu, Wei Chen, Bolin Ding, Xingguang Chen, Andreas Pfadler, Jingren Zhou | Parimarjan Negi, Andreas Kipf, Nesime Tatbul, Ryan Marcus, Sam Madden, Tim Kraska, Mohammad Alizadeh |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['042nb2s44'] B=['01e85r662', '042nb2s44'] shared=['042nb2s44']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Ziniu Wu" with ROR 042nb2s44 on both, in 2023 VLDB papers on learned query optimization and cardinality estimation ("Lero: A Learning-to-Rank Query Optimizer"; "Robust Query Driven Cardinality Estimation under Changing Workloads").

**Supporting evidence:**
- Name exact match: A author#6, B author#2
- enrichment ror=042nb2s44 present on both target mentions (B also 01e85r662)
- Specific topic continuity: learned query optimization/cardinality estimation
- Same year 2023 and venueId S4210226185
- Same OpenAlex-supplied observedOrcid 0000-0002-4405-0865 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- Relies on name, affiliation and topic; no coauthor or registry ORCID link

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:28178fdda7a9df5a02be5eb4b07f35a1eb8300fb6f18675e884f4d0754a62967` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1279`
- A `work` `er-evidence:8b5cc35a989d5afac5411c2b964977382929fc219deb261f8d5788d4b28698fd` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:116`
- B `enrichment` `er-evidence:206b3c9261005d1ba6e3072f0445561e012e4cda86e3565f5083d2a32ea160fa` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1269`
- B `enrichment` `er-evidence:56a011e47ba76059603b133f5d078a74c945e5bdc1ec2b4f4a866067e68c2da6` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1271`
- B `work` `er-evidence:6d13aed5c9a4da1dbb5409677f9453498e55d5d7e57a97cca6b5a0d40116e76d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:115`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 103 — Researcher

- **pairId:** `resolution-pair:3304a4781fb67b8235b16ef0a751ce7f4701a70636859aac2383d9dd17340222`
- **evidenceHash:** `d157c0980b1fb6ba4d1f7c8b2e1ec9f5e4a3aacb6bb23b1d3d01589ec05427e9`
- **Question:** do mention A `mention:openalex:W4289533840#3` and B `mention:openalex:W4289866548#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4289533840#3 | mention:openalex:W4289866548#3 |
| Name as written | Chenjuan Guo | Chenjuan Guo |
| Author position | 3 of 7 | 3 of 7 |
| ORCID on mention | 0000-0002-4516-4637 (OpenAlex-supplied) | 0000-0002-4516-4637 (OpenAlex-supplied) |
| OpenAlex author ID | A5084021933 | A5084021933 |
| Affiliation | ROR 04m5j1k67 | ROR 04m5j1k67 |
| Work title | Robust and Explainable Autoencoders for Unsupervised Time Series Outlier Detection | Anomaly Detection in Time Series with Robust Variational Quasi-Recurrent Autoencoders |
| Year | 2022 | 2022 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210210321 |
| DOI | 10.1109/icde53745.2022.00273 | 10.1109/icde53745.2022.00105 |
| Coauthors | Tung Kieu, Bin Yang, Christian S. Jensen, Yan Zhao, Feiteng Huang, Kai Zheng | Tung Kieu, Bin Yang, Razvan-Gabriel Cirstea, Yan Zhao, Yale Song, Christian S. Jensen |

_helper: shared coauthor normalizedNames = ['bin yang', 'christian s. jensen', 'tung kieu', 'yan zhao']_
_helper: target-mention ROR A=['04m5j1k67'] B=['04m5j1k67'] shared=['04m5j1k67']_

**AI-proposed label: `same`**

**Note:** Both mentions are author#3 "Chenjuan Guo" on 2022 ICDE time-series anomaly-detection autoencoder papers sharing four coauthors (Tung Kieu, Bin Yang, Yan Zhao, Christian S. Jensen) and the same ROR 04m5j1k67.

**Supporting evidence:**
- Name exact match at author#3
- Four shared coauthors
- enrichment ror=04m5j1k67 on both target mentions
- Same topic (time-series anomaly detection with autoencoders), year and venue
- Same OpenAlex-supplied observedOrcid 0000-0002-4516-4637 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- All hints OpenAlex-derived

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:192b7e3b035cdfe7c491e2aa764e1a073de1b7436bed065fbb8c5c09c6e57466` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1441`
- A `work` `er-evidence:c8d047e855bad795bc36bbc14b064f84ccdd20986c01b5ca68534a23f62f2350` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:134`
- B `enrichment` `er-evidence:2ee269fa32333d1d563a89842359b631d856985c0bb3389eed2c49bd55aeeed6` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1401`
- B `work` `er-evidence:7c6e1ccbed16d6e3d5b81cf29d9179f22b4fc374cbb97bb3c36d7d27c211d5fc` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:130`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 104 — Researcher

- **pairId:** `resolution-pair:3242a51af4f3e3d47fb0f7699b456bf9bdb3e1156da49296147639fdffa4b3ec`
- **evidenceHash:** `9a9b27463155e0142cc773b23260cbe58d7863a3379e92ac0067cf41d9b4bc70`
- **Question:** do mention A `mention:openalex:W2914529374#1` and B `mention:openalex:W3031161010#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2914529374#1 | mention:openalex:W3031161010#3 |
| Name as written | Fengan Li | Feifei Li |
| Author position | 1 of 7 | 3 of 5 |
| ORCID on mention | — | 0009-0003-0770-5775 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5100450470 |
| Affiliation | ROR 01y2jtd41 | ROR 03r0ha626 |
| Work title | Tuple-oriented Compression for Large-scale Mini-batch Stochastic Gradient Descent | FalconDB: Blockchain-based Collaborative Database |
| Year | 2019 | 2020 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4393915683 |
| DOI | 10.1145/3299869.3300070 | 10.1145/3318464.3380594 |
| Coauthors | Lingjiao Chen, Yijing Zeng, Arun Kumar, Xi Wu, Jeffrey F. Naughton, Jignesh M. Patel | Yanqing Peng, Min Du, Raymond Cheng, Dawn Song |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01y2jtd41'] B=['03r0ha626'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#1 "Fengan Li" and B author#3 "Feifei Li" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Fengan" vs "Feifei"
- No shared coauthors
- enrichment ror differs: 01y2jtd41 vs 03r0ha626

**Conflicting evidence:**
- Same venueId S4393915683

**Limitations / missing information:**
- A mention has no ORCID

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:3d9cfc79b2144abefc1cca40a4dfaa1d3b1f855e62b5d5a67a0a55a5ebed35bd` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3796`
- A `work` `er-evidence:e9ad95ef7180bf936ac95244b80ad4afe66bb3ca9496abfa4a488ce4b79d5337` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:363`
- B `work` `er-evidence:b687b5023963cfc7bfd0ade65f83e56760fb6b50f796494204f6804225021bb8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:271`
- B `enrichment` `er-evidence:f7712fcb437510b2eec5f9391a0d4fadb6161ecc98c791213a1feda2573a4bf7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2939`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 105 — Researcher

- **pairId:** `resolution-pair:8382597d97af42bb3e044641859385404e8322c1e928edc9ace87c8e0a7d54da`
- **evidenceHash:** `123cf8fdc33c0767230fbaaec3283c7e207d874342e87b84fa15b833f72198a2`
- **Question:** do mention A `mention:openalex:W2794717842#1` and B `mention:openalex:W4285179693#5` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2794717842#1 | mention:openalex:W4285179693#5 |
| Name as written | Tianzheng Wang | Tianwen Wang |
| Author position | 1 of 3 | 5 of 5 |
| ORCID on mention | 0000-0003-0965-9592 (OpenAlex-supplied) | 0000-0001-7440-0056 (OpenAlex-supplied) |
| OpenAlex author ID | A5101598171 | A5019308017 |
| Affiliation | ROR 03dbr7087 | ROR 01tgyzw49 |
| Work title | Easy Lock-Free Indexing in Non-Volatile Memory | Hybrid blockchain database systems |
| Year | 2018 | 2022 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210226185 |
| DOI | 10.1109/icde.2018.00049 | 10.14778/3510397.3510406 |
| Coauthors | Justin Levandoski, Per-Ake Larson | Zerui Ge, Dumitrel Loghin, Beng Chin Ooi, Pingcheng Ruan |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['03dbr7087'] B=['01tgyzw49'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#1 "Tianzheng Wang" and B author#5 "Tianwen Wang" differ in given name (Tianzheng vs Tianwen); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Tianzheng" vs "Tianwen"
- No shared coauthors
- enrichment ror differs: 03dbr7087 vs 01tgyzw49
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:74fb3ec07301b3145fd2c8277f63e937c57d012919a74606133c21f848918a67` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4415`
- A `work` `er-evidence:d6de8e0c8a43b3ca33de006d46039065352fb3c2b8362a5755c06be428367ac4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:435`
- B `enrichment` `er-evidence:70ba6d3a4d91e90db4fa7473ac77d125af105051e7f130f1018b0b7df85723d4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1522`
- B `work` `er-evidence:7e2c53e8b8615e5d4be4225237e3edbab9266563825abf358915e92dc695ee21` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:142`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 106 — Researcher

- **pairId:** `resolution-pair:7ace0cee5ab3ea4f0bc5acbdba02d4e0613faaaa0b2d1602bd71cbc3cfad9c32`
- **evidenceHash:** `c3c7680970fd1da9053b933cc1df224b0814008ad3781ad11d683d967d5b4508`
- **Question:** do mention A `mention:openalex:W2970773487#6` and B `mention:openalex:W4388041083#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2970773487#6 | mention:openalex:W4388041083#4 |
| Name as written | Bo Li | Baolin Li |
| Author position | 6 of 9 | 4 of 8 |
| ORCID on mention | — | 0000-0001-9778-1023 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5100733204 |
| Affiliation | ROR 047426m28 | ROR 04t5xt781 |
| Work title | Efficient task-specific data valuation for nearest neighbor algorithms | Sustainable Supercomputing for AI |
| Year | 2019 | 2023 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S7407088165 |
| DOI | 10.14778/3342263.3342637 | 10.1145/3620678.3624793 |
| Coauthors | Ruoxi Jia, David Dao, Boxin Wang, Frances Ann Hubis, Nezihe Merve Gurel, Ce Zhang, Costas Spanos, Dawn Song | Dan Zhao, Siddharth Samsi, Joseph McDonald, David Bestor, Michael Jones, Devesh Tiwari, Vijay Gadepally |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['047426m28'] B=['04t5xt781'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#6 "Bo Li" and B author#4 "Baolin Li" have different given names (Bo vs Baolin); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Bo" vs "Baolin"
- No shared coauthors
- enrichment ror differs: 047426m28 vs 04t5xt781

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A mention has no ORCID

<details><summary>Evidence references</summary>

- A `work` `er-evidence:03ef2208aa7734a65889ae31546d72edf8c84050607e61b7e9aa7486493c3ba4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:325`
- A `enrichment` `er-evidence:d8b48e20bd0581b75d1b424d59118a2259c3dc13bfe95323da032206070c8db8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3406`
- B `enrichment` `er-evidence:40c99faf55e16b1606f89d4b0bb323dce6325aaae359caf4025f50b35968d09b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:670`
- B `work` `er-evidence:b7e93d6cf73680b225e819e58e7a2772ea9776ae47f4a40f89f07d16ae7c12d3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:61`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 107 — Researcher

- **pairId:** `resolution-pair:35ab3ccd7b21ef14b6e01b1523f4ef62b1f578023b2dd4945c19efb99814a5ba`
- **evidenceHash:** `1846cc6a59e02a668e0bedf56900b1e52f0e6a357accfbaa2ba9c79694f1fee5`
- **Question:** do mention A `mention:openalex:W2948709946#10` and B `mention:openalex:W4387321091#8` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2948709946#10 | mention:openalex:W4387321091#8 |
| Name as written | Haojun Zhang | Hao Zhang |
| Author position | 10 of 20 | 8 of 9 |
| ORCID on mention | 0000-0002-9801-2514 (OpenAlex-supplied) | 0009-0003-8392-3977 (OpenAlex-supplied) |
| OpenAlex author ID | A5101961485 | A5092145402 |
| Affiliation | ROR 01y2jtd41 | ROR 0168r3w48 |
| Work title | Entity Matching Meets Data Science | Efficient Memory Management for Large Language Model Serving with PagedAttention |
| Year | 2019 | 2023 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4306420989 |
| DOI | 10.1145/3299869.3314042 | 10.1145/3600006.3613165 |
| Coauthors | Yash Govind, Pradap Konda, Paul Suganthan G.C., Philip Martinkus, Palaniappan Nagarajan, Han Li, Aravind Soundararajan, Sidharth Mudgal, Jeff R. Ballard, Adel Ardalan, Sanjib Das, Derek Paulsen, Amanpreet Singh Saini, Erik Paulson, Youngchoon Park, Marshall Carter, Mingju Sun, Glenn M. Fung, AnHai Doan | Woosuk Kwon, Zhuohan Li, Siyuan Zhuang, Ying Sheng, Lianmin Zheng, Cody Hao Yu, Joseph Gonzalez, Ion Stoica |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01y2jtd41'] B=['0168r3w48'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#10 "Haojun Zhang" and B author#8 "Hao Zhang" are different given names (Haojun vs Hao), with no shared coauthors, different RORs and different OpenAlex-supplied ORCIDs.

**Supporting evidence:**
- nameText given names differ: "Haojun" vs "Hao"
- No shared coauthors
- enrichment ror differs: 01y2jtd41 vs 0168r3w48
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- "Hao" is a prefix of "Haojun"; a truncated source name would weaken the difference

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:1901fef5cc42d327fdcc18366837f91b5f3d398d17361defccbca71ccf4fcf71` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3620`
- A `work` `er-evidence:c0b57e8bf04dfcab0dcef8bb915a02ecddd4115a60eb7b816d1555fd3857de37` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:346`
- B `work` `er-evidence:37f6d5191c3137e5660487f93af5d1ccd3a09835ebfcf48dc0797e6e56a83cd8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:73`
- B `enrichment` `er-evidence:862100db454eb7010dd0b63abfe7567bdf432dcc8726d5c3a484571535e90cc3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:810`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 108 — Researcher

- **pairId:** `resolution-pair:adfe5c686168d62b5ff148cbf3a6835cfa95c96c44ad8b0974bf32d9c8cb222d`
- **evidenceHash:** `ca72c75fccb5aa1193bc03646894111d5331c39140f9e662cfe3c42ca949e31d`
- **Question:** do mention A `mention:openalex:W2903368601#3` and B `mention:openalex:W3176377144#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2903368601#3 | mention:openalex:W3176377144#4 |
| Name as written | Jianliang Xu | Jianliang Xu |
| Author position | 3 of 3 | 4 of 5 |
| ORCID on mention | 0000-0001-9404-5848 (OpenAlex-supplied) | 0000-0001-9404-5848 (OpenAlex-supplied) |
| OpenAlex author ID | A5008564713 | A5008564713 |
| Affiliation | ROR 0145fw131 | ROR 0145fw131 |
| Work title | vChain | Authenticated Keyword Search in Scalable Hybrid-Storage Blockchains |
| Year | 2019 | 2021 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210210321 |
| DOI | 10.1145/3299869.3300083 | 10.1109/icde51399.2021.00091 |
| Coauthors | Cheng Xu, Ce Zhang | Ce Zhang, Cheng Xu, Haixin Wang, Byron Choi |

_helper: shared coauthor normalizedNames = ['ce zhang', 'cheng xu']_
_helper: target-mention ROR A=['0145fw131'] B=['0145fw131'] shared=['0145fw131']_

**AI-proposed label: `same`**

**Note:** Both "Jianliang Xu" mentions share coauthors Ce Zhang and Cheng Xu, the same ROR 0145fw131, and authenticated blockchain query topics ("vChain" 2019; "Authenticated Keyword Search in Scalable Hybrid-Storage Blockchains" 2021).

**Supporting evidence:**
- Name exact match: A author#3, B author#4
- Two shared coauthors: Ce Zhang, Cheng Xu
- enrichment ror=0145fw131 on both target mentions
- Topic continuity: authenticated blockchain queries
- Same OpenAlex-supplied observedOrcid 0000-0001-9404-5848 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- All hints OpenAlex-derived

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:3d0df5e6d1268b79e5b8731b94f6419a3ed686433dd7d0dbbdb49057c2c265c8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3868`
- A `work` `er-evidence:5caab674bd2f50d0ee8c9a14520d0f118dcdbbc2b7cce5c0f16bea05149dac72` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:373`
- B `work` `er-evidence:909869c222154337058817e2344e0f218220f288c1a9b705545263b42a113c0f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:190`
- B `enrichment` `er-evidence:b1098ba9a62d6de41e4214f6a6a1ca163d251bdd57665b7e91b2b131cdf5ed25` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2093`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 109 — Researcher

- **pairId:** `resolution-pair:c86ed53c202419825ac9bea163a2de0c7898e4ebef5ec4da8d8915a0e26d048f`
- **evidenceHash:** `2eeea2006b3a27ed3de1e83c3e841cb860e318777b86539b044514915b5330f8`
- **Question:** do mention A `mention:openalex:W3029150735#5` and B `mention:openalex:W4286971399#7` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3029150735#5 | mention:openalex:W4286971399#7 |
| Name as written | Ying Zhang | Yong Zhang |
| Author position | 5 of 5 | 7 of 7 |
| ORCID on mention | 0000-0002-2674-1638 (OpenAlex-supplied) | 0000-0003-3928-8761 (OpenAlex-supplied) |
| OpenAlex author ID | A5100386104 | A5100419879 |
| Affiliation | ROR 02n96ep67 | ROR 026venb53 |
| Work title | Efficient Bitruss Decomposition for Large-scale Bipartite Graphs | Improving Fairness for Data Valuation in Horizontal Federated Learning |
| Year | 2020 | 2022 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210210321 |
| DOI | 10.1109/icde48307.2020.00063 | 10.1109/icde53745.2022.00228 |
| Coauthors | Kai Wang, Xuemin Lin, Lu Qin, Wenjie Zhang | Zhenan Fan, Huang Fang, Zirui Zhou, Jian Pei, Michael P. Friedlander, Changxin Liu |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['02n96ep67'] B=['026venb53'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#5 "Ying Zhang" and B author#7 "Yong Zhang" differ in given name (Ying vs Yong); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Ying" vs "Yong"
- No shared coauthors
- enrichment ror differs: 02n96ep67 vs 026venb53
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- Same venueId S4210210321

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:41f6558af10567cc486e199f81c732989870965963f4271c0f29e42bae68335f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:285`
- A `enrichment` `er-evidence:450193c3d5b3d9ac77482b49b5c3e86d599c18592d47f99b73992ed456720cd6` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3060`
- B `work` `er-evidence:53e50a23ccc566c47d12a77cb8e3f93c97ef23e190a131e75a9575c3390a3205` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:141`
- B `enrichment` `er-evidence:af217480d590f0a338334b7f46ed69c3f509bd8a6552fb47236864951ea09d37` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1508`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 110 — Researcher

- **pairId:** `resolution-pair:0a81608e2ccd1e539985776df6f4e270a4ff3e449651583e3a6e76c230d695d8`
- **evidenceHash:** `f8297bcf8ec72167edfb573ce78ae767c877f470be629d8d919dc1caf263aedf`
- **Question:** do mention A `mention:crossref:10.1145/3299887.3299900#2` and B `mention:openalex:W2999832078#12` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:crossref:10.1145/3299887.3299900#2 | mention:openalex:W2999832078#12 |
| Name as written | Xiaokui Xiaokui Xiao | Xiaokui Xiao |
| Author position | 2 of 2 | 12 of 15 |
| ORCID on mention | — | 0000-0003-0914-4580 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5010903591 |
| Affiliation | "Nanyang Technological University, Nanyang, Singapore" | ROR 01tgyzw49 |
| Work title | DANTE | The Disruptions of 5G on Data-Driven Technologies and Applications |
| Year | 2018 | 2020 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S30698027 |
| DOI | 10.1145/3299887.3299900 | 10.1109/tkde.2020.2967670 |
| Coauthors | Sourav S. Bhowmick | Dumitrel Loghin, Shaofeng Cai, Gang Chen, Tien Tuan Anh Dinh, Feiyi Fan, Qian Lin, Janice Ng, Beng Chin Ooi, Xutao Sun, Quang-Trung Ta, Wei Wang, Yang Yang, Meihui Zhang, Zhonghua Zhang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=- B=['01tgyzw49'] shared=none_

**AI-proposed label: `uncertain`**

**Note:** A's Crossref nameText is the irregular "Xiaokui Xiaokui Xiao" (affiliation "Nanyang Technological University…") and B is "Xiaokui Xiao" (ROR 01tgyzw49) on a 15-author 5G survey; no coauthor is shared and the affiliation forms are not comparable.

**Supporting evidence:**
- Name compatible apart from the duplicated given name in A

**Conflicting evidence:**
- No shared coauthors (A: Sourav S. Bhowmick; B: 14 others)

**Limitations / missing information:**
- A organizationName string vs B ROR id without a name cannot be compared
- Topics unrelated by title ("DANTE" vs 5G and data-driven technologies)
- B observedOrcid is OpenAlex-supplied only

<details><summary>Evidence references</summary>

- A `mention-affiliation` `er-evidence:337e5265b9f5b64f4da5d0db0cd35159c5d69c544cd31150833d01bd2a09d178` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/mention-affiliation/part-r-00000:40`
- A `work` `er-evidence:690d131b6af699b1f16bff88ab11c81b14fbd5b45d538e17840e146128ff4308` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:10`
- B `enrichment` `er-evidence:389c0202b04f10e278ce1bdd0df327d5dd95520fe53766f384aa4db0c6240bad` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3208`
- B `work` `er-evidence:6c0b33388e2251485298030b2bf5668a67f68cba6d263bf25331c4c56a0c6c7b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:302`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Both DOIs are listed in ORCID record 0000-0003-0914-4580 (Xiaokui Xiao, pub.orcid.org) and Semantic Scholar assigns the same author ID on both papers (api.semanticscholar.org).

---

## Task 111 — Researcher

- **pairId:** `resolution-pair:356215d9111fdb83b0ff4faac04a31c1ead8c3ba3187285e9fd887fe29e70148`
- **evidenceHash:** `d7d209f2555aaee9ea0f32ee480312d6aa67069ec61284a10500891164238d29`
- **Question:** do mention A `mention:openalex:W2951096868#2` and B `mention:openalex:W4381621971#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2951096868#2 | mention:openalex:W4381621971#3 |
| Name as written | Guoliang Li | Guoliang Li |
| Author position | 2 of 2 | 3 of 3 |
| ORCID on mention | 0000-0002-1398-0621 (OpenAlex-supplied) | 0000-0002-1398-0621 (OpenAlex-supplied) |
| OpenAlex author ID | A5100451576 | A5100451576 |
| Affiliation | ROR 03cve4549 | ROR 03cve4549 |
| Work title | Distributed In-memory Trajectory Similarity Search and Join on Road Network | Learned Index: A Comprehensive Experimental Evaluation |
| Year | 2019 | 2023 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210226185 |
| DOI | 10.1109/icde.2019.00115 | 10.14778/3594512.3594528 |
| Coauthors | Haitao Yuan | Zhaoyan Sun, Xuanhe Zhou |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['03cve4549'] B=['03cve4549'] shared=['03cve4549']_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Guoliang Li" with ROR 03cve4549, but there is no shared coauthor (A: Haitao Yuan; B: Zhaoyan Sun, Xuanhe Zhou) and the topics differ (road-network trajectory search 2019; learned-index evaluation 2023).

**Supporting evidence:**
- Name exact match: A author#2, B author#3
- enrichment ror=03cve4549 on both target mentions
- Same OpenAlex-supplied observedOrcid 0000-0002-1398-0621 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- "Guoliang Li" is a common name; name plus affiliation alone stays below the agreed bar

<details><summary>Evidence references</summary>

- A `work` `er-evidence:5f24ee7d565ba840bc542329751f1461d7c96e8f7055f4d4a07b5f3798c268c0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:340`
- A `enrichment` `er-evidence:650c6fadf6ba8c6ea1f35355fb93bfbb8d96d34a618e23199fc7cd85eb284136` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3556`
- B `work` `er-evidence:aafd5178a636b07ef2ec5605510ef497fbd348529a1654b530fbcdc788b964d4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:96`
- B `enrichment` `er-evidence:f61ee5b6695802412e7c80b669b9af976ca0df8c860e33a52acb048bec4b1d77` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1050`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: All four relevant papers are listed on https://dbgroup.cs.tsinghua.edu.cn/ligl/publications.html (Guoliang Li @ Tsinghua).

---

## Task 112 — Researcher

- **pairId:** `resolution-pair:2f1a333949b08fcc86249851864cf444b87130ec734c3320f9c0d7919204469d`
- **evidenceHash:** `6da9824a2c6be1e84c133c31161279679e347f1e5532696f68b19f22626c967a`
- **Question:** do mention A `mention:openalex:W2945486614#12` and B `mention:openalex:W4379382789#8` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2945486614#12 | mention:openalex:W4379382789#8 |
| Name as written | Tim Kraska | Tim Kraska |
| Author position | 12 of 12 | 8 of 10 |
| ORCID on mention | 0009-0003-2414-2759 (OpenAlex-supplied) | 0009-0003-2414-2759 (OpenAlex-supplied) |
| OpenAlex author ID | A5034086130 | A5034086130 |
| Affiliation | ROR 042nb2s44 | ROR 04mv4n011 |
| Work title | ALEX: An Updatable Adaptive Learned Index | Auto-WLM: Machine Learning Enhanced Workload Management in Amazon Redshift |
| Year | 2020 | 2023 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4393915683 |
| DOI | 10.1145/3318464.3389711 | 10.1145/3555041.3589677 |
| Coauthors | Jialin Ding, Umar Farooq Minhas, Jia Yu, Chi Wang, Jaeyoung Do, Yinan Li, Hantian Zhang, Badrish Chandramouli, Johannes Gehrke, Donald Kossmann, David Lomet | Gaurav Saxena, Mohammad Rahman, Naresh Chainani, Chunbin Lin, George Caragea, Fahim Chowdhury, Ryan Marcus, Ippokratis Pandis, Balakrishnan (Murali) Narayanaswamy |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['042nb2s44'] B=['04mv4n011'] shared=none_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Tim Kraska", but the author lists of "ALEX: An Updatable Adaptive Learned Index" (2020) and "Auto-WLM…in Amazon Redshift" (2023) share no coauthors and the RORs differ (042nb2s44 vs 04mv4n011); only the name and a broad ML-for-data-systems area connect them.

**Supporting evidence:**
- Name exact match: A author#12, B author#8
- Both apply machine learning to data systems; same venueId S4393915683
- Same OpenAlex-supplied observedOrcid 0009-0003-2414-2759 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors
- enrichment ror differs

**Limitations / missing information:**
- Affiliation difference could be a move; it is not evidence of distinct people

<details><summary>Evidence references</summary>

- A `work` `er-evidence:201bcc26625ac020fd5dcf968451e79e197dd1a1ca2929845220bf1753ba05c4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:356`
- A `enrichment` `er-evidence:22d84b98e93f3a62b1d3a4cccef0b945d91a8ebdd1085ccf4f97af10dcc912b0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3721`
- B `enrichment` `er-evidence:c26adfaa9f78511a98299481509e32e87b472a03b9b4adbf74fa1b5bb2c134e3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1220`
- B `work` `er-evidence:deae1540ddd2912800b65d6044277fe1fb9be238fd2599da4e7734052c1ea0c5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:111`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Semantic Scholar assigns the same author ID on both papers (api.semanticscholar.org). Auto-WLM DOI is also in ORCID record 0009-0003-2414-2759 (Tim Kraska).

---

## Task 113 — Researcher

- **pairId:** `resolution-pair:ed688b80dd12bf9f1acf47528830bec645c7ecf5385fb7d0eb3d8fcd9c0b8c99`
- **evidenceHash:** `ca35da7439b3182f76ee0dcd3883b54522cf4df89e2fd93aaf5d0af00fd7533a`
- **Question:** do mention A `mention:openalex:W2970148517#5` and B `mention:openalex:W3176153696#5` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2970148517#5 | mention:openalex:W3176153696#5 |
| Name as written | Mohammad Alizadeh | Mohammad Alizadeh |
| Author position | 5 of 8 | 5 of 6 |
| ORCID on mention | 0000-0002-0014-6742 (OpenAlex-supplied) | 0000-0002-0014-6742 (OpenAlex-supplied) |
| OpenAlex author ID | A5101669321 | A5101669321 |
| Affiliation | ROR 042nb2s44 | ROR 042nb2s44 |
| Work title | Neo | Bao: Making Learned Query Optimization Practical |
| Year | 2019 | 2021 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4393915683 |
| DOI | 10.14778/3342263.3342644 | 10.1145/3448016.3452838 |
| Coauthors | Ryan Marcus, Parimarjan Negi, Hongzi Mao, Chi Zhang, Tim Kraska, Olga Papaemmanouil, Nesime Tatbul | Ryan Marcus, Parimarjan Negi, Hongzi Mao, Nesime Tatbul, Tim Kraska |

_helper: shared coauthor normalizedNames = ['hongzi mao', 'nesime tatbul', 'parimarjan negi', 'ryan marcus', 'tim kraska']_
_helper: target-mention ROR A=['042nb2s44'] B=['042nb2s44'] shared=['042nb2s44']_

**AI-proposed label: `same`**

**Note:** Both mentions are author#5 "Mohammad Alizadeh" on learned query optimizer papers ("Neo" 2019; "Bao: Making Learned Query Optimization Practical" 2021) sharing five coauthors (Ryan Marcus, Parimarjan Negi, Hongzi Mao, Nesime Tatbul, Tim Kraska) and ROR 042nb2s44.

**Supporting evidence:**
- Name exact match at author#5
- Five shared coauthors
- enrichment ror=042nb2s44 on both target mentions
- Specific topic continuity: learned query optimization
- Same OpenAlex-supplied observedOrcid 0000-0002-0014-6742 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- All hints OpenAlex-derived

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:15baa398844abe31f1fb5e01807240766b42c4ebdf7053c7221a1ee465ec1f4b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3419`
- A `work` `er-evidence:2b283b52ed624a5a810efe8e2a3994ac293445e62e514ad27377aca0c532fd4a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:326`
- B `enrichment` `er-evidence:146c4936d0e65c65b0d2ad4562f5bf548f79b4e8717d8b741d58eabcf4c7045f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2118`
- B `work` `er-evidence:38586e2eda6cc77e5786807dfee5402039d8ad726401156e8a1de4401610d423` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:193`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 114 — Researcher

- **pairId:** `resolution-pair:1bd022a079d7c9096e13a07ec316360ef40185976382e975d6c6a78dc8260674`
- **evidenceHash:** `0ac15b59341176b48b9d9d45f58b076fe1a2b5c75f8ce180a9ba6cc62295706b`
- **Question:** do mention A `mention:openalex:W3098748542#1` and B `0000-0003-2342-4060` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3098748542#1 | ORCID profile 0000-0003-2342-4060 |
| Name as written | Shaleen Deep | Shaleen Deep (otherNames: —) |
| Author position | 1 of 5 | — |
| ORCID on mention | 0000-0003-2342-4060 (OpenAlex-supplied) | 0000-0003-2342-4060 (ORCID registry) |
| OpenAlex author ID | A5036934715 | — |
| Affiliation | ROR 01y2jtd41 | — |
| Work title | Comprehensive and efficient workload compression | — |
| Year | 2020 | — |
| Venue ID | venue:openalex:S4210226185 | — |
| DOI | 10.14778/3430915.3430931 | — |
| Coauthors | Anja Gruenheid, Paraschos Koutris, Jeffrey Naughton, Stratis Viglas | — |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01y2jtd41'] B=- shared=none_

**AI-proposed label: `uncertain`**

**Note:** B is ORCID profile 0000-0003-2342-4060 with displayName "Shaleen Deep"; A is the OpenAlex mention "Shaleen Deep" whose observedOrcid 0000-0003-2342-4060 is OpenAlex-supplied. The only link beyond the name is that provider hypothesis; the profile supplies no works or affiliations to confirm it.

**Supporting evidence:**
- Name exact match: A author#1 "Shaleen Deep" = B displayName "Shaleen Deep"
- A OpenAlex-supplied observedOrcid equals B orcid 0000-0003-2342-4060 (provider hypothesis)
- B externalIds orcid interpretation VALIDATED_EXTERNAL (validates the profile, not the authorship link)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- No registry-side binding of this ORCID to A's work is supplied (no orcid-activity for the work)
- Profile has no otherNames, works or affiliations for comparison
- Leans same; held at uncertain because OpenAlex ORCIDs are not independent proof

<details><summary>Evidence references</summary>

- A `work` `er-evidence:60a98911c9fdbaecfc646eaff7871b2830dc4a32e1e77132c0364ace4e9b443c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:232`
- A `enrichment` `er-evidence:fca2ed7cfb19c4463845ab00d97fe1bd205f31d6d66fee590f258fd9f5dd5dba` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2524`
- B `orcid-profile` `er-evidence:c2419cc7f38a7a4a20be1e6d4799a25e33dfb88e81899edc61fb7ead946db55b` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-profile/part-r-00000:6`

</details>

**Danny's decision:** ☐ same ☐ different ☑ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: The PVLDB paper is by Shaleen Deep (UW-Madison/Google); ORCID 0000-0003-2342-4060 has that name but does not list this paper. Switched same -> uncertain because no source links both papers to one person.

---

## Task 115 — Researcher

- **pairId:** `resolution-pair:3064f1b0b0d1cd196288894a531a5d853e5e7b6e4935b38a6a9e213b80a87d23`
- **evidenceHash:** `542ee11d12a9f0a51c0b6fa327982ecd220f11760744aee0aa195909fdeb361d`
- **Question:** do mention A `mention:openalex:W3173572290#3` and B `mention:openalex:W4388041078#5` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3173572290#3 | mention:openalex:W4388041078#5 |
| Name as written | Ying Zhang | Yongsu Zhang |
| Author position | 3 of 6 | 5 of 12 |
| ORCID on mention | 0000-0002-2674-1638 (OpenAlex-supplied) | 0009-0004-8527-4082 (OpenAlex-supplied) |
| OpenAlex author ID | A5100386104 | A5015455494 |
| Affiliation | ROR 03f0f6041 | ROR 04m8av638 |
| Work title | T3S: Effective Representation Learning for Trajectory Similarity Computation | Dissecting Overheads of Service Mesh Sidecars |
| Year | 2021 | 2023 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S7407088165 |
| DOI | 10.1109/icde51399.2021.00221 | 10.1145/3620678.3624652 |
| Coauthors | Peilun Yang, Hanchen Wang, Lu Qin, Wenjie Zhang, Xuemin Lin | Xiangfeng Zhu, Guozhen She, Bowen Xue, Yu Zhang, Xuan Kelvin Zou, XiongChun Duan, Peng He, Arvind Krishnamurthy, Matthew Lentz, Danyang Zhuo, Ratul Mahajan |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['03f0f6041'] B=['04m8av638'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#3 "Ying Zhang" and B author#5 "Yongsu Zhang" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Ying" vs "Yongsu"
- No shared coauthors
- enrichment ror differs: 03f0f6041 vs 04m8av638

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:4cca84856786daafb309cc46b816de6672e0b4d38a38afe8f84952db2502c73e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:211`
- A `enrichment` `er-evidence:e8ddbc7c3b98bbc590b7cb8b30ccfe94d06dcc4737197e04b2d7cf00b75b3d09` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2312`
- B `enrichment` `er-evidence:aad8a8dfc738957ef1f953a347ad921245abe33feb7a6ff5616b43c2ac3e3c13` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:689`
- B `work` `er-evidence:cd980f8b96ded17519f51d7f21087d5a6978d49fca80be03485930a4994ef42a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:62`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 116 — Work

- **pairId:** `resolution-pair:3dc8ecce9a0cc5c0096207142f83c8332abd3ad1f79d0aae6c0c4d2763c3181b`
- **evidenceHash:** `2bfeacec5c186b97df6d9df24e562bd5e3153a8739912229feb4fc2d5101fd5f`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2898662556 (article) | OPENALEX W3095227533 (article) |
| Title | Write-optimized and high-performance hashing index scheme for persistent memory | Twine: A Unified Cluster Management System for Shared Infrastructure |
| Year | 2018 | 2020 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4306420647 |
| DOI | 10.5555/3291168.3291202 | — |
| arXiv ID | — | — |
| Pages | 461-476 | 787-803 |
| Authors | (3) Pengfei Zuo, Yu Hua, Jie Wu | (20) Chunqiang Tang, Kenny Yu, Kaushik Veeraraghavan, Jonathan Kaldor, Scott Michelson, Thawan Kooburat, Aravind Anbudurai, Matthew Clark, Kabir Gogia, Long Cheng, Ben Christensen, Alex Gartrell, Maxim Khutornenko, Sachin Kulkarni, Marcin Pawłowski … (+5 more) |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.5555/3291168.3291202, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.5555/3291168.3291202, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.5555/3291168.3291202'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Write-optimized and high-performance hashing index scheme for persistent memory" (DOI 10.5555/3291168.3291202, OSDI 2018) and B "Twine: A Unified Cluster Management System for Shared Infrastructure" (no DOI, OSDI 2020) have different titles, years and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2018 vs 2020
- work.authors disjoint (3 vs 20)

**Conflicting evidence:**
- Same venueId S4306420647

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:39d95c32424ffff7202a4ce6c28eb291930e2e03212d8fa4293ecb6df5e82e26` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:383`
- B `work` `er-evidence:89c723a4492d89040048728e01108ac1620308c9f1ddb4728304675c3e7d5bb0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:249`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 117 — Researcher

- **pairId:** `resolution-pair:a4d50deced44430b21c034c934755ed681f86434a01a76502ca992dc6e114d50`
- **evidenceHash:** `3701c724e65a10f24b41fd4f85d5d8b40ce75ac642cf703d5610680d2b71376b`
- **Question:** do mention A `mention:openalex:W4286986033#3` and B `mention:openalex:W4404386171#10` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4286986033#3 | mention:openalex:W4404386171#10 |
| Name as written | Yujing Wang | Yida Wang |
| Author position | 3 of 6 | 10 of 10 |
| ORCID on mention | 0000-0002-7940-5216 (OpenAlex-supplied) | 0000-0001-8165-840X (OpenAlex-supplied) |
| OpenAlex author ID | A5100776576 | A5101638214 |
| Affiliation | ROR 0300m5276 | ROR 04mv4n011 |
| Work title | Attentive Knowledge-aware Graph Convolutional Networks with Collaborative Guidance for Personalized Recommendation | Distributed Training of Large Language Models on AWS Trainium |
| Year | 2022 | 2024 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S7407088165 |
| DOI | 10.1109/icde53745.2022.00027 | 10.1145/3698038.3698535 |
| Coauthors | Yankai Chen, Yaming Yang, Jing Bai, Xiangchen Song, Irwin King | Xinwei Fu, Zhen Zhang, Haozheng Fan, Guangtai Huang, Mohammad El-Shabani, Randy Huang, Rahul Solanki, Fei Wu, Ron Diamant |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['0300m5276'] B=['04mv4n011'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#3 "Yujing Wang" and B author#10 "Yida Wang" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Yujing" vs "Yida"
- No shared coauthors
- enrichment ror differs: 0300m5276 vs 04mv4n011

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:7a36ca63ae468ec3fa61e9c2a3122798fe7bf736ed706f90a3d07b467750cee8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:140`
- A `enrichment` `er-evidence:87aa399a14c76e397897fccf295580758189cebb0a2252f9e3c8b5edabe55f93` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1498`
- B `work` `er-evidence:1996e8128f2622a44821348005ee02a2bb82f2f46c814dc4b521112fbec5df1e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:3`
- B `enrichment` `er-evidence:66f89ce877f12c02daf8ea24bbc43e608716ab1cc913a6ad1d46cd5884d73f3d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:56`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 118 — Researcher

- **pairId:** `resolution-pair:a06827849558b53efba5e5d4516125a33d950faafc04b83bc16eb1f12595226d`
- **evidenceHash:** `272db20f4be7553e58f570b76e9520d351a9b4fc3724819dbd5fd9053d1594a8`
- **Question:** do mention A `mention:openalex:W3173850788#1` and B `mention:openalex:W4381621971#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3173850788#1 | mention:openalex:W4381621971#3 |
| Name as written | Guoliang Li | Guoliang Li |
| Author position | 1 of 3 | 3 of 3 |
| ORCID on mention | 0000-0002-1398-0621 (OpenAlex-supplied) | 0000-0002-1398-0621 (OpenAlex-supplied) |
| OpenAlex author ID | A5100451576 | A5100451576 |
| Affiliation | ROR 03cve4549 | ROR 03cve4549 |
| Work title | AI Meets Database: AI4DB and DB4AI | Learned Index: A Comprehensive Experimental Evaluation |
| Year | 2021 | 2023 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210226185 |
| DOI | 10.1145/3448016.3457542 | 10.14778/3594512.3594528 |
| Coauthors | Xuanhe Zhou, Lei Cao | Zhaoyan Sun, Xuanhe Zhou |

_helper: shared coauthor normalizedNames = ['xuanhe zhou']_
_helper: target-mention ROR A=['03cve4549'] B=['03cve4549'] shared=['03cve4549']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Guoliang Li" with shared coauthor Xuanhe Zhou (A#2, B#2), ROR 03cve4549, and AI-for-databases topics ("AI Meets Database: AI4DB and DB4AI" 2021; "Learned Index: A Comprehensive Experimental Evaluation" 2023).

**Supporting evidence:**
- Name exact match: A author#1, B author#3
- Shared coauthor in payload: Xuanhe Zhou
- enrichment ror=03cve4549 on both target mentions
- Topic continuity: machine learning for database systems
- Same OpenAlex-supplied observedOrcid 0000-0002-1398-0621 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- "Guoliang Li" is a common name; coauthor, affiliation and topic are correlated

<details><summary>Evidence references</summary>

- A `work` `er-evidence:91cf192c316bc6019c3bb643cb9a45501a74471e61a9d377739988135b33a8d8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:208`
- A `enrichment` `er-evidence:d48ffd2a5841faf15ed6d4bd12f7392957aa7e89c0193fa118cde925c9a6f708` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2266`
- B `work` `er-evidence:aafd5178a636b07ef2ec5605510ef497fbd348529a1654b530fbcdc788b964d4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:96`
- B `enrichment` `er-evidence:f61ee5b6695802412e7c80b669b9af976ca0df8c860e33a52acb048bec4b1d77` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1050`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 119 — Researcher

- **pairId:** `resolution-pair:f78e39051671affd66bf38e06423a5da7a5880c004c123396b44c1119a2b8925`
- **evidenceHash:** `aa908b00107838979a3dc5bcd961be7aabbf3f363b807f651c36740c297ed69d`
- **Question:** do mention A `mention:openalex:W2970148517#4` and B `mention:openalex:W4289533977#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2970148517#4 | mention:openalex:W4289533977#3 |
| Name as written | Chi Zhang | Ce Zhang |
| Author position | 4 of 8 | 3 of 6 |
| ORCID on mention | 0000-0003-1911-3446 (OpenAlex-supplied) | 0000-0001-9947-9960 (OpenAlex-supplied) |
| OpenAlex author ID | A5100458232 | A5100383721 |
| Affiliation | ROR 05abbep66 | ROR 0145fw131 |
| Work title | Neo | vChain+: Optimizing Verifiable Blockchain Boolean Range Queries |
| Year | 2019 | 2022 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210210321 |
| DOI | 10.14778/3342263.3342644 | 10.1109/icde53745.2022.00190 |
| Coauthors | Ryan Marcus, Parimarjan Negi, Hongzi Mao, Mohammad Alizadeh, Tim Kraska, Olga Papaemmanouil, Nesime Tatbul | Haixin Wang, Cheng Xu, Jianliang Xu, Zhe Peng, Jian Pei |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['05abbep66'] B=['0145fw131'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#4 "Chi Zhang" and B author#3 "Ce Zhang" differ in given name (Chi vs Ce); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Chi" vs "Ce"
- No shared coauthors
- enrichment ror differs: 05abbep66 vs 0145fw131

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:2b283b52ed624a5a810efe8e2a3994ac293445e62e514ad27377aca0c532fd4a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:326`
- A `enrichment` `er-evidence:66fcfa800fe09e86fdf1201fc171bf378215634295a3da0e7a89333423bbc9ef` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3424`
- B `enrichment` `er-evidence:5ebd44dd7d49ad76604f15f6628d94da4b2c4b2df1d7721e1b4aac5b112ac11e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1422`
- B `work` `er-evidence:b6787ca62ab1597b17753759c6552915679ef79e7f125146f635154ec72f1c0a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:132`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 120 — Researcher

- **pairId:** `resolution-pair:4f98430e79a633f46e604b1543a8bccb0753b4e44d507c3bbdb24645d79f09c8`
- **evidenceHash:** `ca3e5dc3314be557fa369294548aff269e5edc7d8c64b2fa5176a4dfc5c7a64b`
- **Question:** do mention A `mention:openalex:W2948051378#8` and B `mention:openalex:W4404386368#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2948051378#8 | mention:openalex:W4404386368#4 |
| Name as written | Sheng Wang | Shaohua Wang |
| Author position | 8 of 10 | 4 of 7 |
| ORCID on mention | 0000-0002-1473-5206 (OpenAlex-supplied) | 0009-0008-0040-0430 (OpenAlex-supplied) |
| OpenAlex author ID | A5100371254 | — |
| Affiliation | — | ROR 00p991c53 |
| Work title | X-Engine | RomeFS: A CXL-SSD Aware File System Exploiting Synergy of Memory-Block Dual Paths |
| Year | 2019 | 2024 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S7407088165 |
| DOI | 10.1145/3299869.3314041 | 10.1145/3698038.3698539 |
| Coauthors | Gui Huang, Xuntao Cheng, Jianying Wang, Yujie Wang, Dengcheng He, Tieying Zhang, Feifei Li, Wei Cao, Qiang Li | Yekang Zhan, Haichuan Hu, Xiangrui Yang, Qiang Cao, Hong Jiang, Jie Yao |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=- B=['00p991c53'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#8 "Sheng Wang" and B author#4 "Shaohua Wang" have different given names (Sheng vs Shaohua); no coauthor overlap.

**Supporting evidence:**
- nameText given names differ: "Sheng" vs "Shaohua"
- No shared coauthors
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no affiliation evidence

<details><summary>Evidence references</summary>

- A `work` `er-evidence:19d0e96eec0f2d8187bc0380a8ee39af1c0570bb3860affa17beff70425a6bba` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:355`
- B `enrichment` `er-evidence:0ee5f3de08fa8cf522bde0d02de22a2fe40027e978a5fb46a2bebe38815c876a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:44`
- B `work` `er-evidence:d421b59cf2d89bbbae634c67cf9c1f785828faf6e5c68fd29e219506f40b85d9` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:2`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---
