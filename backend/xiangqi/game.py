"""
游戏管理类

管理游戏状态、玩家回合和历史记录
"""

from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from xiangqi.board import Board
from xiangqi.piece import Piece
from xiangqi.types import Color, GameResult, Move


class Player(Protocol):
    """玩家接口"""

    color: Color

    def get_move(self, game: "Game") -> Move:
        """获取玩家的下一步走法"""
        ...


@dataclass
class MoveRecord:
    """走棋记录"""

    move: Move
    captured: Piece | None
    notation: str


@dataclass
class GameConfig:
    """游戏配置"""

    time_limit_seconds: int | None = None  # 每步时间限制
    total_time_seconds: int | None = None  # 总时间限制


class Game:
    """象棋游戏"""

    def __init__(self, game_id: str | None = None, config: GameConfig | None = None):
        self.game_id = game_id or str(uuid4())
        self.config = config or GameConfig()
        self.board = Board()
        self.current_turn = Color.RED
        self.move_history: list[MoveRecord] = []
        self.result = GameResult.ONGOING

    def make_move(self, move: Move) -> bool:
        """执行走棋

        返回：是否成功
        """
        if self.result != GameResult.ONGOING:
            return False

        if not self.board.is_valid_move(move, self.current_turn):
            return False

        # 执行走棋
        captured = self.board.make_move(move)
        notation = self._generate_notation(move, captured)
        self.move_history.append(MoveRecord(move, captured, notation))

        # 切换回合
        self.current_turn = self.current_turn.opposite

        # 检查游戏结果
        self.result = self.board.get_game_result(self.current_turn)

        return True

    def undo_move(self) -> bool:
        """撤销上一步"""
        if not self.move_history:
            return False

        record = self.move_history.pop()
        self.board.undo_move(record.move, record.captured)
        self.current_turn = self.current_turn.opposite
        self.result = GameResult.ONGOING
        return True

    def get_legal_moves(self) -> list[Move]:
        """获取当前方的所有合法走法"""
        return self.board.get_legal_moves(self.current_turn)

    def is_in_check(self) -> bool:
        """当前方是否被将军"""
        return self.board.is_in_check(self.current_turn)

    def _generate_notation(self, move: Move, captured: Piece | None) -> str:
        """生成走棋记谱"""
        piece = self.board.get_piece(move.to_pos)
        if piece is None:
            return move.to_notation()

        notation = f"{piece.piece_type.value}"
        if captured:
            notation += "x"
        notation += f"{move.from_pos.col}{move.from_pos.row}-{move.to_pos.col}{move.to_pos.row}"
        return notation

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "game_id": self.game_id,
            "board": self.board.to_dict(),
            "current_turn": self.current_turn.value,
            "result": self.result.value,
            "move_count": len(self.move_history),
            "is_in_check": self.is_in_check(),
            "legal_moves": [
                {
                    "from": {"row": m.from_pos.row, "col": m.from_pos.col},
                    "to": {"row": m.to_pos.row, "col": m.to_pos.col},
                }
                for m in self.get_legal_moves()
            ],
        }

    def get_move_history(self) -> list[dict]:
        """获取走棋历史"""
        return [
            {
                "move": {
                    "from": {"row": r.move.from_pos.row, "col": r.move.from_pos.col},
                    "to": {"row": r.move.to_pos.row, "col": r.move.to_pos.col},
                },
                "notation": r.notation,
                "captured": r.captured.to_dict() if r.captured else None,
            }
            for r in self.move_history
        ]

    def __repr__(self) -> str:
        return (
            f"Game({self.game_id}, turn={self.current_turn.value}, moves={len(self.move_history)})"
        )
