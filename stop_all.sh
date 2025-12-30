#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "========================================================"
echo "  Stopping All Services"
echo "========================================================"

# Function to kill process by PID
kill_process() {
    if [ -f "logs/$1.pid" ]; then
        PID=$(cat logs/$1.pid)
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${RED}Stopping $1 (PID: $PID)...${NC}"
            kill $PID
            rm logs/$1.pid
        else
            echo "$1 was not running"
            rm logs/$1.pid
        fi
    else
        echo "$1 PID file not found"
    fi
}

kill_process "whisper"
kill_process "ocr"
kill_process "streamlit"

# Also kill by port as backup
lsof -ti:8001 | xargs kill -9 2>/dev/null
lsof -ti:8002 | xargs kill -9 2>/dev/null
lsof -ti:8501 | xargs kill -9 2>/dev/null

echo ""
echo -e "${GREEN}✓ All services stopped${NC}"
echo "========================================================"
