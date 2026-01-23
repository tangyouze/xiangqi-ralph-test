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

# Export test positions to JSON
export-positions:
    uv run python scripts/export_positions.py

# Run search correctness tests (compares alpha-beta vs brute-force)
test-correctness:
    cd rust-ai && cargo test search_correctness --release -- --nocapture

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
# POSITION: 局面 ID（JIEQI/REVEALED/END0001 等）或 FEN 字符串
fast-battle RED="muses2" BLACK="muses" GAMES="10" POSITION="JIEQI":
    uv run python scripts/ai_battle.py compare --filter {{RED}},{{BLACK}} --games {{GAMES}} --time 0.1 --workers 10 --position "{{POSITION}}"

# 单局详细对战（支持局面 ID 或 FEN）
# POSITION: 局面 ID（JIEQI/REVEALED/END0001 等）或 FEN 字符串
battle-verbose RED="muses" BLACK="iterative" TIME="0.1" POSITION="JIEQI":
    uv run python scripts/ai_battle.py battle --games 1 --verbose --red {{RED}} --black {{BLACK}} --time {{TIME}} --position "{{POSITION}}"

# 列出可用局面
list-positions *ARGS:
    uv run python scripts/ai_battle.py list-positions {{ARGS}}

# === Rust AI CLI ===
# POSITION 参数支持局面 ID（如 END0001、JIEQI）或 FEN 字符串

# 辅助函数：将 POSITION 转换为 FEN
_get-fen POSITION:
    @uv run python scripts/get_fen.py '{{POSITION}}'

# Get legal moves for a position
rustai-moves POSITION:
    cd rust-ai && cargo run --release -- moves --fen "$(cd .. && uv run python scripts/get_fen.py '{{POSITION}}')"

# Get best move(s) for a position
rustai-best POSITION STRATEGY="muses" TIME="0.5" N="10":
    cd rust-ai && cargo run --release -- best --fen "$(cd .. && uv run python scripts/get_fen.py '{{POSITION}}')" --strategy {{STRATEGY}} --time-limit {{TIME}} --n {{N}} --json

# Evaluate position score (static, no search)
rustai-score POSITION:
    cd rust-ai && cargo run --release -- score --fen "$(cd .. && uv run python scripts/get_fen.py '{{POSITION}}')"

# Static evaluation via eval command
rustai-eval POSITION:
    cd rust-ai && cargo run --release -- score --fen "$(cd .. && uv run python scripts/get_fen.py '{{POSITION}}')" --json

# Search tree debug (two-layer info)
rustai-search POSITION STRATEGY="it2" DEPTH="2":
    cd rust-ai && cargo run --release -- search --fen "$(cd .. && uv run python scripts/get_fen.py '{{POSITION}}')" --strategy {{STRATEGY}} --depth {{DEPTH}} --json

# Show help for Rust AI CLI
rustai-help:
    cd rust-ai && cargo run --release -- --help
