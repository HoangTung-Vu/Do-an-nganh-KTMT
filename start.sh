#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping servers..."
    kill $(jobs -p)
    exit
}

trap cleanup SIGINT SIGTERM

echo "Starting Backend..."
cd BE
# Check if venv exists, if not assume global python or user needs to setup
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
# Run uvicorn
uvicorn main_api:app --reload --port 8000 &
BE_PID=$!

echo "Starting Frontend..."
cd ../FE
npm run dev &
FE_PID=$!

echo "Servers started!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop."

wait
