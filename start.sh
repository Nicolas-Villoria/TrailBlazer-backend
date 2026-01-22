#!/bin/bash

# TrailBlazer Full Stack Startup Script
# Starts both backend and frontend servers

echo "=========================================="
echo "🚀 TrailBlazer Full Stack Application"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/web/backend"
FRONTEND_DIR="$SCRIPT_DIR/web/frontend"

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Check if backend port (8000) is available
if check_port 8000; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use${NC}"
    echo "   Backend might already be running, or another service is using this port"
    read -p "   Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if frontend port (3000) is available
if check_port 3000; then
    echo -e "${YELLOW}⚠️  Port 3000 is already in use${NC}"
    echo "   Frontend might already be running, or another service is using this port"
    read -p "   Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo -e "${BLUE}📦 Starting Backend Server...${NC}"
echo "   Directory: $BACKEND_DIR"
echo "   Port: 8000"
echo ""

# Start backend in background
cd "$BACKEND_DIR"
python3 app.py > /tmp/trailblazer_backend.log 2>&1 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${YELLOW}❌ Backend failed to start${NC}"
    echo "   Check the log file: /tmp/trailblazer_backend.log"
    cat /tmp/trailblazer_backend.log
    exit 1
fi

echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
echo "   API URL: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   Log file: /tmp/trailblazer_backend.log"
echo ""

echo -e "${BLUE}🌐 Starting Frontend Server...${NC}"
echo "   Directory: $FRONTEND_DIR"
echo "   Port: 3000"
echo ""

# Start frontend in background
cd "$FRONTEND_DIR"
python3 serve.py > /tmp/trailblazer_frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait a moment for frontend to start
sleep 2

# Check if frontend is running
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${YELLOW}❌ Frontend failed to start${NC}"
    echo "   Check the log file: /tmp/trailblazer_frontend.log"
    cat /tmp/trailblazer_frontend.log
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
echo "   Frontend URL: http://localhost:3000"
echo "   Log file: /tmp/trailblazer_frontend.log"
echo ""

echo "=========================================="
echo -e "${GREEN}🎉 TrailBlazer is now running!${NC}"
echo "=========================================="
echo ""
echo "📍 Access Points:"
echo "   🌐 Web App:  http://localhost:3000"
echo "   📡 API:      http://localhost:8000"
echo "   📖 API Docs: http://localhost:8000/docs"
echo ""
echo "🔧 Process IDs:"
echo "   Backend:  $BACKEND_PID"
echo "   Frontend: $FRONTEND_PID"
echo ""
echo "📊 Logs:"
echo "   Backend:  /tmp/trailblazer_backend.log"
echo "   Frontend: /tmp/trailblazer_frontend.log"
echo ""
echo "To stop the servers:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "or press Ctrl+C to stop this script"
echo ""

# Save PIDs to file for easy cleanup
echo $BACKEND_PID > /tmp/trailblazer_backend.pid
echo $FRONTEND_PID > /tmp/trailblazer_frontend.pid

# Try to open browser
if command -v open &> /dev/null; then
    echo "🌐 Opening browser..."
    sleep 1
    open http://localhost:3000
elif command -v xdg-open &> /dev/null; then
    echo "🌐 Opening browser..."
    sleep 1
    xdg-open http://localhost:3000
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "=========================================="
    echo "🛑 Stopping TrailBlazer servers..."
    echo "=========================================="
    
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo "   Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null
    fi
    
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "   Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null
    fi
    
    rm -f /tmp/trailblazer_backend.pid
    rm -f /tmp/trailblazer_frontend.pid
    
    echo ""
    echo "✅ Servers stopped"
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup SIGINT SIGTERM

# Wait for user to press Ctrl+C
echo "Press Ctrl+C to stop all servers..."
echo ""

# Keep script running
while true; do
    sleep 1
    
    # Check if processes are still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo ""
        echo -e "${YELLOW}⚠️  Backend process died unexpectedly${NC}"
        echo "   Check log: /tmp/trailblazer_backend.log"
        cleanup
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo ""
        echo -e "${YELLOW}⚠️  Frontend process died unexpectedly${NC}"
        echo "   Check log: /tmp/trailblazer_frontend.log"
        cleanup
    fi
done
