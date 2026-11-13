# Pinned Eclipse Temurin 17 JRE (multi-arch index digest from Docker Hub, 2026-10-04).
FROM eclipse-temurin@sha256:8993f1aed8b25fcea7a7047a7949c1866fa558fc6830d938c22c4f13b26be9d7

ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75.0"

RUN groupadd --system scholarchain && useradd --system --gid scholarchain --home-dir /app scholarchain
WORKDIR /app

# Build locally with `sbt packageServices`; the distribution retains signed/service
# metadata inside dependency JARs rather than merging unrelated resources.
COPY modules/services/target/distribution/services.jar /app/services.jar
COPY modules/services/target/distribution/lib/ /app/lib/
COPY modules/services/target/distribution/prompts/ /app/prompts/

ARG MAIN_CLASS=edu.uic.cs441.scholarchain.services.QueryApiMain
RUN case "$MAIN_CLASS" in \
    edu.uic.cs441.scholarchain.services.QueryApiMain|\
    edu.uic.cs441.scholarchain.services.GraphServiceMain|\
    edu.uic.cs441.scholarchain.services.SemanticServiceMain|\
    edu.uic.cs441.scholarchain.services.EmbeddingWorkerMain) ;; \
    *) echo "Unsupported service main class" >&2; exit 1 ;; \
    esac
ENV SCHOLARCHAIN_MAIN_CLASS=${MAIN_CLASS}

# Image contents must not depend on the builder's umask or the build-context file modes (Docker COPY
# preserves them; a 077 umask once produced 0600 JARs the non-root user could not read). Everything
# under /app stays root-owned and not writable by the application user.
RUN chmod -R go-w,a+rX /app

USER scholarchain

ENTRYPOINT ["sh", "-c", "exec java -cp '/app/services.jar:/app/lib/*' \"$SCHOLARCHAIN_MAIN_CLASS\" \"$@\"", "scholarchain"]
