"""
统一 AI 引擎接口

只支持 Rust AI 后端。Python AI 策略已移除。

## 使用方法

```python
from jieqi.ai.unified import UnifiedAIEngine

# 使用 Rust 后端（只支持Rust）
engine = UnifiedAIEngine(strategy="minimax", depth=3)
moves = engine.get_best_moves(fen, n=5)

# 获取合法走法
legal_moves = engine.get_legal_moves(fen)
```

## 接口规范

输入: FEN 字符串
输出: list[tuple[str, float]] - [(move_str, score), ...]
"""

from __future__ import annotations

import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


@dataclass
class UnifiedAIConfig:
    """统一 AI 配置"""

    # 搜索深度
    depth: int = 3
    # 随机性
    randomness: float = 0.0
    # 随机种子
    seed: int | None = None
    # 时间限制（秒）
    time_limit: float | None = None


class AIBackend(ABC):
    """AI 后端抽象基类"""

    @abstractmethod
    def get_legal_moves(self, fen: str) -> list[str]:
        """获取合法走法"""
        pass

    @abstractmethod
    def get_best_moves(self, fen: str, n: int = 5) -> list[tuple[str, float]]:
        """获取最佳走法"""
        pass

    @abstractmethod
    def list_strategies(self) -> list[str]:
        """列出可用策略"""
        pass


class RustBackend(AIBackend):
    """Rust AI 后端

    通过调用 Rust CLI 二进制文件与 Rust AI 通信
    """

    def __init__(self, strategy: str = "greedy", config: UnifiedAIConfig | None = None):
        self.strategy_name = strategy
        self.config = config or UnifiedAIConfig()

        # Rust 二进制文件路径
        self._binary = PROJECT_ROOT / "rust-ai" / "target" / "release" / "xiangqi-ai"

        if not self._binary.exists():
            # 尝试 debug 版本
            self._binary = PROJECT_ROOT / "rust-ai" / "target" / "debug" / "xiangqi-ai"

        if not self._binary.exists():
            raise FileNotFoundError(
                "Rust AI binary not found. Please build with: cd rust-ai && cargo build --release"
            )

    def _run_command(self, args: list[str]) -> str:
        """执行 Rust CLI 命令"""
        cmd = [str(self._binary)] + args
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Rust AI error: {result.stderr}")

        return result.stdout

    def get_legal_moves(self, fen: str) -> list[str]:
        output = self._run_command(["moves", "--fen", fen])

        # 解析输出
        moves = []
        for line in output.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("Legal moves"):
                moves.append(line)

        return moves

    def get_best_moves(self, fen: str, n: int = 5) -> list[tuple[str, float]]:
        args = [
            "best",
            "--fen",
            fen,
            "--strategy",
            self.strategy_name,
            "--n",
            str(n),
            "--json",
        ]

        # 添加时间限制（使用配置或默认值）
        time_limit = self.config.time_limit if self.config.time_limit is not None else 0.5
        args.extend(["--time-limit", str(time_limit)])

        output = self._run_command(args)

        # 解析 JSON 输出
        data = json.loads(output)
        return [(m["move"], m["score"]) for m in data["moves"]]

    def list_strategies(self) -> list[str]:
        # Rust 支持的策略
        return [
            "random",
            "greedy",
            "minimax",
            "iterative",
            "mcts",
            "muses",
        ]


class UnifiedAIEngine:
    """统一 AI 引擎

    调用 Rust AI 后端（Python AI 已移除）。
    """

    def __init__(
        self,
        backend: Literal["rust"] = "rust",  # 保留参数以兼容，但只支持rust
        strategy: str = "minimax",
        depth: int = 3,
        randomness: float = 0.0,
        seed: int | None = None,
        time_limit: float | None = None,
    ):
        """创建统一 AI 引擎

        Args:
            backend: 后端类型 (只支持 "rust")
            strategy: AI 策略名称
            depth: 搜索深度
            randomness: 随机性
            seed: 随机种子
            time_limit: 时间限制（秒）
        """
        if backend != "rust":
            raise ValueError(f"只支持 Rust 后端。Python AI 策略已移除。")

        self.backend_type = backend
        self.strategy = strategy

        config = UnifiedAIConfig(
            depth=depth,
            randomness=randomness,
            seed=seed,
            time_limit=time_limit,
        )

        self._backend: AIBackend = RustBackend(strategy, config)

    def get_legal_moves(self, fen: str) -> list[str]:
        """获取合法走法

        Args:
            fen: FEN 字符串

        Returns:
            走法字符串列表
        """
        return self._backend.get_legal_moves(fen)

    def get_best_moves(self, fen: str, n: int = 5) -> list[tuple[str, float]]:
        """获取最佳走法

        Args:
            fen: FEN 字符串
            n: 返回的走法数量

        Returns:
            [(move_str, score), ...] 按分数降序排列
        """
        return self._backend.get_best_moves(fen, n)

    def get_best_move(self, fen: str) -> tuple[str, float] | None:
        """获取最佳单一走法

        Args:
            fen: FEN 字符串

        Returns:
            (move_str, score) 或 None
        """
        moves = self.get_best_moves(fen, n=1)
        return moves[0] if moves else None

    def list_strategies(self) -> list[str]:
        """列出当前后端可用的策略"""
        return self._backend.list_strategies()

    @staticmethod
    def list_backends() -> list[str]:
        """列出可用的后端"""
        return ["rust"]  # 只支持Rust


# =============================================================================
# 便捷函数
# =============================================================================


def get_legal_moves(fen: str) -> list[str]:
    """获取合法走法（便捷函数）"""
    engine = UnifiedAIEngine()
    return engine.get_legal_moves(fen)


def get_best_moves(
    fen: str,
    n: int = 5,
    strategy: str = "minimax",
    depth: int = 3,
) -> list[tuple[str, float]]:
    """获取最佳走法（便捷函数）"""
    engine = UnifiedAIEngine(strategy=strategy, depth=depth)
    return engine.get_best_moves(fen, n)
