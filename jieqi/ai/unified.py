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

    # 时间限制（秒）
    time_limit: float = 0.5
    # 随机性
    randomness: float = 0.0
    # 随机种子
    seed: int | None = None


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

    通过长驻 server 进程与 Rust AI 通信（stdin/stdout）
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

        # 长驻进程
        self._process: subprocess.Popen | None = None

    def _ensure_server(self) -> None:
        """确保 server 进程在运行"""
        if self._process is None or self._process.poll() is not None:
            self._process = subprocess.Popen(
                [str(self._binary), "server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

    def _send_request(self, request: dict) -> dict:
        """发送请求并等待响应"""
        self._ensure_server()
        assert self._process is not None
        assert self._process.stdin is not None
        assert self._process.stdout is not None

        # 发送请求
        self._process.stdin.write(json.dumps(request) + "\n")
        self._process.stdin.flush()

        # 读取响应
        response_line = self._process.stdout.readline()
        if not response_line:
            raise RuntimeError("Rust server closed unexpectedly")

        response = json.loads(response_line)
        if not response.get("ok", False):
            raise RuntimeError(f"Rust AI error: {response.get('error', 'Unknown error')}")

        return response

    def get_legal_moves(self, fen: str) -> list[str]:
        response = self._send_request({"cmd": "moves", "fen": fen})
        return response.get("legal_moves", [])

    def get_best_moves(self, fen: str, n: int = 5) -> list[tuple[str, float]]:
        response = self._send_request(
            {
                "cmd": "best",
                "fen": fen,
                "strategy": self.strategy_name,
                "time_limit": self.config.time_limit,
                "n": n,
            }
        )
        return [(m["move"], m["score"]) for m in response.get("moves", [])]

    def get_best_moves_with_stats(
        self, fen: str, n: int = 5
    ) -> tuple[list[tuple[str, float]], int, float]:
        """获取最佳走法及搜索统计

        Returns:
            (moves, nodes, nps) - 走法列表、搜索节点数、每秒节点数
        """
        response = self._send_request(
            {
                "cmd": "best",
                "fen": fen,
                "strategy": self.strategy_name,
                "time_limit": self.config.time_limit,
                "n": n,
            }
        )
        moves = [(m["move"], m["score"]) for m in response.get("moves", [])]
        nodes = response.get("nodes", 0)
        nps = response.get("nps", 0.0)
        return moves, nodes, nps

    def get_eval(self, fen: str) -> tuple[float, str]:
        """静态评估（不搜索）

        Returns:
            (eval_score, color) - 评估分数、当前行棋方
        """
        response = self._send_request({"cmd": "eval", "fen": fen})
        return response.get("eval", 0.0), response.get("color", "red")

    def get_search_tree(self, fen: str, depth: int = 3) -> dict:
        """获取搜索树调试信息

        Returns:
            {
                "fen": str,
                "eval": float,  # 当前局面静态评估
                "depth": int,
                "first_moves": [
                    {
                        "move": str,
                        "type": "move" | "chance",
                        "eval": float,  # 走完后静态评估
                        "score": float,  # 搜索分数
                        "opposite_top10": [...],
                        "opposite_bottom10": [...]
                    }
                ],
                "nodes": int
            }
        """
        response = self._send_request({"cmd": "search", "fen": fen, "depth": depth})
        return response

    def list_strategies(self) -> list[str]:
        # Rust 支持的策略
        return [
            "random",
            "greedy",
            "iterative",
            "mcts",
            "muses",
            "muses2",
            "muses3",
            "muses4",
        ]

    def close(self) -> None:
        """关闭 server 进程"""
        if self._process is not None and self._process.poll() is None:
            try:
                assert self._process.stdin is not None
                self._process.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
                self._process.stdin.flush()
                self._process.wait(timeout=1.0)
            except Exception:
                self._process.kill()
            self._process = None

    def __del__(self):
        """析构时关闭进程"""
        self.close()


class UnifiedAIEngine:
    """统一 AI 引擎

    调用 Rust AI 后端（Python AI 已移除）。
    """

    def __init__(
        self,
        strategy: str = "muses",
        time_limit: float = 0.5,
        randomness: float = 0.0,
        seed: int | None = None,
    ):
        """创建统一 AI 引擎

        Args:
            strategy: AI 策略名称
            time_limit: 时间限制（秒）
            randomness: 随机性
            seed: 随机种子
        """
        self.strategy = strategy

        config = UnifiedAIConfig(
            time_limit=time_limit,
            randomness=randomness,
            seed=seed,
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

    def get_best_moves_with_stats(
        self, fen: str, n: int = 5
    ) -> tuple[list[tuple[str, float]], int, float]:
        """获取最佳走法及搜索统计

        Args:
            fen: FEN 字符串
            n: 返回的走法数量

        Returns:
            (moves, nodes, nps) - 走法列表、搜索节点数、每秒节点数
        """
        return self._backend.get_best_moves_with_stats(fen, n)

    def get_eval(self, fen: str) -> tuple[float, str]:
        """静态评估（不搜索）

        Args:
            fen: FEN 字符串

        Returns:
            (eval_score, color) - 评估分数、当前行棋方
        """
        return self._backend.get_eval(fen)

    def get_search_tree(self, fen: str, depth: int = 3) -> dict:
        """获取搜索树调试信息

        Args:
            fen: FEN 字符串
            depth: 搜索深度

        Returns:
            包含 first_moves、opposite_top10/bottom10 的详细搜索信息
        """
        return self._backend.get_search_tree(fen, depth)

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
    strategy: str = "muses",
    time_limit: float = 0.5,
) -> list[tuple[str, float]]:
    """获取最佳走法（便捷函数）"""
    engine = UnifiedAIEngine(strategy=strategy, time_limit=time_limit)
    return engine.get_best_moves(fen, n)
