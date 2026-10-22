# Successful-run stage DAG

The complete DAG, stage names, parent IDs, partitions and per-stage task/shuffle totals are in [stage-dag.json](stage-dag.json). The graph has **5,667 stage IDs** and **4,532 parent edges**, including **3,663 referenced stages without task events**. All **2,004 executed stage-attempt totals** exactly match the retained original summary. Every name/partition count is present, no parent is missing, and the graph is acyclic.

The production summarizer omitted names and parent IDs; this evidence-only artifact supplements that gap from the retained successful raw log. No code or Spark run changed.

This diagram is a bounded actual ancestor subgraph of stage 5163 (11 nodes, 12 edges), not the entire graph. Full names and metrics remain in the JSON.

```mermaid
flowchart LR
  s5153["Stage 5153: 3 partitions"]
  s5154["Stage 5154: 3 partitions"]
  s5155["Stage 5155: 3 partitions"]
  s5156["Stage 5156: 3 partitions"]
  s5157["Stage 5157: 1 partitions"]
  s5158["Stage 5158: 1 partitions"]
  s5159["Stage 5159: 2 partitions"]
  s5160["Stage 5160: 1 partitions"]
  s5161["Stage 5161: 2 partitions"]
  s5162["Stage 5162: 2 partitions"]
  s5163["Stage 5163: 3 partitions"]
  s5156 --> s5157
  s5155 --> s5158
  s5153 --> s5159
  s5154 --> s5160
  s5153 --> s5161
  s5153 --> s5162
  s5157 --> s5163
  s5158 --> s5163
  s5159 --> s5163
  s5160 --> s5163
  s5161 --> s5163
  s5162 --> s5163
```
