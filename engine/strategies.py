"""
统一的 AI 策略管理模块

从 Rust CLI 动态获取可用策略列表，确保所有地方使用一致的策略。
"""

import json
import subprocess
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_available_strategies() -> list[str]:
    """从 Rust CLI 动态获取可用策略列表（带缓存）

    Returns:
        策略名称列表，如 ["random", "muses2", "it2", "it3"]
    """
    rust_ai_dir = Path(__file__).parent.parent / "rust-ai"
    result = subprocess.run(
        ["cargo", "run", "--release", "-q", "--", "strategies", "--json"],
        capture_output=True,
        text=True,
        cwd=rust_ai_dir,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get strategies from CLI: {result.stderr}")
    data = json.loads(result.stdout)
    return data["strategies"]


# 默认策略
DEFAULT_STRATEGY = "it2"

# 为了方便导入，提供一个别名
AVAILABLE_STRATEGIES = get_available_strategies()
