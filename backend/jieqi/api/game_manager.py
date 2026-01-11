"""
揭棋游戏管理器

管理多个游戏实例和 AI 配置
"""

from jieqi.ai import AIConfig, AIEngine, AIStrategy
from jieqi.api.models import AILevel, GameMode
from jieqi.game import GameConfig, JieqiGame
from jieqi.types import Color, JieqiMove


class GameManager:
    """游戏管理器

    管理多个并发游戏实例，为每个游戏配置 AI
    """

    def __init__(self):
        self._games: dict[str, JieqiGame] = {}
        self._modes: dict[str, GameMode] = {}
        self._ai_configs: dict[str, dict] = {}

    def create_game(
        self,
        mode: GameMode = GameMode.HUMAN_VS_AI,
        ai_level: AILevel | None = None,
        ai_color: str | None = "black",
        ai_strategy: str | None = None,
        seed: int | None = None,
        red_ai_strategy: str | None = None,
        black_ai_strategy: str | None = None,
        delay_reveal: bool = False,
    ) -> JieqiGame:
        """创建新游戏

        Args:
            mode: 游戏模式
            ai_level: AI 难度等级
            ai_color: AI 执子颜色（人机模式）
            ai_strategy: 指定 AI 策略（覆盖 ai_level）
            seed: 随机种子
            red_ai_strategy: 红方 AI 策略（AI vs AI 模式）
            black_ai_strategy: 黑方 AI 策略（AI vs AI 模式）
            delay_reveal: 延迟分配模式（翻棋时决定身份）

        Returns:
            新创建的游戏
        """
        config = GameConfig(seed=seed, delay_reveal=delay_reveal)
        game = JieqiGame(config=config)

        self._games[game.game_id] = game
        self._modes[game.game_id] = mode

        # 配置 AI
        ai_config = {"mode": mode}

        if mode == GameMode.HUMAN_VS_AI:
            strategy_name = self._get_strategy_name(ai_level, ai_strategy)
            ai_config["ai_color"] = ai_color
            ai_config["ai_strategy"] = strategy_name
            ai_config["ai"] = AIEngine.create(strategy_name)
        elif mode == GameMode.AI_VS_AI:
            red_strategy = self._get_strategy_name(ai_level, red_ai_strategy)
            black_strategy = self._get_strategy_name(ai_level, black_ai_strategy)
            ai_config["red_ai"] = AIEngine.create(red_strategy)
            ai_config["black_ai"] = AIEngine.create(black_strategy)
            ai_config["red_strategy"] = red_strategy
            ai_config["black_strategy"] = black_strategy

        self._ai_configs[game.game_id] = ai_config

        return game

    def _get_strategy_name(
        self,
        level: AILevel | None,
        strategy: str | None,
    ) -> str:
        """获取 AI 策略名称"""
        # 优先使用指定的策略
        if strategy:
            return strategy

        # 默认使用 aggressive 策略
        return "aggressive"

    def get_game(self, game_id: str) -> JieqiGame | None:
        """获取游戏实例"""
        return self._games.get(game_id)

    def get_mode(self, game_id: str) -> GameMode | None:
        """获取游戏模式"""
        return self._modes.get(game_id)

    def is_delay_reveal(self, game_id: str) -> bool:
        """检查是否为延迟分配模式"""
        game = self._games.get(game_id)
        if game:
            return game.config.delay_reveal
        return False

    def delete_game(self, game_id: str) -> bool:
        """删除游戏"""
        if game_id in self._games:
            del self._games[game_id]
            self._modes.pop(game_id, None)
            self._ai_configs.pop(game_id, None)
            return True
        return False

    def list_games(self) -> list[str]:
        """列出所有游戏 ID"""
        return list(self._games.keys())

    def get_ai_move(self, game_id: str) -> JieqiMove | None:
        """获取 AI 的走法

        Args:
            game_id: 游戏 ID

        Returns:
            AI 选择的走法，如果不是 AI 回合则返回 None
        """
        game = self._games.get(game_id)
        if not game:
            return None

        config = self._ai_configs.get(game_id, {})
        mode = config.get("mode")

        if mode == GameMode.HUMAN_VS_AI:
            ai_color = config.get("ai_color", "black")
            if game.current_turn.value != ai_color:
                return None
            ai: AIStrategy = config.get("ai")
            if ai:
                # 传递 PlayerView 而不是 JieqiGame，确保 AI 看不到暗子身份
                view = game.get_view(game.current_turn)
                return ai.select_move(view)
        elif mode == GameMode.AI_VS_AI:
            if game.current_turn == Color.RED:
                ai = config.get("red_ai")
            else:
                ai = config.get("black_ai")
            if ai:
                # 传递 PlayerView 而不是 JieqiGame，确保 AI 看不到暗子身份
                view = game.get_view(game.current_turn)
                return ai.select_move(view)

        return None

    def is_ai_turn(self, game_id: str) -> bool:
        """检查是否是 AI 回合"""
        game = self._games.get(game_id)
        if not game:
            return False

        config = self._ai_configs.get(game_id, {})
        mode = config.get("mode")

        if mode == GameMode.HUMAN_VS_AI:
            ai_color = config.get("ai_color", "black")
            return game.current_turn.value == ai_color
        elif mode == GameMode.AI_VS_AI:
            return True

        return False


# 全局游戏管理器实例
game_manager = GameManager()
