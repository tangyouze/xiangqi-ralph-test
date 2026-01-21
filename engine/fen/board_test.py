"""board.py 单元测试"""

import pytest

from engine.fen import apply_move_with_capture, parse_fen


class TestApplyMoveWithCapture:
    """apply_move_with_capture 函数测试"""

    def test_reveal_move_with_type(self):
        """测试揭子走法：指定揭子类型"""
        # 揭棋初始局面
        fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"

        # 揭子走法：角落暗子揭成兵
        move = "+a0a1=P"
        new_fen, captured = apply_move_with_capture(fen, move)

        # 验证揭出的是兵（P），不是车（R）
        board = new_fen.split()[0]
        # a1 在 FEN 中是第 9 行（从上往下数），第 1 列
        # 第 9 行是 "P8/1XXXKXXXX" 中的 "P8"
        assert "P8" in board or board.split("/")[8].startswith("P"), (
            f"Expected P at a1, got: {board}"
        )
        assert captured is None  # 没有吃子

    def test_reveal_move_different_types(self):
        """测试不同揭子类型"""
        fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"

        test_cases = [
            ("+a0a1=R", "R"),  # 揭成车
            ("+a0a1=C", "C"),  # 揭成炮
            ("+a0a1=H", "H"),  # 揭成马
        ]

        for move, expected_type in test_cases:
            new_fen, _ = apply_move_with_capture(fen, move)
            board = new_fen.split()[0]
            row_8 = board.split("/")[8]  # a1 所在行
            assert row_8.startswith(expected_type), (
                f"Move {move}: expected {expected_type}, got {row_8}"
            )

    def test_capture_info(self):
        """测试被吃子信息"""
        # 红车可以吃黑炮
        fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r"
        move = "e4e5"
        new_fen, captured = apply_move_with_capture(fen, move)

        assert captured is not None
        assert captured["type"] == "cannon"
        assert captured["color"] == "black"
        assert captured["was_hidden"] is False


class TestHiddenPool:
    """暗子池计算测试"""

    def test_initial_pool(self):
        """测试初始暗子池"""
        from engine.hidden_pool import get_hidden_pool

        fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"

        # 红方初始暗子池（将已揭，不在池中）
        pool = get_hidden_pool(fen, "red")
        assert pool == {"A": 2, "E": 2, "H": 2, "R": 2, "C": 2, "P": 5}

    def test_pool_after_reveal(self):
        """测试揭子后暗子池减少"""
        from engine.hidden_pool import get_hidden_pool

        # 红方已揭出一个车
        fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/R8/1XXXKXXXX -:- b r"

        pool = get_hidden_pool(fen, "red")
        assert pool["R"] == 1, f"Expected 1 Rook remaining, got {pool['R']}"
        assert pool["P"] == 5, f"Pawn count should be unchanged"

    def test_random_reveal_probability(self):
        """测试随机揭子的概率分布"""
        from engine.hidden_pool import random_reveal

        fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"

        # 多次揭子，统计分布
        counts = {"A": 0, "E": 0, "H": 0, "R": 0, "C": 0, "P": 0}
        n = 1000
        for _ in range(n):
            piece = random_reveal(fen, "red")
            counts[piece] += 1

        # 兵有 5 个，应该比车（2个）出现概率高
        # 15 个暗子中：A=2, E=2, H=2, R=2, C=2, P=5
        # 兵的期望概率 = 5/15 = 33.3%
        # 车的期望概率 = 2/15 = 13.3%
        pawn_ratio = counts["P"] / n
        rook_ratio = counts["R"] / n

        # 允许一定的随机误差
        assert 0.25 < pawn_ratio < 0.45, f"Pawn ratio {pawn_ratio} out of expected range"
        assert 0.08 < rook_ratio < 0.20, f"Rook ratio {rook_ratio} out of expected range"


class TestCapturedDisplay:
    """被吃子显示解析测试"""

    def test_empty_captured(self):
        """测试无被吃子"""
        from engine.fen.display import _parse_captured_for_canvas

        result = _parse_captured_for_canvas("-:-", "red")
        assert result == {"red": [], "black": []}

    def test_revealed_piece_captured(self):
        """测试明子被吃（大写字母）"""
        from engine.fen.display import _parse_captured_for_canvas

        # 红方被吃了一个车R，黑方被吃了一个炮C
        result = _parse_captured_for_canvas("R:C", "red")

        # 红方被吃的车，显示"车"，不是暗子
        assert len(result["red"]) == 1
        assert result["red"][0]["text"] == "车"
        assert result["red"][0]["isHidden"] is False

        # 黑方被吃的炮，显示"砲"，不是暗子
        assert len(result["black"]) == 1
        assert result["black"][0]["text"] == "砲"
        assert result["black"][0]["isHidden"] is False

    def test_hidden_piece_captured_viewer_is_eater(self):
        """测试暗子被吃，viewer 是吃子方（能看到身份）"""
        from engine.fen.display import _parse_captured_for_canvas

        # 黑方被吃了暗子（小写 r 表示暗子车）
        # viewer 是红方，红方吃的黑方暗子，能看到身份
        result = _parse_captured_for_canvas("-:r", "red")

        assert len(result["black"]) == 1
        assert result["black"][0]["text"] == "車"  # 黑方的车是 "車"
        assert result["black"][0]["isHidden"] is True
        assert result["black"][0]["isUnknown"] is False

    def test_hidden_piece_captured_viewer_is_loser(self):
        """测试暗子被吃，viewer 是被吃方（看不到身份）"""
        from engine.fen.display import _parse_captured_for_canvas

        # 红方被吃了暗子（? 表示暗子，红方不知道身份）
        # viewer 是红方，黑方吃的红方暗子，红方不知道是什么
        result = _parse_captured_for_canvas("?:-", "red")

        assert len(result["red"]) == 1
        assert result["red"][0]["text"] == "暗"  # 红方不知道
        assert result["red"][0]["isHidden"] is True
        assert result["red"][0]["isUnknown"] is True

    def test_mixed_captured(self):
        """测试混合被吃子（明子+暗子）"""
        from engine.fen.display import _parse_captured_for_canvas

        # 红方视角
        # 红方被吃：明车R + 暗子?（红方不知道是什么）
        # 黑方被吃：暗车r（红方吃的，红方知道）+ 明炮C
        result = _parse_captured_for_canvas("R?:rC", "red")

        # 红方被吃的
        assert len(result["red"]) == 2
        assert result["red"][0]["text"] == "车"  # 明车
        assert result["red"][0]["isHidden"] is False
        assert result["red"][1]["text"] == "暗"  # 暗子（被黑方吃，红方不知道）
        assert result["red"][1]["isUnknown"] is True

        # 黑方被吃的
        assert len(result["black"]) == 2
        assert result["black"][0]["text"] == "車"  # 暗车（红方吃的，红方知道）
        assert result["black"][0]["isHidden"] is True
        assert result["black"][0]["isUnknown"] is False
        assert result["black"][1]["text"] == "砲"  # 明炮
        assert result["black"][1]["isHidden"] is False
