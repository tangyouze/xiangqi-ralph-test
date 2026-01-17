# Rust AI 接口文档

## 概述

Rust AI 提供两种使用方式：
1. **CLI 命令** - 单次执行
2. **Server 模式** - 长驻进程，通过 stdin/stdout JSON 通信

## CLI 命令

### moves - 获取合法走法

```bash
xiangqi-ai moves --fen "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"
```

输出：
```
Legal moves (44):
  +a0a1
  +a0b0
  ...
```

### best - 搜索最佳走法

```bash
xiangqi-ai best --fen "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r" \
    --strategy muses \
    --time-limit 0.5 \
    --n 5 \
    --json
```

参数：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--fen` | string | 必填 | FEN 字符串 |
| `--strategy` | string | muses | AI 策略 |
| `--time-limit` | float | 无 | 时间限制（秒） |
| `--n` | int | 1 | 返回走法数量 |
| `--json` | flag | false | JSON 输出 |

可用策略：`random`, `greedy`, `iterative`, `mcts`, `muses`, `muses2`, `muses3`, `it2`

输出（JSON）：
```json
{
  "total": 5,
  "moves": [
    {"move": "e4e5", "score": 450.0},
    {"move": "e4e3", "score": 120.0}
  ]
}
```

### score - 静态评估

```bash
xiangqi-ai score --fen "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r" --json
```

输出：
```json
{"fen": "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r", "color": "red", "score": 120.50}
```

### server - 启动服务模式

```bash
xiangqi-ai server
```

启动后通过 stdin 发送 JSON 请求，从 stdout 读取 JSON 响应。

## Server 协议

### 请求格式

所有请求都是单行 JSON：

```json
{"cmd": "命令名", "参数1": "值1", ...}
```

### 响应格式

```json
{
  "ok": true,
  "字段1": "值1",
  ...
}
```

错误响应：
```json
{
  "ok": false,
  "error": "错误信息"
}
```

### 命令列表

#### moves - 获取合法走法

请求：
```json
{"cmd": "moves", "fen": "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"}
```

响应：
```json
{
  "ok": true,
  "legal_moves": ["+a0a1", "+a0b0", "..."]
}
```

#### best - 搜索最佳走法

请求：
```json
{
  "cmd": "best",
  "fen": "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r",
  "strategy": "muses",
  "time_limit": 0.5,
  "n": 5
}
```

参数：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fen` | string | 必填 | FEN 字符串 |
| `strategy` | string | muses | AI 策略 |
| `time_limit` | float | 无 | 时间限制（秒） |
| `n` | int | 5 | 返回走法数量 |

响应：
```json
{
  "ok": true,
  "moves": [
    {"move": "e4e5", "score": 450.0},
    {"move": "e4e3", "score": 120.0}
  ],
  "depth": 8,
  "nodes": 125000,
  "nps": 250000.0,
  "elapsed_ms": 500.0
}
```

#### quit - 退出服务

请求：
```json
{"cmd": "quit"}
```

无响应，进程退出。

---

## 待实现的接口

以下接口用于 debug 和可视化，尚未实现：

### eval - 静态评估（不搜索）

请求：
```json
{"cmd": "eval", "fen": "..."}
```

响应：
```json
{
  "ok": true,
  "eval": 120.5,
  "color": "red"
}
```

说明：直接评估局面，不进行搜索。用于对比静态分数和搜索分数。

### search - 搜索树调试接口

请求：
```json
{
  "cmd": "search",
  "fen": "...",
  "depth": 5
}
```

参数：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fen` | string | 必填 | FEN 字符串 |
| `depth` | int | 必填 | 搜索深度 |

响应：
```json
{
  "ok": true,
  "fen": "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r",
  "eval": 100.0,
  "depth": 5,
  "first_moves": [
    {
      "move": "e4e5",
      "type": "move",
      "eval": 400.0,
      "score": 450.0,
      "opposite_top10": [
        {"move": "a9a8", "type": "move", "eval": -350.0, "score": -380.0},
        {"move": "b9b8", "type": "move", "eval": -320.0, "score": -350.0}
      ],
      "opposite_bottom10": [
        {"move": "h9h8", "type": "move", "eval": -100.0, "score": -50.0},
        {"move": "g9g8", "type": "move", "eval": -80.0, "score": -40.0}
      ]
    },
    {
      "move": "+b0c2",
      "type": "chance",
      "eval": 120.0,
      "score": 150.0,
      "opposite_top10": [...],
      "opposite_bottom10": [...]
    }
  ],
  "nodes": 5000
}
```

响应字段说明：

| 字段 | 说明 |
|------|------|
| `fen` | 当前局面 |
| `eval` | 当前局面的静态评估（不搜索） |
| `depth` | 搜索深度 |
| `first_moves` | 第一步所有走法（**完整列表，不能省略**） |
| `nodes` | 搜索节点数 |

> **注意**：`first_moves` 必须返回所有合法走法，不能只返回部分。这是为了完整展示搜索树第一层。

每个走法的字段：

| 字段 | 说明 |
|------|------|
| `move` | 走法字符串 |
| `type` | `move`（普通走法）或 `chance`（揭子走法） |
| `eval` | 走完这步后的静态评估（不搜索） |
| `score` | 走完这步后的搜索分数（搜索 depth-1 层） |
| `opposite_top10` | 对手最好的 10 个应对 |
| `opposite_bottom10` | 对手最差的 10 个应对 |

说明：
- 返回两层信息：第一步（所有走法）+ 对手应对（top10/bottom10）
- `eval` vs `score`：对比可发现"陷阱走法"（eval 高但 score 低）
- `type: chance` 表示揭子走法，涉及概率计算

---

## Python 调用示例

```python
from jieqi.ai.unified import UnifiedAIEngine

# 创建引擎
engine = UnifiedAIEngine(strategy="muses", time_limit=0.5)

# 获取合法走法
moves = engine.get_legal_moves(fen)

# 搜索最佳走法
best_moves = engine.get_best_moves(fen, n=5)

# 带统计信息
moves, nodes, nps = engine.get_best_moves_with_stats(fen, n=5)
```
