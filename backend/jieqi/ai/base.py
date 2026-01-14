"""
揭棋 AI 引擎基础类

提供 AI 策略的抽象基类和注册机制

## 接口说明

唯一接口：
- `select_moves_fen(fen: str, n: int) -> list[tuple[str, float]]`
  输入 FEN 字符串，返回 Top-N 候选走法字符串及评分

重要：AI 只能看到玩家视角信息，无法看到暗子的真实身份！
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable


@dataclass
class AIConfig:
    """AI 配置"""

    # 搜索深度
    depth: int = 3
    # 时间限制（秒）
    time_limit: float | None = None
    # 随机性（用于避免相同局面下完全相同的走法）
    randomness: float = 0.0
    # 随机种子
    seed: int | None = None


class AIStrategy(ABC):
    """AI 策略基类

    所有 AI 策略必须继承此类并实现 select_moves_fen() 方法。

    信息隔离：AI 只能看到玩家视角信息，暗子的 actual_type = None
    """

    name: str = "base"
    description: str = "Base AI strategy"

    def __init__(self, config: AIConfig | None = None):
        self.config = config or AIConfig()

    @abstractmethod
    def select_moves_fen(self, fen: str, n: int = 10) -> list[tuple[str, float]]:
        """基于 FEN 返回 Top-N 候选走法

        Args:
            fen: FEN 字符串（玩家视角）
            n: 返回的最大候选数

        Returns:
            [(move_str, score), ...] 按分数降序排列
            move_str 格式：
            - "a0a1" 明子走法
            - "+a0a1" 揭子走法
        """
        pass


class AIEngine:
    """AI 引擎

    管理 AI 策略的注册和创建
    """

    _strategies: dict[str, type[AIStrategy]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[type[AIStrategy]], type[AIStrategy]]:
        """注册 AI 策略的装饰器

        Usage:
            @AIEngine.register("my_ai")
            class MyAI(AIStrategy):
                ...
        """

        def decorator(strategy_class: type[AIStrategy]) -> type[AIStrategy]:
            strategy_class.name = name
            cls._strategies[name] = strategy_class
            return strategy_class

        return decorator

    @classmethod
    def create(cls, name: str, config: AIConfig | None = None) -> AIStrategy:
        """创建 AI 策略实例

        Args:
            name: 策略名称
            config: AI 配置

        Returns:
            AI 策略实例

        Raises:
            ValueError: 如果策略名称未注册
        """
        if name not in cls._strategies:
            available = list(cls._strategies.keys())
            raise ValueError(f"Unknown AI strategy: {name}. Available: {available}")

        return cls._strategies[name](config)

    @classmethod
    def list_strategies(cls) -> list[dict[str, str]]:
        """列出所有已注册的 AI 策略

        Returns:
            策略信息列表
        """
        return [
            {"name": name, "description": strategy.description}
            for name, strategy in cls._strategies.items()
        ]

    @classmethod
    def get_strategy_names(cls) -> list[str]:
        """获取所有已注册的策略名称"""
        return list(cls._strategies.keys())
