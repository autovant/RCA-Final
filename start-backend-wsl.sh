#!/bin/bash
# RCA-Final WSL Backend Startup Script

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required but was not found in PATH." >&2
    exit 1
fi

if ! command -v pip3 >/dev/null 2>&1 && ! python3 -m pip --version >/dev/null 2>&1; then
    echo "pip for Python 3 is required but not available." >&2
    exit 1
fi

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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

if port_in_use 8001; then
    listener="$(port_listener_info 8001)"
    echo "Port 8001 is already in use by ${listener:-an unknown process}." >&2
    echo "Stop the conflicting process or adjust the desired port before proceeding." >&2
    exit 1
fi

echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  RCA-Final Backend - WSL Deployment                    ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get the Windows path and convert to WSL path
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${CYAN}→ Working directory: ${NC}$SCRIPT_DIR"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}→ Creating Python virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate venv
echo -e "${CYAN}→ Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Install/update dependencies
echo -e "${CYAN}→ Installing Python dependencies...${NC}"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Run migrations
echo -e "${CYAN}→ Running database migrations...${NC}"
python -m alembic upgrade head
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Migrations complete${NC}"
else
    echo -e "${RED}✗ Migrations failed${NC}"
    echo -e "${YELLOW}Note: This might be expected if migrations have already been run${NC}"
fi
echo ""

# Start backend
echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Starting Backend Server                               ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Backend API:  ${NC}http://localhost:8001"
echo -e "${GREEN}API Docs:     ${NC}http://localhost:8001/docs"
echo -e "${GREEN}Database:     ${NC}rca_engine_final"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload
