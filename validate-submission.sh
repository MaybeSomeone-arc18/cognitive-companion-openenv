#!/bin/bash

PING_URL=$1
REPO_DIR=${2:-.}

if [ -z "$PING_URL" ]; then
    echo -e "\033[31mError: Provide a ping_url.\033[0m"
    echo "Usage: $0 <ping_url> [repo_dir]"
    exit 1
fi

# Fix for the ping URL typo (-env instead of -openenv)
if [[ "$PING_URL" == *"maybesomeone19-cognitive-companion-env"* ]]; then
    PING_URL="${PING_URL/-env/-openenv}"
fi

cd "$REPO_DIR" || exit 1

echo -e "\033[34m=== Step 1: Pinging Space ===\033[0m"
HTTP_STATUS=$(curl -s -o /tmp/curl_out -w "%{http_code}" -X POST "$PING_URL/reset" -H "Content-Type: application/json" -d '{}')

if [ "$HTTP_STATUS" -ne 200 ]; then
    echo -e "\033[31mPing failed! Expected HTTP 200, got $HTTP_STATUS\033[0m"
    cat /tmp/curl_out
    echo ""
    exit 1
fi
echo -e "\033[32mPing successful (HTTP 200).\033[0m"

echo -e "\033[34m=== Step 2: Docker Build ===\033[0m"
docker build -t openenv-validation-image .
if [ $? -ne 0 ]; then
    echo -e "\033[31mDocker build failed!\033[0m"
    exit 1
fi
echo -e "\033[32mDocker build successful.\033[0m"

echo -e "\033[34m=== Step 3: OpenEnv Validate ===\033[0m"
# Check if openenv is installed
if ! command -v openenv &> /dev/null; then
    openenv validate
else
    openenv validate
fi

if [ $? -ne 0 ]; then
    echo -e "\033[31mopenenv validate failed!\033[0m"
    exit 1
fi
echo -e "\033[32mopenenv validate successful.\033[0m"
echo -e "\033[32mAll steps passed successfully!\033[0m"
