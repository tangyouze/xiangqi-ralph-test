"""
统一的局面管理模块

提供局面类和管理接口，支持：
1. 通过 FEN 字符串指定起始局面
2. 通过局面 ID（如 END0001、JIEQI）选择局面
3. 标准开局也是局面的一种，只是 ID 特殊
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass
class GamePosition:
    """游戏局面"""

    id: str  # 局面 ID，如 "JIEQI", "REVEALED", "END0001"
    fen: str  # FEN 字符串
    name: str  # 局面名称
    category: str  # 分类
    has_hidden: bool  # 是否含暗子


# 预置开局 FEN
# 揭棋模式：暗子开局
JIEQI_FEN = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"
# 明棋模式：所有棋子开局即明（揭棋规则：象和士可以过河）
REVEALED_FEN = "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR -:- r r"

# 预置开局局面
JIEQI = GamePosition(
    id="JIEQI",
    fen=JIEQI_FEN,
    name="揭棋开局",
    category="standard",
    has_hidden=True,
)

REVEALED = GamePosition(
    id="REVEALED",
    fen=REVEALED_FEN,
    name="明棋开局",
    category="standard",
    has_hidden=False,
)


def _get_positions_file() -> Path:
    """获取 test_positions.json 文件路径"""
    # 尝试多个可能的路径
    candidates = [
        Path(__file__).parent.parent / "data" / "test_positions.json",
        Path("data/test_positions.json"),
        Path(__file__).resolve().parent.parent / "data" / "test_positions.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"Cannot find test_positions.json in any of: {candidates}")


@lru_cache(maxsize=1)
def _load_positions_from_file() -> list[GamePosition]:
    """从 test_positions.json 加载局面（带缓存）"""
    positions_file = _get_positions_file()
    with open(positions_file, encoding="utf-8") as f:
        data = json.load(f)

    positions = []
    for item in data.get("positions", []):
        positions.append(
            GamePosition(
                id=item["id"],
                fen=item["fen"],
                name=item["name"],
                category=item["category"],
                has_hidden=item["has_hidden"],
            )
        )
    return positions


def list_positions(
    category: str | None = None, has_hidden: bool | None = None
) -> list[GamePosition]:
    """列出所有局面

    Args:
        category: 可选，筛选指定分类的局面
        has_hidden: 可选，筛选是否含暗子的局面

    Returns:
        局面列表
    """
    # 从预置开局开始
    positions = [JIEQI, REVEALED]

    # 加载文件中的局面
    positions.extend(_load_positions_from_file())

    # 筛选
    if category is not None:
        positions = [p for p in positions if p.category == category]
    if has_hidden is not None:
        positions = [p for p in positions if p.has_hidden == has_hidden]

    return positions


def get_position(id_or_fen: str) -> GamePosition | None:
    """获取局面

    Args:
        id_or_fen: 局面 ID 或 FEN 字符串

    Returns:
        如果是已知 ID 则返回对应局面，如果是 FEN 则创建临时局面，否则返回 None
    """
    # 检查是否是已知 ID
    id_upper = id_or_fen.upper()

    # 检查预置开局
    if id_upper == "JIEQI":
        return JIEQI
    if id_upper == "REVEALED":
        return REVEALED

    # 检查文件中的局面
    for position in _load_positions_from_file():
        if position.id.upper() == id_upper:
            return position

    # 检查是否是有效的 FEN 字符串（包含空格和斜杠）
    if "/" in id_or_fen and " " in id_or_fen:
        # 尝试解析为 FEN
        parts = id_or_fen.split()
        if len(parts) >= 2:
            # 检查是否含暗子
            board_part = parts[0]
            has_hidden = "x" in board_part or "X" in board_part
            return GamePosition(
                id="CUSTOM",
                fen=id_or_fen,
                name="自定义局面",
                category="custom",
                has_hidden=has_hidden,
            )

    return None


def get_categories() -> list[str]:
    """获取所有分类"""
    positions = list_positions()
    categories = sorted(set(p.category for p in positions))
    return categories


def is_valid_position_id(id_str: str) -> bool:
    """检查是否是有效的局面 ID"""
    return get_position(id_str) is not None
