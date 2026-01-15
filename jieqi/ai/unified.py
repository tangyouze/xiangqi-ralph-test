"""
统一 AI 引擎接口

提供统一的 FEN 接口，可以调用 Python 或 Rust AI 后端。

## 使用方法

```python
from jieqi.ai.unified import UnifiedAIEngine

# 使用 Python 后端
engine = UnifiedAIEngine(backend="python", strategy="greedy")
moves = engine.get_best_moves(fen, n=5)

# 使用 Rust 后端
engine = UnifiedAIEngine(backend="rust", strategy="minimax", depth=3)
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


class PythonBackend(AIBackend):
    """Python AI 后端"""

    def __init__(self, strategy: str = "greedy", config: UnifiedAIConfig | None = None):
        from jieqi.ai import AIConfig, AIEngine

        self.strategy_name = strategy
        self.config = config or UnifiedAIConfig()

        ai_config = AIConfig(
            depth=self.config.depth,
            randomness=self.config.randomness,
            seed=self.config.seed,
            time_limit=self.config.time_limit,
        )
        self._engine = AIEngine.create(strategy, ai_config)

    def get_legal_moves(self, fen: str) -> list[str]:
        from jieqi.fen import get_legal_moves_from_fen

        return get_legal_moves_from_fen(fen)

    def get_best_moves(self, fen: str, n: int = 5) -> list[tuple[str, float]]:
        return self._engine.select_moves_fen(fen, n)

    def list_strategies(self) -> list[str]:
        from jieqi.ai import AIEngine

        return AIEngine.get_strategy_names()


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
                f"Rust AI binary not found. Please build with: cd rust-ai && cargo build --release"
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
            "--depth",
            str(self.config.depth),
            "--n",
            str(n),
            "--json",
        ]

        # 添加时间限制（如果设置）
        if self.config.time_limit is not None:
            args.extend(["--time-limit", str(self.config.time_limit)])

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
            "positional",
            "defensive",
            "aggressive",
            "pvs",
            "muses",
        ]


class UnifiedAIEngine:
    """统一 AI 引擎

    提供统一的 FEN 接口，可以调用 Python 或 Rust AI 后端。
    """

    def __init__(
        self,
        backend: Literal["python", "rust"] = "python",
        strategy: str = "greedy",
        depth: int = 3,
        randomness: float = 0.0,
        seed: int | None = None,
        time_limit: float | None = None,
    ):
        """创建统一 AI 引擎

        Args:
            backend: 后端类型 ("python" 或 "rust")
            strategy: AI 策略名称
            depth: 搜索深度
            randomness: 随机性
            seed: 随机种子
            time_limit: 时间限制（秒）
        """
        self.backend_type = backend
        self.strategy = strategy

        config = UnifiedAIConfig(
            depth=depth,
            randomness=randomness,
            seed=seed,
            time_limit=time_limit,
        )

        if backend == "python":
            self._backend: AIBackend = PythonBackend(strategy, config)
        elif backend == "rust":
            self._backend = RustBackend(strategy, config)
        else:
            raise ValueError(f"Unknown backend: {backend}. Use 'python' or 'rust'.")

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
        return ["python", "rust"]


# =============================================================================
# 便捷函数
# =============================================================================


def get_legal_moves(fen: str, backend: Literal["python", "rust"] = "python") -> list[str]:
    """获取合法走法（便捷函数）"""
    engine = UnifiedAIEngine(backend=backend)
    return engine.get_legal_moves(fen)


def get_best_moves(
    fen: str,
    n: int = 5,
    backend: Literal["python", "rust"] = "python",
    strategy: str = "greedy",
    depth: int = 3,
) -> list[tuple[str, float]]:
    """获取最佳走法（便捷函数）"""
    engine = UnifiedAIEngine(backend=backend, strategy=strategy, depth=depth)
    return engine.get_best_moves(fen, n)
