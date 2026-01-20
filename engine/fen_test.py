"""FEN 模块测试"""

import pytest

from engine.fen import (
    _parse_captured_counts,
    apply_move_to_fen,
    fen_to_ascii,
    fen_to_ascii_cn,
    move_to_str,
    parse_fen,
    parse_move,
    validate_fen,
)
from engine.types import ActionType, Color, PieceType, Position


class TestParseCaptured:
    """测试被吃棋子解析"""

    def test_empty_captured(self):
        """空被吃"""
        red, black, err = _parse_captured_counts("-:-")
        assert err is None
        assert red == 0
        assert black == 0

    def test_red_captured_only(self):
        """只有红方被吃"""
        red, black, err = _parse_captured_counts("RHP:-")
        assert err is None
        assert red == 3
        assert black == 0

    def test_black_captured_only(self):
        """只有黑方被吃"""
        red, black, err = _parse_captured_counts("-:rhp")
        assert err is None
        assert red == 0
        assert black == 3

    def test_both_captured(self):
        """双方都有被吃"""
        red, black, err = _parse_captured_counts("RP:rh")
        assert err is None
        assert red == 2
        assert black == 2

    def test_unknown_captured(self):
        """暗子被吃（不知道身份）"""
        red, black, err = _parse_captured_counts("??:??")
        assert err is None
        assert red == 2
        assert black == 2

    def test_mixed_captured(self):
        """混合情况"""
        red, black, err = _parse_captured_counts("RP??:raHC")
        assert err is None
        assert red == 4
        assert black == 4

    def test_missing_colon(self):
        """缺少冒号"""
        red, black, err = _parse_captured_counts("RP")
        assert err is not None
        assert "冒号" in err


class TestValidateFenPieceCount:
    """测试 FEN 验证中的棋子数量检查"""

    def test_valid_full_board(self):
        """完整棋盘（32 个棋子）"""
        # 标准开局 FEN
        fen = "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR -:- r r"
        valid, msg = validate_fen(fen)
        assert valid, msg

    def test_valid_endgame(self):
        """有效残局（棋盘 + 被吃 = 32）"""
        # 红方：K + R = 2 个在棋盘上，被吃 14 个 (RHHEECCAAPPPPP = 14)
        # 黑方：k + a = 2 个在棋盘上，被吃 14 个 (rhheeccaappppp = 14)
        # 注意：车不在将的攻击线上（移到 a 列），帅将不对面
        fen = "3ak4/9/9/9/9/9/9/9/R8/3K5 RHHEECCAAPPPPP:rhheeccaappppp r r"
        valid, msg = validate_fen(fen)
        assert valid, msg

    def test_invalid_red_pieces_missing(self):
        """红方棋子缺失"""
        # 红方只有 K 在棋盘上，被吃 0 个，总共 1 个 != 16
        # 黑方正确：k + a = 2，被吃 14
        # 帅将不在同列
        fen = "3ak4/9/9/9/9/9/9/9/9/3K5 -:rhheeccaappppp r r"
        valid, msg = validate_fen(fen)
        assert not valid
        assert "红方棋子数错误" in msg

    def test_invalid_black_pieces_missing(self):
        """黑方棋子缺失"""
        # 红方正确：K + R = 2，被吃 14
        # 黑方只有 k + a = 2 在棋盘上，被吃 0 个，总共 2 != 16
        # 帅将不在同列，车在 a 列不攻击将
        fen = "3ak4/9/9/9/9/9/9/9/R8/3K5 RHHEECCAAPPPPP:- r r"
        valid, msg = validate_fen(fen)
        assert not valid
        assert "黑方棋子数错误" in msg

    def test_valid_with_correct_captured(self):
        """正确记录被吃棋子"""
        # 红方：K + R = 2 个，被吃 14 个 (RHHEECCAAPPPPP = 14)
        # 黑方：k + a = 2 个，被吃 14 个 (rhheeccaappppp = 14)
        # 车在 a 列，不攻击将
        fen = "3ak4/9/9/9/9/9/9/9/R8/3K5 RHHEECCAAPPPPP:rhheeccaappppp r r"
        valid, msg = validate_fen(fen)
        assert valid, msg

    def test_pieces_mismatch_red(self):
        """红方棋子数不匹配（棋盘 + 被吃 != 16）"""
        # 红方：K + R = 2，被吃 RHEECCAAPPPPP = 13，总共 15 != 16
        # 黑方：正确
        fen = "3ak4/9/9/9/9/9/9/9/R8/3K5 RHEECCAAPPPPP:rhheeccaappppp r r"
        valid, msg = validate_fen(fen)
        assert not valid
        assert "红方棋子数错误" in msg

    def test_pieces_mismatch_black(self):
        """黑方棋子数不匹配（棋盘 + 被吃 != 16）"""
        # 红方：正确
        # 黑方：k + a = 2，被吃 rheeccaappppp = 13，总共 15 != 16
        fen = "3ak4/9/9/9/9/9/9/9/R8/3K5 RHHEECCAAPPPPP:rheeccaappppp r r"
        valid, msg = validate_fen(fen)
        assert not valid
        assert "黑方棋子数错误" in msg


class TestParseFen:
    """测试 FEN 解析"""

    def test_parse_standard_opening(self):
        """解析标准开局"""
        fen = "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR -:- r r"
        state = parse_fen(fen)

        assert state.turn == Color.RED
        assert state.viewer == Color.RED
        assert len(state.pieces) == 32

        # 检查红方帅的位置
        king = next(
            p for p in state.pieces if p.piece_type == PieceType.KING and p.color == Color.RED
        )
        assert king.position == Position(0, 4)
        assert not king.is_hidden

    def test_parse_hidden_pieces(self):
        """解析暗子"""
        fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"
        state = parse_fen(fen)

        assert len(state.pieces) == 32
        # 所有非帅将的棋子都是暗子
        hidden_count = sum(1 for p in state.pieces if p.is_hidden)
        assert hidden_count == 30  # 除了两个将帅

    def test_parse_captured(self):
        """解析被吃子"""
        fen = "3ak4/9/9/9/9/9/9/9/R8/3K5 RHHEECCAAPPPPP:rhheeccaappppp r r"
        state = parse_fen(fen)

        assert len(state.captured.red_captured) == 14
        assert len(state.captured.black_captured) == 14

    def test_parse_invalid_format(self):
        """无效格式"""
        with pytest.raises(ValueError):
            parse_fen("invalid")

    def test_parse_invalid_rows(self):
        """行数错误"""
        with pytest.raises(ValueError):
            parse_fen("rnbakabnr/9/1c5c1 -:- r r")  # 只有 3 行


class TestParseMove:
    """测试走法解析"""

    def test_parse_regular_move(self):
        """解析普通走法"""
        move, revealed = parse_move("a0a1")
        assert move.action_type == ActionType.MOVE
        assert move.from_pos == Position(0, 0)
        assert move.to_pos == Position(1, 0)
        assert revealed is None

    def test_parse_reveal_move(self):
        """解析揭子走法"""
        move, revealed = parse_move("+e2e3")
        assert move.action_type == ActionType.REVEAL_AND_MOVE
        assert move.from_pos == Position(2, 4)
        assert move.to_pos == Position(3, 4)
        assert revealed is None

    def test_parse_reveal_with_type(self):
        """解析带类型的揭子走法"""
        move, revealed = parse_move("+a0a1=R")
        assert move.action_type == ActionType.REVEAL_AND_MOVE
        assert revealed == PieceType.ROOK

    def test_parse_invalid_move(self):
        """无效走法"""
        with pytest.raises(ValueError):
            parse_move("abc")


class TestMoveToStr:
    """测试走法转字符串"""

    def test_regular_move(self):
        """普通走法"""
        from engine.types import JieqiMove

        move = JieqiMove(ActionType.MOVE, Position(0, 0), Position(1, 0))
        assert move_to_str(move) == "a0a1"

    def test_reveal_move(self):
        """揭子走法"""
        from engine.types import JieqiMove

        move = JieqiMove(ActionType.REVEAL_AND_MOVE, Position(2, 4), Position(3, 4))
        assert move_to_str(move) == "+e2e3"

    def test_reveal_with_type(self):
        """带类型的揭子走法"""
        from engine.types import JieqiMove

        move = JieqiMove(ActionType.REVEAL_AND_MOVE, Position(0, 0), Position(1, 0))
        assert move_to_str(move, PieceType.ROOK) == "+a0a1=R"


class TestApplyMoveToFen:
    """测试走法应用"""

    def test_simple_move(self):
        """简单走法"""
        # 红帅从 e0 走到 e1
        fen = "3ak4/9/9/9/9/9/9/9/R8/3K5 RHHEECCAAPPPPP:rhheeccaappppp r r"
        new_fen = apply_move_to_fen(fen, "d0d1")

        # 验证帅移动了
        assert new_fen.split()[2] == "b"  # 轮到黑方
        # 帅从 row 0 移动到 row 1
        board_rows = new_fen.split()[0].split("/")
        assert "K" in board_rows[8]  # row 1 (从上往下第9行)

    def test_capture_move(self):
        """吃子走法"""
        # 红车吃黑卒 (a1 -> a2)
        fen = "3ak4/9/9/9/9/9/9/p8/R8/3K5 RHHEECCAAPPPPP:rhheeccaapppp r r"
        new_fen = apply_move_to_fen(fen, "a1a2")

        # 验证吃子被记录
        captured_part = new_fen.split()[1]
        assert "p" in captured_part.split(":")[1].lower()  # 黑方被吃了一个卒


class TestFenToAscii:
    """测试 ASCII 显示"""

    def test_ascii_output(self):
        """测试 ASCII 输出"""
        fen = "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR -:- r r"
        ascii_board = fen_to_ascii(fen)

        # 验证包含行列标记
        assert "a b c d e f g h i" in ascii_board
        assert "9 " in ascii_board
        assert "0 " in ascii_board

    def test_ascii_cn_output(self):
        """测试中文 ASCII 输出"""
        fen = "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR -:- r r"
        ascii_board = fen_to_ascii_cn(fen)

        # 验证包含中文棋子
        assert "帅" in ascii_board
        assert "将" in ascii_board


class TestValidateFenMore:
    """更多 FEN 验证测试"""

    def test_hidden_piece_count_valid(self):
        """暗子数量合法"""
        # 全是暗子（只有帅将是明的）
        fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"
        valid, msg = validate_fen(fen)
        assert valid, msg

    def test_hidden_piece_count_invalid(self):
        """暗子数量超标"""
        # 红方已有 16 个明子，不应有暗子
        fen = "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/X8/RHEAKAEHR -:- r r"
        valid, msg = validate_fen(fen)
        assert not valid
        assert "暗子" in msg

    def test_facing_kings_invalid(self):
        """帅将对面非法"""
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 RHHEECCAAPPPPP:rhheeccaappppp r r"
        valid, msg = validate_fen(fen)
        assert not valid
        assert "对面" in msg

    def test_black_in_check_invalid(self):
        """黑方被将军非法"""
        # 红车直接可以吃将 (车在 e1，将在 e9)
        # 红方: K + R = 2，被吃 14
        # 黑方: k + a = 2，被吃 14
        fen = "3ak4/9/9/9/9/9/9/9/4R4/3K5 RHHEECCAAPPPPP:rhheeccaappppp r r"
        valid, msg = validate_fen(fen)
        assert not valid
        assert "将军" in msg

    def test_wrong_turn_invalid(self):
        """非红方走非法"""
        fen = "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR -:- b r"
        valid, msg = validate_fen(fen)
        assert not valid
        assert "红方走" in msg
