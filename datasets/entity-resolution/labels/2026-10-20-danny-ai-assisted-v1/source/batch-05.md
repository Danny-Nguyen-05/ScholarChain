# ScholarChain AI review drafts — batch 05 (tasks 81–100)

> **Status: AI_SUGGESTIONS_PENDING_HUMAN_REVIEW.** These are AI-generated suggestions from a session-reported `claude-opus-5-5` model (not independently verified). They are not human reviews or gold labels. Record your own decision in each task's decision box; an empty box means not reviewed.

Queue: `review-queue:05c5817f62a70d378829be361b9c9169fc9af18448f7c83c245f1d65bbca6175`  
Work tasks: 4 · Researcher tasks: 16

Rows marked `>> … <<` in the raw data and the 'Name as written' row identify the mention being compared. OpenAlex author IDs and OpenAlex-supplied ORCIDs are provider hypotheses. Lines in _italics_ starting with 'helper:' are exact-string comparisons computed by a script to help reading; they are not judgments.

---
## Task 81 — Work

- **pairId:** `resolution-pair:93666f5032ef4920164fe2b83cad17c723dc24ff1a41cd782d7bd8b5ced9258a`
- **evidenceHash:** `0146c10de162c1de6fb02bb92859e2d9a8d6f6f216ab723222536a9d12a81933`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | ORCID activity 0000-0003-0832-116X/work/151681314 | ORCID activity 0000-0003-0832-116X/work/151681321 |
| Title | Constant delay algorithms for regular document spanners | Constant Delay Algorithms for Regular Document Spanners |
| Year | publicationYear=2018 | publicationYear=2018 |
| Venue ID | — | — |
| DOI | — | 10.1145/3196959.3196987 |
| arXiv ID | — | — |
| Pages | — | — |
| Authors | ORCID record owner 0000-0003-0832-116X (author list not supplied) | ORCID record owner 0000-0003-0832-116X (author list not supplied) |
| Observed identifiers | wosuid=PPRN:12862028 (self) | doi=10.1145/3196959.3196987 (self); wosuid=WOS:000455483100013 (self) |

_helper: normalized DOI A=- B=['10.1145/3196959.3196987'] -> not comparable_

**AI-proposed label: `uncertain`** — flags: `VERSION_RELATIONSHIP`

**Note:** Both ORCID activities on record 0000-0003-0832-116X carry the title "Constant delay algorithms for regular document spanners" (2018), but A has no DOI and only wosuid=PPRN:12862028, while B has doi=10.1145/3196959.3196987 and wosuid=WOS:000455483100013. The PPRN identifier suggests A may be a preprint-index entry of the published paper; the evidence does not settle whether they are the same publication.

**Supporting evidence:**
- orcid-activity.title identical apart from capitalization
- publicationYear 2018 on both
- Same ORCID record owner 0000-0003-0832-116X (ORCID-sourced)

**Conflicting evidence:**
- Different self identifiers: A wosuid=PPRN:12862028 vs B wosuid=WOS:000455483100013 and doi=10.1145/3196959.3196987
- A observedDoi is null, so no DOI binds A to B

**Limitations / missing information:**
- ORCID activities carry no author list, venue or pages
- Interpreting the PPRN prefix as a preprint index is an inference from the identifier form

<details><summary>Evidence references</summary>

- A `orcid-activity` `er-evidence:b1c4791acc2f6d86f4f7965fe2edf753d202b51165125d87eaff0873e1cc43e5` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:300`
- B `orcid-activity` `er-evidence:6ea31b6added941ade7b54464aa3c40520a988ce3ec43ddefcd9a40d2ba31829` — `snapshot=orcid-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/orcid-activity/part-r-00000:294`

</details>

**Danny's decision:** ☐ same ☐ different ☑ uncertain

**Comments:**

> 

---

## Task 82 — Researcher

- **pairId:** `resolution-pair:5cf86608a13bd8b3a276ca7855af64187910a422fca33a5a6c4c32629a6c893d`
- **evidenceHash:** `9ad748f9eb7f26d7db6d20ac75527be9b086e2d8abc8d5f5f030ab050677d161`
- **Question:** do mention A `mention:openalex:W3014705052#1` and B `mention:openalex:W3029978369#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3014705052#1 | mention:openalex:W3029978369#4 |
| Name as written | Yuliang Li | Yaguang Li |
| Author position | 1 of 5 | 4 of 8 |
| ORCID on mention | — | 0000-0001-9218-0990 (OpenAlex-supplied) |
| OpenAlex author ID | — | A5027731521 |
| Affiliation | — | ROR 02tcm9e24; ROR 00njsd438; ROR 03cve4549 |
| Work title | Deep entity matching with pre-trained language models | Predicting Origin-Destination Flow via Multi-Perspective Graph Convolutional Network |
| Year | 2020 | 2020 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210210321 |
| DOI | 10.14778/3421424.3421431 | 10.1109/icde48307.2020.00178 |
| Coauthors | Jinfeng Li, Yoshihiko Suhara, AnHai Doan, Wang-Chiew Tan | Hongzhi Shi, Quanming Yao, Qi Guo, Lingyu Zhang, Jieping Ye, Yong Li, Yan Liu |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=- B=['00njsd438', '02tcm9e24', '03cve4549'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#1 "Yuliang Li" and B author#4 "Yaguang Li" have different given names; no shared coauthors or affiliation.

**Supporting evidence:**
- nameText given names differ: "Yuliang" vs "Yaguang"
- No shared coauthors
- Topics differ: entity matching with language models vs origin-destination flow prediction

**Conflicting evidence:**
- Same year 2020

**Limitations / missing information:**
- A mention has no ORCID or affiliation

<details><summary>Evidence references</summary>

- A `work` `er-evidence:9c4a8b1d3317d6ea2aa6be01f926e719f090919b58950101615b00924736bece` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:289`
- B `enrichment` `er-evidence:13889181e8387ee25b32051882241db9c157ab16fe261e20d2574a0628742471` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2983`
- B `enrichment` `er-evidence:cb27f59719761d4068ccd16436bc3b28a03c65365682520d172a5c23d9e8f5df` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2984`
- B `enrichment` `er-evidence:f68610d10ad2600bb59b35a370ac1aefcd9ec026ba28a3cfc6a5bc56cea089bf` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2979`
- B `work` `er-evidence:ffb84ec67959d2448eb2eb52a82ddfc96f86a265299ebd61f7f8a0e0ace07874` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:276`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 83 — Researcher

- **pairId:** `resolution-pair:3d759a5e74843c8d1ba95a5e6539a19ab65088a1dc6f1b3fa8d7c1da653c685c`
- **evidenceHash:** `6fdff5dbf04f83fd2459d005503cf4d57edbe366eaaa42845ca3eca8f582c8e2`
- **Question:** do mention A `mention:openalex:W2951217911#5` and B `mention:openalex:W4388041408#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2951217911#5 | mention:openalex:W4388041408#3 |
| Name as written | Jiali Yang | Jun Yang |
| Author position | 5 of 6 | 3 of 5 |
| ORCID on mention | 0000-0002-1560-7660 (OpenAlex-supplied) | 0009-0001-8532-1262 (OpenAlex-supplied) |
| OpenAlex author ID | A5000271322 | A5101789758 |
| Affiliation | ROR 05t8y2r12 | — |
| Work title | Social Influence-Based Group Representation Learning for Group Recommendation | Golgi |
| Year | 2019 | 2023 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S7407088165 |
| DOI | 10.1109/icde.2019.00057 | 10.1145/3620678.3624645 |
| Coauthors | Hongzhi Yin, Qinyong Wang, Kai Zheng, Zhixu Li, Xiaofang Zhou | Suyi Li, Wei Wang, Guangzhen Chen, Daohe Lu |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['05t8y2r12'] B=- shared=none_

**AI-proposed label: `different`**

**Note:** A author#5 "Jiali Yang" and B author#3 "Jun Yang" differ in given name (Jiali vs Jun); no coauthor overlap.

**Supporting evidence:**
- nameText given names differ: "Jiali" vs "Jun"
- No shared coauthors
- Different OpenAlex-supplied ORCIDs (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no affiliation evidence

<details><summary>Evidence references</summary>

- A `work` `er-evidence:0ccdee0176c2d55656156cdd0a748ea8338c91d62d9a619bc0b43ce12c9aa5ef` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:339`
- A `enrichment` `er-evidence:4d1d346c059a7e33e381d95dfe59001c92cb77473e3915b5ff6ba3f9ff37539a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3546`
- B `work` `er-evidence:abeeb930f85f1b7fc3801805c6f14255864fd38868568e3b5d843b23d82f9aa5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:60`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 84 — Researcher

- **pairId:** `resolution-pair:09bdd83b52a354a6cf36504bc8574b5ba63fb302f5d53a5bebb7cc5b228fdcc8`
- **evidenceHash:** `de5ddd7c503f39507d8222bf205db73e0acfbb8e9facff89dc085e94eb6df803`
- **Question:** do mention A `mention:openalex:W2797862701#14` and B `mention:openalex:W4399208444#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2797862701#14 | mention:openalex:W4399208444#2 |
| Name as written | Yang Wang | Yibo Wang |
| Author position | 14 of 20 | 2 of 9 |
| ORCID on mention | 0000-0002-6815-0879 (OpenAlex-supplied) | 0009-0005-1971-3398 (OpenAlex-supplied) |
| OpenAlex author ID | A5100714578 | A5103147568 |
| Affiliation | ROR 01ek73717; ROR 00hhjss72 | ROR 011ashp19 |
| Work title | BigDL | GPTuner: A Manual-Reading Database Tuning System via GPT-Guided Bayesian Optimization |
| Year | 2019 | 2024 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210226185 |
| DOI | 10.1145/3357223.3362707 | 10.14778/3659437.3659449 |
| Coauthors | Jason Jinquan Dai, Yiheng Wang, Xin Qiu, Ding Ding, Yao Zhang, Yanzhang Wang, Xianyan Jia, Cherry Li Zhang, Yan Wan, Zhichao Li, Jiao Wang, Shengsheng Huang, Zhongyuan Wu, Yuhao Yang, Bowen She, Dongjie Shi, Qi Lu, Kai Huang, Guoqiong Song | Jiale Lao, Yufei Li, Jianping Wang, Yunjia Zhang, Zhiyuan Cheng, Wanghu Chen, Mingjie Tang, Jianguo Wang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00hhjss72', '01ek73717'] B=['011ashp19'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#14 "Yang Wang" and B author#2 "Yibo Wang" differ in given name (Yang vs Yibo); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Yang" vs "Yibo"
- No shared coauthors
- enrichment ror sets disjoint: {01ek73717, 00hhjss72} vs {011ashp19}

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:7f23ff95eec85ee7e1670f4b0e01e515a25005e60fdf9568ca996325d47d0dc5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:422`
- A `enrichment` `er-evidence:8acc8f21a9d0c7e6692b419eb03a7837e3993bebace5623d2419d633f590648c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4296`
- A `enrichment` `er-evidence:b93b2632181e59d247bdc69c78038d28148fbe26c93c0d9db954ae53dc42e0ca` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4295`
- B `enrichment` `er-evidence:1d41077ae3d3940b5c47e44fcb42fa86fde7c886dbc225aea2d8680a63225ed0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:412`
- B `work` `er-evidence:a1496fd5ac846f7d9990387455b6780ffe67d59e7e2a70eb58e527bf3ab463c8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:37`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 85 — Researcher

- **pairId:** `resolution-pair:6200161157f1139a3d32b322989ef6c1e3d54bbf6c3e79eb9b27ce5bde238f52`
- **evidenceHash:** `a13bc824d5daa7ffd10890fc185e4261670a971f5b7533a7d3ad2e8c6653db73`
- **Question:** do mention A `mention:openalex:W3029978369#4` and B `mention:openalex:W3145728363#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3029978369#4 | mention:openalex:W3145728363#3 |
| Name as written | Yaguang Li | Yuliang Li |
| Author position | 4 of 8 | 3 of 7 |
| ORCID on mention | 0000-0001-9218-0990 (OpenAlex-supplied) | 0000-0002-0602-149X (OpenAlex-supplied) |
| OpenAlex author ID | A5027731521 | A5100750716 |
| Affiliation | ROR 02tcm9e24; ROR 00njsd438; ROR 03cve4549 | — |
| Work title | Predicting Origin-Destination Flow via Multi-Perspective Graph Convolutional Network | Annotating Columns with Pre-trained Language Models |
| Year | 2020 | 2022 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4393915683 |
| DOI | 10.1109/icde48307.2020.00178 | 10.1145/3514221.3517906 |
| Coauthors | Hongzhi Shi, Quanming Yao, Qi Guo, Lingyu Zhang, Jieping Ye, Yong Li, Yan Liu | Yoshihiko Suhara, Jinfeng Li, Dan Zhang, Çağatay Demiralp, Chen Chen, Wang-Chiew Tan |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00njsd438', '02tcm9e24', '03cve4549'] B=- shared=none_

**AI-proposed label: `different`**

**Note:** A author#4 "Yaguang Li" and B author#3 "Yuliang Li" have different given names; no shared coauthors.

**Supporting evidence:**
- nameText given names differ: "Yaguang" vs "Yuliang"
- No shared coauthors
- Different OpenAlex-supplied ORCIDs 0000-0001-9218-0990 vs 0000-0002-0602-149X (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no affiliation evidence

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:13889181e8387ee25b32051882241db9c157ab16fe261e20d2574a0628742471` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2983`
- A `enrichment` `er-evidence:cb27f59719761d4068ccd16436bc3b28a03c65365682520d172a5c23d9e8f5df` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2984`
- A `enrichment` `er-evidence:f68610d10ad2600bb59b35a370ac1aefcd9ec026ba28a3cfc6a5bc56cea089bf` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2979`
- A `work` `er-evidence:ffb84ec67959d2448eb2eb52a82ddfc96f86a265299ebd61f7f8a0e0ace07874` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:276`
- B `work` `er-evidence:f2ef2ec961ccb328f039d863120c449773e030019003e86a9532b7d124b604c9` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:217`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 86 — Researcher

- **pairId:** `resolution-pair:551055d803c019b7eca4c06f56b69dfdc9b8772d054dd0deae1db455443e02c5`
- **evidenceHash:** `9531745aedd4fddf6f6fc69e6f1f1fecdf61cef1861e220545776276dcd6c9a1`
- **Question:** do mention A `mention:openalex:W3096956001#4` and B `mention:openalex:W4402043038#4` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3096956001#4 | mention:openalex:W4402043038#4 |
| Name as written | Yang Zhang | Yuxin Zhang |
| Author position | 4 of 9 | 4 of 10 |
| ORCID on mention | 0000-0002-4170-4798 (OpenAlex-supplied) | 0009-0000-6729-0004 (OpenAlex-supplied) |
| OpenAlex author ID | A5100354683 | A5104254031 |
| Affiliation | ROR 00k642b80 | ROR 041pakw92 |
| Work title | AntMan: Dynamic Scaling on GPU Clusters for Deep Learning. | Combining Small Language Models and Large Language Models for Zero-Shot NL2SQL |
| Year | 2020 | 2024 |
| Venue ID | venue:openalex:S4306420647 | venue:openalex:S4210226185 |
| DOI | — | 10.14778/3681954.3681960 |
| Coauthors | Wencong Xiao, Shiru Ren, Yong Li, Pengyang Hou, Zhi Li, Yihui Feng, Wei Lin, Yangqing Jia | Ju Fan, Zihui Gu, Songyue Zhang, Zui Chen, Lei Cao, Guoliang Li, Samuel Madden, Xiaoyong Du, Nan Tang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00k642b80'] B=['041pakw92'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#4 "Yang Zhang" and B author#4 "Yuxin Zhang" differ in given name (Yang vs Yuxin); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Yang" vs "Yuxin"
- No shared coauthors
- enrichment ror differs: 00k642b80 vs 041pakw92

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:3a976ed2d27bc3df028c6218be3b503385c67db56c99d843c825ea97ff9a7a57` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2614`
- A `work` `er-evidence:7e6eb194eea3dec822758e4861d17383b1296911fe7ca5a337f3a4a0b91673d1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:240`
- B `enrichment` `er-evidence:2663c4808d21fb7f0b3528e46033c4cd56b56bb32fefe1ea6ddce1cda7c434f0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:207`
- B `work` `er-evidence:eac927034deb68a4c47259836c0c94161022705316b86d5597490a22a4dfa064` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:18`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 87 — Researcher

- **pairId:** `resolution-pair:d0b88fe069ce777056129ff2d9fa4061325f429dec235f5e0d6fc9c29f688dda`
- **evidenceHash:** `801c2172cc654c0e0ad43c99b463f423af47bf28c33080a4cc1cc3c4bf266ef3`
- **Question:** do mention A `mention:openalex:W2797862701#13` and B `mention:openalex:W4366492480#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2797862701#13 | mention:openalex:W4366492480#6 |
| Name as written | Zhongyuan Wu | Ziniu Wu |
| Author position | 13 of 20 | 6 of 7 |
| ORCID on mention | 0000-0001-7916-4259 (OpenAlex-supplied) | 0000-0002-4405-0865 (OpenAlex-supplied) |
| OpenAlex author ID | A5075740303 | A5002733135 |
| Affiliation | ROR 01ek73717 | ROR 042nb2s44 |
| Work title | BigDL | Lero: A Learning-to-Rank Query Optimizer |
| Year | 2019 | 2023 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210226185 |
| DOI | 10.1145/3357223.3362707 | 10.14778/3583140.3583160 |
| Coauthors | Jason Jinquan Dai, Yiheng Wang, Xin Qiu, Ding Ding, Yao Zhang, Yanzhang Wang, Xianyan Jia, Cherry Li Zhang, Yan Wan, Zhichao Li, Jiao Wang, Shengsheng Huang, Yang Wang, Yuhao Yang, Bowen She, Dongjie Shi, Qi Lu, Kai Huang, Guoqiong Song | Rong Zhu, Wei Chen, Bolin Ding, Xingguang Chen, Andreas Pfadler, Jingren Zhou |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['01ek73717'] B=['042nb2s44'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#13 "Zhongyuan Wu" and B author#6 "Ziniu Wu" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Zhongyuan" vs "Ziniu"
- No shared coauthors
- enrichment ror differs: 01ek73717 vs 042nb2s44

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:7f23ff95eec85ee7e1670f4b0e01e515a25005e60fdf9568ca996325d47d0dc5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:422`
- A `enrichment` `er-evidence:bf7eb058f0d03e4301708bd6aa2b220b3438a328c01fc1fa296b569e536e7c47` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4297`
- B `enrichment` `er-evidence:28178fdda7a9df5a02be5eb4b07f35a1eb8300fb6f18675e884f4d0754a62967` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1279`
- B `work` `er-evidence:8b5cc35a989d5afac5411c2b964977382929fc219deb261f8d5788d4b28698fd` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:116`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 88 — Researcher

- **pairId:** `resolution-pair:9ed63b8fc2bb9797ee3e90a0c23f9732798688efbab2c5bb34f2aa44970a246c`
- **evidenceHash:** `31bd35840e0b3599db3a2a656f5109ee8a92074491c5f9731a349f475eea5ece`
- **Question:** do mention A `mention:openalex:W2963999972#5` and B `mention:openalex:W4404386171#2` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2963999972#5 | mention:openalex:W4404386171#2 |
| Name as written | Zhenjie Zhang | Zhen Zhang |
| Author position | 5 of 5 | 2 of 10 |
| ORCID on mention | 0009-0000-9080-7489 (OpenAlex-supplied) | 0000-0002-0164-0849 (OpenAlex-supplied) |
| OpenAlex author ID | A5100633297 | A5029095203 |
| Affiliation | — | ROR 04mv4n011 |
| Work title | Elasticutor | Distributed Training of Large Language Models on AWS Trainium |
| Year | 2019 | 2024 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S7407088165 |
| DOI | 10.1145/3299869.3319868 | 10.1145/3698038.3698535 |
| Coauthors | LI Wang, Tom Z. J. Fu, Richard T. B. Ma, Marianne Winslett | Xinwei Fu, Haozheng Fan, Guangtai Huang, Mohammad El-Shabani, Randy Huang, Rahul Solanki, Fei Wu, Ron Diamant, Yida Wang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=- B=['04mv4n011'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#5 "Zhenjie Zhang" and B author#2 "Zhen Zhang" are different given names (Zhenjie vs Zhen) with no shared coauthors, and their OpenAlex-supplied ORCIDs differ.

**Supporting evidence:**
- nameText given names differ: "Zhenjie" vs "Zhen"
- No shared coauthors
- Different OpenAlex-supplied ORCIDs 0009-0000-9080-7489 vs 0000-0002-0164-0849 (provider hypothesis)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- "Zhen" is a prefix of "Zhenjie"; if a source truncated the given name, this would weaken the difference
- A has no affiliation evidence

<details><summary>Evidence references</summary>

- A `work` `er-evidence:945852404468f48ffddecfe0b1024730e327532bc9f703d98dcb9fb124ca7320` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:327`
- B `enrichment` `er-evidence:11b32bd8a5f0e10134a8e0b99cdbbfa53b4314cd61b4f6150f445edef64b1756` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:55`
- B `work` `er-evidence:1996e8128f2622a44821348005ee02a2bb82f2f46c814dc4b521112fbec5df1e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:3`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 89 — Researcher

- **pairId:** `resolution-pair:06b27afdf815d7f1b909e16ad0c84c86d11f9abe5bf38f8a5ee169c23ec2994d`
- **evidenceHash:** `ce17906a373b6d656b03a88f10f3fef00a7a66d3c569e7c5676b52605fbec17b`
- **Question:** do mention A `mention:openalex:W2952493731#3` and B `mention:openalex:W3159219445#9` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2952493731#3 | mention:openalex:W3159219445#9 |
| Name as written | Chao Zhang | Ce Zhang |
| Author position | 3 of 4 | 9 of 9 |
| ORCID on mention | 0000-0003-3009-598X (OpenAlex-supplied) | 0000-0002-8105-7505 (OpenAlex-supplied) |
| OpenAlex author ID | A5100460272 | A5004750246 |
| Affiliation | ROR 047426m28 | ROR 05a28rw58 |
| Work title | Computing Trajectory Similarity in Linear Time: A Generic Seed-Guided Neural Metric Learning Approach | Towards Demystifying Serverless Machine Learning Training |
| Year | 2019 | 2021 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4393915683 |
| DOI | 10.1109/icde.2019.00123 | 10.1145/3448016.3459240 |
| Coauthors | Di Yao, Gao Cong, Jingping Bi | Jiawei Jiang, Shaoduo Gan, Yue Liu, Fanlin Wang, Gustavo Alonso, Ana Klimovic, Ankit Singla, Wentao Wu |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['047426m28'] B=['05a28rw58'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#3 "Chao Zhang" and B author#9 "Ce Zhang" differ in given name (Chao vs Ce); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Chao" vs "Ce"
- No shared coauthors
- enrichment ror differs: 047426m28 vs 05a28rw58

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:8be67b0c58bab1ad6008149b00e303abac40d59ffa691942b69129af52ff9581` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3520`
- A `work` `er-evidence:95ac0148df9f2c3e5df93bfcc7da1c11c3b2e6c4035dc81f4936383a2b290b97` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:336`
- B `enrichment` `er-evidence:04497230f40a3149bb8046bd2163b2cdf4576f6a8d89645cc8ec194138e2777c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2358`
- B `work` `er-evidence:b593359758c550f5d4a88e9164918614ab8c0f34ddaa6ab49dcac7f87d6e3f5c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:215`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 90 — Researcher

- **pairId:** `resolution-pair:cec55279c7837a31f87b5bc3f4fd7ac0fbaa2febf9a2cf4d2668896ebfb78903`
- **evidenceHash:** `586d9ee3dde323310df9cfa832bcc6ab65068b12b7976450171b7f9f18931da5`
- **Question:** do mention A `mention:openalex:W4388041447#4` and B `mention:openalex:W4388080974#7` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4388041447#4 | mention:openalex:W4388080974#7 |
| Name as written | Qiong Chen | Quan Chen |
| Author position | 4 of 5 | 7 of 10 |
| ORCID on mention | 0000-0002-9606-4492 (OpenAlex-supplied) | 0000-0001-5832-0347 (OpenAlex-supplied) |
| OpenAlex author ID | A5059506279 | A5100377840 |
| Affiliation | ROR 00cmhce21 | ROR 0220qvk04 |
| Work title | AsyFunc | Not All Resources are Visible |
| Year | 2023 | 2023 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S7407088165 |
| DOI | 10.1145/3620678.3624664 | 10.1145/3620678.3624650 |
| Coauthors | Qiangyu Pei, Yongjie Yuan, Haichuan Hu, Fangming Liu | Xinkai Wang, Hao He, Yuancheng Li, Chao Li, Xiaofeng Hou, Jing Wang, Jingwen Leng, Minyi Guo, Leibo Wang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['00cmhce21'] B=['0220qvk04'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#4 "Qiong Chen" and B author#7 "Quan Chen" differ in given name (Qiong vs Quan); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Qiong" vs "Quan"
- No shared coauthors
- enrichment ror differs: 00cmhce21 vs 0220qvk04

**Conflicting evidence:**
- Same year 2023 and venueId S7407088165

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:544ba317a0cea318b638e9c9f31b9b2346da272244f5a9f2cd53896b8b5fa727` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:59`
- A `enrichment` `er-evidence:d1311fb9731ff0dc124e904c156e9c7a60e7ed46ebc644b29f6bf5e1b8da047d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:651`
- B `enrichment` `er-evidence:3441706e96946dda4cd8cc74595ca132ac56a136ffd0c074bb3f7c33b84e010c` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:639`
- B `work` `er-evidence:e3b33803800b5dac4d7991d96d8b89b74fcd541270ae737413e08b31075262ed` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:57`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 91 — Researcher

- **pairId:** `resolution-pair:6a42ff16e7ec01cc89dfb7947ec265eefeac83189d36af7420723a875b442486`
- **evidenceHash:** `b2e0107fa6cdd3f9de9e28aa3ff0777c6ebd5f77a68acac4607e122e38f1b4bc`
- **Question:** do mention A `mention:openalex:W2797851444#6` and B `mention:openalex:W4285179693#5` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2797851444#6 | mention:openalex:W4285179693#5 |
| Name as written | Tianhao Wang | Tianwen Wang |
| Author position | 6 of 6 | 5 of 5 |
| ORCID on mention | 0000-0002-9017-7947 (OpenAlex-supplied) | 0000-0001-7440-0056 (OpenAlex-supplied) |
| OpenAlex author ID | A5100610986 | A5019308017 |
| Affiliation | ROR 02dqehb95 | ROR 01tgyzw49 |
| Work title | Privacy at Scale | Hybrid blockchain database systems |
| Year | 2018 | 2022 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S4210226185 |
| DOI | 10.1145/3183713.3197390 | 10.14778/3510397.3510406 |
| Coauthors | Graham Cormode, Somesh Jha, Tejas Kulkarni, Ninghui Li, Divesh Srivastava | Zerui Ge, Dumitrel Loghin, Beng Chin Ooi, Pingcheng Ruan |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['02dqehb95'] B=['01tgyzw49'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#6 "Tianhao Wang" and B author#5 "Tianwen Wang" differ in given name (Tianhao vs Tianwen); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Tianhao" vs "Tianwen"
- No shared coauthors
- enrichment ror differs: 02dqehb95 vs 01tgyzw49

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:7416e579389d7ff05cb18397a250a160bfc46cd6812de3aa651ff0556fbeb9e0` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:4309`
- A `work` `er-evidence:e6ac5f643fffe1f52c03c264e5715da6fe4a19f1c15309e4737918f6f55e355e` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:423`
- B `enrichment` `er-evidence:70ba6d3a4d91e90db4fa7473ac77d125af105051e7f130f1018b0b7df85723d4` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1522`
- B `work` `er-evidence:7e2c53e8b8615e5d4be4225237e3edbab9266563825abf358915e92dc695ee21` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:142`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 92 — Researcher

- **pairId:** `resolution-pair:3cbe1254167cf14ff2f8b96b92a694c195ff265a582ccd2e4f592a7b7ae638e6`
- **evidenceHash:** `ea3e319836d0590df03ef28d8f221cba903d63f9f62c6efd686a7a696db9593e`
- **Question:** do mention A `mention:openalex:W4375928372#3` and B `mention:openalex:W4396571402#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4375928372#3 | mention:openalex:W4396571402#3 |
| Name as written | Yuliang Li | Yaliang Li |
| Author position | 3 of 5 | 3 of 7 |
| ORCID on mention | 0000-0002-0602-149X (OpenAlex-supplied) | 0000-0002-4204-6096 (OpenAlex-supplied) |
| OpenAlex author ID | A5100750716 | A5046576694 |
| Affiliation | — | ROR 00k642b80 |
| Work title | Semantics-Aware Dataset Discovery from Data Lakes with Contextualized Column-Based Representation Learning | Text-to-SQL Empowered by Large Language Models: A Benchmark Evaluation |
| Year | 2023 | 2024 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S4210226185 |
| DOI | 10.14778/3587136.3587146 | 10.14778/3641204.3641221 |
| Coauthors | Grace Fan, Jin Wang, Dan Zhang, Renée J. Miller | Dawei Gao, Haibin Wang, Xiuyu Sun, Yichen Qian, Bolin Ding, Jingren Zhou |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=- B=['00k642b80'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#3 "Yuliang Li" and B author#3 "Yaliang Li" are different given names (one vowel apart but distinct names) with no shared coauthors and different OpenAlex-supplied ORCIDs.

**Supporting evidence:**
- nameText given names differ: "Yuliang" vs "Yaliang"
- No shared coauthors
- Different OpenAlex-supplied ORCIDs 0000-0002-0602-149X vs 0000-0002-4204-6096 (provider hypothesis)

**Conflicting evidence:**
- Same venueId S4210226185; adjacent years 2023/2024

**Limitations / missing information:**
- A has no affiliation evidence
- A one-letter spelling difference could in principle be a source typo

<details><summary>Evidence references</summary>

- A `work` `er-evidence:b5d7bbfa5c0638306c4760406fbb9b1dbd511b4efce97f0aeaeb754c0408a99f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:112`
- B `work` `er-evidence:20d19dacee726c5adb40fba30716e80a72b0ebb1dae41b39343e56accf46fc33` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:53`
- B `enrichment` `er-evidence:5acf65a9cba29b8b04ca2d8edf94a400d2c2ba6b4cfa918a76ef34953c2ab8ef` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:583`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 93 — Researcher

- **pairId:** `resolution-pair:88a5571e5b8ae0f36f5d367f6dbf45f247bddec48c70f063e06a089a6439b311`
- **evidenceHash:** `1ad16c077cef1a60b40808a1c566ed827949a03a969f3485f5bc78738ea12058`
- **Question:** do mention A `mention:openalex:W3086150815#1` and B `mention:openalex:W3174749316#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W3086150815#1 | mention:openalex:W3174749316#1 |
| Name as written | Shaleen Deep | Shaleen Deep |
| Author position | 1 of 6 | 1 of 6 |
| ORCID on mention | 0000-0003-2342-4060 (OpenAlex-supplied) | 0000-0003-2342-4060 (OpenAlex-supplied) |
| OpenAlex author ID | A5036934715 | A5036934715 |
| Affiliation | ROR 01y2jtd41 | ROR 01y2jtd41 |
| Work title | DIAMetrics | DIAMetrics |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S4210226185 | venue:openalex:S47508943 |
| DOI | 10.14778/3415478.3415551 | 10.1145/3471485.3471492 |
| Coauthors | Anja Gruenheid, Kruthi Nagaraj, Hiro Naito, Jeff Naughton, Stratis Viglas | Anja Gruenheid, Kruthi Nagaraj, Hiro Naito, Jeff Naughton, Stratis Viglas |

_helper: shared coauthor normalizedNames = ['anja gruenheid', 'hiro naito', 'jeff naughton', 'kruthi nagaraj', 'stratis viglas']_
_helper: target-mention ROR A=['01y2jtd41'] B=['01y2jtd41'] shared=['01y2jtd41']_

**AI-proposed label: `same`**

**Note:** Both mentions are author#1 "Shaleen Deep" on works titled "DIAMetrics" with identical five coauthors in identical order (Anja Gruenheid, Kruthi Nagaraj, Hiro Naito, Jeff Naughton, Stratis Viglas) and the same ROR 01y2jtd41.

**Supporting evidence:**
- Name exact match at author#1 in both
- All five coauthors shared, same order
- Identical work.title (2020 venue S4210226185; 2021 venue S47508943)
- enrichment ror=01y2jtd41 on both target mentions
- Same OpenAlex-supplied observedOrcid 0000-0003-2342-4060 (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- The two works have distinct DOIs; this affects work identity, not the person
- All evidence OpenAlex-derived

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:69aaa3a046554c4642d5388c16df78a523b64e30be4ee7e2198c99bc621a701f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2775`
- A `work` `er-evidence:bff8e344468e582c2cf76796189cab1c3b74e054f2a828a5304485126087a243` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:255`
- B `work` `er-evidence:99d9d791a675540524e40d0648240feb6130b89545e9ef3be5e7cba724fd26b5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:203`
- B `enrichment` `er-evidence:f664da51f710be8aa36f35a29d3ba7379662b523433949a89c066f0021715645` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2220`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---

## Task 94 — Researcher

- **pairId:** `resolution-pair:91a16bfc05d240567329d8537a26315ea1f9ca6c1bcee097dfee5d8fe02d0e6e`
- **evidenceHash:** `56d7a10da447b9db4058c008fb1252875bca50a9abfc1a25aea8a016a23c777c`
- **Question:** do mention A `mention:openalex:W2950694221#6` and B `mention:openalex:W4396571402#3` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2950694221#6 | mention:openalex:W4396571402#3 |
| Name as written | Yong Li | Yaliang Li |
| Author position | 6 of 8 | 3 of 7 |
| ORCID on mention | 0000-0001-5617-1659 (OpenAlex-supplied) | 0000-0002-4204-6096 (OpenAlex-supplied) |
| OpenAlex author ID | A5100355277 | A5046576694 |
| Affiliation | ROR 02tcm9e24; ROR 03cve4549 | ROR 00k642b80 |
| Work title | Neural Multi-task Recommendation from Multi-behavior Data | Text-to-SQL Empowered by Large Language Models: A Benchmark Evaluation |
| Year | 2019 | 2024 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4210226185 |
| DOI | 10.1109/icde.2019.00140 | 10.14778/3641204.3641221 |
| Coauthors | Chen Gao, Xiangnan He, Dahua Gan, Xiangning Chen, Fuli Feng, Tat-Seng Chua, Depeng Jin | Dawei Gao, Haibin Wang, Xiuyu Sun, Yichen Qian, Bolin Ding, Jingren Zhou |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['02tcm9e24', '03cve4549'] B=['00k642b80'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#6 "Yong Li" and B author#3 "Yaliang Li" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Yong" vs "Yaliang"
- No shared coauthors
- enrichment ror sets disjoint: {02tcm9e24, 03cve4549} vs {00k642b80}

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:533081b7223cbad6177ed3555152e295372cd94aae6d3b073f4676700703ff82` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3573`
- A `enrichment` `er-evidence:82fe6ec284b0ef113127fd8b3890a6875266f242506e00032dde904560bd6648` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3572`
- A `work` `er-evidence:9b8a6c300924062e6adbb00ce07b22af3e5be3df887796b0ad5a1612df44f3f1` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:341`
- B `work` `er-evidence:20d19dacee726c5adb40fba30716e80a72b0ebb1dae41b39343e56accf46fc33` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:53`
- B `enrichment` `er-evidence:5acf65a9cba29b8b04ca2d8edf94a400d2c2ba6b4cfa918a76ef34953c2ab8ef` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:583`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 95 — Researcher

- **pairId:** `resolution-pair:50d1bc13fd8d17a2ee128c757f5a44e798bb4a9f1746771391aad645cd743121`
- **evidenceHash:** `ff1b49b8e6fa5f51aff2190c21c0ff97265e2f95a64b8b01a0881ba659e7a75c`
- **Question:** do mention A `mention:openalex:W2952570284#1` and B `mention:openalex:W4379390584#1` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2952570284#1 | mention:openalex:W4379390584#1 |
| Name as written | Ce Zhang | Chao Zhang |
| Author position | 1 of 5 | 1 of 3 |
| ORCID on mention | 0000-0001-9947-9960 (OpenAlex-supplied) | 0000-0003-4972-9380 (OpenAlex-supplied) |
| OpenAlex author ID | A5100383721 | A5100460293 |
| Affiliation | ROR 0145fw131 | ROR 01aff2v68 |
| Work title | GEM^2-Tree: A Gas-Efficient Structure for Authenticated Range Queries in Blockchain | An Overview of Reachability Indexes on Graphs |
| Year | 2019 | 2023 |
| Venue ID | venue:openalex:S4210210321 | venue:openalex:S4393915683 |
| DOI | 10.1109/icde.2019.00080 | 10.1145/3555041.3589408 |
| Coauthors | Cheng Xu, Jianliang Xu, Yuzhe Tang, Byron Choi | Angela Bonifati, M. Tamer Özsu |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['0145fw131'] B=['01aff2v68'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#1 "Ce Zhang" and B author#1 "Chao Zhang" differ in given name (Ce vs Chao); no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Ce" vs "Chao"
- No shared coauthors
- enrichment ror differs: 0145fw131 vs 01aff2v68

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `work` `er-evidence:34126b2ca887d3b53acbace76cea632036414c45fe050a7bd4b71a56718f5303` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:335`
- A `enrichment` `er-evidence:4762fccb0d81a2f42a03403fac290145267977466752a0726a08150950d7ef43` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3508`
- B `work` `er-evidence:54e9f1ba3478f316e85ba21ad6cb6ddcb9f52689d03816ddf94530150fb65efc` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:105`
- B `enrichment` `er-evidence:e5e9e9755e6fe45cad40b5d19c473a669d3e6e453d9ce61d211ffab55317447f` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:1138`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 96 — Work

- **pairId:** `resolution-pair:f6ecee61e20cd3de650fc38732a82b118c614787b2940a34d2043accec2127d0`
- **evidenceHash:** `a88fcad3b19d473300e325ae7832d843d4114a93bb62fc582ca2740455083bfe`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W3094923044 (conference-paper) | OPENALEX W3181897344 (article) |
| Title | Challenges and solutions for fast remote persistent memory access | Addra: Metadata-private voice communication over fully untrusted infrastructure. |
| Year | 2020 | 2021 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4306420647 |
| DOI | 10.1145/3419111.3421294 | — |
| arXiv ID | — | — |
| Pages | 105-119 | — |
| Authors | (3) Anuj Kalia, David Andersen, Michael Kaminsky | (5) Ishtiyaque Ahmad, Yuntian Yang, Divyakant Agrawal, Amr El Abbadi, Trinabh Gupta |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3419111.3421294, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3419111.3421294, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1145/3419111.3421294'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Challenges and solutions for fast remote persistent memory access" (DOI 10.1145/3419111.3421294, 2020) and B "Addra: Metadata-private voice communication over fully untrusted infrastructure." (no DOI, OSDI 2021) have unrelated titles and disjoint authors.

**Supporting evidence:**
- work.title unrelated
- work.year 2020 vs 2021
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:bf2d2cd631b4c8ac292c084002c81724947607313f2b02d43220783f168c4c62` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:250`
- B `work` `er-evidence:216c341b63b697c447cd8e4c5051a30dc178ac930724d4504496026fbc771783` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:185`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 97 — Work

- **pairId:** `resolution-pair:3da54ed429066d0c73c338f5e8518c632a5673e99b1dd05148c42f49d07c3d0d`
- **evidenceHash:** `096a35e88459ae4d6dad8fb4ba7d27ffa660a6f91b627907f060b3a0dc2d48b9`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2892952080 (conference-paper) | OPENALEX W3097770476 (article) |
| Title | IONN | The CacheLib Caching Engine: Design and Experiences at Scale |
| Year | 2018 | 2020 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4306420647 |
| DOI | 10.1145/3267809.3267828 | — |
| arXiv ID | — | — |
| Pages | 401-411 | 753-768 |
| Authors | (4) Hyuk-Jin Jeong, Hyeon-Jae Lee, Chang Hyun Shin, Soo-Mook Moon | (11) Benjamin Wagner vom Berg, Daniel S. Berger, Sara McAllister, Isaac Grosof, Sathya Gunasekar, Jimmy Lu, Michael Uhlar, Jim Carrig, Nathan Beckmann, Mor Harchol‐Balter, Gregory R. Ganger |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3267809.3267828, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3267809.3267828, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1145/3267809.3267828'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "IONN" (DOI 10.1145/3267809.3267828, 2018, 4 authors) and B "The CacheLib Caching Engine: Design and Experiences at Scale" (no DOI, OSDI 2020, 11 authors) have different titles, years and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2018 vs 2020
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:439a90b8bf8d6eab259421f654b36d699da30634ed2330c1a69bc266e1a3d423` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:392`
- B `work` `er-evidence:9077058943211a3d57147957a5b6b8f33c3099382a96b1b8235ebf3c9e6f8024` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:234`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 98 — Researcher

- **pairId:** `resolution-pair:2e446deba355f3eab2c9dff4b7ad20c1bba29638d22e68296831ed7c2053f126`
- **evidenceHash:** `1b449a6456b3b7b0b3a0331b2f69765c8611cd980034e16af7e03ec4c1ec4508`
- **Question:** do mention A `mention:openalex:W4388041078#5` and B `mention:openalex:W4399208444#5` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W4388041078#5 | mention:openalex:W4399208444#5 |
| Name as written | Yongsu Zhang | Yunjia Zhang |
| Author position | 5 of 12 | 5 of 9 |
| ORCID on mention | 0009-0004-8527-4082 (OpenAlex-supplied) | 0000-0002-8067-3592 (OpenAlex-supplied) |
| OpenAlex author ID | A5015455494 | A5026461715 |
| Affiliation | ROR 04m8av638 | ROR 01y2jtd41 |
| Work title | Dissecting Overheads of Service Mesh Sidecars | GPTuner: A Manual-Reading Database Tuning System via GPT-Guided Bayesian Optimization |
| Year | 2023 | 2024 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4210226185 |
| DOI | 10.1145/3620678.3624652 | 10.14778/3659437.3659449 |
| Coauthors | Xiangfeng Zhu, Guozhen She, Bowen Xue, Yu Zhang, Xuan Kelvin Zou, XiongChun Duan, Peng He, Arvind Krishnamurthy, Matthew Lentz, Danyang Zhuo, Ratul Mahajan | Jiale Lao, Yibo Wang, Yufei Li, Jianping Wang, Zhiyuan Cheng, Wanghu Chen, Mingjie Tang, Jianguo Wang |

_helper: shared coauthor normalizedNames = none_
_helper: target-mention ROR A=['04m8av638'] B=['01y2jtd41'] shared=none_

**AI-proposed label: `different`**

**Note:** A author#5 "Yongsu Zhang" and B author#5 "Yunjia Zhang" have different given names; no coauthor or affiliation overlap.

**Supporting evidence:**
- nameText given names differ: "Yongsu" vs "Yunjia"
- No shared coauthors
- enrichment ror differs: 04m8av638 vs 01y2jtd41

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- none noted

<details><summary>Evidence references</summary>

- A `enrichment` `er-evidence:aad8a8dfc738957ef1f953a347ad921245abe33feb7a6ff5616b43c2ac3e3c13` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:689`
- A `work` `er-evidence:cd980f8b96ded17519f51d7f21087d5a6978d49fca80be03485930a4994ef42a` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:62`
- B `work` `er-evidence:a1496fd5ac846f7d9990387455b6780ffe67d59e7e2a70eb58e527bf3ab463c8` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:37`
- B `enrichment` `er-evidence:abae82ce23e698ae1b5ccb5deb4df79bdb9458a092d38e4ce8036421f33e7467` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:416`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 99 — Work

- **pairId:** `resolution-pair:e1530b4d35fff5238207e357d5bcda973132827c7b18128401ab1797d829d653`
- **evidenceHash:** `0ca5540bd68e0ab2345d6ca556758d96b1f74005ec01bc320bd99d9a64ae0435`
- **Question:** do observations A and B refer to the same publication?

| Field | A | B |
|---|---|---|
| Record | OPENALEX W2987607480 (conference-paper) | OPENALEX W3176081047 (article) |
| Title | Cirrus | The nanoPU: A Nanosecond Network Stack for Datacenters |
| Year | 2019 | 2021 |
| Venue ID | venue:openalex:S7407088165 | venue:openalex:S4306420647 |
| DOI | 10.1145/3357223.3362711 | — |
| arXiv ID | — | — |
| Pages | 13-24 | 239-256 |
| Authors | (5) Joao Carreira, Pedro Fonseca, Alexey Tumanov, Andrew Zhang, Randy Katz | (7) Stephen Ibanez, Alex Mallery, Serhat Arslan, Theo Jepsen, Muhammad Shahbaz, Changhoon Kim, Nick McKeown |
| Observed identifiers | namespace=openalex.doi, value=https://doi.org/10.1145/3357223.3362711, interpretation=SOURCE_OBSERVATION; namespace=openalex.ids.doi, value=https://doi.org/10.1145/3357223.3362711, interpretation=SOURCE_OBSERVATION | — |

_helper: normalized DOI A=['10.1145/3357223.3362711'] B=- -> not comparable_

**AI-proposed label: `different`**

**Note:** A "Cirrus" (DOI 10.1145/3357223.3362711, 2019) and B "The nanoPU: A Nanosecond Network Stack for Datacenters" (no DOI, OSDI 2021) have different titles, years and disjoint authors.

**Supporting evidence:**
- work.title different
- work.year 2019 vs 2021
- work.authors disjoint

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B has no DOI, so identifiers cannot be compared

<details><summary>Evidence references</summary>

- A `work` `er-evidence:19cceb480abd8eeedd60d899740a2f5f6d662b24ab3c43441642f89480dd47ec` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:310`
- B `work` `er-evidence:4511884fb6014a4cd0d412ce95cfd0fc559b4178356b3ac1240a451f9c47c1d3` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:196`

</details>

**Danny's decision:** ☐ same ☑ different ☐ uncertain

**Comments:**

> 

---

## Task 100 — Researcher

- **pairId:** `resolution-pair:607b9a7d9ed7ff1642dd362affb8afdfcdeb00a518196c8d2dc45d41fa4d59d3`
- **evidenceHash:** `0fc2ed534d02201be347468e2d7c72efabedb66ab87789416c41bc01dfacd5f6`
- **Question:** do mention A `mention:openalex:W2948709946#9` and B `mention:openalex:W3145232008#6` refer to the same person?

| Field | A | B |
|---|---|---|
| Mention / record | mention:openalex:W2948709946#9 | mention:openalex:W3145232008#6 |
| Name as written | Jeff R. Ballard | Jeffrey R. Ballard |
| Author position | 9 of 20 | 6 of 15 |
| ORCID on mention | — | — |
| OpenAlex author ID | A5026326684 | A5026326684 |
| Affiliation | ROR 01y2jtd41 | ROR 01y2jtd41 |
| Work title | Entity Matching Meets Data Science | Technical Perspective: |
| Year | 2019 | 2018 |
| Venue ID | venue:openalex:S4393915683 | venue:openalex:S47508943 |
| DOI | 10.1145/3299869.3314042 | 10.1145/3277006.3277015 |
| Coauthors | Yash Govind, Pradap Konda, Paul Suganthan G.C., Philip Martinkus, Palaniappan Nagarajan, Han Li, Aravind Soundararajan, Sidharth Mudgal, Haojun Zhang, Adel Ardalan, Sanjib Das, Derek Paulsen, Amanpreet Singh Saini, Erik Paulson, Youngchoon Park, Marshall Carter, Mingju Sun, Glenn M. Fung, AnHai Doan | Pradap Konda, Sanjib Das, Paul Suganthan G.C., Philip Martinkus, Adel Ardalan, Yash Govind, Han Li, Fatemah Panahi, Haojun Zhang, Jeff Naughton, Shishir Prasad, Ganesh Krishnan, Rohit Deep, Vijay Raghavendra |

_helper: shared coauthor normalizedNames = ['adel ardalan', 'han li', 'haojun zhang', 'paul suganthan g.c.', 'philip martinkus', 'pradap konda', 'sanjib das', 'yash govind']_
_helper: target-mention ROR A=['01y2jtd41'] B=['01y2jtd41'] shared=['01y2jtd41']_

**AI-proposed label: `same`**

**Note:** A "Jeff R. Ballard" and B "Jeffrey R. Ballard" are compatible name forms (same middle initial R) on entity-matching-group papers sharing eight coauthors (e.g., Pradap Konda, Sanjib Das, Paul Suganthan G.C., Yash Govind, Han Li) with the same ROR 01y2jtd41.

**Supporting evidence:**
- Name variant Jeff/Jeffrey with same middle initial and surname
- Eight shared coauthors in the payloads
- enrichment ror=01y2jtd41 on both target mentions
- Same OpenAlex author id A5026326684 on both (provider hypothesis only)

**Conflicting evidence:**
- none noted

**Limitations / missing information:**
- B title is truncated ("Technical Perspective:"), limiting topic comparison
- No ORCID on either mention

<details><summary>Evidence references</summary>

- A `work` `er-evidence:c0b57e8bf04dfcab0dcef8bb915a02ecddd4115a60eb7b816d1555fd3857de37` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:346`
- A `enrichment` `er-evidence:f862e4a4f284c56d951b5fc5bcfd5f1e7e1db94a015d696fd6acc1f691d5f7b5` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:3621`
- B `work` `er-evidence:b13c23e42fcaedcadc0070447130bdb28189aac6c7b466d69ea79e91cff520be` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/work/part-r-00000:218`
- B `enrichment` `er-evidence:cf82f4191f22878e9678d7911c768796313d1bdefb93a815805a879082e6b19d` — `snapshot=openalex-er5c-live-api-2026-10-16/run=bd424a86-0a1b-4e44-bbdb-4a9b8c8a20e3/enrichment/part-r-00000:2391`

</details>

**Danny's decision:** ☑ same ☐ different ☐ uncertain

**Comments:**

> 

---
