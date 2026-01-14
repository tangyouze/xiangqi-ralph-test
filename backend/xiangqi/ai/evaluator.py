"""
棋局评估器

提供棋局状态的评分函数，用于 AI 决策
"""

from xiangqi.board import Board
from xiangqi.types import Color, PieceType, Position


class Evaluator:
    """棋局评估器

    基于棋子价值、位置和战术的综合评估
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

    # 车的位置分数表（红方视角，row 0 = 红方底线）
    # 车在中路和对手阵地价值高
    ROOK_POSITION_TABLE = [
        [-2, 10, 6, 14, 12, 14, 6, 10, -2],  # row 0: 红方底线
        [8, 4, 8, 16, 8, 16, 8, 4, 8],
        [4, 8, 6, 14, 12, 14, 6, 8, 4],
        [6, 10, 8, 14, 14, 14, 8, 10, 6],
        [12, 16, 14, 20, 20, 20, 14, 16, 12],  # row 4: 接近河界
        [12, 14, 12, 18, 18, 18, 12, 14, 12],  # row 5: 过河
        [12, 18, 16, 22, 22, 22, 16, 18, 12],
        [12, 12, 12, 18, 18, 18, 12, 12, 12],
        [16, 20, 18, 24, 26, 24, 18, 20, 16],
        [14, 14, 12, 18, 16, 18, 12, 14, 14],  # row 9: 黑方底线（沉底车）
    ]

    # 马的位置分数表（红方视角，row 0 = 红方底线）
    HORSE_POSITION_TABLE = [
        [0, -4, 0, 0, 0, 0, 0, -4, 0],  # row 0: 红方底线（边角差）
        [0, 2, 4, 4, -2, 4, 4, 2, 0],
        [4, 2, 8, 8, 4, 8, 8, 2, 4],
        [2, 6, 8, 6, 10, 6, 8, 6, 2],
        [4, 12, 16, 14, 12, 14, 16, 12, 4],  # row 4: 接近河界
        [6, 16, 14, 18, 16, 18, 14, 16, 6],  # row 5: 过河
        [8, 24, 18, 24, 20, 24, 18, 24, 8],
        [12, 14, 16, 20, 18, 20, 16, 14, 12],
        [4, 10, 28, 16, 8, 16, 28, 10, 4],
        [4, 8, 16, 12, 4, 12, 16, 8, 4],  # row 9: 黑方底线
    ]

    # 炮的位置分数表（红方视角，row 0 = 红方底线）
    # 炮在后方有隔山打牛的价值，过河后也有威胁
    CANNON_POSITION_TABLE = [
        [0, 0, 2, 6, 6, 6, 2, 0, 0],  # row 0: 红方底线
        [0, 2, 4, 6, 6, 6, 4, 2, 0],
        [4, 0, 8, 6, 10, 6, 8, 0, 4],  # row 2: 炮初始位置
        [0, 0, 0, 2, 4, 2, 0, 0, 0],
        [-2, 0, 4, 2, 6, 2, 4, 0, -2],  # row 4: 接近河界
        [0, 0, 0, 2, 8, 2, 0, 0, 0],  # row 5: 过河
        [0, 0, -2, 4, 10, 4, -2, 0, 0],
        [2, 2, 0, -10, -8, -10, 0, 2, 2],
        [2, 2, 0, -4, -14, -4, 0, 2, 2],
        [6, 4, 0, -10, -12, -10, 0, 4, 6],  # row 9: 黑方底线（太深不好）
    ]

    # 兵/卒的位置分数表（红方视角，row 0 是红方底线，row 9 是黑方底线）
    # 兵越往前（row 越大）价值越高，过河后可以左右移动更有价值
    PAWN_POSITION_TABLE = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0],  # row 0: 红方底线，兵不可能在这
        [0, 0, 0, 0, 0, 0, 0, 0, 0],  # row 1
        [0, 0, 0, 0, 0, 0, 0, 0, 0],  # row 2
        [0, 0, -2, 0, 4, 0, -2, 0, 0],  # row 3: 兵的初始位置（未过河）
        [2, 0, 8, 0, 8, 0, 8, 0, 2],  # row 4: 接近河界
        [6, 12, 18, 18, 20, 18, 18, 12, 6],  # row 5: 刚过河，可左右移动
        [10, 20, 30, 34, 40, 34, 30, 20, 10],  # row 6: 深入敌阵
        [14, 26, 42, 60, 80, 60, 42, 26, 14],  # row 7: 威胁区域
        [18, 36, 56, 80, 120, 80, 56, 36, 18],  # row 8: 接近对方底线
        [0, 3, 6, 9, 12, 9, 6, 3, 0],  # row 9: 黑方底线（中心位置最有价值）
    ]

    # 仕的位置分数表（红方视角，row 0 = 红方底线）
    # 仕只能在九宫格内移动（红方 row 0-2, col 3-5）
    ADVISOR_POSITION_TABLE = [
        [0, 0, 0, 20, 0, 20, 0, 0, 0],  # row 0: 红方底线
        [0, 0, 0, 0, 23, 0, 0, 0, 0],  # row 1: 中心位置最佳
        [0, 0, 0, 20, 0, 20, 0, 0, 0],  # row 2
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]

    # 相/象的位置分数表（红方视角，row 0 = 红方底线）
    # 相只能在己方半场移动（红方 row 0-4）
    ELEPHANT_POSITION_TABLE = [
        [0, 0, 20, 0, 0, 0, 20, 0, 0],  # row 0: 红方底线
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [18, 0, 0, 0, 23, 0, 0, 0, 18],  # row 2: 中心位置最佳
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 20, 0, 0, 0, 20, 0, 0],  # row 4: 河界边
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]

    # 将/帅的位置分数表（红方视角，row 0 = 红方底线）
    # 帅只能在九宫格内移动（红方 row 0-2, col 3-5）
    KING_POSITION_TABLE = [
        [0, 0, 0, 1, 5, 1, 0, 0, 0],  # row 0: 红方底线（底线中心最安全）
        [0, 0, 0, -8, -9, -8, 0, 0, 0],  # row 1: 向前稍差
        [0, 0, 0, 1, -8, 1, 0, 0, 0],  # row 2
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]

    def __init__(self):
        # 将位置表转为字典形式
        self.position_tables = {
            PieceType.ROOK: self.ROOK_POSITION_TABLE,
            PieceType.HORSE: self.HORSE_POSITION_TABLE,
            PieceType.CANNON: self.CANNON_POSITION_TABLE,
            PieceType.PAWN: self.PAWN_POSITION_TABLE,
            PieceType.ADVISOR: self.ADVISOR_POSITION_TABLE,
            PieceType.ELEPHANT: self.ELEPHANT_POSITION_TABLE,
            PieceType.KING: self.KING_POSITION_TABLE,
        }

    def _get_position_bonus(self, piece_type: PieceType, row: int, col: int, color: Color) -> float:
        """获取棋子在特定位置的加分"""
        table = self.position_tables.get(piece_type)
        if table is None:
            return 0.0

        # 黑方需要翻转行坐标（因为位置表是以红方视角设计的）
        if color == Color.BLACK:
            row = 9 - row

        if 0 <= row < 10 and 0 <= col < 9:
            return table[row][col]
        return 0.0

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
            # 基础棋子价值
            piece_value = self.PIECE_VALUES[piece.piece_type]

            # 位置加成
            position_bonus = self._get_position_bonus(
                piece.piece_type,
                piece.position.row,
                piece.position.col,
                piece.color,
            )
            piece_value += position_bonus

            # 根据棋子颜色调整分数
            if piece.color == color:
                score += piece_value
            else:
                score -= piece_value

        # 机动性加成（可走步数）
        our_moves = len(board.get_legal_moves(color))
        their_moves = len(board.get_legal_moves(color.opposite))
        score += (our_moves - their_moves) * 3

        # 将军加成/惩罚
        if board.is_in_check(color):
            score -= 80
        if board.is_in_check(color.opposite):
            score += 80

        # 王的安全性：检查王前是否有防守
        score += self._evaluate_king_safety(board, color)

        return score

    def _evaluate_king_safety(self, board: Board, color: Color) -> float:
        """评估王的安全性"""
        score = 0.0

        # 找到己方的王
        king = None
        for piece in board.get_all_pieces():
            if piece.piece_type == PieceType.KING and piece.color == color:
                king = piece
                break

        if king is None:
            return -10000  # 没有王，极端不利

        # 检查王的周围有多少友方棋子
        king_col = king.position.col
        for dc in [-1, 0, 1]:
            new_col = king_col + dc
            if 3 <= new_col <= 5:
                # 检查王前方是否有棋子
                if color == Color.RED:
                    # 红方王在下方，检查上方
                    for row in range(king.position.row + 1, min(king.position.row + 3, 3)):
                        defender = board.get_piece(Position(row, new_col))
                        if defender and defender.color == color:
                            score += 10
                else:
                    # 黑方王在上方，检查下方
                    for row in range(max(king.position.row - 2, 7), king.position.row):
                        defender = board.get_piece(Position(row, new_col))
                        if defender and defender.color == color:
                            score += 10

        return score

    def evaluate_move(
        self, board: Board, from_pos: Position, to_pos: Position, color: Color
    ) -> float:
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
            capture_value += (
                self.PIECE_VALUES[target.piece_type] - self.PIECE_VALUES[attacker.piece_type]
            ) * 0.1

        return capture_value
