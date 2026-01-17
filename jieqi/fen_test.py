"""
FEN 格式测试

测试场景：
1. 初始局面的 FEN 生成
2. 中局的 FEN 生成（有明子、有暗子）
3. 被吃子信息的正确性（信息不对称）
4. 走法字符串的格式化和解析
5. FEN 解析后重新生成，验证往返一致性
"""

import pytest

from jieqi.fen import (
    CapturedInfo,
    CapturedPieceInfo,
    FenPiece,
    fen_from_pieces,
    move_to_str,
    parse_fen,
    parse_move,
    to_fen,
)
from jieqi.types import Color, GameResult, JieqiMove, PieceType, Position
from jieqi.view import CapturedPiece, PlayerView, ViewPiece


class TestBoardFen:
    """测试棋盘部分的 FEN 生成和解析"""

    def test_initial_position_red_view(self):
        """初始局面，红方视角 - 所有子都是暗子"""
        # 构建初始局面的 FEN
        pieces = []

        # 黑方 row 9（从 FEN 角度是第一行）
        for col in range(9):
            pieces.append(FenPiece(Position(9, col), Color.BLACK, is_hidden=True, piece_type=None))
        # row 7 炮
        pieces.append(FenPiece(Position(7, 1), Color.BLACK, is_hidden=True, piece_type=None))
        pieces.append(FenPiece(Position(7, 7), Color.BLACK, is_hidden=True, piece_type=None))
        # row 6 卒
        for col in [0, 2, 4, 6, 8]:
            pieces.append(FenPiece(Position(6, col), Color.BLACK, is_hidden=True, piece_type=None))

        # 红方 row 3 兵
        for col in [0, 2, 4, 6, 8]:
            pieces.append(FenPiece(Position(3, col), Color.RED, is_hidden=True, piece_type=None))
        # row 2 炮
        pieces.append(FenPiece(Position(2, 1), Color.RED, is_hidden=True, piece_type=None))
        pieces.append(FenPiece(Position(2, 7), Color.RED, is_hidden=True, piece_type=None))
        # row 0
        for col in range(9):
            pieces.append(FenPiece(Position(0, col), Color.RED, is_hidden=True, piece_type=None))

        fen = fen_from_pieces(pieces, turn=Color.RED, viewer=Color.RED)

        # 验证格式
        parts = fen.split()
        assert len(parts) == 4
        board, captured, turn, viewer = parts

        # 棋盘部分
        assert board == "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX"  # 测试全暗子场景（非真实开局）
        assert captured == "-:-"
        assert turn == "r"
        assert viewer == "r"

    def test_mixed_pieces(self):
        """混合局面：部分明子、部分暗子"""
        pieces = [
            # 红方将（明子）
            FenPiece(Position(0, 4), Color.RED, is_hidden=False, piece_type=PieceType.KING),
            # 红方车（暗子）
            FenPiece(Position(0, 0), Color.RED, is_hidden=True, piece_type=None),
            # 黑方将（明子）
            FenPiece(Position(9, 4), Color.BLACK, is_hidden=False, piece_type=PieceType.KING),
            # 黑方炮（明子）
            FenPiece(Position(7, 1), Color.BLACK, is_hidden=False, piece_type=PieceType.CANNON),
        ]

        fen = fen_from_pieces(pieces, turn=Color.RED, viewer=Color.RED)
        parts = fen.split()
        board = parts[0]

        # 验证每行
        rows = board.split("/")
        assert rows[0] == "4k4"  # row 9
        assert rows[2] == "1c7"  # row 7
        assert rows[9] == "X3K4"  # row 0

    def test_parse_and_regenerate(self):
        """解析后重新生成，验证往返一致性"""
        original = "4k4/9/1c7/9/9/9/9/9/9/X3K4 -:- r r"

        state = parse_fen(original)
        # 重新生成
        regenerated = fen_from_pieces(state.pieces, state.captured, state.turn, state.viewer)

        assert regenerated == original


class TestCapturedFen:
    """测试被吃子信息的 FEN 处理

    格式说明：
    - 大写 = 明子被吃
    - 小写 = 暗子被吃（我知道身份）
    - ? = 暗子被吃（我不知道身份）
    """

    def test_red_view_captured(self):
        """红方视角看被吃子

        场景：
        - 红方车被黑方吃了（明子）→ 红方知道，显示 R
        - 红方马被黑方吃了（暗子）→ 红方不知道，显示 ?
        - 黑方炮被红方吃了（暗子）→ 红方知道，显示 c（小写）
        - 黑方马被红方吃了（明子）→ 红方知道，显示 H（大写）
        """
        captured = CapturedInfo(
            red_captured=[
                CapturedPieceInfo(piece_type=PieceType.ROOK, was_hidden=False),  # 明子车
                CapturedPieceInfo(piece_type=None, was_hidden=True),  # 暗子（不知道）
            ],
            black_captured=[
                CapturedPieceInfo(piece_type=PieceType.CANNON, was_hidden=True),  # 暗子炮
                CapturedPieceInfo(piece_type=PieceType.HORSE, was_hidden=False),  # 明子马
            ],
        )

        fen = fen_from_pieces(
            pieces=[
                FenPiece(Position(0, 4), Color.RED, False, PieceType.KING),
                FenPiece(Position(9, 4), Color.BLACK, False, PieceType.KING),
            ],
            captured=captured,
            turn=Color.RED,
            viewer=Color.RED,
        )

        parts = fen.split()
        captured_str = parts[1]

        # R? = 红方被吃了明子车 + 暗子（不知道）
        # cH = 黑方被吃了暗子炮（小写）+ 明子马（大写）
        assert captured_str == "R?:cH"

    def test_black_view_same_game(self):
        """黑方视角看同一局游戏的被吃子

        同样的游戏，从黑方视角看：
        - 红方车被黑方吃了（明子）→ 黑方知道，显示 R
        - 红方马被黑方吃了（暗子）→ 黑方知道（自己吃的），显示 h（小写）
        - 黑方炮被红方吃了（暗子）→ 黑方不知道，显示 ?
        - 黑方马被红方吃了（明子）→ 黑方知道，显示 H（大写）
        """
        captured = CapturedInfo(
            red_captured=[
                CapturedPieceInfo(piece_type=PieceType.ROOK, was_hidden=False),  # 明子车
                CapturedPieceInfo(
                    piece_type=PieceType.HORSE, was_hidden=True
                ),  # 暗子马（黑方吃的）
            ],
            black_captured=[
                CapturedPieceInfo(piece_type=None, was_hidden=True),  # 暗子（不知道）
                CapturedPieceInfo(piece_type=PieceType.HORSE, was_hidden=False),  # 明子马
            ],
        )

        fen = fen_from_pieces(
            pieces=[
                FenPiece(Position(0, 4), Color.RED, False, PieceType.KING),
                FenPiece(Position(9, 4), Color.BLACK, False, PieceType.KING),
            ],
            captured=captured,
            turn=Color.RED,
            viewer=Color.BLACK,
        )

        parts = fen.split()
        captured_str = parts[1]
        viewer_str = parts[3]

        # Rh = 红方被吃了明子车 + 暗子马（黑方吃的，知道）
        # ?H = 黑方被吃了暗子（不知道）+ 明子马
        assert captured_str == "Rh:?H"
        assert viewer_str == "b"

    def test_empty_captured(self):
        """没有被吃子"""
        fen = fen_from_pieces(
            pieces=[
                FenPiece(Position(0, 4), Color.RED, False, PieceType.KING),
            ],
            captured=None,
            turn=Color.RED,
            viewer=Color.RED,
        )

        parts = fen.split()
        assert parts[1] == "-:-"

    def test_parse_captured(self):
        """解析被吃子字符串"""
        fen = "4K4/9/9/9/9/9/9/9/9/4k4 Rh?:cP? r r"
        state = parse_fen(fen)

        # 红方被吃：R(明子车) h(暗子马) ?(未知)
        assert len(state.captured.red_captured) == 3
        assert state.captured.red_captured[0].piece_type == PieceType.ROOK
        assert state.captured.red_captured[0].was_hidden is False
        assert state.captured.red_captured[1].piece_type == PieceType.HORSE
        assert state.captured.red_captured[1].was_hidden is True
        assert state.captured.red_captured[2].piece_type is None
        assert state.captured.red_captured[2].was_hidden is True

        # 黑方被吃：c(暗子炮) P(明子兵) ?(未知)
        assert len(state.captured.black_captured) == 3
        assert state.captured.black_captured[0].piece_type == PieceType.CANNON
        assert state.captured.black_captured[0].was_hidden is True
        assert state.captured.black_captured[1].piece_type == PieceType.PAWN
        assert state.captured.black_captured[1].was_hidden is False
        assert state.captured.black_captured[2].piece_type is None


class TestMoveFen:
    """测试走法字符串"""

    def test_regular_move(self):
        """明子走法"""
        move = JieqiMove.regular_move(Position(0, 0), Position(1, 0))
        s = move_to_str(move)
        assert s == "a0a1"

        # 解析
        parsed, revealed = parse_move(s)
        assert parsed == move
        assert revealed is None

    def test_reveal_move_without_result(self):
        """揭子走法（AI 选择时，不知道结果）"""
        move = JieqiMove.reveal_move(Position(0, 0), Position(1, 0))
        s = move_to_str(move)
        assert s == "+a0a1"

        # 解析
        parsed, revealed = parse_move(s)
        assert parsed == move
        assert revealed is None

    def test_reveal_move_with_result(self):
        """揭子走法（执行后，带揭示结果）"""
        move = JieqiMove.reveal_move(Position(0, 0), Position(1, 0))
        s = move_to_str(move, revealed_type=PieceType.ROOK)
        assert s == "+a0a1=R"

        # 解析
        parsed, revealed = parse_move(s)
        assert parsed == move
        assert revealed == PieceType.ROOK

    def test_various_positions(self):
        """各种位置的走法"""
        test_cases = [
            (Position(0, 0), Position(9, 8), "a0i9"),  # 角到角
            (Position(5, 4), Position(4, 4), "e5e4"),  # 中间位置
            (Position(2, 1), Position(2, 7), "b2h2"),  # 同一行
        ]

        for from_pos, to_pos, expected in test_cases:
            move = JieqiMove.regular_move(from_pos, to_pos)
            assert move_to_str(move) == expected

            parsed, _ = parse_move(expected)
            assert parsed.from_pos == from_pos
            assert parsed.to_pos == to_pos


class TestInformationAsymmetry:
    """测试信息不对称性

    核心场景：同一局游戏，红黑双方看到的 FEN 中被吃子部分不同
    """

    def test_same_game_different_views(self):
        """同一局游戏，红黑双方看到的 FEN 不同"""
        # 场景：
        # - 红方暗子车被黑方吃了（暗子）
        # - 黑方暗子马被红方吃了（暗子）

        # 棋盘相同
        pieces = [
            FenPiece(Position(0, 4), Color.RED, False, PieceType.KING),  # 红将明
            FenPiece(Position(9, 4), Color.BLACK, False, PieceType.KING),  # 黑将明
            FenPiece(Position(0, 0), Color.RED, True, None),  # 红暗子
            FenPiece(Position(9, 0), Color.BLACK, True, None),  # 黑暗子
        ]

        # 从红方视角的被吃子信息
        red_view_captured = CapturedInfo(
            red_captured=[
                CapturedPieceInfo(piece_type=None, was_hidden=True),  # 我的暗子被吃，不知道
            ],
            black_captured=[
                CapturedPieceInfo(piece_type=PieceType.HORSE, was_hidden=True),  # 我吃的暗子，知道
            ],
        )

        red_fen = fen_from_pieces(pieces, red_view_captured, Color.RED, Color.RED)

        # 从黑方视角的被吃子信息
        black_view_captured = CapturedInfo(
            red_captured=[
                CapturedPieceInfo(piece_type=PieceType.ROOK, was_hidden=True),  # 我吃的暗子，知道
            ],
            black_captured=[
                CapturedPieceInfo(piece_type=None, was_hidden=True),  # 我的暗子被吃，不知道
            ],
        )

        black_fen = fen_from_pieces(pieces, black_view_captured, Color.RED, Color.BLACK)

        # 解析并比较
        parse_fen(red_fen)
        parse_fen(black_fen)

        # 棋盘部分应该相同
        red_board = red_fen.split()[0]
        black_board = black_fen.split()[0]
        assert red_board == black_board

        # 被吃子部分不同
        red_captured_str = red_fen.split()[1]
        black_captured_str = black_fen.split()[1]

        # 红方视角：?:h（红方被吃未知，黑方被吃暗子马）
        assert red_captured_str == "?:h"
        # 黑方视角：r:?（红方被吃暗子车，黑方被吃未知）
        assert black_captured_str == "r:?"


class TestFromPlayerView:
    """测试从 PlayerView 生成 FEN"""

    def test_to_fen_basic(self):
        """基本的 PlayerView 转 FEN"""
        view = PlayerView(
            viewer=Color.RED,
            current_turn=Color.RED,
            result=GameResult.ONGOING,
            move_count=10,
            is_in_check=False,
            pieces=[
                ViewPiece(
                    color=Color.RED,
                    position=Position(0, 4),
                    is_hidden=False,
                    actual_type=PieceType.KING,
                    movement_type=PieceType.KING,
                ),
                ViewPiece(
                    color=Color.BLACK,
                    position=Position(9, 4),
                    is_hidden=False,
                    actual_type=PieceType.KING,
                    movement_type=PieceType.KING,
                ),
                ViewPiece(
                    color=Color.RED,
                    position=Position(0, 0),
                    is_hidden=True,
                    actual_type=None,  # 暗子看不到身份
                    movement_type=PieceType.ROOK,
                ),
            ],
            legal_moves=[],
            captured_pieces=[],
        )

        fen = to_fen(view)
        parts = fen.split()

        assert parts[0] == "4k4/9/9/9/9/9/9/9/9/X3K4"  # 棋盘
        assert parts[1] == "-:-"  # 无被吃子
        assert parts[2] == "r"  # 红方走
        assert parts[3] == "r"  # 红方视角

    def test_to_fen_with_captured(self):
        """带被吃子的 PlayerView 转 FEN"""
        view = PlayerView(
            viewer=Color.RED,
            current_turn=Color.BLACK,
            result=GameResult.ONGOING,
            move_count=20,
            is_in_check=False,
            pieces=[
                ViewPiece(
                    color=Color.RED,
                    position=Position(0, 4),
                    is_hidden=False,
                    actual_type=PieceType.KING,
                ),
                ViewPiece(
                    color=Color.BLACK,
                    position=Position(9, 4),
                    is_hidden=False,
                    actual_type=PieceType.KING,
                ),
            ],
            legal_moves=[],
            captured_pieces=[
                # 红方车被黑方吃了（明子）
                CapturedPiece(
                    color=Color.RED,
                    was_hidden=False,
                    actual_type=PieceType.ROOK,
                    captured_by=Color.BLACK,
                    move_number=5,
                ),
                # 红方暗子被黑方吃了
                CapturedPiece(
                    color=Color.RED,
                    was_hidden=True,
                    actual_type=PieceType.HORSE,  # 实际是马，但红方不知道
                    captured_by=Color.BLACK,
                    move_number=10,
                ),
                # 黑方炮被红方吃了（暗子）
                CapturedPiece(
                    color=Color.BLACK,
                    was_hidden=True,
                    actual_type=PieceType.CANNON,  # 红方吃的，红方知道
                    captured_by=Color.RED,
                    move_number=8,
                ),
            ],
        )

        fen = to_fen(view)
        parts = fen.split()

        # 红方被吃：R（明子车）+ ?（暗子不知道）
        # 黑方被吃：c（暗子炮，小写）
        assert parts[1] == "R?:c"
        assert parts[2] == "b"  # 黑方走
        assert parts[3] == "r"  # 红方视角


class TestEdgeCases:
    """边界情况测试"""

    def test_full_row(self):
        """满行（无空格）"""
        pieces = [FenPiece(Position(0, col), Color.RED, True, None) for col in range(9)]
        fen = fen_from_pieces(pieces, turn=Color.RED, viewer=Color.RED)
        board = fen.split()[0]
        assert board.split("/")[9] == "XXXXXXXXX"

    def test_empty_row(self):
        """空行"""
        pieces = [
            FenPiece(Position(0, 4), Color.RED, False, PieceType.KING),
        ]
        fen = fen_from_pieces(pieces, turn=Color.RED, viewer=Color.RED)
        board = fen.split()[0]
        # 大部分行应该是 9（空）
        rows = board.split("/")
        assert rows[0] == "9"  # row 9 空

    def test_invalid_fen_format(self):
        """无效 FEN 格式"""
        with pytest.raises(ValueError):
            parse_fen("invalid")

        with pytest.raises(ValueError):
            parse_fen("4k4/9/9/9/9/9/9/9/9/4K4")  # 缺少部分

        with pytest.raises(ValueError):
            parse_fen("4k4/9/9/9/9/9/9/9/4K4 -:- r r")  # 行数不对

    def test_invalid_move_format(self):
        """无效走法格式"""
        with pytest.raises(ValueError):
            parse_move("invalid")

        with pytest.raises(ValueError):
            parse_move("a0")  # 太短

        with pytest.raises(ValueError):
            parse_move("+a0a1=Z")  # 无效棋子类型


class TestRoundTrip:
    """测试往返一致性（解析后重新生成）"""

    def test_simple_board(self):
        """简单棋盘往返"""
        original = "4k4/9/9/9/9/9/9/9/9/4K4 -:- r r"
        state = parse_fen(original)
        regenerated = fen_from_pieces(state.pieces, state.captured, state.turn, state.viewer)
        assert regenerated == original

    def test_complex_captured(self):
        """复杂被吃子往返"""
        original = "4k4/9/9/9/9/9/9/9/9/4K4 Rh?:cP? b b"
        state = parse_fen(original)
        regenerated = fen_from_pieces(state.pieces, state.captured, state.turn, state.viewer)
        assert regenerated == original

    def test_full_board(self):
        """完整棋盘往返（测试全暗子场景）"""
        original = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"
        state = parse_fen(original)
        regenerated = fen_from_pieces(state.pieces, state.captured, state.turn, state.viewer)
        assert regenerated == original


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
