"""带暗子的测试局面

用于测试 it2 的 Chance 节点处理能力。
这些局面包含未揭开的暗子(X/x)，it2 应该能够：
1. 正确计算暗子的期望价值
2. 做出合理的揭子决策
3. 在概率不确定时做出稳健的选择

FEN 格式说明：
- X = 红方暗子
- x = 黑方暗子
- 被吃子部分需要平衡棋子总数
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HiddenPosition:
    """带暗子的测试局面"""

    id: str
    fen: str
    name: str
    description: str
    category: str


# =============================================================================
# 简单暗子局面（1-2个暗子）
# =============================================================================

_SIMPLE_HIDDEN_DATA = [
    # 红方有1个暗子，位置是车位
    # 红方：K + X (暗子在 a0) = 2，被吃 14
    # 黑方：k + a = 2，被吃 14
    (
        "3ak4/9/9/9/9/9/9/9/9/X2K5 RHHEECCAAPPPPP:rhheeccaappppp r r",
        "红方单暗",
        "红方有一个暗子在 a0 位置（车位），可能是任何未揭开的棋子",
        "单暗子",
    ),
    # 黑方有1个暗子
    # 红方：K + R = 2，被吃 14
    # 黑方：k + x (暗子在 a9) = 2，被吃 14
    # 注意：帅在 d0，将在 e9，不在同列
    (
        "x3k4/9/9/9/9/9/9/9/R8/3K5 RHHEECCAAPPPPP:rhheeccaappppp r r",
        "黑方单暗",
        "黑方有一个暗子在 a9 位置（车位）",
        "单暗子",
    ),
    # 双方各有1个暗子
    # 红方：K + X = 2，被吃 14
    # 黑方：k + x = 2，被吃 14
    # 注意：帅在 d0，将在 e9，不在同列
    (
        "x3k4/9/9/9/9/9/9/9/9/X2K5 RHHEECCAAPPPPP:rhheeccaappppp r r",
        "双方单暗",
        "双方各有一个暗子",
        "单暗子",
    ),
    # 红方有2个暗子
    # 红方：K + X + X = 3，被吃 13
    # 黑方：k + a = 2，被吃 14
    (
        "3ak4/9/9/9/9/9/9/9/9/XX1K5 RHEECCAAPPPPP:rhheeccaappppp r r",
        "红方双暗",
        "红方有两个暗子在 a0, b0 位置",
        "双暗子",
    ),
]


# =============================================================================
# 揭子决策局面（需要选择揭哪个暗子）
# =============================================================================

_REVEAL_DECISION_DATA = [
    # 红方有2个暗子，需要决定揭哪个
    # a0 和 i0 都是暗子，一个是车位一个是马位
    # 红方：K + X + X = 3，被吃 13
    # 黑方：k + a = 2，被吃 14
    (
        "3ak4/9/9/9/9/9/9/9/9/X2K4X RHEECCAAPPPPP:rhheeccaappppp r r",
        "揭子选择",
        "红方有两个暗子(a0和i0)，需要决定揭哪个更有利",
        "揭子决策",
    ),
    # 进攻性揭子：暗子在初始位置，揭后可威胁将
    # 红方：K + X (b0马位) = 2，被吃 14 (RHHEECCAAPPPPP)
    # 黑方：k = 1，被吃 15 (rhheeccaapppppa)
    # 帅在 e0，将在 d9，不同列
    (
        "3k5/9/9/9/9/9/9/9/9/1X2K4 RHHEECCAAPPPPP:rhheeccaapppppa r r",
        "进攻揭子",
        "红方暗子在 b0（马位），揭开后可能直接威胁黑将",
        "揭子决策",
    ),
]


# =============================================================================
# 中局暗子局面（较多棋子）
# =============================================================================

_MIDGAME_HIDDEN_DATA = [
    # 中局局面，双方各有几个暗子
    # 红方：K + R + X + X = 4，被吃 12 (HHEECCAAPPPP = 2+2+2+2+4)
    # 黑方：k + a + x + x = 4，被吃 12 (hheeccaapppp = 2+2+2+2+4)
    # 注意：帅在 d0，将在 e9，不在同列
    (
        "xx1ak4/9/9/9/9/9/9/9/R8/XX1K5 HHEECCAAPPPP:hheeccaapppp r r",
        "中局双暗",
        "双方各有两个暗子的中局",
        "中局暗子",
    ),
    # 更多暗子
    # 红方：K + X*4 = 5，被吃 11 (HEECCAAPPPP = 1+2+2+2+4)
    # 黑方：k + x*4 = 5，被吃 11 (heeccaapppp = 1+2+2+2+4)
    # 注意：帅在 e0，将在 d8，不在同列
    (
        "xxxx5/3k5/9/9/9/9/9/9/4K4/XXXX5 HEECCAAPPPP:heeccaapppp r r",
        "多暗子中局",
        "双方各有四个暗子",
        "中局暗子",
    ),
]


# =============================================================================
# 生成局面对象
# =============================================================================


def _make_positions(
    data: list[tuple[str, str, str, str]], prefix: str
) -> list[HiddenPosition]:
    """从数据生成 HiddenPosition 列表"""
    positions = []
    for i, (fen, name, desc, category) in enumerate(data, 1):
        positions.append(
            HiddenPosition(
                id=f"{prefix}{i:04d}",
                fen=fen,
                name=name,
                description=desc,
                category=category,
            )
        )
    return positions


# 生成各类局面
SIMPLE_HIDDEN_POSITIONS = _make_positions(_SIMPLE_HIDDEN_DATA, "SIMP")
REVEAL_DECISION_POSITIONS = _make_positions(_REVEAL_DECISION_DATA, "RVDEC")
MIDGAME_HIDDEN_POSITIONS = _make_positions(_MIDGAME_HIDDEN_DATA, "MID")

# 所有带暗子局面
ALL_HIDDEN_POSITIONS = (
    SIMPLE_HIDDEN_POSITIONS + REVEAL_DECISION_POSITIONS + MIDGAME_HIDDEN_POSITIONS
)


def get_position_by_id(pos_id: str) -> HiddenPosition | None:
    """按 ID 获取局面"""
    for pos in ALL_HIDDEN_POSITIONS:
        if pos.id == pos_id:
            return pos
    return None


def get_positions_by_category(category: str) -> list[HiddenPosition]:
    """按类别获取局面"""
    return [p for p in ALL_HIDDEN_POSITIONS if p.category == category]


# 导出
__all__ = [
    "HiddenPosition",
    "SIMPLE_HIDDEN_POSITIONS",
    "REVEAL_DECISION_POSITIONS",
    "MIDGAME_HIDDEN_POSITIONS",
    "ALL_HIDDEN_POSITIONS",
    "get_position_by_id",
    "get_positions_by_category",
]
