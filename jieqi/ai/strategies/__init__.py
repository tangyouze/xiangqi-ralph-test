"""
揭棋 AI 策略集合

每个 AI 策略在独立的子文件夹中，使用版本号标识：
- v001_random: 随机 AI
- v002_greedy: 贪心 AI（只看一步）
- v011_minimax: Minimax 搜索 AI
- v013_iterative: 迭代加深搜索 AI
- v016_muses: Muses 风格 AI（参考揭棋 AI 大师思路）
- v018_mcts: 基础 MCTS (UCT)

其他旧版策略已归档到 docs/archived_strategies.md
"""

# 导入所有策略以触发注册
from jieqi.ai.strategies.v001_random import strategy as v001  # noqa: F401
from jieqi.ai.strategies.v002_greedy import strategy as v002  # noqa: F401
from jieqi.ai.strategies.v011_minimax import strategy as v011  # noqa: F401
from jieqi.ai.strategies.v013_iterative import strategy as v013  # noqa: F401
from jieqi.ai.strategies.v016_muses import strategy as v016  # noqa: F401
from jieqi.ai.strategies.v018_mcts import strategy as v018  # noqa: F401
