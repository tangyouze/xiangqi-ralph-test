# 揭棋项目测试指南

## 快速开始

```bash
# 一键运行所有测试
just test
```

## 命令总览

```bash
just              # 显示所有命令
just test         # 运行全部测试 (Rust + Python)
just test-rust    # 只运行 Rust 测试
just test-py      # 只运行 Python 测试
just test-jieqi   # 只运行揭棋测试
just start        # 启动服务
just health       # 检查 API 健康状态
just battle       # 运行 AI 对战
```

## 测试命令详解

| 命令 | 说明 |
|------|------|
| `just test` | Rust 23个 + Python 196个测试 |
| `just test-rust` | Rust AI 引擎测试 |
| `just test-py` | Python 全部测试 |
| `just test-jieqi` | 揭棋相关测试 |
| `just test-e2e` | 前端 E2E 测试 |

## 服务命令

| 命令 | 说明 |
|------|------|
| `just start` | 启动所有服务 (overmind) |
| `just restart` | 重启所有服务 |
| `just backend` | 只启动揭棋后端 (6703) |
| `just frontend` | 只启动前端 (6701) |
| `just health` | 检查 API 健康状态 |

## 构建命令

| 命令 | 说明 |
|------|------|
| `just install` | 安装所有依赖 |
| `just build-rust` | 构建 Rust release |
| `just build-frontend` | 构建前端 |

## 工具命令

| 命令 | 说明 |
|------|------|
| `just fmt` | 格式化代码 |
| `just lint` | 代码检查 |
| `just battle` | 运行 AI 对战 |

## 完整测试流程

```bash
# 1. 安装依赖
just install

# 2. 运行所有测试
just test

# 3. 启动服务
just start

# 4. 检查 API
just health

# 5. 浏览器测试
open http://localhost:6701
```

## AI 对战测试

```bash
# 快速对战 (5局)
just battle -n 5 greedy minimax

# 指定时间限制
just battle -n 10 -t 1.0 greedy pvs
```

## 端口说明

| 端口 | 服务 |
|------|------|
| 6701 | 前端 |
| 6702 | 普通象棋后端 |
| 6703 | 揭棋后端 |
| 6704 | Dashboard |

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
