"""
揭棋 AI 引擎

提供各种 AI 策略实现

策略版本:
- v001_random: 随机 AI
- v002_greedy: 贪心 AI（只看一步）
"""

from jieqi.ai.base import AIEngine, AIStrategy, AIConfig

# 导入所有策略以触发注册
from jieqi.ai import strategies  # noqa: F401

__all__ = [
    "AIEngine",
    "AIStrategy",
    "AIConfig",
]
