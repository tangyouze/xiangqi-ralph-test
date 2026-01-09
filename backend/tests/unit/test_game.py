"""
游戏管理单元测试
"""

import pytest

from xiangqi.game import Game, GameConfig
from xiangqi.types import Color, GameResult, Move, Position


class TestGameInitialization:
    """游戏初始化测试"""

    def test_new_game(self):
        """测试创建新游戏"""
        game = Game()
        assert game.game_id is not None
        assert game.current_turn == Color.RED
        assert game.result == GameResult.ONGOING
        assert len(game.move_history) == 0

    def test_new_game_with_id(self):
        """测试使用指定 ID 创建游戏"""
        game = Game(game_id="test-game-123")
        assert game.game_id == "test-game-123"

    def test_new_game_with_config(self):
        """测试使用配置创建游戏"""
        config = GameConfig(time_limit_seconds=60)
        game = Game(config=config)
        assert game.config.time_limit_seconds == 60


class TestGameMoves:
    """游戏走棋测试"""

    def test_make_valid_move(self):
        """测试执行有效走棋"""
        game = Game()
        # 红车前进
        move = Move(Position(0, 0), Position(2, 0))
        result = game.make_move(move)

        assert result is True
        assert game.current_turn == Color.BLACK
        assert len(game.move_history) == 1

    def test_make_invalid_move(self):
        """测试执行无效走棋"""
        game = Game()
        # 帅不能走两步
        move = Move(Position(0, 4), Position(2, 4))
        result = game.make_move(move)

        assert result is False
        assert game.current_turn == Color.RED
        assert len(game.move_history) == 0

    def test_cannot_move_opponent_piece(self):
        """测试不能移动对方棋子"""
        game = Game()
        # 尝试移动黑方棋子
        move = Move(Position(9, 0), Position(7, 0))
        result = game.make_move(move)

        assert result is False
        assert game.current_turn == Color.RED

    def test_undo_move(self):
        """测试撤销走棋"""
        game = Game()
        move = Move(Position(0, 0), Position(2, 0))
        game.make_move(move)

        result = game.undo_move()
        assert result is True
        assert game.current_turn == Color.RED
        assert len(game.move_history) == 0

    def test_undo_when_no_moves(self):
        """测试没有走棋时撤销"""
        game = Game()
        result = game.undo_move()
        assert result is False


class TestGameStatus:
    """游戏状态测试"""

    def test_get_legal_moves(self):
        """测试获取合法走法"""
        game = Game()
        moves = game.get_legal_moves()
        # 初始局面红方应该有多个合法走法
        assert len(moves) > 0

    def test_is_in_check(self):
        """测试检查将军状态"""
        game = Game()
        # 初始局面不应该被将军
        assert not game.is_in_check()


class TestGameSerialization:
    """游戏序列化测试"""

    def test_to_dict(self):
        """测试序列化为字典"""
        game = Game()
        data = game.to_dict()

        assert "game_id" in data
        assert "board" in data
        assert "current_turn" in data
        assert "result" in data
        assert "move_count" in data
        assert "is_in_check" in data
        assert "legal_moves" in data

    def test_get_move_history(self):
        """测试获取走棋历史"""
        game = Game()
        move = Move(Position(0, 0), Position(2, 0))
        game.make_move(move)

        history = game.get_move_history()
        assert len(history) == 1
        assert "move" in history[0]
        assert "notation" in history[0]
