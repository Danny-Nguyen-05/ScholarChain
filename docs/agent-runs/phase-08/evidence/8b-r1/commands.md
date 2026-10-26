# Repair-round command record

Every sbt command uses:
```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

Preflight git status/rev-parse exits0: phase-8, HEAD3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e;19 tracked changes/81 untracked files retained before this repair. Source plan copied to phase8-plan.md and compared byte-for-byte, exit0. Read AGENTS.md and phase evidence contract. Full external review retained verbatim; no duplicate of prior reviews.

No build or test result is claimed for this repair at this checkpoint. Root owns the shared sbt slot; specialist agents author only their assigned paths.

First affected command:
```sh
sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'rag/testOnly *EmbeddingRetrievalSpec *LiveEmbeddingGuardSpec' 'independentTests/Test/scalafmt' 'independentTests/testOnly *IndependentEmbedding8BPipelineSpec *IndependentEmbedding8BGuardSpec *IndependentStorageRuntimeFenceSpec'
```
Raw /tmp/phase8b-r1-targeted-1.txt, exit0. Existing RAG retrieval/guard7passed; independent pipeline1+guard2+fence8=11passed,0failed. New discovered pipeline generates genuine temporary G1 and all literal local acceptance/source/render-only/pure-report checks pass. Runtime fence7 roots/22 inspected/no findings. No approved live route or provider call. The first command intentionally precedes final smoke tests; all final affected suites run next.

Second affected command:
```sh
sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'rag/test' 'independentTests/Test/scalafmt' 'independentTests/testOnly *IndependentEmbedding*Spec *IndependentStorageRuntimeFenceSpec'
```
Raw /tmp/phase8b-r1-targeted-2.txt, exit1. RAG32passed/1failed: new topic/institution fixture expected lowercase openalex instead of the established OPENALEX wire value. Routed to RAG owner; corrected the expected test literal only. All five new query-smoke pure/refusal cases passed. Independent stage did not execute because RAG failed. Same command reruns as targeted-3 after correction.

Final affected rerun uses the same exact command as targeted-2; raw /tmp/phase8b-r1-targeted-3.txt, exit0. RAG33passed0failed; independent41passed0failed across9suites, including discovered temporary G1 pipeline, new smoke refusal and unchanged runtime fence (7 roots/22 inspected/no findings). All checks remain offline; no approved live execution route even with fakes. Source inventory frozen before the full gate; all module/build/test files are read-only through that gate.

Full gate started after freezing all module/build/test bytes:
```sh
/usr/bin/time -p sbt -batch check > /tmp/phase8b-r1-final-check-1.txt 2>&1
```
Raw log remains outsideGit. The repair delta is8files in repair-files.json compared to the prior254-file scope; the new full frozen snapshot covers346 files across all modules/tests/project, adding unchanged prior module files to the audit rather than treating them as repair changes. Final observed result:exit0,766passed/0failed,695.67seconds real; module counts157/64/39/38/51/33/376/8. Raw log 1520049bytes, SHA256 3b5abff12a025530e445a79ccddfe438a0f1df29f25c240078ebe4b81b46876f. The new temporary-G1 case is present and passed in check, along with the expected injected failure-path self-test. All346 frozen files and8repair/35cumulative hashes match;251prior-scope files unchanged. Source whitespace and plan comparison exit0.
