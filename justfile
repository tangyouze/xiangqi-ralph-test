# Xiangqi project commands

# List all available commands (default)
default:
    @just --list

# Start both frontend and backend with overmind
overmind-start:
    overmind start

# Restart overmind in daemon mode and connect
overmind-restart:
    -overmind quit 2>/dev/null
    -pkill -f "uvicorn main:app" 2>/dev/null
    -pkill -f "uvicorn jieqi_main:app" 2>/dev/null
    -pkill -f "npm run dev -- --port 6701" 2>/dev/null
    -pkill -f "streamlit" 2>/dev/null
    -lsof -ti:6701 | xargs kill -9 2>/dev/null
    -lsof -ti:6702 | xargs kill -9 2>/dev/null
    -lsof -ti:6703 | xargs kill -9 2>/dev/null
    -lsof -ti:6704 | xargs kill -9 2>/dev/null
    -rm -f .overmind.sock
    sleep 1
    overmind start -D
    @echo "Waiting for services..."
    @sleep 5
    @echo "Services started. Use 'overmind connect' to attach."
    @echo "Ports: Frontend=6701, Backend=6702, Jieqi=6703, Dashboard=6704"
    open http://localhost:6701

# Start backend only
backend:
    cd backend && source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 6702 --reload

# Start frontend only
frontend:
    cd frontend && npm run dev

# Install all dependencies
install:
    cd backend && uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"
    cd frontend && npm install

# Run all tests
test:
    cd backend && source .venv/bin/activate && pytest tests/ -v
    cd frontend && npm run test:e2e

# Run backend tests only
test-backend:
    cd backend && source .venv/bin/activate && pytest tests/ -v --cov=xiangqi --cov-report=term-missing

# Run frontend e2e tests only
test-e2e:
    cd frontend && npm run test:e2e

# Format code
fmt:
    cd backend && source .venv/bin/activate && ruff format .

# Build frontend
build:
    cd frontend && npm run build
