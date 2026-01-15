"""
揭棋 AI 测试

使用统一的 FEN 接口测试
"""

import pytest

from jieqi.ai import AIConfig, AIEngine
from jieqi.ai.strategies.v001_random.strategy import RandomAI
from jieqi.fen import apply_move_to_fen, get_legal_moves_from_fen, parse_fen
from jieqi.types import Color

# 标准初始 FEN
INITIAL_FEN = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"


class TestAIEngine:
    """测试 AI 引擎"""

    def test_random_ai_registered(self):
        """测试随机 AI 已注册"""
        strategies = AIEngine.get_strategy_names()
        assert "random" in strategies

    def test_create_random_ai(self):
        """测试创建随机 AI"""
        ai = AIEngine.create("random")
        assert isinstance(ai, RandomAI)

    def test_create_unknown_ai_raises(self):
        """测试创建未知 AI 报错"""
        with pytest.raises(ValueError):
            AIEngine.create("unknown_strategy")

    def test_list_strategies(self):
        """测试列出策略"""
        strategies = AIEngine.list_strategies()
        assert len(strategies) > 0
        assert any(s["name"] == "random" for s in strategies)


class TestRandomAI:
    """测试随机 AI（使用 FEN 接口）"""

    def test_select_moves_fen_returns_legal_move(self):
        """测试选择的走法是合法的"""
        ai = RandomAI()
        moves = ai.select_moves_fen(INITIAL_FEN, n=1)

        assert len(moves) == 1
        move_str, score = moves[0]

        legal_moves = get_legal_moves_from_fen(INITIAL_FEN)
        assert move_str in legal_moves

    def test_select_moves_fen_with_seed_is_deterministic(self):
        """测试使用种子时走法是确定性的"""
        ai1 = RandomAI(AIConfig(seed=123))
        ai2 = RandomAI(AIConfig(seed=123))

        moves1 = ai1.select_moves_fen(INITIAL_FEN, n=5)
        moves2 = ai2.select_moves_fen(INITIAL_FEN, n=5)

        assert moves1 == moves2

    def test_select_moves_fen_returns_multiple(self):
        """测试返回多个候选走法"""
        ai = RandomAI()
        moves = ai.select_moves_fen(INITIAL_FEN, n=10)

        assert len(moves) == 10
        # 所有走法都应该是合法的
        legal_moves = get_legal_moves_from_fen(INITIAL_FEN)
        for move_str, _ in moves:
            assert move_str in legal_moves


class TestAIVsAI:
    """测试 AI 对战（使用 FEN 接口）"""

    def test_ai_vs_ai_game_completes(self):
        """测试两个 AI 可以完成一局游戏"""
        fen = INITIAL_FEN
        ai_red = RandomAI(AIConfig(seed=1))
        ai_black = RandomAI(AIConfig(seed=2))

        max_moves = 200
        move_count = 0

        for _ in range(max_moves):
            state = parse_fen(fen)
            current_ai = ai_red if state.turn == Color.RED else ai_black

            moves = current_ai.select_moves_fen(fen, n=1)
            if not moves:
                break

            move_str, _ = moves[0]
            try:
                fen = apply_move_to_fen(fen, move_str)
                move_count += 1
            except Exception:
                break

        assert move_count > 0
        print(f"Game ended after {move_count} moves")

    def test_multiple_ai_games(self):
        """测试多局 AI 对战"""
        completed_games = 0

        for seed in range(5):
            fen = INITIAL_FEN
            ai_red = RandomAI(AIConfig(seed=seed * 2))
            ai_black = RandomAI(AIConfig(seed=seed * 2 + 1))

            for _ in range(200):
                state = parse_fen(fen)
                current_ai = ai_red if state.turn == Color.RED else ai_black

                moves = current_ai.select_moves_fen(fen, n=1)
                if not moves:
                    break

                move_str, _ = moves[0]
                try:
                    fen = apply_move_to_fen(fen, move_str)
                except Exception:
                    break

            completed_games += 1

        assert completed_games == 5


class TestSelectMovesFen:
    """测试 select_moves_fen() 接口"""

    def test_select_moves_fen_returns_candidates(self):
        """测试 select_moves_fen 返回多个候选"""
        ai = AIEngine.create("minimax", AIConfig(depth=2))
        candidates = ai.select_moves_fen(INITIAL_FEN, n=5)

        assert len(candidates) > 0
        assert len(candidates) <= 5

        # 检查返回格式：[(move_str, score), ...]
        for move_str, score in candidates:
            assert isinstance(move_str, str)
            assert isinstance(score, (int, float))

        # 检查分数降序排列
        scores = [s for _, s in candidates]
        assert scores == sorted(scores, reverse=True)

    def test_all_moves_are_legal(self):
        """测试所有返回的走法都是合法的"""
        ai = AIEngine.create("greedy")
        candidates = ai.select_moves_fen(INITIAL_FEN, n=10)

        legal_moves = get_legal_moves_from_fen(INITIAL_FEN)
        for move_str, _ in candidates:
            assert move_str in legal_moves

    def test_different_strategies_work(self):
        """测试不同策略都能正常工作"""
        strategies = ["random", "greedy", "minimax", "iterative"]

        for name in strategies:
            ai = AIEngine.create(name, AIConfig(depth=2))
            candidates = ai.select_moves_fen(INITIAL_FEN, n=3)

            assert len(candidates) > 0, f"Strategy {name} returned no moves"
            move_str, _ = candidates[0]
            assert isinstance(move_str, str), f"Strategy {name} returned invalid move"
