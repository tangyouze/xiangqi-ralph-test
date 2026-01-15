"""
中央日志配置

提供统一的日志目录常量和 logger 配置。
"""

from pathlib import Path

from loguru import logger

# 路径常量
PROJECT_ROOT = Path(__file__).parent.parent
BATTLE_LOGS_DIR = PROJECT_ROOT / "data" / "battle_logs"
RUNTIME_LOGS_DIR = PROJECT_ROOT / "logs"

# 确保目录存在
BATTLE_LOGS_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 配置 logger 输出到文件
logger.add(
    RUNTIME_LOGS_DIR / "app.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
)

__all__ = ["logger", "BATTLE_LOGS_DIR", "RUNTIME_LOGS_DIR"]
