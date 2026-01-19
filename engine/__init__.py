"""
揭棋 (Jieqi) - 中国象棋变体

揭棋是一种充满悬念和策略的象棋变体，开局时除将帅外，
其余棋子反面朝上（暗子）随机摆放，玩家轮流揭开暗子并走子。
"""

from engine.board import JieqiBoard
from engine.game import JieqiGame
from engine.piece import JieqiPiece, create_jieqi_piece
from engine.types import (
    ActionType,
    Color,
    GameResult,
    JieqiMove,
    PieceState,
    PieceType,
    Position,
)

__all__ = [
    "ActionType",
    "JieqiMove",
    "Color",
    "GameResult",
    "PieceState",
    "PieceType",
    "Position",
    "JieqiPiece",
    "create_jieqi_piece",
    "JieqiBoard",
    "JieqiGame",
]
