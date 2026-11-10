#!/usr/bin/env bash
# Phase 13 release packaging: jars, linux/amd64 images, architecture gate, release manifest.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/package.sh [--require-images] [--require-runtime-archive] [--help]

Purpose
  Build the release artifacts from the current commit and record them in
  target/release/<commit>/release-manifest.json (git-ignored target/):
    - runs "sbt -batch packageRelease" under JDK 17 (the script applies the JDK 17 environment)
    - collects the Hadoop submit JAR, Hadoop dependency bundle, Spark job JAR, entity-resolution
      job JAR (er-job-jar) and the service distribution (what the Dockerfile COPYs), each with size
      and sha256
    - builds one image per service (query-api, graph-service, semantic-service, embedding-worker):
        docker buildx build --platform <IMAGE_PLATFORM> --provenance=false --sbom=false
          --build-arg MAIN_CLASS=<main> -t scholarchain-<service>:<tag> --load .
      tag = the full 40-hex commit SHA, plus "-dirty" when the work tree is dirty (deploy.sh
      refuses dirty releases). --provenance=false --sbom=false keep buildx from adding an
      attestation manifest, so the loaded image is single-platform and its architecture can be
      inspected unambiguously.
    - ARCHITECTURE GATE: (a) docker image inspect Os/Architecture must equal IMAGE_PLATFORM, and
      (b) IMAGE_PLATFORM must equal the ECS task cpu_architecture parsed from
      infra/terraform/modules/runtime/compute.tf (X86_64 -> linux/amd64, ARM64 -> linux/arm64;
      unparseable fails). Check (b) always runs, even when Docker is unreachable.
    - G5 runtime archive: if SCHOLARCHAIN_RUNTIME_ARCHIVE (local path) is set, or the default
      ignored path in config exists, its size and sha256 are verified against the config pins;
      a mismatch is fatal; absence is recorded.
  The four EMR job JARs (Hadoop submit JAR and dependency bundle, entity-resolution and Spark job JARs) are
  built byte-reproducibly (the build's target/emr-artifacts/emr-artifact-manifest.json records
  byteReproducible=true for each); the sha256 recorded here is still the hash of this build.
  Registry digests do not exist yet: deploy.sh records them at push time. Nothing is uploaded.

Options
  --require-images           fatal (exit 3) when Docker is unreachable, instead of the fallback
  --require-runtime-archive  fatal (exit 3) when no runtime archive is found
  -h, --help                 this text

Docker-unreachable fallback
  The jars are still built; a static Dockerfile check runs (FROM pinned by digest, COPY sources
  exist after packaging, MAIN_CLASS allowlist equals the configured service mains); the images are
  recorded as "skipped" with a warning and the manifest status is "partial-no-images".

Inputs (environment variable NAMES; none are secrets)
  JAVA_HOME                       optional JDK 17 override
  SBT_BIN                         sbt executable (default: sbt)
  SCHOLARCHAIN_RUNTIME_ARCHIVE    optional local path of the G5 runtime archive
  SCHOLARCHAIN_REPO_ROOT          repository root override (tests)
  Settings (platform, services, expected archive hash/size, timeouts, artifact globs) live in
  scripts/config/release.conf. Pins (platform, services, expected archive hash and size) ignore
  same-named environment variables (announced as CONFIG-IGNORED); other settings may be overridden
  by one (announced as CONFIG-OVERRIDE).

Mode
  Real run (no cloud call, no registry login, no push). Human approval: none required.

Exit codes
  0    packaged (RESULT: PASS)
  2    usage error
  3    precondition: JDK 17, missing tool, Docker unreachable with --require-images, no runtime
       archive with --require-runtime-archive
  4    gate failure: architecture gate, static Dockerfile check, runtime archive mismatch,
       missing or ambiguous artifact
  5    sbt or docker build failed
  124  a command timed out

Evidence produced
  <RELEASE_DIR>/<commit>/release-manifest.json: commit, dirty flag, UTC time, toolchain versions,
  artifact paths/sizes/sha256, image tags, local image IDs, architecture gate result, runtime
  archive verification. Build logs under <RELEASE_DIR>/<commit>/logs/.
EOF
}

REQUIRE_IMAGES=0
REQUIRE_ARCHIVE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --require-images)
      REQUIRE_IMAGES=1
      shift
      ;;
    --require-runtime-archive)
      REQUIRE_ARCHIVE=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      sc_usage_exit "package.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "package.sh"
DRY_RUN=0
sc_banner "real-run"

sc_step "preflight"
sc_require_tool python3
sc_require_tool git
COMMIT="$(sc_git_head)" || sc_refuse "${EX_REFUSED}" "not a git work tree with a commit"
if [[ ! "${COMMIT}" =~ ^[0-9a-f]{40}$ ]]; then
  sc_refuse "${EX_REFUSED}" "git HEAD is not a 40-hex SHA"
fi
DIRTY=false
IMAGE_TAG="${COMMIT}"
if sc_git_dirty; then
  DIRTY=true
  IMAGE_TAG="${COMMIT}-dirty"
  sc_warn "work tree is dirty: images are tagged ${IMAGE_TAG}; deploy.sh will refuse this release"
fi
OUT_DIR="${REPO_ROOT}/${RELEASE_DIR}/${COMMIT}"
LOG_DIR="${OUT_DIR}/logs"
MANIFEST="${OUT_DIR}/release-manifest.json"
mkdir -p "${LOG_DIR}"
rm -f "${MANIFEST}"
sc_mktemp FACTS
sc_mktemp INSPECT_JSON
WARNINGS=""
sc_info "commit=${COMMIT} dirty=${DIRTY} image_tag=${IMAGE_TAG}"

# ---- G5 runtime archive (cheap, fail fast before the long build) ------------------------------
sc_step "runtime-archive"
ARCHIVE_STATUS="absent"
ARCHIVE_PATH=""
ARCHIVE_SIZE=""
ARCHIVE_SHA=""
if [[ -n "${SCHOLARCHAIN_RUNTIME_ARCHIVE:-}" ]]; then
  ARCHIVE_PATH="${SCHOLARCHAIN_RUNTIME_ARCHIVE}"
elif [[ -f "${REPO_ROOT}/${RUNTIME_ARCHIVE_DEFAULT_PATH}" ]]; then
  ARCHIVE_PATH="${REPO_ROOT}/${RUNTIME_ARCHIVE_DEFAULT_PATH}"
fi
if [[ -n "${ARCHIVE_PATH}" ]]; then
  if [[ ! -f "${ARCHIVE_PATH}" ]]; then
    sc_fail "${EX_GATE}" "runtime archive path does not exist: ${ARCHIVE_PATH}"
  fi
  ARCHIVE_SIZE="$(wc -c <"${ARCHIVE_PATH}" | tr -d ' ')"
  if [[ "${ARCHIVE_SIZE}" != "${RUNTIME_ARCHIVE_EXPECTED_SIZE}" ]]; then
    sc_fail "${EX_GATE}" "runtime archive size ${ARCHIVE_SIZE} != expected ${RUNTIME_ARCHIVE_EXPECTED_SIZE}"
  fi
  ARCHIVE_SHA="$(sc_sha256 "${ARCHIVE_PATH}")"
  if [[ "${ARCHIVE_SHA}" != "${RUNTIME_ARCHIVE_EXPECTED_SHA256}" ]]; then
    sc_fail "${EX_GATE}" "runtime archive sha256 ${ARCHIVE_SHA} != expected ${RUNTIME_ARCHIVE_EXPECTED_SHA256}"
  fi
  ARCHIVE_STATUS="verified"
  sc_info "runtime archive verified: size=${ARCHIVE_SIZE} sha256=${ARCHIVE_SHA}"
else
  sc_warn "runtime archive not found; recorded as absent (G5 is verified again before upload in deploy.sh)"
  WARNINGS="${WARNINGS}runtime archive absent|"
  if [[ "${REQUIRE_ARCHIVE}" -eq 1 ]]; then
    sc_refuse "${EX_REFUSED}" "--require-runtime-archive set and no runtime archive found"
  fi
fi

# ---- build ------------------------------------------------------------------------------------
sc_step "jdk17"
sc_setup_jdk17

sc_step "sbt-package-release"
SBT="${SBT_BIN:-sbt}"
sc_require_tool "${SBT}" "install sbt or set SBT_BIN"
RC=0
sc_exec --timeout "${TIMEOUT_SBT_PACKAGE_SECONDS}" --log "${LOG_DIR}/sbt-packageRelease.log" -- "${SBT}" -batch packageRelease || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  sc_fail "$(sc_rc_to_exit "${RC}")" "sbt -batch packageRelease failed (exit ${RC}); log ${LOG_DIR}/sbt-packageRelease.log"
fi

# ---- collect artifacts ------------------------------------------------------------------------
sc_step "collect-artifacts"
# _pick_newest NAME GLOB: sets PICKED to the newest file matching GLOB (relative to the repo
# root); fails the run if none. Called directly (not in a subshell) so warnings persist.
PICKED=""
_pick_newest() {
  local name="$1" glob="$2" matches=() m
  while IFS= read -r m; do
    matches+=("${m}")
  done < <(compgen -G "${glob}" || true)
  if [[ ${#matches[@]} -eq 0 ]]; then
    sc_fail "${EX_GATE}" "${name}: no artifact matches ${glob}"
  fi
  if [[ ${#matches[@]} -gt 1 ]]; then
    sc_warn "${name}: ${#matches[@]} matches for ${glob}; using the newest (${matches[*]})"
    WARNINGS="${WARNINGS}${name}: multiple matches, newest used|"
  fi
  # shellcheck disable=SC2012 # ls -t orders by mtime; the names here are plain jar paths
  PICKED="$(ls -t "${matches[@]}" | head -n 1)"
}
_pick_newest hadoop-submit-jar "${ARTIFACT_HADOOP_SUBMIT_GLOB}"
SUBMIT_JAR="${PICKED}"
_pick_newest hadoop-dependency-bundle "${ARTIFACT_HADOOP_BUNDLE_GLOB}"
BUNDLE_JAR="${PICKED}"
_pick_newest spark-job-jar "${ARTIFACT_SPARK_JOB_GLOB}"
SPARK_JAR="${PICKED}"
_pick_newest er-job-jar "${ARTIFACT_ER_JOB_GLOB}"
ER_JAR="${PICKED}"
DIST_DIR="${ARTIFACT_SERVICE_DIST_DIR}"
for need in "${DIST_DIR}/services.jar" "${DIST_DIR}/prompts/runtime" "${DIST_DIR}/prompts/schemas"; do
  if [[ ! -e "${need}" ]]; then
    sc_fail "${EX_GATE}" "service distribution incomplete: ${need} missing"
  fi
done
if ! compgen -G "${DIST_DIR}/lib/*.jar" >/dev/null; then
  sc_fail "${EX_GATE}" "service distribution incomplete: no jars in ${DIST_DIR}/lib"
fi
sc_info "hadoop-submit-jar=${SUBMIT_JAR}"
sc_info "hadoop-dependency-bundle=${BUNDLE_JAR}"
sc_info "spark-job-jar=${SPARK_JAR}"
sc_info "er-job-jar=${ER_JAR}"
sc_info "service-distribution=${DIST_DIR}"

# ---- static checks (always) -------------------------------------------------------------------
sc_step "static-dockerfile-check"
MAINS=""
SERVICES=""
while read -r svc main; do
  MAINS="${MAINS} ${main}"
  SERVICES="${SERVICES} ${svc}"
done < <(sc_service_list)
RC=0
python3 -I "${SC_LIB_DIR}/tools.py" dockerfile-check --dockerfile "${DOCKERFILE}" --repo "${REPO_ROOT}" --mains "${MAINS# }" || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  sc_fail "${EX_GATE}" "static Dockerfile check failed"
fi

sc_step "arch-gate-ecs"
ECS_ARCH="$(sc_ecs_arch)" || sc_fail "${EX_GATE}" "cannot read the ECS cpu_architecture from ${ECS_ARCH_SOURCE}"
if [[ "${ECS_ARCH}" != "${IMAGE_PLATFORM}" ]]; then
  sc_fail "${EX_GATE}" "architecture gate: configured image platform ${IMAGE_PLATFORM} != ECS task architecture ${ECS_ARCH} (${ECS_ARCH_SOURCE})"
fi
sc_info "architecture gate (b) ok: configured ${IMAGE_PLATFORM} == ECS task ${ECS_ARCH}"

# ---- images -----------------------------------------------------------------------------------
sc_step "docker-images"
DOCKER_OK=0
DOCKER_SERVER=unknown
DOCKER_BUILDX=unknown
if command -v docker >/dev/null 2>&1; then
  if sc_exec --timeout 60 --log "${LOG_DIR}/docker-info.log" -- docker info; then
    DOCKER_OK=1
  fi
fi
ARCH_GATE=static-only
ARCH_DETAIL="static check only; images skipped"
IMAGE_FACTS=""
if [[ "${DOCKER_OK}" -eq 0 ]]; then
  if [[ "${REQUIRE_IMAGES}" -eq 1 ]]; then
    sc_refuse "${EX_REFUSED}" "Docker is unreachable and --require-images was given"
  fi
  sc_warn "Docker is unreachable: images were NOT built; falling back to jars plus the static Dockerfile check"
  WARNINGS="${WARNINGS}docker unreachable: images skipped|"
  while read -r svc main; do
    IMAGE_FACTS="${IMAGE_FACTS}image"$'\t'"${svc}"$'\t'"${LOCAL_IMAGE_PREFIX}-${svc}:${IMAGE_TAG}"$'\t'"skipped"$'\t'""$'\t'""$'\n'
  done < <(sc_service_list)
else
  sc_exec --timeout 60 --capture "${INSPECT_JSON}" -- docker version --format '{{.Server.Version}}' >/dev/null || true
  DOCKER_SERVER="$(tr -d '\n' <"${INSPECT_JSON}" 2>/dev/null || true)"
  [[ -n "${DOCKER_SERVER}" ]] || DOCKER_SERVER=unknown
  DOCKER_BUILDX="$(docker buildx version 2>/dev/null | head -n 1 || true)"
  [[ -n "${DOCKER_BUILDX}" ]] || DOCKER_BUILDX=unknown
  ARCH_GATE=passed
  ARCH_DETAIL="images ${IMAGE_PLATFORM} == ECS ${ECS_ARCH}"
  while read -r svc main; do
    img="${LOCAL_IMAGE_PREFIX}-${svc}:${IMAGE_TAG}"
    sc_info "building ${img} (MAIN_CLASS=${main}, platform ${IMAGE_PLATFORM})"
    RC=0
    sc_exec --timeout "${TIMEOUT_DOCKER_BUILD_SECONDS}" --log "${LOG_DIR}/docker-${svc}.log" -- \
      docker buildx build --platform "${IMAGE_PLATFORM}" --provenance=false --sbom=false \
      --build-arg "MAIN_CLASS=${main}" -f "${DOCKERFILE}" -t "${img}" --load . || RC=$?
    if [[ "${RC}" -ne 0 ]]; then
      sc_fail "$(sc_rc_to_exit "${RC}")" "docker buildx build failed for ${svc} (exit ${RC})"
    fi
    sc_step "arch-gate-image-${svc}"
    RC=0
    sc_exec --timeout 60 --capture "${INSPECT_JSON}" -- docker image inspect "${img}" || RC=$?
    if [[ "${RC}" -ne 0 ]]; then
      sc_fail "${EX_CMDFAIL}" "docker image inspect failed for ${img}"
    fi
    INSPECTED="$(python3 -I "${SC_LIB_DIR}/tools.py" image-inspect "${INSPECT_JSON}")" || sc_fail "${EX_GATE}" "cannot parse docker image inspect output for ${img}"
    OS_ARCH="${INSPECTED%% *}"
    IMAGE_ID="${INSPECTED#* }"
    if [[ "${OS_ARCH}" != "${IMAGE_PLATFORM}" ]]; then
      sc_fail "${EX_GATE}" "architecture gate: image ${img} is ${OS_ARCH}, expected ${IMAGE_PLATFORM}"
    fi
    sc_info "architecture gate (a) ok: ${img} is ${OS_ARCH}"
    IMAGE_FACTS="${IMAGE_FACTS}image"$'\t'"${svc}"$'\t'"${img}"$'\t'"built"$'\t'"${IMAGE_ID}"$'\t'"${OS_ARCH}"$'\n'
  done < <(sc_service_list)
fi

# ---- manifest ---------------------------------------------------------------------------------
sc_step "write-manifest"
JAVA_LINE="${SC_JAVA_VERSION:-unknown}"
SBT_VERSION="$(sed -n 's/^sbt.version=//p' "${REPO_ROOT}/project/build.properties" 2>/dev/null | head -n 1)"
{
  printf 'meta\tcommit\t%s\n' "${COMMIT}"
  printf 'meta\tdirty\t%s\n' "${DIRTY}"
  printf 'meta\tcreated_utc\t%s\n' "$(sc_now)"
  printf 'meta\trun_id\t%s\n' "${RUN_ID}"
  printf 'meta\timage_tag\t%s\n' "${IMAGE_TAG}"
  printf 'meta\timage_platform\t%s\n' "${IMAGE_PLATFORM}"
  printf 'meta\tecs_architecture\t%s\n' "${ECS_ARCH}"
  printf 'meta\tarch_gate\t%s\n' "${ARCH_GATE}"
  printf 'meta\tarch_gate_detail\t%s\n' "${ARCH_DETAIL}"
  printf 'meta\twarnings\t%s\n' "${WARNINGS%|}"
  printf 'toolchain\tjava\t%s\n' "${JAVA_LINE}"
  printf 'toolchain\tsbt\t%s\n' "${SBT_VERSION:-unknown}"
  printf 'toolchain\tpython\t%s\n' "$(python3 --version 2>&1)"
  printf 'toolchain\tgit\t%s\n' "$(git --version 2>&1)"
  printf 'toolchain\tdocker_server\t%s\n' "${DOCKER_SERVER}"
  printf 'toolchain\tdocker_buildx\t%s\n' "${DOCKER_BUILDX}"
  printf 'artifact\thadoop-submit-jar\tfile\t%s\n' "${REPO_ROOT}/${SUBMIT_JAR}"
  printf 'artifact\thadoop-dependency-bundle\tfile\t%s\n' "${REPO_ROOT}/${BUNDLE_JAR}"
  printf 'artifact\tspark-job-jar\tfile\t%s\n' "${REPO_ROOT}/${SPARK_JAR}"
  printf 'artifact\ter-job-jar\tfile\t%s\n' "${REPO_ROOT}/${ER_JAR}"
  printf 'artifact\tservice-distribution\tdir\t%s\n' "${REPO_ROOT}/${DIST_DIR}"
  printf '%s' "${IMAGE_FACTS}"
  printf 'archive\t%s\t%s\t%s\t%s\t%s\t%s\n' "${ARCHIVE_STATUS}" "${ARCHIVE_PATH}" "${ARCHIVE_SIZE}" "${ARCHIVE_SHA}" \
    "${RUNTIME_ARCHIVE_EXPECTED_SIZE}" "${RUNTIME_ARCHIVE_EXPECTED_SHA256}"
} >"${FACTS}"
python3 -I "${SC_LIB_DIR}/tools.py" release-manifest --facts "${FACTS}" --out "${MANIFEST}"
sc_info "manifest: ${MANIFEST}"
sc_info "manifest sha256: $(sc_sha256 "${MANIFEST}")"

if [[ "${DOCKER_OK}" -eq 0 ]]; then
  sc_result PASS "jars-built images-skipped(docker-unreachable) manifest=${MANIFEST}" "${EX_OK}"
fi
sc_result PASS "jars-built images-built arch-gate=passed manifest=${MANIFEST}" "${EX_OK}"
