# Jieqi project commands

# List all available commands (default)
default:
    @just --list

# === 测试命令 ===

# Run all tests (Rust + Python)
test:
    @echo "=== Rust Tests ==="
    cd rust-ai && cargo test
    @echo "=== Python Tests ==="
    uv run pytest tests/ -v
    @echo "=== All Tests Passed ==="

# Run Rust tests only
test-rust:
    cd rust-ai && cargo test

# Run Python tests only
test-py:
    uv run pytest tests/ -v

# === 服务命令 ===

# Start streamlit dashboard
start:
    uv run streamlit run streamlit_app.py --server.port 6704

# Restart with overmind
restart:
    -overmind quit 2>/dev/null
    -pkill -f "streamlit" 2>/dev/null
    -lsof -ti:6704 | xargs kill -9 2>/dev/null
    -rm -f .overmind.sock
    sleep 1
    overmind start -D
    @echo "Streamlit started on port 6704"

# === 构建命令 ===

# Install all dependencies
install:
    uv sync
    cd rust-ai && cargo build --release

# Build Rust release
build-rust:
    cd rust-ai && cargo build --release

# === 工具命令 ===

# Format code
fmt:
    uv run ruff format .
    cd rust-ai && cargo fmt

# Lint code
lint:
    uv run ruff check .
    cd rust-ai && cargo clippy

# Run AI battle
battle *ARGS:
    uv run python scripts/ai_battle.py {{ARGS}}

# === AI 评估命令 ===

# Generate AI evaluation report
ai-report STRATEGY="muses":
    uv run python scripts/ai_eval.py report --strategy {{STRATEGY}}

# Generate AI evaluation report with win rate testing
ai-report-winrate STRATEGY="muses" GAMES="5":
    uv run python scripts/ai_eval.py report --strategy {{STRATEGY}} --winrate --winrate-games {{GAMES}}

# List evaluation scenarios
ai-scenarios:
    uv run python scripts/ai_eval.py list-scenarios
