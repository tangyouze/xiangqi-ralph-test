"""
棋子单元测试
"""

import pytest

from xiangqi.board import Board
from xiangqi.piece import (
    Advisor,
    Cannon,
    Elephant,
    Horse,
    King,
    Pawn,
    Rook,
    create_piece,
)
from xiangqi.types import Color, PieceType, Position


class TestPieceFactory:
    """棋子工厂函数测试"""

    def test_create_all_piece_types(self):
        """测试创建所有类型的棋子"""
        pos = Position(0, 0)
        for piece_type in PieceType:
            piece = create_piece(piece_type, Color.RED, pos)
            assert piece.piece_type == piece_type
            assert piece.color == Color.RED
            assert piece.position == pos


class TestKing:
    """将/帅测试"""

    def test_king_basic_moves(self):
        """测试将/帅的基本移动"""
        board = Board()
        # 清空棋盘
        board._pieces.clear()

        # 放置红帅在中心位置
        king = King(Color.RED, Position(1, 4))
        board.set_piece(king.position, king)

        moves = king.get_potential_moves(board)
        expected_positions = [
            Position(0, 4),  # 下
            Position(2, 4),  # 上
            Position(1, 3),  # 左
            Position(1, 5),  # 右
        ]

        assert len(moves) == 4
        for pos in expected_positions:
            assert pos in moves

    def test_king_palace_restriction(self):
        """测试将/帅不能出九宫格"""
        board = Board()
        board._pieces.clear()

        # 放置红帅在九宫格边角
        king = King(Color.RED, Position(0, 3))
        board.set_piece(king.position, king)

        moves = king.get_potential_moves(board)
        # 只能向上和向右
        assert Position(1, 3) in moves
        assert Position(0, 4) in moves
        # 不能向左出九宫格
        assert Position(0, 2) not in moves


class TestAdvisor:
    """士/仕测试"""

    def test_advisor_diagonal_moves(self):
        """测试士/仕的斜线移动"""
        board = Board()
        board._pieces.clear()

        advisor = Advisor(Color.RED, Position(1, 4))
        board.set_piece(advisor.position, advisor)

        moves = advisor.get_potential_moves(board)
        expected = [
            Position(0, 3),
            Position(0, 5),
            Position(2, 3),
            Position(2, 5),
        ]
        assert len(moves) == 4
        for pos in expected:
            assert pos in moves


class TestElephant:
    """象/相测试"""

    def test_elephant_diagonal_moves(self):
        """测试象/相的田字走法"""
        board = Board()
        board._pieces.clear()

        elephant = Elephant(Color.RED, Position(2, 4))
        board.set_piece(elephant.position, elephant)

        moves = elephant.get_potential_moves(board)
        expected = [
            Position(0, 2),
            Position(0, 6),
            Position(4, 2),
            Position(4, 6),
        ]
        for pos in expected:
            assert pos in moves

    def test_elephant_blocked_by_eye(self):
        """测试象眼被堵"""
        board = Board()
        board._pieces.clear()

        elephant = Elephant(Color.RED, Position(2, 4))
        board.set_piece(elephant.position, elephant)

        # 放置一个棋子堵住象眼
        blocker = Pawn(Color.RED, Position(3, 5))
        board.set_piece(blocker.position, blocker)

        moves = elephant.get_potential_moves(board)
        # 右上方的移动应该被阻挡
        assert Position(4, 6) not in moves

    def test_elephant_cannot_cross_river(self):
        """测试象/相不能过河"""
        board = Board()
        board._pieces.clear()

        elephant = Elephant(Color.RED, Position(4, 4))
        board.set_piece(elephant.position, elephant)

        moves = elephant.get_potential_moves(board)
        # 过河的位置不应该出现
        assert Position(6, 2) not in moves
        assert Position(6, 6) not in moves


class TestHorse:
    """马测试"""

    def test_horse_l_shape_moves(self):
        """测试马的日字走法"""
        board = Board()
        board._pieces.clear()

        horse = Horse(Color.RED, Position(4, 4))
        board.set_piece(horse.position, horse)

        moves = horse.get_potential_moves(board)
        expected = [
            Position(2, 3),
            Position(2, 5),
            Position(3, 2),
            Position(3, 6),
            Position(5, 2),
            Position(5, 6),
            Position(6, 3),
            Position(6, 5),
        ]
        assert len(moves) == 8
        for pos in expected:
            assert pos in moves

    def test_horse_blocked_leg(self):
        """测试蹩马腿"""
        board = Board()
        board._pieces.clear()

        horse = Horse(Color.RED, Position(4, 4))
        board.set_piece(horse.position, horse)

        # 放置一个棋子堵住马脚（向上的马脚）
        blocker = Pawn(Color.RED, Position(3, 4))
        board.set_piece(blocker.position, blocker)

        moves = horse.get_potential_moves(board)
        # 向上跳的两个位置应该被阻挡
        assert Position(2, 3) not in moves
        assert Position(2, 5) not in moves


class TestRook:
    """车测试"""

    def test_rook_straight_moves(self):
        """测试车的直线移动"""
        board = Board()
        board._pieces.clear()

        rook = Rook(Color.RED, Position(4, 4))
        board.set_piece(rook.position, rook)

        moves = rook.get_potential_moves(board)
        # 车应该能走到所有同行同列的位置
        for col in range(9):
            if col != 4:
                assert Position(4, col) in moves
        for row in range(10):
            if row != 4:
                assert Position(row, 4) in moves

    def test_rook_blocked_by_piece(self):
        """测试车被棋子阻挡"""
        board = Board()
        board._pieces.clear()

        rook = Rook(Color.RED, Position(4, 4))
        board.set_piece(rook.position, rook)

        # 放置一个己方棋子在右边
        blocker = Pawn(Color.RED, Position(4, 6))
        board.set_piece(blocker.position, blocker)

        moves = rook.get_potential_moves(board)
        # 可以走到阻挡棋子之前的位置
        assert Position(4, 5) in moves
        # 不能走到阻挡棋子的位置（己方棋子）
        assert Position(4, 6) not in moves
        # 不能跨过阻挡棋子
        assert Position(4, 7) not in moves


class TestCannon:
    """炮测试"""

    def test_cannon_move_without_capture(self):
        """测试炮的移动（不吃子）"""
        board = Board()
        board._pieces.clear()

        cannon = Cannon(Color.RED, Position(4, 4))
        board.set_piece(cannon.position, cannon)

        moves = cannon.get_potential_moves(board)
        # 炮应该能走到所有空位
        for col in range(9):
            if col != 4:
                assert Position(4, col) in moves

    def test_cannon_capture_over_platform(self):
        """测试炮隔子吃子"""
        board = Board()
        board._pieces.clear()

        cannon = Cannon(Color.RED, Position(4, 0))
        board.set_piece(cannon.position, cannon)

        # 放置炮架
        platform = Pawn(Color.RED, Position(4, 3))
        board.set_piece(platform.position, platform)

        # 放置可吃的目标
        target = Pawn(Color.BLACK, Position(4, 6))
        board.set_piece(target.position, target)

        moves = cannon.get_potential_moves(board)
        # 可以吃到目标
        assert Position(4, 6) in moves
        # 不能直接走到炮架位置
        assert Position(4, 3) not in moves
        # 不能走过炮架（除非吃子）
        assert Position(4, 4) not in moves
        assert Position(4, 5) not in moves


class TestPawn:
    """兵/卒测试"""

    def test_pawn_forward_only_before_river(self):
        """测试兵/卒过河前只能前进"""
        board = Board()
        board._pieces.clear()

        pawn = Pawn(Color.RED, Position(3, 4))
        board.set_piece(pawn.position, pawn)

        moves = pawn.get_potential_moves(board)
        # 只能向前
        assert len(moves) == 1
        assert Position(4, 4) in moves

    def test_pawn_sideways_after_river(self):
        """测试兵/卒过河后可以左右移动"""
        board = Board()
        board._pieces.clear()

        pawn = Pawn(Color.RED, Position(5, 4))
        board.set_piece(pawn.position, pawn)

        moves = pawn.get_potential_moves(board)
        # 可以向前和左右
        assert Position(6, 4) in moves  # 前
        assert Position(5, 3) in moves  # 左
        assert Position(5, 5) in moves  # 右

    def test_black_pawn_moves(self):
        """测试黑方卒的移动方向"""
        board = Board()
        board._pieces.clear()

        pawn = Pawn(Color.BLACK, Position(4, 4))  # 过河后
        board.set_piece(pawn.position, pawn)

        moves = pawn.get_potential_moves(board)
        # 黑方卒向下移动
        assert Position(3, 4) in moves  # 前（向下）
        assert Position(4, 3) in moves  # 左
        assert Position(4, 5) in moves  # 右
