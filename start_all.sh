#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================================"
echo "  Starting All Services"
echo "========================================================"

# Function to check if a port is in use
check_port() {
    lsof -i:$1 > /dev/null 2>&1
    return $?
}

# Kill any existing processes on these ports
echo -e "${YELLOW}Checking for existing processes...${NC}"
if check_port 8001; then
    echo "Killing process on port 8001..."
    lsof -ti:8001 | xargs kill -9 2>/dev/null
fi
if check_port 8002; then
    echo "Killing process on port 8002..."
    lsof -ti:8002 | xargs kill -9 2>/dev/null
fi
if check_port 8501; then
    echo "Killing process on port 8501..."
    lsof -ti:8501 | xargs kill -9 2>/dev/null
fi

sleep 2

# Start Whisper Server
echo -e "\n${GREEN}[1/3] Starting Whisper Server (Port 8001)...${NC}"
cd whisper_model
python whisper_server.py > ../logs/whisper.log 2>&1 &
WHISPER_PID=$!
cd ..
echo "Whisper PID: $WHISPER_PID"

# Wait a bit
sleep 2

# Start OCR Server
echo -e "\n${GREEN}[2/3] Starting OCR Server (Port 8002)...${NC}"
cd ocr_model
python ocr_server.py > ../logs/ocr.log 2>&1 &
OCR_PID=$!
cd ..
echo "OCR PID: $OCR_PID"

# Wait a bit
sleep 2

# Start Streamlit App
echo -e "\n${GREEN}[3/3] Starting Streamlit App (Port 8501)...${NC}"
streamlit run app_integrated.py > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo "Streamlit PID: $STREAMLIT_PID"

echo ""
echo "========================================================"
echo -e "${GREEN}✓ All services started!${NC}"
echo "========================================================"
echo ""
echo "Process IDs:"
echo "  Whisper:   $WHISPER_PID"
echo "  OCR:       $OCR_PID"
echo "  Streamlit: $STREAMLIT_PID"
echo ""
echo "URLs:"
echo "  Whisper:   http://localhost:8001/health"
echo "  OCR:       http://localhost:8002/health"
echo "  Streamlit: http://localhost:8501"
echo ""
echo "Logs:"
echo "  Whisper:   logs/whisper.log"
echo "  OCR:       logs/ocr.log"
echo "  Streamlit: logs/streamlit.log"
echo ""
echo "To stop all services, run: ./stop_all.sh"
echo "========================================================"

# Save PIDs to file for stopping later
echo "$WHISPER_PID" > logs/whisper.pid
echo "$OCR_PID" > logs/ocr.pid
echo "$STREAMLIT_PID" > logs/streamlit.pid
