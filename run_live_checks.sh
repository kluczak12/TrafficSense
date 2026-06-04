#!/bin/bash

echo -e "\033[0;36mStarting docker-compose...\033[0m"
docker compose up -d --build

echo -e "\033[0;90mWaiting for services to become active...\033[0m"
max_retries=40
retry_interval=5
success=false

for ((i=1; i<=max_retries; i++)); do
    if curl -s -f http://localhost:3000/ > /dev/null; then
        success=true
        break
    fi
    echo -e "\033[0;90m  Waiting for frontend to respond... ($i/$max_retries)\033[0m"
    sleep $retry_interval
done

if [ "$success" = false ]; then
    echo -e "\033[0;31mTimeout: Services did not become healthy within $((max_retries * retry_interval)) seconds.\033[0m"
    docker compose down
    exit 1
fi

python test_endpoints.py "localhost:3000"
exit_code=$?

echo -e "\033[0;90mTearing down TrafficSense stack...\033[0m"
docker compose down

if [ $exit_code -eq 0 ]; then
    echo -e "\033[0;32mSUCCESS: All live endpoints checked successfully!\033[0m"
else
    echo -e "\033[0;31mFAILURE: Endpoint checks failed (Exit Code: $exit_code).\033[0m"
fi

exit $exit_code
