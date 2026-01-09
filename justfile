# Xiangqi project commands

# Start both frontend and backend with overmind
overmind-start:
    overmind start

# Start backend only
backend:
    cd backend && source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

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
