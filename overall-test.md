# 揭棋项目测试指南

## 快速测试

```bash
# 一键运行所有测试
just test-all
```

## 测试组成

| 测试类型 | 命令 | 说明 |
|---------|------|------|
| Rust 单元测试 | `cd rust-ai && cargo test` | 23 个测试 |
| Python 单元测试 | `cd backend && pytest tests/unit/` | AI、棋盘、游戏逻辑 |
| Python 集成测试 | `cd backend && pytest tests/integration/` | API 端到端测试 |
| 前后端集成 | 手动 | 启动服务后浏览器测试 |

## 1. Rust AI 测试

```bash
cd rust-ai

# 运行所有测试
cargo test

# 运行特定测试
cargo test test_pvs

# 性能基准测试
./target/release/xiangqi-ai best \
  --fen "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r" \
  --strategy pvs --depth 20 --time-limit 1.0
```

预期输出：
```
test result: ok. 23 passed; 0 failed
Stats: nodes=..., time=1.0s, nps=1200000+
```

## 2. Python 后端测试

```bash
cd backend
source .venv/bin/activate

# 运行所有测试
pytest

# 运行单元测试（快）
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行特定测试文件
pytest tests/unit/jieqi/test_ai.py -v

# 运行带覆盖率
pytest --cov=jieqi --cov-report=html
```

预期输出：
```
30 passed
```

## 3. 启动服务

### 方式一：使用 overmind（推荐）

```bash
just overmind-start
```

### 方式二：手动启动

```bash
# 终端 1: 揭棋后端 (端口 6703)
cd backend && source .venv/bin/activate
uvicorn jieqi.api.app:app --host 0.0.0.0 --port 6703 --reload

# 终端 2: 前端 (端口 6701)
cd frontend
npm run dev
```

## 4. 前后端集成测试

### 4.1 API 健康检查

```bash
# 健康检查
curl http://localhost:6703/health

# 获取 AI 策略列表
curl http://localhost:6703/ai/info
```

### 4.2 创建游戏测试

```bash
# 创建人机对战
curl -X POST http://localhost:6703/games \
  -H "Content-Type: application/json" \
  -d '{"mode": "human_vs_ai", "ai_strategy": "pvs"}'

# 创建 AI 对战
curl -X POST http://localhost:6703/games \
  -H "Content-Type: application/json" \
  -d '{"mode": "ai_vs_ai", "red_ai_strategy": "pvs", "black_ai_strategy": "greedy"}'
```

### 4.3 浏览器测试

1. 打开 http://localhost:6701
2. 测试项目：
   - [ ] 创建新游戏
   - [ ] 点击棋子显示合法走法
   - [ ] 执行走法
   - [ ] AI 自动应答
   - [ ] 揭子功能
   - [ ] 悔棋功能
   - [ ] 游戏结束判定

## 5. AI 对战测试

```bash
cd backend
source .venv/bin/activate

# 快速对战（5局）
python scripts/ai_battle.py -n 5 -t 1.0 greedy minimax

# Python vs Rust 对战
python scripts/parallel_battle.py -n 10 -t 1.0 --python-strategy pvs --rust-strategy pvs
```

## 6. 完整测试流程

```bash
# 1. Rust 测试
cd rust-ai && cargo test && cargo build --release

# 2. Python 测试
cd ../backend && source .venv/bin/activate && pytest

# 3. 启动服务
just overmind-start &

# 4. 等待服务启动
sleep 3

# 5. API 测试
curl http://localhost:6703/health
curl http://localhost:6703/ai/info

# 6. 浏览器测试
open http://localhost:6701
```

## 7. CI/CD 测试脚本

```bash
#!/bin/bash
set -e

echo "=== Rust Tests ==="
cd rust-ai
cargo test
cargo build --release

echo "=== Python Tests ==="
cd ../backend
source .venv/bin/activate
pytest tests/unit/ tests/integration/ -v

echo "=== All Tests Passed ==="
```

## 常见问题

### Rust 编译失败
```bash
cd rust-ai && cargo clean && cargo build --release
```

### Python 依赖问题
```bash
cd backend && uv sync
```

### 端口被占用
```bash
lsof -i :6701 -i :6703
kill -9 <PID>
```

### 前端构建失败
```bash
cd frontend && rm -rf node_modules && npm install
```
