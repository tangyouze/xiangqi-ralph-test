# IT2 (Iterative Deepening v2)

## 核心思想

- **问题**：揭棋是不完全信息博弈，暗子翻开前身份未知
- **方案**：Expectimax 算法 + 迭代加深 + Alpha-Beta 剪枝

## 算法结构

### 1. 迭代加深搜索

从深度 1 开始逐步加深，支持时间限制：

```rust
for depth in 1..=max_depth {
    if time_limit_reached { break; }
    // 搜索当前深度
}
```

### 2. Expectimax 搜索

节点类型：
- **MAX 节点**：当前玩家，选择最大值
- **MIN 节点**：对手（Negamax 风格取负）
- **CHANCE 节点**：揭子走法，计算期望值

```
    MAX (我方)
       |
   ├── CHANCE (揭子) ← 枚举所有可能棋子，按概率加权
   │      |
   │   MIN (对方)
   │
   └── MIN (普通走法)
```

### 3. Alpha-Beta 剪枝

在 MAX/MIN 节点使用剪枝优化：

```rust
if alpha >= beta {
    break; // Beta 剪枝
}
```

## 概率计算

`HiddenPieceDistribution` 负责计算剩余暗子分布：

1. 统计已揭开的棋子类型和数量
2. 推算剩余暗子池：`remaining[type] = initial[type] - revealed[type]`
3. 概率 = `remaining[type] / total_remaining`
4. 期望值 = `Σ(probability × value)`

初始棋子数量：
| 类型 | 数量 | 价值 |
|------|------|------|
| King | 1 | 100000 |
| Advisor | 2 | 200 |
| Elephant | 2 | 200 |
| Horse | 2 | 400 |
| Rook | 2 | 900 |
| Cannon | 2 | 450 |
| Pawn | 5 | 100 |

## 评估函数

子力 + 吃子潜力：

### 1. 子力评估
- **明子**：使用实际棋子价值
- **暗子**：使用动态期望价值（所有暗子价值相同，和位置无关）
  - 车炮原价，其他 7 折
  - 鼓励揭车/炮

### 2. 吃子潜力（Capture Gain）
简单的 quiescence 替代方案：

```
best_gain_us = max(被吃子价值) for 我方所有吃子走法
best_gain_them = max(被吃子价值) for 对方所有吃子走法
score += 0.3 * (best_gain_us - best_gain_them)
```

权重 0.3 避免过度估计吃子潜力。

## 与 iterative.rs 的区别

| 方面 | iterative | IT2 |
|------|-----------|-----|
| 搜索 | Negamax | Expectimax |
| 暗子估值 | 固定值 320 | 动态期望价值 |
| 揭子处理 | 假设揭成 movement_type | Chance 节点枚举所有可能 |
| 时间控制 | 支持 | 支持 |

## 关键实现

| 组件 | 函数/结构体 | 说明 |
|------|-------------|------|
| 概率分布 | `HiddenPieceDistribution` | 计算剩余暗子概率 |
| 期望价值 | `expected_value()` | 暗子的加权平均价值 |
| 搜索入口 | `iterative_deepening()` | 迭代加深主循环 |
| Expectimax | `expectimax()` | Negamax 风格的递归搜索 |
| Chance 节点 | `chance_node()` | 处理揭子走法的期望值 |
| 模拟揭子 | `board.simulate_reveal()` | 临时设置暗子类型 |

## 使用

```rust
let config = AIConfig {
    depth: 4,           // 最大深度（有时间限制时忽略）
    time_limit: Some(1.0), // 1秒时间限制
    ..Default::default()
};
let ai = IT2AI::new(&config);
let moves = ai.select_moves(&board, 5);
```
