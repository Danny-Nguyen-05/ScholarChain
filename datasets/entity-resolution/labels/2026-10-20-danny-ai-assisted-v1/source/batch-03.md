# ScholarChain AI review drafts — batch 03 (tasks 41–60)

> **Status: AI_SUGGESTIONS_PENDING_HUMAN_REVIEW.** These are AI-generated suggestions from a session-reported `claude-opus-5-5` model (not independently verified). They are not human reviews or gold labels. Record your own decision in each task's decision box; an empty box means not reviewed.

Queue: `review-queue:05c5817f62a70d378829be361b9c9169fc9af18448f7c83c245f1d65bbca6175`  
Work tasks: 10 · Researcher tasks: 10

Rows marked `>> … <<` in the raw data and the 'Name as written' row identify the mention being compared. OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider hypotheses. Lines in _italics_ starting with 'helper:' are exact-string comparisons computed by a script to help reading; they are not judgments.

---
## Task 41 — Researcher

- **pairId:** `resolution-pair:1c8d25477544e0f42ffa0786add32d2adabc3da061d25b22c04cbe1030edcf43`
- **evidenceHash:** `67d932ab4a7de92142a0b1ccc70839d0cbf1d1545a3de807bb4dddb087ff4498`
- **Question:** do mention A `mention:openalex:W2948709946#6` and B `mention:openalex:W3197468999#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2948709946#6 | mention:openalex:W3197468999#2 |
| Name as written | Han Li | Han Li |
| Author position | 6 of 20 | 2 of 8 |
| ORCID on mention | — | 0000-0002-7380-6174 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5100452600 |
| Affiliation | ROR 01y2jtd41 | ROR 04mv4n011 |
| Work title | Entity Matching Meets Data Science | Deep learning for blocking in entity matching |
| Year | 2019 | 2021 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210226185 |
| DOI | 10.1145/3299869.3314042 | 10.14778/3476249.3476294 |
| Coauthors | Yash Govind, Pradap Konda, Paul Suganthan G.C., Philip Martinkus, Palaniappan Nagarajan, Aravind Soundararajan, Sidharth Mudgal, Jeff R. Ballard, Haojun Zhang, Adel Ardalan, Sanjib Das, Derek Paulsen, Amanpreet Singh Saini, Erik Paulson, Youngchoon Park, Marshall Carter, Mingju Sun, Glenn M. Fung, AnHai Doan | Saravanan Thirumuruganathan, Nan Tang, Mourad Ouzzani, Yash Govind, Derek Paulsen, Glenn Fung, AnHai Doan |

_helper: shared coauthor normalizedNames = ['anhai doan', 'derek paulsen', 'yash govind']_
_helper: target-mention ROR A=['01y2jtd41'] B=['04mv4n011'] shared=none_

**AI-proposed label: `same`**

**Note:** Both "Han Li" mentions are on entity-matching papers ("Entity Matching Meets Data Science" 2019; "Deep learning for blocking in entity matching" 2021) that share three coauthors in the payloads: AnHai Doan, Derek Paulsen and Yash Govind.

**Supporting evidence:**
- Name exact match: A author#6, B author#2
- Three shared coauthors: AnHai Doan, Derek Paulsen, Yash Govind
- Specific topic continuity: entity matching (2019, 2021)

**Conflicting evidence:**
- enrichment ror differs: A 01y2jtd41 vs B 04mv4n011 (could reflect a move; not conclusive)

**Limitations / missing information:**
- "Han Li" is a common name
- A mention has no ORCID or OpenAlex author id; B observedOrcid 0000-0002-7380-6174 is OpenAlex-supplied only
- Coauthor and topic overlap are correlated (same research group)

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:7451477560b776e07c9b04a124317edef660f962ad399cf13d8c650fbb29aa33` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3622`
- A `work` `er-evidence:c0b57e8bf04dfcab0dcef8bb915a02ecddd4115a60eb7b816d1555fd3857de37` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:346`
- B `enrichment` `er-evidence:256acadedde29e63218c59a807ea76f26daac8c658b5d6bdb809bf27319c4fa5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2000`
- B `work` `er-evidence:e9ce9a5ce535f27d46fdae6c3b440f61958c0ab022ac7883cfaaa776df8f2aaf` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:182`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 42 — Work

- **pairId:** `resolution-pair:ae8ccaaefd996fd04f440e687b56d5822919843f0a704361331a621fd73f0977`
- **evidenceHash:** `7d330b870c54d968bac6160ddf254076714d70bcb043a25f29714bbb38677f3a`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3014616325 (conference-paper) | OPENALEX W3196904276 (article) |
| Title | Dataset Discovery in Data Lakes | Auctus |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210226185 |
| DOI | 10.1109/icde48307.2020.00067 | 10.14778/3476311.3476346 |
| arXiv ID | — | — |
| Pages | 709-720 | 2791-2794 |
| Authors | (4) Alex Bogatu, Alvaro A. A. Fernandes, Norman W. Paton, Nikolaos Konstantinou | (6) Sonia Castelo, Rémi Rampin, Aécio Santos, Aline Bessa, Fernando Chirigati, Juliana Freire |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde48307.2020.00067, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde48307.2020.00067, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.14778/3476311.3476346, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3476311.3476346, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1109/icde48307.2020.00067'] B=['10.14778/3476311.3476346'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Dataset Discovery in Data Lakes" (10.1109/icde48307.2020.00067, 2020) and B "Auctus" (10.14778/3476311.3476346, 2021) have distinct DOIs, different titles, years and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2020 vs 2021
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:01309b00fda4ace6389101bda1cb5fb3c64576850070a80846a0ba27388d36d2` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:290`
- B `work` `er-evidence:80fa14e2b3ea608c4f7b4bdbf31e79f71107ef243e8c96289bdeeef6fc6e9021` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:183`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 43 — Work

- **pairId:** `resolution-pair:08bb0a03de6d98ec0a19d0d374fa5d74f25c2215329204293cdf9a53cf14fdae`
- **evidenceHash:** `b680ab3b9246483dd941cd5256e87ef92b81d815c0e8af343a02a253c5a2fc90`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3209366914 (conference-paper) | OPENALEX W4312703862 (article) |
| Title | Characterizing Microservice Dependency and Performance | Decoupled dynamic spatial-temporal graph neural network for traffic forecasting |
| Year | 2021 | 2022 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210226185 |
| DOI | 10.1145/3472883.3487003 | 10.14778/3551793.3551827 |
| arXiv ID | — | — |
| Pages | 412-426 | 2733-2746 |
| Authors | (9) Shutian Luo, Huanle Xu, Chengzhi Lu, Kejiang Ye, Guoyao Xu, Liping Zhang, Yu Ding, Jian He, Chengzhong Xu | (7) Zezhi Shao, Zhao Zhang, Wei Wei, Fei Wang, Yongjun Xu, Xin Cao, Christian S. Jensen |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3472883.3487003, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3472883.3487003, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.14778/3551793.3551827, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3551793.3551827, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3472883.3487003'] B=['10.14778/3551793.3551827'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Characterizing Microservice Dependency and Performance" (10.1145/3472883.3487003, 2021) and B "Decoupled dynamic spatial-temporal graph neural network for traffic forecasting" (10.14778/3551793.3551827, 2022) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2021 vs 2022
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:513647a5dc2ae953239b0220da4f7af494354bd07630beb88510e3697c10f158` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:175`
- B `work` `er-evidence:9dc915c7fe2133de2177bbbad0681e879bd2ed188cedafca976b265cfc5049b4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:122`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 44 — Researcher

- **pairId:** `resolution-pair:502822510c87540bc9f8f7c4d08cd0910b534b1cd8aa99f998ac0814414b510c`
- **evidenceHash:** `f2f3842e76a5747512437042026da5dd4f4748c5e9cc2c44a1bc630a8205e63a`
- **Question:** do mention A `mention:openalex:W3029687524#3` and B `mention:openalex:W4289533840#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3029687524#3 | mention:openalex:W4289533840#3 |
| Name as written | Chenjuan Guo | Chenjuan Guo |
| Author position | 3 of 5 | 3 of 7 |
| ORCID on mention | 0000-0002-4516-4637 (OpenAlex-supplied) | 0000-0002-4516-4637 (OpenAlex-supplied) |
| OpenAlex author ID | A5084021933 | A5084021933 |
| Affiliation | ROR 04m5j1k67 | ROR 04m5j1k67 |
| Work title | Stochastic Origin-Destination Matrix Forecasting Using Dual-Stage Graph Convolutional, Recurrent Neural Networks | Robust and Explainable Autoencoders for Unsupervised Time Series Outlier Detection |
| Year | 2020 | 2022 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210210321 |
| DOI | 10.1109/icde48307.2020.00126 | 10.1109/icde53745.2022.00273 |
| Coauthors | Jilin Hu, Bin Yang, Christian S. Jensen, Hui Xiong | Tung Kieu, Bin Yang, Christian S. Jensen, Yan Zhao, Feiteng Huang, Kai Zheng |

_helper: shared coauthor normalizedNames = ['bin yang', 'christian s. jensen']_
_helper: target-mention ROR A=['04m5j1k67'] B=['04m5j1k67'] shared=['04m5j1k67']_

**AI-proposed label: `same`**

**Note:** Both mentions are author#3 "Chenjuan Guo" with two shared coauthors (Bin Yang, Christian S. Jensen), the same affiliation ROR 04m5j1k67, and the same venue S4210210321 in 2020 and 2022.

**Supporting evidence:**
- Name exact match at author#3 in both
- Two shared coauthors: Bin Yang, Christian S. Jensen
- enrichment ror=04m5j1k67 on both target mentions
- Related topics: spatio-temporal forecasting (2020) and time-series outlier detection (2022)
- Same OpenAlex-supplied observedOrcid 0000-0002-4516-4637 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- All hints OpenAlex-derived

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:1bc325ce3cbac9b76530693dbb38f88b2223cf50e1b1f6082715faec627eebeb` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3018`
- A `work` `er-evidence:448a19e8aec46536cfc0da570bda9d3e349773c77226e1306c44ed841ee5c3b6` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:279`
- B `enrichment` `er-evidence:192b7e3b035cdfe7c491e2aa764e1a073de1b7436bed065fbb8c5c09c6e57466` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1441`
- B `work` `er-evidence:c8d047e855bad795bc36bbc14b064f84ccdd20986c01b5ca68534a23f62f2350` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:134`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 45 — Work

- **pairId:** `resolution-pair:c1e40d59a0eaf96cd353049b79dd4987fcc2e8b45b35ffe26239ba73c6ed4667`
- **evidenceHash:** `a2df94570c97f523e216a38d1d42fc927e6ee20ef06c452a4ea53280a71850f2`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2970992672 (article) | OPENALEX W4281725510 (conference-paper) |
| Title | Data lake management | NeutronStar: Distributed GNN Training with Hybrid Dependency Management |
| Year | 2019 | 2022 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4393915683 |
| DOI | 10.14778/3352063.3352116 | 10.1145/3514221.3526134 |
| arXiv ID | — | — |
| Pages | 1986-1989 | 1301-1315 |
| Authors | (5) Fatemeh Nargesian, Erkang Zhu, Renée J. Miller, Ken Q. Pu, Patricia C. Arocena | (6) Qiange Wang, Yanfeng Zhang, Hao Wang, Chaoyi Chen, Xiaodong Zhang, Ge Yu |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3352063.3352116, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3352063.3352116, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3514221.3526134, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3514221.3526134, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3352063.3352116'] B=['10.1145/3514221.3526134'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Data lake management" (10.14778/3352063.3352116, 2019) and B "NeutronStar: Distributed GNN Training with Hybrid Dependency Management" (10.1145/3514221.3526134, 2022) have distinct DOIs, different titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2019 vs 2022
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:4d1f75598054751b7eeae3c15a95baba95307d778da8d6c53705d5b79edea84d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:322`
- B `work` `er-evidence:18d788d629a580f452b96d336c54304c01faaf0e58a8a887203921396b92e581` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:152`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 46 — Researcher

- **pairId:** `resolution-pair:98a15ad296950644cdf66e93da3680d0617d673fdef323353b6c5932f1d66f16`
- **evidenceHash:** `955eea4533ab7e031e5915f62327ac0c80e900e60eac387fd4e5f2c1a43062ac`
- **Question:** do mention A `mention:openalex:W2796285681#2` and B `mention:openalex:W3009138933#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2796285681#2 | mention:openalex:W3009138933#3 |
| Name as written | Evaggelia Pitoura | Evaggelia Pitoura |
| Author position | 2 of 2 | 3 of 4 |
| ORCID on mention | 0000-0002-3775-4995 (OpenAlex-supplied) | 0000-0002-3775-4995 (OpenAlex-supplied) |
| OpenAlex author ID | A5047515620 | A5047515620 |
| Affiliation | ROR 01qg3j183 | ROR 01qg3j183 |
| Work title | Top- Durable Graph Pattern Queries on Temporal Graphs | Flow Computation in Temporal Interaction Networks |
| Year | 2018 | 2021 |
| Venue ID | venue:openalex:S30698027 | venue:openalex:S4210210321 |
| DOI | 10.1109/tkde.2018.2823754 | 10.1109/icde51399.2021.00063 |
| Coauthors | Konstantinos Semertzidis | Chrysanthi Kosyfaki, Nikos Mamoulis, Panayiotis Tsaparas |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01qg3j183'] B=['01qg3j183'] shared=['01qg3j183']_

**AI-proposed label: `same`**

**Note:** The full name "Evaggelia Pitoura" appears on both mentions with the same affiliation ROR 01qg3j183, and both works are on temporal graphs/networks (durable pattern queries on temporal graphs, TKDE 2018; flow computation in temporal interaction networks, ICDE 2021).

**Supporting evidence:**
- Name exact match: A author#2, B author#3
- enrichment ror=01qg3j183 on both target mentions
- Specific topic continuity: temporal graph/network analysis
- Same OpenAlex-supplied observedOrcid 0000-0002-3775-4995 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthor

**Limitations / missing information:**
- All hints OpenAlex-derived

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:b13d84484f66db37a1f6dfd753e7fe0520343293c4981c1e0fc19eb3eda2136b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4314`
- A `work` `er-evidence:c30d4f3f1f4f574cd03c12ff3d26b17e8e72e4dd0c7d3c067e806dd39e8483e4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:424`
- B `work` `er-evidence:4fac2fc8f0d31b4dce3de0f532b59051b37397eadac206fc037478cd4b5f46b1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:297`
- B `enrichment` `er-evidence:c3e22e9d251d21ffc67510c939010d2f1335c1acd9b0f5bb4bb844a43d75931c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3164`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 47 — Researcher

- **pairId:** `resolution-pair:2af49eca811744910ac4ed6a87f6d5710a37fa8a3163bd0b851385ad104d2e88`
- **evidenceHash:** `de4e657e3da327d426a213a4184039f61bd3193b384accb37051483737d6d68e`
- **Question:** do mention A `mention:openalex:W2797862701#8` and B `mention:openalex:W3198515637#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2797862701#8 | mention:openalex:W3198515637#2 |
| Name as written | Cherry Li Zhang | Ce Zhang |
| Author position | 8 of 20 | 2 of 4 |
| ORCID on mention | — | 0000-0001-9947-9960 (OpenAlex-supplied) |
| OpenAlex author ID | A5109394206 | A5100383721 |
| Affiliation | ROR 01ek73717 | ROR 0145fw131 |
| Work title | BigDL | SlimChain |
| Year | 2019 | 2021 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210226185 |
| DOI | 10.1145/3357223.3362707 | 10.14778/3476249.3476283 |
| Coauthors | Jason Jinquan Dai, Yiheng Wang, Xin Qiu, Ding Ding, Yao Zhang, Yanzhang Wang, Xianyan Jia, Yan Wan, Zhichao Li, Jiao Wang, Shengsheng Huang, Zhongyuan Wu, Yang Wang, Yuhao Yang, Bowen She, Dongjie Shi, Qi Lu, Kai Huang, Guoqiong Song | Cheng Xu, Jianliang Xu, Jian Pei |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01ek73717'] B=['0145fw131'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#8 "Cherry Li Zhang" and B author#2 "Ce Zhang" have different given names (Cherry Li vs Ce) and share only the surname; no coauthors or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Cherry Li" vs "Ce"
- No shared coauthors
- enrichment ror differs: 01ek73717 vs 0145fw131

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A mention has no ORCID

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:39ad2b2eae9e457864c8ec5ffc694490096fcc17d440be60955a61854ae461f5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4301`
- A `work` `er-evidence:7f23ff95eec85ee7e1670f4b0e01e515a25005e60fdf9568ca996325d47d0dc5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:422`
- B `work` `er-evidence:211e4e51b6ffcf680947ff3d349488dc074dbfb17a649ed3860360c0f8ba02dd` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:180`
- B `enrichment` `er-evidence:87bdd11b1fc001bce60798ec84d3b4198f3599d5243ffc3082db2cfc493ba104` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1940`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 48 — Researcher

- **pairId:** `resolution-pair:1bda332a97dad21d344f9003783980730f927f2b8f45738bd36f56767ddafc9d`
- **evidenceHash:** `24e467e286f251fb6638b9c0450e065a103bc7cad78f676daf0a76c223d6cb10`
- **Question:** do mention A `mention:openalex:W3104436288#5` and B `mention:openalex:W3209593805#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3104436288#5 | mention:openalex:W3209593805#6 |
| Name as written | Aditya Akella | Aditya Akella |
| Author position | 5 of 5 | 6 of 6 |
| ORCID on mention | 0000-0002-5920-170X (OpenAlex-supplied) | 0000-0002-5920-170X (OpenAlex-supplied) |
| OpenAlex author ID | A5035329776 | A5035329776 |
| Affiliation | ROR 01y2jtd41 | ROR 00njsd438; ROR 00hj54h04 |
| Work title | {PANIC}: A High-Performance Programmable {NIC} for Multi-tenant Networks | Atoll |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S7407088165 |
| DOI | — | 10.1145/3472883.3486981 |
| Coauthors | Jiaxin Lin, Kiran Patel, Brent Stephens, Anirudh Sivaraman | Arjun Singhvi, Arjun Balasubramanian, Kevin Houck, Mohammed Danish Shaikh, Shivaram Venkataraman |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01y2jtd41'] B=['00hj54h04', '00njsd438'] shared=none_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Aditya Akella" on systems papers, but there is no shared coauthor and no shared affiliation (A ROR 01y2jtd41 vs B RORs 00njsd438 and 00hj54h04); only the name and broad area support a match.

**Supporting evidence:**
- Name exact match: A author#5, B author#6
- Same OpenAlex-supplied observedOrcid 0000-0002-5920-170X / oaAuthor A5035329776 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors
- No overlapping ROR

**Limitations / missing information:**
- Title-level topics too thin to compare ("{PANIC}: … Programmable {NIC}…" OSDI 2020 vs "Atoll" 2021)
- A work has no DOI

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:119c4270fe1b07c75edc72698f4aefe24c38c21713a8fcd05b536339c283c2e6` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2485`
- A `work` `er-evidence:2412f5e08c3933491025ec72d9da4e7e79b260d6e88429f43978de6218645441` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:228`
- B `work` `er-evidence:270fb8267598928f36847af91ca7adf33922a796f40dec4f11caab62beb92218` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:173`
- B `enrichment` `er-evidence:a1bbc16dc2db70fc40e6ac27de7e4bf1523c677b53a659d1c9d622e064f92856` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1861`
- B `enrichment` `er-evidence:ad44e599c55cfd4cc27aff3394fee44350b68aece9a8d2698b9f4860dbdcf3e9` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1862`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Semantic Scholar assigns the same author ID on both papers (api.semanticscholar.org). (PANIC and Atoll)

---

## Task 49 — Work

- **pairId:** `resolution-pair:261d40379723bab888034d72b294d209d697e8856fe2cd5fbd1c0c536a78fc3b`
- **evidenceHash:** `812e6ad24c1fbecf6c7c959b5481b28f4bf76730f5cbed6762abe19c283ee8ec`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W4226021524 (conference-paper) | OPENALEX W4366492480 (article) |
| Title | FedRecAttack: Model Poisoning Attack to Federated Recommendation | Lero: A Learning-to-Rank Query Optimizer |
| Year | 2022 | 2023 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210226185 |
| DOI | 10.1109/icde53745.2022.00243 | 10.14778/3583140.3583160 |
| arXiv ID | — | — |
| Pages | 2643-2655 | 1466-1479 |
| Authors | (6) Dazhong Rong, Shuai Ye, Ruoyan Zhao, Hon Ning Yuen, Jianhai Chen, Qinming He | (7) Rong Zhu, Wei Chen, Bolin Ding, Xingguang Chen, Andreas Pfadler, Ziniu Wu, Jingren Zhou |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde53745.2022.00243, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde53745.2022.00243, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.14778/3583140.3583160, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3583140.3583160, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1109/icde53745.2022.00243'] B=['10.14778/3583140.3583160'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "FedRecAttack: Model Poisoning Attack to Federated Recommendation" (10.1109/icde53745.2022.00243, 2022) and B "Lero: A Learning-to-Rank Query Optimizer" (10.14778/3583140.3583160, 2023) have distinct DOIs, unrelated titles and disjoint authors.

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

- A `work` `er-evidence:2e0016a09e4b4ec3df13c2fcb5bc1717a8f5cdb4de5bd5f235e9dd9317663e19` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:161`
- B `work` `er-evidence:8b5cc35a989d5afac5411c2b964977382929fc219deb261f8d5788d4b28698fd` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:116`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 50 — Work

- **pairId:** `resolution-pair:2e18fb91e8c6fb464eafdb423af37ab5ff59e2a4facd7254ff8c651d42561b01`
- **evidenceHash:** `70592e6b9893b13be755412d5d665e47ac66294b0a4190bbd80364a0660a1c90`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3173799718 (conference-paper) | OPENALEX W4379382789 (conference-paper) |
| Title | PG-Keys: Keys for Property Graphs | Auto-WLM: Machine Learning Enhanced Workload Management in Amazon Redshift |
| Year | 2021 | 2023 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4393915683 |
| DOI | 10.1145/3448016.3457561 | 10.1145/3555041.3589677 |
| arXiv ID | — | — |
| Pages | 2423-2436 | 225-237 |
| Authors | (17) Renzo Angles, Angela Bonifati, Stefania Dumbrava, George Fletcher, Keith W. Hare, Jan Hidders, Victor E. Lee, Bei Li, Leonid Libkin, Wim Martens, Filip Murlak, Josh Perryman, Ognjen Savković, Michael Schmidt, Juan Sequeda … (+2 more) | (10) Gaurav Saxena, Mohammad Rahman, Naresh Chainani, Chunbin Lin, George Caragea, Fahim Chowdhury, Ryan Marcus, Tim Kraska, Ippokratis Pandis, Balakrishnan (Murali) Narayanaswamy |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3448016.3457561, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3448016.3457561, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3555041.3589677, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3555041.3589677, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3448016.3457561'] B=['10.1145/3555041.3589677'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "PG-Keys: Keys for Property Graphs" (10.1145/3448016.3457561, 2021, 17 authors) and B "Auto-WLM: Machine Learning Enhanced Workload Management in Amazon Redshift" (10.1145/3555041.3589677, 2023, 10 authors) have distinct DOIs, different titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2021 vs 2023
- work.authors disjoint

**Conflicting evidence:**
- Same venueId S4393915683

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:84472d1ab10050dd478f739686fce4a6ea4c336ab37ab638b9602628b953f9ea` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:210`
- B `work` `er-evidence:deae1540ddd2912800b65d6044277fe1fb9be238fd2599da4e7734052c1ea0c5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:111`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 51 — Researcher

- **pairId:** `resolution-pair:062cc1ebb11a7487e91e508f3984e70a4ce9725b07757d95ace3cc29e0f1ec49`
- **evidenceHash:** `db6c16acd8056cd77593d22f3c05e0eab85febbce4bedffe140cb5202461a76d`
- **Question:** do mention A `mention:openalex:W2797862701#6` and B `mention:openalex:W2952933729#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2797862701#6 | mention:openalex:W2952933729#1 |
| Name as written | Yanzhang Wang | Yansheng Wang |
| Author position | 6 of 20 | 1 of 6 |
| ORCID on mention | 0000-0003-4039-9215 (OpenAlex-supplied) | 0009-0007-3496-8676 (OpenAlex-supplied) |
| OpenAlex author ID | A5056283001 | A5101838851 |
| Affiliation | ROR 00hhjss72; ROR 01ek73717 | ROR 00wk2mp56 |
| Work title | BigDL | Adaptive Dynamic Bipartite Graph Matching: A Reinforcement Learning Approach |
| Year | 2019 | 2019 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210210321 |
| DOI | 10.1145/3357223.3362707 | 10.1109/icde.2019.00133 |
| Coauthors | Jason Jinquan Dai, Yiheng Wang, Xin Qiu, Ding Ding, Yao Zhang, Xianyan Jia, Cherry Li Zhang, Yan Wan, Zhichao Li, Jiao Wang, Shengsheng Huang, Zhongyuan Wu, Yang Wang, Yuhao Yang, Bowen She, Dongjie Shi, Qi Lu, Kai Huang, Guoqiong Song | Yongxin Tong, Cheng Long, Pan Xu, Ke Xu, Weifeng Lv |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00hhjss72', '01ek73717'] B=['00wk2mp56'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#6 "Yanzhang Wang" and B author#1 "Yansheng Wang" differ in given name (Yanzhang vs Yansheng); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Yanzhang" vs "Yansheng"
- No shared coauthors
- enrichment ror sets disjoint: {00hhjss72, 01ek73717} vs {00wk2mp56}
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- Both 2019 publications

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:6697407201dc1d50699e451c7cf0e661aa1e3d2c4d4bb09528a811f983fb0dac` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4282`
- A `work` `er-evidence:7f23ff95eec85ee7e1670f4b0e01e515a25005e60fdf9568ca996325d47d0dc5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:422`
- A `enrichment` `er-evidence:af747573d087712ca425c09eef961ca5ffc038af66bace65dcbc49d2da51a895` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4284`
- B `enrichment` `er-evidence:db0911867e9d2b5e529f2b72493479e49d3652a8581bf5d8f629ddc7a66440e7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3503`
- B `work` `er-evidence:fae6b7bbaed55d3b82548b091044276de940b07577eca0c8b737c4a2d03fafee` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:334`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 52 — Work

- **pairId:** `resolution-pair:5a555ee8e6cad310eef1bb7a017e3034318948d08b16686f8462b72504c10abd`
- **evidenceHash:** `38326fe6c5323f9836c6cbd0ea9cab42b9fb21fbd5f8fb6637ce020e199c5bfc`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2963128714 (conference-paper) | OPENALEX W3100228586 (article) |
| Title | Overload Control for Scaling WeChat Microservices | Testing Configuration Changes in Context to Prevent Production Failures. |
| Year | 2018 | 2020 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4306420647 |
| DOI | 10.1145/3267809.3267823 | — |
| arXiv ID | — | — |
| Pages | 149-161 | 735-751 |
| Authors | (9) Hao Zhou, Ming Chen, Qian Lin, Yong Wang, Xiaobin She, Sifan Liu, Rui Gu, Beng Chin Ooi, Junfeng Yang | (6) Xudong Sun, Runxiang Cheng, Jianyan Chen, Elaine Ang, Owolabi Legunsen, Tianyin Xu |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3267809.3267823, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3267809.3267823, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1145/3267809.3267823'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Overload Control for Scaling WeChat Microservices" (DOI 10.1145/3267809.3267823, 2018) and B "Testing Configuration Changes in Context to Prevent Production Failures." (no DOI, OSDI 2020 PDF) have different titles, years, venues and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2018 vs 2020
- venueId S7407088165 vs S4306420647
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:713f9afc8a05b3a899ebff84c0046f7b89ed1f53f64fb0843fcce7ffae2b1648` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:331`
- B `work` `er-evidence:7b880d1ce3608084b75f700bbbe4c5a16e700a2f5c5d8d7ac4a6b04e6673e66b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:231`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 53 — Work

- **pairId:** `resolution-pair:1bf1f82c93c439c417be345e57c289ae0cd150b29f19e3d3d4c4504f68d15147`
- **evidenceHash:** `cdb5cfffceee1255f03a890f9ef560a7d9765d6de434d048c7c54d1d0dd2e8bd`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W4387321071 (conference-paper) | OPENALEX W4400909953 (conference-paper) |
| Title | SPFresh: Incremental In-Place Update for Billion-Scale Vector Search | Adapting Large Language Models by Integrating Collaborative Semantics for Recommendation |
| Year | 2023 | 2024 |
| Venue ID | venue:openalex:S4306420989 | venue:openalex:S4210210321 |
| DOI | 10.1145/3600006.3613166 | 10.1109/icde60146.2024.00118 |
| arXiv ID | — | — |
| Pages | 545-561 | 1435-1448 |
| Authors | (12) Yuming Xu, Hengyu Liang, Jin Li, Shuotao Xu, Qi Chen, Qianxi Zhang, Cheng Li, Ziyue Yang, Fan Yang, Yuqing Yang, Peng Cheng, Mao Yang | (7) Bowen Zheng, Yupeng Hou, Hongyu Lu, Yu Chen, Wayne Xin Zhao, Ming Chen, Ji-Rong Wen |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3600006.3613166, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3600006.3613166, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1109/icde60146.2024.00118, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde60146.2024.00118, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3600006.3613166'] B=['10.1109/icde60146.2024.00118'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "SPFresh: Incremental In-Place Update for Billion-Scale Vector Search" (10.1145/3600006.3613166, 2023) and B "Adapting Large Language Models by Integrating Collaborative Semantics for Recommendation" (10.1109/icde60146.2024.00118, 2024) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2023 vs 2024
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:0165c810044156b387afec53613b29410c2ea86c6e87c1973a6fdebde5cab511` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:76`
- B `work` `er-evidence:a82d51106e187740ffbf08b5e852ff1d8191d23dd2e5a531341fa734870c6efe` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:26`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 54 — Researcher

- **pairId:** `resolution-pair:1ea7319d0ca49a709aabbcf0fdc8a31e38cd2c398314b397fc020e2d3db55474`
- **evidenceHash:** `fa0c5b6724be0de1071222a2440aa55899c107276310ab5bf1d9a3c8c4ad06c7`
- **Question:** do mention A `mention:openalex:W2789607830#3` and B `mention:openalex:W2963431420#7` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2789607830#3 | mention:openalex:W2963431420#7 |
| Name as written | Junbum Shin | Junbum Shin |
| Author position | 3 of 4 | 7 of 8 |
| ORCID on mention | 0009-0005-7985-6163 (OpenAlex-supplied) | — |
| OpenAlex author ID | A5090468303 | — |
| Affiliation | ROR 04w3jy968; ROR 020m7t761 | ROR 020m7t761 |
| Work title | Privacy Enhanced Matrix Factorization for Recommendation with Local Differential Privacy | Collecting and Analyzing Multidimensional Data with Local Differential Privacy |
| Year | 2018 | 2019 |
| Venue ID | venue:openalex:S30698027 | venue:openalex:S4210210321 |
| DOI | 10.1109/tkde.2018.2805356 | 10.1109/icde.2019.00063 |
| Coauthors | Hyejin Shin, Sungwook Kim, Xiaokui Xiao | Ning Wang, Xiaokui Xiao, Yin Yang, Jun Zhao, Siu Cheung Hui, Hyejin Shin, Ge Yu |

_helper: shared coauthor normalizedNames = ['hyejin shin', 'xiaokui xiao']_
_helper: target-mention ROR A=['020m7t761', '04w3jy968'] B=['020m7t761'] shared=['020m7t761']_

**AI-proposed label: `same`**

**Note:** Both "Junbum Shin" mentions share coauthors Hyejin Shin and Xiaokui Xiao, the affiliation ROR 020m7t761, and the topic of local differential privacy (TKDE 2018; ICDE 2019).

**Supporting evidence:**
- Name exact match: A author#3, B author#7
- Two shared coauthors: Hyejin Shin, Xiaokui Xiao
- enrichment ror=020m7t761 present on both target mentions (A also has 04w3jy968)
- Specific topic continuity: local differential privacy

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B mention has no ORCID/OpenAlex author id; A observedOrcid 0009-0005-7985-6163 is OpenAlex-supplied only

<details><summary>Evidence references</summary>

- A `work` `er-evidence:60107b4781dbaa3abfc7f506d7e55f06c717d187508ea2eb375b3216b6bd6e78` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:440`
- A `enrichment` `er-evidence:9ddbd3769d1cfe11f8c07e7a9f3e87e33344d6de7c9dfef0c3dfc4a71a05a834` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4470`
- A `enrichment` `er-evidence:bdca0792eedcf2169c1178a2b79a5beb8c755a72a8c59374b0c2b615b35d73e7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4469`
- B `work` `er-evidence:ec3e4de73bbb8fd85736344e239e8959865b9a4abff9cfd2df326339630b30b0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:329`
- B `enrichment` `er-evidence:f7c286bb3fdc2309d5542a6a2861d3cc928c95b8af7f40bc14ed7dcd2dd912ae` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3451`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 55 — Work

- **pairId:** `resolution-pair:2cdc70c302c58135bb4ae50f61f75e189f533d4003601b2135670d12ed6e5aa2`
- **evidenceHash:** `1f6fc2ca6d9a56073a5127b608a8fb59feaa0813948f27a6bda61ece2656651d`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2948513753 (conference-paper) | OPENALEX W2952395191 (conference-paper) |
| Title | An End-to-End Automatic Cloud Database Tuning System Using Deep Reinforcement Learning | Information Diffusion Prediction via Recurrent Cascades Convolution |
| Year | 2019 | 2019 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210210321 |
| DOI | 10.1145/3299869.3300085 | 10.1109/icde.2019.00074 |
| arXiv ID | — | — |
| Pages | 415-432 | 770-781 |
| Authors | (12) Ji Zhang, Yu Liu, Ke Zhou, Guoliang Li, Zhili Xiao, Bin Cheng, Jiashu Xing, Yangtao Wang, Tianheng Cheng, Li Liu, Minwei Ran, Zekang Li | (6) Xueqin Chen, Fan Zhou, Kunpeng Zhang, Goce Trajcevski, Ting Zhong, Fengli Zhang |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3299869.3300085, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3299869.3300085, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1109/icde.2019.00074, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde.2019.00074, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3299869.3300085'] B=['10.1109/icde.2019.00074'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "An End-to-End Automatic Cloud Database Tuning System Using Deep Reinforcement Learning" (10.1145/3299869.3300085) and B "Information Diffusion Prediction via Recurrent Cascades Convolution" (10.1109/icde.2019.00074) are both 2019 but have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- venueId S4393915683 vs S4210210321
- work.authors disjoint

**Conflicting evidence:**
- Same year 2019

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:97f6793e2a3a2e6b71d5159d991fbd0f28083011b727bc847e4064c2da12bf80` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:347`
- B `work` `er-evidence:877a845200acf423a24946e94244840a5e04bccfdd6a075a2b548e1277d7dd59` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:337`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 56 — Researcher

- **pairId:** `resolution-pair:dd313653fb8c4dfc1a704090b553fa9610ae6094db390140712fe1664feeb147`
- **evidenceHash:** `ceb34129ee5bdd1b5665183da05d0dba483e2f2ea0dc9f0a55a99fc05bb17dab`
- **Question:** do mention A `mention:openalex:W4400909541#5` and B `mention:openalex:W4400909566#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4400909541#5 | mention:openalex:W4400909566#6 |
| Name as written | Chao Huang | Can Huang |
| Author position | 5 of 6 | 6 of 10 |
| ORCID on mention | 0000-0002-4061-1573 (OpenAlex-supplied) | 0000-0003-0223-0494 (OpenAlex-supplied) |
| OpenAlex author ID | A5101857110 | A5000202631 |
| Affiliation | ROR 02zhqgq86 | ROR 013q1eq08 |
| Work title | Graph Augmentation for Recommendation | PURPLE: Making a Large Language Model a Better SQL Writer |
| Year | 2024 | 2024 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210210321 |
| DOI | 10.1109/icde60146.2024.00049 | 10.1109/icde60146.2024.00009 |
| Coauthors | Qianru Zhang, Lianghao Xia, Xuheng Cai, Siu-Ming Yiu, Christian S. Jensen | Tonghui Ren, Yuankai Fan, Zhenying He, Ren Huang, Jiaqi Dai, Yinan Jing, Kai Zhang, Yifan Yang, X. Sean Wang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['02zhqgq86'] B=['013q1eq08'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#5 "Chao Huang" and B author#6 "Can Huang" differ in given name (Chao vs Can); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Chao" vs "Can"
- No shared coauthors
- enrichment ror differs: 02zhqgq86 vs 013q1eq08
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- Same year 2024 and same venueId S4210210321

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:48d70597ccb8170e5e6538f2ea8a03fdb03b983802ab500dfd395a851938c846` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:32`
- A `enrichment` `er-evidence:e1589fbbf694fb903356c9264bb2fb62179aa85d637050924c4b0f4397730863` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:365`
- B `work` `er-evidence:d2083a16899f4790ccf48fcdf6142aa02d682b4358f21e292799673f80fb8c6e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:31`
- B `enrichment` `er-evidence:e37b7580fe55d103a3ff2503a3286ef46c51bb47c326fcf1a75a7587b3771d09` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:351`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 57 — Work

- **pairId:** `resolution-pair:d4955b77b2d8e48e9f836e68b4a48de4ce8cd4d19aac9b847f43b7a34d5a1330`
- **evidenceHash:** `86fbe249cbe4f168dd224daeacad9f0421bfd6338a36345bff99d5a522e114da`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2795016801 (conference-paper) | OPENALEX W4283326127 (article) |
| Title | Deep Representation Learning for Trajectory Similarity Computation | QueryFormer |
| Year | 2018 | 2022 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210226185 |
| DOI | 10.1109/icde.2018.00062 | 10.14778/3529337.3529349 |
| arXiv ID | — | — |
| Pages | 617-628 | 1658-1670 |
| Authors | (5) Xiucheng Li, Kaiqi Zhao, Gao Cong, Christian S. Jensen, Wei Wei | (4) Yue Zhao, Gao Cong, Jiachen Shi, Chunyan Miao |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde.2018.00062, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde.2018.00062, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.14778/3529337.3529349, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3529337.3529349, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1109/icde.2018.00062'] B=['10.14778/3529337.3529349'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Deep Representation Learning for Trajectory Similarity Computation" (10.1109/icde.2018.00062, 2018) and B "QueryFormer" (10.14778/3529337.3529349, 2022) have distinct DOIs and different titles; only Gao Cong is shared.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2018 vs 2022

**Conflicting evidence:**
- Shared author Gao Cong

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:08749f629aa0645ec74d5e4277f0db0e404abc4881bdd82a7400a1c2f485b39c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:431`
- B `work` `er-evidence:1b1b21c7eff486082fcd13d16a3cac06c5236e55b74842c37e339c0eaf91e239` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:144`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 58 — Work

- **pairId:** `resolution-pair:dada93f06d98de7525d040aa45f3686c7055bc2b9122801db444668c24d2ff93`
- **evidenceHash:** `cba77ad1366ae7f2ba0b6e0849abb66f1c9aae7fbb0176275d929818ab6ab2fc`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2798654119 (conference-paper) | OPENALEX W4400910543 (conference-paper) |
| Title | Online Processing Algorithms for Influence Maximization | MergeSFL: Split Federated Learning with Feature Merging and Batch Size Regulation |
| Year | 2018 | 2024 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210210321 |
| DOI | 10.1145/3183713.3183749 | 10.1109/icde60146.2024.00164 |
| arXiv ID | — | — |
| Pages | 991-1005 | 2054-2067 |
| Authors | (4) Jing Tang, Xueyan Tang, Xiaokui Xiao, Junsong Yuan | (6) Yunming Liao, Yang Xu, Hongli Xu, Lun Wang, Zhiwei Yao, Chunming Qiao |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3183713.3183749, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3183713.3183749, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1109/icde60146.2024.00164, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde60146.2024.00164, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3183713.3183749'] B=['10.1109/icde60146.2024.00164'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Online Processing Algorithms for Influence Maximization" (10.1145/3183713.3183749, 2018) and B "MergeSFL: Split Federated Learning…" (10.1109/icde60146.2024.00164, 2024) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2018 vs 2024
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:6ef41e03789f3341825c8f0cec1a09c8e684da54599aa3933846547c61467c61` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:418`
- B `work` `er-evidence:dfb7129687ca2f2d61dacab0a8d6e3e67a57f7881a02823a93ec2e4364654ed3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:22`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 59 — Researcher

- **pairId:** `resolution-pair:08e8f2b855f86120e545bebf4957605f788fac057e256c3a7d39dc1b65ad1b1e`
- **evidenceHash:** `5ef138da24617b8373652b7c39c33070dda4222088898144e1f9b811f1c86aa0`
- **Question:** do mention A `mention:openalex:W2963128714#8` and B `mention:openalex:W4285179693#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2963128714#8 | mention:openalex:W4285179693#3 |
| Name as written | Beng Chin Ooi | Beng Chin Ooi |
| Author position | 8 of 9 | 3 of 5 |
| ORCID on mention | — | 0000-0003-4446-1100 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5024892041 |
| Affiliation | ROR 01tgyzw49 | ROR 01tgyzw49 |
| Work title | Overload Control for Scaling WeChat Microservices | Hybrid blockchain database systems |
| Year | 2018 | 2022 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210226185 |
| DOI | 10.1145/3267809.3267823 | 10.14778/3510397.3510406 |
| Coauthors | Hao Zhou, Ming Chen, Qian Lin, Yong Wang, Xiaobin She, Sifan Liu, Rui Gu, Junfeng Yang | Zerui Ge, Dumitrel Loghin, Pingcheng Ruan, Tianwen Wang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01tgyzw49'] B=['01tgyzw49'] shared=['01tgyzw49']_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Beng Chin Ooi" with the same affiliation ROR 01tgyzw49, but there is no shared coauthor and the topics differ (WeChat microservice overload control 2018; hybrid blockchain databases 2022); name plus affiliation alone stays below the agreed bar.

**Supporting evidence:**
- Name exact match: A author#8, B author#3
- enrichment ror=01tgyzw49 on both target mentions

**Conflicting evidence:**
- No shared coauthors
- Topics not continuous

**Limitations / missing information:**
- A mention has no ORCID; B observedOrcid 0000-0003-4446-1100 is OpenAlex-supplied only
- Leans same given the full three-part name and shared ROR, but no further corroboration is supplied

<details><summary>Evidence references</summary>

- A `work` `er-evidence:713f9afc8a05b3a899ebff84c0046f7b89ed1f53f64fb0843fcce7ffae2b1648` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:331`
- A `enrichment` `er-evidence:c631b83e22622f9ffbaba65aed5cf48c40007b82b2ce772321995474d2f509f7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3473`
- B `work` `er-evidence:7e2c53e8b8615e5d4be4225237e3edbab9266563825abf358915e92dc695ee21` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:142`
- B `enrichment` `er-evidence:d1ee3ba6754d3fea7b2fbcd20f1445ed645f547ac6596bcff6c7840005f1c887` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1520`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Semantic Scholar assigns the same author ID on both papers (api.semanticscholar.org).

---

## Task 60 — Researcher

- **pairId:** `resolution-pair:2d3399015e5a4cb10b799ab65b3564b1ba05db2c09a8a2011c659fb15d73c72d`
- **evidenceHash:** `d94b0f2194fba0ee481431a7d1c5a826228d3bdd28664327bb64f8cf76c69d3d`
- **Question:** do mention A `mention:openalex:W3177116918#4` and B `mention:openalex:W4398234451#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3177116918#4 | mention:openalex:W4398234451#4 |
| Name as written | Feifei Li | Feifei Li |
| Author position | 4 of 23 | 4 of 8 |
| ORCID on mention | 0009-0003-0770-5775 (OpenAlex-supplied) | 0009-0003-0770-5775 (OpenAlex-supplied) |
| OpenAlex author ID | A5100450470 | A5100450470 |
| Affiliation | ROR 00k642b80 | ROR 00k642b80 |
| Work title | PolarDB Serverless | PolarDB-MP: A Multi-Primary Cloud-Native Database via Disaggregated Shared Memory |
| Year | 2021 | 2024 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4393915683 |
| DOI | 10.1145/3448016.3457560 | 10.1145/3626246.3653377 |
| Coauthors | Wei Cao, Yingqiang Zhang, Xinjun Yang, Sheng Wang, Qingda Hu, Xuntao Cheng, Zongzhi Chen, Zhenjun Liu, Jing Fang, Bo Wang, Yuhui Wang, Haiqing Sun, Ze Yang, Zhushi Cheng, Sen Chen, Jian Wu, Wei Hu, Jianwei Zhao, Yusong Gao, Songlu Cai, Yunyang Zhang, Jiawang Tong | Xinjun Yang, Yingqiang Zhang, Hao Chen, Bo Wang, Jing Fang, Chuan Sun, Yuhui Wang |

_helper: shared coauthor normalizedNames = ['bo wang', 'jing fang', 'xinjun yang', 'yingqiang zhang', 'yuhui wang']_
_helper: target-mention ROR A=['00k642b80'] B=['00k642b80'] shared=['00k642b80']_

**AI-proposed label: `same`**

**Note:** Both mentions are author#4 "Feifei Li" on PolarDB papers ("PolarDB Serverless" 2021; "PolarDB-MP…" 2024) with five shared coauthors (Xinjun Yang, Yingqiang Zhang, Bo Wang, Jing Fang, Yuhui Wang) and the same ROR 00k642b80.

**Supporting evidence:**
- Name exact match at author#4 in both
- Five shared coauthors
- enrichment ror=00k642b80 on both target mentions
- Same system line (PolarDB) and venueId S4393915683
- Same OpenAlex-supplied observedOrcid 0009-0003-0770-5775 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- All hints OpenAlex-derived

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:1c5e7c105b1ef57d170f64b2e54fd67e7925fbfc56bc722868398f31cccc3373` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2057`
- A `work` `er-evidence:f5e94042ae7e543c7b77ca4b0d8e947d920de48ef87d4f6337d9e1c7722012a5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:186`
- B `enrichment` `er-evidence:9b025805d2b1607aee8f1d9974ae9989652e5e0ebf2b0d4216ebeed107759447` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:489`
- B `work` `er-evidence:fa1a30705fe6976d1d84d39fa4d21311edffd2530dd4b5803ffab9538122275c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:44`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---
