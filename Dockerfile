# Pinned Eclipse Temurin 17 JRE (multi-arch index digest from Docker Hub, 2026-10-04).
FROM eclipse-temurin@sha256:8993f1aed8b25fcea7a7047a7949c1866fa558fc6830d938c22c4f13b26be9d7

ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75.0"

RUN groupadd --system scholarchain && useradd --system --gid scholarchain --home-dir /app scholarchain
WORKDIR /app

COPY modules/services/target/scala-3.3.4/services_*.jar /app/services.jar

USER scholarchain

ENTRYPOINT ["java", "-jar", "/app/services.jar"]
