#!/usr/bin/env bash
set -Eeuo pipefail
IMAGE="$1"
CONTAINER="$2"
PORT="$3"
TEST_CONTAINER="${CONTAINER}-candidate-test"
OLD_IMAGE=""
OLD_EXISTS=0

cleanup_test() { docker rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup_test EXIT

# Test candidate on a temporary port before touching the live container.
cleanup_test
docker run -d --name "$TEST_CONTAINER" -p 127.0.0.1:18001:8000 "$IMAGE" >/dev/null
ok=0
for _ in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:18001/health >/dev/null; then ok=1; break; fi
  sleep 2
done
if [[ "$ok" != "1" ]]; then
  echo "Candidate failed pre-deployment health check" >&2
  docker logs "$TEST_CONTAINER" || true
  exit 1
fi
cleanup_test

if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  OLD_EXISTS=1
  OLD_IMAGE="$(docker inspect --format='{{.Config.Image}}' "$CONTAINER")"
  docker rm -f "$CONTAINER" >/dev/null
fi

rollback() {
  code=$?
  if [[ "$code" -ne 0 ]]; then
    echo "Deployment failed; attempting rollback" >&2
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    if [[ "$OLD_EXISTS" == "1" && -n "$OLD_IMAGE" ]]; then
      docker run -d --restart unless-stopped --name "$CONTAINER" -p "${PORT}:8000" "$OLD_IMAGE" >/dev/null || true
    fi
  fi
  exit "$code"
}
trap rollback ERR

docker run -d --restart unless-stopped --name "$CONTAINER" -p "${PORT}:8000" "$IMAGE" >/dev/null
ok=0
for _ in $(seq 1 30); do
  if curl --fail --silent "http://127.0.0.1:${PORT}/health" >/dev/null; then ok=1; break; fi
  sleep 2
done
if [[ "$ok" != "1" ]]; then
  docker logs "$CONTAINER" || true
  echo "Live health check failed" >&2
  false
fi
trap - ERR
echo "Deployment healthy: $CONTAINER on port $PORT using $IMAGE"
