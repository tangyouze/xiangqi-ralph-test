# 架构设计

## 分层原则

```
┌─────────────────────────────────────────┐
│         Python 层（灵活）                │
│  - 游戏引擎 (jieqi/)                    │
│  - Streamlit UI                         │
│  - 测试验证                              │
│  - 数据分析                              │
└──────────────┬──────────────────────────┘
               │ CLI 接口
               ▼
┌─────────────────────────────────────────┐
│         Rust 内核（性能）                │
│  - AI 搜索                              │
│  - 评估函数                              │
└─────────────────────────────────────────┘
```

---

## Rust 接口定义

### 唯一对外接口：CLI

```bash
xiangqi-ai best \
  --fen <FEN> \
  --strategy <STRATEGY> \
  --time-limit <TIME> \
  --n <N> \
  --json
```

**输入**：
- `fen`: 当前局面
- `strategy`: AI策略 (it2, muses, iterative, greedy, ...)
- `time-limit`: 搜索时间限制（秒）
- `n`: 返回走法数量

**输出**（JSON）：
```json
{
  "moves": [
    {"move": "+a0a1", "score": 463.0},
    {"move": "+b0b1", "score": 450.0}
  ]
}
```

---

## 职责划分

### Rust 负责（内核）
- ✅ AI 算法实现
- ✅ 搜索优化
- ✅ 评估函数
- ✅ 通过 CLI 暴露接口

### Python 负责（其他一切）
- ✅ 游戏规则引擎
- ✅ FEN 解析
- ✅ 走法生成
- ✅ UI 渲染
- ✅ 数据分析
- ✅ 测试验证

### 接口边界
- Python 只通过 CLI 调用 Rust
- Rust 不关心 Python 内部实现
- JSON 是唯一的数据交换格式

---

## 当前实现

### Rust CLI
**文件**：`rust-ai/src/main.rs`

```rust
// 已实现
fn main() {
    match cli.command {
        Command::Best { fen, strategy, depth, n, json } => {
            let moves = ai.select_moves(&fen, n);
            if json {
                println!("{}", serde_json::to_string(&moves)?);
            }
        }
    }
}
```

### Python 调用
**文件**：`jieqi/ai/unified.py`

```python
class UnifiedAIEngine:
    def get_best_moves(self, fen: str, n: int) -> list[tuple[str, float]]:
        cmd = ["cargo", "run", "--release", "--",
               "best", fen,
               "--strategy", self.strategy,
               "--time-limit", str(self.time_limit),
               "--n", str(n),
               "--json"]

        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        return [(m["move"], m["score"]) for m in data["moves"]]
```

---

## 开发原则

1. **单一职责**：Rust = AI，Python = 其他
2. **最小接口**：只暴露必要的 CLI 命令
3. **松耦合**：通过 JSON 通信，互不依赖内部实现
4. **各自优化**：Rust 追求性能，Python 追求灵活

---

## 为什么这样设计？

**优势**：
- ✅ Rust 专注算法，不被 UI/引擎分散精力
- ✅ Python 快速迭代，不受 Rust 编译拖累
- ✅ 清晰边界，易于测试和维护
- ✅ 可独立升级（只要接口不变）

**替代方案（不推荐）**：
- ❌ 用 PyO3 绑定：复杂，调试困难
- ❌ Rust 做游戏引擎：重复工作
- ❌ Python 做 AI：性能差
