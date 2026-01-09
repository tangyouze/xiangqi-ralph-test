"""
AI 引擎基类和策略接口

定义可扩展的 AI 架构，支持策略模式和注册机制
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from xiangqi.game import Game
from xiangqi.types import Move


@dataclass
class AIConfig:
    """AI 配置"""

    name: str = "AI"
    # 搜索深度（对于搜索类 AI）
    depth: int = 3
    # 时间限制（毫秒）
    time_limit_ms: int | None = None
    # 随机性参数
    randomness: float = 0.0


class AIStrategy(ABC):
    """AI 策略接口

    所有 AI 实现必须继承此类，实现可插拔的 AI 策略
    """

    # 策略名称，用于注册和识别
    name: ClassVar[str] = "base"

    def __init__(self, config: AIConfig | None = None):
        self.config = config or AIConfig()

    @abstractmethod
    def select_move(self, game: Game) -> Move | None:
        """选择一步走法

        Args:
            game: 当前游戏状态

        Returns:
            选择的走法，如果没有合法走法则返回 None
        """
        pass

    def on_game_start(self, game: Game) -> None:
        """游戏开始时的回调"""
        pass

    def on_game_end(self, game: Game) -> None:
        """游戏结束时的回调"""
        pass


class AIEngine:
    """AI 引擎

    管理 AI 策略的注册和选择，提供统一的 AI 调用接口
    """

    # 已注册的策略
    _strategies: ClassVar[dict[str, type[AIStrategy]]] = {}

    def __init__(self, strategy: AIStrategy | None = None):
        self.strategy = strategy

    @classmethod
    def register(cls, strategy_class: type[AIStrategy]) -> type[AIStrategy]:
        """注册 AI 策略（可用作装饰器）"""
        cls._strategies[strategy_class.name] = strategy_class
        return strategy_class

    @classmethod
    def get_strategy(cls, name: str, config: AIConfig | None = None) -> AIStrategy:
        """获取指定名称的策略实例"""
        if name not in cls._strategies:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(f"Unknown AI strategy: {name}. Available: {available}")
        return cls._strategies[name](config)

    @classmethod
    def list_strategies(cls) -> list[str]:
        """列出所有已注册的策略"""
        return list(cls._strategies.keys())

    def select_move(self, game: Game) -> Move | None:
        """使用当前策略选择走法"""
        if self.strategy is None:
            raise ValueError("No AI strategy set")
        return self.strategy.select_move(game)

    def set_strategy(self, strategy: AIStrategy) -> None:
        """设置 AI 策略"""
        self.strategy = strategy

    def set_strategy_by_name(self, name: str, config: AIConfig | None = None) -> None:
        """通过名称设置策略"""
        self.strategy = self.get_strategy(name, config)
