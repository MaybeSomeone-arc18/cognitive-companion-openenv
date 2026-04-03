
#!/usr/bin/env bash
# Simple OpenEnv submission validator

set -euo pipefail

BOLD="\033[1m"
GREEN="\033[32m"
RED="\033[31m"
NC="\033[0m"

log()  { printf "%b\n" "$1"; }
pass() { printf "${GREEN}✓ %s${NC}\n" "$1"; }
fail() { printf "${RED}✗ %s${NC}\n" "$1"; }

PING_URL="${PING_URL:-}"
REPO_DIR="${REPO_DIR:-$(pwd)}"

if [ -z "$PING_URL" ]; then
  fail "PING_URL not set. Export PING_URL to your HF Space base URL."
  log "Example: export PING_URL=\"https://your-space-name.hf.space\""
  exit 1
fi

printf "${BOLD}=== OpenEnv Local Validator ===${NC}\n"
log "Repo:     $REPO_DIR"
log "Ping URL: $PING_URL"
printf "\n"

# Step 1: Ping HF Space /reset
log "${BOLD}Step 1/3: Pinging HF Space${NC} ($PING_URL/reset) ..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H "Content-Type: application/json" -d '{}' \
  "$PING_URL/reset" --max-time 30 || printf "000")

if [ "$HTTP_CODE" = "200" ]; then
  pass "HF Space is live and responds to /reset"
elif [ "$HTTP_CODE" = "000" ]; then
  fail "HF Space not reachable (connection failed or timed out)"
  log "Hint: Check that the Space is running and URL is correct."
  exit 1
else
  fail "HF Space /reset returned HTTP $HTTP_CODE (expected 200)"
  exit 1
fi

# Step 2: Docker build
log "${BOLD}Step 2/3: Running docker build${NC} ..."

if ! command -v docker >/dev/null 2>&1; then
  fail "docker command not found (install Docker first)"
  exit 1
fi

if [ -f "$REPO_DIR/Dockerfile" ]; then
  DOCKER_CONTEXT="$REPO_DIR"
elif [ -f "$REPO_DIR/server/Dockerfile" ]; then
  DOCKER_CONTEXT="$REPO_DIR/server"
else
  fail "No Dockerfile found in repo root or server/ directory"
  exit 1
fi

log "  Found Dockerfile in $DOCKER_CONTEXT"

if docker build "$DOCKER_CONTEXT"; then
  pass "Docker build succeeded"
else
  fail "Docker build failed"
  exit 1
fi

# Step 3: openenv validate
log "${BOLD}Step 3/3: Running openenv validate${NC} ..."

if ! command -v openenv >/dev/null 2>&1; then
  fail "openenv command not found (pip install openenv-core)"
  exit 1
fi

if (cd "$REPO_DIR" && openenv validate); then
  pass "openenv validate passed"
else
  fail "openenv validate failed"
  exit 1
fi

printf "\n${GREEN}${BOLD}All 3/3 checks passed! Your env looks ready.${NC}\n"

