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

# Start streamlit dashboard (builds Rust first, kills existing on same port)
streamlit: build-rust
    -lsof -ti:6704 | xargs kill 2>/dev/null
    sleep 1
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

# 快速对战测试（10局, 0.1秒, 10并发）
# MODE: jieqi (揭棋，暗子开局) 或 revealed (明棋开局)
fast-battle RED="muses2" BLACK="muses" GAMES="10" MODE="jieqi":
    uv run python scripts/ai_battle.py compare --filter {{RED}},{{BLACK}} --games {{GAMES}} --time 0.1 --workers 10 --mode {{MODE}}

# Run single AI battle with verbose output
# MODE: jieqi (揭棋，暗子开局) 或 revealed (明棋开局)
battle-verbose RED="muses" BLACK="iterative" TIME="0.1" MODE="jieqi":
    uv run python scripts/ai_battle.py battle --games 1 --verbose --red {{RED}} --black {{BLACK}} --time {{TIME}} --mode {{MODE}}

# === Rust AI CLI ===

# Get legal moves for a position
rustai-moves FEN:
    cd rust-ai && cargo run --release -- moves --fen "{{FEN}}"

# Get best move(s) for a position
rustai-best FEN STRATEGY="muses" TIME="0.5" N="10":
    cd rust-ai && cargo run --release -- best --fen "{{FEN}}" --strategy {{STRATEGY}} --time-limit {{TIME}} --n {{N}} --json

# Evaluate position score (static, no search)
rustai-score FEN:
    cd rust-ai && cargo run --release -- score --fen "{{FEN}}"

# Static evaluation via eval command
rustai-eval FEN:
    cd rust-ai && cargo run --release -- score --fen "{{FEN}}" --json

# Search tree debug (two-layer info)
rustai-search FEN STRATEGY="it2" DEPTH="2":
    cd rust-ai && cargo run --release -- search --fen "{{FEN}}" --strategy {{STRATEGY}} --depth {{DEPTH}} --json

# Show help for Rust AI CLI
rustai-help:
    cd rust-ai && cargo run --release -- --help
