"""
AI Engine Module

Extensible AI engine with pluggable strategies.
"""

from xiangqi.ai.base import AIEngine, AIStrategy
from xiangqi.ai.random_ai import RandomAI
from xiangqi.ai.minimax_ai import MinimaxAI

__all__ = ["AIEngine", "AIStrategy", "RandomAI", "MinimaxAI"]
