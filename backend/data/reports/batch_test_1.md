# AI Battle Test Report - Batch 1

## Test Configuration

- **Date**: 2026-01-12
- **Strategies Tested**: aggressive, greedy, minimax, advanced, random
- **Games Per Matchup**: 5
- **Max Moves**: 200
- **Total Matchups**: 20 (round-robin)

## Results Summary

### Win Matrix (Row = Red, Column = Black)

| AI         | advanced | greedy | minimax | aggressive | random | Score  |
|------------|----------|--------|---------|------------|--------|--------|
| advanced   | -        | 30%    | 60%     | 30%        | 80%    | 70.0%  |
| greedy     | 20%      | -      | 40%     | 30%        | 60%    | 60.0%  |
| minimax    | 10%      | 20%    | -       | 40%        | 90%    | 55.0%  |
| aggressive | 10%      | 20%    | 20%     | -          | 60%    | 51.2%  |
| random     | 0%       | 0%     | 0%      | 0%         | -      | 13.8%  |

### Final Rankings

| Rank | Strategy   | Win Rate | Elo Rating |
|------|------------|----------|------------|
| 1    | advanced   | 70.0%    | 1616       |
| 2    | greedy     | 60.0%    | 1559       |
| 3    | minimax    | 55.0%    | 1534       |
| 4    | aggressive | 51.2%    | 1513       |
| 5    | random     | 13.8%    | 1305       |

## Strategy Analysis

### 1. Advanced (v014) - Champion

- **Performance**: 最强策略，胜率 70.0%，Elo 1616
- **Strengths**:
  - 对 random 有压倒性优势 (80%)
  - 对 minimax 表现优异 (60%)
- **Weaknesses**:
  - 对 greedy 和 aggressive 表现一般 (各 30%)
- **Summary**: 综合实力最强，在多数对局中占优

### 2. Greedy (v002) - Strong Contender

- **Performance**: 胜率 60.0%，Elo 1559
- **Strengths**:
  - 对 random 稳定获胜 (60%)
  - 策略简单但有效
- **Weaknesses**:
  - 对 advanced 处于劣势 (20%)
- **Summary**: 贪心策略表现出色，性价比高

### 3. Minimax (v011) - Solid Middle

- **Performance**: 胜率 55.0%，Elo 1534
- **Strengths**:
  - 对 random 有绝对优势 (90%)
  - 对 aggressive 有一定优势 (40%)
- **Weaknesses**:
  - 对 advanced 表现不佳 (10%)
  - 对 greedy 偏弱 (20%)
- **Summary**: 搜索算法表现中规中矩，对弱手效果好

### 4. Aggressive (v005) - Below Average

- **Performance**: 胜率 51.2%，Elo 1513
- **Strengths**:
  - 对 random 稳定 (60%)
- **Weaknesses**:
  - 对其他策略均处于劣势或平手
  - 对 advanced 和 minimax 表现最差 (各 10%, 20%)
- **Summary**: 激进策略在强手面前容易暴露弱点

### 5. Random (v001) - Baseline

- **Performance**: 最弱策略，胜率 13.8%，Elo 1305
- **Strengths**:
  - 无 (作为基准测试)
- **Weaknesses**:
  - 对所有策略均 0% 胜率
- **Summary**: 随机策略作为性能基准，验证其他策略的有效性

## Key Observations

1. **策略层级明显**: advanced > greedy > minimax > aggressive > random
2. **Elo 差距**: 顶尖 (1616) 与最弱 (1305) 相差约 300 分，表示约 85% 预期胜率差
3. **贪心策略有效**: greedy 虽简单但排名第二，说明在揭棋中短期利益很重要
4. **搜索深度并非万能**: minimax 有搜索深度但不如 greedy，可能因揭棋的随机性降低了前瞻优势
5. **激进策略风险高**: aggressive 容易被反制，表现不如预期

## Recommendations

1. 进一步优化 advanced 策略，特别是对抗 greedy 和 aggressive 的情况
2. 研究为什么 greedy 能战胜 minimax，可能需要调整评估函数
3. 考虑结合 greedy 的短期决策和 minimax 的长期规划
4. 增加测试样本量以获得更稳定的统计结果
