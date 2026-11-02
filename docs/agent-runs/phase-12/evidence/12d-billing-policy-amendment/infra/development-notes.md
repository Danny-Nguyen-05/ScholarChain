# Development attempts

- One development formatting command (`terraform fmt -recursive`) wrote formatting inside the assigned root before source freeze. It exited 0 and is separately labeled development-format. Every final formatting gate uses `fmt -check -recursive`.
- Every final native gate exited 0. The two RED init/test pairs are expected negative evidence, not gate failures.
- An initial metadata-only Python helper searched for a literal `name = {` assignment and failed on the existing conditional trust/caller assignments. Its tool-result traceback is transcribed in metadata-development-error.log.txt. The corrected collect_metadata.py locates the assignment before counting braces and validates all three unchanged block hashes. No source edit resulted from this helper failure, and no pass was claimed for it.
- Full JDK 17 gate and final source freeze belong to the coordinator/build-engineer; this native packet does not claim that gate has completed. No source writes occurred after SOURCE FINAL.
