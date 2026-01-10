"""
AI Engine Module

Extensible AI engine with pluggable strategies.
"""

from xiangqi.ai.base import AIEngine, AIStrategy
from xiangqi.ai.random_ai import RandomAI
from xiangqi.ai.minimax_ai import MinimaxAI
from xiangqi.ai.greedy_ai import GreedyAI
from xiangqi.ai.defensive_ai import DefensiveAI
from xiangqi.ai.aggressive_ai import AggressiveAI

__all__ = [
    "AIEngine",
    "AIStrategy",
    "RandomAI",
    "MinimaxAI",
    "GreedyAI",
    "DefensiveAI",
    "AggressiveAI",
]
