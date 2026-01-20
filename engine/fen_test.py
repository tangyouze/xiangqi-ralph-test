"""FEN 验证测试"""

import pytest

from engine.fen import _parse_captured, validate_fen


class TestParseCaptured:
    """测试被吃棋子解析"""

    def test_empty_captured(self):
        """空被吃"""
        red, black, err = _parse_captured("-:-")
        assert err is None
        assert red == 0
        assert black == 0

    def test_red_captured_only(self):
        """只有红方被吃"""
        red, black, err = _parse_captured("RHP:-")
        assert err is None
        assert red == 3
        assert black == 0

    def test_black_captured_only(self):
        """只有黑方被吃"""
        red, black, err = _parse_captured("-:rhp")
        assert err is None
        assert red == 0
        assert black == 3

    def test_both_captured(self):
        """双方都有被吃"""
        red, black, err = _parse_captured("RP:rh")
        assert err is None
        assert red == 2
        assert black == 2

    def test_unknown_captured(self):
        """暗子被吃（不知道身份）"""
        red, black, err = _parse_captured("??:??")
        assert err is None
        assert red == 2
        assert black == 2

    def test_mixed_captured(self):
        """混合情况"""
        red, black, err = _parse_captured("RP??:raHC")
        assert err is None
        assert red == 4
        assert black == 4

    def test_missing_colon(self):
        """缺少冒号"""
        red, black, err = _parse_captured("RP")
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
