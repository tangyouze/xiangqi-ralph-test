# Xiangqi project commands

# List all available commands (default)
default:
    @just --list

# === 测试命令 ===

# Run all tests (Rust + Python)
test:
    @echo "=== Rust Tests ==="
    cd rust-ai && cargo test
    @echo "=== Python Tests ==="
    cd backend && uv run pytest tests/unit/ tests/integration/ -v
    @echo "=== All Tests Passed ==="

# Run Rust tests only
test-rust:
    cd rust-ai && cargo test

# Run Python tests only
test-py:
    cd backend && uv run pytest tests/ -v

# Run jieqi tests only
test-jieqi:
    cd backend && uv run pytest tests/unit/jieqi/ tests/integration/jieqi/ -v

# Run frontend e2e tests only
test-e2e:
    cd frontend && npm run test:e2e

# === 服务命令 ===

# Start all services with overmind
start:
    overmind start

# Restart overmind in daemon mode
restart:
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

# Start backend only (jieqi)
backend:
    cd backend && uv run uvicorn jieqi.api.app:app --host 0.0.0.0 --port 6703 --reload

# Start frontend only
frontend:
    cd frontend && npm run dev

# === 构建命令 ===

# Install all dependencies
install:
    cd backend && uv sync
    cd frontend && npm install
    cd rust-ai && cargo build --release

# Build Rust release
build-rust:
    cd rust-ai && cargo build --release

# Build frontend
build-frontend:
    cd frontend && npm run build

# === 工具命令 ===

# Format code
fmt:
    cd backend && uv run ruff format .
    cd rust-ai && cargo fmt

# Lint code
lint:
    cd backend && uv run ruff check .
    cd rust-ai && cargo clippy

# API health check
health:
    @curl -s http://localhost:6703/health | jq .
    @curl -s http://localhost:6703/ai/info | jq .

# Run AI battle
battle *ARGS:
    cd backend && uv run python scripts/ai_battle.py {{ARGS}}
