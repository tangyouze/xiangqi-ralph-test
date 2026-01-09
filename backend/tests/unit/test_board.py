"""
棋盘单元测试
"""

import pytest

from xiangqi.board import Board
from xiangqi.piece import King, Rook, create_piece
from xiangqi.types import Color, GameResult, Move, PieceType, Position


class TestBoardInitialization:
    """棋盘初始化测试"""

    def test_initial_piece_count(self):
        """测试初始棋子数量"""
        board = Board()
        # 每方 16 个棋子，共 32 个
        assert len(board.get_all_pieces()) == 32

    def test_initial_piece_positions(self):
        """测试初始棋子位置"""
        board = Board()

        # 检查红方帅的位置
        red_king = board.find_king(Color.RED)
        assert red_king == Position(0, 4)

        # 检查黑方将的位置
        black_king = board.find_king(Color.BLACK)
        assert black_king == Position(9, 4)

    def test_red_pieces_count(self):
        """测试红方棋子数量"""
        board = Board()
        red_pieces = board.get_all_pieces(Color.RED)
        assert len(red_pieces) == 16

    def test_black_pieces_count(self):
        """测试黑方棋子数量"""
        board = Board()
        black_pieces = board.get_all_pieces(Color.BLACK)
        assert len(black_pieces) == 16


class TestBoardOperations:
    """棋盘操作测试"""

    def test_get_piece(self):
        """测试获取棋子"""
        board = Board()
        piece = board.get_piece(Position(0, 4))
        assert piece is not None
        assert piece.piece_type == PieceType.KING
        assert piece.color == Color.RED

    def test_get_piece_empty(self):
        """测试获取空位置"""
        board = Board()
        piece = board.get_piece(Position(4, 4))
        assert piece is None

    def test_set_piece(self):
        """测试设置棋子"""
        board = Board()
        board._pieces.clear()

        king = King(Color.RED, Position(0, 4))
        board.set_piece(Position(0, 4), king)

        retrieved = board.get_piece(Position(0, 4))
        assert retrieved is king

    def test_remove_piece(self):
        """测试移除棋子"""
        board = Board()
        piece = board.remove_piece(Position(0, 4))
        assert piece is not None
        assert piece.piece_type == PieceType.KING
        assert board.get_piece(Position(0, 4)) is None


class TestBoardMoves:
    """棋盘走棋测试"""

    def test_make_move(self):
        """测试执行走棋"""
        board = Board()
        # 红方车走棋
        move = Move(Position(0, 0), Position(2, 0))
        captured = board.make_move(move)

        assert captured is None  # 没有吃子
        assert board.get_piece(Position(0, 0)) is None
        piece = board.get_piece(Position(2, 0))
        assert piece is not None
        assert piece.piece_type == PieceType.ROOK

    def test_make_move_capture(self):
        """测试走棋吃子"""
        board = Board()
        board._pieces.clear()

        # 放置红车和黑车
        red_rook = Rook(Color.RED, Position(0, 0))
        black_rook = Rook(Color.BLACK, Position(5, 0))
        board.set_piece(red_rook.position, red_rook)
        board.set_piece(black_rook.position, black_rook)

        # 红车吃黑车
        move = Move(Position(0, 0), Position(5, 0))
        captured = board.make_move(move)

        assert captured is black_rook
        piece = board.get_piece(Position(5, 0))
        assert piece is red_rook

    def test_undo_move(self):
        """测试撤销走棋"""
        board = Board()

        # 执行走棋
        move = Move(Position(0, 0), Position(2, 0))
        captured = board.make_move(move)

        # 撤销
        board.undo_move(move, captured)

        assert board.get_piece(Position(2, 0)) is None
        piece = board.get_piece(Position(0, 0))
        assert piece is not None
        assert piece.piece_type == PieceType.ROOK


class TestBoardValidation:
    """棋盘验证测试"""

    def test_is_in_check_false(self):
        """测试未被将军"""
        board = Board()
        assert not board.is_in_check(Color.RED)
        assert not board.is_in_check(Color.BLACK)

    def test_is_in_check_true(self):
        """测试被将军"""
        board = Board()
        board._pieces.clear()

        # 放置红帅和黑车
        red_king = King(Color.RED, Position(0, 4))
        black_rook = Rook(Color.BLACK, Position(5, 4))
        board.set_piece(red_king.position, red_king)
        board.set_piece(black_rook.position, black_rook)

        # 红方被将军
        assert board.is_in_check(Color.RED)

    def test_is_valid_move_basic(self):
        """测试走棋有效性"""
        board = Board()
        # 红车前进两步应该是有效的
        move = Move(Position(0, 0), Position(2, 0))
        assert board.is_valid_move(move, Color.RED)

    def test_is_valid_move_invalid(self):
        """测试无效走棋"""
        board = Board()
        # 帅不能走两步
        move = Move(Position(0, 4), Position(2, 4))
        assert not board.is_valid_move(move, Color.RED)

    def test_is_valid_move_would_cause_check(self):
        """测试走棋后导致被将军"""
        board = Board()
        board._pieces.clear()

        # 放置红帅、红车（保护帅）、黑车
        red_king = King(Color.RED, Position(0, 4))
        red_rook = Rook(Color.RED, Position(1, 4))  # 挡在将面前
        black_rook = Rook(Color.BLACK, Position(5, 4))

        board.set_piece(red_king.position, red_king)
        board.set_piece(red_rook.position, red_rook)
        board.set_piece(black_rook.position, black_rook)

        # 红车离开会导致帅被将军，所以不能走
        move = Move(Position(1, 4), Position(1, 0))
        assert not board.is_valid_move(move, Color.RED)


class TestBoardGameResult:
    """游戏结果测试"""

    def test_game_ongoing(self):
        """测试游戏进行中"""
        board = Board()
        result = board.get_game_result(Color.RED)
        assert result == GameResult.ONGOING

    def test_checkmate(self):
        """测试将死"""
        board = Board()
        board._pieces.clear()

        # 构造一个将死局面
        # 黑将在角落，被两个红车困住
        black_king = King(Color.BLACK, Position(9, 4))
        red_rook1 = Rook(Color.RED, Position(9, 0))
        red_rook2 = Rook(Color.RED, Position(8, 4))
        red_king = King(Color.RED, Position(0, 4))

        board.set_piece(black_king.position, black_king)
        board.set_piece(red_rook1.position, red_rook1)
        board.set_piece(red_rook2.position, red_rook2)
        board.set_piece(red_king.position, red_king)

        # 检查黑方是否被将死
        result = board.get_game_result(Color.BLACK)
        assert result == GameResult.RED_WIN


class TestBoardCopy:
    """棋盘复制测试"""

    def test_copy_board(self):
        """测试复制棋盘"""
        board = Board()
        board_copy = board.copy()

        # 修改原棋盘
        board.remove_piece(Position(0, 0))

        # 复制的棋盘应该不受影响
        assert board_copy.get_piece(Position(0, 0)) is not None


class TestBoardFEN:
    """FEN 格式测试"""

    def test_to_fen(self):
        """测试转换为 FEN 格式"""
        board = Board()
        fen = board.to_fen()

        # FEN 应该是非空字符串
        assert len(fen) > 0
        # FEN 应该有 10 行（用 / 分隔）
        assert fen.count("/") == 9
