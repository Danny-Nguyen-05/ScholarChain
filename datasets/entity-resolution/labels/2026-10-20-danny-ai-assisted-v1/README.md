# Danny's AI-assisted human review conversion

The user confirmed completing all 12 Markdown batches and authorized conversion and import. `source/` preserves the original 16 source files byte for byte. `checkpoint.json` records the 240 human checkbox selections under reviewer ID `danny`; it is a conversion artifact, not an original HTML export. `provenance.v1.json` and `conversion-report.json` must accompany the checkpoint and any validated derivative.

The reviewer saw AI suggestions and explanations. These labels are **human-reviewed, AI-assisted**, not independent blind gold. Twenty-two Comments explicitly attribute supplementary external source checks to Claude, not Danny. Those comments are preserved verbatim with their original attribution, but neither their external claims nor retrieval were independently verified during conversion. They exceeded the original frozen-source-only draft boundary; the referenced evidence is not silently added to the frozen queue. The AI draft rationales remain separate and are not copied as Danny's reasoning. Reviewer identity is self-entered provenance, not authentication.

All annotation and export timestamps are the conversion instant `2026-10-20T21:58:48Z`, not reconstructed click times. Original filesystem mtimes are retained as observations only. Every annotation is revision 1 with no predecessor; no prior official annotation history was supplied. Conversion does not overwrite the sources or authorize a later revision to the human choices.

| Partition / entity | Same | Different | Uncertain | Reviewed | Binary labels |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development / Work | 1 | 17 | 2 | 20 | 18 |
| Development / Researcher | 10 | 10 | 0 | 20 | 20 |
| Held out / Work | 26 | 73 | 1 | 100 | 99 |
| Held out / Researcher | 46 | 49 | 5 | 100 | 95 |
| Total | 83 | 149 | 8 | 240 | 232 |

The 40 development and 200 held-out **review counts** are complete. Binary-gold counts are 38 development and 194 held-out. If 40/200 definitive labels are required, at least eight additional definitive reviews/adjudications are needed: two development Work, one held-out Work and five held-out Researcher. Additional uncertain answers could increase that number. Existing uncertain selections are preserved, never converted to negatives. No reserves were selected automatically: all 60 remain untouched. The importer's generic `missing: 60` therefore means unreviewed reserves, not missing initial tasks.

Seventeen final human choices differ from the AI proposals. All seventeen are Researcher tasks where the AI draft was `uncertain` and Danny decided after reading a Claude-attributed external source check; all seventeen became definitive labels (13 held out, 4 development; exact rows in `decision-attribution.v1.json`). There is no accuracy, agreement-quality, calibration or prediction claim.

## Decision attribution for the 22 Claude source-check tasks

On 2026-10-20 the user stated, verbatim: "it was actually from me but claude mistaken but under it decision, now I want you to change all of them under my decisions", then "I want you to change it, that's fine". `decision-attribution.v1.json` records this: Danny set every final checkbox, including all 22 tasks whose Comments begin "Source check by Claude ... not Danny". The comment wording, including "Switched same -> uncertain" on tasks 40, 114, 121, 128 and 132, does not mean Claude made or changed a decision; Claude performed only the external source checks. The attribution is self-attested, not authenticated. The cited external evidence was not retained or independently verified, so later evaluation should report results with and without these 22 pairs. No label value, `checkpoint.json`, `validated-labels.json`, provenance, conversion report or `source/` byte changed. No evaluation or live model request was executed by this conversion. Do not tune policy using held-out labels.

The coordinator runs the existing Scala `import-labels` CLI to create `validated-labels.json` separately. Successful schema import cannot authenticate human participation or erase AI/external-assistance limitations. No 5E authorization is implied.

To reproduce the checkpoint without altering this retained directory, use a fresh output path and the same conversion timestamp:

```sh
python3 datasets/scripts/convert_review_batches.py \
  --source datasets/entity-resolution/labels/2026-10-20-danny-ai-assisted-v1/source \
  --queue docs/agent-runs/phase-05/evidence/5c-repair/review-artifacts/queue.json \
  --output /private/tmp/scholarchain-label-replay-NEW \
  --reviewer danny \
  --converted-at 2026-10-20T21:58:48Z
```

The checkpoint and conversion-report bytes replay identically. Provenance original paths and observed filesystem mtimes legitimately reflect the selected source location; the retained originals preserve the initial conversion's observed provenance.

## Observed import receipt

The coordinator subsequently ran the existing Scala `import-labels` CLI successfully (exit 0). `validated-labels.json` contains the exact 240 converted selections: 83 Same, 149 Different and 8 Uncertain, with `missing: 60` referring solely to untouched reserves. Its SHA-256 is `5fbf6f5bdc1d34f7b79e910a07b964b60bdaaf1dfc825de7744b5f684e39e4a6`. The retained execution receipt and independent binding check are `docs/agent-runs/phase-05/evidence/5d-label-import/import-labels.txt` and `import-proof.json`. The conversion report's earlier pending-import status is historical; its bytes and all original sources remain unchanged.
