#!/bin/bash
# start-backend-host-network.sh
# Starts backend with host networking mode

set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required but was not found in PATH." >&2
    exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required but was not found in PATH." >&2
    exit 1
fi

port_listener_info() {
    local port="$1"

    if command -v lsof >/dev/null 2>&1; then
        lsof -Pi ":$port" -sTCP:LISTEN 2>/dev/null | awk 'NR==2 {printf "%s (PID %s)", $1, $2}'
        return
    fi

    if command -v ss >/dev/null 2>&1; then
        ss -ltnp "sport = :$port" 2>/dev/null | awk 'NR==2 {print $0; exit}'
        return
    fi

    if command -v netstat >/dev/null 2>&1; then
            netstat -ltnp 2>/dev/null | awk -v p=":$port" '$4 ~ p {print $7; exit}'
        return
    fi

    echo "unknown process"
}

port_in_use() {
    local port="$1"

    if command -v ss >/dev/null 2>&1; then
        ss -ltn 2>/dev/null | awk -v p=":$port" 'NR>1 && $4 ~ p {found=1; exit} END {exit (found==1)?0:1}'
        return $?
    fi

    if command -v lsof >/dev/null 2>&1; then
        lsof -Pi ":$port" -sTCP:LISTEN >/dev/null 2>&1
        return $?
    fi

        if command -v netstat >/dev/null 2>&1; then
            if netstat -ltn 2>/dev/null | grep -E "[:\.]$port\s" >/dev/null 2>&1; then
            return 0
        fi
    fi

    return 1
}

echo "==============================================="
echo "  START BACKEND WITH HOST NETWORKING"
echo "==============================================="
echo ""

echo "1. Stopping existing rca_core container..."
docker stop rca_core 2>/dev/null || true
docker rm rca_core 2>/dev/null || true
sleep 2
echo "   ✓ Stopped"
echo ""

if port_in_use 8000; then
    listener="$(port_listener_info 8000)"
    echo "Port 8000 is already in use by ${listener:-an unknown process}." >&2
    echo "Stop the conflicting process or adjust the port configuration before retrying." >&2
    exit 1
fi

echo "2. Starting backend with host network mode..."
echo "   (This allows Windows to access backend via localhost:8000)"
echo ""

docker run -d \
  --name rca_core \
  --network host \
  --restart unless-stopped \
  --env-file deploy/docker/.env \
  -e POSTGRES_HOST=localhost \
  -e POSTGRES_PORT=15432 \
  -e ENVIRONMENT=development \
  -e DEBUG=false \
  -e LOG_LEVEL=INFO \
  -v "$(pwd)/deploy/uploads:/app/uploads" \
  -v "$(pwd)/deploy/reports:/app/reports" \
  -v "$(pwd)/deploy/logs:/app/logs" \
  docker-rca_core

if [ $? -ne 0 ]; then
    echo "   ❌ Failed to start backend"
    exit 1
fi

echo "   ✓ Backend container started with host networking"
echo ""

echo "3. Waiting for backend to be ready..."
attempts=0
max_attempts=20

while [ $attempts -lt $max_attempts ]; do
    sleep 3
    ((attempts++))
    
    result=$(curl -s http://localhost:8000/api/health/live 2>&1)
    if echo "$result" | grep -q "ok"; then
        echo "   ✓ Backend is ready!"
        break
    else
        echo "   Attempt $attempts/$max_attempts..."
    fi
done

if [ $attempts -eq $max_attempts ]; then
    echo "   ⚠️  Backend didn't respond in time. Checking logs..."
    docker logs rca_core --tail 20
    exit 1
fi

echo ""
echo "==============================================="
echo "  BACKEND STARTED"
echo "==============================================="
echo ""
echo "Backend is running at: http://localhost:8000"
echo ""
echo "To stop: docker stop rca_core"
echo "To view logs: docker logs -f rca_core"
echo ""
