# Repair documentation checks

Read-only official pages checked 2026-10-23; no account or provider API call.

- https://docs.aws.amazon.com/neptune/latest/userguide/loader-message.html
  The status table distinguishes pending states, completion, write conflicts, deadlock and other failures. The repair uses the explicit pending allowlist required by the review; all unrecognized states fail closed. A final write-conflict status can be retried.
- https://docs.aws.amazon.com/java/api/latest/software/amazon/awssdk/core/document/Document.html
  Structural accessors distinguish maps, lists, strings, numbers, booleans and null. Web reference version is not proof of the pinned runtime; owner inspects cached SDK2.56.0 APIs.
- https://docs.aws.amazon.com/java/api/latest/software/amazon/awssdk/core/SdkNumber.html
  bigDecimalValue preserves precision; floating-point accessors may lose precision. The structural representation must preserve numeric values rather than silently coercing JSON numbers to strings or rounding them.

No change to Phase6 output, IDs, hashes, producer or dependency pins is required.
