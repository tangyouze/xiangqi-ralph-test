"""
揭棋棋盘测试
"""

import pytest
from jieqi.board import JieqiBoard
from jieqi.piece import create_jieqi_piece
from jieqi.types import (
    ActionType,
    Color,
    GameResult,
    JieqiMove,
    PieceState,
    PieceType,
    Position,
)


class TestJieqiBoardInit:
    """测试棋盘初始化"""

    def test_board_has_32_pieces(self):
        """棋盘初始化有32个棋子"""
        board = JieqiBoard(seed=42)
        assert len(board.get_all_pieces()) == 32

    def test_each_side_has_16_pieces(self):
        """每方各有16个棋子"""
        board = JieqiBoard(seed=42)
        assert len(board.get_all_pieces(Color.RED)) == 16
        assert len(board.get_all_pieces(Color.BLACK)) == 16

    def test_kings_are_revealed(self):
        """将/帅是明子"""
        board = JieqiBoard(seed=42)
        red_king = board.get_piece(Position(0, 4))
        black_king = board.get_piece(Position(9, 4))
        assert red_king is not None
        assert red_king.is_revealed
        assert red_king.actual_type == PieceType.KING
        assert black_king is not None
        assert black_king.is_revealed
        assert black_king.actual_type == PieceType.KING

    def test_other_pieces_are_hidden(self):
        """除将/帅外其他棋子都是暗子"""
        board = JieqiBoard(seed=42)
        for piece in board.get_all_pieces():
            if piece.actual_type != PieceType.KING:
                assert piece.is_hidden

    def test_seed_produces_same_board(self):
        """相同种子产生相同棋盘"""
        board1 = JieqiBoard(seed=123)
        board2 = JieqiBoard(seed=123)
        for pos in board1._pieces:
            p1 = board1.get_piece(pos)
            p2 = board2.get_piece(pos)
            assert p1 is not None
            assert p2 is not None
            assert p1.actual_type == p2.actual_type
            assert p1.color == p2.color

    def test_different_seeds_produce_different_boards(self):
        """不同种子产生不同棋盘"""
        board1 = JieqiBoard(seed=1)
        board2 = JieqiBoard(seed=2)
        # 比较所有非将位置的真实身份
        differences = 0
        for pos in board1._pieces:
            p1 = board1.get_piece(pos)
            p2 = board2.get_piece(pos)
            if p1 and p2 and p1.actual_type != PieceType.KING:
                if p1.actual_type != p2.actual_type:
                    differences += 1
        # 应该有一些不同
        assert differences > 0


class TestJieqiBoardMoves:
    """测试棋盘走法"""

    @pytest.fixture
    def board(self):
        """创建测试棋盘"""
        return JieqiBoard(seed=42)

    def test_get_hidden_pieces(self, board: JieqiBoard):
        """测试获取暗子"""
        hidden = board.get_hidden_pieces(Color.RED)
        # 红方有15个暗子（除帅外）
        assert len(hidden) == 15
        for piece in hidden:
            assert piece.is_hidden
            assert piece.color == Color.RED

    def test_get_revealed_pieces(self, board: JieqiBoard):
        """测试获取明子"""
        revealed = board.get_revealed_pieces(Color.RED)
        # 红方只有帅是明子
        assert len(revealed) == 1
        assert revealed[0].actual_type == PieceType.KING

    def test_find_king(self, board: JieqiBoard):
        """测试找将/帅"""
        red_king_pos = board.find_king(Color.RED)
        black_king_pos = board.find_king(Color.BLACK)
        assert red_king_pos == Position(0, 4)
        assert black_king_pos == Position(9, 4)

    def test_reveal_piece(self, board: JieqiBoard):
        """测试揭开暗子"""
        pos = Position(3, 0)  # 兵位
        piece = board.get_piece(pos)
        assert piece is not None
        assert piece.is_hidden

        result = board.reveal_piece(pos)
        assert result is True
        assert piece.is_revealed

    def test_reveal_already_revealed(self, board: JieqiBoard):
        """测试揭开明子失败"""
        pos = Position(0, 4)  # 帅位
        result = board.reveal_piece(pos)
        assert result is False

    def test_make_reveal_move(self, board: JieqiBoard):
        """测试揭子走法"""
        # 获取兵位暗子
        from_pos = Position(3, 0)
        to_pos = Position(4, 0)
        piece = board.get_piece(from_pos)
        assert piece is not None
        assert piece.is_hidden

        move = JieqiMove.reveal_move(from_pos, to_pos)
        captured = board.make_move(move)

        # 棋子应该移动并变成明子
        assert board.get_piece(from_pos) is None
        moved_piece = board.get_piece(to_pos)
        assert moved_piece is not None
        assert moved_piece.is_revealed
        assert captured is None

    def test_make_regular_move(self, board: JieqiBoard):
        """测试明子走法"""
        # 帅是明子，可以直接走
        from_pos = Position(0, 4)
        to_pos = Position(0, 3)  # 向左走一格

        # 先清空目标位置
        board.remove_piece(to_pos)

        move = JieqiMove.regular_move(from_pos, to_pos)
        captured = board.make_move(move)

        assert board.get_piece(from_pos) is None
        king = board.get_piece(to_pos)
        assert king is not None
        assert king.actual_type == PieceType.KING

    def test_undo_reveal_move(self, board: JieqiBoard):
        """测试撤销揭子走法"""
        from_pos = Position(3, 0)
        to_pos = Position(4, 0)
        piece = board.get_piece(from_pos)
        assert piece is not None

        move = JieqiMove.reveal_move(from_pos, to_pos)
        captured = board.make_move(move)

        # 撤销
        board.undo_move(move, captured, was_hidden=True)

        # 棋子应该回到原位并恢复暗子状态
        restored = board.get_piece(from_pos)
        assert restored is not None
        assert restored.is_hidden
        assert board.get_piece(to_pos) is None


class TestJieqiBoardValidation:
    """测试走法验证"""

    @pytest.fixture
    def board(self):
        """创建测试棋盘"""
        return JieqiBoard(seed=42)

    def test_hidden_piece_must_use_reveal_move(self, board: JieqiBoard):
        """暗子必须使用揭子走法"""
        from_pos = Position(3, 0)
        to_pos = Position(4, 0)

        # 用普通走法会失败
        regular_move = JieqiMove.regular_move(from_pos, to_pos)
        assert not board.is_valid_move(regular_move, Color.RED)

        # 用揭子走法会成功
        reveal_move = JieqiMove.reveal_move(from_pos, to_pos)
        assert board.is_valid_move(reveal_move, Color.RED)

    def test_revealed_piece_must_use_regular_move(self, board: JieqiBoard):
        """明子必须使用普通走法"""
        from_pos = Position(0, 4)
        to_pos = Position(0, 3)
        # 清空目标位置
        board.remove_piece(to_pos)

        # 用揭子走法会失败
        reveal_move = JieqiMove.reveal_move(from_pos, to_pos)
        assert not board.is_valid_move(reveal_move, Color.RED)

        # 用普通走法会成功
        regular_move = JieqiMove.regular_move(from_pos, to_pos)
        assert board.is_valid_move(regular_move, Color.RED)

    def test_cannot_move_opponent_piece(self, board: JieqiBoard):
        """不能移动对方棋子"""
        # 红方回合尝试移动黑方棋子
        from_pos = Position(6, 0)  # 黑方卒位
        to_pos = Position(5, 0)
        move = JieqiMove.reveal_move(from_pos, to_pos)
        assert not board.is_valid_move(move, Color.RED)

    def test_get_legal_moves(self, board: JieqiBoard):
        """测试获取合法走法"""
        moves = board.get_legal_moves(Color.RED)
        assert len(moves) > 0
        # 所有走法都应该是合法的
        for move in moves:
            assert board.is_valid_move(move, Color.RED)


class TestJieqiBoardGameResult:
    """测试游戏结果判断"""

    def test_ongoing_game(self):
        """测试进行中的游戏"""
        board = JieqiBoard(seed=42)
        result = board.get_game_result(Color.RED)
        assert result == GameResult.ONGOING

    def test_red_wins_when_black_king_captured(self):
        """测试吃掉黑将时红方获胜"""
        board = JieqiBoard(seed=42)
        # 移除黑将
        board.remove_piece(Position(9, 4))
        result = board.get_game_result(Color.RED)
        assert result == GameResult.RED_WIN

    def test_black_wins_when_red_king_captured(self):
        """测试吃掉红帅时黑方获胜"""
        board = JieqiBoard(seed=42)
        # 移除红帅
        board.remove_piece(Position(0, 4))
        result = board.get_game_result(Color.BLACK)
        assert result == GameResult.BLACK_WIN


class TestJieqiBoardCopy:
    """测试棋盘复制"""

    def test_copy_produces_independent_board(self):
        """复制产生独立的棋盘"""
        board = JieqiBoard(seed=42)
        copy = board.copy()

        # 修改原棋盘
        board.remove_piece(Position(3, 0))

        # 复制的棋盘不受影响
        assert copy.get_piece(Position(3, 0)) is not None


class TestJieqiBoardDisplay:
    """测试棋盘显示"""

    def test_display(self):
        """测试棋盘文本显示"""
        board = JieqiBoard(seed=42)
        display = board.display()
        # 应该包含帅和将
        assert "帅" in display
        assert "将" in display
        # 应该包含暗子标记
        assert "暗" in display or "闇" in display

    def test_display_full(self):
        """测试完整棋盘显示"""
        board = JieqiBoard(seed=42)
        display = board.display_full()
        # 应该显示所有棋子（包括暗子的真实身份）
        assert "帅" in display
        assert "将" in display
