"""
揭棋 AI 策略集合

每个 AI 策略在独立的子文件夹中，使用版本号标识：
- v001_random: 随机 AI
- v002_greedy: 贪心 AI（只看一步）
- v003_positional: 位置评估 AI
- v004_defensive: 防守优先 AI
- v005_aggressive: 进攻性 AI
- v006_balanced: 综合平衡 AI
- v007_reveal: 揭子策略优化 AI
- v008_lookahead: 向前看一步 AI
- v009_coordination: 棋子协作 AI
- v010_fast: 快速评估 AI
- v011_minimax: Minimax 搜索 AI
- v012_alphabeta: Alpha-Beta + TT AI
- v013_iterative: 迭代加深搜索 AI
- v014_advanced: 高级搜索 AI
- v016_muses: Muses 风格 AI（参考揭棋 AI 大师思路）
- v017_muses2: 深度优化揭棋 AI
- v018_mcts: 基础 MCTS (UCT)
- v019_mcts_rave: MCTS + RAVE 快速收敛
- v020_mcts_eval: MCTS + 评估函数混合深度搜索
"""

# 导入所有策略以触发注册
from jieqi.ai.strategies.v001_random import strategy as v001  # noqa: F401
from jieqi.ai.strategies.v002_greedy import strategy as v002  # noqa: F401
from jieqi.ai.strategies.v003_positional import strategy as v003  # noqa: F401
from jieqi.ai.strategies.v004_defensive import strategy as v004  # noqa: F401
from jieqi.ai.strategies.v005_aggressive import strategy as v005  # noqa: F401
from jieqi.ai.strategies.v006_balanced import strategy as v006  # noqa: F401
from jieqi.ai.strategies.v007_reveal import strategy as v007  # noqa: F401
from jieqi.ai.strategies.v008_lookahead import strategy as v008  # noqa: F401
from jieqi.ai.strategies.v009_coordination import strategy as v009  # noqa: F401
from jieqi.ai.strategies.v010_fast import strategy as v010  # noqa: F401
from jieqi.ai.strategies.v011_minimax import strategy as v011  # noqa: F401
from jieqi.ai.strategies.v012_alphabeta import strategy as v012  # noqa: F401
from jieqi.ai.strategies.v013_iterative import strategy as v013  # noqa: F401
from jieqi.ai.strategies.v014_advanced import strategy as v014  # noqa: F401
from jieqi.ai.strategies.v016_muses import strategy as v016  # noqa: F401
from jieqi.ai.strategies.v017_muses2 import strategy as v017  # noqa: F401
from jieqi.ai.strategies.v018_mcts import strategy as v018  # noqa: F401
from jieqi.ai.strategies.v019_mcts_rave import strategy as v019  # noqa: F401
from jieqi.ai.strategies.v020_mcts_eval import strategy as v020  # noqa: F401
