# 搜索树可视化

## 概述

本文档描述 Streamlit 应用中搜索树可视化功能的设计方案。目标是展示 AI 如何搜索走法：
- 静态评估 vs 搜索评估
- MAX/MIN/CHANCE 节点结构
- 揭子走法的概率分布

## 目标

帮助用户理解：
1. **静态 vs 搜索分数**：为什么一个看起来好的走法（高静态分数）实际上可能是坏的（低搜索分数）
2. **MAX/MIN 结构**：AI 如何在选择最佳走法（MAX）和假设对手选择对我们最差走法（MIN）之间交替
3. **CHANCE 节点**：揭子走法如何处理 - AI 考虑所有可能的棋子类型，按概率加权

## UI 设计

### 布局

```
┌─────────────────────────────────────────────────┐
│  搜索树可视化                                    │
├─────────────────────────────────────────────────┤
│  侧边栏:                                         │
│  - FEN 输入框                                   │
│  - 搜索深度 (1-3)                               │
│  - [分析] 按钮                                  │
│                                                  │
│  主区域:                                         │
│  ┌─ 当前局面 ─────────────────────────────────┐ │
│  │ 静态: +120  │  搜索(d=2): -158             │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  第 1 层 - 红方 MAX (取最大值):                 │
│  ┌────────┬────────┬────────┬─────────────────┐ │
│  │ 走法   │ 类型   │ 静态   │ 搜索            │ │
│  ├────────┼────────┼────────┼─────────────────┤ │
│  │ +b0c2  │ CHANCE │ +80    │ -158 (期望值)   │ │
│  │ e0e1   │ MOVE   │ +100   │ -184            │ │
│  └────────┴────────┴────────┴─────────────────┘ │
│                                                  │
│  [点击走法展开第 2 层]                          │
│                                                  │
│  第 2 层 - 黑方 MIN (+b0c2 之后):               │
│  (CHANCE: 假设揭成车)                           │
│  ├─ a9b9: 静态 +600, 搜索 +450                  │
│  ├─ h8h0: 静态 +500, 搜索 +380                  │
│  └─ ...                                         │
└─────────────────────────────────────────────────┘
```

### 分数说明

| 术语 | 含义 |
|------|------|
| **静态** | 不搜索直接评估。只看棋子价值和位置。 |
| **搜索** | N 层搜索后的分数，考虑对手的最佳应对。 |

示例：
- 某走法静态分数 +500（吃掉一个车）
- 但搜索分数 -200（对手可以将死你）

## 算法：带 CHANCE 节点的 Minimax

### 节点类型

1. **MAX 节点**：当前玩家回合。选择分数最高的走法。
2. **MIN 节点**：对手回合。假设对手选择使我方分数最低的走法。
3. **CHANCE 节点**：揭子走法。枚举所有可能的棋子类型，计算期望值。

### CHANCE 节点概率

每方初始棋子池：
- 将/帅: 1
- 士/仕: 2
- 象/相: 2
- 马: 2
- 车: 2
- 炮: 2
- 兵/卒: 5
- **总计: 16**

概率公式：
```
P(棋子类型) = remaining[棋子类型] / total_remaining
```

示例：开局时，揭子可能揭成：
- 车: 2/16 = 12.5%
- 炮: 2/16 = 12.5%
- 兵: 5/16 = 31.25%
- 等等

期望值：
```
E = Σ P(类型) × search_score(类型)
```

### 搜索树示例

```
局面: 红方走棋
静态评估: +120

第 1 层 - MAX (红方取最大值):
├─ +b0c2 (CHANCE): 期望值 = -158
│   ├─ 如果是车 (12.5%): 搜索 = +500
│   ├─ 如果是炮 (12.5%): 搜索 = +200
│   ├─ 如果是兵 (31.25%): 搜索 = -300
│   └─ ...
│   期望值 = 0.125×500 + 0.125×200 + 0.3125×(-300) + ...
│
├─ e0e1 (MOVE): 搜索 = -184
│   第 2 层 - MIN (黑方取最小值):
│   ├─ a9b9: 搜索 = -184 (黑方最佳)
│   ├─ h8h0: 搜索 = -150
│   └─ ...
```

## 实现

### 文件结构
```
pages/2_Search.py      # Streamlit 页面
```

### 依赖
```python
from jieqi.ai.unified import UnifiedAIEngine  # Rust AI
from jieqi.ai.evaluator import JieqiEvaluator  # Python 评估器
from jieqi.fen import parse_move, to_fen
from jieqi.game import JieqiGame
```

### 核心函数

```python
def get_static_score(fen: str) -> float:
    """不搜索直接评估"""
    game = JieqiGame.from_fen(fen)
    evaluator = JieqiEvaluator()
    return evaluator.evaluate(board, game.current_turn)

def get_search_score(fen: str) -> tuple[str, float]:
    """使用 Rust AI 搜索评估"""
    engine = UnifiedAIEngine(strategy="iterative", time_limit=1.0)
    moves = engine.get_best_moves(fen, n=1)
    return moves[0] if moves else (None, 0)

def get_legal_moves(fen: str) -> list[str]:
    """获取所有合法走法"""
    engine = UnifiedAIEngine()
    return engine.get_legal_moves(fen)

def apply_move(fen: str, move: str) -> str:
    """执行走法并返回新 FEN"""
    game = JieqiGame.from_fen(fen)
    mv, reveal_type = parse_move(move)
    game.make_move(mv, reveal_type=reveal_type)
    return to_fen(game.get_view(game.current_turn))

def is_reveal_move(move: str) -> bool:
    """判断是否是揭子走法（以 + 开头）"""
    return move.startswith("+")
```

### 概率分布

```python
INITIAL_COUNTS = {
    "king": 1, "advisor": 2, "elephant": 2,
    "horse": 2, "rook": 2, "cannon": 2, "pawn": 5
}

def get_probability_distribution(remaining: dict) -> list[tuple[str, float]]:
    """计算每种棋子类型的概率"""
    total = sum(remaining.values())
    return [(t, c/total) for t, c in remaining.items() if c > 0]
```

## 预设局面

UI 侧边栏应提供以下预设局面供快速选择：

### 1. 初始局面
```
xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r
```
- 全是暗子
- 所有走法都是 CHANCE 节点
- 用于验证概率分布计算

### 2. 中局局面（红方有仕）
```
1pxxkxxAx/1p5r1/9/x1x1x1x1x/9/9/X1X1X1X1X/A8/9/1XXXKXXXX P:ap r r
```
- 红方已揭开一个仕（A）
- 黑方有车（r）和兵（p）
- 混合 MOVE 和 CHANCE 节点

### 3. 简单吃子局面
```
4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r
```
- 车可以吃炮
- 最佳走法明显：e4e5
- 用于验证静态 vs 搜索分数一致

### 4. 陷阱局面（待补充）
```
# TODO: 找一个静态看起来好但搜索分数差的局面
```
- 展示为什么需要搜索
- 静态高分但搜索后发现是陷阱

## 测试

### 运行方式
```bash
just streamlit
# 访问 http://localhost:6704，点击侧边栏 "Search"
```

### 验证要点

1. **初始局面**：
   - 所有走法都应该是 CHANCE 节点
   - 概率分布应该符合初始棋子数量（兵 31.25%，车/炮/马/象/士各 12.5%，将 6.25%）

2. **中局局面**：
   - 已揭开的棋子走法是 MOVE 节点
   - 暗子走法是 CHANCE 节点
   - 概率分布应排除已揭开的棋子

3. **简单吃子局面**：
   - 车 e4e5（吃炮）应该有最高搜索分数
   - 静态和搜索分数应该一致（因为吃子是明显好棋）

## 未来优化

1. **交互式树**：点击展开/折叠分支
2. **动画**：逐步展示搜索过程
3. **主要变例**：高亮最佳路线
4. **Alpha-Beta 剪枝可视化**：显示哪些分支被剪掉
