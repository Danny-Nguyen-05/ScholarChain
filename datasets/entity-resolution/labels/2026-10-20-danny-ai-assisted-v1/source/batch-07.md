# ScholarChain AI review drafts — batch 07 (tasks 121–140)

> **Status: AI_SUGGESTIONS_PENDING_HUMAN_REVIEW.** These are AI-generated suggestions from a session-reported `claude-opus-5-5` model (not independently verified). They are not human reviews or gold labels. Record your own decision in each task's decision box; an empty box means not reviewed.

Queue: `review-queue:05c5817f62a70d378829be361b9c9169fc9af18448f7c83c245f1d65bbca6175`  
Work tasks: 7 · Researcher tasks: 13

Rows marked `>> … <<` in the raw data and the 'Name as written' row identify the mention being compared. OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider hypotheses. Lines in _italics_ starting with 'helper:' are exact-string comparisons computed by a script to help reading; they are not judgments.

---
## Task 121 — Researcher

- **pairId:** `resolution-pair:5c70f1f5744429b5080032add48c2223044b01eb97e173ef511a2880dce5560c`
- **evidenceHash:** `096b8b4d8052a4cecbb1c1c56397f81df120005bb9369a30efece07a60e2977c`
- **Question:** do mention A `mention:openalex:W2987954639#6` and B `mention:openalex:W4221142004#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2987954639#6 | mention:openalex:W4221142004#6 |
| Name as written | Ion Stoica | Ion Stoica |
| Author position | 6 of 7 | 6 of 6 |
| ORCID on mention | 0000-0002-5373-0088 (OpenAlex-supplied) | 0000-0002-5373-0088 (OpenAlex-supplied) |
| OpenAlex author ID | A5041920173 | A5041920173 |
| Affiliation | ROR 01an7q238 | ROR 01an7q238 |
| Work title | HyperSched | Balsa: Learning a Query Optimizer Without Expert Demonstrations |
| Year | 2019 | 2022 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4393915683 |
| DOI | 10.1145/3357223.3362719 | 10.1145/3514221.3517885 |
| Coauthors | Richard Liaw, Romil Bhardwaj, Lisa Dunlap, Yitian Zou, Joseph E. Gonzalez, Alexey Tumanov | Zongheng Yang, Wei-Lin Chiang, Sifei Luan, Gautam Mittal, Michael Luo |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01an7q238'] B=['01an7q238'] shared=['01an7q238']_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Ion Stoica" with ROR 01an7q238, but no coauthor is shared between "HyperSched" (2019) and "Balsa: Learning a Query Optimizer Without Expert Demonstrations" (2022), and the topics differ; name plus affiliation alone stays below the agreed bar.

**Supporting evidence:**
- Name exact match: A author#6, B author#6
- enrichment ror=01an7q238 on both target mentions
- Same OpenAlex-supplied observedOrcid 0000-0002-5373-0088 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- Leans same given the distinctive name and shared ROR, but no further corroboration is supplied

<details><summary>Evidence references</summary>

- A `work` `er-evidence:b8800f361dd11f85e58766390e98d06ef8d581cb74716968be22b4bf88576923` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:309`
- A `enrichment` `er-evidence:b884387b24f1790df9320a27af32b5d1d707071bb2a695941b9e93277d3591ea` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3276`
- B `enrichment` `er-evidence:1938dc76c9e0dc2097a12ddc70cb894504f315cdb111b52e26d2da995ad39ced` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1767`
- B `work` `er-evidence:767a6c15668af1ebb3e13845afe9cdf35a87ba1e4480cb52ab5d9bdcf4a67757` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:164`

</details>

**Danny's decision:** ☐ same ☐ different ☑ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Both papers list Ion Stoica with Berkeley affiliation, but Semantic Scholar splits him into two profiles and no checked page lists both papers. Switched same -> uncertain because no source links both papers to one person.

---

## Task 122 — Researcher

- **pairId:** `resolution-pair:d3ea784f5534e9844c60bb47d81e631c668ddcfeb18ee6f4209dee1d722c7f2c`
- **evidenceHash:** `70a87280ef30d50177aabf2f47f985b41b6715b3f5cbe84159d5cd5d7c3b362e`
- **Question:** do mention A `mention:openalex:W2987954639#7` and B `mention:openalex:W2999202099#7` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2987954639#7 | mention:openalex:W2999202099#7 |
| Name as written | Alexey Tumanov | Alexey Tumanov |
| Author position | 7 of 7 | 7 of 7 |
| ORCID on mention | 0009-0005-7862-1477 (OpenAlex-supplied) | 0009-0005-7862-1477 (OpenAlex-supplied) |
| OpenAlex author ID | A5048451114 | A5048451114 |
| Affiliation | ROR 01zkghx44 | ROR 01zkghx44 |
| Work title | HyperSched | Cloudburst |
| Year | 2019 | 2020 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210226185 |
| DOI | 10.1145/3357223.3362719 | 10.14778/3407790.3407836 |
| Coauthors | Richard Liaw, Romil Bhardwaj, Lisa Dunlap, Yitian Zou, Joseph E. Gonzalez, Ion Stoica | Vikram Sreekanti, Chenggang Wu, Xiayue Charles Lin, Johann Schleier-Smith, Joseph E. Gonzalez, Joseph M. Hellerstein |

_helper: shared coauthor normalizedNames = ['joseph e. gonzalez']_
_helper: target-mention ROR A=['01zkghx44'] B=['01zkghx44'] shared=['01zkghx44']_

**AI-proposed label: `same`**

**Note:** Both mentions are last author "Alexey Tumanov" with shared coauthor Joseph E. Gonzalez (A#5, B#5) and the same ROR 01zkghx44 on "HyperSched" (2019) and "Cloudburst" (2020).

**Supporting evidence:**
- Name exact match at author#7 in both
- Shared coauthor in payload: Joseph E. Gonzalez
- enrichment ror=01zkghx44 on both target mentions
- Same OpenAlex-supplied observedOrcid 0009-0005-7862-1477 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- Coauthor and affiliation overlap are correlated
- Titles give limited topic detail

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:7a161e8f658d5d23fbdb9df88972ace0f399ff1cd0ba148767d711f8b5ec3674` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3268`
- A `work` `er-evidence:b8800f361dd11f85e58766390e98d06ef8d581cb74716968be22b4bf88576923` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:309`
- B `enrichment` `er-evidence:1837c1194f74af7f9b9a640934afde1457fea4f7e33622d1d08485b847f74053` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3220`
- B `work` `er-evidence:87dcb262cf41212d9e359b2536c541c3703fe17b2bc508a5440fdb95fc8acf4f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:303`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 123 — Work

- **pairId:** `resolution-pair:d8c2256381c352a0751d7407040ef5f0d4a173895abf23d5b4a65cfc377b722f`
- **evidenceHash:** `2777634234478e05510f41469e5ffa3c1497e22e3556950e34b40ee3f5d1ab40`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3085924233 (article) | OPENALEX W3097770476 (article) |
| Title | TiDB | The CacheLib Caching Engine: Design and Experiences at Scale |
| Year | 2020 | 2020 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4306420647 |
| DOI | 10.14778/3415478.3415535 | — |
| arXiv ID | — | — |
| Pages | 3072-3084 | 753-768 |
| Authors | (22) Dongxu Huang, Qi Liu, Qiu Cui, Zhuhe Fang, Xiaoyu Ma, Fei Xu, Li Shen, Liu Tang, Yuxing Zhou, Menglong Huang, Wan Wei, Cong Liu, Jian Zhang, Jianjun Li, Xuelian Wu … (+7 more) | (11) Benjamin Wagner vom Berg, Daniel S. Berger, Sara McAllister, Isaac Grosof, Sathya Gunasekar, Jimmy Lu, Michael Uhlar, Jim Carrig, Nathan Beckmann, Mor Harchol‐Balter, Gregory R. Ganger |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.14778/3415478.3415535, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3415478.3415535, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.14778/3415478.3415535'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "TiDB" (DOI 10.14778/3415478.3415535, VLDB 2020, 22 authors) and B "The CacheLib Caching Engine: Design and Experiences at Scale" (no DOI, OSDI 2020, 11 authors) have different titles, venues and disjoint authors.

**Supporting evidence:**
- work.title different
- venueId S4210226185 vs S4306420647
- work.authors disjoint

**Conflicting evidence:**
- Same year 2020

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:04bbd977568f2fcbbff11d5d668aa9bdcb5efa08983841b9f42e9b3e513a938a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:257`
- B `work` `er-evidence:9077058943211a3d57147957a5b6b8f33c3099382a96b1b8235ebf3c9e6f8024` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:234`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 124 — Work

- **pairId:** `resolution-pair:a289904d7067045aaa559f39c72b4f8c6d092070ff4cdedb594cfc0245772dc6`
- **evidenceHash:** `3397377c6d8fd7d986d3d667eb82abb858025ded8f2d25511efe281d1d08102d`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3173154111 (article) | OPENALEX W3173572290 (conference-paper) |
| Title | PET: Optimizing Tensor Programs with Partially Equivalent Transformations and Automated Corrections. | T3S: Effective Representation Learning for Trajectory Similarity Computation |
| Year | 2021 | 2021 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210210321 |
| DOI | — | 10.1109/icde51399.2021.00221 |
| arXiv ID | — | — |
| Pages | 37-54 | 2183-2188 |
| Authors | (10) Haojie Wang, Jidong Zhai, Mingyu Gao, Zixuan Ma, Shizhi Tang, Liyan Zheng, Yuanzhi Li, Kaiyuan Rong, Yuanyong Chen, Zhihao Jia | (6) Peilun Yang, Hanchen Wang, Ying Zhang, Lu Qin, Wenjie Zhang, Xuemin Lin |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1109/icde51399.2021.00221, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde51399.2021.00221, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.1109/icde51399.2021.00221'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "PET: Optimizing Tensor Programs with Partially Equivalent Transformations…" (no DOI, OSDI 2021) and B "T3S: Effective Representation Learning for Trajectory Similarity Computation" (10.1109/icde51399.2021.00221) share only the year 2021; titles, venues and authors differ.

**Supporting evidence:**
- work.title unrelated
- venueId S4306420647 vs S4210210321
- work.authors disjoint

**Conflicting evidence:**
- Same year 2021

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:4bc9c48a33ef23748d4aa824a198749991a3ceb52f13c5cc576848a3e5b59d3f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:213`
- B `work` `er-evidence:4cca84856786daafb309cc46b816de6672e0b4d38a38afe8f84952db2502c73e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:211`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 125 — Work

- **pairId:** `resolution-pair:3560db098e4790e104e0c75257598a404e9e7a9ce9cf8cefa2960d2f18c8f0cb`
- **evidenceHash:** `4b194e6f7a377f66f1abfc85e595c6a0f98d3680cb3f1c9fa3df31687530f578`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3096956001 (article) | OPENALEX W4387321645 (conference-paper) |
| Title | AntMan: Dynamic Scaling on GPU Clusters for Deep Learning. | XFaaS: Hyperscale and Low Cost Serverless Functions at Meta |
| Year | 2020 | 2023 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4306420989 |
| DOI | — | 10.1145/3600006.3613155 |
| arXiv ID | — | — |
| Pages | 533-548 | 231-246 |
| Authors | (9) Wencong Xiao, Shiru Ren, Yong Li, Yang Zhang, Pengyang Hou, Zhi Li, Yihui Feng, Wei Lin, Yangqing Jia | (19) Alireza Sahraei, Soteris Demetriou, Amirali Sobhgol, Haoran Zhang, Abhigna Nagaraja, Neeraj Pathak, Girish Joshi, Carla Souza, Bo Huang, Wyatt Cook, Andrii Golovei, Pradeep Venkat, Andrew Mcfague, Dimitrios Skarlatos, Vipul Patel … (+4 more) |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3600006.3613155, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3600006.3613155, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.1145/3600006.3613155'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "AntMan: Dynamic Scaling on GPU Clusters for Deep Learning." (no DOI, OSDI 2020) and B "XFaaS: Hyperscale and Low Cost Serverless Functions at Meta" (10.1145/3600006.3613155, 2023) have different titles, years and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2020 vs 2023
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:7e6eb194eea3dec822758e4861d17383b1296911fe7ca5a337f3a4a0b91673d1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:240`
- B `work` `er-evidence:e6c585fd47f52f3607e6f0f73466f52acd709aa50d66f56af47b58bb7f8eb2f4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:68`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 126 — Researcher

- **pairId:** `resolution-pair:ca4cb14d93abd300ebfc521616d5d86ae11451d6d5c2e07455142ae0000fbf19`
- **evidenceHash:** `547162e57e76ff98cc915b327c0fd44f8ec9fd1e2f7cf89c3a7058e7d79e79bd`
- **Question:** do mention A `mention:openalex:W2803846618#3` and B `mention:openalex:W3029978369#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2803846618#3 | mention:openalex:W3029978369#6 |
| Name as written | Jieping Ye | Jieping Ye |
| Author position | 3 of 3 | 6 of 8 |
| ORCID on mention | 0000-0001-8662-5818 (OpenAlex-supplied) | 0000-0001-8662-5818 (OpenAlex-supplied) |
| OpenAlex author ID | A5010419481 | A5010419481 |
| Affiliation | ROR 02ksqcf75 | ROR 02ksqcf75 |
| Work title | Order dispatch in price-aware ridesharing | Predicting Origin-Destination Flow via Multi-Perspective Graph Convolutional Network |
| Year | 2018 | 2020 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210210321 |
| DOI | 10.14778/3204028.3204030 | 10.1109/icde48307.2020.00178 |
| Coauthors | Libin Zheng, Lei Chen | Hongzhi Shi, Quanming Yao, Qi Guo, Yaguang Li, Lingyu Zhang, Yong Li, Yan Liu |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['02ksqcf75'] B=['02ksqcf75'] shared=['02ksqcf75']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Jieping Ye" with the same ROR 02ksqcf75 on mobility-data papers ("Order dispatch in price-aware ridesharing" 2018; "Predicting Origin-Destination Flow via Multi-Perspective Graph Convolutional Network" 2020).

**Supporting evidence:**
- Name exact match: A author#3, B author#6
- enrichment ror=02ksqcf75 on both target mentions
- Topic continuity: ride-hailing / urban mobility data
- Same OpenAlex-supplied observedOrcid 0000-0001-8662-5818 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- Rests on name, affiliation and topic; a reviewer may prefer uncertain

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:bacbaff059905143d24c8c67b1eb830ac71659485fbe94398a6e847c1bfa60dc` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4158`
- A `work` `er-evidence:c731640325bf3ed0f3207cd84485c097b9f274eef0c0e244e9e956f6c68a4174` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:409`
- B `enrichment` `er-evidence:ed913b1fa09caa11117efb41719484c75b62745d7e2e6ce322cb8cab595b3d2e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2992`
- B `work` `er-evidence:ffb84ec67959d2448eb2eb52a82ddfc96f86a265299ebd61f7f8a0e0ace07874` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:276`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 127 — Researcher

- **pairId:** `resolution-pair:4e3ca5a7d2b203fe12e4ae3fabee0338739fd46ab0115968ca84f9ae8aa04d50`
- **evidenceHash:** `3738db61c118cefae1b395316e6462f401cfb94e22ed8d25c517af0257e01ba3`
- **Question:** do mention A `mention:openalex:W2963128714#4` and B `mention:openalex:W4398234451#8` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2963128714#4 | mention:openalex:W4398234451#8 |
| Name as written | Yong Wang | Yuhui Wang |
| Author position | 4 of 9 | 8 of 8 |
| ORCID on mention | — | 0009-0005-4408-2129 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5041179106 |
| Affiliation | ROR 00hhjss72 | ROR 00k642b80 |
| Work title | Overload Control for Scaling WeChat Microservices | PolarDB-MP: A Multi-Primary Cloud-Native Database via Disaggregated Shared Memory |
| Year | 2018 | 2024 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4393915683 |
| DOI | 10.1145/3267809.3267823 | 10.1145/3626246.3653377 |
| Coauthors | Hao Zhou, Ming Chen, Qian Lin, Xiaobin She, Sifan Liu, Rui Gu, Beng Chin Ooi, Junfeng Yang | Xinjun Yang, Yingqiang Zhang, Hao Chen, Feifei Li, Bo Wang, Jing Fang, Chuan Sun |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00hhjss72'] B=['00k642b80'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#4 "Yong Wang" and B author#8 "Yuhui Wang" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Yong" vs "Yuhui"
- No shared coauthors
- enrichment ror differs: 00hhjss72 vs 00k642b80

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A mention has no ORCID

<details><summary>Evidence references</summary>

- A `work` `er-evidence:713f9afc8a05b3a899ebff84c0046f7b89ed1f53f64fb0843fcce7ffae2b1648` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:331`
- A `enrichment` `er-evidence:89ffebc275230e6c483f0dcad4086392b28a70e7a717d8bf32edc8d460ff7045` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3474`
- B `enrichment` `er-evidence:11df23920fa8a002432bf3414e3f63a697ae2ac7a892d4f2c0a10dbb9acadcb5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:493`
- B `work` `er-evidence:fa1a30705fe6976d1d84d39fa4d21311edffd2530dd4b5803ffab9538122275c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:44`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 128 — Researcher

- **pairId:** `resolution-pair:d055798cc098fe9da0612a14791cc5a207d03d030aa2baccb195c5c3e64db64f`
- **evidenceHash:** `687601e8c970fb4f4e892b7129e3ccd0f774d69a9b7cb920e8ebd4665dce0ff5`
- **Question:** do mention A `mention:openalex:W3145232008#11` and B `mention:openalex:W4243064622#11` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3145232008#11 | mention:openalex:W4243064622#11 |
| Name as written | Jeff Naughton | Jeff Naughton |
| Author position | 11 of 15 | 11 of 13 |
| ORCID on mention | 0000-0002-3710-8096 (OpenAlex-supplied) | 0000-0002-3710-8096 (OpenAlex-supplied) |
| OpenAlex author ID | A5017678555 | A5017678555 |
| Affiliation | ROR 00njsd438 | ROR 00njsd438 |
| Work title | Technical Perspective: | DIFF: a relational interface for large-scale data explanation |
| Year | 2018 | 2020 |
| Venue ID | venue:openalex:S47508943 | venue:openalex:S78926909 |
| DOI | 10.1145/3277006.3277015 | 10.1007/s00778-020-00633-6 |
| Coauthors | Pradap Konda, Sanjib Das, Paul Suganthan G.C., Philip Martinkus, Adel Ardalan, Jeffrey R. Ballard, Yash Govind, Han Li, Fatemah Panahi, Haojun Zhang, Shishir Prasad, Ganesh Krishnan, Rohit Deep, Vijay Raghavendra | Firas Abuzaid, Peter Kraft, Sahaana Suri, Edward Gan, Eric Xu, Atul Shenoy, Asvin Ananthanarayan, John Sheu, Erik Meijer, Xi Wu, Peter Bailis, Matei Zaharia |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00njsd438'] B=['00njsd438'] shared=['00njsd438']_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Jeff Naughton" with ROR 00njsd438, but no coauthor is shared between the 15-author "Technical Perspective:" (2018) and the 13-author "DIFF: a relational interface for large-scale data explanation" (2020); name plus affiliation alone stays below the agreed bar.

**Supporting evidence:**
- Name exact match: author#11 in both
- enrichment ror=00njsd438 on both target mentions
- Same OpenAlex-supplied observedOrcid 0000-0002-3710-8096 (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- A title is truncated, limiting topic comparison

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:a49712761aa22939279d07c3cfc8b9124e0c4ee52cbe52ac095dae20ea10fe33` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2385`
- A `work` `er-evidence:b13c23e42fcaedcadc0070447130bdb28189aac6c7b466d69ea79e91cff520be` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:218`
- B `work` `er-evidence:0f8f0e46098014be9c073e4b5d5243aa64f0c13280ecd99819f84db64345b688` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:157`
- B `enrichment` `er-evidence:9571779710f027f288282ab95147210199d73f7a065c26a818ecb20bb8549b5b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1686`

</details>

**Danny's decision:** ☐ same ☐ different ☑ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Jeff Naughton is listed on the SIGMOD Record Magellan highlight and on DIFF, but no checked source ties the two together. Switched same -> uncertain because no source links both papers to one person.

---

## Task 129 — Researcher

- **pairId:** `resolution-pair:ed46e40dc5283af7c03f6e885e51e936da7fc8db45f2890d66a9c6c05128ddab`
- **evidenceHash:** `411233d494e3a4579bc48b31389a14b74749ea06bda72e8c073c27bda0d1cf84`
- **Question:** do mention A `mention:openalex:W2795104036#5` and B `mention:openalex:W2951217911#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2795104036#5 | mention:openalex:W2951217911#6 |
| Name as written | Xiaofang Zhou | Xiaofang Zhou |
| Author position | 5 of 5 | 6 of 6 |
| ORCID on mention | 0000-0001-6343-1455 (OpenAlex-supplied) | 0000-0001-6343-1455 (OpenAlex-supplied) |
| OpenAlex author ID | A5051566631 | A5051566631 |
| Affiliation | ROR 00rqy9422 | ROR 00rqy9422 |
| Work title | Joint Event-Partner Recommendation in Event-Based Social Networks | Social Influence-Based Group Representation Learning for Group Recommendation |
| Year | 2018 | 2019 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210210321 |
| DOI | 10.1109/icde.2018.00088 | 10.1109/icde.2019.00057 |
| Coauthors | Hongzhi Yin, Lei Zou, Quoc Viet Hung Nguyen, Zi Huang | Hongzhi Yin, Qinyong Wang, Kai Zheng, Zhixu Li, Jiali Yang |

_helper: shared coauthor normalizedNames = ['hongzhi yin']_
_helper: target-mention ROR A=['00rqy9422'] B=['00rqy9422'] shared=['00rqy9422']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Xiaofang Zhou" with shared coauthor Hongzhi Yin (author#1 in both), the same ROR 00rqy9422, and social recommendation topics (event-partner recommendation 2018; group recommendation 2019).

**Supporting evidence:**
- Name exact match: A author#5, B author#6
- Shared coauthor in payload: Hongzhi Yin
- enrichment ror=00rqy9422 on both target mentions
- Topic continuity: recommendation in social networks
- Same OpenAlex-supplied observedOrcid 0000-0001-6343-1455 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- All hints OpenAlex-derived

<details><summary>Evidence references</summary>

- A `work` `er-evidence:b17891a3880acf2542d0f3e1df29aeeacdab5a51ef0379454bcc1eb3249a5d85` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:429`
- A `enrichment` `er-evidence:e477d59296728311fe28ded1ff0d3d3ed5c12560a625822b448ba6082688b962` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4365`
- B `enrichment` `er-evidence:0c369c179c09ab1c41dc4bde76f596ee808c8cf570699bf7656dfc4550624b97` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3552`
- B `work` `er-evidence:0ccdee0176c2d55656156cdd0a748ea8338c91d62d9a619bc0b43ce12c9aa5ef` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:339`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 130 — Researcher

- **pairId:** `resolution-pair:88aa4f38ca153032b673a32fed122ed8445867c9cff1f36d22c9206d1b4084c5`
- **evidenceHash:** `ad3e9ae4e5e94d143fdc2619452bf82f061969b64af690849d4e54132b3fd9e0`
- **Question:** do mention A `mention:openalex:W3175195073#7` and B `mention:openalex:W4396755233#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3175195073#7 | mention:openalex:W4396755233#4 |
| Name as written | Filip Murlak | Filip Murlak |
| Author position | 7 of 10 | 4 of 5 |
| ORCID on mention | 0000-0003-0989-3717 (OpenAlex-supplied) | 0000-0003-0989-3717 (OpenAlex-supplied) |
| OpenAlex author ID | A5037986297 | A5037986297 |
| Affiliation | ROR 039bjqg32 | ROR 039bjqg32 |
| Work title | Threshold queries in theory and in the wild | Static Analysis of Graph Database Transformations |
| Year | 2022 | 2023 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S7407087293 |
| DOI | 10.14778/3510397.3510407 | 10.1145/3584372.3588654 |
| Coauthors | Angela Bonifati, Stefania Dumbrava, George Fletcher, Jan Hidders, Matthias Hofer, Wim Martens, Joshua Shinavier, Sławek Staworko, Dominik Tomaszuk | Iovka Boneva, Benoît Groz, Jan Hidders, Slawek Staworko |

_helper: shared coauthor normalizedNames = ['jan hidders']_
_helper: target-mention ROR A=['039bjqg32'] B=['039bjqg32'] shared=['039bjqg32']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Filip Murlak" with shared coauthors Jan Hidders and Sławek/Slawek Staworko, the same ROR 039bjqg32, and graph-query theory topics ("Threshold queries in theory and in the wild" 2022; "Static Analysis of Graph Database Transformations" 2023).

**Supporting evidence:**
- Name exact match: A author#7, B author#4
- Shared coauthor Jan Hidders; Sławek vs Slawek Staworko is a diacritic variant
- enrichment ror=039bjqg32 on both target mentions
- Topic continuity: graph database theory
- Same OpenAlex-supplied observedOrcid 0000-0003-0989-3717 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- All hints OpenAlex-derived

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:263d9d3805d00b4f9c9caa2a77d1398089f5c2c49db44843decf7b898a5e7aa4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2173`
- A `work` `er-evidence:97b60c34cef450a6e3ac37ed57ff6a650ca52aaf8f12ee4d4da12102842cc14b` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:199`
- B `enrichment` `er-evidence:9924afe2f62bf69420f2706982a871b6e8115cd56a7b663fec2b001c52828fcd` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:571`
- B `work` `er-evidence:e60912634f16e2a4e88934f26eb5ea77e9c0dc3eb6e899ba2a1ae31bfbd1eba6` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:51`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 131 — Work

- **pairId:** `resolution-pair:467370ecde92c4e89eea8a54f968c6dca00b34173a18ca2462cfa1f32342b3ff`
- **evidenceHash:** `89e7cfd3b62310e6534fc2c3a11fa1828e7789781d8032b07a5bb0e02b0e60f8`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3173154111 (article) | OPENALEX W3176377144 (conference-paper) |
| Title | PET: Optimizing Tensor Programs with Partially Equivalent Transformations and Automated Corrections. | Authenticated Keyword Search in Scalable Hybrid-Storage Blockchains |
| Year | 2021 | 2021 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210210321 |
| DOI | — | 10.1109/icde51399.2021.00091 |
| arXiv ID | — | — |
| Pages | 37-54 | 996-1007 |
| Authors | (10) Haojie Wang, Jidong Zhai, Mingyu Gao, Zixuan Ma, Shizhi Tang, Liyan Zheng, Yuanzhi Li, Kaiyuan Rong, Yuanyong Chen, Zhihao Jia | (5) Ce Zhang, Cheng Xu, Haixin Wang, Jianliang Xu, Byron Choi |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1109/icde51399.2021.00091, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1109/icde51399.2021.00091, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.1109/icde51399.2021.00091'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "PET: Optimizing Tensor Programs…" (no DOI, OSDI 2021) and B "Authenticated Keyword Search in Scalable Hybrid-Storage Blockchains" (10.1109/icde51399.2021.00091) share only the year 2021; titles, venues and authors differ.

**Supporting evidence:**
- work.title unrelated
- venueId S4306420647 vs S4210210321
- work.authors disjoint

**Conflicting evidence:**
- Same year 2021

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:4bc9c48a33ef23748d4aa824a198749991a3ceb52f13c5cc576848a3e5b59d3f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:213`
- B `work` `er-evidence:909869c222154337058817e2344e0f218220f288c1a9b705545263b42a113c0f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:190`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 132 — Researcher

- **pairId:** `resolution-pair:d37a4841608e0fcd8aa7209f961ad1aa7dea519140d8d543d424f9c55f889680`
- **evidenceHash:** `98b2b4bcac963678afe5348dfd5f6fa61794640bf48613040b5803e851709699`
- **Question:** do mention A `mention:openalex:W4288079579#3` and B `mention:openalex:W4388041408#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4288079579#3 | mention:openalex:W4388041408#2 |
| Name as written | Wei Wang | Wei Wang |
| Author position | 3 of 5 | 2 of 5 |
| ORCID on mention | 0000-0002-2990-229X (OpenAlex-supplied) | 0000-0002-2990-229X (OpenAlex-supplied) |
| OpenAlex author ID | A5100391928 | A5100391928 |
| Affiliation | ROR 00q4vv597 | ROR 00q4vv597 |
| Work title | Semi-dynamic load balancing | Golgi |
| Year | 2020 | 2023 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S7407088165 |
| DOI | 10.1145/3419111.3421299 | 10.1145/3620678.3624645 |
| Coauthors | Chen Chen, Qizhen Weng, Baochun Li, Bo Li | Suyi Li, Jun Yang, Guangzhen Chen, Daohe Lu |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00q4vv597'] B=['00q4vv597'] shared=['00q4vv597']_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Wei Wang" with ROR 00q4vv597, but no coauthor is shared (A: Chen Chen, Qizhen Weng, Baochun Li, Bo Li; B: Suyi Li, Jun Yang, Guangzhen Chen, Daohe Lu); "Wei Wang" is a very common name.

**Supporting evidence:**
- Name exact match: A author#3, B author#2
- enrichment ror=00q4vv597 on both target mentions
- Both in venue S7407088165 (2020, 2023)
- Same OpenAlex-supplied observedOrcid 0000-0002-2990-229X (provider hypothesis only)

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- Common name; title-level topics ("Semi-dynamic load balancing", "Golgi") too thin to compare

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:14582919ba249c9d2546830d013de6de62ab27fea5b492ccaab493fc39f04fbf` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1475`
- A `work` `er-evidence:646ed0e881b65665cef0beac414b875ddb64f458b30f797766cb218374a4b264` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:137`
- B `enrichment` `er-evidence:97b56bd65191a507b55e020a821e46e14a2c79ee2011a7dd90c94ade70246d6c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:663`
- B `work` `er-evidence:abeeb930f85f1b7fc3801805c6f14255864fd38868568e3b5d843b23d82f9aa5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:60`

</details>

**Danny's decision:** ☐ same ☐ different ☑ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Both papers list a Wei Wang at HKUST, but no source links them; Semantic Scholar names the 2020 author "Wen Wang". Switched same -> uncertain because no source links both papers to one person.

---

## Task 133 — Researcher

- **pairId:** `resolution-pair:935b2d38b5b6c95be60f94e1409041bf9ec5c69a8db0b8b4d52f79b52a9df1a0`
- **evidenceHash:** `5bb0ba3b3883d52ad66e8f97ff5f5a4d8cd7db2a8d0aba7eefd944ac894cd5aa`
- **Question:** do mention A `mention:openalex:W2939050176#5` and B `mention:openalex:W2963431420#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2939050176#5 | mention:openalex:W2963431420#4 |
| Name as written | Jun Zhao | Jun Zhao |
| Author position | 5 of 6 | 4 of 8 |
| ORCID on mention | 0000-0002-3004-7091 (OpenAlex-supplied) | — |
| OpenAlex author ID | A5071321132 | — |
| Affiliation | ROR 02e7b5302 | ROR 02e7b5302 |
| Work title | Efficient Estimation of Heat Kernel PageRank for Local Clustering | Collecting and Analyzing Multidimensional Data with Local Differential Privacy |
| Year | 2019 | 2019 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210210321 |
| DOI | 10.1145/3299869.3319886 | 10.1109/icde.2019.00063 |
| Coauthors | Renchi Yang, Xiaokui Xiao, Zhewei Wei, Sourav S. Bhowmick, Rong-Hua Li | Ning Wang, Xiaokui Xiao, Yin Yang, Siu Cheung Hui, Hyejin Shin, Junbum Shin, Ge Yu |

_helper: shared coauthor normalizedNames = ['xiaokui xiao']_
_helper: target-mention ROR A=['02e7b5302'] B=['02e7b5302'] shared=['02e7b5302']_

**AI-proposed label: `same`**

**Note:** Both mentions are "Jun Zhao" in 2019 papers sharing coauthor Xiaokui Xiao (author#2 in both) and the same ROR 02e7b5302.

**Supporting evidence:**
- Name exact match: A author#5, B author#4
- Shared coauthor in payload: Xiaokui Xiao
- enrichment ror=02e7b5302 on both target mentions
- Same year 2019

**Conflicting evidence:**
- Topics differ: heat-kernel PageRank (SIGMOD) vs local differential privacy (ICDE)

**Limitations / missing information:**
- "Jun Zhao" is a common name; coauthor and affiliation overlap are correlated
- B mention has no ORCID; A observedOrcid is OpenAlex-supplied only
- A reviewer may prefer uncertain

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:964e9b0ae918fe3ad0e79037234f94b03e53ac2db81d42581e1de583c13b8ad0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3752`
- A `work` `er-evidence:e0918f64c8eeaf5c71ce8f3e79aac8b3861a06efbe4aa63d02e5c466ae492fa9` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:358`
- B `work` `er-evidence:ec3e4de73bbb8fd85736344e239e8959865b9a4abff9cfd2df326339630b30b0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:329`
- B `enrichment` `er-evidence:f40b226d1ef0dbc234f09ab0fc541eec679fbd8669d9df32eb08c2aa302e6ec9` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3444`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 134 — Researcher

- **pairId:** `resolution-pair:45b63afe055db72a575a76b611aef40cee920ecdbad4ec7d809714e96e291c1f`
- **evidenceHash:** `cc5f0b58ec5d26de16175f88cfdd82b808171e8d5820db313a1e261a07affe34`
- **Question:** do mention A `mention:openalex:W3031161010#3` and B `mention:openalex:W3174969457#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3031161010#3 | mention:openalex:W3174969457#6 |
| Name as written | Feifei Li | Feifei Li |
| Author position | 3 of 5 | 6 of 8 |
| ORCID on mention | 0009-0003-0770-5775 (OpenAlex-supplied) | — |
| OpenAlex author ID | A5100450470 | — |
| Affiliation | ROR 03r0ha626 | — |
| Work title | FalconDB: Blockchain-based Collaborative Database | ResTune: Resource Oriented Tuning Boosted by Meta-Learning for Cloud Databases |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4393915683 |
| DOI | 10.1145/3318464.3380594 | 10.1145/3448016.3457291 |
| Coauthors | Yanqing Peng, Min Du, Raymond Cheng, Dawn Song | Xinyi Zhang, Hong Wu, Zhuo Chang, Shuowei Jin, Jian Tan, Tieying Zhang, Bin Cui |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['03r0ha626'] B=- shared=none_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Feifei Li" in SIGMOD papers, but no coauthor is shared, B has no affiliation or identifiers, and the topics differ (blockchain collaborative database 2020; cloud-database tuning 2021).

**Supporting evidence:**
- Name exact match: A author#3, B author#6
- Same venueId S4393915683

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- B mention has no ORCID, OpenAlex author id or affiliation
- A observedOrcid 0009-0003-0770-5775 is OpenAlex-supplied only

<details><summary>Evidence references</summary>

- A `work` `er-evidence:b687b5023963cfc7bfd0ade65f83e56760fb6b50f796494204f6804225021bb8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:271`
- A `enrichment` `er-evidence:f7712fcb437510b2eec5f9391a0d4fadb6161ecc98c791213a1feda2573a4bf7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2939`
- B `work` `er-evidence:b91380e05fdc6fdc92131fb044a70a6687f64c66ee4f04e844c65caa439b4a8d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:200`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: FalconDB PDF is hosted on https://users.cs.utah.edu/~lifeifei/ (homepage says now at Alibaba); ResTune lists Feifei Li, Alibaba, lifeifei@alibaba-inc.com.

---

## Task 135 — Work

- **pairId:** `resolution-pair:5957914190c786c33ca30cd906c7109c7c422ba901645c16b6ec5e5b7605d82a`
- **evidenceHash:** `b0c3fb960dc7be43486cb029d418ee0ee59da2a288c550f053697b972e15766c`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3092725982 (article) | OPENALEX W3164254023 (article) |
| Title | Protean: VM allocation service at scale | Updatable learned index with precise positions |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210226185 |
| DOI | — | 10.14778/3457390.3457393 |
| arXiv ID | — | — |
| Pages | 845-861 | 1276-1288 |
| Authors | (11) Ori Hadary, Luke Marshall, Ishai Menache, Abhisek Pan, Esaias E Greeff, David Pascal Dion, Star Dorminey, Shailesh N. Joshi, Yang Chen, Mark Russinovich, Thomas Moscibroda | (6) Jiacheng Wu, Yong Zhang, Shimin Chen, Jin Wang, Yu Chen, Chunxiao Xing |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.14778/3457390.3457393, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.14778/3457390.3457393, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.14778/3457390.3457393'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Protean: VM allocation service at scale" (no DOI, OSDI 2020) and B "Updatable learned index with precise positions" (10.14778/3457390.3457393, 2021) have different titles, years, venues and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2020 vs 2021
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:775ddc86b78c396a9374a7b011e3383b0c9f216105f8b549078549b484d66a60` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:254`
- B `work` `er-evidence:8267452962081e577b518d746f23c11e9dbbed831c494d5c8c538f00cd7adb06` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:214`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 136 — Work

- **pairId:** `resolution-pair:2172ae4d89522be8de0e868d7c6f5a469ac4718abbcc497183ce263eb520f7b8`
- **evidenceHash:** `502113c428acb2038e33f88925a9f4358b98fceb9eade08ac78099e512161e47`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2779573052 (conference-paper) | OPENALEX W3095227533 (article) |
| Title | Designing Fair Ranking Schemes | Twine: A Unified Cluster Management System for Shared Infrastructure |
| Year | 2019 | 2020 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4306420647 |
| DOI | 10.1145/3299869.3300079 | — |
| arXiv ID | — | — |
| Pages | 1259-1276 | 787-803 |
| Authors | (4) Abolfazl Asudeh, H. V. Jagadish, Julia Stoyanovich, Gautam Das | (20) Chunqiang Tang, Kenny Yu, Kaushik Veeraraghavan, Jonathan Kaldor, Scott Michelson, Thawan Kooburat, Aravind Anbudurai, Matthew Clark, Kabir Gogia, Long Cheng, Ben Christensen, Alex Gartrell, Maxim Khutornenko, Sachin Kulkarni, Marcin Pawłowski … (+5 more) |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3299869.3300079, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3299869.3300079, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1145/3299869.3300079'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Designing Fair Ranking Schemes" (DOI 10.1145/3299869.3300079, 2019) and B "Twine: A Unified Cluster Management System for Shared Infrastructure" (no DOI, OSDI 2020) have unrelated titles, different years and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2019 vs 2020
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:de8a953b9fbef949ff0a7bd7cce6c218954e0ce8eba2582af15ecc5430614d2a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:441`
- B `work` `er-evidence:89c723a4492d89040048728e01108ac1620308c9f1ddb4728304675c3e7d5bb0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:249`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 137 — Work

- **pairId:** `resolution-pair:5ea6d7eea09cdb2dcc77e2b5f488090f837aa5afa684e025b5b0070afab5b579`
- **evidenceHash:** `74a26d88a600dd15e1e29256fd237766eabd1a923bf25e27ac4ab8c29d5f094f`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3095227533 (article) | OPENALEX W3210974992 (conference-paper) |
| Title | Twine: A Unified Cluster Management System for Shared Infrastructure | Mu |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S7407088165 |
| DOI | — | 10.1145/3472883.3487014 |
| arXiv ID | — | — |
| Pages | 787-803 | 168-181 |
| Authors | (20) Chunqiang Tang, Kenny Yu, Kaushik Veeraraghavan, Jonathan Kaldor, Scott Michelson, Thawan Kooburat, Aravind Anbudurai, Matthew Clark, Kabir Gogia, Long Cheng, Ben Christensen, Alex Gartrell, Maxim Khutornenko, Sachin Kulkarni, Marcin Pawłowski … (+5 more) | (10) Viyom Mittal, Shixiong Qi, Ratnadeep Bhattacharya, Xiaosu Lyu, Junfeng Li, Sameer G. Kulkarni, Dan Li, Jinho Hwang, K. K. Ramakrishnan, Timothy Wood |
| Observed identifiers | — | namespace=openalex.doi, value=https://doi.org/10.1145/3472883.3487014, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3472883.3487014, interpretation=SOURCE_OBSERVATION |

_helper: normalized DOI A=- B=['10.1145/3472883.3487014'] -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Twine: A Unified Cluster Management System for Shared Infrastructure" (no DOI, OSDI 2020) and B "Mu" (10.1145/3472883.3487014, 2021) have different titles, years, venues and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2020 vs 2021
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:89c723a4492d89040048728e01108ac1620308c9f1ddb4728304675c3e7d5bb0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:249`
- B `work` `er-evidence:4248fc22c42f1b0171985f9d8b7d6f85d6fc71037a325c264e15ce5c4e4eeba8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:169`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 138 — Researcher

- **pairId:** `resolution-pair:9963b41b22b9373b2c398dcb9b1ed8e9331e1d99a771e7c774f8354e343451ce`
- **evidenceHash:** `7c0126455098d3cbaaeebc2785c845e16a02bd807c89d70c52e2a8c39747370e`
- **Question:** do mention A `mention:openalex:W2903965607#6` and B `mention:openalex:W2914529374#7` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2903965607#6 | mention:openalex:W2914529374#7 |
| Name as written | Jignesh M. Patel | Jignesh M. Patel |
| Author position | 6 of 6 | 7 of 7 |
| ORCID on mention | 0000-0003-3653-2538 (OpenAlex-supplied) | — |
| OpenAlex author ID | A5069237428 | — |
| Affiliation | ROR 01y2jtd41 | ROR 01y2jtd41 |
| Work title | Scaling-up in-memory datalog processing | Tuple-oriented Compression for Large-scale Mini-batch Stochastic Gradient Descent |
| Year | 2019 | 2019 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4393915683 |
| DOI | 10.14778/3311880.3311886 | 10.1145/3299869.3300070 |
| Coauthors | Zhiwei Fan, Jianqiao Zhu, Zuyu Zhang, Aws Albarghouthi, Paraschos Koutris | Fengan Li, Lingjiao Chen, Yijing Zeng, Arun Kumar, Xi Wu, Jeffrey F. Naughton |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01y2jtd41'] B=['01y2jtd41'] shared=['01y2jtd41']_

**AI-proposed label: `uncertain`**

**Note:** Both mentions are "Jignesh M. Patel" with ROR 01y2jtd41 in 2019, but there is no shared coauthor and the topics differ (in-memory datalog processing; tuple-oriented compression for SGD).

**Supporting evidence:**
- Name exact match including middle initial: A author#6, B author#7
- enrichment ror=01y2jtd41 on both target mentions
- Same year 2019

**Conflicting evidence:**
- No shared coauthors

**Limitations / missing information:**
- B mention has no ORCID; A observedOrcid 0000-0003-3653-2538 is OpenAlex-supplied only
- Leans same; name plus affiliation alone stays below the agreed bar

<details><summary>Evidence references</summary>

- A `work` `er-evidence:b494e7c9c287b413eea2a17f0b3848296886689d3af01870f721b8e244446d28` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:372`
- A `enrichment` `er-evidence:f88fa3fc7699bafbda311b89eb7815952077b63a241315bf7d1e910f1b2c8017` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3858`
- B `enrichment` `er-evidence:95e2f418d70a4c2261ca575035772943ac4a45c5be4746173760dc93710a8955` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3799`
- B `work` `er-evidence:e9ad95ef7180bf936ac95244b80ad4afe66bb3ca9496abfa4a488ce4b79d5337` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:363`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> Source check by Claude (2026-10-20), not Danny: Semantic Scholar assigns the same author ID on both papers (api.semanticscholar.org).

---

## Task 139 — Researcher

- **pairId:** `resolution-pair:9f3c6c16e57c505e431a5f59bf2c5f3ca0f79e610c031ed9d1f89d64f517bfa3`
- **evidenceHash:** `1202ee1fa826322a53fb5b324fe556eaa08dbf41f7e95cc6b61de7c91aec477c`
- **Question:** do mention A `mention:openalex:W2970773487#6` and B `mention:openalex:W4381326861#7` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2970773487#6 | mention:openalex:W4381326861#7 |
| Name as written | Bo Li | Bei Li |
| Author position | 6 of 9 | 7 of 21 |
| ORCID on mention | — | 0009-0002-8102-978X (OpenAlex-supplied) |
| OpenAlex author ID | — | A5100356464 |
| Affiliation | ROR 047426m28 | ROR 00njsd438; ROR 01vy4gh70 |
| Work title | Efficient task-specific data valuation for nearest neighbor algorithms | PG-Schema: Schemas for Property Graphs |
| Year | 2019 | 2023 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4387289859 |
| DOI | 10.14778/3342263.3342637 | 10.1145/3589778 |
| Coauthors | Ruoxi Jia, David Dao, Boxin Wang, Frances Ann Hubis, Nezihe Merve Gurel, Ce Zhang, Costas Spanos, Dawn Song | Renzo Angles, Angela Bonifati, Stefania Dumbrava, George Fletcher, Alastair Green, Jan Hidders, Leonid Libkin, Victor Marsault, Wim Martens, Filip Murlak, Stefan Plantikow, Ognjen Savkovic, Michael Schmidt, Juan Sequeda, Slawek Staworko, Dominik Tomaszuk, Hannes Voigt, Domagoj Vrgoc, Mingxi Wu, Dusan Zivkovic |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['047426m28'] B=['00njsd438', '01vy4gh70'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#6 "Bo Li" and B author#7 "Bei Li" differ in given name (Bo vs Bei); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Bo" vs "Bei"
- No shared coauthors
- enrichment ror sets disjoint: {047426m28} vs {00njsd438, 01vy4gh70}

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- A mention has no ORCID

<details><summary>Evidence references</summary>

- A `work` `er-evidence:03ef2208aa7734a65889ae31546d72edf8c84050607e61b7e9aa7486493c3ba4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:325`
- A `enrichment` `er-evidence:d8b48e20bd0581b75d1b424d59118a2259c3dc13bfe95323da032206070c8db8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3406`
- B `work` `er-evidence:3aebf9384d47efd5daac4e2bc465ca4d8d9550b7d1e463ad7ba06c50b0ba0b04` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:98`
- B `enrichment` `er-evidence:4dd57a01596d41dc3351c3d1b5149b217d4ef044663e9797a9e5ada1e2548df7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1079`
- B `enrichment` `er-evidence:f617abb38e03ab0c30456940a95f613f10df2741cb856ac9dfdb582ca4d28723` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1080`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 140 — Researcher

- **pairId:** `resolution-pair:557c111616e3fb2a083d224623cd5800dde2311b4bb0a8f98a39faa1c0daba53`
- **evidenceHash:** `abc679a65a91da026606c0e921c856d475e9e5d67778b439efec6fd44c95197e`
- **Question:** do mention A `mention:openalex:W2914529374#2` and B `mention:openalex:W2948279890#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2914529374#2 | mention:openalex:W2948279890#3 |
| Name as written | Lingjiao Chen | Leshang Chen |
| Author position | 2 of 7 | 3 of 5 |
| ORCID on mention | 0009-0001-4473-7544 (OpenAlex-supplied) | — |
| OpenAlex author ID | A5003134390 | A5026685207 |
| Affiliation | ROR 01y2jtd41 | ROR 00b30xv10; ROR 01y2jtd41 |
| Work title | Tuple-oriented Compression for Large-scale Mini-batch Stochastic Gradient Descent | Demonstration of Nimbus |
| Year | 2019 | 2019 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4393915683 |
| DOI | 10.1145/3299869.3300070 | 10.1145/3299869.3320231 |
| Coauthors | Fengan Li, Yijing Zeng, Arun Kumar, Xi Wu, Jeffrey F. Naughton, Jignesh M. Patel | Lingjiao Chen, Hongyi Wang, Paraschos Koutris, Arun Kumar |

_helper: shared coauthor normalizedNames = ['arun kumar']_
_helper: target-mention ROR A=['01y2jtd41'] B=['00b30xv10', '01y2jtd41'] shared=['01y2jtd41']_

**AI-proposed label: `different`**

**Note:** A is "Lingjiao Chen" and B is "Leshang Chen"; B's own work lists "Lingjiao Chen" as author#1 and "Leshang Chen" as author#3, so both names appear as separate authors on the same paper.

**Supporting evidence:**
- nameText given names differ: "Lingjiao" vs "Leshang"
- B work.authors contains both Lingjiao Chen (#1) and Leshang Chen (#3) as distinct authorships

**Conflicting evidence:**
- Shared coauthor Arun Kumar and shared ROR 01y2jtd41 (consistent with colleagues, not identity)

**Limitations / missing information:**
- B mention has no ORCID; A observedOrcid is OpenAlex-supplied only

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:9bcff068a13f7d88c608af8dbb852f05d7b6a2d586692653f96f918b9f3b4bfb` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3792`
- A `work` `er-evidence:e9ad95ef7180bf936ac95244b80ad4afe66bb3ca9496abfa4a488ce4b79d5337` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:363`
- B `work` `er-evidence:2f30d3a5350062f212102589eea2835bc3f93d35b027dcc1a49f037bd226079c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:349`
- B `enrichment` `er-evidence:84fde4f844a6308b229c1a1563d54e2a64008a257f4b0ee58dae221f6da5acfc` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3663`
- B `enrichment` `er-evidence:857f9fe5255e851e6d34a3ed464cf4312d66a759f916cce5c4241fad86834df7` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3660`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---
