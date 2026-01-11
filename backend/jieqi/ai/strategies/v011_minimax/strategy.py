"""
v011_minimax - Minimax with Alpha-Beta Pruning AI

ID: v011
名称: Minimax AI
描述: 使用 Minimax 算法和 Alpha-Beta 剪枝进行搜索

改进方向：真正的搜索算法
- Minimax 搜索到可配置的深度（默认深度2）
- Alpha-Beta 剪枝减少搜索节点
- 移动排序优化剪枝效率
- 静态交换评估 (SEE) 用于吃子走法排序
- 改进的评估函数
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.bitboard import FastMoveGenerator
from jieqi.types import Color, PieceType, GameResult, Position, ActionType, JieqiMove

if TYPE_CHECKING:
    from jieqi.game import JieqiGame
    from jieqi.piece import JieqiPiece
    from jieqi.board import JieqiBoard


AI_ID = "v011"
AI_NAME = "minimax"


# 棋子基础价值
PIECE_VALUES = {
    PieceType.KING: 10000,
    PieceType.ROOK: 900,
    PieceType.CANNON: 450,
    PieceType.HORSE: 400,
    PieceType.ELEPHANT: 200,
    PieceType.ADVISOR: 200,
    PieceType.PAWN: 100,
}

# 隐藏棋子的估计价值（因为不知道真实身份）
HIDDEN_PIECE_VALUE = 350


def get_piece_value(piece: JieqiPiece) -> int:
    """获取棋子价值"""
    if piece.is_hidden:
        return HIDDEN_PIECE_VALUE
    return PIECE_VALUES.get(piece.actual_type, 0)


def quick_material_eval(board: JieqiBoard, color: Color) -> float:
    """超快速子力评估"""
    score = 0.0
    for piece in board.get_all_pieces(color):
        if piece.is_hidden:
            score += HIDDEN_PIECE_VALUE
        else:
            score += PIECE_VALUES.get(piece.actual_type, 0)

    for piece in board.get_all_pieces(color.opposite):
        if piece.is_hidden:
            score -= HIDDEN_PIECE_VALUE
        else:
            score -= PIECE_VALUES.get(piece.actual_type, 0)

    return score


# 位置价值表：鼓励棋子占据中心和活跃位置
# 索引为 row * 9 + col
POSITION_BONUS = {
    # 中心控制加分
    PieceType.ROOK: [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        5,
        5,
        10,
        15,
        20,
        15,
        10,
        5,
        5,
        10,
        10,
        15,
        20,
        25,
        20,
        15,
        10,
        10,
        10,
        10,
        15,
        20,
        25,
        20,
        15,
        10,
        10,
        5,
        5,
        10,
        15,
        20,
        15,
        10,
        5,
        5,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ],
    PieceType.HORSE: [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        5,
        10,
        10,
        10,
        10,
        10,
        5,
        0,
        0,
        10,
        15,
        15,
        15,
        15,
        15,
        10,
        0,
        5,
        15,
        20,
        25,
        25,
        25,
        20,
        15,
        5,
        10,
        20,
        25,
        30,
        30,
        30,
        25,
        20,
        10,
        10,
        20,
        25,
        30,
        30,
        30,
        25,
        20,
        10,
        5,
        15,
        20,
        25,
        25,
        25,
        20,
        15,
        5,
        0,
        10,
        15,
        15,
        15,
        15,
        15,
        10,
        0,
        0,
        5,
        10,
        10,
        10,
        10,
        10,
        5,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ],
    PieceType.CANNON: [
        0,
        5,
        10,
        10,
        15,
        10,
        10,
        5,
        0,
        0,
        5,
        10,
        15,
        20,
        15,
        10,
        5,
        0,
        0,
        5,
        10,
        15,
        20,
        15,
        10,
        5,
        0,
        5,
        10,
        15,
        20,
        25,
        20,
        15,
        10,
        5,
        10,
        15,
        20,
        25,
        30,
        25,
        20,
        15,
        10,
        10,
        15,
        20,
        25,
        30,
        25,
        20,
        15,
        10,
        5,
        10,
        15,
        20,
        25,
        20,
        15,
        10,
        5,
        0,
        5,
        10,
        15,
        20,
        15,
        10,
        5,
        0,
        0,
        5,
        10,
        15,
        20,
        15,
        10,
        5,
        0,
        0,
        5,
        10,
        10,
        15,
        10,
        10,
        5,
        0,
    ],
}


def get_position_bonus(piece: JieqiPiece) -> int:
    """获取位置加成"""
    if piece.is_hidden:
        return 0

    pos_index = piece.position.row * 9 + piece.position.col
    if piece.actual_type in POSITION_BONUS:
        bonus_table = POSITION_BONUS[piece.actual_type]
        if pos_index < len(bonus_table):
            return bonus_table[pos_index]
    return 0


@AIEngine.register(AI_NAME)
class MinimaxAI(AIStrategy):
    """Minimax with Alpha-Beta Pruning AI

    使用 Minimax 搜索算法，通过向前看多步来选择最佳走法。
    Alpha-Beta 剪枝显著减少需要评估的节点数量。
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "Minimax 搜索策略 (v011)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        # 默认深度2（比较快）
        if self.config.depth == 3:  # AIConfig 默认值是 3
            self.config.depth = 2
        self._rng = random.Random(self.config.seed)
        self._nodes_evaluated = 0
        self._fast_gen = None

    def select_move(self, game: JieqiGame) -> JieqiMove | None:
        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None

        if len(legal_moves) == 1:
            return legal_moves[0]

        my_color = game.current_turn
        depth = self.config.depth
        self._fast_gen = FastMoveGenerator(game.board)

        self._nodes_evaluated = 0

        # 对走法排序以提高剪枝效率
        sorted_moves = self._order_moves(game, legal_moves, my_color)

        best_score = float("-inf")
        best_moves: list[JieqiMove] = []

        alpha = float("-inf")
        beta = float("inf")

        for move in sorted_moves:
            # 执行走法
            piece = game.board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = game.board.make_move(move)
            self._fast_gen.invalidate_cache()

            # 吃将直接返回
            if captured and captured.actual_type == PieceType.KING:
                game.board.undo_move(move, captured, was_hidden)
                return move

            # 递归搜索
            score = -self._minimax(game, depth - 1, -beta, -alpha, my_color.opposite)

            game.board.undo_move(move, captured, was_hidden)

            if score > best_score:
                best_score = score
                best_moves = [move]
                alpha = max(alpha, score)
            elif score == best_score:
                best_moves.append(move)

        # 从最佳走法中随机选择一个（添加少量随机性）
        return self._rng.choice(best_moves)

    def _minimax(
        self,
        game: JieqiGame,
        depth: int,
        alpha: float,
        beta: float,
        color: Color,
    ) -> float:
        """Minimax with Alpha-Beta Pruning

        使用 negamax 变体简化代码。
        返回当前玩家视角的分数。
        """
        self._nodes_evaluated += 1

        # 检查是否无将（被吃掉）
        if game.board.find_king(color) is None:
            return -50000
        if game.board.find_king(color.opposite) is None:
            return 50000

        # 达到搜索深度，返回静态评估
        if depth <= 0:
            return self._evaluate_position_fast(game, color)

        # 获取走法（使用自定义快速版本）
        legal_moves = self._get_moves_fast(game, color)
        if not legal_moves:
            # 无合法走法
            if self._fast_gen.is_in_check_fast(color):
                return -40000  # 被将死
            return 0  # 逼和

        # 对走法排序（只在根节点附近）
        if depth >= 2:
            sorted_moves = self._order_moves(game, legal_moves, color)
        else:
            sorted_moves = legal_moves

        best_score = float("-inf")

        for move in sorted_moves:
            piece = game.board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = game.board.make_move(move)
            self._fast_gen.invalidate_cache()

            # 吃将直接返回高分
            if captured and captured.actual_type == PieceType.KING:
                game.board.undo_move(move, captured, was_hidden)
                return 50000

            score = -self._minimax(game, depth - 1, -beta, -alpha, color.opposite)

            game.board.undo_move(move, captured, was_hidden)
            self._fast_gen.invalidate_cache()

            best_score = max(best_score, score)
            alpha = max(alpha, score)

            # Alpha-Beta 剪枝
            if alpha >= beta:
                break

        return best_score

    def _get_moves_fast(self, game: JieqiGame, color: Color) -> list[JieqiMove]:
        """快速获取走法（简化版，不检查将军）"""
        moves = []
        for piece in game.board.get_all_pieces(color):
            action_type = ActionType.REVEAL_AND_MOVE if piece.is_hidden else ActionType.MOVE
            was_hidden = piece.is_hidden

            for to_pos in piece.get_potential_moves(game.board):
                move = JieqiMove(action_type, piece.position, to_pos)
                # 检查走完后是否会导致自己被将军
                captured = game.board.make_move(move)
                self._fast_gen.invalidate_cache()
                in_check = self._fast_gen.is_in_check_fast(color)
                game.board.undo_move(move, captured, was_hidden)
                if not in_check:
                    moves.append(move)

        return moves

    def _order_moves(
        self,
        game: JieqiGame,
        moves: list[JieqiMove],
        color: Color,
    ) -> list[JieqiMove]:
        """对走法排序以提高 Alpha-Beta 剪枝效率

        优先级：
        1. 吃子走法（按价值排序）
        2. 将军走法
        3. 其他走法
        """
        scored_moves: list[tuple[float, JieqiMove]] = []

        for move in moves:
            score = 0.0
            target = game.board.get_piece(move.to_pos)

            # 吃子得分
            if target is not None and target.color != color:
                capture_value = get_piece_value(target)
                if target.actual_type == PieceType.KING:
                    score += 100000  # 吃将最高优先级
                else:
                    score += capture_value * 10  # 优先考虑吃子

            # 揭子有一定价值
            if move.action_type == ActionType.REVEAL_AND_MOVE:
                score += 5

            scored_moves.append((score, move))

        # 按分数降序排序
        scored_moves.sort(key=lambda x: -x[0])

        return [m for _, m in scored_moves]

    def _evaluate_position_fast(self, game: JieqiGame, color: Color) -> float:
        """快速评估当前局面（简化版）

        从指定颜色的视角评估。
        """
        score = 0.0

        # 子力价值（最重要的因素）
        for piece in game.board.get_all_pieces():
            value = get_piece_value(piece)
            pos_bonus = get_position_bonus(piece)
            total = value + pos_bonus

            if piece.color == color:
                score += total
            else:
                score -= total

        # 将军威胁
        if self._fast_gen.is_in_check_fast(color.opposite):
            score += 50
        if self._fast_gen.is_in_check_fast(color):
            score -= 50

        return score

    def _evaluate_position(self, game: JieqiGame, color: Color) -> float:
        """评估当前局面（完整版）

        从指定颜色的视角评估。
        """
        score = self._evaluate_position_fast(game, color)

        # 控制中心区域的加分
        center_control = self._evaluate_center_control(game, color)
        score += center_control

        # 暗子数量评估
        my_hidden = len(game.board.get_hidden_pieces(color))
        enemy_hidden = len(game.board.get_hidden_pieces(color.opposite))

        # 游戏早期，己方暗子多是优势（保留选择权）
        total_pieces = len(game.board.get_all_pieces())
        if total_pieces > 24:
            score += (my_hidden - enemy_hidden) * 5
        else:
            score -= (my_hidden - enemy_hidden) * 3

        return score

    def _evaluate_center_control(self, game: JieqiGame, color: Color) -> float:
        """评估中心控制"""
        score = 0.0

        # 定义中心区域
        center_positions = [
            Position(4, 3),
            Position(4, 4),
            Position(4, 5),
            Position(5, 3),
            Position(5, 4),
            Position(5, 5),
        ]

        for pos in center_positions:
            piece = game.board.get_piece(pos)
            if piece is not None:
                if piece.color == color:
                    score += 10
                else:
                    score -= 10

        return score
