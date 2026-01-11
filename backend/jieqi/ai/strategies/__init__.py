"""
揭棋 AI 策略集合

每个 AI 策略在独立的子文件夹中，使用版本号标识：
- v001_random: 随机 AI
- v002_greedy: 贪心 AI（只看一步）
- v003_positional: 位置评估 AI
- v004_defensive: 防守优先 AI
- v005_aggressive: 进攻性 AI
"""

# 导入所有策略以触发注册
from jieqi.ai.strategies.v001_random import strategy as v001  # noqa: F401
from jieqi.ai.strategies.v002_greedy import strategy as v002  # noqa: F401
from jieqi.ai.strategies.v003_positional import strategy as v003  # noqa: F401
from jieqi.ai.strategies.v004_defensive import strategy as v004  # noqa: F401
from jieqi.ai.strategies.v005_aggressive import strategy as v005  # noqa: F401

# TODO: 以下策略待更新为使用 PlayerView 接口后再启用
# from jieqi.ai.strategies.v006_balanced import strategy as v006  # noqa: F401
# from jieqi.ai.strategies.v007_reveal import strategy as v007  # noqa: F401
# from jieqi.ai.strategies.v008_lookahead import strategy as v008  # noqa: F401
# from jieqi.ai.strategies.v009_coordination import strategy as v009  # noqa: F401
# from jieqi.ai.strategies.v010_fast import strategy as v010  # noqa: F401
# from jieqi.ai.strategies.v011_minimax import strategy as v011  # noqa: F401
# from jieqi.ai.strategies.v012_alphabeta import strategy as v012  # noqa: F401
# from jieqi.ai.strategies.v013_iterative import strategy as v013  # noqa: F401
# from jieqi.ai.strategies.v014_advanced import strategy as v014  # noqa: F401
