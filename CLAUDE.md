# 揭棋 AI 项目

## AI 策略概览

| 策略 | 类型 | 特点 | 适用场景 |
|------|------|------|----------|
| random | 随机 | 随机选择合法走法 | 基准测试 |
| greedy | 贪婪 | 只看当前吃子价值 | 简单对手 |
| iterative | Negamax | Alpha-Beta 剪枝，迭代加深 | 基础搜索 |
| mcts | 蒙特卡洛 | 随机模拟 | 不确定性博弈 |
| muses | PVS | Principal Variation Search，置换表，LMR | 标准搜索 |
| muses2 | PVS+ | 增加 Aspiration Window，Countermove，动态暗子期望值 | 增强搜索 |
| muses3 | PVS++ | 增加 IID，将军延伸，揭子延伸，残局评估 | 最强搜索 |
| it2 | Expectimax | 揭子走法用 Chance 节点处理概率 | 概率搜索 |

## 策略详解

### random
随机选择合法走法，用于基准测试。

### greedy
贪婪策略，只看当前一步能吃到的子的价值。

### iterative
- **算法**: Negamax + Alpha-Beta 剪枝
- **特点**: 迭代加深，时间控制
- **暗子处理**: 固定值 320

### mcts
- **算法**: Monte Carlo Tree Search
- **特点**: UCB1 选择，随机 playout

### muses
- **算法**: Principal Variation Search (PVS)
- **特点**:
  - 置换表 1M 条目
  - Late Move Reduction (LMR)
  - Killer moves & History heuristic
  - MVV-LVA 走法排序
  - Quiescence Search (深度4)
- **暗子处理**: 固定值

### muses2
在 muses 基础上增加：
- **Aspiration Window**: 上一深度最佳分数 ± 50
- **Countermove Heuristic**: 记录反制走法
- **动态暗子期望值**: 根据剩余暗子池计算平均价值
- **Delta Pruning**: 静态搜索剪枝

### muses3
在 muses2 基础上增加：
- **IID (Internal Iterative Deepening)**: 深度>=4 且无 TT 走法时，先做浅层搜索
- **将军延伸**: 将军时深度+1
- **揭子延伸**: 揭子时深度+1
- **残局评估**: 棋子<=10 时调整评估
- **置换表 2M**: 比 muses2 大一倍
- **Quiescence Search 深度6**: 比 muses 更深

### it2
- **算法**: Expectimax
- **核心改进**: 揭子走法使用 Chance 节点
- **概率计算**:
  ```
  remaining[type] = initial[type] - revealed[type]
  probability = remaining[type] / total_remaining
  expected_value = Σ(probability × value)
  ```
- **节点结构**:
  ```
      MAX (我方)
         |
     Chance (揭子) ← 枚举所有可能棋子，按概率加权
         |
      MIN (对方)
  ```

## 测试命令

```bash
# 获取最佳走法
just rustai-best "FEN" STRATEGY TIME N

# 单局详细对战
just battle-verbose RED BLACK TIME

# 快速对战（多局）
just fast-battle RED BLACK GAMES
```

## 文件位置

- `rust-ai/src/ai/random.rs` - 随机策略
- `rust-ai/src/ai/greedy.rs` - 贪婪策略
- `rust-ai/src/ai/iterative.rs` - 迭代加深
- `rust-ai/src/ai/mcts.rs` - MCTS
- `rust-ai/src/ai/muses.rs` - Muses (PVS)
- `rust-ai/src/ai/muses2.rs` - Muses2 (PVS+)
- `rust-ai/src/ai/muses3.rs` - Muses3 (PVS++)
- `rust-ai/src/ai/it2/mod.rs` - IT2 (Expectimax)


# language fix, streamlit, no use following function again

2026-01-19 06:42:32.306 Please replace `use_container_width` with `width`.

`use_container_width` will be removed after 2025-12-31.

For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.

