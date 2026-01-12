"""
v008_lookahead - 向前看一步 AI

ID: v008
名称: Lookahead AI
描述: 在 v007 基础上增加对手回应预测

改进方向：简单搜索
- 评估我方走法后对手的最佳回应
- 考虑对手吃子的威胁
- 避免被对手反吃

注意：AI 使用 PlayerView，无法看到暗子的真实身份！
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.simulation import SimulationBoard, SimPiece
from jieqi.types import Color, GameResult, PieceType, Position

if TYPE_CHECKING:
    from jieqi.types import JieqiMove
    from jieqi.view import PlayerView


AI_ID = "v008"
AI_NAME = "lookahead"


PIECE_VALUES = {
    PieceType.KING: 10000,
    PieceType.ROOK: 900,
    PieceType.CANNON: 450,
    PieceType.HORSE: 400,
    PieceType.ELEPHANT: 200,
    PieceType.ADVISOR: 200,
    PieceType.PAWN: 100,
}

HIDDEN_PIECE_VALUE = 320


def get_piece_value(piece: SimPiece) -> int:
    """获取棋子价值"""
    if piece.is_hidden or piece.actual_type is None:
        return HIDDEN_PIECE_VALUE
    return PIECE_VALUES.get(piece.actual_type, 0)


def count_attackers(board: SimulationBoard, pos: Position, color: Color) -> int:
    """计算有多少对方棋子可以攻击这个位置"""
    count = 0
    for enemy in board.get_all_pieces(color.opposite):
        if pos in board.get_potential_moves(enemy):
            count += 1
    return count


def count_defenders(board: SimulationBoard, pos: Position, color: Color) -> int:
    """计算有多少己方棋子可以保护这个位置"""
    count = 0
    for ally in board.get_all_pieces(color):
        if ally.position != pos and pos in board.get_potential_moves(ally):
            count += 1
    return count


def count_hidden(board: SimulationBoard, color: Color) -> int:
    """统计某方隐藏棋子数量"""
    count = 0
    for piece in board.get_all_pieces(color):
        if piece.is_hidden:
            count += 1
    return count


def get_game_phase(board: SimulationBoard, my_color: Color) -> str:
    """判断游戏阶段"""
    my_hidden = count_hidden(board, my_color)
    enemy_hidden = count_hidden(board, my_color.opposite)
    total_hidden = my_hidden + enemy_hidden

    if total_hidden >= 20:
        return "early"
    elif total_hidden >= 10:
        return "mid"
    else:
        return "late"


def evaluate_board(board: SimulationBoard, my_color: Color) -> float:
    """评估整个棋盘局势"""
    score = 0.0

    # 棋子价值
    for piece in board.get_all_pieces(my_color):
        score += get_piece_value(piece)

    for piece in board.get_all_pieces(my_color.opposite):
        score -= get_piece_value(piece)

    return score


@AIEngine.register(AI_NAME)
class LookaheadAI(AIStrategy):
    """向前看一步 AI

    考虑对手的最佳回应
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "向前看一步策略 (v008)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self._rng = random.Random(self.config.seed)

    def select_move(self, view: PlayerView) -> JieqiMove | None:
        """选择最佳走法"""
        if not view.legal_moves:
            return None

        my_color = view.viewer
        best_moves: list[JieqiMove] = []
        best_score = float("-inf")

        # 创建模拟棋盘
        sim_board = SimulationBoard(view)

        for move in view.legal_moves:
            score = self._evaluate_move_with_response(sim_board, move, my_color)

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return self._rng.choice(best_moves)

    def _evaluate_move_with_response(
        self, board: SimulationBoard, move: JieqiMove, my_color: Color
    ) -> float:
        """评估走法，考虑对手最佳回应"""
        target = board.get_piece(move.to_pos)

        # 直接吃将
        if target is not None and target.color != my_color:
            if target.actual_type == PieceType.KING:
                return 100000

        piece = board.get_piece(move.from_pos)
        if piece is None:
            return 0

        was_hidden = piece.is_hidden
        captured = board.make_move(move)

        # 检查获胜
        result = board.get_game_result(my_color.opposite)
        if result == GameResult.RED_WIN and my_color == Color.RED:
            board.undo_move(move, captured, was_hidden)
            return 100000
        elif result == GameResult.BLACK_WIN and my_color == Color.BLACK:
            board.undo_move(move, captured, was_hidden)
            return 100000

        # 基础分数
        base_score = self._evaluate_move_base(board, move, my_color, was_hidden)

        # 预测对手最佳回应
        enemy_best_capture = self._find_best_enemy_capture(board, my_color.opposite)

        board.undo_move(move, captured, was_hidden)

        # 如果对手能吃掉高价值棋子，扣分
        final_score = base_score - enemy_best_capture * 0.8

        return final_score

    def _find_best_enemy_capture(self, board: SimulationBoard, enemy_color: Color) -> float:
        """找出对手能吃掉的最高价值棋子"""
        best_capture = 0.0

        # 只检查吃子走法，不模拟执行
        for enemy in board.get_all_pieces(enemy_color):
            potential_moves = board.get_potential_moves(enemy)
            for target_pos in potential_moves:
                target = board.get_piece(target_pos)
                if target and target.color != enemy_color:
                    value = get_piece_value(target)
                    if value > best_capture:
                        best_capture = value

        return best_capture

    def _evaluate_move_base(
        self,
        board: SimulationBoard,
        move: JieqiMove,
        my_color: Color,
        was_hidden: bool,
    ) -> float:
        """基础走法评估（来自 v007）"""
        score = 0.0

        # 将军加分
        if board.is_in_check(my_color.opposite):
            score += 60

        # 防守评估
        moved_piece = board.get_piece(move.to_pos)
        if moved_piece:
            my_piece_value = get_piece_value(moved_piece)
            attackers = count_attackers(board, move.to_pos, my_color)
            defenders = count_defenders(board, move.to_pos, my_color)

            if attackers > 0:
                if defenders >= attackers:
                    score -= my_piece_value * 0.2
                else:
                    score -= my_piece_value * 0.75

            if not moved_piece.is_hidden and moved_piece.actual_type == PieceType.ROOK:
                if attackers > 0:
                    score -= 150

        # 揭子策略
        if was_hidden:
            game_phase = get_game_phase(board, my_color)
            attackers = count_attackers(board, move.to_pos, my_color)
            defenders = count_defenders(board, move.to_pos, my_color)

            if attackers == 0:
                base_reveal_bonus = 25
            elif defenders >= attackers:
                base_reveal_bonus = 10
            else:
                base_reveal_bonus = -40

            if game_phase == "early":
                phase_multiplier = 0.7
            elif game_phase == "mid":
                phase_multiplier = 1.0
            else:
                phase_multiplier = 1.5

            score += base_reveal_bonus * phase_multiplier

        return score
