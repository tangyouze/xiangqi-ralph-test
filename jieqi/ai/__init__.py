"""
揭棋 AI 引擎

Python AI 策略已移除，现在使用 Rust 后端。
使用 UnifiedAIEngine 调用 Rust AI。
"""

from jieqi.ai.base import AIConfig, AIStrategy
from jieqi.ai.unified import DEFAULT_STRATEGY, UnifiedAIEngine

__all__ = [
    "DEFAULT_STRATEGY",
    "UnifiedAIEngine",
    "AIStrategy",
    "AIConfig",
]
