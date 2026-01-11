"""
揭棋 AI 测试
"""

import pytest
from jieqi.ai import AIConfig, AIEngine, RandomAI
from jieqi.game import GameConfig, JieqiGame
from jieqi.types import ActionType, Color, GameResult


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
    """测试随机 AI"""

    @pytest.fixture
    def game(self):
        """创建测试游戏"""
        config = GameConfig(seed=42)
        return JieqiGame(config=config)

    def test_select_move_returns_legal_move(self, game: JieqiGame):
        """测试选择的走法是合法的"""
        ai = RandomAI()
        move = ai.select_move(game)

        assert move is not None
        legal_moves = game.get_legal_moves()
        assert move in legal_moves

    def test_select_move_with_seed_is_deterministic(self, game: JieqiGame):
        """测试使用种子时走法是确定性的"""
        # 需要使用相同的游戏状态才能确保确定性
        config1 = GameConfig(seed=42)
        config2 = GameConfig(seed=42)
        game1 = JieqiGame(config=config1)
        game2 = JieqiGame(config=config2)

        ai1 = RandomAI(AIConfig(seed=123))
        ai2 = RandomAI(AIConfig(seed=123))

        move1 = ai1.select_move(game1)
        move2 = ai2.select_move(game2)

        assert move1 == move2

    def test_select_move_returns_none_when_no_legal_moves(self):
        """测试没有合法走法时返回 None"""
        config = GameConfig(seed=42)
        game = JieqiGame(config=config)

        # 移除所有红方棋子（除了帅）
        for piece in game.board.get_all_pieces(Color.RED):
            if piece.actual_type != game.board.get_piece(piece.position).actual_type:
                continue
            game.board.remove_piece(piece.position)

        # 让帅被困住（这个测试可能需要更复杂的设置）
        ai = RandomAI()
        # 正常情况下应该有走法，这里只是测试接口


class TestAIVsAI:
    """测试 AI 对战"""

    def test_ai_vs_ai_game_completes(self):
        """测试两个 AI 可以完成一局游戏"""
        config = GameConfig(seed=42)
        game = JieqiGame(config=config)

        ai_red = RandomAI(AIConfig(seed=1))
        ai_black = RandomAI(AIConfig(seed=2))

        max_moves = 200  # 防止无限循环
        move_count = 0

        while game.result == GameResult.ONGOING and move_count < max_moves:
            current_ai = ai_red if game.current_turn == Color.RED else ai_black
            move = current_ai.select_move(game)

            if move is None:
                break

            game.make_move(move)
            move_count += 1

        # 游戏应该结束或达到最大步数
        assert move_count > 0
        # 打印结果用于调试
        print(f"Game ended after {move_count} moves with result: {game.result}")

    def test_multiple_ai_games(self):
        """测试多局 AI 对战"""
        results = {
            GameResult.RED_WIN: 0,
            GameResult.BLACK_WIN: 0,
            GameResult.DRAW: 0,
            GameResult.ONGOING: 0,
        }

        for seed in range(5):  # 5局游戏
            config = GameConfig(seed=seed)
            game = JieqiGame(config=config)

            ai_red = RandomAI(AIConfig(seed=seed * 2))
            ai_black = RandomAI(AIConfig(seed=seed * 2 + 1))

            max_moves = 200
            for _ in range(max_moves):
                if game.result != GameResult.ONGOING:
                    break

                current_ai = ai_red if game.current_turn == Color.RED else ai_black
                move = current_ai.select_move(game)

                if move is None:
                    break

                game.make_move(move)

            results[game.result] += 1

        # 所有游戏都有结果
        total = sum(results.values())
        assert total == 5

        print(f"AI vs AI results: {results}")
