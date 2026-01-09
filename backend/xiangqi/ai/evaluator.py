"""
棋局评估器

提供棋局状态的评分函数，用于 AI 决策
"""

from xiangqi.board import Board
from xiangqi.types import Color, PieceType, Position


class Evaluator:
    """棋局评估器

    基于棋子价值和位置的简单评估
    """

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

    # 位置加成表（简化版）
    # 兵/卒过河后价值增加
    PAWN_POSITION_BONUS = {
        Color.RED: lambda row: 50 if row >= 5 else 0,
        Color.BLACK: lambda row: 50 if row <= 4 else 0,
    }

    def evaluate(self, board: Board, color: Color) -> float:
        """评估棋局

        返回正值表示有利于指定颜色，负值表示不利

        Args:
            board: 棋盘状态
            color: 评估视角的颜色

        Returns:
            评估分数
        """
        score = 0.0

        for piece in board.get_all_pieces():
            piece_value = self.PIECE_VALUES[piece.piece_type]

            # 添加位置加成
            if piece.piece_type == PieceType.PAWN:
                piece_value += self.PAWN_POSITION_BONUS[piece.color](piece.position.row)

            # 根据棋子颜色调整分数
            if piece.color == color:
                score += piece_value
            else:
                score -= piece_value

        # 机动性加成（可走步数）
        our_moves = len(board.get_legal_moves(color))
        their_moves = len(board.get_legal_moves(color.opposite))
        score += (our_moves - their_moves) * 5

        # 将军惩罚
        if board.is_in_check(color):
            score -= 100
        if board.is_in_check(color.opposite):
            score += 100

        return score

    def evaluate_move(self, board: Board, from_pos: Position, to_pos: Position, color: Color) -> float:
        """评估单步走法的价值"""
        target = board.get_piece(to_pos)
        if target is None:
            return 0.0

        # 基础吃子价值
        capture_value = self.PIECE_VALUES[target.piece_type]

        # MVV-LVA（Most Valuable Victim - Least Valuable Attacker）
        # 用低价值棋子吃高价值棋子更好
        attacker = board.get_piece(from_pos)
        if attacker:
            capture_value += (self.PIECE_VALUES[target.piece_type] - self.PIECE_VALUES[attacker.piece_type]) * 0.1

        return capture_value
