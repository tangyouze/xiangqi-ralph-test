"""
揭棋 AI 沙盒接口

提供干净的接口让用户：
1. 摆放任意棋盘局面
2. 调用 AI 获取下一步决策

信息隔离：AI 只能看到 PlayerView，无法看到暗子真实身份

## JFN (Jieqi FEN Notation) 格式

类似国际象棋 FEN，用于表示揭棋局面：

格式: `<棋盘>` `<回合>`

棋子符号:
- K/k = 将/帅 (King)
- R/r = 车 (Rook)
- H/h = 马 (Horse)
- C/c = 炮 (Cannon)
- E/e = 象 (Elephant)
- A/a = 士 (Advisor)
- P/p = 兵/卒 (Pawn)

规则:
- 大写 = 红方，小写 = 黑方
- (X) = 暗子，X 是真实类型
- 数字 = 连续空格数
- / = 行分隔符
- 最后 r/b = 当前回合方

示例 (标准开局):
(r)(h)(e)(a)(k)(a)(e)(h)(r)/9/1(c)5(c)1/(p)1(p)1(p)1(p)1(p)/9/9/(P)1(P)1(P)1(P)1(P)/1(C)5(C)1/9/(R)(H)(E)(A)(K)(A)(E)(H)(R) r
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jieqi.ai import AIEngine
from jieqi.simulation import SimulationBoard, SimPiece
from jieqi.types import (
    ActionType,
    Color,
    JieqiMove,
    PieceType,
    Position,
    get_position_piece_type,
)
from jieqi.view import PlayerView, ViewPiece

if TYPE_CHECKING:
    from jieqi.ai.base import AIStrategy


# 棋子类型映射（完整名称）
PIECE_TYPE_MAP = {
    "king": PieceType.KING,
    "k": PieceType.KING,
    "rook": PieceType.ROOK,
    "r": PieceType.ROOK,
    "horse": PieceType.HORSE,
    "h": PieceType.HORSE,
    "cannon": PieceType.CANNON,
    "c": PieceType.CANNON,
    "elephant": PieceType.ELEPHANT,
    "e": PieceType.ELEPHANT,
    "advisor": PieceType.ADVISOR,
    "a": PieceType.ADVISOR,
    "pawn": PieceType.PAWN,
    "p": PieceType.PAWN,
}

# JFN 单字符映射
JFN_CHAR_TO_TYPE = {
    "k": PieceType.KING,
    "r": PieceType.ROOK,
    "h": PieceType.HORSE,
    "c": PieceType.CANNON,
    "e": PieceType.ELEPHANT,
    "a": PieceType.ADVISOR,
    "p": PieceType.PAWN,
}

JFN_TYPE_TO_CHAR = {v: k for k, v in JFN_CHAR_TO_TYPE.items()}

COLOR_MAP = {
    "red": Color.RED,
    "r": Color.RED,
    "black": Color.BLACK,
    "b": Color.BLACK,
}


def _parse_piece_type(s: str) -> PieceType:
    """解析棋子类型"""
    key = s.lower()
    if key not in PIECE_TYPE_MAP:
        raise ValueError(f"Unknown piece type: {s}")
    return PIECE_TYPE_MAP[key]


def _parse_color(s: str) -> Color:
    """解析颜色"""
    key = s.lower()
    if key not in COLOR_MAP:
        raise ValueError(f"Unknown color: {s}")
    return COLOR_MAP[key]


def parse_jfn(jfn: str) -> tuple[list[BoardPiece], Color]:
    """解析 JFN 字符串

    Args:
        jfn: JFN 格式字符串

    Returns:
        (棋子列表, 当前回合方)

    Example:
        >>> pieces, turn = parse_jfn("(R)8/9/9/9/9/9/9/9/9/4k4 r")
    """
    parts = jfn.strip().split()
    if len(parts) != 2:
        raise ValueError(f"Invalid JFN format: expected '<board> <turn>', got: {jfn}")

    board_str, turn_str = parts

    # 解析回合
    turn = Color.RED if turn_str.lower() == "r" else Color.BLACK

    # 解析棋盘（从 row 9 到 row 0，因为 FEN 是从上往下）
    rows = board_str.split("/")
    if len(rows) != 10:
        raise ValueError(f"Invalid JFN: expected 10 rows, got {len(rows)}")

    pieces: list[BoardPiece] = []

    for row_idx, row_str in enumerate(rows):
        # JFN 从上往下是 row 9 到 row 0
        row = 9 - row_idx
        col = 0

        # 解析该行的棋子
        i = 0
        while i < len(row_str) and col < 9:
            ch = row_str[i]

            if ch.isdigit():
                # 空格
                col += int(ch)
                i += 1
            elif ch == "(":
                # 暗子: (X)
                end = row_str.find(")", i)
                if end == -1:
                    raise ValueError(f"Invalid JFN: unclosed parenthesis at row {row}")
                piece_char = row_str[i + 1 : end]
                if len(piece_char) != 1:
                    raise ValueError(f"Invalid JFN: expected single char in (), got: {piece_char}")

                piece_type = JFN_CHAR_TO_TYPE.get(piece_char.lower())
                if piece_type is None:
                    raise ValueError(f"Invalid JFN: unknown piece type: {piece_char}")

                color = Color.RED if piece_char.isupper() else Color.BLACK
                pieces.append(
                    BoardPiece(
                        position=Position(row, col),
                        piece_type=piece_type,
                        color=color,
                        is_hidden=True,
                    )
                )
                col += 1
                i = end + 1
            elif ch.isalpha():
                # 明子: X
                piece_type = JFN_CHAR_TO_TYPE.get(ch.lower())
                if piece_type is None:
                    raise ValueError(f"Invalid JFN: unknown piece type: {ch}")

                color = Color.RED if ch.isupper() else Color.BLACK
                pieces.append(
                    BoardPiece(
                        position=Position(row, col),
                        piece_type=piece_type,
                        color=color,
                        is_hidden=False,
                    )
                )
                col += 1
                i += 1
            else:
                raise ValueError(f"Invalid JFN: unexpected character: {ch}")

        if col != 9:
            raise ValueError(f"Invalid JFN: row {row} has {col} columns, expected 9")

    return pieces, turn


def to_jfn(pieces: list[BoardPiece], turn: Color) -> str:
    """生成 JFN 字符串

    Args:
        pieces: 棋子列表
        turn: 当前回合方

    Returns:
        JFN 格式字符串
    """
    # 构建棋盘数组
    board: list[list[BoardPiece | None]] = [[None] * 9 for _ in range(10)]
    for piece in pieces:
        board[piece.position.row][piece.position.col] = piece

    rows_str: list[str] = []

    # 从 row 9 到 row 0 （FEN 从上往下）
    for row in range(9, -1, -1):
        row_str = ""
        empty_count = 0

        for col in range(9):
            piece = board[row][col]
            if piece is None:
                empty_count += 1
            else:
                if empty_count > 0:
                    row_str += str(empty_count)
                    empty_count = 0

                char = JFN_TYPE_TO_CHAR[piece.piece_type]
                if piece.color == Color.RED:
                    char = char.upper()

                if piece.is_hidden:
                    row_str += f"({char})"
                else:
                    row_str += char

        if empty_count > 0:
            row_str += str(empty_count)

        rows_str.append(row_str)

    board_str = "/".join(rows_str)
    turn_str = "r" if turn == Color.RED else "b"

    return f"{board_str} {turn_str}"


@dataclass
class BoardPiece:
    """棋盘上的棋子（上帝视角，知道所有信息）"""

    position: Position
    piece_type: PieceType
    color: Color
    is_hidden: bool


@dataclass
class BoardSetup:
    """棋盘构建器

    用于摆放任意棋盘局面（上帝视角）

    Example:
        setup = BoardSetup()
        setup.hidden(0, 4, "king", "red")
        setup.hidden(0, 0, "rook", "red")
        setup.revealed(5, 4, "pawn", "red")

        position = setup.build(turn="red")
        move = AIPlayer("greedy").next_move(position, "red")
    """

    _pieces: list[BoardPiece] = field(default_factory=list)

    def hidden(
        self, row: int, col: int, piece_type: str, color: str
    ) -> BoardSetup:
        """放置暗子

        Args:
            row: 行号 (0-9, 0是红方底线)
            col: 列号 (0-8)
            piece_type: 棋子类型 (king/rook/horse/cannon/elephant/advisor/pawn)
            color: 颜色 (red/black)

        Returns:
            self (支持链式调用)
        """
        pos = Position(row, col)
        self._pieces.append(
            BoardPiece(
                position=pos,
                piece_type=_parse_piece_type(piece_type),
                color=_parse_color(color),
                is_hidden=True,
            )
        )
        return self

    def revealed(
        self, row: int, col: int, piece_type: str, color: str
    ) -> BoardSetup:
        """放置明子

        Args:
            row: 行号 (0-9, 0是红方底线)
            col: 列号 (0-8)
            piece_type: 棋子类型
            color: 颜色

        Returns:
            self (支持链式调用)
        """
        pos = Position(row, col)
        self._pieces.append(
            BoardPiece(
                position=pos,
                piece_type=_parse_piece_type(piece_type),
                color=_parse_color(color),
                is_hidden=False,
            )
        )
        return self

    def clear(self) -> BoardSetup:
        """清空棋盘"""
        self._pieces.clear()
        return self

    def build(self, turn: str = "red") -> GamePosition:
        """构建游戏局面

        Args:
            turn: 当前回合方 (red/black)

        Returns:
            GamePosition 对象
        """
        return GamePosition(
            pieces=list(self._pieces),
            current_turn=_parse_color(turn),
        )

    @classmethod
    def standard(cls) -> BoardSetup:
        """创建标准开局（所有棋子都是暗子）"""
        setup = cls()

        # 红方 (row 0-4)
        # 底线
        setup.hidden(0, 0, "rook", "red")
        setup.hidden(0, 1, "horse", "red")
        setup.hidden(0, 2, "elephant", "red")
        setup.hidden(0, 3, "advisor", "red")
        setup.hidden(0, 4, "king", "red")
        setup.hidden(0, 5, "advisor", "red")
        setup.hidden(0, 6, "elephant", "red")
        setup.hidden(0, 7, "horse", "red")
        setup.hidden(0, 8, "rook", "red")
        # 炮
        setup.hidden(2, 1, "cannon", "red")
        setup.hidden(2, 7, "cannon", "red")
        # 兵
        setup.hidden(3, 0, "pawn", "red")
        setup.hidden(3, 2, "pawn", "red")
        setup.hidden(3, 4, "pawn", "red")
        setup.hidden(3, 6, "pawn", "red")
        setup.hidden(3, 8, "pawn", "red")

        # 黑方 (row 5-9)
        # 底线
        setup.hidden(9, 0, "rook", "black")
        setup.hidden(9, 1, "horse", "black")
        setup.hidden(9, 2, "elephant", "black")
        setup.hidden(9, 3, "advisor", "black")
        setup.hidden(9, 4, "king", "black")
        setup.hidden(9, 5, "advisor", "black")
        setup.hidden(9, 6, "elephant", "black")
        setup.hidden(9, 7, "horse", "black")
        setup.hidden(9, 8, "rook", "black")
        # 炮
        setup.hidden(7, 1, "cannon", "black")
        setup.hidden(7, 7, "cannon", "black")
        # 卒
        setup.hidden(6, 0, "pawn", "black")
        setup.hidden(6, 2, "pawn", "black")
        setup.hidden(6, 4, "pawn", "black")
        setup.hidden(6, 6, "pawn", "black")
        setup.hidden(6, 8, "pawn", "black")

        return setup


@dataclass
class GamePosition:
    """游戏局面（上帝视角）

    包含完整的棋盘信息，可以生成任意玩家的视角
    """

    pieces: list[BoardPiece]
    current_turn: Color

    def get_view(self, viewer: Color) -> PlayerView:
        """获取指定玩家的视角

        信息隔离在这里发生：暗子的 actual_type 被遮蔽

        Args:
            viewer: 观察者颜色

        Returns:
            PlayerView（AI 使用的输入）
        """
        view_pieces: list[ViewPiece] = []

        for bp in self.pieces:
            if bp.is_hidden:
                # 暗子：不知道真实身份，只知道走法类型（由位置决定）
                movement_type = get_position_piece_type(bp.position)
                view_pieces.append(
                    ViewPiece(
                        position=bp.position,
                        color=bp.color,
                        is_hidden=True,
                        actual_type=None,  # 关键：AI 看不到
                        movement_type=movement_type,
                    )
                )
            else:
                # 明子：知道真实身份
                view_pieces.append(
                    ViewPiece(
                        position=bp.position,
                        color=bp.color,
                        is_hidden=False,
                        actual_type=bp.piece_type,
                        movement_type=bp.piece_type,
                    )
                )

        # 计算合法走法
        legal_moves = self._compute_legal_moves(viewer)

        # 检查是否被将军
        from jieqi.simulation import SimulationBoard
        from jieqi.types import GameResult

        temp_view = PlayerView(
            viewer=viewer,
            current_turn=self.current_turn,
            result=GameResult.ONGOING,
            move_count=0,
            is_in_check=False,
            pieces=view_pieces,
            legal_moves=[],
            captured_pieces=[],
        )
        sim = SimulationBoard(temp_view)
        is_in_check = sim.is_in_check(self.current_turn)

        return PlayerView(
            viewer=viewer,
            current_turn=self.current_turn,
            result=GameResult.ONGOING,
            move_count=0,
            is_in_check=is_in_check,
            pieces=view_pieces,
            legal_moves=legal_moves,
            captured_pieces=[],
        )

    def _compute_legal_moves(self, color: Color) -> list[JieqiMove]:
        """计算合法走法"""
        # 如果不是该方回合，返回空
        if self.current_turn != color:
            return []

        # 使用 SimulationBoard 计算
        view = self._create_internal_view(color)
        sim = SimulationBoard(view)
        return sim.get_legal_moves(color)

    def _create_internal_view(self, viewer: Color) -> PlayerView:
        """创建内部视角（用于计算走法）"""
        view_pieces: list[ViewPiece] = []

        for bp in self.pieces:
            if bp.is_hidden:
                movement_type = get_position_piece_type(bp.position)
                view_pieces.append(
                    ViewPiece(
                        position=bp.position,
                        color=bp.color,
                        is_hidden=True,
                        actual_type=None,
                        movement_type=movement_type,
                    )
                )
            else:
                view_pieces.append(
                    ViewPiece(
                        position=bp.position,
                        color=bp.color,
                        is_hidden=False,
                        actual_type=bp.piece_type,
                        movement_type=bp.piece_type,
                    )
                )

        from jieqi.types import GameResult

        return PlayerView(
            viewer=viewer,
            current_turn=self.current_turn,
            result=GameResult.ONGOING,
            move_count=0,
            is_in_check=False,
            pieces=view_pieces,
            legal_moves=[],  # 先空，避免循环
            captured_pieces=[],
        )


class AIPlayer:
    """AI 玩家

    封装 AI 策略，提供简洁的接口

    Example:
        ai = AIPlayer("greedy")
        move = ai.next_move(position, "red")
    """

    def __init__(self, strategy: str = "greedy"):
        """创建 AI 玩家

        Args:
            strategy: AI 策略名称 (random/greedy/positional/advanced 等)
        """
        self._strategy_name = strategy
        self._ai: AIStrategy = AIEngine.create(strategy)

    @property
    def strategy(self) -> str:
        """AI 策略名称"""
        return self._strategy_name

    def next_move(
        self, position: GamePosition, as_color: str | Color
    ) -> JieqiMove | None:
        """获取 AI 的下一步

        Args:
            position: 游戏局面
            as_color: AI 执子颜色

        Returns:
            AI 选择的走法，如果无合法走法则返回 None
        """
        if isinstance(as_color, str):
            color = _parse_color(as_color)
        else:
            color = as_color

        # 获取该颜色的视角（信息隔离）
        view = position.get_view(color)

        # AI 决策
        return self._ai.select_move(view)


# =============================================================================
# 核心接口：state -> next_move
# =============================================================================


def think(view: PlayerView, strategy: str = "greedy") -> JieqiMove | None:
    """核心函数：给定视角，返回下一步走法

    这是 AI 的核心接口，下棋程序不断调用此函数：
    1. 游戏给 AI 一个 PlayerView
    2. AI 返回下一步 JieqiMove
    3. 游戏执行走法，更新状态
    4. 重复

    Args:
        view: 玩家视角（AI 看到的信息）
        strategy: AI 策略名称

    Returns:
        AI 选择的走法，无合法走法时返回 None

    Example:
        >>> view = position.get_view(Color.RED)
        >>> move = think(view, "greedy")
    """
    ai = AIEngine.create(strategy)
    return ai.select_move(view)


def think_from_jfn(
    jfn: str,
    player: str | Color = "red",
    strategy: str = "greedy",
) -> JieqiMove | None:
    """从 JFN 字符串获取 AI 走法

    便捷函数，一行代码完成：解析 -> 获取视角 -> AI 思考

    Args:
        jfn: JFN 格式棋盘字符串
        player: AI 执子颜色
        strategy: AI 策略

    Returns:
        AI 选择的走法

    Example:
        >>> move = think_from_jfn(
        ...     "(r)(h)(e)(a)(k)(a)(e)(h)(r)/9/1(c)5(c)1/...",
        ...     player="red",
        ...     strategy="greedy"
        ... )
    """
    position = GamePosition.from_jfn(jfn)
    color = _parse_color(player) if isinstance(player, str) else player
    view = position.get_view(color)
    return think(view, strategy)


# 便捷函数（保持兼容）
def get_ai_move(
    position: GamePosition,
    player: str | Color,
    strategy: str = "greedy",
) -> JieqiMove | None:
    """获取 AI 走法

    Args:
        position: 游戏局面
        player: 玩家颜色
        strategy: AI 策略

    Returns:
        AI 选择的走法
    """
    color = _parse_color(player) if isinstance(player, str) else player
    view = position.get_view(color)
    return think(view, strategy)
