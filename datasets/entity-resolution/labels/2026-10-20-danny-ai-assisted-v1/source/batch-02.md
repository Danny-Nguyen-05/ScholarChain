# ScholarChain AI review drafts — batch 02 (tasks 21–40)

> **Status: AI_SUGGESTIONS_PENDING_HUMAN_REVIEW.** These are AI-generated suggestions from a session-reported `claude-opus-5-5` model (not independently verified). They are not human reviews or gold labels. Record your own decision in each task's decision box; an empty box means not reviewed.

Queue: `review-queue:05c5817f62a70d378829be361b9c9169fc9af18448f7c83c245f1d65bbca6175`  
Work tasks: 11 · Researcher tasks: 9

Rows marked `>> … <<` in the raw data and the 'Name as written' row identify the mention being compared. OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider hypotheses. Lines in _italics_ starting with 'helper:' are exact-string comparisons computed by a script to help reading; they are not judgments.

---
## Task 21 — Researcher

- **pairId:** `resolution-pair:e2b51a58fa6b25ac33dd6979633bf21237586d0932dac758353d35667c3d4c42`
- **evidenceHash:** `f7f06d7105e65ab176df7fc432517a8ff4043fb55002739ce2ba1713ce725f02`
- **Question:** do mention A `mention:openalex:W4388080974#6` and B `mention:openalex:W4400641571#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4388080974#6 | mention:openalex:W4400641571#2 |
| Name as written | Jing Wang | Jianguo Wang |
| Author position | 6 of 10 | 2 of 3 |
| ORCID on mention | 0000-0001-7260-0521 (OpenAlex-supplied) | 0000-0002-3039-1175 (OpenAlex-supplied) |
| OpenAlex author ID | A5100378346 | A5004019699 |
| Affiliation | ROR 0220qvk04 | ROR 02dqehb95 |
| Work title | Not All Resources are Visible | Survey of vector database management systems |
| Year | 2023 | 2024 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S78926909 |
| DOI | 10.1145/3620678.3624650 | 10.1007/s00778-024-00864-x |
| Coauthors | Xinkai Wang, Hao He, Yuancheng Li, Chao Li, Xiaofeng Hou, Quan Chen, Jingwen Leng, Minyi Guo, Leibo Wang | James Jie Pan, Guoliang Li |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['0220qvk04'] B=['02dqehb95'] shared=none_

**AI-proposed label: `different`**

**Note:** The compared names have different given names: A author#6 "Jing Wang" vs B author#2 "Jianguo Wang"; neither is an initial or transliteration variant of the other, and only the common surname is shared.

**Supporting evidence:**
- nameText given names differ: "Jing" vs "Jianguo"
- No shared coauthors (10-author vs 3-author lists)
- enrichment ror differs: 0220qvk04 vs 02dqehb95 (weak alone)
- Different OpenAlex-supplied ORCIDs 0000-0001-7260-0521 vs 0000-0002-3039-1175 (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- ORCIDs are OpenAlex-supplied, not registry-confirmed

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:cdbb3c8063ea910e06a902c0e21cd6e7243cd665bd82dadae9272a9419459337` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:627`
- A `work` `er-evidence:e3b33803800b5dac4d7991d96d8b89b74fcd541270ae737413e08b31075262ed` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:57`
- B `work` `er-evidence:2b092e565a1ab970db70a97026858504371f33dc3cfca8abd3c77a88654bba30` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:35`
- B `enrichment` `er-evidence:82444c6d8e31f61b45ea29aee6f4aed08a16aa7728686af26074e76c37eb6d3e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:398`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 22 — Researcher

- **pairId:** `resolution-pair:b440d6f3e180d15dada17075cc6f965f2574de4095a362d165825d7a22d2d0a7`
- **evidenceHash:** `e8b070efdd90d7b7aef45093a0b62735184fd4b14f4d5ef575ca2c599d7d0fa7`
- **Question:** do mention A `mention:openalex:W2884596205#4` and B `mention:openalex:W3145728363#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2884596205#4 | mention:openalex:W3145728363#2 |
| Name as written | Jianxin Li | Jinfeng Li |
| Author position | 4 of 6 | 2 of 7 |
| ORCID on mention | 0000-0002-9059-330X (OpenAlex-supplied) | 0000-0001-9462-2625 (OpenAlex-supplied) |
| OpenAlex author ID | A5100380474 | A5100428948 |
| Affiliation | ROR 047272k79 | — |
| Work title | Maximum co-located community search in large scale social networks | Annotating Columns with Pre-trained Language Models |
| Year | 2018 | 2022 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4393915683 |
| DOI | 10.14778/3231751.3231755 | 10.1145/3514221.3517906 |
| Coauthors | Lu Chen, Chengfei Liu, Rui Zhou, Xiaochun Yang, Bin Wang | Yoshihiko Suhara, Yuliang Li, Dan Zhang, Çağatay Demiralp, Chen Chen, Wang-Chiew Tan |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['047272k79'] B=- shared=none_

**AI-proposed label: `different`**

**Note:** A author#4 "Jianxin Li" and B author#2 "Jinfeng Li" differ in given name and share only the surname Li; no coauthor is shared.

**Supporting evidence:**
- nameText given names differ: "Jianxin" vs "Jinfeng"
- No shared coauthors
- Different OpenAlex-supplied ORCIDs 0000-0002-9059-330X vs 0000-0001-9462-2625 (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no affiliation evidence

<details><summary>Evidence references</summary>

- A `work` `er-evidence:992f97b965b17e88a800281006561e68eb3af3e2070d8cc786b83d20a86b7457` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:406`
- A `enrichment` `er-evidence:fbcf41a02878689313f0ef89c5314995e20bf4226a78de738180e841545b3d3e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4125`
- B `work` `er-evidence:f2ef2ec961ccb328f039d863120c449773e030019003e86a9532b7d124b604c9` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:217`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 23 — Work

- **pairId:** `resolution-pair:4f68b1440e0c09ea63d7843bdff95da7ca6a7ad719dff7eb073b7e26115dbff3`
- **evidenceHash:** `7ab106be7af082bacc6e87223e6b0c9602e6eedd01cec636f810658dd6cced08`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2797851444 (conference-paper) | OPENALEX W3096785379 (conference-paper) |
| Title | Privacy at Scale | Vessels |
| Year | 2018 | 2020 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S7407088165 |
| DOI | 10.1145/3183713.3197390 | 10.1145/3419111.3421282 |
| arXiv ID | — | — |
| Pages | 1655-1658 | 462-476 |
| Authors | (6) Graham Cormode, Somesh Jha, Tejas Kulkarni, Ninghui Li, Divesh Srivastava, Tianhao Wang | (7) Kyungtae Kim, Chung Hwan Kim, Junghwan "John" Rhee, Xiao Yu, Haifeng Chen, Dave (Jing) Tian, Byoungyoung Lee |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3183713.3197390, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3183713.3197390, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3419111.3421282, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3419111.3421282, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3183713.3197390'] B=['10.1145/3419111.3421282'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Privacy at Scale" (10.1145/3183713.3197390, 2018) and B "Vessels" (10.1145/3419111.3421282, 2020) have distinct DOIs, different titles, years, venues and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2018 vs 2020; venueId S4393915683 vs S7407088165
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:e6ac5f643fffe1f52c03c264e5715da6fe4a19f1c15309e4737918f6f55e355e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:423`
- B `work` `er-evidence:7eceb968dd2b3d617a2b6c9e5255da1216a88155b83e5830f420aae9a74ff477` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:241`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 24 — Researcher

- **pairId:** `resolution-pair:6a790bd55802f926656f0daca7d0bcb78378ca003e0a43bd1a9036d27cc16b50`
- **evidenceHash:** `638898fda10a9a3964fd138f8ed7e3e060f757be2192a870540ac018b4105ecd`
- **Question:** do mention A `mention:openalex:W3029535034#2` and B `mention:openalex:W3196849431#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3029535034#2 | mention:openalex:W3196849431#1 |
| Name as written | Guoliang Li | Guoliang Li |
| Author position | 2 of 4 | 1 of 9 |
| ORCID on mention | 0000-0002-1398-0621 (OpenAlex-supplied) | 0000-0002-1398-0621 (OpenAlex-supplied) |
| OpenAlex author ID | A5100451576 | A5100451576 |
| Affiliation | ROR 03cve4549 | ROR 03cve4549 |
| Work title | Reinforcement Learning with Tree-LSTM for Join Order Selection | openGauss |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210226185 |
| DOI | 10.1109/icde48307.2020.00116 | 10.14778/3476311.3476380 |
| Coauthors | Xiang Yu, Chengliang Chai, Nan Tang | Xuanhe Zhou, Ji Sun, Xiang Yu, Yue Han, Lianyuan Jin, Wenbo Li, Tianqing Wang, Shifu Li |

_helper: shared coauthor normalizedNames = ['xiang yu']_
_helper: target-mention ROR A=['03cve4549'] B=['03cve4549'] shared=['03cve4549']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Guoliang Li" with shared coauthor Xiang Yu (A author#1, B author#4), the same affiliation ROR 03cve4549, and database-system topics in consecutive years (RL join-order selection 2020; openGauss 2021).

**Supporting evidence:**
- Name exact match: A author#2, B author#1
- Shared coauthor in payload: Xiang Yu
- enrichment ror=03cve4549 on both target mentions
- Topic continuity in database systems (2020, 2021)
- Same OpenAlex-supplied observedOrcid 0000-0002-1398-0621 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- "Guoliang Li" is a common name; identity relies on the coauthor and affiliation overlap, which are correlated
- All hints are OpenAlex-derived

<details><summary>Evidence references</summary>

- A `work` `er-evidence:216ec4887d9129835850349363b70285662cf9985159961feacfb34ea73ad9a1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:281`
- A `enrichment` `er-evidence:867599c6234f563b67dea0da2490205304dc657d89830aaae8416e001b82de0e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3030`
- B `work` `er-evidence:4c9b040c6500e7809cd094389c14d26496881096f7f855bd0b6411e267acf993` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:184`
- B `enrichment` `er-evidence:e63bf305e0a74f4d1b51ba244dea5608d3124151045cf6017af9c8cbbd1596a4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2024`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 25 — Work

- **pairId:** `resolution-pair:3ae7c97b55003ca8bfdc8ca53e6e7573dad4b86bcf8e050543df2be3408f9f5f`
- **evidenceHash:** `0ac6b4fdaced3f9d2010b2f1f299d13f746078d23002fa4ab518832daa4e4f75`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2798945787 (conference-paper) | OPENALEX W4379390538 (conference-paper) |
| Title | Cold Filter | Proactively Screening Machine Learning Pipelines with ARGUSEYES |
| Year | 2018 | 2023 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4393915683 |
| DOI | 10.1145/3183713.3183726 | 10.1145/3555041.3589682 |
| arXiv ID | — | — |
| Pages | 741-756 | 91-94 |
| Authors | (7) Yang Zhou, Tong Yang, Jie Jiang, Bin Cui, Minlan Yu, Xiaoming Li, Steve Uhlig | (5) Sebastian Schelter, Stefan Grafberger, Shubha Guha, Bojan Karlas, Ce Zhang |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3183713.3183726, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3183713.3183726, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3555041.3589682, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3555041.3589682, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3183713.3183726'] B=['10.1145/3555041.3589682'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Cold Filter" (10.1145/3183713.3183726, 2018) and B "Proactively Screening Machine Learning Pipelines with ARGUSEYES" (10.1145/3555041.3589682, 2023) have distinct DOIs, different titles, years and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2018 vs 2023
- work.authors disjoint

**Conflicting evidence:**
- Same venueId S4393915683

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:533cb6a4ec05ffe8fb5cd5ac12caa4147f0024ac0e0a5183d24262701c733b8d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:415`
- B `work` `er-evidence:1da0799930275b6d16032738cc31d1cfca84429b9abcd36068fa8fefcbc53455` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:106`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 26 — Work

- **pairId:** `resolution-pair:2f26ec4370dc9dbfcc7899e0214742010a70302a334ffab325a1b77ea78c30c3`
- **evidenceHash:** `3b64cfd020b23fb42168b007d713b376255db04700d337174a4de447930a336d`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3029150735 (conference-paper) | OPENALEX W3176367300 (conference-paper) |
| Title | Efficient Bitruss Decomposition for Large-scale Bipartite Graphs | Enabling Efficient Cyber Threat Hunting With Cyber Threat Intelligence |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210210321 |
| DOI | 10.1109/icde48307.2020.00063 | 10.1109/icde51399.2021.00024 |
| arXiv ID | — | — |
| Pages | 661-672 | 193-204 |
| Authors | (5) Kai Wang, Xuemin Lin, Lu Qin, Wenjie Zhang, Ying Zhang | (9) Peng Gao, Fei Shao, Xiaoyuan Liu, Xusheng Xiao, Zheng Qin, Fengyuan Xu, Prateek Mittal, Sanjeev R. Kulkarni, Dawn Song |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde48307.2020.00063, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde48307.2020.00063, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1109/icde51399.2021.00024, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde51399.2021.00024, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1109/icde48307.2020.00063'] B=['10.1109/icde51399.2021.00024'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Efficient Bitruss Decomposition for Large-scale Bipartite Graphs" (10.1109/icde48307.2020.00063, 2020) and B "Enabling Efficient Cyber Threat Hunting With Cyber Threat Intelligence" (10.1109/icde51399.2021.00024, 2021) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2020 vs 2021
- work.authors disjoint

**Conflicting evidence:**
- Same venueId S4210210321

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:41f6558af10567cc486e199f81c732989870965963f4271c0f29e42bae68335f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:285`
- B `work` `er-evidence:fd7de9e0fc8f9fdd0efbb16cd0626216a4ca465e983e9bdebd0adfdfd1228f3c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:191`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 27 — Researcher

- **pairId:** `resolution-pair:9bf0674c3648be88a2c2609a77866d77600cf318b9d038c6f17f347a48a9efc4`
- **evidenceHash:** `bc83abfa72a3e609a3dd0e0f006a0ba9a919b983380169257286e36f723806ef`
- **Question:** do mention A `mention:crossref:10.1145/3196959.3196987#1` and B `mention:openalex:W3013397275#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:crossref:10.1145/3196959.3196987#1 | mention:openalex:W3013397275#1 |
| Name as written | Fernando Florenzano | Fernando Florenzano |
| Author position | 1 of 5 | 1 of 5 |
| ORCID on mention | — | 0000-0002-0846-3291 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5010251788 |
| Affiliation | "Pontificia Universidad Católica de Chile, Santiago, Chile" | ROR 04teye511 |
| Work title | Constant Delay Algorithms for Regular Document Spanners | Efficient Enumeration Algorithms for Regular Document Spanners |
| Year | 2018 | 2020 |
| Venue ID | None | venue:openalex:S90119964 |
| DOI | 10.1145/3196959.3196987 | 10.1145/3351451 |
| Coauthors | Cristian Riveros, Martin Ugarte, Stijn Vansummeren, Domagoj Vrgoc | Cristian Riveros, Martín Ugarte, Stijn Vansummeren, Domagoj Vrgoč |

_helper: shared coauthor normalizedNames = ['cristian riveros', 'stijn vansummeren']_
_helper: target-mention ROR A=- B=['04teye511'] shared=none_

**AI-proposed label: `same`**

**Note:** Both mentions are first author "Fernando Florenzano" on regular-document-spanner papers (Crossref 2018 "Constant Delay Algorithms…"; OpenAlex 2020 "Efficient Enumeration Algorithms…") with the same four coauthors in the same order (Riveros, Ugarte/Martín Ugarte, Vansummeren, Vrgoc/Vrgoč).

**Supporting evidence:**
- Name exact match at author#1 in both works
- Coauthor lists match in order; accent differences (Martin/Martín, Vrgoc/Vrgoč) explain why the exact-string helper shows only 2 shared
- Closely related titles on regular document spanners (2018, 2020)
- Cross-source: A from CROSSREF, B from OPENALEX

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- Affiliations not comparable: A Crossref organizationName "Pontificia Universidad Católica de Chile, Santiago, Chile" vs B ROR 04teye511 (no name supplied)
- B observedOrcid 0000-0002-0846-3291 is OpenAlex-supplied only

<details><summary>Evidence references</summary>

- A `work` `er-evidence:4f6776ddaca408a49641068a430f58a43e972bdb49a4b8b32b39bc711f0d3f47` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:3`
- A `mention-affiliation` `er-evidence:f846af60d3622e1a5fd2def74e22ead106bff1e90d20deeae3969948a09138b6` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/mention-affiliation/part-r-00000:17`
- B `work` `er-evidence:0366818a398a6d1fc64f8ff2c5aee380c8acfae08e505908074bed20befb5593` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:292`
- B `enrichment` `er-evidence:9a23348e32f3c7704042b549dfdf873cc9815be6f3619578c881f641d7529ff6` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3125`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 28 — Work

- **pairId:** `resolution-pair:f3457dff8dcfbfe64a9feef3a68ecf8427aba761b2e52cef5bab0e387a57d6ae`
- **evidenceHash:** `f537f607ab8c4b2a2564394537623fe9934d4fc8c087c3ff345a8166ceb080c6`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2970148517 (article) | OPENALEX W4281718197 (conference-paper) |
| Title | Neo | Amazon Redshift Re-invented |
| Year | 2019 | 2022 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4393915683 |
| DOI | 10.14778/3342263.3342644 | 10.1145/3514221.3526045 |
| arXiv ID | — | — |
| Pages | 1705-1718 | 2205-2217 |
| Authors | (8) Ryan Marcus, Parimarjan Negi, Hongzi Mao, Chi Zhang, Mohammad Alizadeh, Tim Kraska, Olga Papaemmanouil, Nesime Tatbul | (24) Nikos Armenatzoglou, Sanuj Basu, Naga Bhanoori, Mengchu Cai, Naresh Chainani, Kiran Chinta, Venkatraman Govindaraju, Todd J. Green, Monish Gupta, Sebastian Hillig, Eric Hotinger, Yan Leshinksy, Jintian Liang, Michael McCreedy, Fabian Nagel … (+9 more) |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3342263.3342644, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3342263.3342644, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3514221.3526045, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3514221.3526045, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3342263.3342644'] B=['10.1145/3514221.3526045'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Neo" (10.14778/3342263.3342644, 2019, 8 authors) and B "Amazon Redshift Re-invented" (10.1145/3514221.3526045, 2022, 24 authors) have distinct DOIs, different titles, years and disjoint authors.

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

- A `work` `er-evidence:2b283b52ed624a5a810efe8e2a3994ac293445e62e514ad27377aca0c532fd4a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:326`
- B `work` `er-evidence:597b93c05d7af6ead1d601ad9fcae0edd8c7dd470fda23129f8bcebdc4ad2ce2` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:154`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 29 — Work

- **pairId:** `resolution-pair:4e00e01af01a0d78292937b93f45883999c26250abcf68f42cec4e4707c9434e`
- **evidenceHash:** `fda556f509b29e1984f0d15834a1625a1bcf31963e827cb529bd19f761e6984f`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2917161856 (article) | OPENALEX W3086105743 (article) |
| Title | DIFF | PyTorch distributed |
| Year | 2018 | 2020 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210226185 |
| DOI | 10.14778/3297753.3297761 | 10.14778/3415478.3415530 |
| arXiv ID | — | — |
| Pages | 419-432 | 3005-3018 |
| Authors | (13) Firas Abuzaid, Peter Kraft, Sahaana Suri, Edward Gan, Eric Xu, Atul Shenoy, Asvin Ananthanarayan, John Sheu, Erik Meijer, Xi Wu, Jeff Naughton, Peter Bailis, Matei Zaharia | (11) Shen Li, Yanli Zhao, Rohan Varma, Omkar Salpekar, Pieter Noordhuis, Teng Li, Adam Paszke, Jeff Smith, Brian Vaughan, Pritam Damania, Soumith Chintala |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3297753.3297761, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3297753.3297761, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.14778/3415478.3415530, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3415478.3415530, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3297753.3297761'] B=['10.14778/3415478.3415530'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "DIFF" (10.14778/3297753.3297761, 2018, 13 authors) and B "PyTorch distributed" (10.14778/3415478.3415530, 2020, 11 authors) have distinct DOIs, different titles, years and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2018 vs 2020; pages 419-432 vs 3005-3018
- work.authors disjoint

**Conflicting evidence:**
- Same venueId S4210226185

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:dc5665d09c344ae4ad05e3988d5b7cd8e47a9a7b7737c3847727aa3f339789ba` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:362`
- B `work` `er-evidence:25b002cc4cd2c20b15a8ce9bd48a789efba0318347590a5f3fe188c5f75acbe0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:256`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 30 — Work

- **pairId:** `resolution-pair:805ec2340dffab6dc176fbe0e5b46c533ef2ba061688386343aed3b6dae55e1b`
- **evidenceHash:** `7232298de74b71894eee330ce2b3fb86cb15ad52744b63cb7fd9713cd047dc21`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3011807731 (article) | OPENALEX W4385270408 (conference-paper) |
| Title | Distributed representations of tuples for entity resolution | Relational Message Passing for Fully Inductive Knowledge Graph Completion |
| Year | 2018 | 2023 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210210321 |
| DOI | 10.14778/3236187.3236198 | 10.1109/icde55515.2023.00098 |
| arXiv ID | — | — |
| Pages | 1454-1467 | 1221-1233 |
| Authors | (5) Muhammad Ebraheem, Saravanan Thirumuruganathan, Shafiq Joty, Mourad Ouzzani, Nan Tang | (7) Yuxia Geng, Jiaoyan Chen, Jeff Z. Pan, Mingyang Chen, Song Jiang, Wen Zhang, Huajun Chen |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3236187.3236198, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3236187.3236198, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1109/icde55515.2023.00098, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde55515.2023.00098, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3236187.3236198'] B=['10.1109/icde55515.2023.00098'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Distributed representations of tuples for entity resolution" (10.14778/3236187.3236198, 2018) and B "Relational Message Passing for Fully Inductive Knowledge Graph Completion" (10.1109/icde55515.2023.00098, 2023) have distinct DOIs, different titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2018 vs 2023
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:84d77ba9e074950213311ce809ffd42c6f2dd5962024dccafca2763e6ae021aa` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:295`
- B `work` `er-evidence:cee97cbc4ed183b9a755412ae56ac1cc0be7d3f04099fa3cf24c426edb920e66` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:92`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 31 — Researcher

- **pairId:** `resolution-pair:9554e7ae15056928884136d8eeff869a4372c2cdb9dec1d8a22d8e09748f65e0`
- **evidenceHash:** `615eca9c9187b9912f817bc33d75b6e2881d834072f6003d26dc9a0ef09b2661`
- **Question:** do mention A `mention:openalex:W3096241851#1` and B `mention:openalex:W4387321086#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3096241851#1 | mention:openalex:W4387321086#1 |
| Name as written | Juncheng Yang | Juncheng Yang |
| Author position | 1 of 3 | 1 of 5 |
| ORCID on mention | 0000-0002-0412-1139 (OpenAlex-supplied) | 0000-0002-0412-1139 (OpenAlex-supplied) |
| OpenAlex author ID | A5034227509 | A5034227509 |
| Affiliation | ROR 05x2bcf33 | ROR 05x2bcf33 |
| Work title | A large scale analysis of hundreds of in-memory cache clusters at Twitter | FIFO queues are all you need for cache eviction |
| Year | 2020 | 2023 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4306420989 |
| DOI | — | 10.1145/3600006.3613147 |
| Coauthors | Yao Yue, K. V. Rashmi | Yazhuo Zhang, Ziyue Qiu, Yao Yue, Rashmi Vinayak |

_helper: shared coauthor normalizedNames = ['yao yue']_
_helper: target-mention ROR A=['05x2bcf33'] B=['05x2bcf33'] shared=['05x2bcf33']_

**AI-proposed label: `same`**

**Note:** Both mentions are first author "Juncheng Yang" with shared coauthor Yao Yue, the same affiliation ROR 05x2bcf33, and a consistent caching topic (Twitter in-memory cache clusters 2020; FIFO cache eviction 2023).

**Supporting evidence:**
- Name exact match at author#1 in both
- Shared coauthor in payload: Yao Yue (A#2, B#4)
- enrichment ror=05x2bcf33 on both target mentions
- Topic continuity: cache systems
- Same OpenAlex-supplied observedOrcid 0000-0002-0412-1139 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A third coauthor appears as "K. V. Rashmi" vs "Rashmi Vinayak"; not treated as a confirmed match
- A work has no DOI

<details><summary>Evidence references</summary>

- A `work` `er-evidence:1a1d361d247b62e78fd5d23790b0abf8f40069e5b5ba926d6213ad2161d2d47a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:245`
- A `enrichment` `er-evidence:fd4535e037611f2f35484e13b15908ecea42eebaa8cceefbc6b8227e8745e533` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2662`
- B `work` `er-evidence:117ae26e9e2407afc482701da784b6e93d0135b3bd5a59361a0ad6194bd2f8dd` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:74`
- B `enrichment` `er-evidence:a51a457877dacbf51ae73cf460296139b0875947995dd9de557ab0e13f75b6c2` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:820`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 32 — Researcher

- **pairId:** `resolution-pair:2c225ee91f580a826eccb1b6be0e05b0694ce6e79c7c51963a05ae2fd408c495`
- **evidenceHash:** `23b943b9ce9931ddd397129509312683878922a228212e59b9ad7ed258ec5ca0`
- **Question:** do mention A `mention:openalex:W2952570284#5` and B `mention:openalex:W3028571058#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2952570284#5 | mention:openalex:W3028571058#2 |
| Name as written | Byron Choi | Byron Choi |
| Author position | 5 of 5 | 2 of 6 |
| ORCID on mention | 0000-0002-8381-336X (OpenAlex-supplied) | 0000-0002-8381-336X (OpenAlex-supplied) |
| OpenAlex author ID | A5052275926 | A5052275926 |
| Affiliation | ROR 0145fw131 | ROR 0145fw131 |
| Work title | GEM^2-Tree: A Gas-Efficient Structure for Authenticated Range Queries in Blockchain | Efficient Shapelet Discovery for Time Series Classification |
| Year | 2019 | 2020 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S30698027 |
| DOI | 10.1109/icde.2019.00080 | 10.1109/tkde.2020.2995870 |
| Coauthors | Ce Zhang, Cheng Xu, Jianliang Xu, Yuzhe Tang | Guozhong Li, Jianliang Xu, Sourav S Bhowmick, Kwok-Pan Chun, Grace Lai-Hung Wong |

_helper: shared coauthor normalizedNames = ['jianliang xu']_
_helper: target-mention ROR A=['0145fw131'] B=['0145fw131'] shared=['0145fw131']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Byron Choi" with shared coauthor Jianliang Xu (A#3, B#3) and the same affiliation ROR 0145fw131 in 2019 and 2020.

**Supporting evidence:**
- Name exact match: A author#5, B author#2
- Shared coauthor in payload: Jianliang Xu
- enrichment ror=0145fw131 on both target mentions
- Same OpenAlex-supplied observedOrcid 0000-0002-8381-336X (provider hypothesis only)

**Conflicting evidence:**
- Topics differ: blockchain authenticated range queries (ICDE 2019) vs time-series shapelet discovery (TKDE 2020)

**Limitations / missing information:**
- Coauthor and affiliation overlap are correlated (colleagues at one institution)
- All hints OpenAlex-derived

<details><summary>Evidence references</summary>

- A `work` `er-evidence:34126b2ca887d3b53acbace76cea632036414c45fe050a7bd4b71a56718f5303` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:335`
- A `enrichment` `er-evidence:9b3dd75fab00f94c75bdd18ce0d5cd095a92ac624a53569cd4157f9cac05af54` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3510`
- B `work` `er-evidence:012afe8ea62f3163d4bdf25b71db8bb077d18c5fe9aa0e41ea36c5b47323ee4f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:288`
- B `enrichment` `er-evidence:d502aa4b24955e0d808f647562e9185929a4bff9c41d414042ad875110040c23` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3087`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 33 — Work

- **pairId:** `resolution-pair:a4a1c668c2809676465aaed9ba32ddae4e7df55067f93824e033c05bdc8bf59c`
- **evidenceHash:** `3ba17ffec1cb29559d21bff2037adcc9862c74c9e27428e4ecd926b5f633006d`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3111141572 (article) | OPENALEX W4388041408 (conference-paper) |
| Title | Are we ready for learned cardinality estimation? | Golgi |
| Year | 2021 | 2023 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S7407088165 |
| DOI | 10.14778/3461535.3461552 | 10.1145/3620678.3624645 |
| arXiv ID | — | — |
| Pages | 1640-1654 | 32-47 |
| Authors | (5) Xiaoying Wang, Changbo Qu, Weiyuan Wu, Jiannan Wang, Qingqing Zhou | (5) Suyi Li, Wei Wang, Jun Yang, Guangzhen Chen, Daohe Lu |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3461535.3461552, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3461535.3461552, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3620678.3624645, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3620678.3624645, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3461535.3461552'] B=['10.1145/3620678.3624645'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Are we ready for learned cardinality estimation?" (10.14778/3461535.3461552, 2021) and B "Golgi" (10.1145/3620678.3624645, 2023) have distinct DOIs, different titles, years and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2021 vs 2023
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:e5eed6d11e250dfcb296a2d89aca2347a76fc33984dc86aef3030a48a0bece11` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:225`
- B `work` `er-evidence:abeeb930f85f1b7fc3801805c6f14255864fd38868568e3b5d843b23d82f9aa5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:60`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 34 — Work

- **pairId:** `resolution-pair:89236790cec6497d18bbfba617ce9f6d872465a2347ac2aa1d06a8d43f02e2b7`
- **evidenceHash:** `ed2fb6b8498ba46dcb3cab4e29c7715b2b2d8ae46d9177b06b1ad7257dc888f5`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W4380433181 (article) | OPENALEX W4404181268 (article) |
| Title | Foreign Keys Open the Door for Faster Incremental View Maintenance | Vector Databases: What's Really New and What's Next? (VLDB 2024 Panel) |
| Year | 2023 | 2024 |
| Venue ID | venue:openalex:S4387289859 | venue:openalex:S4210226185 |
| DOI | 10.1145/3588720 | 10.14778/3685800.3685911 |
| arXiv ID | — | — |
| Pages | 1-25 | 4505-4506 |
| Authors | (5) Christoforos Svingos, Andre Hernich, Hinnerk Gildhoff, Yannis Papakonstantinou, Yannis Ioannidis | (6) Jianguo Wang, Eric Hanson, Guoliang Li, Yannis Papakonstantinou, Harsha Simhadri, Charles Xie |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3588720, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3588720, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.14778/3685800.3685911, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3685800.3685911, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3588720'] B=['10.14778/3685800.3685911'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Foreign Keys Open the Door for Faster Incremental View Maintenance" (10.1145/3588720, 2023) and B "Vector Databases: What's Really New and What's Next? (VLDB 2024 Panel)" (10.14778/3685800.3685911, 2024) have distinct DOIs and different titles; only Yannis Papakonstantinou is shared.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2023 vs 2024; venueId S4387289859 vs S4210226185

**Conflicting evidence:**
- Shared author name Yannis Papakonstantinou

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:d4b54e6e69b33827fb487f07b1bfb6ed4697de4deb5866a75f593163c6406c41` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:99`
- B `work` `er-evidence:3e3027f65e52c1070a9f5742ebc0d39c488f84fa00f99432ed40720040417d63` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:13`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 35 — Researcher

- **pairId:** `resolution-pair:70e2eb0bce1c8a1a045362024d6f1561014689a97249e040d39013978fda2d67`
- **evidenceHash:** `8341b5e6110515d593a11c9a2afb01ff61684677948297d17d9d895ce6cb97f6`
- **Question:** do mention A `mention:openalex:W3097411828#2` and B `mention:openalex:W3176367300#8` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3097411828#2 | mention:openalex:W3176367300#8 |
| Name as written | Sameer G Kulkarni | Sanjeev R. Kulkarni |
| Author position | 2 of 3 | 8 of 9 |
| ORCID on mention | 0000-0003-4727-6875 (OpenAlex-supplied) | 0000-0002-5308-5250 (OpenAlex-supplied) |
| OpenAlex author ID | A5081037214 | A5053530986 |
| Affiliation | ROR 0036p5w23 | ROR 00hx57361 |
| Work title | GSLICE | Enabling Efficient Cyber Threat Hunting With Cyber Threat Intelligence |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210210321 |
| DOI | 10.1145/3419111.3421284 | 10.1109/icde51399.2021.00024 |
| Coauthors | Aditya Dhakal, K. K. Ramakrishnan | Peng Gao, Fei Shao, Xiaoyuan Liu, Xusheng Xiao, Zheng Qin, Fengyuan Xu, Prateek Mittal, Dawn Song |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['0036p5w23'] B=['00hx57361'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#2 "Sameer G Kulkarni" and B author#8 "Sanjeev R. Kulkarni" differ in both given name and middle initial (G vs R); only the surname is shared, with no common coauthors.

**Supporting evidence:**
- nameText given name differs: "Sameer" vs "Sanjeev"; middle initial G vs R
- No shared coauthors
- enrichment ror differs: 0036p5w23 vs 00hx57361
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:43f0b7f448b38d6f1f40bf066b66bebe4b948f072c6f3452f0ff80cf397e6cd0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2560`
- A `work` `er-evidence:8675363d5404e5d2ec42e47141318330f6c3f317fbba66348561206adcf5af6a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:235`
- B `enrichment` `er-evidence:7c05c4587016c95cb78f2c465ac1beaf1481b6d39a55ce50106f1e06a09730d5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2101`
- B `work` `er-evidence:fd7de9e0fc8f9fdd0efbb16cd0626216a4ca465e983e9bdebd0adfdfd1228f3c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:191`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 36 — Work

- **pairId:** `resolution-pair:60d9439a93eac87601cf3930e5bb85faf88817e06b689d5c09bf69f7c6b16b11`
- **evidenceHash:** `b61ccd104c1ab973f781eae09ebc0b5ab4cbf89285e73911127419d60ad689ef`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W4379390733 (conference-paper) | OPENALEX W4399208468 (article) |
| Title | DataChat: An Intuitive and Collaborative Data Analytics Platform | ReAcTable: Enhancing ReAct for Table Question Answering |
| Year | 2023 | 2024 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210226185 |
| DOI | 10.1145/3555041.3589678 | 10.14778/3659437.3659452 |
| arXiv ID | — | — |
| Pages | 203-215 | 1981-1994 |
| Authors | (9) Rogers Jeffrey Leo John, Dylan Bacon, Junda Chen, Ushmal Ramesh, Jiatong Li, Deepan Das, Robert Claus, Amos Kendall, Jignesh M. Patel | (6) Yunjia Zhang, Jordan Henkel, Avrilia Floratou, Joyce Cahoon, Shaleen Deep, Jignesh M. Patel |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3555041.3589678, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3555041.3589678, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.14778/3659437.3659452, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3659437.3659452, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3555041.3589678'] B=['10.14778/3659437.3659452'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "DataChat: An Intuitive and Collaborative Data Analytics Platform" (10.1145/3555041.3589678, 2023) and B "ReAcTable: Enhancing ReAct for Table Question Answering" (10.14778/3659437.3659452, 2024) have distinct DOIs and different titles; only Jignesh M. Patel is shared.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2023 vs 2024
- Only 1 of 9/6 author names shared

**Conflicting evidence:**
- Shared author Jignesh M. Patel

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:0650b9b9ec9010e88135cea716faa7f1c954838ee55b425c2da79ce5f3c3ef28` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:102`
- B `work` `er-evidence:09e72a62d54e4d484b1d1f4aaf8fd5dddabffab756c429ee127095b324fd61fd` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:36`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 37 — Work

- **pairId:** `resolution-pair:09f1c20ba484a2051489b650ed3fcad8203a9bce3eed9788d26cf13f0996d3e2`
- **evidenceHash:** `0a69f91f0a2c1b1421d6a40855408416eda437fe55ee39facfee63ab48b55b8c`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2991530444 (article) | OPENALEX W4400910543 (conference-paper) |
| Title | Deep unsupervised cardinality estimation | MergeSFL: Split Federated Learning with Feature Merging and Batch Size Regulation |
| Year | 2019 | 2024 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210210321 |
| DOI | 10.14778/3368289.3368294 | 10.1109/icde60146.2024.00164 |
| arXiv ID | — | — |
| Pages | 279-292 | 2054-2067 |
| Authors | (10) Zongheng Yang, Eric Liang, Amog Kamsetty, Chenggang Wu, Yan Duan, Xi Chen, Pieter Abbeel, Joseph M. Hellerstein, Sanjay Krishnan, Ion Stoica | (6) Yunming Liao, Yang Xu, Hongli Xu, Lun Wang, Zhiwei Yao, Chunming Qiao |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3368289.3368294, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3368289.3368294, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1109/icde60146.2024.00164, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde60146.2024.00164, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3368289.3368294'] B=['10.1109/icde60146.2024.00164'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Deep unsupervised cardinality estimation" (10.14778/3368289.3368294, 2019) and B "MergeSFL: Split Federated Learning with Feature Merging…" (10.1109/icde60146.2024.00164, 2024) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2019 vs 2024
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:aa92f3cda1b44cc864a6941540bce151b2e9915074a493e2f361783f4f6d1040` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:305`
- B `work` `er-evidence:dfb7129687ca2f2d61dacab0a8d6e3e67a57f7881a02823a93ec2e4364654ed3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:22`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 38 — Work

- **pairId:** `resolution-pair:6345f19232ebe2473bbf9674bcb3078f2ad62140f7a911eaf3fe7453edc316e6`
- **evidenceHash:** `d1692851c1840e338e6f169f89f0370366e21f07df11ada74c995da82426e579`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W4379390584 (conference-paper) | OPENALEX W4381326861 (article) |
| Title | An Overview of Reachability Indexes on Graphs | PG-Schema: Schemas for Property Graphs |
| Year | 2023 | 2023 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4387289859 |
| DOI | 10.1145/3555041.3589408 | 10.1145/3589778 |
| arXiv ID | — | — |
| Pages | 61-68 | 1-25 |
| Authors | (3) Chao Zhang, Angela Bonifati, M. Tamer Özsu | (21) Renzo Angles, Angela Bonifati, Stefania Dumbrava, George Fletcher, Alastair Green, Jan Hidders, Bei Li, Leonid Libkin, Victor Marsault, Wim Martens, Filip Murlak, Stefan Plantikow, Ognjen Savkovic, Michael Schmidt, Juan Sequeda … (+6 more) |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3555041.3589408, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3555041.3589408, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3589778, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3589778, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3555041.3589408'] B=['10.1145/3589778'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "An Overview of Reachability Indexes on Graphs" (10.1145/3555041.3589408, 3 authors) and B "PG-Schema: Schemas for Property Graphs" (10.1145/3589778, 21 authors) are both 2023 but have distinct DOIs and different titles; only Angela Bonifati is shared.

**Supporting evidence:**
- work.doi distinct
- work.title different
- venueId S4393915683 vs S4387289859; pages 61-68 vs 1-25

**Conflicting evidence:**
- Same year 2023; shared author Angela Bonifati

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:54e9f1ba3478f316e85ba21ad6cb6ddcb9f52689d03816ddf94530150fb65efc` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:105`
- B `work` `er-evidence:3aebf9384d47efd5daac4e2bc465ca4d8d9550b7d1e463ad7ba06c50b0ba0b04` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:98`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 39 — Researcher

- **pairId:** `resolution-pair:5594b59eeb970624a6496f053029a6ba88744733fb6acf61bb99dc2e40d376db`
- **evidenceHash:** `c0c091a2ff10d7e4385edf4d7b1eb5fe873c2bb9a975f095d1c3673de9170e0f`
- **Question:** do mention A `mention:openalex:W3097213700#4` and B `mention:openalex:W3159219445#5` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3097213700#4 | mention:openalex:W3159219445#5 |
| Name as written | Gustavo Alonso | Gustavo Alonso |
| Author position | 4 of 4 | 5 of 9 |
| ORCID on mention | 0000-0002-4396-6695 (OpenAlex-supplied) | 0000-0002-4396-6695 (OpenAlex-supplied) |
| OpenAlex author ID | A5103144919 | A5103144919 |
| Affiliation | ROR 05a28rw58 | ROR 05a28rw58 |
| Work title | Photons | Towards Demystifying Serverless Machine Learning Training |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4393915683 |
| DOI | 10.1145/3419111.3421297 | 10.1145/3448016.3459240 |
| Coauthors | Vojislav Dukic, Rodrigo Bruno, Ankit Singla | Jiawei Jiang, Shaoduo Gan, Yue Liu, Fanlin Wang, Ana Klimovic, Ankit Singla, Wentao Wu, Ce Zhang |

_helper: shared coauthor normalizedNames = ['ankit singla']_
_helper: target-mention ROR A=['05a28rw58'] B=['05a28rw58'] shared=['05a28rw58']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Gustavo Alonso" with shared coauthor Ankit Singla (A#3, B#7) and the same affiliation ROR 05a28rw58 in 2020 and 2021.

**Supporting evidence:**
- Name exact match: A author#4, B author#5
- Shared coauthor in payload: Ankit Singla
- enrichment ror=05a28rw58 on both target mentions
- Same OpenAlex-supplied observedOrcid 0000-0002-4396-6695 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A work title "Photons" gives little topic context
- Coauthor and affiliation overlap are correlated

<details><summary>Evidence references</summary>

- A `work` `er-evidence:4c10e30909e5507e91219579f3af4a39ea21f7aa0a429662e98b1ad45e0b881e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:237`
- A `enrichment` `er-evidence:9b6266e174fe9ccb8942632b73d17231b775fc55c24747d87d4d78a7a5ca6adc` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2577`
- B `enrichment` `er-evidence:01f4beb961fdcc77b7f935760587e18f5719907a9001d0d3ef58672e6cd060b5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2350`
- B `work` `er-evidence:b593359758c550f5d4a88e9164918614ab8c0f34ddaa6ab49dcac7f87d6e3f5c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:215`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 40 — Researcher

- **pairId:** `resolution-pair:ab9722a3c84211a9c05689676954f03375472f663ae8f4f3e024b5c24fa97a2f`
- **evidenceHash:** `fb9d12de0a2240530a0fb700679eb027ae4aaab49352787860b74bcd8de0c7a8`
- **Question:** do mention A `mention:crossref:10.1145/3299887.3299900#2` and B `mention:openalex:W4360825594#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:crossref:10.1145/3299887.3299900#2 | mention:openalex:W4360825594#3 |
| Name as written | Xiaokui Xiaokui Xiao | Xiaokui Xiao |
| Author position | 2 of 2 | 3 of 6 |
| ORCID on mention | — | 0000-0003-0914-4580 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5010903591 |
| Affiliation | "Nanyang Technological University, Nanyang, Singapore" | ROR 01tgyzw49 |
| Work title | DANTE | PANE: scalable and effective attributed network embedding |
| Year | 2018 | 2023 |
| Venue ID | venue:issn:0163-5808 | venue:openalex:S78926909 |
| DOI | 10.1145/3299887.3299900 | 10.1007/s00778-023-00790-4 |
| Coauthors | Sourav S. Bhowmick | Renchi Yang, Jieming Shi, Yin Yang, Sourav S. Bhowmick, Juncheng Liu |

_helper: shared coauthor normalizedNames = ['sourav s. bhowmick']_
_helper: target-mention ROR A=- B=['01tgyzw49'] shared=none_

**AI-proposed label: `uncertain`**

**Note:** Both mentions share the coauthor Sourav S. Bhowmick, but A's Crossref nameText is the irregular "Xiaokui Xiaokui Xiao" and the affiliations cannot be compared (A organizationName "Nanyang Technological University…" vs B ROR 01tgyzw49); one coauthor overlap plus a name is not enough here.

**Supporting evidence:**
- Shared coauthor in payload: Sourav S. Bhowmick (A#1, B#5)
- Name compatible: "Xiaokui Xiao" vs "Xiaokui Xiaokui Xiao" (apparent duplicated given name)

**Conflicting evidence:**
- A nameText duplicates the given name, so the source string is irregular

**Limitations / missing information:**
- Affiliation forms are not comparable (name string vs ROR id without a name)
- Topics not clearly linked: "DANTE" (SIGMOD Record 2018) vs attributed network embedding (2023)
- B observedOrcid 0000-0003-0914-4580 is OpenAlex-supplied only

<details><summary>Evidence references</summary>

- A `mention-affiliation` `er-evidence:337e5265b9f5b64f4da5d0db0cd35159c5d69c544cd31150833d01bd2a09d178` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/mention-affiliation/part-r-00000:40`
- A `work` `er-evidence:690d131b6af699b1f16bff88ab11c81b14fbd5b45d538e17840e146128ff4308` — `snapshot=crossref-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:10`
- B `work` `er-evidence:203a524ad32ea677d5928b454e4343598ddbb2165dca19f7fd843a7c0db2689b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:117`
- B `enrichment` `er-evidence:ccb6b127594cbfefc82376ad6c8847a9e2ebc12b15f35a0ac627be604771d04a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1286`

</details>

**Danny's decision:** ☐ same ☐ different ☑ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: DANTE is in ORCID 0000-0003-0914-4580 (Xiaokui Xiao), but PANE 2023 is not, and Semantic Scholar files PANE under a separate "X. Xiao" profile. Switched same -> uncertain because no source links both papers to one person.

---
