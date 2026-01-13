"""
揭棋 AI 引擎基础类

提供 AI 策略的抽象基类和注册机制

## 接口说明

### 新接口（推荐）
- `select_moves_fen(fen: str, n: int) -> list[tuple[str, float]]`
  输入 FEN 字符串，返回 Top-N 候选走法字符串及评分

### 旧接口（兼容）
- `select_move(view: PlayerView) -> JieqiMove | None`
- `select_moves(view: PlayerView, n: int) -> list[tuple[JieqiMove, float]]`

重要：AI 只能看到玩家视角信息，无法看到暗子的真实身份！
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from jieqi.types import JieqiMove
    from jieqi.view import PlayerView


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

    所有 AI 策略必须继承此类并实现以下方法之一：
    1. select_moves_fen() - 新接口，基于 FEN 字符串（推荐）
    2. select_move() - 旧接口，基于 PlayerView（兼容）

    信息隔离：AI 只能看到玩家视角信息，暗子的 actual_type = None
    """

    name: str = "base"
    description: str = "Base AI strategy"

    def __init__(self, config: AIConfig | None = None):
        self.config = config or AIConfig()

    # =========================================================================
    # 新接口（基于 FEN 字符串）
    # =========================================================================

    def select_moves_fen(self, fen: str, n: int = 10) -> list[tuple[str, float]]:
        """基于 FEN 返回 Top-N 候选走法

        新接口，推荐子类重写此方法。
        默认实现会转换到旧接口。

        Args:
            fen: FEN 字符串（玩家视角）
            n: 返回的最大候选数

        Returns:
            [(move_str, score), ...] 按分数降序排列
            move_str 格式：
            - "a0a1" 明子走法
            - "+a0a1" 揭子走法
        """
        # 默认实现：转换到旧接口
        from jieqi.fen import create_board_from_fen, move_to_str, parse_fen, to_fen
        from jieqi.types import GameResult
        from jieqi.view import PlayerView

        state = parse_fen(fen)
        board = create_board_from_fen(fen)
        legal_moves = board.get_legal_moves(state.turn)

        # 构建 PlayerView
        from jieqi.types import get_position_piece_type
        from jieqi.view import ViewPiece

        view_pieces = []
        for fp in state.pieces:
            if fp.is_hidden:
                movement_type = get_position_piece_type(fp.position)
                view_pieces.append(
                    ViewPiece(
                        color=fp.color,
                        position=fp.position,
                        is_hidden=True,
                        actual_type=None,
                        movement_type=movement_type,
                    )
                )
            else:
                view_pieces.append(
                    ViewPiece(
                        color=fp.color,
                        position=fp.position,
                        is_hidden=False,
                        actual_type=fp.piece_type,
                        movement_type=fp.piece_type,
                    )
                )

        view = PlayerView(
            viewer=state.viewer,
            current_turn=state.turn,
            result=GameResult.ONGOING,
            move_count=0,
            is_in_check=board.is_in_check(state.turn),
            pieces=view_pieces,
            legal_moves=legal_moves,
            captured_pieces=[],
        )

        # 调用旧接口
        old_results = self.select_moves(view, n)

        # 转换结果
        return [(move_to_str(move), score) for move, score in old_results]

    # =========================================================================
    # 旧接口（基于 PlayerView，保持兼容）
    # =========================================================================

    def select_move(self, view: "PlayerView") -> "JieqiMove | None":
        """选择下一步走法（旧接口）

        Args:
            view: 玩家视角

        Returns:
            选择的走法，无合法走法返回 None
        """
        candidates = self.select_moves(view, n=1)
        if candidates:
            return candidates[0][0]
        return None

    def select_moves(self, view: "PlayerView", n: int = 10) -> list[tuple["JieqiMove", float]]:
        """返回 Top-N 候选着法及其评分（旧接口）

        默认实现会尝试调用新接口（如果子类重写了的话）。

        Args:
            view: 玩家视角
            n: 返回的最大候选数

        Returns:
            [(move, score), ...] 按分数降序排列
        """
        # 检查子类是否重写了 select_moves_fen
        if type(self).select_moves_fen is not AIStrategy.select_moves_fen:
            # 子类实现了新接口，转换调用
            from jieqi.fen import parse_move, to_fen

            fen = to_fen(view)
            str_results = self.select_moves_fen(fen, n)
            return [(parse_move(move_str)[0], score) for move_str, score in str_results]

        # 检查子类是否重写了 select_move（旧策略）
        if type(self).select_move is not AIStrategy.select_move:
            # 子类实现了旧的 select_move，调用它
            move = type(self).select_move(self, view)
            return [(move, 0.0)] if move else []

        # 默认实现：返回空（子类应该重写）
        return []


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
