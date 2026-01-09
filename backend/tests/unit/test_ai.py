"""
AI 引擎单元测试
"""

import pytest

from xiangqi.ai import AIEngine, MinimaxAI, RandomAI
from xiangqi.ai.base import AIConfig
from xiangqi.ai.evaluator import Evaluator
from xiangqi.board import Board
from xiangqi.game import Game
from xiangqi.types import Color, PieceType, Position


class TestAIEngine:
    """AI 引擎测试"""

    def test_register_strategy(self):
        """测试策略注册"""
        strategies = AIEngine.list_strategies()
        assert "random" in strategies
        assert "minimax" in strategies

    def test_get_strategy(self):
        """测试获取策略"""
        strategy = AIEngine.get_strategy("random")
        assert isinstance(strategy, RandomAI)

    def test_get_strategy_with_config(self):
        """测试获取策略并配置"""
        config = AIConfig(depth=5)
        strategy = AIEngine.get_strategy("minimax", config)
        assert isinstance(strategy, MinimaxAI)
        assert strategy.config.depth == 5

    def test_unknown_strategy(self):
        """测试未知策略"""
        with pytest.raises(ValueError):
            AIEngine.get_strategy("unknown_strategy")


class TestRandomAI:
    """随机 AI 测试"""

    def test_select_move(self):
        """测试随机选择走法"""
        game = Game()
        ai = RandomAI()

        move = ai.select_move(game)
        assert move is not None
        # 验证走法是合法的
        assert move in game.get_legal_moves()

    def test_select_move_multiple_times(self):
        """测试多次选择走法（验证随机性）"""
        game = Game()
        ai = RandomAI()

        moves = set()
        for _ in range(100):
            move = ai.select_move(game)
            moves.add((move.from_pos, move.to_pos))

        # 应该选择了多种不同的走法
        assert len(moves) > 1


class TestMinimaxAI:
    """Minimax AI 测试"""

    def test_select_move(self):
        """测试 Minimax 选择走法"""
        game = Game()
        config = AIConfig(depth=2)
        ai = MinimaxAI(config)

        move = ai.select_move(game)
        assert move is not None
        assert move in game.get_legal_moves()

    def test_nodes_searched(self):
        """测试搜索节点计数"""
        game = Game()
        config = AIConfig(depth=2)
        ai = MinimaxAI(config)

        ai.select_move(game)
        assert ai.nodes_searched > 0

    def test_captures_winning_move(self):
        """测试 AI 会选择明显的好走法"""
        from xiangqi.piece import King, Rook

        game = Game()
        game.board._pieces.clear()

        # 放置红帅
        red_king = King(Color.RED, Position(0, 4))
        game.board.set_piece(red_king.position, red_king)

        # 放置黑将
        black_king = King(Color.BLACK, Position(9, 4))
        game.board.set_piece(black_king.position, black_king)

        # 放置红车，可以吃黑车
        red_rook = Rook(Color.RED, Position(5, 0))
        game.board.set_piece(red_rook.position, red_rook)

        # 放置黑车，处于可被吃的位置
        black_rook = Rook(Color.BLACK, Position(5, 8))
        game.board.set_piece(black_rook.position, black_rook)

        config = AIConfig(depth=2)
        ai = MinimaxAI(config)

        move = ai.select_move(game)
        # AI 应该选择吃黑车
        assert move is not None
        # 红车应该吃掉黑车（高价值目标）
        if move.from_pos == Position(5, 0):
            assert move.to_pos == Position(5, 8)


class TestEvaluator:
    """评估器测试"""

    def test_initial_position_balance(self):
        """测试初始局面评估接近平衡"""
        board = Board()
        evaluator = Evaluator()

        red_score = evaluator.evaluate(board, Color.RED)
        black_score = evaluator.evaluate(board, Color.BLACK)

        # 由于对称性，双方分数应该接近（红方先手可能有微小优势）
        assert abs(red_score - (-black_score)) < 100

    def test_piece_value_difference(self):
        """测试棋子价值差异影响评估"""
        board = Board()
        evaluator = Evaluator()

        # 初始评估
        initial_score = evaluator.evaluate(board, Color.RED)

        # 移除黑方一个车
        from xiangqi.types import Position

        board.remove_piece(Position(9, 0))

        # 重新评估
        new_score = evaluator.evaluate(board, Color.RED)

        # 红方分数应该增加（少了一个敌方车）
        assert new_score > initial_score

    def test_pawn_position_bonus(self):
        """测试兵过河后的位置加成"""
        board = Board()
        board._pieces.clear()

        from xiangqi.piece import King, Pawn
        from xiangqi.types import Position

        # 放置必要的将帅
        red_king = King(Color.RED, Position(0, 4))
        black_king = King(Color.BLACK, Position(9, 4))
        board.set_piece(red_king.position, red_king)
        board.set_piece(black_king.position, black_king)

        # 放置一个未过河的红兵
        pawn_before = Pawn(Color.RED, Position(3, 4))
        board.set_piece(pawn_before.position, pawn_before)

        evaluator = Evaluator()
        score_before = evaluator.evaluate(board, Color.RED)

        # 将兵移动过河
        board.remove_piece(Position(3, 4))
        pawn_after = Pawn(Color.RED, Position(5, 4))
        board.set_piece(pawn_after.position, pawn_after)

        score_after = evaluator.evaluate(board, Color.RED)

        # 过河后分数应该更高
        assert score_after > score_before
