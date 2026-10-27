# Service runtime packaging

`sbt packageServices` writes `modules/services/target/distribution/` with
`services.jar` and `lib/*.jar`. It packages core, rag, storage, and the services
runtime dependency classpath. Spark is not a service dependency. Storage's
Parquet/Hadoop dependencies remain because the storage module still declares
them; splitting the storage adapters is outside this phase.

The distribution also copies the versioned `prompts/runtime/**` and
`prompts/schemas/**` trees to `distribution/prompts/`, retaining exact file bytes
and relative paths. Each build replaces that generated asset tree so removed
assets cannot survive in an image. Both source directories must contain files;
symbolic links are rejected. Docker places these assets at `/app/prompts` for
the explicit offline synthetic runtime and configured runtime composition.

The distribution task validates the four service entry points, rejects duplicate
dependency filenames, and replaces stale generated libraries. Keeping dependency
JARs intact preserves their resources and service-provider descriptors. There is
no shaded dependency merge.

`sbt dockerLocal` first packages the distribution and then builds four local
images, with the `MAIN_CLASS` Docker build argument selecting the entry point:

| Local image | Main class suffix |
| --- | --- |
| `scholarchain-query-api:local` | `QueryApiMain` |
| `scholarchain-graph-service:local` | `GraphServiceMain` |
| `scholarchain-semantic-service:local` | `SemanticServiceMain` |
| `scholarchain-embedding-worker:local` | `EmbeddingWorkerMain` |

All main classes are in `edu.uic.cs441.scholarchain.services`. Docker validates
the build argument against these four classes. Each image starts Java as the
non-root `scholarchain` user and forwards startup arguments. The Dockerfile-specific
ignore file admits only the generated distribution into the build context. The
task does not push images or deploy anything. Images tagged by Git SHA belong to
the later deployment scripts phase.

For a single image, after `sbt packageServices`:

```bash
docker build -f Dockerfile \
  --build-arg MAIN_CLASS=edu.uic.cs441.scholarchain.services.QueryApiMain \
  -t scholarchain-query-api:local .
```

Cask is pinned at 0.10.2 because its published Maven POM depends on the project's
Scala 3.3.4 and uPickle 4.0.2 versions. Compilation and HTTP behavior tests remain
the compatibility gates. The POM is at
https://repo.maven.apache.org/maven2/com/lihaoyi/cask_3/0.10.2/cask_3-0.10.2.pom.
