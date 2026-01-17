# IT2 (Iterative Deepening v2)

## 核心思想

- **问题**：揭棋是不完全信息博弈，暗子翻开前身份未知
- **方案**：Expectimax 算法，揭子走法用 Chance 节点处理

## 节点结构

```
    MAX (我方)
       |
   Chance (揭子) ← 枚举所有可能棋子，按概率加权
       |
    MIN (对方)
```

## 概率计算

1. 统计已揭开的棋子类型和数量
2. 推算剩余暗子池：`remaining[type] = initial[type] - revealed[type]`
3. 概率 = `remaining[type] / total_remaining`
4. 期望值 = `Σ(probability × value)`

## 与 iterative.rs 的区别

| 方面 | iterative | IT2 |
|------|-----------|-----|
| 搜索 | Negamax | Expectimax |
| 暗子 | 固定值 320 | 动态期望价值 |
| 揭子 | 假设揭成 movement_type | Chance 节点枚举 |

## 关键实现点

1. `HiddenPieceDistribution` - 计算剩余暗子概率分布
2. `simulate_reveal()` - 模拟揭成特定棋子
3. `chance_node()` - Expectimax 的 Chance 节点处理
