# ScholarChain AI review drafts — batch 01 (tasks 1–20)

> **Status: AI_SUGGESTIONS_PENDING_HUMAN_REVIEW.** These are AI-generated suggestions from a session-reported `claude-opus-5-5` model (not independently verified). They are not human reviews or gold labels. Record your own decision in each task's decision box; an empty box means not reviewed.

Queue: `review-queue:05c5817f62a70d378829be361b9c9169fc9af18448f7c83c245f1d65bbca6175`  
Work tasks: 16 · Researcher tasks: 4

Rows marked `>> … <<` in the raw data and the 'Name as written' row identify the mention being compared. OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider hypotheses. Lines in _italics_ starting with 'helper:' are exact-string comparisons computed by a script to help reading; they are not judgments.

---
## Task 1 — Work

- **pairId:** `resolution-pair:37a7e5c7d4d9d754b428590917c6e5a6b51283d3660eba4296756b03a934bec5`
- **evidenceHash:** `d5e59b17f0f33d1a175b9cc2f7bd61fbbaac6aa555de4a53b45ab6b739dffdb2`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W4281721601 (conference-paper) | OPENALEX W4385285758 (conference-paper) |
| Title | Entity Resolution with Hierarchical Graph Attention Networks | RETIA: Relation-Entity Twin-Interact Aggregation for Temporal Knowledge Graph Extrapolation |
| Year | 2022 | 2023 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210210321 |
| DOI | 10.1145/3514221.3517872 | 10.1109/icde55515.2023.00138 |
| arXiv ID | — | — |
| Pages | 429-442 | 1761-1774 |
| Authors | (5) Dezhong Yao, Yuhong Gu, Gao Cong, Hai Jin, Xinqiao Lv | (5) Kangzheng Liu, Feng Zhao, Guandong Xu, Xianzhi Wang, Hai Jin |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3514221.3517872, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3514221.3517872, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1109/icde55515.2023.00138, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde55515.2023.00138, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3514221.3517872'] B=['10.1109/icde55515.2023.00138'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A work.doi=10.1145/3514221.3517872 ("Entity Resolution with Hierarchical Graph Attention Networks", 2022) and B work.doi=10.1109/icde55515.2023.00138 ("RETIA: Relation-Entity Twin-Interact Aggregation…", 2023) are distinct DOIs with unrelated titles, different venues and different page ranges.

**Supporting evidence:**
- work.doi differs after normalization: 10.1145/3514221.3517872 vs 10.1109/icde55515.2023.00138
- work.title unrelated (entity resolution vs temporal knowledge graph extrapolation)
- work.year 2022 vs 2023; venueId S4393915683 vs S4210210321; pages 429-442 vs 1761-1774
- work.authors: only Hai Jin appears in both 5-author lists

**Conflicting evidence:**
- One shared author name (Hai Jin)

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:eb401d25293577056664424abe8449406bf31f4fe4402b8ff845550f3c7809db` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:153`
- B `work` `er-evidence:f8369be65e9726a82cfd715cefa5d6dd8c7c4dfaf92ec1354759fb5d79de0ae3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:86`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 2 — Work

- **pairId:** `resolution-pair:1bb247ad60a79e13ba1c623ba74bcdeea308fa41c1565572fa53bd68754e4a85`
- **evidenceHash:** `a98d59ed47f0b4899c86a125a8565ad46be396b7aad4fbe7fa9e17d7a5d61d8e`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2805618604 (conference-paper) | OPENALEX W4404385440 (conference-paper) |
| Title | iFair: Learning Individually Fair Data Representations for Algorithmic Decision Making | Building AI Agents for Autonomous Clouds: Challenges and Design Principles |
| Year | 2019 | 2024 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S7407088165 |
| DOI | 10.1109/icde.2019.00121 | 10.1145/3698038.3698525 |
| arXiv ID | — | — |
| Pages | 1334-1345 | 99-110 |
| Authors | (3) Preethi Lahoti, Krishna P. Gummadi, Gerhard Weikum | (13) Manish Shetty, Yinfang Chen, Gagan Somashekar, Minghua Ma, Yogesh Simmhan, Xuchao Zhang, Jonathan Mace, Dax Vandevoorde, Pedro Las-Casas, Shachee Mishra Gupta, Suman Nath, Chetan Bansal, Saravan Rajmohan |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde.2019.00121, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde.2019.00121, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3698038.3698525, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3698038.3698525, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1109/icde.2019.00121'] B=['10.1145/3698038.3698525'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A ("iFair: Learning Individually Fair Data Representations…", ICDE-style DOI 10.1109/icde.2019.00121, 2019) and B ("Building AI Agents for Autonomous Clouds…", 10.1145/3698038.3698525, 2024) have distinct DOIs, unrelated titles and disjoint author lists.

**Supporting evidence:**
- work.doi distinct: 10.1109/icde.2019.00121 vs 10.1145/3698038.3698525
- work.title unrelated
- work.year 2019 vs 2024
- work.authors: no shared names (3 vs 13 authors)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:602ab99a99ec19d774843ec6db00e2d33701f7cd18077a006917ea3d669fa1b2` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:408`
- B `work` `er-evidence:17ebfe0030f1775803d2a0855c73c09897efc4012ad868e40a9c7fc40f4fdf51` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:8`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 3 — Work

- **pairId:** `resolution-pair:941ce071df7cd771ae07fd4adf4d74846ed508e513c4d1a3dd27f4d339146763`
- **evidenceHash:** `93bb1c8e14aa4029d89343fb5e2f7eacd486c782caac8c66c95a8f129f82eb92`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3013555795 (article) | OPENALEX W4398234802 (conference-paper) |
| Title | DeepDB | Demonstrating CAESURA: Language Models as Multi-Modal Query Planners |
| Year | 2020 | 2024 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4393915683 |
| DOI | 10.14778/3384345.3384349 | 10.1145/3626246.3654732 |
| arXiv ID | — | — |
| Pages | 992-1005 | 472-475 |
| Authors | (6) Benjamin Hilprecht, Andreas Schmidt, Moritz Kulessa, Alejandro Molina, Kristian Kersting, Carsten Binnig | (2) Matthias Urban, Carsten Binnig |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3384345.3384349, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3384345.3384349, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3626246.3654732, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3626246.3654732, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3384345.3384349'] B=['10.1145/3626246.3654732'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "DeepDB" (10.14778/3384345.3384349, 2020, 6 authors) and B "Demonstrating CAESURA: Language Models as Multi-Modal Query Planners" (10.1145/3626246.3654732, 2024, 2 authors) have distinct DOIs, different titles and years; only Carsten Binnig is shared.

**Supporting evidence:**
- work.doi distinct: 10.14778/3384345.3384349 vs 10.1145/3626246.3654732
- work.title different (DeepDB vs CAESURA demo)
- work.year 2020 vs 2024; venueId S4210226185 vs S4393915683

**Conflicting evidence:**
- Carsten Binnig appears in both author lists

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:a750cfe48085a827607af5cab7d7dd9a37b36d996373d133cf988ea2d576a723` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:291`
- B `work` `er-evidence:62a09c8b72e72c1138dcb69d2f77eeef8f8112e64a121ad429966ae5dc3b8418` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:41`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 4 — Work

- **pairId:** `resolution-pair:79a8d13f0708109279e3653827bc294b5bf48cb0c63ad3d2ed18e0c7d8a363e5`
- **evidenceHash:** `76b460253875b4a86e3ca0413ce0e905eadd667b592dc8b31cad1685da40e9e6`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2905267911 (conference-paper) | OPENALEX W4402042542 (article) |
| Title | NSCaching: Simple and Efficient Negative Sampling for Knowledge Graph Embedding | The Dawn of Natural Language to SQL: Are We Fully Ready? |
| Year | 2019 | 2024 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210226185 |
| DOI | 10.1109/icde.2019.00061 | 10.14778/3681954.3682003 |
| arXiv ID | — | — |
| Pages | 614-625 | 3318-3331 |
| Authors | (4) Yongqi Zhang, Quanming Yao, Yingxia Shao, Lei Chen | (5) Boyan Li, Yuyu Luo, Chengliang Chai, Guoliang Li, Nan Tang |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1109/icde.2019.00061, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde.2019.00061, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.14778/3681954.3682003, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3681954.3682003, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1109/icde.2019.00061'] B=['10.14778/3681954.3682003'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "NSCaching: Simple and Efficient Negative Sampling for Knowledge Graph Embedding" (10.1109/icde.2019.00061, 2019) and B "The Dawn of Natural Language to SQL: Are We Fully Ready?" (10.14778/3681954.3682003, 2024) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2019 vs 2024
- work.authors: no shared names

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:bf3d8546b399130661bbacbf80e5bbc5b06b7acd84c28d40fbee47be8ecbd2d4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:368`
- B `work` `er-evidence:c32902bfdaad6eb216f79e79a6701a9e44a17800ee8c602c64813e6614756257` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:19`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 5 — Work

- **pairId:** `resolution-pair:1c67fc43093ed61ce83b62719b39022a7a54eb5b9a2a8548bdf6c410f3921c43`
- **evidenceHash:** `9cb3cc72ea681f272090849a4f8a1f88d6252d03419a4ac672f2ae1ece3b8337`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3109841242 (conference-paper) | OPENALEX W4291713239 (conference-paper) |
| Title | APAN: Asynchronous Propagation Attention Network for Real-time Temporal Graph Embedding | Apache Calcite |
| Year | 2021 | 2018 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4393915683 |
| DOI | 10.1145/3448016.3457564 | 10.1145/3183713.3190662 |
| arXiv ID | — | — |
| Pages | 2628-2638 | 221-230 |
| Authors | (11) Xuhong Wang, Ding Lyu, Mengjian Li, Yang Xia, Qi Yang, Xinwen Wang, Xinguang Wang, Ping Cui, Yupu Yang, Bowen Sun, Zhenyu Guo | (5) Edmon Begoli, Jesús Camacho-Rodríguez, Julian Hyde, Michael J. Mior, Daniel Lemire |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3448016.3457564, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3448016.3457564, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3183713.3190662, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3183713.3190662, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3448016.3457564'] B=['10.1145/3183713.3190662'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "APAN: Asynchronous Propagation Attention Network…" (10.1145/3448016.3457564, 2021, 11 authors) and B "Apache Calcite" (10.1145/3183713.3190662, 2018, 5 authors) have distinct DOIs, unrelated titles, different years and no shared authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2021 vs 2018; pages 2628-2638 vs 221-230
- work.authors disjoint

**Conflicting evidence:**
- Same venueId S4393915683 (venue only)

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:315df73c446e94772b2a939cfcb468a83c73a87d68920076a45ce79129dce0f3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:227`
- B `work` `er-evidence:05ff5a1e3553665d750baf730f2a472d42e0bc282eabb30d3f156cb336ac3bea` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:129`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 6 — Researcher

- **pairId:** `resolution-pair:e68c5816247b9754795a656cdf92d7cf82a38a611438c55ad2fa415196eef830`
- **evidenceHash:** `3bfc6d9b039731b0eea9e349a4a4c3ac72f8242174b17745cd099778d2f233c1`
- **Question:** do mention A `mention:openalex:W2951096868#1` and B `mention:openalex:W3030299187#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2951096868#1 | mention:openalex:W3030299187#1 |
| Name as written | Haitao Yuan | Haitao Yuan |
| Author position | 1 of 2 | 1 of 4 |
| ORCID on mention | 0000-0001-7403-2871 (OpenAlex-supplied) | 0000-0001-7403-2871 (OpenAlex-supplied) |
| OpenAlex author ID | A5082331221 | A5082331221 |
| Affiliation | ROR 03cve4549 | ROR 03cve4549 |
| Work title | Distributed In-memory Trajectory Similarity Search and Join on Road Network | Effective Travel Time Estimation: When Historical Trajectories over Road Networks Matter |
| Year | 2019 | 2020 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4393915683 |
| DOI | 10.1109/icde.2019.00115 | 10.1145/3318464.3389771 |
| Coauthors | Guoliang Li | Guoliang Li, Zhifeng Bao, Ling Feng |

_helper: shared coauthor normalizedNames = ['guoliang li']_
_helper: target-mention ROR A=['03cve4549'] B=['03cve4549'] shared=['03cve4549']_

**AI-proposed label: `same`**

**Note:** Both mentions are first author "Haitao Yuan" with the same coauthor Guoliang Li, the same mention-level affiliation ROR 03cve4549, and closely related topics (trajectory similarity on road networks, 2019; travel-time estimation from trajectories over road networks, 2020).

**Supporting evidence:**
- Name exact match: A author#1 "Haitao Yuan" and B author#1 "Haitao Yuan"
- Shared coauthor in payload: Guoliang Li (A author#2, B author#2)
- enrichment ror=03cve4549 on both target mentions
- Topic continuity: road-network trajectory work in consecutive years (2019, 2020)
- Same OpenAlex-supplied observedOrcid 0000-0001-7403-2871 and oaAuthor A5082331221 on both (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- Affiliation, coauthor and ORCID values all come from OpenAlex; no ORCID-registry record is supplied
- Coauthor and topic overlap are correlated signals

<details><summary>Evidence references</summary>

- A `work` `er-evidence:5f24ee7d565ba840bc542329751f1461d7c96e8f7055f4d4a07b5f3798c268c0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:340`
- A `enrichment` `er-evidence:ea30b4544b9b533f65b6a571c8ca0bd78553abf00b4cff6c8303a62588c90c64` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3557`
- B `enrichment` `er-evidence:26359f90c2a67b9ab2d83c313f3d98c2876ca4e16e0870c8f7b293ad674e309f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2959`
- B `work` `er-evidence:3e8697c6da863844598834fd80c127c40d901a7ca815b56396a47b0adfabd918` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:273`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 7 — Work

- **pairId:** `resolution-pair:c409423b9ca6288e76852690319ddb940c330da0b78c4025dee229e95089c376`
- **evidenceHash:** `313b78a3ac0439a3f7c3174ebb453a8eefbd117817e29801023c7144e56570a0`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3007098654 (conference-paper) | OPENALEX W3174566165 (article) |
| Title | RobustPeriod: Robust Time-Frequency Mining for Multiple Periodicity Detection | Nap: A Black-Box Approach to NUMA-Aware Persistent Memory Indexes |
| Year | 2021 | 2021 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4306420647 |
| DOI | 10.1145/3448016.3452779 | — |
| arXiv ID | — | — |
| Pages | 2328-2337 | 93-111 |
| Authors | (6) Qingsong Wen, Kai He, Liang Sun, Yingying Zhang, Min Ke, Huan Xu | (4) Qing Wang, Youyou Lu, Junru Li, Jiwu Shu |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3448016.3452779, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3448016.3452779, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1145/3448016.3452779'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "RobustPeriod: Robust Time-Frequency Mining for Multiple Periodicity Detection" (DOI 10.1145/3448016.3452779) and B "Nap: A Black-Box Approach to NUMA-Aware Persistent Memory Indexes" (no DOI, OSDI PDF URL) share only the year 2021; titles and all authors differ.

**Supporting evidence:**
- work.title unrelated
- work.authors disjoint (6 vs 4)
- venueId S4393915683 vs S4306420647; pages 2328-2337 vs 93-111

**Conflicting evidence:**
- Same year 2021

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:19455bab9a0e6ac40374db89bdd7d526311531d55409bf3a5884927b3881eb24` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:300`
- B `work` `er-evidence:2873ea80b995b181f3d7d3bff511f82977a32037ec5af6e2ffa09aceaba2489e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:206`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 8 — Work

- **pairId:** `resolution-pair:d473c416a70148a1baed857b2b103fba6fe64d34c3f645c815c9dba4cc9fdc68`
- **evidenceHash:** `2b4f4fb67ed03996c59e25d90ead550ed966a200d05f77a221d6a9faf7f824a9`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3209190856 (conference-paper) | OPENALEX W4281718197 (conference-paper) |
| Title | Faa$T | Amazon Redshift Re-invented |
| Year | 2021 | 2022 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4393915683 |
| DOI | 10.1145/3472883.3486974 | 10.1145/3514221.3526045 |
| arXiv ID | — | — |
| Pages | 122-137 | 2205-2217 |
| Authors | (9) Francisco Romero, Gohar Irfan Chaudhry, Íñigo Goiri, Pragna Gopa, Paul Batum, Neeraja J. Yadwadkar, Rodrigo Fonseca, Christos Kozyrakis, Ricardo Bianchini | (24) Nikos Armenatzoglou, Sanuj Basu, Naga Bhanoori, Mengchu Cai, Naresh Chainani, Kiran Chinta, Venkatraman Govindaraju, Todd J. Green, Monish Gupta, Sebastian Hillig, Eric Hotinger, Yan Leshinksy, Jintian Liang, Michael McCreedy, Fabian Nagel … (+9 more) |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3472883.3486974, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3472883.3486974, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3514221.3526045, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3514221.3526045, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3472883.3486974'] B=['10.1145/3514221.3526045'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Faa$T" (10.1145/3472883.3486974, 2021, 9 authors) and B "Amazon Redshift Re-invented" (10.1145/3514221.3526045, 2022, 24 authors) have distinct DOIs, different titles and disjoint author lists.

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

- A `work` `er-evidence:943c01bc9fe6932a92c7fb082153801b213932c57601cc9552161d5a6f672e34` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:177`
- B `work` `er-evidence:597b93c05d7af6ead1d601ad9fcae0edd8c7dd470fda23129f8bcebdc4ad2ce2` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:154`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 9 — Work

- **pairId:** `resolution-pair:2f4ac66c0da6260a1f31edad3cf5243f8586fe2319a08349625565b6243388cf`
- **evidenceHash:** `dce87941bae75beb21a99553b81927ff76fa83209bb948e6b244bb3fe405c6f8`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2899396876 (article) | OPENALEX W4391054939 (article) |
| Title | LegoOS: a disseminated, distributed OS for hardware resource disaggregation | ImDiffusion: Imputed Diffusion Models for Multivariate Time Series Anomaly Detection |
| Year | 2018 | 2023 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210226185 |
| DOI | 10.5555/3291168.3291175 | 10.14778/3632093.3632101 |
| arXiv ID | — | — |
| Pages | 69-87 | 359-372 |
| Authors | (4) Yizhou Shan, Yutong Huang, Yilun Chen, Yiying Zhang | (10) Yuhang Chen, Chaoyun Zhang, Minghua Ma, Yudong Liu, Ruomeng Ding, Bowen Li, Shilin He, Saravan Rajmohan, Qingwei Lin, Dongmei Zhang |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.5555/3291168.3291175, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.5555/3291168.3291175, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.14778/3632093.3632101, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3632093.3632101, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.5555/3291168.3291175'] B=['10.14778/3632093.3632101'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "LegoOS: a disseminated, distributed OS for hardware resource disaggregation" (10.5555/3291168.3291175, 2018) and B "ImDiffusion: Imputed Diffusion Models for Multivariate Time Series Anomaly Detection" (10.14778/3632093.3632101, 2023) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2018 vs 2023
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:37803296eca1524605ccf5277c9c675662b394dd216a7206bc660b966a4ac1fb` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:375`
- B `work` `er-evidence:3563a3a7496f9d011a2d86b3de67a7bcd6d2682fc231eef6b4c7214563379d62` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:54`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 10 — Work

- **pairId:** `resolution-pair:f3201afb8ed3ff3ca8be6918b1204f490d256e709babe451d89e69dcd44c1afe`
- **evidenceHash:** `e6db95f4a5845f5eafc9731d151047af575185377709f38985c7b0f878713438`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2945486614 (conference-paper) | OPENALEX W2987607480 (conference-paper) |
| Title | ALEX: An Updatable Adaptive Learned Index | Cirrus |
| Year | 2020 | 2019 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S7407088165 |
| DOI | 10.1145/3318464.3389711 | 10.1145/3357223.3362711 |
| arXiv ID | — | — |
| Pages | 969-984 | 13-24 |
| Authors | (12) Jialin Ding, Umar Farooq Minhas, Jia Yu, Chi Wang, Jaeyoung Do, Yinan Li, Hantian Zhang, Badrish Chandramouli, Johannes Gehrke, Donald Kossmann, David Lomet, Tim Kraska | (5) Joao Carreira, Pedro Fonseca, Alexey Tumanov, Andrew Zhang, Randy Katz |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3318464.3389711, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3318464.3389711, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3357223.3362711, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3357223.3362711, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3318464.3389711'] B=['10.1145/3357223.3362711'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "ALEX: An Updatable Adaptive Learned Index" (10.1145/3318464.3389711, 2020) and B "Cirrus" (10.1145/3357223.3362711, 2019) have distinct DOIs, different titles, years and author lists.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2020 vs 2019
- work.authors disjoint (12 vs 5)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:201bcc26625ac020fd5dcf968451e79e197dd1a1ca2929845220bf1753ba05c4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:356`
- B `work` `er-evidence:19cceb480abd8eeedd60d899740a2f5f6d662b24ab3c43441642f89480dd47ec` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:310`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 11 — Researcher

- **pairId:** `resolution-pair:47291b52dc219e30f9d7d6f613794472930d713e78e77dc2c4f5ab3e928dc4d4`
- **evidenceHash:** `5b695e0d8bca3955f9241ef597e32f26f095cc1f78d87d57b92f96506ecc26ab`
- **Question:** do mention A `mention:openalex:W2803609932#3` and B `mention:openalex:W2951565607#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2803609932#3 | mention:openalex:W2951565607#4 |
| Name as written | Vanessa Braganholo | Vanessa Braganholo |
| Author position | 3 of 3 | 4 of 4 |
| ORCID on mention | 0000-0002-1184-8192 (OpenAlex-supplied) | 0000-0002-1184-8192 (OpenAlex-supplied) |
| OpenAlex author ID | A5031131350 | A5031131350 |
| Affiliation | ROR 02rjhbb08 | ROR 02rjhbb08 |
| Work title | Provenance Analytics for Workflow-Based Computational Experiments | A Survey on Collecting, Managing, and Analyzing Provenance from Scripts |
| Year | 2018 | 2019 |
| Venue ID | venue:openalex:S157921468 | venue:openalex:S157921468 |
| DOI | 10.1145/3184900 | 10.1145/3311955 |
| Coauthors | Wellington Oliveira, Daniel De Oliveira | João Felipe Pimentel, Juliana Freire, Leonardo Murta |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['02rjhbb08'] B=['02rjhbb08'] shared=['02rjhbb08']_

**AI-proposed label: `same`**

**Note:** The distinctive full name "Vanessa Braganholo" appears on both mentions with the same affiliation ROR 02rjhbb08, and both works are on provenance (workflow provenance analytics 2018; survey on provenance from scripts 2019) in the same venue S157921468.

**Supporting evidence:**
- Name exact match: A author#3 and B author#4 "Vanessa Braganholo"
- enrichment ror=02rjhbb08 on both target mentions
- Specific topic continuity: provenance of computational experiments/scripts
- Same venueId S157921468, years 2018 and 2019
- Same OpenAlex-supplied observedOrcid 0000-0002-1184-8192 / oaAuthor A5031131350 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthor between the two author lists

**Limitations / missing information:**
- All identity hints are OpenAlex-derived; no ORCID-registry evidence supplied

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:c9b39b3abb4c8c0cfc8c47da40daaf4366151e784feb09db601da0eefa2c13c7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4165`
- A `work` `er-evidence:f0637a65a21d2a58e7ff5d7a3edc3d70c56622cd811b0762c4dbe7d31909502f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:410`
- B `enrichment` `er-evidence:069c29a3d538ebeee92f016adf8c298c687554f7584de021312e82a09bf2ea61` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3542`
- B `work` `er-evidence:4b2b40ec503ac89a85a10812f889d151106c25654d3d7d9e9162cd79b22a8015` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:338`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 12 — Work

- **pairId:** `resolution-pair:fe4d0d9101b0d6e3c804c0a4e97e6dc14a7aca79ec136bc751c104326bccdd59`
- **evidenceHash:** `775b1566978a529e412e9ff187646e1616d9ee7c3eb2b6c12bfbb594735e5b26`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2899225507 (article) | OPENALEX W4388073594 (conference-paper) |
| Title | Deconstructing RDMA-enabled distributed transactions: hybrid is better | Building GPU TEEs using CPU Secure Enclaves with GEVisor |
| Year | 2018 | 2023 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S7407088165 |
| DOI | 10.5555/3291168.3291186 | 10.1145/3620678.3624659 |
| arXiv ID | — | — |
| Pages | 233-251 | 249-264 |
| Authors | (4) Xingda Wei, Zhiyuan Dong, Rong Chen, Haibo Chen | (3) Xiaolong Wu, Dave Jing Tian, Chung Hwan Kim |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.5555/3291168.3291186, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.5555/3291168.3291186, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3620678.3624659, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3620678.3624659, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.5555/3291168.3291186'] B=['10.1145/3620678.3624659'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Deconstructing RDMA-enabled distributed transactions: hybrid is better" (10.5555/3291168.3291186, 2018) and B "Building GPU TEEs using CPU Secure Enclaves with GEVisor" (10.1145/3620678.3624659, 2023) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2018 vs 2023
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:27973a9f97229a430617c1d42afdb0b6fc288659357c82bf64e25003bb176626` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:376`
- B `work` `er-evidence:c93cc7b5ded53ae76a19ae28fc520fe14a424b1a5c26ebc8f98f1ea609a18381` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:58`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 13 — Work

- **pairId:** `resolution-pair:11b910f23d3574b7a71623ebec852efda9abd2d1c5b1470a8a34ef3535d9b04d`
- **evidenceHash:** `2fa6f22e7e119c97df1a88a9cbba2e16cd9dca1e30b9d0a842df7bd82d42847c`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W4312924702 (article) | OPENALEX W4398234408 (conference-paper) |
| Title | SQLite | BigLake: BigQuery's Evolution toward a Multi-Cloud Lakehouse |
| Year | 2022 | 2024 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4393915683 |
| DOI | 10.14778/3554821.3554842 | 10.1145/3626246.3653388 |
| arXiv ID | — | — |
| Pages | 3535-3547 | 334-346 |
| Authors | (6) Kevin P. Gaffney, Martin Prammer, Larry Brasfield, D. Richard Hipp, Dan Kennedy, Jignesh M. Patel | (15) Justin Levandoski, Garrett Casto, Mingge Deng, Rushabh Desai, Pavan Edara, Thibaud Hottelier, Amir Hormati, Anoop Johnson, Jeff Johnson, Dawid Kurzyniec, Sam McVeety, Prem Ramanathan, Gaurav Saxena, Vidya Shanmugan, Yuri Volobuev |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3554821.3554842, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3554821.3554842, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1145/3626246.3653388, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3626246.3653388, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3554821.3554842'] B=['10.1145/3626246.3653388'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "SQLite" (10.14778/3554821.3554842, 2022, 6 authors) and B "BigLake: BigQuery's Evolution toward a Multi-Cloud Lakehouse" (10.1145/3626246.3653388, 2024, 15 authors) have distinct DOIs, different titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2022 vs 2024
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:fbcfd147d7d8ef8ca99839e8c7ee882b3859bd80a404b9d2f2f219594d85d709` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:120`
- B `work` `er-evidence:7421e6288313d693187ecff74e4a9d4fa4699f03799f707bc423c187f4f3292d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:45`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 14 — Researcher

- **pairId:** `resolution-pair:c7f48676ac59dd922ad57337937fa630b562c15a213b86bebe2e4af697153a32`
- **evidenceHash:** `b7dbd58c8dcd1894538877504d879e5ecbed24200a42c9bc6d195b7d8f12dfba`
- **Question:** do mention A `mention:openalex:W4386768656#18` and B `mention:openalex:W4388041408#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4386768656#18 | mention:openalex:W4388041408#1 |
| Name as written | Shen Li | Suyi Li |
| Author position | 18 of 18 | 1 of 5 |
| ORCID on mention | — | 0000-0003-3921-9037 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5066034443 |
| Affiliation | ROR 01zbnvs85 | ROR 00q4vv597 |
| Work title | PyTorch FSDP: Experiences on Scaling Fully Sharded Data Parallel | Golgi |
| Year | 2023 | 2023 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S7407088165 |
| DOI | 10.14778/3611540.3611569 | 10.1145/3620678.3624645 |
| Coauthors | Yanli Zhao, Andrew Gu, Rohan Varma, Liang Luo, Chien-Chin Huang, Min Xu, Less Wright, Hamid Shojanazeri, Myle Ott, Sam Shleifer, Alban Desmaison, Can Balioglu, Pritam Damania, Bernard Nguyen, Geeta Chauhan, Yuchen Hao, Ajit Mathews | Wei Wang, Jun Yang, Guangzhen Chen, Daohe Lu |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01zbnvs85'] B=['00q4vv597'] shared=none_

**AI-proposed label: `different`**

**Note:** The compared names differ in given name: A author#18 "Shen Li" vs B author#1 "Suyi Li"; these are not initial or transliteration variants of each other, and only the common surname Li is shared.

**Supporting evidence:**
- nameText given names differ: "Shen" vs "Suyi"
- No shared coauthors between the 18-author and 5-author lists
- enrichment ror differs: 01zbnvs85 vs 00q4vv597 (weak on its own)

**Conflicting evidence:**
- Both 2023 systems/ML-infrastructure papers

**Limitations / missing information:**
- A mention has no ORCID or OpenAlex author id
- Relies on the name difference being genuine, not a source error

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:96dc6d4918746672c6b4a5902b4a55936f3dde18fca29a0a8ef6e553a1dd6a57` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:908`
- A `work` `er-evidence:f503c5922b0f40bcd51d6f0bc71362335062af7b7a25201c907dec1d596a3581` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:81`
- B `work` `er-evidence:abeeb930f85f1b7fc3801805c6f14255864fd38868568e3b5d843b23d82f9aa5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:60`
- B `enrichment` `er-evidence:be28249950f75bff8d28c27617aeab71c647934476845bbb4e9d27f6c9c6994b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:658`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 15 — Work

- **pairId:** `resolution-pair:d18e11b94d726b7ec4839a262e8fe143c9ace627337980f18683cf945b1fd9c8`
- **evidenceHash:** `06bf0ffd348af19a3d4bcaa4e9647eac51f130f751afc6e04f6e15b2b811b046`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2790867877 (conference-paper) | OPENALEX W2899435347 (article) |
| Title | Constant Delay Algorithms for Regular Document Spanners | Graviton: trusted execution environments on GPUs |
| Year | 2018 | 2018 |
| Venue ID | venue:openalex:S7407087293 | venue:openalex:S4306420647 |
| DOI | 10.1145/3196959.3196987 | 10.5555/3291168.3291219 |
| arXiv ID | — | — |
| Pages | 165-177 | 681-696 |
| Authors | (5) Fernando Florenzano, Cristian Riveros, Martin Ugarte, Stijn Vansummeren, Domagoj Vrgoc | (3) Stavros Volos, Kapil Vaswani, Rodrigo Bruno |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3196959.3196987, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3196959.3196987, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.5555/3291168.3291219, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.5555/3291168.3291219, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3196959.3196987'] B=['10.5555/3291168.3291219'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Constant Delay Algorithms for Regular Document Spanners" (10.1145/3196959.3196987) and B "Graviton: trusted execution environments on GPUs" (10.5555/3291168.3291219) share only the year 2018; DOIs, titles, venues and authors all differ.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- venueId S7407087293 vs S4306420647
- work.authors disjoint

**Conflicting evidence:**
- Same year 2018

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:a3456d9611f41700ebb2ec6ce329192a0e2e91ccf89b1e94e50c1288ede5c242` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:439`
- B `work` `er-evidence:5bdc056378ed07f6d62e9fbaea4b4b80463541e1282c74650678870472c1da92` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:374`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 16 — Work

- **pairId:** `resolution-pair:59e49efdf520ab427386c59a1ead29d59384def12a7f42200269ed30eee290e2`
- **evidenceHash:** `6bb8c07488e60a6860d3c7a73c3626b9e09a724a1f4c925b5fa4b667de448501`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W4381610063 (article) | OPENALEX W4385285758 (conference-paper) |
| Title | Towards Efficient Index Construction and Approximate Nearest Neighbor Search in High-Dimensional Spaces | RETIA: Relation-Entity Twin-Interact Aggregation for Temporal Knowledge Graph Extrapolation |
| Year | 2023 | 2023 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210210321 |
| DOI | 10.14778/3594512.3594527 | 10.1109/icde55515.2023.00138 |
| arXiv ID | — | — |
| Pages | 1979-1991 | 1761-1774 |
| Authors | (5) Xi Zhao, Yao Tian, Kai Huang, Bolong Zheng, Xiaofang Zhou | (5) Kangzheng Liu, Feng Zhao, Guandong Xu, Xianzhi Wang, Hai Jin |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3594512.3594527, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3594512.3594527, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1109/icde55515.2023.00138, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde55515.2023.00138, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3594512.3594527'] B=['10.1109/icde55515.2023.00138'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Towards Efficient Index Construction and Approximate Nearest Neighbor Search in High-Dimensional Spaces" (10.14778/3594512.3594527) and B "RETIA…" (10.1109/icde55515.2023.00138) are both 2023 but have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- venueId S4210226185 vs S4210210321
- work.authors disjoint

**Conflicting evidence:**
- Same year 2023

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:ea9dbe86a0ba8dc5aecb52ed30c1cfbfbb8bc684ec8cb7554fc6157ebe3bd44c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:97`
- B `work` `er-evidence:f8369be65e9726a82cfd715cefa5d6dd8c7c4dfaf92ec1354759fb5d79de0ae3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:86`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 17 — Work

- **pairId:** `resolution-pair:53f50e58a9cc736af370e6a6babd51e4768a29d7a9345581ffdd43ad03856337`
- **evidenceHash:** `fe2b86742ba0560fe58e21e3bf658790459001818f7d8ffdae97cbab83fd4929`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2798891709 (conference-paper) | OPENALEX W4226086155 (article) |
| Title | SuRF | Cardinality estimation in DBMS |
| Year | 2018 | 2021 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210226185 |
| DOI | 10.1145/3183713.3196931 | 10.14778/3503585.3503586 |
| arXiv ID | — | — |
| Pages | 323-336 | 752-765 |
| Authors | (7) Huanchen Zhang, Hyeontaek Lim, Viktor Leis, David G. Andersen, Michael Kaminsky, Kimberly Keeton, Andrew Pavlo | (14) Yuxing Han, Ziniu Wu, Peizhi Wu, Rong Zhu, Jingyi Yang, Liang Wei Tan, Kai Zeng, Gao Cong, Yanzhao Qin, Andreas Pfadler, Zhengping Qian, Jingren Zhou, Jiangneng Li, Bin Cui |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3183713.3196931, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3183713.3196931, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.14778/3503585.3503586, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3503585.3503586, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.1145/3183713.3196931'] B=['10.14778/3503585.3503586'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "SuRF" (10.1145/3183713.3196931, 2018, 7 authors) and B "Cardinality estimation in DBMS" (10.14778/3503585.3503586, 2021, 14 authors) have distinct DOIs, different titles, years and authors.

**Supporting evidence:**
- work.doi distinct
- work.title different
- work.year 2018 vs 2021
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:7590861c64db0151f8c403c6155a33c76a6386902b9c7a26c630083416af682a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:416`
- B `work` `er-evidence:3023c40c8356e57320f52477068980e9b7b2f45db866b77e81f2bede1c4a9137` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:159`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 18 — Researcher

- **pairId:** `resolution-pair:5aa34321971ee91bb041221791541b0c45b03374baed99c8399626f920592527`
- **evidenceHash:** `b0d21dd3622ab63bc93f3045742115cc1cb4f992da2c803d77e89e24f5cd2134`
- **Question:** do mention A `mention:openalex:W3086150815#2` and B `mention:openalex:W3174749316#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3086150815#2 | mention:openalex:W3174749316#2 |
| Name as written | Anja Gruenheid | Anja Gruenheid |
| Author position | 2 of 6 | 2 of 6 |
| ORCID on mention | 0009-0009-2547-8610 (OpenAlex-supplied) | 0009-0009-2547-8610 (OpenAlex-supplied) |
| OpenAlex author ID | A5043472177 | A5043472177 |
| Affiliation | ROR 00njsd438 | ROR 00njsd438 |
| Work title | DIAMetrics | DIAMetrics |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S47508943 |
| DOI | 10.14778/3415478.3415551 | 10.1145/3471485.3471492 |
| Coauthors | Shaleen Deep, Kruthi Nagaraj, Hiro Naito, Jeff Naughton, Stratis Viglas | Shaleen Deep, Kruthi Nagaraj, Hiro Naito, Jeff Naughton, Stratis Viglas |

_helper: shared coauthor normalizedNames = ['hiro naito', 'jeff naughton', 'kruthi nagaraj', 'shaleen deep', 'stratis viglas']_
_helper: target-mention ROR A=['00njsd438'] B=['00njsd438'] shared=['00njsd438']_

**AI-proposed label: `same`**

**Note:** Both mentions are author#2 "Anja Gruenheid" on works titled "DIAMetrics" whose six-author lists are identical in names and order (Shaleen Deep, Kruthi Nagaraj, Hiro Naito, Jeff Naughton, Stratis Viglas), with the same affiliation ROR 00njsd438.

**Supporting evidence:**
- Name exact match at the same ordinal (2) in both works
- All five coauthors shared, in identical order
- Identical work.title "DIAMetrics" (2020 venue S4210226185; 2021 venue S47508943)
- enrichment ror=00njsd438 on both target mentions
- Same OpenAlex-supplied observedOrcid 0009-0009-2547-8610 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- The two works have distinct DOIs (10.14778/3415478.3415551 vs 10.1145/3471485.3471492); this affects work identity, not the person
- Evidence is all OpenAlex-derived

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:200375f73808e62586d126cfff36814fc112169d32a41cd34e187fcfc1d5baff` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2772`
- A `work` `er-evidence:bff8e344468e582c2cf76796189cab1c3b74e054f2a828a5304485126087a243` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:255`
- B `enrichment` `er-evidence:8cdaac5044d8da2942df46c65c3f5b90b54776ba93d9c6abe9308013831c8cf6` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2225`
- B `work` `er-evidence:99d9d791a675540524e40d0648240feb6130b89545e9ef3be5e7cba724fd26b5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:203`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 19 — Work

- **pairId:** `resolution-pair:bb226a122017151e87206aebcf138709305f23d81421023ae46d83777ab672ee`
- **evidenceHash:** `6d794bb6f0fe8585d2d50aaf94955f785a3de568e27d2fa7d610e15e2304a43c`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3085477028 (article) | OPENALEX W4289533840 (conference-paper) |
| Title | Delta lake | Robust and Explainable Autoencoders for Unsupervised Time Series Outlier Detection |
| Year | 2020 | 2022 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210210321 |
| DOI | 10.14778/3415478.3415560 | 10.1109/icde53745.2022.00273 |
| arXiv ID | — | — |
| Pages | 3411-3424 | 3038-3050 |
| Authors | (21) Michael Armbrust, Tathagata Das, Liwen Sun, Burak Yavuz, Shixiong Zhu, Mukul Murthy, Joseph Torres, Herman van Hovell, Adrian Ionescu, Alicja Łuszczak, Michał Świtakowski, Michał Szafrański, Xiao Li, Takuya Ueshin, Mostafa Mokhtar … (+6 more) | (7) Tung Kieu, Bin Yang, Chenjuan Guo, Christian S. Jensen, Yan Zhao, Feiteng Huang, Kai Zheng |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3415478.3415560, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3415478.3415560, interpretation=SOURCE_OBSERVATION | namespace=openalex.doi, value=https://doi.org/10.1109/icde53745.2022.00273, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde53745.2022.00273, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=['10.14778/3415478.3415560'] B=['10.1109/icde53745.2022.00273'] -> DISTINCT_

**AI-proposed label: `different`** — flags: `IDENTIFIER_CONFLICT`

**Note:** A "Delta lake" (10.14778/3415478.3415560, 2020, 21 authors) and B "Robust and Explainable Autoencoders for Unsupervised Time Series Outlier Detection" (10.1109/icde53745.2022.00273, 2022, 7 authors) have distinct DOIs, unrelated titles and disjoint authors.

**Supporting evidence:**
- work.doi distinct
- work.title unrelated
- work.year 2020 vs 2022
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:495e20185c02d7a59899b8bb6eb5a9b983d3bb223cd8fc74002f06be8533c2d1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:258`
- B `work` `er-evidence:c8d047e855bad795bc36bbc14b064f84ccdd20986c01b5ca68534a23f62f2350` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:134`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 20 — Work

- **pairId:** `resolution-pair:c2447d5e3e2bf99cc7645c6b657f51ec13a602c57df528b88da66d54a659de2d`
- **evidenceHash:** `e50836f524462919dbbe7ef7c3864910683366fd09c0418c98f800a550dbde78`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3095841401 (conference-paper) | OPENALEX W3096140366 (article) |
| Title | Serverless linear algebra | LinnOS: Predictability on Unpredictable Flash Storage with a Light Neural Network |
| Year | 2020 | 2020 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4306420647 |
| DOI | 10.1145/3419111.3421287 | — |
| arXiv ID | — | — |
| Pages | 281-295 | 173-190 |
| Authors | (9) Vaishaal Shankar, Karl Krauth, Kailas Vodrahalli, Qifan Pu, Benjamin Recht, Ion Stoica, Jonathan Ragan-Kelley, Eric Jonas, Shivaram Venkataraman | (6) Mingzhe Hao, Levent Toksoz, Nanqinqin Li, Edward Edberg Halim, Henry Hoffmann, Haryadi S. Gunawi |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3419111.3421287, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3419111.3421287, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1145/3419111.3421287'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Serverless linear algebra" (DOI 10.1145/3419111.3421287) and B "LinnOS: Predictability on Unpredictable Flash Storage with a Light Neural Network" (no DOI, OSDI PDF) share only the year 2020; titles, venues and all authors differ.

**Supporting evidence:**
- work.title unrelated
- work.authors disjoint (9 vs 6)
- venueId S7407088165 vs S4306420647

**Conflicting evidence:**
- Same year 2020

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:22b6852005fdef69acaafc4f152bb28f47ae6cbd465aefdbf1275f40d1f46b58` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:247`
- B `work` `er-evidence:3b493ab6e68f7ad5746297452611542e02f06faa608fc7e9bdb92488793bff34` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:246`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---
