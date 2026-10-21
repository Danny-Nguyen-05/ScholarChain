# ScholarChain AI review drafts — batch 09 (tasks 161–180)

> **Status: AI_SUGGESTIONS_PENDING_HUMAN_REVIEW.** These are AI-generated suggestions from a session-reported `claude-opus-5-5` model (not independently verified). They are not human reviews or gold labels. Record your own decision in each task's decision box; an empty box means not reviewed.

Queue: `review-queue:05c5817f62a70d378829be361b9c9169fc9af18448f7c83c245f1d65bbca6175`  
Work tasks: 12 · Researcher tasks: 8

Rows marked `>> … <<` in the raw data and the 'Name as written' row identify the mention being compared. OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider hypotheses. Lines in _italics_ starting with 'helper:' are exact-string comparisons computed by a script to help reading; they are not judgments.

---
## Task 161 — Researcher

- **pairId:** `resolution-pair:01a3c608058966b8dc730ece260dd5f6d9101cc9b9da1c6117e5ba31cac464a9`
- **evidenceHash:** `1fee663f96fe790d93e4e65a6d991cd02a7405bfe6ef03e099575904c42c32bc`
- **Question:** do mention A `mention:openalex:W2794566778#3` and B `mention:openalex:W3109841242#9` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2794566778#3 | mention:openalex:W3109841242#9 |
| Name as written | Yin Yang | Yupu Yang |
| Author position | 3 of 7 | 9 of 11 |
| ORCID on mention | 0000-0002-0549-3882 (OpenAlex-supplied) | — |
| OpenAlex author ID | A5034022345 | — |
| Affiliation | ROR 03eyq4y97 | ROR 0220qvk04 |
| Work title | PrivTrie: Effective Frequent Term Discovery under Local Differential Privacy | APAN: Asynchronous Propagation Attention Network for Real-time Temporal Graph Embedding |
| Year | 2018 | 2021 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4393915683 |
| DOI | 10.1109/icde.2018.00079 | 10.1145/3448016.3457564 |
| Coauthors | Ning Wang, Xiaokui Xiao, Ta Duy Hoang, Hyejin Shin, Junbum Shin, Ge Yu | Xuhong Wang, Ding Lyu, Mengjian Li, Yang Xia, Qi Yang, Xinwen Wang, Xinguang Wang, Ping Cui, Bowen Sun, Zhenyu Guo |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['03eyq4y97'] B=['0220qvk04'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#3 "Yin Yang" and B author#9 "Yupu Yang" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Yin" vs "Yupu"
- No shared coauthors
- enrichment ror differs: 03eyq4y97 vs 0220qvk04

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B mention has no ORCID

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:39320ca50985bcf7c4250104936fc4dc64c4d87cd65ef19d7867ef793ddc892b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4428`
- A `work` `er-evidence:78249ba973652ca03a8f37118169ebe7a56eae159f650cf1c06ac5f4a50f40c7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:436`
- B `work` `er-evidence:315df73c446e94772b2a939cfcb468a83c73a87d68920076a45ce79129dce0f3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:227`
- B `enrichment` `er-evidence:df1d995f942206c61992b3a8ad8c62be53ade64e4fe6a38161e3a3b39b4b159f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2467`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 162 — Researcher

- **pairId:** `resolution-pair:89505642895d2ed6f81019ac9d94262ad9ee3059d986b1914159313e1e756453`
- **evidenceHash:** `68a74831280cbe07e316a7fc9221d9cb71ae643fea40af8f6841dc2f36a2c7fa`
- **Question:** do mention A `mention:openalex:W2999832078#3` and B `mention:openalex:W3049595782#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2999832078#3 | mention:openalex:W3049595782#4 |
| Name as written | Gang Chen | Gang Chen |
| Author position | 3 of 15 | 4 of 5 |
| ORCID on mention | 0000-0002-3711-4250 (OpenAlex-supplied) | — |
| OpenAlex author ID | A5046439009 | — |
| Affiliation | ROR 00a2xv884 | ROR 00a2xv884 |
| Work title | The Disruptions of 5G on Data-Driven Technologies and Applications | Privacy preserving vertical federated learning for tree-based models |
| Year | 2020 | 2020 |
| Venue ID | venue:openalex:S30698027 | venue:openalex:S4210226185 |
| DOI | 10.1109/tkde.2020.2967670 | 10.14778/3407790.3407811 |
| Coauthors | Dumitrel Loghin, Shaofeng Cai, Tien Tuan Anh Dinh, Feiyi Fan, Qian Lin, Janice Ng, Beng Chin Ooi, Xutao Sun, Quang-Trung Ta, Wei Wang, Xiaokui Xiao, Yang Yang, Meihui Zhang, Zhonghua Zhang | Yuncheng Wu, Shaofeng Cai, Xiaokui Xiao, Beng Chin Ooi |

_helper: shared coauthor normalizedNames = ['beng chin ooi', 'shaofeng cai', 'xiaokui xiao']_
_helper: target-mention ROR A=['00a2xv884'] B=['00a2xv884'] shared=['00a2xv884']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Gang Chen" in 2020 papers sharing three coauthors (Shaofeng Cai, Xiaokui Xiao, Beng Chin Ooi) and the same ROR 00a2xv884.

**Supporting evidence:**
- Name exact match: A author#3, B author#4
- Three shared coauthors
- enrichment ror=00a2xv884 on both target mentions
- Same year 2020

**Conflicting evidence:**
- Topics differ: 5G and data-driven technologies (survey) vs vertical federated learning

**Limitations / missing information:**
- "Gang Chen" is a common name
- B mention has no ORCID; A observedOrcid is OpenAlex-supplied only

<details><summary>Evidence references</summary>

- A `work` `er-evidence:6c0b33388e2251485298030b2bf5668a67f68cba6d263bf25331c4c56a0c6c7b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:302`
- A `enrichment` `er-evidence:c94c9f2961538ff86acdf29e52b9d5d56ce6957b2ee41fe55e29c93b3df4c3b3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3211`
- B `enrichment` `er-evidence:17e7a9a04fa0fa7a82621e2e1745f4bde8d4866f4901aef33f2be41efaaf19fa` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2865`
- B `work` `er-evidence:5827c73c0b8de9f6830a983e69817bc6080f425cc20ea20dbc32021a83e863f2` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:262`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 163 — Work

- **pairId:** `resolution-pair:c26f02ebf8274b7d4d42bfc69a493bbdfa116d9c9898748c25300696fd9943fd`
- **evidenceHash:** `0c20410067423977a470438ce3b5b6268cfb16d2d1fa0a11efa4779437aecb6c`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3095227533 (article) | OPENALEX W4312750676 (article) |
| Title | Twine: A Unified Cluster Management System for Shared Infrastructure | Volume under the surface |
| Year | 2020 | 2022 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210226185 |
| DOI | — | 10.14778/3551793.3551830 |
| arXiv ID | — | — |
| Pages | 787-803 | 2774-2787 |
| Authors | (20) Chunqiang Tang, Kenny Yu, Kaushik Veeraraghavan, Jonathan Kaldor, Scott Michelson, Thawan Kooburat, Aravind Anbudurai, Matthew Clark, Kabir Gogia, Long Cheng, Ben Christensen, Alex Gartrell, Maxim Khutornenko, Sachin Kulkarni, Marcin Pawłowski … (+5 more) | (6) John Paparrizos, Paul Boniol, Themis Palpanas, Ruey S. Tsay, Aaron Elmore, Michael J. Franklin |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.14778/3551793.3551830, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3551793.3551830, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.14778/3551793.3551830'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Twine: A Unified Cluster Management System for Shared Infrastructure" (no DOI, 2020) and B "Volume under the surface" (10.14778/3551793.3551830, 2022) have different titles, years, venues and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2020 vs 2022
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:89c723a4492d89040048728e01108ac1620308c9f1ddb4728304675c3e7d5bb0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:249`
- B `work` `er-evidence:5497cbe00f66e94be2650e88bed6d07ff438d155c7b3f3529c8d47be66b40ef6` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:121`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 164 — Work

- **pairId:** `resolution-pair:309501c27d6a2e3b05bf7c9c685699cca7de039c2fe47077a7b0d9115cf6e07a`
- **evidenceHash:** `697cd6f5742bc57463b0e26111c59a02d9a1f9bd11d6dd9f26e91d575c5a668f`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2897044322 (article) | OPENALEX W4400909749 (conference-paper) |
| Title | REPT: reverse debugging of failures in deployed software | CAGRA: Highly Parallel Graph Construction and Approximate Nearest Neighbor Search for GPUs |
| Year | 2018 | 2024 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210210321 |
| DOI | 10.5555/3291168.3291171 | 10.1109/icde60146.2024.00323 |
| arXiv ID | — | — |
| Pages | 17-32 | 4236-4247 |
| Authors | (7) Weidong Cui, Xinyang Ge, Baris Kasikci, Ben Niu, Upamanyu Sharma, Ruoyu Wang, Insu Yun | (6) Hiroyuki Ootomo, Akira Naruse, Corey Nolet, Ray Wang, Tamas Feher, Yong Wang |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.5555/3291168.3291171, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.5555/3291168.3291171, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1109/icde60146.2024.00323, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde60146.2024.00323, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.5555/3291168.3291171'] B=['10.1109/icde60146.2024.00323'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "REPT: reverse debugging of failures in deployed software" (10.5555/3291168.3291171, 2018) and B "CAGRA: Highly Parallel Graph Construction…" (10.1109/icde60146.2024.00323, 2024) have distinct DOIs, unrelated titles and disjoint authors.

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

- A `work` `er-evidence:85ad07193da71efc6d54a839e20e910917fe1c9a5ee24544bc6ab534dd607e1c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:386`
- B `work` `er-evidence:1bf5bf18fdd700f45ad7266e084cc85448ca79dc7a483fdc361cb436d6c35685` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:29`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 165 — Researcher

- **pairId:** `resolution-pair:cc1def86f56c13fcad6c3c014c4dc956c2936fabbd395a9339ccb2356c2a19c1`
- **evidenceHash:** `618fa5e155b2df3a3a87c4c4025b01238cf3fa9240716e19ee3774960cd3f859`
- **Question:** do mention A `mention:openalex:W2797862701#8` and B `mention:openalex:W2970773487#7` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2797862701#8 | mention:openalex:W2970773487#7 |
| Name as written | Cherry Li Zhang | Ce Zhang |
| Author position | 8 of 20 | 7 of 9 |
| ORCID on mention | — | 0000-0002-8105-7505 (OpenAlex-supplied) |
| OpenAlex author ID | A5109394206 | A5004750246 |
| Affiliation | ROR 01ek73717 | ROR 05a28rw58 |
| Work title | BigDL | Efficient task-specific data valuation for nearest neighbor algorithms |
| Year | 2019 | 2019 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210226185 |
| DOI | 10.1145/3357223.3362707 | 10.14778/3342263.3342637 |
| Coauthors | Jason Jinquan Dai, Yiheng Wang, Xin Qiu, Ding Ding, Yao Zhang, Yanzhang Wang, Xianyan Jia, Yan Wan, Zhichao Li, Jiao Wang, Shengsheng Huang, Zhongyuan Wu, Yang Wang, Yuhao Yang, Bowen She, Dongjie Shi, Qi Lu, Kai Huang, Guoqiong Song | Ruoxi Jia, David Dao, Boxin Wang, Frances Ann Hubis, Nezihe Merve Gurel, Bo Li, Costas Spanos, Dawn Song |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01ek73717'] B=['05a28rw58'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#8 "Cherry Li Zhang" and B author#7 "Ce Zhang" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Cherry Li" vs "Ce"
- No shared coauthors
- enrichment ror differs: 01ek73717 vs 05a28rw58

**Conflicting evidence:**
- Same year 2019

**Limitations / missing information:**
- A mention has no ORCID

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:39ad2b2eae9e457864c8ec5ffc694490096fcc17d440be60955a61854ae461f5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4301`
- A `work` `er-evidence:7f23ff95eec85ee7e1670f4b0e01e515a25005e60fdf9568ca996325d47d0dc5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:422`
- B `work` `er-evidence:03ef2208aa7734a65889ae31546d72edf8c84050607e61b7e9aa7486493c3ba4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:325`
- B `enrichment` `er-evidence:f11c9b2f8b2a71fc9637ed99a4f39db659c94691bb2f9556f2aa0cc106311375` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3413`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 166 — Researcher

- **pairId:** `resolution-pair:04192cf62c78588b97283b2663b61ef273f48e66d6ed4c8ca334a30b6f12362a`
- **evidenceHash:** `c88b41561bcd41ebd7550c3f48e3d952c331e5bcd2f4de7c55669c50d4e092a6`
- **Question:** do mention A `mention:openalex:W3100228586#3` and B `mention:openalex:W4312357089#15` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3100228586#3 | mention:openalex:W4312357089#15 |
| Name as written | Jianyan Chen | Junquan Chen |
| Author position | 3 of 6 | 15 of 16 |
| ORCID on mention | — | 0000-0002-4353-9327 (OpenAlex-supplied) |
| OpenAlex author ID | A5036335737 | A5029292332 |
| Affiliation | ROR 047426m28 | — |
| Work title | Testing Configuration Changes in Context to Prevent Production Failures. | OceanBase |
| Year | 2020 | 2022 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210226185 |
| DOI | — | 10.14778/3554821.3554830 |
| Coauthors | Xudong Sun, Runxiang Cheng, Elaine Ang, Owolabi Legunsen, Tianyin Xu | Zhenkun Yang, Chuanhui Yang, Fusheng Han, Mingqiang Zhuang, Bing Yang, Zhifeng Yang, Xiaojun Cheng, Yuzhong Zhao, Wenhui Shi, Huafeng Xi, Huang Yu, Bin Liu, Yi Pan, Boxue Yin, Quanqing Xu |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['047426m28'] B=- shared=none_

**AI-proposed label: `different`**

**Note:** A author#3 "Jianyan Chen" and B author#15 "Junquan Chen" have different given names; no coauthor overlap.

**Supporting evidence:**
- nameText given names differ: "Jianyan" vs "Junquan"
- No shared coauthors

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no affiliation evidence; A has no ORCID

<details><summary>Evidence references</summary>

- A `work` `er-evidence:7b880d1ce3608084b75f700bbbe4c5a16e700a2f5c5d8d7ac4a6b04e6673e66b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:231`
- A `enrichment` `er-evidence:c70781dfe941ba953d7dd68fa8b481b6f4e792ef6cc63bcb6f36882fe8f2b486` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2515`
- B `work` `er-evidence:5fd523c89fec071c27aa59adf754e97b144a5f43ab00bbcb08a85578f0f84a23` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:123`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 167 — Work

- **pairId:** `resolution-pair:e5ca3ac118ffd0156677458ccc7f64f5aa3f340d7d44c569f4907358845e3875`
- **evidenceHash:** `8a68b518259ab43a422737ffeeafdb08837af849ba25370e3cdae89d3dc01750`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2951217911 (conference-paper) | OPENALEX W3174566165 (article) |
| Title | Social Influence-Based Group Representation Learning for Group Recommendation | Nap: A Black-Box Approach to NUMA-Aware Persistent Memory Indexes |
| Year | 2019 | 2021 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4306420647 |
| DOI | 10.1109/icde.2019.00057 | — |
| arXiv ID | — | — |
| Pages | 566-577 | 93-111 |
| Authors | (6) Hongzhi Yin, Qinyong Wang, Kai Zheng, Zhixu Li, Jiali Yang, Xiaofang Zhou | (4) Qing Wang, Youyou Lu, Junru Li, Jiwu Shu |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde.2019.00057, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde.2019.00057, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1109/icde.2019.00057'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Social Influence-Based Group Representation Learning for Group Recommendation" (DOI 10.1109/icde.2019.00057, 2019) and B "Nap: A Black-Box Approach to NUMA-Aware Persistent Memory Indexes" (no DOI, 2021) have unrelated titles and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2019 vs 2021
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:0ccdee0176c2d55656156cdd0a748ea8338c91d62d9a619bc0b43ce12c9aa5ef` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:339`
- B `work` `er-evidence:2873ea80b995b181f3d7d3bff511f82977a32037ec5af6e2ffa09aceaba2489e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:206`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 168 — Researcher

- **pairId:** `resolution-pair:83044b367a776177976aaadb83291e654467bfa70c971622547cb18635ca5398`
- **evidenceHash:** `fc699cd597ee41402e691eb5a13163409ca0b9853e8bcf52d4ea14c7e126b460`
- **Question:** do mention A `mention:openalex:W2963431420#2` and B `mention:openalex:W2999832078#12` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2963431420#2 | mention:openalex:W2999832078#12 |
| Name as written | Xiaokui Xiao | Xiaokui Xiao |
| Author position | 2 of 8 | 12 of 15 |
| ORCID on mention | — | 0000-0003-0914-4580 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5010903591 |
| Affiliation | ROR 01tgyzw49 | ROR 01tgyzw49 |
| Work title | Collecting and Analyzing Multidimensional Data with Local Differential Privacy | The Disruptions of 5G on Data-Driven Technologies and Applications |
| Year | 2019 | 2020 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S30698027 |
| DOI | 10.1109/icde.2019.00063 | 10.1109/tkde.2020.2967670 |
| Coauthors | Ning Wang, Yin Yang, Jun Zhao, Siu Cheung Hui, Hyejin Shin, Junbum Shin, Ge Yu | Dumitrel Loghin, Shaofeng Cai, Gang Chen, Tien Tuan Anh Dinh, Feiyi Fan, Qian Lin, Janice Ng, Beng Chin Ooi, Xutao Sun, Quang-Trung Ta, Wei Wang, Yang Yang, Meihui Zhang, Zhonghua Zhang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01tgyzw49'] B=['01tgyzw49'] shared=['01tgyzw49']_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Xiaokui Xiao" with ROR 01tgyzw49, but no coauthor is shared between the LDP paper (ICDE 2019) and the 15-author 5G survey (TKDE 2020); name plus affiliation alone stays below the agreed bar.

**Supporting evidence:**
- Name exact match: A author#2, B author#12
- enrichment ror=01tgyzw49 on both target mentions

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- A mention has no ORCID; B observedOrcid is OpenAlex-supplied only

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:deffd1c04bee22132d4e54b9f637ddec3c473e9394da3581b4dc985d06e52fe1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3448`
- A `work` `er-evidence:ec3e4de73bbb8fd85736344e239e8959865b9a4abff9cfd2df326339630b30b0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:329`
- B `enrichment` `er-evidence:389c0202b04f10e278ce1bdd0df327d5dd95520fe53766f384aa4db0c6240bad` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3208`
- B `work` `er-evidence:6c0b33388e2251485298030b2bf5668a67f68cba6d263bf25331c4c56a0c6c7b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:302`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Both DOIs are listed in ORCID record 0000-0003-0914-4580 (Xiaokui Xiao, pub.orcid.org) and Semantic Scholar assigns the same author ID on both papers (api.semanticscholar.org).

---

## Task 169 — Researcher

- **pairId:** `resolution-pair:7043e3f9d782d19896773046d640de2820383b1a8d9d6647ec1acb80ae34252d`
- **evidenceHash:** `728e2a84461cce5f6fe3170725855c54f5a0c94fdcec5c554ed6d9ef5c653f59`
- **Question:** do mention A `mention:openalex:W2773069775#1` and B `mention:openalex:W4293162637#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2773069775#1 | mention:openalex:W4293162637#1 |
| Name as written | Foto Afrati | Foto Afrati |
| Author position | 1 of 2 | 1 of 2 |
| ORCID on mention | — | — |
| OpenAlex author ID | A5088568415 | A5088568415 |
| Affiliation | ROR 03cx6bg69 | ROR 03cx6bg69 |
| Work title | Answering Queries Using Views | Query Containment and Equivalence |
| Year | 2019 | 2019 |
| Venue ID | venue:openalex:S982029923 | venue:openalex:S982029923 |
| DOI | 10.1007/978-3-031-01871-8_7 | 10.1007/978-3-031-01871-8_2 |
| Coauthors | Rada Chirkova | Rada Chirkova |

_helper: shared coauthor normalizedNames = ['rada chirkova']_
_helper: target-mention ROR A=['03cx6bg69'] B=['03cx6bg69'] shared=['03cx6bg69']_

**AI-proposed label: `same`**

**Note:** Both mentions are author#1 "Foto Afrati" on chapters of the same 2019 book (DOIs 10.1007/978-3-031-01871-8_7 and …_2, venue S982029923) with the same coauthor Rada Chirkova and ROR 03cx6bg69.

**Supporting evidence:**
- Name exact match at author#1
- Shared coauthor: Rada Chirkova (the only other author on both)
- Same book DOI prefix 10.1007/978-3-031-01871-8 and venueId
- enrichment ror=03cx6bg69 on both target mentions
- Same OpenAlex author id A5088568415 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- No ORCID on either mention

<details><summary>Evidence references</summary>

- A `work` `er-evidence:5a071cb834a5bc89ad9d20e30e1aa42167c68849aaa9dcfb6934a218abe323f7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:443`
- A `enrichment` `er-evidence:6f5a6d0e8c2df17ce761131d5d1ac10c1b62044102594cf86f4daa45447166ef` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4490`
- B `work` `er-evidence:18707ecb01208d0b8da58315fc1a85019e691e6f9be57b3328c67b5d1573bb8c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:128`
- B `enrichment` `er-evidence:33288c6a73e3f1cd0c0d0fd82230210da0de1842233af43cfd266e18862c636a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1376`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 170 — Work

- **pairId:** `resolution-pair:b788a3aeceaaa4cf334e3a1290cebccef7220ebdb65d6cde3bf2298e143b8008`
- **evidenceHash:** `260d521bafcda111c9e273e37151b9d486ab6d1a6d4f897278ace326b110f223`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3164254023 (article) | OPENALEX W3176147180 (article) |
| Title | Updatable learned index with precise positions | SONIC: Application-aware Data Passing for Chained Serverless Applications |
| Year | 2021 | 2021 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4306420647 |
| DOI | 10.14778/3457390.3457393 | — |
| arXiv ID | — | — |
| Pages | 1276-1288 | 973-988 |
| Authors | (6) Jiacheng Wu, Yong Zhang, Shimin Chen, Jin Wang, Yu Chen, Chunxiao Xing | (6) Ashraf Mahgoub, Karthick Shankar, Subrata Mitra, Ana Klimovic, Somali Chaterji, Saurabh Bagchi |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3457390.3457393, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3457390.3457393, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.14778/3457390.3457393'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Updatable learned index with precise positions" (DOI 10.14778/3457390.3457393) and B "SONIC: Application-aware Data Passing for Chained Serverless Applications" (no DOI) share only the year 2021; titles, venues and authors differ.

**Supporting evidence:**
- work.title unrelated
- venueId S4210226185 vs S4306420647
- work.authors disjoint

**Conflicting evidence:**
- Same year 2021

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:8267452962081e577b518d746f23c11e9dbbed831c494d5c8c538f00cd7adb06` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:214`
- B `work` `er-evidence:7d69e1dc64a8cc33f6576fe2fb237114230b3cd706958ff42233dd1c39389cfc` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:194`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 171 — Work

- **pairId:** `resolution-pair:72b245776dc15fdc0bf6d257cac311571cb63f3c07ddc450747c4b17a4ea01d0`
- **evidenceHash:** `c8e73db82b2db2dc2a4c22f78c9fed74c1a9dc935b42355b7288f93bfdea4d77`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3096140366 (article) | OPENALEX W4404386368 (conference-paper) |
| Title | LinnOS: Predictability on Unpredictable Flash Storage with a Light Neural Network | RomeFS: A CXL-SSD Aware File System Exploiting Synergy of Memory-Block Dual Paths |
| Year | 2020 | 2024 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S7407088165 |
| DOI | — | 10.1145/3698038.3698539 |
| arXiv ID | — | — |
| Pages | 173-190 | 720-736 |
| Authors | (6) Mingzhe Hao, Levent Toksoz, Nanqinqin Li, Edward Edberg Halim, Henry Hoffmann, Haryadi S. Gunawi | (7) Yekang Zhan, Haichuan Hu, Xiangrui Yang, Shaohua Wang, Qiang Cao, Hong Jiang, Jie Yao |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3698038.3698539, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3698038.3698539, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.1145/3698038.3698539'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "LinnOS: Predictability on Unpredictable Flash Storage with a Light Neural Network" (no DOI, 2020) and B "RomeFS: A CXL-SSD Aware File System…" (10.1145/3698038.3698539, 2024) have different titles, years and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2020 vs 2024
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:3b493ab6e68f7ad5746297452611542e02f06faa608fc7e9bdb92488793bff34` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:246`
- B `work` `er-evidence:d421b59cf2d89bbbae634c67cf9c1f785828faf6e5c68fd29e219506f40b85d9` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:2`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 172 — Researcher

- **pairId:** `resolution-pair:3d68ad856035770c23944aea204b97f2cf1503796e7f878ad9817f243e179a1a`
- **evidenceHash:** `320afd0b440ea377424f1a5e003116c716125f1723ecba9c39ccc018efdb9c9f`
- **Question:** do mention A `mention:openalex:W3030055324#1` and B `mention:openalex:W3093150360#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3030055324#1 | mention:openalex:W3093150360#2 |
| Name as written | Jiawei Zhang | Jingyuan Zhang |
| Author position | 1 of 3 | 2 of 6 |
| ORCID on mention | 0000-0003-4057-9400 (OpenAlex-supplied) | — |
| OpenAlex author ID | A5100462856 | — |
| Affiliation | ROR 05g3dte14 | ROR 02jqj7156 |
| Work title | FakeDetector: Effective Fake News Detection with Deep Diffusive Neural Network | Wukong |
| Year | 2020 | 2020 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S7407088165 |
| DOI | 10.1109/icde48307.2020.00180 | 10.1145/3419111.3421286 |
| Coauthors | Bowen Dong, Philip S. Yu | Benjamin Carver, Ao Wang, Ali Anwar, Panruo Wu, Yue Cheng |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['05g3dte14'] B=['02jqj7156'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#1 "Jiawei Zhang" and B author#2 "Jingyuan Zhang" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Jiawei" vs "Jingyuan"
- No shared coauthors
- enrichment ror differs: 05g3dte14 vs 02jqj7156

**Conflicting evidence:**
- Same year 2020

**Limitations / missing information:**
- B mention has no ORCID

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:5508a04f80566298615150d43e7acdd09923e9a906d2dee235fb6bb3f8170607` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2977`
- A `work` `er-evidence:d955d052d25a773315d36fd40c29469fd94e3f332c60a0f1d9a6b4d1443079e3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:275`
- B `enrichment` `er-evidence:16d18937d6b2591ee3e89e74cda93216c18a5247d8d0db45b2ac9376b31b5b59` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2755`
- B `work` `er-evidence:6c77b692abc917bba0450a486a0c8f4c190577093c28451fbc94494874b6b18a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:253`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 173 — Work

- **pairId:** `resolution-pair:ef1a232202dfbdf5e2c3bca71664809bc8f70db3e551e6b6743f6ad274a85ab2`
- **evidenceHash:** `3995e775d26a9c8e1488f1949d7a0f732b6509520f10580e0905e027ef205f12`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3096403968 (article) | OPENALEX W4286986033 (conference-paper) |
| Title | A Unified Architecture for Accelerating Distributed {DNN} Training in Heterogeneous GPU/CPU Clusters | Attentive Knowledge-aware Graph Convolutional Networks with Collaborative Guidance for Personalized Recommendation |
| Year | 2020 | 2022 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210210321 |
| DOI | — | 10.1109/icde53745.2022.00027 |
| arXiv ID | — | — |
| Pages | 463-479 | 299-311 |
| Authors | (6) Yimin Jiang, Yibo Zhu, Chang Lan, Bairen Yi, Yong Cui, Chuanxiong Guo | (6) Yankai Chen, Yaming Yang, Yujing Wang, Jing Bai, Xiangchen Song, Irwin King |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1109/icde53745.2022.00027, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde53745.2022.00027, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.1109/icde53745.2022.00027'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "A Unified Architecture for Accelerating Distributed {DNN} Training in Heterogeneous GPU/CPU Clusters" (no DOI, OSDI 2020) and B "Attentive Knowledge-aware Graph Convolutional Networks…" (10.1109/icde53745.2022.00027, 2022) have unrelated titles and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2020 vs 2022
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:682316e1575d30bb6248243025c502519d69748c728061def84d915746828cfe` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:244`
- B `work` `er-evidence:7a36ca63ae468ec3fa61e9c2a3122798fe7bf736ed706f90a3d07b467750cee8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:140`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 174 — Work

- **pairId:** `resolution-pair:8548441f3d9e762eb4a181b842f18cc21e9600661f354e60680fd631cf79b6d7`
- **evidenceHash:** `f0d5d26a06c1c8c6cfd887410c98346246b55bf6911a1a3822ee6be67f35d819`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3096403968 (article) | OPENALEX W4398234485 (conference-paper) |
| Title | A Unified Architecture for Accelerating Distributed {DNN} Training in Heterogeneous GPU/CPU Clusters | Data-Juicer: A One-Stop Data Processing System for Large Language Models |
| Year | 2020 | 2024 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4393915683 |
| DOI | — | 10.1145/3626246.3653385 |
| arXiv ID | — | — |
| Pages | 463-479 | 120-134 |
| Authors | (6) Yimin Jiang, Yibo Zhu, Chang Lan, Bairen Yi, Yong Cui, Chuanxiong Guo | (13) Daoyuan Chen, Yilun Huang, Zhijian Ma, Hesen Chen, Xuchen Pan, Ce Ge, Dawei Gao, Yuexiang Xie, Zhaoyang Liu, Jinyang Gao, Yaliang Li, Bolin Ding, Jingren Zhou |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3626246.3653385, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3626246.3653385, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.1145/3626246.3653385'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "A Unified Architecture for Accelerating Distributed {DNN} Training…" (no DOI, 2020) and B "Data-Juicer: A One-Stop Data Processing System for Large Language Models" (10.1145/3626246.3653385, 2024) have different titles, years and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2020 vs 2024
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:682316e1575d30bb6248243025c502519d69748c728061def84d915746828cfe` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:244`
- B `work` `er-evidence:3ec65fbdce7fa801921efcc3925c0e27481ca46581a2af702ea5f75020bda311` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:43`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 175 — Work

- **pairId:** `resolution-pair:a752d77bd75097eb93fcaf25f9c711615206b622ecf13af84d76cd253f3c1752`
- **evidenceHash:** `5c6978dfd2cc352cd830fc9a8a95c5940121cc016b22b6c196df6d3f9abff57a`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3096403968 (article) | OPENALEX W4391054939 (article) |
| Title | A Unified Architecture for Accelerating Distributed {DNN} Training in Heterogeneous GPU/CPU Clusters | ImDiffusion: Imputed Diffusion Models for Multivariate Time Series Anomaly Detection |
| Year | 2020 | 2023 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210226185 |
| DOI | — | 10.14778/3632093.3632101 |
| arXiv ID | — | — |
| Pages | 463-479 | 359-372 |
| Authors | (6) Yimin Jiang, Yibo Zhu, Chang Lan, Bairen Yi, Yong Cui, Chuanxiong Guo | (10) Yuhang Chen, Chaoyun Zhang, Minghua Ma, Yudong Liu, Ruomeng Ding, Bowen Li, Shilin He, Saravan Rajmohan, Qingwei Lin, Dongmei Zhang |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.14778/3632093.3632101, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3632093.3632101, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.14778/3632093.3632101'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "A Unified Architecture for Accelerating Distributed {DNN} Training…" (no DOI, 2020) and B "ImDiffusion: Imputed Diffusion Models for Multivariate Time Series Anomaly Detection" (10.14778/3632093.3632101, 2023) have different titles, years and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2020 vs 2023
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:682316e1575d30bb6248243025c502519d69748c728061def84d915746828cfe` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:244`
- B `work` `er-evidence:3563a3a7496f9d011a2d86b3de67a7bcd6d2682fc231eef6b4c7214563379d62` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:54`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 176 — Work

- **pairId:** `resolution-pair:1cffbebe535133c4d1579dac105b90bde998935c411ff8ed62230e1a645d3529`
- **evidenceHash:** `ecd0fe9791182c21acfdce2d81f3fa9b5e98b334553cfbd0fdcc9808133ae1b4`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2963452187 (conference-paper) | OPENALEX W3095227533 (article) |
| Title | Partitioned Data Security on Outsourced Sensitive and Non-Sensitive Data | Twine: A Unified Cluster Management System for Shared Infrastructure |
| Year | 2019 | 2020 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4306420647 |
| DOI | 10.1109/icde.2019.00064 | — |
| arXiv ID | — | — |
| Pages | 650-661 | 787-803 |
| Authors | (4) Sharad Mehrotra, Shantanu Sharma, Jeffrey Ullman, Anurag Mishra | (20) Chunqiang Tang, Kenny Yu, Kaushik Veeraraghavan, Jonathan Kaldor, Scott Michelson, Thawan Kooburat, Aravind Anbudurai, Matthew Clark, Kabir Gogia, Long Cheng, Ben Christensen, Alex Gartrell, Maxim Khutornenko, Sachin Kulkarni, Marcin Pawłowski … (+5 more) |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde.2019.00064, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde.2019.00064, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1109/icde.2019.00064'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Partitioned Data Security on Outsourced Sensitive and Non-Sensitive Data" (DOI 10.1109/icde.2019.00064, 2019) and B "Twine: A Unified Cluster Management System…" (no DOI, 2020) have unrelated titles and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2019 vs 2020
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:4e7897103fbaadf68f6b5d27fc900719af8561e32e3441ef08e34b637a20a4a7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:328`
- B `work` `er-evidence:89c723a4492d89040048728e01108ac1620308c9f1ddb4728304675c3e7d5bb0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:249`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 177 — Work

- **pairId:** `resolution-pair:fce991d0774325af3fe1b82ad85af20bee1795ba911c18337255287fa94cf943`
- **evidenceHash:** `cb7c9e0a150823e7d27fa60556f2e74ea7e2e7b4dc37298eee59283b0e97c720`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2899160556 (article) | OPENALEX W3176081047 (article) |
| Title | Pocket: elastic ephemeral storage for serverless analytics | The nanoPU: A Nanosecond Network Stack for Datacenters |
| Year | 2018 | 2021 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4306420647 |
| DOI | 10.5555/3291168.3291200 | — |
| arXiv ID | — | — |
| Pages | 427-444 | 239-256 |
| Authors | (6) Ana Klimovic, Yawen Wang, Patrick Stuedi, Animesh Trivedi, Jonas Pfefferle, Christos Kozyrakis | (7) Stephen Ibanez, Alex Mallery, Serhat Arslan, Theo Jepsen, Muhammad Shahbaz, Changhoon Kim, Nick McKeown |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.5555/3291168.3291200, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.5555/3291168.3291200, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.5555/3291168.3291200'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Pocket: elastic ephemeral storage for serverless analytics" (DOI 10.5555/3291168.3291200, OSDI 2018) and B "The nanoPU: A Nanosecond Network Stack for Datacenters" (no DOI, OSDI 2021) have different titles, years and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2018 vs 2021
- work.authors disjoint

**Conflicting evidence:**
- Same venueId S4306420647

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:2b949f0a51fc2bbff63428b639743e71a1363fb1bdfb4ba61de5cb2c4f710b5d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:377`
- B `work` `er-evidence:4511884fb6014a4cd0d412ce95cfd0fc559b4178356b3ac1240a451f9c47c1d3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:196`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 178 — Work

- **pairId:** `resolution-pair:25ce141f3f657b7e6e0105bb99365e9c5346c1eae0388d168bf60350ea4a457a`
- **evidenceHash:** `498e50cacc3bd01dba9fab1ce4da7932285ad8635b73e0ffbb5a7feb46960c92`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3173154111 (article) | OPENALEX W4396571402 (article) |
| Title | PET: Optimizing Tensor Programs with Partially Equivalent Transformations and Automated Corrections. | Text-to-SQL Empowered by Large Language Models: A Benchmark Evaluation |
| Year | 2021 | 2024 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210226185 |
| DOI | — | 10.14778/3641204.3641221 |
| arXiv ID | — | — |
| Pages | 37-54 | 1132-1145 |
| Authors | (10) Haojie Wang, Jidong Zhai, Mingyu Gao, Zixuan Ma, Shizhi Tang, Liyan Zheng, Yuanzhi Li, Kaiyuan Rong, Yuanyong Chen, Zhihao Jia | (7) Dawei Gao, Haibin Wang, Yaliang Li, Xiuyu Sun, Yichen Qian, Bolin Ding, Jingren Zhou |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.14778/3641204.3641221, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3641204.3641221, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.14778/3641204.3641221'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "PET: Optimizing Tensor Programs…" (no DOI, 2021) and B "Text-to-SQL Empowered by Large Language Models: A Benchmark Evaluation" (10.14778/3641204.3641221, 2024) have unrelated titles and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2021 vs 2024
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:4bc9c48a33ef23748d4aa824a198749991a3ceb52f13c5cc576848a3e5b59d3f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:213`
- B `work` `er-evidence:20d19dacee726c5adb40fba30716e80a72b0ebb1dae41b39343e56accf46fc33` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:53`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 179 — Work

- **pairId:** `resolution-pair:1d1db1abd7033d65e6f2d6a6c6ab4df45a8f235b3e4975e7be6760b029665650`
- **evidenceHash:** `92ebcb0cc1c02c1ecfd46c065c30b434ae757169b9d5f11b305c5433f5de1df8`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2797851444 (conference-paper) | OPENALEX W3173563914 (article) |
| Title | Privacy at Scale | DistAI: Data-Driven Automated Invariant Learning for Distributed Protocols. |
| Year | 2018 | 2021 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4306420647 |
| DOI | 10.1145/3183713.3197390 | — |
| arXiv ID | — | — |
| Pages | 1655-1658 | 405-421 |
| Authors | (6) Graham Cormode, Somesh Jha, Tejas Kulkarni, Ninghui Li, Divesh Srivastava, Tianhao Wang | (6) Jianan Yao, Runzhou Tao, Ronghui Gu, Jason Nieh, Suman Jana, Gabriel Ryan |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3183713.3197390, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3183713.3197390, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1145/3183713.3197390'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Privacy at Scale" (DOI 10.1145/3183713.3197390, 2018) and B "DistAI: Data-Driven Automated Invariant Learning for Distributed Protocols." (no DOI, 2021) have unrelated titles and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2018 vs 2021
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:e6ac5f643fffe1f52c03c264e5715da6fe4a19f1c15309e4737918f6f55e355e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:423`
- B `work` `er-evidence:3db98d591ee891a15936357cc48a569a7bce863c89118ccf3c1819c60e2436d7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:212`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 180 — Researcher

- **pairId:** `resolution-pair:2c50d3cf98709e870ce063e5dd1775883ba86807236a76b1353900415afec36c`
- **evidenceHash:** `44bce29d24c8763938c64e9d3bf29156e44ff4b773da033e8bfb03e654aa672e`
- **Question:** do mention A `mention:openalex:W4281972940#1` and B `mention:openalex:W4389539730#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4281972940#1 | mention:openalex:W4389539730#6 |
| Name as written | Immanuel Trummer | Immanuel Trummer |
| Author position | 1 of 1 | 6 of 7 |
| ORCID on mention | 0000-0002-7203-2349 (OpenAlex-supplied) | 0000-0002-7203-2349 (OpenAlex-supplied) |
| OpenAlex author ID | A5087259526 | A5087259526 |
| Affiliation | ROR 05bnh6r87 | ROR 05bnh6r87 |
| Work title | DB-BERT: A Database Tuning Tool that "Reads the Manual" | Language Models Enable Simple Systems for Generating Structured Views of Heterogeneous Data Lakes |
| Year | 2022 | 2023 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210226185 |
| DOI | 10.1145/3514221.3517843 | 10.14778/3626292.3626294 |
| Coauthors | — | Simran Arora, Brandon Yang, Sabri Eyuboglu, Avanika Narayan, Andrew Hojel, Christopher Ré |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['05bnh6r87'] B=['05bnh6r87'] shared=['05bnh6r87']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Immanuel Trummer" with ROR 05bnh6r87 on papers applying language models to data management ("DB-BERT: A Database Tuning Tool that 'Reads the Manual'" 2022; "Language Models Enable Simple Systems for Generating Structured Views of Heterogeneous Data Lakes" 2023).

**Supporting evidence:**
- Name exact match: A author#1 (sole author), B author#6
- enrichment ror=05bnh6r87 on both target mentions
- Specific topic continuity: language models for data systems
- Same OpenAlex-supplied observedOrcid 0000-0002-7203-2349 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors (A is single-authored)

**Limitations / missing information:**
- Relies on name, affiliation and topic; no coauthor or registry link

<details><summary>Evidence references</summary>

- A `work` `er-evidence:92eec0ac96307fdee94effce8ceccfdd30d9b75ca0bc5c99381be2fbceccdd30` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:149`
- A `enrichment` `er-evidence:e742c8d753d157f02b048e8d1c6847026695b68d23b128b6c1f143d2caf890b7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1580`
- B `work` `er-evidence:b52af49df5e710c14d8349165a45d91793cb3fceb4b5312cc67eb17813b99805` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:55`
- B `enrichment` `er-evidence:eaac67c827666583c3f5120413ef080527bfcbd6a3fbbb7c83e9165846faae6a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:617`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---
