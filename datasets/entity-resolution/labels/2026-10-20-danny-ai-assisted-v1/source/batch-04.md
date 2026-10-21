# ScholarChain AI review drafts — batch 04 (tasks 61–80)

> **Status: AI_SUGGESTIONS_PENDING_HUMAN_REVIEW.** These are AI-generated suggestions from a session-reported `claude-opus-5-5` model (not independently verified). They are not human reviews or gold labels. Record your own decision in each task's decision box; an empty box means not reviewed.

Queue: `review-queue:05c5817f62a70d378829be361b9c9169fc9af18448f7c83c245f1d65bbca6175`  
Work tasks: 6 · Researcher tasks: 14

Rows marked `>> … <<` in the raw data and the 'Name as written' row identify the mention being compared. OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider hypotheses. Lines in _italics_ starting with 'helper:' are exact-string comparisons computed by a script to help reading; they are not judgments.

---
## Task 61 — Work

- **pairId:** `resolution-pair:2eb757e0ab235c4d53ae1a4f86e672c343f3e0e92de5d14d9e250eef3f04e759`
- **evidenceHash:** `341527a71e2584164adc34454e1c7370695c7145b7b8c09e42f32110db53da69`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2795302121 (conference-paper) | OPENALEX W3174906424 (conference-paper) |
| Title | Seeping Semantics: Linking Datasets Using Word Embeddings for Data Discovery | Synthesizing Natural Language to Visualization (NL2VIS) Benchmarks from NL2SQL Benchmarks |
| Year | 2018 | 2021 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4393915683 |
| DOI | 10.1109/icde.2018.00093 | 10.1145/3448016.3457261 |
| arXiv ID | — | — |
| Pages | 989-1000 | 1235-1247 |
| Authors | (9) Raul Castro Fernandez, Essam Mansour, Abdulhakim A. Qahtan, Ahmed Elmagarmid, Ihab Ilyas, Samuel Madden, Mourad Ouzzani, Michael Stonebraker, Nan Tang | (6) Yuyu Luo, Nan Tang, Guoliang Li, Chengliang Chai, Wenbo Li, Xuedi Qin |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde.2018.00093, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde.2018.00093, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3448016.3457261, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3448016.3457261, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1109/icde.2018.00093'] B=['10.1145/3448016.3457261'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Seeping Semantics: Linking Datasets Using Word Embeddings for Data Discovery" (10.1109/icde.2018.00093, 2018) and B "Synthesizing Natural Language to Visualization (NL2VIS) Benchmarks…" (10.1145/3448016.3457261, 2021) have distinct DOIs and different titles; only Nan Tang is shared.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2018 vs 2021

**Conflicting evidence:**
- Shared author Nan Tang

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:5e81b64cde3a7f21336672d5dfd0a5adc5e281da10b1b1612ed522d53ff41da3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:426`
- B `work` `er-evidence:369ad40fc4315dccc3ed1752e88a95e87167a9adf0f917713a133a2d31518e0a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:201`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 62 — Work

- **pairId:** `resolution-pair:3269fb7a7166b5d232fc5967afe8f476d608251a0aae635f44f327f2d5f490bb`
- **evidenceHash:** `8a9d5c268d280a062ff7b2ebfb1778a2a8068bbdfce5ee0dea344dfa34a4f7ee`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3174969457 (conference-paper) | OPENALEX W4283314525 (article) |
| Title | ResTune: Resource Oriented Tuning Boosted by Meta-Learning for Cloud Databases | ByteGNN |
| Year | 2021 | 2022 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210226185 |
| DOI | 10.1145/3448016.3457291 | 10.14778/3514061.3514069 |
| arXiv ID | — | — |
| Pages | 2102-2114 | 1228-1242 |
| Authors | (8) Xinyi Zhang, Hong Wu, Zhuo Chang, Shuowei Jin, Jian Tan, Feifei Li, Tieying Zhang, Bin Cui | (9) Chenguang Zheng, Hongzhi Chen, Yuxuan Cheng, Zhezheng Song, Yifan Wu, Changji Li, James Cheng, Hao Yang, Shuai Zhang |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3448016.3457291, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3448016.3457291, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.14778/3514061.3514069, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3514061.3514069, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3448016.3457291'] B=['10.14778/3514061.3514069'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "ResTune: Resource Oriented Tuning Boosted by Meta-Learning for Cloud Databases" (10.1145/3448016.3457291, 2021) and B "ByteGNN" (10.14778/3514061.3514069, 2022) have distinct DOIs, different titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2021 vs 2022
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:b91380e05fdc6fdc92131fb044a70a6687f64c66ee4f04e844c65caa439b4a8d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:200`
- B `work` `er-evidence:54074ec6ae0f5c5b1986edca2dda6f07d8264fcd10bfdf4cdb2b74d3d4db6644` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:147`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 63 — Researcher

- **pairId:** `resolution-pair:d228a844eeb02e00e4be7b4148c759f4a121cc3044f31286a0267225519a23f0`
- **evidenceHash:** `3f95274e627c8e01ec6a719bac854e98a0bad7fdf9a014c55c5efee122cab21e`
- **Question:** do mention A `mention:openalex:W2982913301#3` and B `mention:openalex:W4224911291#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2982913301#3 | mention:openalex:W4224911291#1 |
| Name as written | Zhongwei Li | Zhonghang Li |
| Author position | 3 of 7 | 1 of 5 |
| ORCID on mention | 0000-0003-4651-4763 (OpenAlex-supplied) | 0000-0002-3977-1334 (OpenAlex-supplied) |
| OpenAlex author ID | A5100726890 | A5023084303 |
| Affiliation | ROR 019kgqr73 | ROR 0530pts50 |
| Work title | Pigeon | Spatial-Temporal Hypergraph Self-Supervised Learning for Crime Prediction |
| Year | 2019 | 2022 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210210321 |
| DOI | 10.1145/3357223.3362728 | 10.1109/icde53745.2022.00269 |
| Coauthors | Zhijun Wang, Huiyang Li, Xiaocui Sun, Jia Rao, Hao Che, Hong Jiang | Chao Huang, Lianghao Xia, Yong Xu, Jian Pei |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['019kgqr73'] B=['0530pts50'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#3 "Zhongwei Li" and B author#1 "Zhonghang Li" differ in given name (Zhongwei vs Zhonghang); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Zhongwei" vs "Zhonghang"
- No shared coauthors
- enrichment ror differs: 019kgqr73 vs 0530pts50
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:4f69215ba97477c10203017f8bd30011f895f5660246e512906b6768b3e47f9a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3339`
- A `work` `er-evidence:b27807d55d3097d0bd34a0b9e826f7837f36832656f44266837d268a8743ecd7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:317`
- B `work` `er-evidence:4ea00802f1d863f423c62ce5763db4824577445accb340fa42a98ce073672927` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:163`
- B `enrichment` `er-evidence:77d190eed142b7d262ddc0d898b7788abef88a7acc7ea525c39660568cef0fe8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1759`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 64 — Researcher

- **pairId:** `resolution-pair:e00cfa278adcebec68e4ff4ac1dde2dee8fec80ae28f2da6a77c658f197dec7f`
- **evidenceHash:** `ab4f1056ba75f0e0f4c64b2d51a7272dc095e2a5e7d24ed09c726bed6f9f3bbe`
- **Question:** do mention A `mention:openalex:W3176085787#5` and B `mention:openalex:W4312703862#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3176085787#5 | mention:openalex:W4312703862#2 |
| Name as written | Zongquan Zhang | Zhao Zhang |
| Author position | 5 of 7 | 2 of 7 |
| ORCID on mention | 0009-0009-4216-0110 (OpenAlex-supplied) | 0000-0001-9165-1439 (OpenAlex-supplied) |
| OpenAlex author ID | A5025504557 | A5100422993 |
| Affiliation | ROR 00cmhce21 | ROR 034t30j35 |
| Work title | DAEMON: Unsupervised Anomaly Detection and Interpretation for Multivariate Time Series | Decoupled dynamic spatial-temporal graph neural network for traffic forecasting |
| Year | 2021 | 2022 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210226185 |
| DOI | 10.1109/icde51399.2021.00228 | 10.14778/3551793.3551827 |
| Coauthors | Xuanhao Chen, Liwei Deng, Feiteng Huang, Chengwei Zhang, Yan Zhao, Kai Zheng | Zezhi Shao, Wei Wei, Fei Wang, Yongjun Xu, Xin Cao, Christian S. Jensen |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00cmhce21'] B=['034t30j35'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#5 "Zongquan Zhang" and B author#2 "Zhao Zhang" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Zongquan" vs "Zhao"
- No shared coauthors
- enrichment ror differs: 00cmhce21 vs 034t30j35
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:23fd3d6764b4b4fc93dd4b70cfc51719574a7d51cf98b5f40e88a13a4c45dbd5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:195`
- A `enrichment` `er-evidence:a6050f0d97f64b70f3829b5b700b74e60fb1cdaa702d2840d20cecd0d264e1a9` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2141`
- B `work` `er-evidence:9dc915c7fe2133de2177bbbad0681e879bd2ed188cedafca976b265cfc5049b4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:122`
- B `enrichment` `er-evidence:fcc00dfbce7d036e7153045fb925c2c4ccbe5719d51907bc738a6d644eb10ed1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1337`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 65 — Work

- **pairId:** `resolution-pair:862944ae569776d39c37df923fc4203cb0bbf682ad88c7901a1ab10408675b95`
- **evidenceHash:** `23f93898b71ccc74abff0d2630671a84e2dcfce7396c2f058cb6544a480eed52`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W4224911291 (conference-paper) | OPENALEX W4387321071 (conference-paper) |
| Title | Spatial-Temporal Hypergraph Self-Supervised Learning for Crime Prediction | SPFresh: Incremental In-Place Update for Billion-Scale Vector Search |
| Year | 2022 | 2023 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4306420989 |
| DOI | 10.1109/icde53745.2022.00269 | 10.1145/3600006.3613166 |
| arXiv ID | — | — |
| Pages | 2984-2996 | 545-561 |
| Authors | (5) Zhonghang Li, Chao Huang, Lianghao Xia, Yong Xu, Jian Pei | (12) Yuming Xu, Hengyu Liang, Jin Li, Shuotao Xu, Qi Chen, Qianxi Zhang, Cheng Li, Ziyue Yang, Fan Yang, Yuqing Yang, Peng Cheng, Mao Yang |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde53745.2022.00269, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde53745.2022.00269, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3600006.3613166, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3600006.3613166, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1109/icde53745.2022.00269'] B=['10.1145/3600006.3613166'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Spatial-Temporal Hypergraph Self-Supervised Learning for Crime Prediction" (10.1109/icde53745.2022.00269, 2022) and B "SPFresh: Incremental In-Place Update for Billion-Scale Vector Search" (10.1145/3600006.3613166, 2023) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2022 vs 2023
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:4ea00802f1d863f423c62ce5763db4824577445accb340fa42a98ce073672927` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:163`
- B `work` `er-evidence:0165c810044156b387afec53613b29410c2ea86c6e87c1973a6fdebde5cab511` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:76`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 66 — Researcher

- **pairId:** `resolution-pair:f793c19df1b55f29f150e5ed0a38967e3fc11ea9f27fb500becf8becc4b0feec`
- **evidenceHash:** `cefff5f1f3ca9e46a8668ee36e5d1224725d415f8dee88d8d329fb4fa1894b53`
- **Question:** do mention A `mention:openalex:W2939050176#2` and B `mention:openalex:W2999832078#12` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2939050176#2 | mention:openalex:W2999832078#12 |
| Name as written | Xiaokui Xiao | Xiaokui Xiao |
| Author position | 2 of 6 | 12 of 15 |
| ORCID on mention | 0000-0003-0914-4580 (OpenAlex-supplied) | 0000-0003-0914-4580 (OpenAlex-supplied) |
| OpenAlex author ID | A5010903591 | A5010903591 |
| Affiliation | ROR 01tgyzw49 | ROR 01tgyzw49 |
| Work title | Efficient Estimation of Heat Kernel PageRank for Local Clustering | The Disruptions of 5G on Data-Driven Technologies and Applications |
| Year | 2019 | 2020 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S30698027 |
| DOI | 10.1145/3299869.3319886 | 10.1109/tkde.2020.2967670 |
| Coauthors | Renchi Yang, Zhewei Wei, Sourav S. Bhowmick, Jun Zhao, Rong-Hua Li | Dumitrel Loghin, Shaofeng Cai, Gang Chen, Tien Tuan Anh Dinh, Feiyi Fan, Qian Lin, Janice Ng, Beng Chin Ooi, Xutao Sun, Quang-Trung Ta, Wei Wang, Yang Yang, Meihui Zhang, Zhonghua Zhang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01tgyzw49'] B=['01tgyzw49'] shared=['01tgyzw49']_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Xiaokui Xiao" with the same ROR 01tgyzw49, but there is no shared coauthor and the topics are not continuous (heat-kernel PageRank estimation, SIGMOD 2019; 5G and data-driven technologies, TKDE 2020).

**Supporting evidence:**
- Name exact match: A author#2, B author#12
- enrichment ror=01tgyzw49 on both target mentions
- Same OpenAlex-supplied observedOrcid 0000-0003-0914-4580 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- Only name plus affiliation corroborate; B is a 15-author survey with limited topical signal

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:7263a6e960ca7f975f839d991fca07e02515ba99b261b0a20f9c2828fc594426` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3750`
- A `work` `er-evidence:e0918f64c8eeaf5c71ce8f3e79aac8b3861a06efbe4aa63d02e5c466ae492fa9` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:358`
- B `enrichment` `er-evidence:389c0202b04f10e278ce1bdd0df327d5dd95520fe53766f384aa4db0c6240bad` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3208`
- B `work` `er-evidence:6c0b33388e2251485298030b2bf5668a67f68cba6d263bf25331c4c56a0c6c7b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:302`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Both DOIs are listed in ORCID record 0000-0003-0914-4580 (Xiaokui Xiao, pub.orcid.org) and Semantic Scholar assigns the same author ID on both papers (api.semanticscholar.org).

---

## Task 67 — Researcher

- **pairId:** `resolution-pair:59e49f68f7e1782607d0ebb9685431bdab998471dd87e7e9ad9338119556d6e4`
- **evidenceHash:** `93059b31fc47cc8383a8d5c30f774f06025345488bfec82e973e3bf8feb353ce`
- **Question:** do mention A `mention:openalex:W2970773487#6` and B `mention:openalex:W3173799718#8` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2970773487#6 | mention:openalex:W3173799718#8 |
| Name as written | Bo Li | Bei Li |
| Author position | 6 of 9 | 8 of 17 |
| ORCID on mention | — | 0009-0002-8102-978X (OpenAlex-supplied) |
| OpenAlex author ID | — | A5100356464 |
| Affiliation | ROR 047426m28 | ROR 00njsd438 |
| Work title | Efficient task-specific data valuation for nearest neighbor algorithms | PG-Keys: Keys for Property Graphs |
| Year | 2019 | 2021 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4393915683 |
| DOI | 10.14778/3342263.3342637 | 10.1145/3448016.3457561 |
| Coauthors | Ruoxi Jia, David Dao, Boxin Wang, Frances Ann Hubis, Nezihe Merve Gurel, Ce Zhang, Costas Spanos, Dawn Song | Renzo Angles, Angela Bonifati, Stefania Dumbrava, George Fletcher, Keith W. Hare, Jan Hidders, Victor E. Lee, Leonid Libkin, Wim Martens, Filip Murlak, Josh Perryman, Ognjen Savković, Michael Schmidt, Juan Sequeda, Slawek Staworko, Dominik Tomaszuk |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['047426m28'] B=['00njsd438'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#6 "Bo Li" and B author#8 "Bei Li" differ in given name (Bo vs Bei); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Bo" vs "Bei"
- No shared coauthors
- enrichment ror differs: 047426m28 vs 00njsd438

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A mention has no ORCID

<details><summary>Evidence references</summary>

- A `work` `er-evidence:03ef2208aa7734a65889ae31546d72edf8c84050607e61b7e9aa7486493c3ba4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:325`
- A `enrichment` `er-evidence:d8b48e20bd0581b75d1b424d59118a2259c3dc13bfe95323da032206070c8db8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3406`
- B `work` `er-evidence:84472d1ab10050dd478f739686fce4a6ea4c336ab37ab638b9602628b953f9ea` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:210`
- B `enrichment` `er-evidence:b56a84108cb02b603ab0ca22ba53b14634d48a0b17e65d964eeaf1f1336be2a7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2299`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 68 — Researcher

- **pairId:** `resolution-pair:45b9c7b2022d4e43fc3774c74e7dc27fd9431b66814166d253fae47011230823`
- **evidenceHash:** `04dbbc73960b1fe5024c7d066944035059db04ba0a0a6c2966614f39846ddf46`
- **Question:** do mention A `mention:openalex:W4379382789#4` and B `mention:openalex:W4388040958#18` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4379382789#4 | mention:openalex:W4388040958#18 |
| Name as written | Chunbin Lin | Caixue Lin |
| Author position | 4 of 10 | 18 of 20 |
| ORCID on mention | 0000-0002-7068-9929 (OpenAlex-supplied) | 0009-0003-0570-6352 (OpenAlex-supplied) |
| OpenAlex author ID | A5036384670 | A5077661988 |
| Affiliation | ROR 04mv4n011 | ROR 04m8av638 |
| Work title | Auto-WLM: Machine Learning Enhanced Workload Management in Amazon Redshift | Gödel |
| Year | 2023 | 2023 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S7407088165 |
| DOI | 10.1145/3555041.3589677 | 10.1145/3620678.3624663 |
| Coauthors | Gaurav Saxena, Mohammad Rahman, Naresh Chainani, George Caragea, Fahim Chowdhury, Ryan Marcus, Tim Kraska, Ippokratis Pandis, Balakrishnan (Murali) Narayanaswamy | Wu Xiang, Yakun Li, Yuquan Ren, Fan Jiang, Chaohui Xin, Varun Gupta, Chao Xiang, Xinyi Song, Meng Liu, Bing Li, Kaiyang Shao, Chen Xu, Wei Shao, Yuqi Fu, Wilson Wang, Cong Xu, Wei Xu, Rui Shi, Yuming Liang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['04mv4n011'] B=['04m8av638'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#4 "Chunbin Lin" and B author#18 "Caixue Lin" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Chunbin" vs "Caixue"
- No shared coauthors
- enrichment ror differs: 04mv4n011 vs 04m8av638
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- Same year 2023

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:deae1540ddd2912800b65d6044277fe1fb9be238fd2599da4e7734052c1ea0c5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:111`
- A `enrichment` `er-evidence:f7c8815ea7d677a7a1c448886c17660a547bbd57bbb16b1102b8b26b5fdae7f8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1216`
- B `enrichment` `er-evidence:79d84331c732530b424a20c17f81fffd2ead84b3bf274a089767a86d5238bcaa` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:729`
- B `work` `er-evidence:96ec67c714f494ce9cbf96eb5072486ef317424448848854bf8b62301ca3f703` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:65`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 69 — Researcher

- **pairId:** `resolution-pair:113b8ab9f77a8bbeaab3172abd06e210f364f95bd08ff3845a302124720a86d0`
- **evidenceHash:** `41b2fc9ca1147e80f5c82483131f3e6f54bfac0d737b7c1726db2ac902faf1f6`
- **Question:** do mention A `mention:openalex:W2955344300#6` and B `mention:openalex:W4385270450#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2955344300#6 | mention:openalex:W4385270450#6 |
| Name as written | Meihui Zhang | Ming Zhang |
| Author position | 6 of 6 | 6 of 6 |
| ORCID on mention | 0000-0002-0752-9877 (OpenAlex-supplied) | 0000-0002-9809-3430 (OpenAlex-supplied) |
| OpenAlex author ID | A5032263010 | A5100642537 |
| Affiliation | ROR 01skt4w74 | ROR 02v51f717 |
| Work title | Fine-grained, secure and efficient data provenance on blockchain systems | Dynamic Hypergraph Structure Learning for Traffic Flow Forecasting |
| Year | 2019 | 2023 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210210321 |
| DOI | 10.14778/3329772.3329775 | 10.1109/icde55515.2023.00178 |
| Coauthors | Pingcheng Ruan, Gang Chen, Tien Tuan Anh Dinh, Qian Lin, Beng Chin Ooi | Yusheng Zhao, Xiao Luo, Wei Ju, Chong Chen, Xian-Sheng Hua |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01skt4w74'] B=['02v51f717'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#6 "Meihui Zhang" and B author#6 "Ming Zhang" differ in given name (Meihui vs Ming); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Meihui" vs "Ming"
- No shared coauthors
- enrichment ror differs: 01skt4w74 vs 02v51f717
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:55acdc7f2784f1ffb8133d638df8661e6b5da4cedec9d82b94645d46770461d4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3489`
- A `work` `er-evidence:8c7bab3df25f10a8ada2650fb0d8a24d2377edcf5a844e2bb557057941b07e42` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:333`
- B `work` `er-evidence:421c32f725bdbe087da0648beb612df38eac7e3eb1db71cd58c2f5f5309763b4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:91`
- B `enrichment` `er-evidence:9abdb211e94b37cdadd5b0afa4b7c43c680b48fef778419d1b754629bea98ec1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:995`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 70 — Work

- **pairId:** `resolution-pair:960355d1d965cbc55253d53cd87366e4c94f569bc40da3209bce8659b1e85fdf`
- **evidenceHash:** `dd04a40077f7a2fa6e47799cca404b2414a9151d4eda1b42eedbac2179bbb018`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2949762319 (conference-paper) | OPENALEX W3096956001 (article) |
| Title | Presto: SQL on Everything | AntMan: Dynamic Scaling on GPU Clusters for Deep Learning. |
| Year | 2019 | 2020 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4306420647 |
| DOI | 10.1109/icde.2019.00196 | — |
| arXiv ID | — | — |
| Pages | 1802-1813 | 533-548 |
| Authors | (11) Raghav Sethi, Martin Traverso, Dain Sundstrom, David Phillips, Wenlei Xie, Yutian Sun, Nezih Yegitbasi, Haozhun Jin, Eric Hwang, Nileema Shingte, Christopher Berner | (9) Wencong Xiao, Shiru Ren, Yong Li, Yang Zhang, Pengyang Hou, Zhi Li, Yihui Feng, Wei Lin, Yangqing Jia |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde.2019.00196, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde.2019.00196, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1109/icde.2019.00196'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Presto: SQL on Everything" (DOI 10.1109/icde.2019.00196, 2019) and B "AntMan: Dynamic Scaling on GPU Clusters for Deep Learning." (no DOI, OSDI 2020 PDF) have different titles, years, venues and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2019 vs 2020
- venueId S4210210321 vs S4306420647
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:bdfb3c3f469555ad2edf7329633a7ec65e79aaf3bf0d1904854cc60bde19df27` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:342`
- B `work` `er-evidence:7e6eb194eea3dec822758e4861d17383b1296911fe7ca5a337f3a4a0b91673d1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:240`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 71 — Researcher

- **pairId:** `resolution-pair:41b38e0ab33d41452a0ff43bb059095d90d2315a485c46f2cec6e0e839c5777f`
- **evidenceHash:** `6b256ae410b9ce7a2e010bd1231306c53db8cb5941ab48375d7084f582fe7480`
- **Question:** do mention A `mention:openalex:W2952395191#3` and B `mention:openalex:W4400909566#8` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2952395191#3 | mention:openalex:W4400909566#8 |
| Name as written | Kunpeng Zhang | Kai Zhang |
| Author position | 3 of 6 | 8 of 10 |
| ORCID on mention | 0000-0002-1474-3169 (OpenAlex-supplied) | 0000-0003-4426-1897 (OpenAlex-supplied) |
| OpenAlex author ID | A5014223717 | A5077800960 |
| Affiliation | ROR 047s2c258 | ROR 013q1eq08 |
| Work title | Information Diffusion Prediction via Recurrent Cascades Convolution | PURPLE: Making a Large Language Model a Better SQL Writer |
| Year | 2019 | 2024 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210210321 |
| DOI | 10.1109/icde.2019.00074 | 10.1109/icde60146.2024.00009 |
| Coauthors | Xueqin Chen, Fan Zhou, Goce Trajcevski, Ting Zhong, Fengli Zhang | Tonghui Ren, Yuankai Fan, Zhenying He, Ren Huang, Jiaqi Dai, Can Huang, Yinan Jing, Yifan Yang, X. Sean Wang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['047s2c258'] B=['013q1eq08'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#3 "Kunpeng Zhang" and B author#8 "Kai Zhang" differ in given name (Kunpeng vs Kai); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Kunpeng" vs "Kai"
- No shared coauthors
- enrichment ror differs: 047s2c258 vs 013q1eq08
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:877a845200acf423a24946e94244840a5e04bccfdd6a075a2b548e1277d7dd59` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:337`
- A `enrichment` `er-evidence:8ef314d8c513521bad77a282d2e910c1091aa1146730fc32aa355d6c39ec62d7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3532`
- B `enrichment` `er-evidence:89f98a839c2f4aa55ca24930ce5fe033cbbd46ad38e107b1aa461db66c6a7063` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:350`
- B `work` `er-evidence:d2083a16899f4790ccf48fcdf6142aa02d682b4358f21e292799673f80fb8c6e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:31`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 72 — Researcher

- **pairId:** `resolution-pair:77596c9cef6afceb898b6fe43455a62fe76f0192698137556da210d9a36dd02c`
- **evidenceHash:** `7af0caed368d6330a42faf6bad3c376628e6cf6e9256170fed433bf33bb7f3cd`
- **Question:** do mention A `mention:openalex:W2899225507#4` and B `mention:openalex:W4398234451#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2899225507#4 | mention:openalex:W4398234451#3 |
| Name as written | Haibo Chen | Hao Chen |
| Author position | 4 of 4 | 3 of 8 |
| ORCID on mention | 0000-0002-9720-0361 (OpenAlex-supplied) | 0000-0001-8249-7046 (OpenAlex-supplied) |
| OpenAlex author ID | A5100406215 | A5100353492 |
| Affiliation | ROR 0220qvk04 | ROR 00k642b80 |
| Work title | Deconstructing RDMA-enabled distributed transactions: hybrid is better | PolarDB-MP: A Multi-Primary Cloud-Native Database via Disaggregated Shared Memory |
| Year | 2018 | 2024 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4393915683 |
| DOI | 10.5555/3291168.3291186 | 10.1145/3626246.3653377 |
| Coauthors | Xingda Wei, Zhiyuan Dong, Rong Chen | Xinjun Yang, Yingqiang Zhang, Feifei Li, Bo Wang, Jing Fang, Chuan Sun, Yuhui Wang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['0220qvk04'] B=['00k642b80'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#4 "Haibo Chen" and B author#3 "Hao Chen" differ in given name (Haibo vs Hao); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Haibo" vs "Hao"
- No shared coauthors
- enrichment ror differs: 0220qvk04 vs 00k642b80
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:27973a9f97229a430617c1d42afdb0b6fc288659357c82bf64e25003bb176626` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:376`
- A `enrichment` `er-evidence:8ed3ba5c01841a3c9074d5186f7b3f83f93a02f6c466b1f257328e3e3c67cef4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3886`
- B `enrichment` `er-evidence:11f8dca0fba45870b216e88cc9125113fc62cce994fca0b66d7dae298310e253` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:488`
- B `work` `er-evidence:fa1a30705fe6976d1d84d39fa4d21311edffd2530dd4b5803ffab9538122275c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:44`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 73 — Work

- **pairId:** `resolution-pair:9245fe73e7aee843e52c4c17592e07db09eed019044fc7e650296cae7f609824`
- **evidenceHash:** `166aac84c36bc5d31076cce608cbddc7f822cb0107502c74dd73d3be2f2f0082`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3032754641 (conference-paper) | OPENALEX W3176147180 (article) |
| Title | Estimating Numerical Distributions under Local Differential Privacy | SONIC: Application-aware Data Passing for Chained Serverless Applications |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4306420647 |
| DOI | 10.1145/3318464.3389700 | — |
| arXiv ID | — | — |
| Pages | 621-635 | 973-988 |
| Authors | (5) Zitao Li, Tianhao Wang, Milan Lopuhaä-Zwakenberg, Ninghui Li, Boris Škoric | (6) Ashraf Mahgoub, Karthick Shankar, Subrata Mitra, Ana Klimovic, Somali Chaterji, Saurabh Bagchi |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3318464.3389700, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3318464.3389700, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1145/3318464.3389700'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Estimating Numerical Distributions under Local Differential Privacy" (DOI 10.1145/3318464.3389700, 2020) and B "SONIC: Application-aware Data Passing for Chained Serverless Applications" (no DOI, 2021) have unrelated titles, different years, venues and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2020 vs 2021
- venueId S4393915683 vs S4306420647
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:1bc4d9f5d5a3786f2c0550d0f6a2ff0e48ef92992c6d6857c5d1772b10def6f9` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:266`
- B `work` `er-evidence:7d69e1dc64a8cc33f6576fe2fb237114230b3cd706958ff42233dd1c39389cfc` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:194`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 74 — Researcher

- **pairId:** `resolution-pair:183f908d4ff7b79b9bcee27350208c57a6a0faa43fc3ff0ff531235936ed3f94`
- **evidenceHash:** `0b4e33ab87252b3b6fac0e88deee311dd3d4fa427ba0df084c5b3c8e4c864d44`
- **Question:** do mention A `mention:openalex:W2951096868#2` and B `mention:openalex:W2991028016#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2951096868#2 | mention:openalex:W2991028016#4 |
| Name as written | Guoliang Li | Guoliang Li |
| Author position | 2 of 2 | 4 of 4 |
| ORCID on mention | 0000-0002-1398-0621 (OpenAlex-supplied) | 0000-0002-1398-0621 (OpenAlex-supplied) |
| OpenAlex author ID | A5100451576 | A5100451576 |
| Affiliation | ROR 03cve4549 | ROR 03cve4549 |
| Work title | Distributed In-memory Trajectory Similarity Search and Join on Road Network | Making data visualization more efficient and effective: a survey |
| Year | 2019 | 2019 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S78926909 |
| DOI | 10.1109/icde.2019.00115 | 10.1007/s00778-019-00588-3 |
| Coauthors | Haitao Yuan | Xuedi Qin, Yuyu Luo, Nan Tang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['03cve4549'] B=['03cve4549'] shared=['03cve4549']_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Guoliang Li" with the same ROR 03cve4549 in 2019, but no coauthor is shared (A: Haitao Yuan; B: Xuedi Qin, Yuyu Luo, Nan Tang) and topics differ (road-network trajectory search vs data-visualization survey).

**Supporting evidence:**
- Name exact match: A author#2, B author#4
- enrichment ror=03cve4549 on both target mentions
- Same OpenAlex-supplied observedOrcid 0000-0002-1398-0621 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors
- Topics differ

**Limitations / missing information:**
- "Guoliang Li" is a common name; name plus affiliation alone stays below the agreed bar

<details><summary>Evidence references</summary>

- A `work` `er-evidence:5f24ee7d565ba840bc542329751f1461d7c96e8f7055f4d4a07b5f3798c268c0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:340`
- A `enrichment` `er-evidence:650c6fadf6ba8c6ea1f35355fb93bfbb8d96d34a618e23199fc7cd85eb284136` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3556`
- B `work` `er-evidence:5aec721ab799bc8899a43ad4367eb31d89c69003ebf311f2d6dc8ef1f7d9cc1d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:306`
- B `enrichment` `er-evidence:f1fdf556d0bb1a8cb0e5c992f4da0325ef17d3fff990846bc37deb8140180d07` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3247`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: All four relevant papers are listed on https://dbgroup.cs.tsinghua.edu.cn/ligl/publications.html (Guoliang Li @ Tsinghua).

---

## Task 75 — Researcher

- **pairId:** `resolution-pair:fd0da02f1fb6000187b46c875db5cc3bb8467999e934adc86b7e07f7ae88ad68`
- **evidenceHash:** `51131178fb509875678318461c213270278d66cb6d37775f1fd2384aa8b26aca`
- **Question:** do mention A `mention:openalex:W3173154111#7` and B `mention:openalex:W4400910165#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3173154111#7 | mention:openalex:W4400910165#6 |
| Name as written | Yuanzhi Li | Yuxin Li |
| Author position | 7 of 10 | 6 of 7 |
| ORCID on mention | 0000-0002-4604-0468 (OpenAlex-supplied) | 0000-0002-4705-2372 (OpenAlex-supplied) |
| OpenAlex author ID | A5101879892 | A5100321628 |
| Affiliation | ROR 05x2bcf33 | ROR 01yj56c84 |
| Work title | PET: Optimizing Tensor Programs with Partially Equivalent Transformations and Automated Corrections. | Local-Global History-Aware Contrastive Learning for Temporal Knowledge Graph Reasoning |
| Year | 2021 | 2024 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210210321 |
| DOI | — | 10.1109/icde60146.2024.00062 |
| Coauthors | Haojie Wang, Jidong Zhai, Mingyu Gao, Zixuan Ma, Shizhi Tang, Liyan Zheng, Kaiyuan Rong, Yuanyong Chen, Zhihao Jia | Wei Chen, Huaiyu Wan, Yuting Wu, Shuyuan Zhao, Jiayaqi Cheng, Youfang Lin |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['05x2bcf33'] B=['01yj56c84'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#7 "Yuanzhi Li" and B author#6 "Yuxin Li" differ in given name (Yuanzhi vs Yuxin); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Yuanzhi" vs "Yuxin"
- No shared coauthors
- enrichment ror differs: 05x2bcf33 vs 01yj56c84
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:4bc9c48a33ef23748d4aa824a198749991a3ceb52f13c5cc576848a3e5b59d3f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:213`
- A `enrichment` `er-evidence:b19a05b640a23750148203b66c435f31c2a6a91ecd306595c7b1b66b49755d25` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2333`
- B `work` `er-evidence:1fc38f83233a9d15f426352781ecf9eb72716d67c6d0d7b88299777524cee1ff` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:25`
- B `enrichment` `er-evidence:c6f3f4bb15c85a6260b3d2045994d48b33d229175702a6a452a2e35f2f5d6e69` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:291`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 76 — Researcher

- **pairId:** `resolution-pair:93a25422078d451c6241d8cf0bf44e0d7d18415cb4fad702fd795fba3c4a15e5`
- **evidenceHash:** `31fbcea5d97d6867b72178eceba9dff00f086b48e4f1ccb76f5a66b10d3586ae`
- **Question:** do mention A `mention:openalex:W3029564598#4` and B `mention:openalex:W4398234120#10` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3029564598#4 | mention:openalex:W4398234120#10 |
| Name as written | Tim Kraska | Tim Kraska |
| Author position | 4 of 4 | 10 of 10 |
| ORCID on mention | 0009-0003-2414-2759 (OpenAlex-supplied) | 0009-0003-2414-2759 (OpenAlex-supplied) |
| OpenAlex author ID | A5034086130 | A5034086130 |
| Affiliation | ROR 042nb2s44 | ROR 04mv4n011 |
| Work title | Learning Multi-Dimensional Indexes | Intelligent Scaling in Amazon Redshift |
| Year | 2020 | 2024 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4393915683 |
| DOI | 10.1145/3318464.3380579 | 10.1145/3626246.3653394 |
| Coauthors | Vikram Nathan, Jialin Ding, Mohammad Alizadeh | Vikram Nathan, Vikramank Singh, Zhengchun Liu, Mohammad Rahman, Andreas Kipf, Dominik Horn, Davide Pagano, Gaurav Saxena, Balakrishnan Narayanaswamy |

_helper: shared coauthor normalizedNames = ['vikram nathan']_
_helper: target-mention ROR A=['042nb2s44'] B=['04mv4n011'] shared=none_

**AI-proposed label: `same`**

**Note:** Both mentions are "Tim Kraska" on papers whose first author is the same Vikram Nathan ("Learning Multi-Dimensional Indexes", SIGMOD 2020; "Intelligent Scaling in Amazon Redshift", SIGMOD 2024), both applying learning to data systems.

**Supporting evidence:**
- Name exact match: A author#4, B author#10
- Shared coauthor in payload: Vikram Nathan (author#1 in both)
- Same venueId S4393915683; learned/ML-for-data-systems topics
- Same OpenAlex-supplied observedOrcid 0009-0003-2414-2759 (provider hypothesis only)

**Conflicting evidence:**
- enrichment ror differs: 042nb2s44 (2020) vs 04mv4n011 (2024) — plausibly an affiliation change

**Limitations / missing information:**
- Rests mainly on one shared coauthor plus topic; a reviewer may prefer uncertain

<details><summary>Evidence references</summary>

- A `work` `er-evidence:96d832d2f9f25646dd80104605ff1d719778f6c68b4c100cf2d0a30c2fcefe9d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:280`
- A `enrichment` `er-evidence:aaa72289392069c06c5ee782b4fcedb02b53872f03e622c9daffe99a227002f8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3024`
- B `enrichment` `er-evidence:35239698f504bed03ad3df1d70ed1494a5335209a6891b13de0d7bcdc930017e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:528`
- B `work` `er-evidence:c71b74955981d8a460e89e963302314f1d0445d9b8e4bb55965e5b355081c5fb` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:47`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 77 — Researcher

- **pairId:** `resolution-pair:17cab78048d757b3e72b49e1804d49fafbbf3a48e60db2f86894460514c717dc`
- **evidenceHash:** `57c6f19f24fed4f8a51defba7b40f229ba1b5168ca3171a09b5500ffc0c2c1a8`
- **Question:** do mention A `mention:openalex:W3085441975#15` and B `mention:openalex:W4308883303#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3085441975#15 | mention:openalex:W4308883303#2 |
| Name as written | Goetz Graefe | Goetz Graefe |
| Author position | 15 of 17 | 2 of 3 |
| ORCID on mention | 0000-0003-0194-6466 (OpenAlex-supplied) | 0000-0003-0194-6466 (OpenAlex-supplied) |
| OpenAlex author ID | A5041862671 | A5041862671 |
| Affiliation | ROR 00njsd438 | ROR 00njsd438 |
| Work title | F1 lightning | Efficient Sorting, Duplicate Removal, Grouping, and Aggregation |
| Year | 2020 | 2022 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S90119964 |
| DOI | 10.14778/3415478.3415553 | 10.1145/3568027 |
| Coauthors | Jiacheng Yang, Ian Rae, Jun Xu, Jeff Shute, Zhan Yuan, Kelvin Lau, Qiang Zeng, Xi Zhao, Jun Ma, Ziyang Chen, Yuan Gao, Qilin Dong, Junxiong Zhou, Jeremy Wood, Jeff Naughton, John Cieslewicz | Thanh Do, Jeffrey Naughton |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00njsd438'] B=['00njsd438'] shared=['00njsd438']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Goetz Graefe" with the same ROR 00njsd438, coauthor Jeff Naughton (A#16) / Jeffrey Naughton (B#3), and query-processing topics ("F1 lightning" 2020; "Efficient Sorting, Duplicate Removal, Grouping, and Aggregation" 2022).

**Supporting evidence:**
- Name exact match: A author#15, B author#2
- Coauthor name variant Jeff/Jeffrey Naughton (exact-string helper misses it)
- enrichment ror=00njsd438 on both target mentions
- Topic continuity in query processing
- Same OpenAlex-supplied observedOrcid 0000-0003-0194-6466 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- Jeff/Jeffrey Naughton equivalence is itself a name-variant inference

<details><summary>Evidence references</summary>

- A `work` `er-evidence:6c64f112fd18e5022bbfb03d60310be9a901394e4e13351b097b9cf8648e853b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:259`
- A `enrichment` `er-evidence:d6821ae342980f4343c081803bf08a501fc59e5d7d6105a5030320a13168e7ba` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2841`
- B `enrichment` `er-evidence:c1daa555e86f66bc1f927835477f82855b3c6b9754aa997ba8fcfde4107e185e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1374`
- B `work` `er-evidence:e92e9858ec6dc93be0246860f4ec4431c145fc5f1ce0e6c0c0fbbc65c83878f5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:127`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 78 — Researcher

- **pairId:** `resolution-pair:1c2e039e8d66e1e5aecbc00e958ecb040c47b2163b9fb7c842d39caebc228c51`
- **evidenceHash:** `16c4235a8aa1cab5c4a8a047c5fc30dfc30d43325a90d7531450211514966345`
- **Question:** do mention A `mention:openalex:W2991028016#4` and B `mention:openalex:W4401352024#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2991028016#4 | mention:openalex:W4401352024#2 |
| Name as written | Guoliang Li | Guoliang Li |
| Author position | 4 of 4 | 2 of 9 |
| ORCID on mention | 0000-0002-1398-0621 (OpenAlex-supplied) | 0000-0002-1398-0621 (OpenAlex-supplied) |
| OpenAlex author ID | A5100451576 | A5100451576 |
| Affiliation | ROR 03cve4549 | ROR 03cve4549 |
| Work title | Making data visualization more efficient and effective: a survey | D-Bot: Database Diagnosis System using Large Language Models |
| Year | 2019 | 2024 |
| Venue ID | venue:openalex:S78926909 | venue:openalex:S4210226185 |
| DOI | 10.1007/s00778-019-00588-3 | 10.14778/3675034.3675043 |
| Coauthors | Xuedi Qin, Yuyu Luo, Nan Tang | Xuanhe Zhou, Zhaoyan Sun, Zhiyuan Liu, Weize Chen, Jianming Wu, Jiesi Liu, Ruohang Feng, Guoyang Zeng |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['03cve4549'] B=['03cve4549'] shared=['03cve4549']_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Guoliang Li" with the same ROR 03cve4549, but no coauthor is shared (A: Xuedi Qin, Yuyu Luo, Nan Tang; B: Xuanhe Zhou and others) and the topics differ (data-visualization survey 2019; LLM database diagnosis 2024).

**Supporting evidence:**
- Name exact match: A author#4, B author#2
- enrichment ror=03cve4549 on both target mentions
- Same OpenAlex-supplied observedOrcid 0000-0002-1398-0621 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- "Guoliang Li" is a common name; name plus affiliation alone stays below the agreed bar

<details><summary>Evidence references</summary>

- A `work` `er-evidence:5aec721ab799bc8899a43ad4367eb31d89c69003ebf311f2d6dc8ef1f7d9cc1d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:306`
- A `enrichment` `er-evidence:f1fdf556d0bb1a8cb0e5c992f4da0325ef17d3fff990846bc37deb8140180d07` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3247`
- B `enrichment` `er-evidence:3000b8148d36a241f0aaf2516792dcf2051c90234d3cb3926f7b2b87cf0c253b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:255`
- B `work` `er-evidence:97c8eafdb2ed56953a85c86e0f1a5ec6b7ab68b505375a1831c3e435e91536c0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:21`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: All four relevant papers are listed on https://dbgroup.cs.tsinghua.edu.cn/ligl/publications.html (Guoliang Li @ Tsinghua).

---

## Task 79 — Researcher

- **pairId:** `resolution-pair:59392b91e3a67e98ea38acad3b5a5af15d9aedf652c9e941e4c780b2c37aab03`
- **evidenceHash:** `4817b913ca6017d7e1d3b8e730e377694cef6a4f708dbb8ea4c1dbf46adb24fc`
- **Question:** do mention A `mention:openalex:W2797862701#5` and B `mention:openalex:W3029150735#5` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2797862701#5 | mention:openalex:W3029150735#5 |
| Name as written | Yao Zhang | Ying Zhang |
| Author position | 5 of 20 | 5 of 5 |
| ORCID on mention | 0000-0002-7375-9152 (OpenAlex-supplied) | 0000-0002-2674-1638 (OpenAlex-supplied) |
| OpenAlex author ID | A5100446990 | A5100386104 |
| Affiliation | — | ROR 02n96ep67 |
| Work title | BigDL | Efficient Bitruss Decomposition for Large-scale Bipartite Graphs |
| Year | 2019 | 2020 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210210321 |
| DOI | 10.1145/3357223.3362707 | 10.1109/icde48307.2020.00063 |
| Coauthors | Jason Jinquan Dai, Yiheng Wang, Xin Qiu, Ding Ding, Yanzhang Wang, Xianyan Jia, Cherry Li Zhang, Yan Wan, Zhichao Li, Jiao Wang, Shengsheng Huang, Zhongyuan Wu, Yang Wang, Yuhao Yang, Bowen She, Dongjie Shi, Qi Lu, Kai Huang, Guoqiong Song | Kai Wang, Xuemin Lin, Lu Qin, Wenjie Zhang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=- B=['02n96ep67'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#5 "Yao Zhang" and B author#5 "Ying Zhang" differ in given name (Yao vs Ying); no coauthor overlap.

**Supporting evidence:**
- nameText given names differ: "Yao" vs "Ying"
- No shared coauthors
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no affiliation evidence

<details><summary>Evidence references</summary>

- A `work` `er-evidence:7f23ff95eec85ee7e1670f4b0e01e515a25005e60fdf9568ca996325d47d0dc5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:422`
- B `work` `er-evidence:41f6558af10567cc486e199f81c732989870965963f4271c0f29e42bae68335f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:285`
- B `enrichment` `er-evidence:450193c3d5b3d9ac77482b49b5c3e86d599c18592d47f99b73992ed456720cd6` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3060`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 80 — Work

- **pairId:** `resolution-pair:c0df7866d93aa7486f5d3f8711ec4efe726e9a02cea75c5d3606d3e4a7894a57`
- **evidenceHash:** `30dc229f2301ed054f522165e1606b4eb4139ce7970d92d7abfc13c9602e0290`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2948709946 (conference-paper) | OPENALEX W3176081047 (article) |
| Title | Entity Matching Meets Data Science | The nanoPU: A Nanosecond Network Stack for Datacenters |
| Year | 2019 | 2021 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4306420647 |
| DOI | 10.1145/3299869.3314042 | — |
| arXiv ID | — | — |
| Pages | 389-403 | 239-256 |
| Authors | (20) Yash Govind, Pradap Konda, Paul Suganthan G.C., Philip Martinkus, Palaniappan Nagarajan, Han Li, Aravind Soundararajan, Sidharth Mudgal, Jeff R. Ballard, Haojun Zhang, Adel Ardalan, Sanjib Das, Derek Paulsen, Amanpreet Singh Saini, Erik Paulson … (+5 more) | (7) Stephen Ibanez, Alex Mallery, Serhat Arslan, Theo Jepsen, Muhammad Shahbaz, Changhoon Kim, Nick McKeown |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3299869.3314042, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3299869.3314042, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1145/3299869.3314042'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Entity Matching Meets Data Science" (DOI 10.1145/3299869.3314042, 2019, 20 authors) and B "The nanoPU: A Nanosecond Network Stack for Datacenters" (no DOI, OSDI 2021, 7 authors) have unrelated titles, different years and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2019 vs 2021
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:c0b57e8bf04dfcab0dcef8bb915a02ecddd4115a60eb7b816d1555fd3857de37` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:346`
- B `work` `er-evidence:4511884fb6014a4cd0d412ce95cfd0fc559b4178356b3ac1240a451f9c47c1d3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:196`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---
