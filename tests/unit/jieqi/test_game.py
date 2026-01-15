"""
揭棋游戏测试
"""

import pytest
from jieqi.game import JieqiGame, GameConfig
from jieqi.types import ActionType, Color, GameResult, JieqiMove, Position


class TestJieqiGameInit:
    """测试游戏初始化"""

    def test_game_creates_with_id(self):
        """游戏创建时有ID"""
        game = JieqiGame()
        assert game.game_id is not None
        assert len(game.game_id) > 0

    def test_game_starts_with_red_turn(self):
        """游戏开始时是红方回合"""
        game = JieqiGame()
        assert game.current_turn == Color.RED

    def test_game_starts_ongoing(self):
        """游戏开始时状态为进行中"""
        game = JieqiGame()
        assert game.result == GameResult.ONGOING

    def test_game_with_seed(self):
        """使用种子创建游戏"""
        config = GameConfig(seed=42)
        game1 = JieqiGame(config=config)
        game2 = JieqiGame(config=config)
        # 相同种子产生相同棋盘
        assert game1.board.to_full_dict() == game2.board.to_full_dict()


class TestJieqiGameMoves:
    """测试游戏走法"""

    @pytest.fixture
    def game(self):
        """创建测试游戏"""
        config = GameConfig(seed=42)
        return JieqiGame(config=config)

    def test_make_valid_move(self, game: JieqiGame):
        """测试有效走法"""
        # 获取红方的一个合法走法
        legal_moves = game.get_legal_moves()
        assert len(legal_moves) > 0

        move = legal_moves[0]
        result = game.make_move(move)
        assert result is True
        assert game.current_turn == Color.BLACK
        assert len(game.move_history) == 1

    def test_make_invalid_move(self, game: JieqiGame):
        """测试无效走法"""
        # 尝试一个无效走法
        invalid_move = JieqiMove.regular_move(Position(0, 0), Position(5, 5))
        result = game.make_move(invalid_move)
        assert result is False
        assert game.current_turn == Color.RED
        assert len(game.move_history) == 0

    def test_turns_alternate(self, game: JieqiGame):
        """测试回合交替"""
        assert game.current_turn == Color.RED

        # 红方走一步
        red_move = game.get_legal_moves()[0]
        game.make_move(red_move)
        assert game.current_turn == Color.BLACK

        # 黑方走一步
        black_move = game.get_legal_moves()[0]
        game.make_move(black_move)
        assert game.current_turn == Color.RED

    def test_undo_move(self, game: JieqiGame):
        """测试撤销走法"""
        # 先走一步
        move = game.get_legal_moves()[0]
        game.make_move(move)
        assert game.current_turn == Color.BLACK

        # 撤销
        result = game.undo_move()
        assert result is True
        assert game.current_turn == Color.RED
        assert len(game.move_history) == 0

    def test_undo_empty_history(self, game: JieqiGame):
        """测试空历史撤销"""
        result = game.undo_move()
        assert result is False


class TestJieqiGameState:
    """测试游戏状态"""

    @pytest.fixture
    def game(self):
        """创建测试游戏"""
        config = GameConfig(seed=42)
        return JieqiGame(config=config)

    def test_hidden_count(self, game: JieqiGame):
        """测试暗子计数"""
        assert game.get_hidden_count(Color.RED) == 15
        assert game.get_hidden_count(Color.BLACK) == 15

    def test_revealed_count(self, game: JieqiGame):
        """测试明子计数"""
        assert game.get_revealed_count(Color.RED) == 1  # 只有帅
        assert game.get_revealed_count(Color.BLACK) == 1  # 只有将

    def test_hidden_count_decreases_after_reveal_move(self, game: JieqiGame):
        """测试揭子后暗子数减少"""
        # 找一个揭子走法
        reveal_moves = [
            m for m in game.get_legal_moves() if m.action_type == ActionType.REVEAL_AND_MOVE
        ]
        assert len(reveal_moves) > 0

        game.make_move(reveal_moves[0])
        assert game.get_hidden_count(Color.RED) == 14
        assert game.get_revealed_count(Color.RED) == 2


class TestJieqiGameSerialization:
    """测试游戏序列化"""

    def test_to_dict(self):
        """测试游戏序列化"""
        config = GameConfig(seed=42)
        game = JieqiGame(game_id="test-game", config=config)

        data = game.to_dict()
        assert data["game_id"] == "test-game"
        assert data["current_turn"] == "red"
        assert data["result"] == "ongoing"
        assert "board" in data
        assert "legal_moves" in data
        assert "hidden_count" in data

    def test_to_full_dict(self):
        """测试完整序列化"""
        config = GameConfig(seed=42)
        game = JieqiGame(config=config)

        data = game.to_full_dict()
        # 完整字典应该包含暗子的真实身份
        assert "board" in data
        pieces = data["board"]["pieces"]
        # 检查暗子有 actual_type
        hidden_pieces = [p for p in pieces if p["state"] == "hidden"]
        assert len(hidden_pieces) > 0
        for p in hidden_pieces:
            assert "actual_type" in p

    def test_get_move_history(self):
        """测试走棋历史"""
        config = GameConfig(seed=42)
        game = JieqiGame(config=config)

        # 走几步
        for _ in range(3):
            moves = game.get_legal_moves()
            if moves:
                game.make_move(moves[0])

        history = game.get_move_history()
        assert len(history) == 3
        for record in history:
            assert "move" in record
            assert "notation" in record


class TestJieqiGameResult:
    """测试游戏结果"""

    def test_game_ends_when_king_captured(self):
        """测试吃掉将/帅时游戏结束"""
        config = GameConfig(seed=42)
        game = JieqiGame(config=config)

        # 移除黑将
        game.board.remove_piece(Position(9, 4))
        # 手动更新结果
        game.result = game.board.get_game_result(game.current_turn)

        assert game.result == GameResult.RED_WIN

    def test_cannot_move_after_game_ends(self):
        """测试游戏结束后不能走棋"""
        config = GameConfig(seed=42)
        game = JieqiGame(config=config)
        game.result = GameResult.RED_WIN

        moves = game.get_legal_moves()
        if moves:
            result = game.make_move(moves[0])
            assert result is False
