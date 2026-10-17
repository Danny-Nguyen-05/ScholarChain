# Approved 5C pre-commit cleanup

The user supplied external APPROVE for B1/B2, explicitly requested this bounded cleanup, assigned `.gitattributes` to build-engineer, requested a real-queue load-only browser check and one final `sbt check`, and forbade starting 5D. See external-approval.json for the exact supplied verdict; no longer review report was provided.

Four giant patches were replaced by sibling `.diff.manifest.json` files. Each manifest contains the original patch hash/byte count, changed path list, target file hashes/byte counts, Git base, capture HEAD and exact regeneration command. Small compressed historical source versions in historical-source-blobs/ retain earlier code bytes necessary for faithful reconstruction; large data is referenced from Git/the hash-verified working tree. No full patch remains at the four replaced paths.

Before deletion all four reconstructed patches matched byte-for-byte; the standalone regeneration helper was then run successfully on all four manifests. regeneration-proof.json records those results. Commands regenerate into an explicit new path outside the repository and refuse overwrite:

```text
python3 docs/agent-runs/phase-05/evidence/5c-precommit/regenerate-diff.py.txt --manifest docs/agent-runs/phase-05/5c-implementation.diff.manifest.json --target-ref HEAD --output /private/tmp/reconstructed-phase5c.diff
```

After committing, `--target-ref` identifies the cleanup commit (or use its SHA). Before committing, the helper falls back to verified current files. All source bytes must match their recorded hashes; it will not silently reconstruct using changed inputs. The resulting file must match the original patch SHA-256 and byte count.

Historical hash references to implementation.diff and 5c-implementation.diff in earlier reports/prompts/inventories describe the original reviewed patches. Their sibling manifests now preserve those hashes and reconstruction recipes. Original historical reports were not rewritten to claim a new review. The current inventory describes current files and deletions.

The collector here deliberately updates only freeze/test evidence/inventory; unlike historical collectors, its inventory mode never regenerates huge patches. Historical collectors are evidence, not commands to rerun as the current packaging procedure.

Required exact prepared input, v3 source population, repaired queue/split/generation audit remain. optional-size-proposal.json is a proposal only: v1/v2 and the pre-repair queue/split are unchanged. Any future archival needs separate approval and careful preservation of v3 parent/provenance references. No application logic, original source records, labels or matching policy changed.
