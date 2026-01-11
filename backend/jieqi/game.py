"""
揭棋游戏管理类

管理揭棋游戏状态、玩家回合和历史记录
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from jieqi.board import JieqiBoard
from jieqi.piece import JieqiPiece
from jieqi.types import (
    ActionType,
    Color,
    GameResult,
    JieqiMove,
    PieceState,
    get_position_piece_type,
)
from jieqi.view import CapturedPiece, PlayerView, ViewPiece


class Player(Protocol):
    """玩家接口"""

    color: Color

    def get_move(self, game: "JieqiGame") -> JieqiMove:
        """获取玩家的下一步走法"""
        ...


@dataclass
class MoveRecord:
    """走棋记录"""

    move: JieqiMove
    captured: JieqiPiece | None
    was_hidden: bool  # 走棋前是否为暗子
    revealed_type: str | None  # 揭开后的真实身份（如果是揭子走法）
    notation: str


@dataclass
class GameConfig:
    """游戏配置"""

    time_limit_seconds: int | None = None  # 每步时间限制
    total_time_seconds: int | None = None  # 总时间限制
    seed: int | None = None  # 随机种子（用于复现棋局）
    max_repetitions: int = 3  # 同一局面最大重复次数（超过判和）
    track_repetitions: bool = True  # 是否追踪重复局面
    delay_reveal: bool = False  # 延迟分配暗子身份（True=翻棋时决定）


class JieqiGame:
    """揭棋游戏"""

    def __init__(self, game_id: str | None = None, config: GameConfig | None = None):
        self.game_id = game_id or str(uuid4())
        self.config = config or GameConfig()
        self.board = JieqiBoard(
            seed=self.config.seed,
            delay_reveal=self.config.delay_reveal,
        )
        self.current_turn = Color.RED
        self.move_history: list[MoveRecord] = []
        self.result = GameResult.ONGOING
        # 被吃掉的棋子列表
        self.captured_pieces: list[CapturedPiece] = []
        # 重复局面追踪：position_key -> count
        self._position_counts: dict[str, int] = {}
        if self.config.track_repetitions:
            self._record_position()

    def make_move(
        self,
        move: JieqiMove,
        reveal_type: str | None = None,
    ) -> bool:
        """执行走棋

        Args:
            move: 走法
            reveal_type: 揭子时指定的棋子类型（仅延迟分配模式有效）
                - None：随机选择（默认）
                - str：指定类型名称（如 "rook", "horse" 等）

        返回：是否成功
        """
        from jieqi.types import PieceType

        if self.result != GameResult.ONGOING:
            return False

        if not self.board.is_valid_move(move, self.current_turn):
            return False

        # 记录走棋前的状态
        piece = self.board.get_piece(move.from_pos)
        if piece is None:
            return False

        was_hidden = piece.is_hidden
        revealed_type_str = None

        # 解析 reveal_type
        reveal_piece_type = None
        if reveal_type is not None:
            try:
                reveal_piece_type = PieceType(reveal_type)
            except ValueError:
                return False  # 无效的类型

        # 执行走棋（传递 reveal_type 给 board）
        captured = self.board.make_move(move, reveal_type=reveal_piece_type)

        # 记录被吃的棋子
        if captured is not None:
            self.captured_pieces.append(
                CapturedPiece(
                    color=captured.color,
                    was_hidden=captured.is_hidden,  # 注意：被吃时可能已经是明子（之前被翻过）
                    actual_type=captured.actual_type,  # 上帝视角保存真实身份
                    captured_by=self.current_turn,
                    move_number=len(self.move_history) + 1,
                )
            )

        # 如果是揭子走法，记录揭开的身份
        if move.action_type == ActionType.REVEAL_AND_MOVE:
            revealed_type_str = piece.actual_type.value if piece.actual_type else None

        notation = self._generate_notation(move, captured, revealed_type_str)
        self.move_history.append(
            MoveRecord(move, captured, was_hidden, revealed_type_str, notation)
        )

        # 切换回合
        self.current_turn = self.current_turn.opposite

        # 记录新局面
        if self.config.track_repetitions:
            self._record_position()

        # 检查游戏结果（包括重复局面判和）
        self.result = self._check_game_result()

        return True

    def _record_position(self) -> None:
        """记录当前局面"""
        key = self.board.get_position_key()
        self._position_counts[key] = self._position_counts.get(key, 0) + 1

    def _unrecord_position(self) -> None:
        """撤销当前局面的记录"""
        key = self.board.get_position_key()
        if key in self._position_counts:
            self._position_counts[key] -= 1
            if self._position_counts[key] <= 0:
                del self._position_counts[key]

    def get_position_count(self) -> int:
        """获取当前局面出现的次数"""
        key = self.board.get_position_key()
        return self._position_counts.get(key, 0)

    def _check_game_result(self) -> GameResult:
        """检查游戏结果，包括重复局面判和"""
        # 先检查基本结果
        result = self.board.get_game_result(self.current_turn)
        if result != GameResult.ONGOING:
            return result

        # 检查重复局面
        if self.config.track_repetitions:
            if self.get_position_count() >= self.config.max_repetitions:
                return GameResult.DRAW

        return GameResult.ONGOING

    def undo_move(self) -> bool:
        """撤销上一步"""
        if not self.move_history:
            return False

        # 撤销当前局面的记录
        if self.config.track_repetitions:
            self._unrecord_position()

        record = self.move_history.pop()
        self.board.undo_move(record.move, record.captured, record.was_hidden)
        self.current_turn = self.current_turn.opposite
        self.result = GameResult.ONGOING
        return True

    def get_legal_moves(self) -> list[JieqiMove]:
        """获取当前方的所有合法走法"""
        return self.board.get_legal_moves(self.current_turn)

    def is_in_check(self) -> bool:
        """当前方是否被将军"""
        return self.board.is_in_check(self.current_turn)

    def get_hidden_count(self, color: Color) -> int:
        """获取某方暗子数量"""
        return len(self.board.get_hidden_pieces(color))

    def get_revealed_count(self, color: Color) -> int:
        """获取某方明子数量"""
        return len(self.board.get_revealed_pieces(color))

    def get_view(self, viewer: Color) -> PlayerView:
        """获取某个玩家的视角

        Args:
            viewer: 谁在看

        Returns:
            PlayerView: 该玩家能看到的游戏状态
        """
        # 生成棋盘上的棋子视图
        pieces: list[ViewPiece] = []
        for piece in self.board.get_all_pieces():
            if piece.is_hidden:
                # 暗子：身份不可见，但需要知道走法类型（按位置规则）
                view_piece = ViewPiece(
                    color=piece.color,
                    position=piece.position,
                    is_hidden=True,
                    actual_type=None,  # 身份不可见
                    movement_type=get_position_piece_type(piece.position),
                )
            else:
                # 明子：身份可见
                view_piece = ViewPiece(
                    color=piece.color,
                    position=piece.position,
                    is_hidden=False,
                    actual_type=piece.actual_type,
                    movement_type=None,
                )
            pieces.append(view_piece)

        # 生成被吃棋子视图
        captured_view: list[CapturedPiece] = []
        for cap in self.captured_pieces:
            if cap.captured_by == viewer:
                # 我吃掉的对方棋子：能看到身份
                captured_view.append(
                    CapturedPiece(
                        color=cap.color,
                        was_hidden=cap.was_hidden,
                        actual_type=cap.actual_type,  # 可见
                        captured_by=cap.captured_by,
                        move_number=cap.move_number,
                    )
                )
            else:
                # 对方吃掉的我的棋子：如果被吃时是暗子，我不知道是什么
                if cap.was_hidden:
                    captured_view.append(
                        CapturedPiece(
                            color=cap.color,
                            was_hidden=cap.was_hidden,
                            actual_type=None,  # 不可见
                            captured_by=cap.captured_by,
                            move_number=cap.move_number,
                        )
                    )
                else:
                    # 被吃时是明子，我知道是什么
                    captured_view.append(
                        CapturedPiece(
                            color=cap.color,
                            was_hidden=cap.was_hidden,
                            actual_type=cap.actual_type,
                            captured_by=cap.captured_by,
                            move_number=cap.move_number,
                        )
                    )

        return PlayerView(
            viewer=viewer,
            current_turn=self.current_turn,
            result=self.result,
            move_count=len(self.move_history),
            is_in_check=self.board.is_in_check(self.current_turn),
            pieces=pieces,
            legal_moves=self.board.get_legal_moves(self.current_turn)
            if self.result == GameResult.ONGOING
            else [],
            captured_pieces=captured_view,
            hidden_count={
                "red": self.get_hidden_count(Color.RED),
                "black": self.get_hidden_count(Color.BLACK),
            },
        )

    def _generate_notation(
        self, move: JieqiMove, captured: JieqiPiece | None, revealed_type: str | None
    ) -> str:
        """生成走棋记谱"""
        # 格式: [R/M] 类型 起点-终点 (x被吃)
        piece = self.board.get_piece(move.to_pos)
        if piece is None:
            return move.to_notation()

        action_prefix = "R:" if move.action_type == ActionType.REVEAL_AND_MOVE else ""
        notation = f"{action_prefix}{piece.actual_type.value}"
        if captured:
            notation += "x"
        notation += f" {move.from_pos.col}{move.from_pos.row}-{move.to_pos.col}{move.to_pos.row}"
        return notation

    def to_dict(self) -> dict:
        """序列化为字典（不暴露暗子身份）"""
        return {
            "game_id": self.game_id,
            "board": self.board.to_dict(),
            "current_turn": self.current_turn.value,
            "result": self.result.value,
            "move_count": len(self.move_history),
            "is_in_check": self.is_in_check(),
            "hidden_count": {
                "red": self.get_hidden_count(Color.RED),
                "black": self.get_hidden_count(Color.BLACK),
            },
            "legal_moves": [
                {
                    "action_type": m.action_type.value,
                    "from": {"row": m.from_pos.row, "col": m.from_pos.col},
                    "to": {"row": m.to_pos.row, "col": m.to_pos.col},
                }
                for m in self.get_legal_moves()
            ],
        }

    def to_full_dict(self) -> dict:
        """序列化为完整字典（包含暗子身份，用于调试）"""
        return {
            "game_id": self.game_id,
            "board": self.board.to_full_dict(),
            "current_turn": self.current_turn.value,
            "result": self.result.value,
            "move_count": len(self.move_history),
            "is_in_check": self.is_in_check(),
            "hidden_count": {
                "red": self.get_hidden_count(Color.RED),
                "black": self.get_hidden_count(Color.BLACK),
            },
            "legal_moves": [
                {
                    "action_type": m.action_type.value,
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
                    "action_type": r.move.action_type.value,
                    "from": {"row": r.move.from_pos.row, "col": r.move.from_pos.col},
                    "to": {"row": r.move.to_pos.row, "col": r.move.to_pos.col},
                },
                "notation": r.notation,
                "captured": r.captured.to_dict() if r.captured else None,
                "revealed_type": r.revealed_type,
            }
            for r in self.move_history
        ]

    def __repr__(self) -> str:
        return f"JieqiGame({self.game_id}, turn={self.current_turn.value}, moves={len(self.move_history)})"
