"""
揭棋 AI 引擎

提供各种 AI 策略实现
"""

from jieqi.ai.base import AIEngine, AIStrategy, AIConfig
from jieqi.ai.random_ai import RandomAI

__all__ = [
    "AIEngine",
    "AIStrategy",
    "AIConfig",
    "RandomAI",
]
