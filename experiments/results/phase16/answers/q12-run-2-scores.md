# Q12 benchmark scores

Run `q12-run-2`, key `6f5ef014d310136d` (export run `run:ba7402d1-959a-4277-8c6e-e92878a38afa`), deep checks: export.

## Headline: the 27 answer-expected questions

retrieval 23, claims 23, text 23, all three 23 of 27. Unverified evidence items (not fetched or too large, neither failed nor passed): 0 across 0 questions.

## Abstain-expected questions (thin data): 6

correct abstentions 6 of 6 (a 200 ABSTAINED answer or a 422 UNSUPPORTED_QUERY refusal; anything else is an error).

## Per question

| id | type | level | outcome | retrieval | unverified | claims (a/v/r) | text | all | first failure |
|---|---|---|---|---|---|---|---|---|---|
| q01 | coauthor_breadth | values-and-order | answered | pass | 0 | 2/2/0 pass | pass | pass |  |
| q02 | topic | abstain | refused | pass | 0 | None/None/None pass | pass | pass | not applicable: the key expects an abstention |
| q03 | max_team_size | values-and-order | answered | pass | 0 | 2/2/0 pass | pass | pass |  |
| q04 | direct_collab | exact | answered | pass | 0 | 1/1/0 pass | pass | pass |  |
| q05 | institution | abstain | refused | pass | 0 | None/None/None pass | pass | pass | not applicable: the key expects an abstention |
| q06 | shortest_path | exact | answered | pass | 0 | 2/2/0 pass | pass | pass |  |
| q07 | component | exact | answered | pass | 0 | 2/2/0 pass | pass | pass |  |
| q08 | community | exact | abstained | FAIL | 0 | 0/0/0 FAIL | FAIL | FAIL | the system did not answer (outcome kind abstained) |
| q09 | bridge | values-and-order | answered | pass | 0 | 2/2/0 pass | pass | pass |  |
| q10 | temporal | exact | answered | pass | 0 | 1/1/0 pass | pass | pass |  |
| q11 | evidence | exact | answered | pass | 0 | 2/2/0 pass | pass | pass |  |
| q12 | coauthor_breadth | values-and-order | answered | pass | 0 | 2/2/0 pass | pass | pass |  |
| q13 | topic | abstain | refused | pass | 0 | None/None/None pass | pass | pass | not applicable: the key expects an abstention |
| q14 | max_team_size | bounded | error | FAIL | 0 | None/None/None FAIL | FAIL | FAIL | the system did not answer (outcome kind error) |
| q15 | direct_collab | exact | answered | pass | 0 | 12/12/0 pass | pass | pass |  |
| q16 | institution | abstain | refused | pass | 0 | None/None/None pass | pass | pass | not applicable: the key expects an abstention |
| q17 | shortest_path | exact | answered | pass | 0 | 3/3/0 pass | pass | pass |  |
| q18 | component | exact | answered | pass | 0 | 1/1/0 pass | pass | pass |  |
| q19 | community | exact | refused | FAIL | 0 | None/None/None FAIL | FAIL | FAIL | the system did not answer (outcome kind refused) |
| q20 | bridge | values-and-order | answered | pass | 0 | 2/2/0 pass | pass | pass |  |
| q21 | temporal | exact | answered | pass | 0 | 1/1/0 pass | pass | pass |  |
| q22 | evidence | exact | answered | pass | 0 | 2/2/0 pass | pass | pass |  |
| q23 | coauthor_breadth | values-and-order | answered | pass | 0 | 2/2/0 pass | pass | pass |  |
| q24 | topic | abstain | refused | pass | 0 | None/None/None pass | pass | pass | not applicable: the key expects an abstention |
| q25 | max_team_size | bounded | answered | pass | 0 | 2/2/0 pass | pass | pass |  |
| q26 | direct_collab | exact | answered | pass | 0 | 14/14/0 pass | pass | pass |  |
| q27 | institution | abstain | refused | pass | 0 | None/None/None pass | pass | pass | not applicable: the key expects an abstention |
| q28 | shortest_path | exact | answered | pass | 0 | 4/4/0 pass | pass | pass |  |
| q29 | component | exact | answered | pass | 0 | 1/1/0 pass | pass | pass |  |
| q30 | community | exact | refused | FAIL | 0 | None/None/None FAIL | FAIL | FAIL | the system did not answer (outcome kind refused) |
| q31 | bridge | values-and-order | answered | pass | 0 | 2/2/0 pass | pass | pass |  |
| q32 | temporal | exact | answered | pass | 0 | 1/1/0 pass | pass | pass |  |
| q33 | evidence | exact | answered | pass | 0 | 2/2/0 pass | pass | pass |  |

## Per type

| type | questions | retrieval | claims | text | all pass | abstained/refused |
|---|---|---|---|---|---|---|
| bridge | 3 | 3 | 3 | 3 | 3 | 0 |
| coauthor_breadth | 3 | 3 | 3 | 3 | 3 | 0 |
| community | 3 | 0 | 0 | 0 | 0 | 3 |
| component | 3 | 3 | 3 | 3 | 3 | 0 |
| direct_collab | 3 | 3 | 3 | 3 | 3 | 0 |
| evidence | 3 | 3 | 3 | 3 | 3 | 0 |
| institution | 3 | 3 | 3 | 3 | 3 | 3 |
| max_team_size | 3 | 2 | 2 | 2 | 2 | 0 |
| shortest_path | 3 | 3 | 3 | 3 | 3 | 0 |
| temporal | 3 | 3 | 3 | 3 | 3 | 0 |
| topic | 3 | 3 | 3 | 3 | 3 | 3 |
| **total answer-expected** | 27 | 23 | 23 | 23 | 23 | 3 |
| **total abstain-expected** | 6 | 6 | 6 | 6 | 6 | 6 |
