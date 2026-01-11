# Xiangqi Project

## Current Focus

**揭棋 AI 开发** - 目标是构建一个超越顶尖人类水平的揭棋 AI。

### Goals

1. 实现多种 AI 策略 (random, greedy, minimax, MCTS, neural network)
2. 构建完善的测试框架用于 AI 对战和评估
3. 最终目标：创建世界顶级的揭棋 AI

### Ports

- Frontend: 6701
- Backend (普通象棋): 6702
- Backend (揭棋): 6703

### Commands

```bash
# 启动所有服务
just overmind-start

# AI 对战
cd backend && source .venv/bin/activate && python scripts/ai_battle.py --help
```
