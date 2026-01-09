"""
游戏管理器

管理游戏实例和 AI 配置
"""

from xiangqi.ai import AIEngine, AIStrategy, MinimaxAI, RandomAI
from xiangqi.ai.base import AIConfig
from xiangqi.api.models import AILevel, GameMode
from xiangqi.game import Game
from xiangqi.types import Color, Move, Position


class GameManager:
    """游戏管理器

    管理多个游戏实例和对应的 AI 配置
    """

    def __init__(self):
        self._games: dict[str, Game] = {}
        self._game_modes: dict[str, GameMode] = {}
        self._ai_engines: dict[str, dict[str, AIEngine]] = {}  # game_id -> {color -> engine}
        self._ai_colors: dict[str, list[Color]] = {}  # game_id -> list of AI colors

    def create_game(
        self, mode: GameMode, ai_level: AILevel = AILevel.EASY, ai_color: str = "black"
    ) -> Game:
        """创建新游戏"""
        game = Game()
        self._games[game.game_id] = game
        self._game_modes[game.game_id] = mode

        # 设置 AI
        self._ai_engines[game.game_id] = {}
        self._ai_colors[game.game_id] = []

        if mode == GameMode.HUMAN_VS_AI:
            color = Color.BLACK if ai_color == "black" else Color.RED
            self._setup_ai(game.game_id, color, ai_level)
            self._ai_colors[game.game_id].append(color)
        elif mode == GameMode.AI_VS_AI:
            self._setup_ai(game.game_id, Color.RED, ai_level)
            self._setup_ai(game.game_id, Color.BLACK, ai_level)
            self._ai_colors[game.game_id] = [Color.RED, Color.BLACK]

        return game

    def _setup_ai(self, game_id: str, color: Color, level: AILevel) -> None:
        """设置 AI 引擎"""
        engine = AIEngine()

        if level == AILevel.RANDOM:
            engine.set_strategy(RandomAI())
        else:
            # 根据难度设置搜索深度
            depth_map = {
                AILevel.EASY: 2,
                AILevel.MEDIUM: 3,
                AILevel.HARD: 4,
            }
            config = AIConfig(depth=depth_map.get(level, 2))
            engine.set_strategy(MinimaxAI(config))

        self._ai_engines[game_id][color.value] = engine

    def get_game(self, game_id: str) -> Game | None:
        """获取游戏实例"""
        return self._games.get(game_id)

    def get_mode(self, game_id: str) -> GameMode | None:
        """获取游戏模式"""
        return self._game_modes.get(game_id)

    def is_ai_turn(self, game_id: str) -> bool:
        """检查是否是 AI 的回合"""
        game = self._games.get(game_id)
        if not game:
            return False
        return game.current_turn in self._ai_colors.get(game_id, [])

    def get_ai_move(self, game_id: str) -> Move | None:
        """获取 AI 的走法"""
        game = self._games.get(game_id)
        if not game:
            return None

        color = game.current_turn
        engine = self._ai_engines.get(game_id, {}).get(color.value)
        if not engine:
            return None

        return engine.select_move(game)

    def make_move(self, game_id: str, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """执行走棋"""
        game = self._games.get(game_id)
        if not game:
            return False

        move = Move(Position(from_row, from_col), Position(to_row, to_col))
        return game.make_move(move)

    def delete_game(self, game_id: str) -> bool:
        """删除游戏"""
        if game_id not in self._games:
            return False

        del self._games[game_id]
        self._game_modes.pop(game_id, None)
        self._ai_engines.pop(game_id, None)
        self._ai_colors.pop(game_id, None)
        return True

    def list_games(self) -> list[str]:
        """列出所有游戏 ID"""
        return list(self._games.keys())


# 全局游戏管理器实例
game_manager = GameManager()
