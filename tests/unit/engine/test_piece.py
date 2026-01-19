"""
揭棋棋子测试
"""

import pytest

from engine.board import JieqiBoard
from engine.piece import create_jieqi_piece
from engine.types import Color, PieceType, Position


class TestJieqiPiece:
    """测试 JieqiPiece 类"""

    def test_create_hidden_piece(self):
        """测试创建暗子"""
        piece = create_jieqi_piece(Color.RED, PieceType.ROOK, Position(0, 0), revealed=False)
        assert piece.color == Color.RED
        assert piece.actual_type == PieceType.ROOK
        assert piece.position == Position(0, 0)
        assert piece.is_hidden
        assert not piece.is_revealed

    def test_create_revealed_piece(self):
        """测试创建明子"""
        piece = create_jieqi_piece(Color.RED, PieceType.KING, Position(0, 4), revealed=True)
        assert piece.is_revealed
        assert not piece.is_hidden

    def test_reveal_piece(self):
        """测试揭开暗子"""
        piece = create_jieqi_piece(Color.RED, PieceType.HORSE, Position(0, 1), revealed=False)
        assert piece.is_hidden
        piece.reveal()
        assert piece.is_revealed

    def test_get_movement_type_hidden(self):
        """测试暗子走法类型（按位置）"""
        # 在车位的暗子按车走法
        piece = create_jieqi_piece(Color.RED, PieceType.PAWN, Position(0, 0), revealed=False)
        assert piece.get_movement_type() == PieceType.ROOK

        # 在马位的暗子按马走法
        piece = create_jieqi_piece(Color.RED, PieceType.CANNON, Position(0, 1), revealed=False)
        assert piece.get_movement_type() == PieceType.HORSE

    def test_get_movement_type_revealed(self):
        """测试明子走法类型（按真实身份）"""
        # 明子按真实身份走
        piece = create_jieqi_piece(Color.RED, PieceType.PAWN, Position(0, 0), revealed=True)
        assert piece.get_movement_type() == PieceType.PAWN

    def test_copy(self):
        """测试棋子复制"""
        piece = create_jieqi_piece(Color.RED, PieceType.HORSE, Position(0, 1), revealed=False)
        copy = piece.copy()
        assert copy.color == piece.color
        assert copy.actual_type == piece.actual_type
        assert copy.position == piece.position
        assert copy.state == piece.state
        # 确保是独立副本
        copy.reveal()
        assert piece.is_hidden

    def test_to_dict_hidden(self):
        """测试暗子序列化"""
        piece = create_jieqi_piece(Color.RED, PieceType.HORSE, Position(0, 1), revealed=False)
        data = piece.to_dict()
        assert data["color"] == "red"
        assert data["state"] == "hidden"
        assert "type" not in data  # 暗子不暴露类型

    def test_to_dict_revealed(self):
        """测试明子序列化"""
        piece = create_jieqi_piece(Color.RED, PieceType.KING, Position(0, 4), revealed=True)
        data = piece.to_dict()
        assert data["color"] == "red"
        assert data["state"] == "revealed"
        assert data["type"] == "king"


class TestPieceMoves:
    """测试棋子走法"""

    @pytest.fixture
    def board(self):
        """创建一个固定种子的棋盘"""
        return JieqiBoard(seed=42)

    def test_king_moves_in_palace(self, board: JieqiBoard):
        """测试将/帅在九宫格内移动"""
        king = board.get_piece(Position(0, 4))
        assert king is not None
        assert king.actual_type == PieceType.KING
        moves = king.get_potential_moves(board)
        # 帅在初始位置可以走的方向取决于周围是否有暗子阻挡
        assert len(moves) > 0
        # 所有走法必须在九宫格内
        for pos in moves:
            assert pos.is_in_palace(Color.RED)

    def test_hidden_rook_position_moves_as_rook(self, board: JieqiBoard):
        """测试车位暗子按车走法"""
        # 获取车位的暗子
        piece = board.get_piece(Position(0, 0))
        assert piece is not None
        assert piece.is_hidden
        # 车位暗子按车走法
        assert piece.get_movement_type() == PieceType.ROOK

    def test_hidden_pawn_position_moves_as_pawn(self, board: JieqiBoard):
        """测试兵位暗子按兵走法"""
        # 获取兵位的暗子
        piece = board.get_piece(Position(3, 0))
        assert piece is not None
        assert piece.is_hidden
        # 兵位暗子按兵走法
        assert piece.get_movement_type() == PieceType.PAWN
        moves = piece.get_potential_moves(board)
        # 兵只能向前走一步
        assert Position(4, 0) in moves

    def test_revealed_advisor_can_cross_river(self, board: JieqiBoard):
        """测试明子士可以过河"""
        # 创建一个在过河位置的明子士
        advisor = create_jieqi_piece(Color.RED, PieceType.ADVISOR, Position(5, 4), revealed=True)
        # 清空棋盘并放置
        empty_board = JieqiBoard.__new__(JieqiBoard)
        empty_board._pieces = {}
        empty_board._seed = None
        empty_board.set_piece(Position(5, 4), advisor)

        moves = advisor.get_potential_moves(empty_board)
        # 明子士可以斜走，不限制九宫格
        assert len(moves) == 4  # 四个斜角方向
        assert Position(4, 3) in moves
        assert Position(4, 5) in moves
        assert Position(6, 3) in moves
        assert Position(6, 5) in moves

    def test_revealed_elephant_can_cross_river(self, board: JieqiBoard):
        """测试明子象可以过河"""
        # 创建一个在过河位置的明子象
        elephant = create_jieqi_piece(Color.RED, PieceType.ELEPHANT, Position(5, 4), revealed=True)
        # 清空棋盘并放置
        empty_board = JieqiBoard.__new__(JieqiBoard)
        empty_board._pieces = {}
        empty_board._seed = None
        empty_board.set_piece(Position(5, 4), elephant)

        moves = elephant.get_potential_moves(empty_board)
        # 明子象可以过河，走田字
        assert Position(3, 2) in moves
        assert Position(3, 6) in moves
        assert Position(7, 2) in moves
        assert Position(7, 6) in moves

    def test_hidden_elephant_stays_on_own_side(self, board: JieqiBoard):
        """测试暗子象位的走法限制在己方半场"""
        # 获取象位的暗子
        piece = board.get_piece(Position(0, 2))
        assert piece is not None
        assert piece.is_hidden
        assert piece.get_movement_type() == PieceType.ELEPHANT

        # 暗子只能在初始位置，走一步后就变成明子
        # 所以测试暗子象在初始位置的走法
        moves = piece.get_potential_moves(board)
        # 暗子象的目标位置必须在己方半场
        for pos in moves:
            assert pos.is_on_own_side(Color.RED)
