"""象棋残局库

包含经典残局和随机残局 FEN，用于 AI 训练和测试。
"""

from __future__ import annotations

from dataclasses import dataclass

# 从 fen 模块导入 utility 函数
from engine.fen import (
    EMPTY_SYMBOL,
    FULL_PIECE_COUNT,
    PIECE_SYMBOLS,
    PIECE_SYMBOLS_CN,
    fen_to_ascii,
    fen_to_ascii_cn,
    validate_fen,
)

# 重新导出供外部使用
__all__ = [
    "PIECE_SYMBOLS",
    "PIECE_SYMBOLS_CN",
    "EMPTY_SYMBOL",
    "FULL_PIECE_COUNT",
    "validate_fen",
    "fen_to_ascii",
    "fen_to_ascii_cn",
    "Endgame",
    "CLASSIC_ENDGAMES",
    "RANDOM_ENDGAMES",
    "ALL_ENDGAMES",
    "get_endgame_by_id",
    "get_classic_endgames",
    "get_random_endgames",
    "get_all_endgames",
]


@dataclass
class Endgame:
    """残局数据"""

    id: str  # END0001, END0002, ...
    fen: str
    name: str
    category: str


# 经典残局（28 个有效，红方走，黑方未被将军）
_CLASSIC_DATA = [
    # 单车杀将
    ("4k4/4a4/9/9/9/9/9/4R4/9/4K4 -:- r r", "车入宫", "单车杀将"),
    ("4k4/9/4e4/9/9/9/9/4R4/9/4K4 -:- r r", "绕象", "单车杀将"),
    # 双车杀将
    ("4k4/4a4/9/9/9/9/9/4R4/3R5/4K4 -:- r r", "破士", "双车杀将"),
    ("3ak4/4a4/9/9/9/9/9/3R5/4R4/4K4 -:- r r", "穿双士", "双车杀将"),
    # 车马杀将
    ("4k4/9/9/9/9/4H4/9/4R4/9/4K4 -:- r r", "车马配合", "车马杀将"),
    ("4k4/4a4/9/9/9/3H5/9/4R4/9/4K4 -:- r r", "马挂角", "车马杀将"),
    ("4k4/9/4e4/9/9/4H4/9/4R4/9/4K4 -:- r r", "马跳象", "车马杀将"),
    # 车炮杀将
    ("4k4/9/9/9/4C4/9/9/4R4/9/4K4 -:- r r", "车炮配合", "车炮杀将"),
    ("4k4/9/9/9/9/9/4C4/4R4/9/4K4 -:- r r", "炮架子", "车炮杀将"),
    # 车兵杀将
    ("4k4/9/9/4P4/9/9/9/4R4/9/4K4 -:- r r", "兵控逃路", "车兵杀将"),
    ("4k4/4a4/4P4/9/9/9/9/4R4/9/4K4 -:- r r", "兵破防", "车兵杀将"),
    ("3k5/9/9/3P5/9/9/9/3R5/9/4K4 -:- r r", "车兵赶将", "车兵杀将"),
    ("4k4/9/4e4/4P4/9/9/9/4R4/9/4K4 -:- r r", "兵堵象", "车兵杀将"),
    ("4k4/4a4/9/9/4P4/9/9/4R4/9/4K4 -:- r r", "兵进杀", "车兵杀将"),
    # 马炮杀将
    ("4k4/4a4/9/9/9/4H4/9/4C4/9/4K4 -:- r r", "逼士", "马炮杀将"),
    ("4k4/9/4e4/9/9/4H4/9/4C4/9/4K4 -:- r r", "跳象", "马炮杀将"),
    # 双马杀将
    ("4k4/9/9/9/9/3H5/4H4/9/9/4K4 -:- r r", "双马围困", "双马杀将"),
    ("3k5/9/9/9/9/2H6/3H5/9/9/4K4 -:- r r", "角杀", "双马杀将"),
    ("4k4/4a4/9/9/9/3H5/4H4/9/9/4K4 -:- r r", "破士", "双马杀将"),
    ("4k4/9/9/9/4H4/9/3H5/9/9/4K4 -:- r r", "马梯", "双马杀将"),
    ("4k4/9/9/9/3H5/4H4/9/9/9/4K4 -:- r r", "中控", "双马杀将"),
    # 双炮杀将
    ("4k4/4a4/4a4/9/4C4/9/4C4/9/9/4K4 -:- r r", "双士架", "双炮杀将"),
    ("4k4/9/9/9/C8/9/4C4/9/9/4K4 -:- r r", "交叉炮", "双炮杀将"),
    # 炮兵杀将
    ("4k4/4a4/4P4/9/4C4/9/9/9/9/4K4 -:- r r", "逼杀", "炮兵杀将"),
    ("4k4/4a4/9/4P4/4C4/9/9/9/9/4K4 -:- r r", "破士", "炮兵杀将"),
    # 综合杀法
    ("4k4/9/9/9/4C4/4H4/9/4R4/9/4K4 -:- r r", "车马炮", "综合杀法"),
    ("4k4/4a4/4e4/9/4C4/4H4/9/4R4/9/4K4 -:- r r", "全攻", "综合杀法"),
    ("3k5/4a4/9/9/3C5/3H5/9/3R5/9/4K4 -:- r r", "侧攻", "综合杀法"),
]

# Mate Distance 测试残局（简单局面，用于验证 AI 选择最快将死路径）
_MATE_DISTANCE_DATA = [
    # 单车残局 - 不同位置（黑将在 d9，避免同列）
    ("3k5/9/9/9/9/9/9/9/R8/4K4 -:- r r", "车a1", "单车测试"),
    ("3k5/9/9/9/9/9/9/9/1R7/4K4 -:- r r", "车b1", "单车测试"),
    ("3k5/9/9/9/9/9/9/9/2R6/4K4 -:- r r", "车c1", "单车测试"),
    ("3k5/9/9/9/9/9/4R4/9/9/4K4 -:- r r", "车e3", "单车测试"),
    ("3k5/9/9/9/9/9/9/6R2/9/4K4 -:- r r", "车g2", "单车测试"),
    ("3k5/9/9/9/9/9/9/9/8R/4K4 -:- r r", "车i1", "单车测试"),
    # 单车残局 - 快速将死
    ("3k5/9/9/9/9/9/R8/9/9/4K4 -:- r r", "车a3", "单车快杀"),
    ("4k4/R8/9/9/9/9/9/9/9/3K5 -:- r r", "车a8近将", "单车快杀"),
    # 单马残局（黑将在 d9，避免被马直接吃）
    ("3k5/9/9/3H5/9/9/9/9/9/4K4 -:- r r", "马d6", "单马测试"),
    ("3k5/9/9/9/9/4H4/9/9/9/4K4 -:- r r", "马e4", "单马测试"),
    ("3k5/9/9/9/9/9/9/9/9/H3K4 -:- r r", "马a0角落", "单马测试"),
    ("3k5/2H6/9/9/9/9/9/9/9/4K4 -:- r r", "马c8近将", "单马测试"),
    # 简单必杀局面（有士挡路，避免直接将军）
    ("4k4/4a4/9/9/9/9/9/4R4/9/4K4 -:- r r", "车入宫快杀", "简单必杀"),
    ("3k5/9/9/9/9/9/9/4R4/9/4K4 -:- r r", "车对空将", "简单必杀"),
    ("3k5/9/9/9/4R4/9/9/9/9/4K4 -:- r r", "车e5中心", "简单必杀"),
    # 单马困毙（经典残局）
    ("3k5/9/1H7/9/9/9/9/9/9/4K4 -:- r r", "单马困毙", "单马困毙"),
]

# 生成带 ID 的经典残局列表
CLASSIC_ENDGAMES = [
    Endgame(id=f"END{i + 1:04d}", fen=fen, name=name, category=cat)
    for i, (fen, name, cat) in enumerate(_CLASSIC_DATA)
]

# 生成带 ID 的 Mate Distance 测试残局列表（ID 从 END0029 开始）
MATE_DISTANCE_ENDGAMES = [
    Endgame(id=f"END{i + 29:04d}", fen=fen, name=name, category=cat)
    for i, (fen, name, cat) in enumerate(_MATE_DISTANCE_DATA)
]

# 随机残局 FEN 数据（100 个，自动生成，多样化子力分布）
_RANDOM_FENS = [
    "5k3/9/9/9/9/3H5/2P6/9/2pEK4/9 AACCEHPPPPRR:aacceehhpppprr r r",
    "H3eC3/9/3k4r/p3h1e2/9/9/9/4pK3/c8/9 AACEEHPPPPPRR:aachpppr r r",
    "3k1h2h/8e/9/6e2/9/9/P1p6/4Kc3/9/9 AACCEEHHPPPPRR:aacpppprr r r",
    "5a2e/3r5/5k3/1Pp6/1H7/4c4/9/4Ah3/3h5/4K4 ACCEEHPPPPRR:aceppppr r r",
    "6c2/3k5/9/2r6/p8/7p1/9/9/5H2R/4KA3 ACCEEHPPPPPR:aaceehhpppr r r",
    "5k3/4P4/8H/R8/9/3C1r3/9/9/5K3/3EA4 ACEHPPPPR:aacceehhpppppr r r",
    "9/3k4H/1P7/9/9/1E7/9/CR7/6E2/5K1H1 AACPPPPR:aacceehhppppprr r r",
    "7R1/3P5/3k5/7P1/9/1E7/9/5K3/2C2A3/3A5 CEHHPPPR:aacceehhppppprr r r",
    "4k4/8C/9/9/8c/3p5/9/8E/1H3K3/7h1 AACEHPPPPPRR:aaceehpppprr r r",
    "4k4/3P5/7P1/7C1/3R5/6p1E/6c2/5K1C1/9/9 AAEHHPPPR:aaceehhpppprr r r",
    "1R7/5k3/9/7P1/9/5p3/4P4/9/4K4/7r1 AACCEEHHPPPR:aacceehhppppr r r",
    "9/4a4/3k5/9/8p/3p4P/9/9/4K4/4E4 AACCEHHPPPPRR:acceehhppprr r r",
    "5k3/9/1C3a1P1/7r1/7e1/9/9/3K5/9/9 AACEEHHPPPPRR:accehhpppppr r r",
    "4a4/9/5k3/9/9/5Cpc1/1P7/p3E2r1/5K3/5p3 AACEHHPPPPRR:aceehhppr r r",
    "PP5e1/3k3c1/P3a4/9/9/9/9/p4K3/2hp5/3p5 AACCEEHHPPRR:acehpprr r r",
    "P2kC4/9/1C3c1h1/9/9/R1H6/8P/9/9/5K3 AAEEHPPPR:aaceehppppprr r r",
    "3k1P1e1/3a5/3a5/9/9/9/9/3K5/4rA1R1/9 ACCEEHHPPPPR:ccehhpppppr r r",
    "4k4/9/9/9/4eh3/6P2/1C3p3/5A3/3K5/1p2E4 ACEHHPPPPRR:aaccehppprr r r",
    "3C5/5k3/6PH1/9/9/9/9/3AR4/4E4/E2K5 ACHPPPPR:aacceehhppppprr r r",
    "5a3/1P3H2r/c4k3/5h3/6e2/9/9/4K4/8C/9 AACEEHPPPPRR:acehpppppr r r",
    "2R2a3/4k4/9/6e2/2e3h2/3P2E2/2C6/9/5H3/3K1R3 AACEHPPPP:acchppppprr r r",
    "9/C3k4/9/1P6H/1R2P4/9/9/4A4/5K3/8c ACEEHPPPR:aaceehhppppprr r r",
    "9/5k3/1P7/9/4p4/2C6/5C2P/2p6/3A5/3K5 AEEHHPPPRR:aacceehhppprr r r",
    "7P1/3a5/4k4/9/7c1/9/4r4/5K3/9/5A3 ACCEEHHPPPPRR:aceehhpppppr r r",
    "3k5/3e1r3/3R5/3r5/3pC4/1P4h2/8p/5K3/9/3A5 ACEEHHPPPPR:aaccehppp r r",
    "4k4/8C/6P2/9/9/3PP1H2/9/9/4K4/9 AACEEHPPRR:aacceehhppppprr r r",
    "4kH3/1P7/2Ra3C1/9/8P/9/9/5K3/5A2E/9 ACEHPPPR:acceehhppppprr r r",
    "5a3/4k4/9/8e/9/9/9/5A3/7E1/5K3 ACCEHHPPPPPRR:accehhppppprr r r",
    "9/4k4/3a5/9/2P1C4/9/9/3KA4/9/3A5 CEEHHPPPPRR:acceehhppppprr r r",
    "9/5k3/2P6/9/4p1P2/9/9/9/5A1C1/4K4 ACEEHHPPPRR:aacceehhpppprr r r",
    "3kh4/2P6/6e2/7P1/1pr6/9/1H7/9/2R1K3p/6E2 AACCEHPPPR:aaccehpppr r r",
    "4k4/5a3/8P/7P1/9/9/4E4/9/C8/4K4 AACEHHPPPRR:acceehhppppprr r r",
    "4P3P/4k4/9/9/9/9/3EP4/3E5/4A4/4AK3 CCHHPPRR:aacceehhppppprr r r",
    "9/9/P3k4/9/2p6/9/9/h8/5A1C1/p2K5 ACEEHHPPPPRR:aacceehppprr r r",
    "3r5/2P1k1C2/2e1a4/9/4c4/9/8p/9/6p2/3CK4 AAEEHHPPPPRR:acehhpppr r r",
    "9/4k4/1c7/4P4/1p7/7p1/6H2/H2h5/9/3pAK3 ACCEEPPPPRR:aaceehpprr r r",
    "9/3k1C3/9/9/9/5H3/2P6/5K3/4A1EH1/9 ACEPPPPRR:aacceehhppppprr r r",
    "5k3/3c5/3R5/c8/9/9/9/h3K4/5A1E1/9 ACCEHHPPPPPR:aaeehppppprr r r",
    "3k2P2/9/9/1P5P1/9/9/9/9/4K4/1E5R1 AACCEHHPPR:aacceehhppppprr r r",
    "5k3/R4a3/2Pe5/9/3r5/9/9/1p2c4/2pK2E1h/9 AACCEHHPPPPR:acehpppr r r",
    "5k3/9/4a4/5p3/4P4/9/6p2/9/4K3h/4c4 AACCEEHHPPPPRR:aceehppprr r r",
    "3k2P2/4P4/1h7/9/9/8R/5E2p/4K4/3p5/5A3 ACCEHHPPPR:aacceehppprr r r",
    "4k3r/3a1H3/6P2/6p2/1H7/8R/6P2/2hK5/9/6p2 AACCEEPPPR:acceehpppr r r",
    "9/3ak4/9/9/6P2/3E2hC1/9/9/3K5/9 AACEHHPPPPRR:acceehppppprr r r",
    "2r6/3k5/1e7/9/2p6/4c1p2/9/5K3/3A5/9 ACCEEHHPPPPPRR:aacehhpppr r r",
    "2h2k3/9/6P2/9/9/9/7h1/1CC1KA3/9/9 AEEHHPPPPRR:aacceeppppprr r r",
    "8H/4k4/6P2/7P1/9/3E3R1/9/5K3/1C7/9 AACEHPPPR:aacceehhppppprr r r",
    "P3c4/4k4/5a3/9/p4cee1/9/9/3p1K3/9/9 AACCEEHHPPPPRR:ahhppprr r r",
    "3k5/9/9/2p1e2p1/9/9/9/5Kr2/9/h5r2 AACCEEHHPPPPPRR:aaccehppp r r",
    "9/5C3/1Hr1k4/5e3/3P3P1/1p4p2/9/5p3/9/5K3 AACEEHPPPRR:aaccehhppr r r",
    "3a5/4e4/4ck3/9/2c2e3/9/1r7/4K4/9/9 AACCEEHHPPPPPRR:ahhpppppr r r",
    "3k1r3/9/2h6/7p1/2r6/9/9/c4K2p/9/9 AACCEEHHPPPPPRR:aaceehppp r r",
    "9/9/4k1P2/9/9/5R3/9/3K1A3/5H3/9 ACCEEHPPPPR:aacceehhppppprr r r",
    "5k3/2r4e1/1c7/5P3/9/3P1h3/3p5/h8/9/1E1K5 AACCEHHPPPRR:aaceppppr r r",
    "9/3ak4/4H4/1p7/9/2P6/1C7/1c3K3/7p1/9 AACEEHPPPPRR:aceehhppprr r r",
    "9/5k3/9/7P1/3c3e1/5cP2/9/6E2/4K4/2R3p2 AACCEHHPPPR:aaehhpppprr r r",
    "3k5/2P6/3P5/1C7/9/3H5/9/2p6/3K5/p8 AACEEHPPPRR:aacceehhppprr r r",
    "5a3/4k4/3C5/1P7/3P2hr1/4P4/9/6p2/4KH3/4A4 ACEEHPPRR:acceehppppr r r",
    "5a3/4ek3/5e3/3h5/3P5/p6P1/9/4p4/3K5/2E1h4 AACCEHHPPPRR:accppprr r r",
    "P3k4/9/P8/2p6/6C2/4c4/5H3/3A5/9/3K2r2 ACEEHPPPRR:aaceehhppppr r r",
    "6e2/C8/1h1k1a2e/1P4P2/2p2H3/9/3P5/9/5K3/9 AACEEHPPRR:acchpppprr r r",
    "P1HP1e2c/3k5/9/9/9/4p4/9/5K3/5p3/9 AACCEEHPPPRR:aacehhppprr r r",
    "h8/6P2/5k3/1p5C1/4p2h1/4P4/8p/4K4/1H7/9 AACEEHPPPRR:aacceepprr r r",
    "3k5/9/5P3/P8/9/9/9/9/5K3/4AA3 CCEEHHPPPRR:aacceehhppppprr r r",
    "9/H3k2e1/4a4/8P/9/1P4P2/3P5/9/R2K5/2h6 AACCEEHPR:accehppppprr r r",
    "9/9/2ek5/7p1/H8/3p1P3/9/9/4K4/9 AACCEEHPPPPRR:aaccehhppprr r r",
    "9/1C3k3/1h7/9/9/7c1/9/3E2p2/2pK5/p8 AACEHHPPPPPRR:aaceehpprr r r",
    "3ak1e2/6h2/9/p8/9/9/r2c5/7p1/9/3K5 AACCEEHHPPPPPRR:acehpppr r r",
    "9/3k5/4a4/1e7/9/9/9/7E1/3Ap4/3K5 ACCEHHPPPPPRR:accehhpppprr r r",
    "5k3/9/9/9/6p2/C8/9/3A5/4K4/6E2 ACEHHPPPPPRR:aacceehhpppprr r r",
    "9/5k3/9/9/8P/6R2/7r1/3K5/4A4/9 ACCEEHHPPPPR:aacceehhpppppr r r",
    "4a4/4k4/9/3e5/9/9/2p6/9/4pK3/9 AACCEEHHPPPPPRR:accehhppprr r r",
    "9/4k4/4a4/5P3/rP7/5R3/3C4p/4hA3/9/3HK4 ACEEHPPPR:acceehppppr r r",
    "9/3k1r3/3ea4/9/2p6/2E6/9/9/h3K4/9 AACCEHHPPPPPRR:accehppppr r r",
    "3k1a3/5a3/1e7/3h5/9/9/9/3p5/5K1r1/9 AACCEEHHPPPPPRR:ccehppppr r r",
    "9/5r3/4k4/9/2C1pP3/9/2c1p2E1/2R6/5K3/9 AACEHHPPPPR:aaceehhpppr r r",
    "9/4k4/9/2h5H/e8/7H1/1P1p1c3/7pp/5K3/1h7 AACCEEPPPPRR:aacepprr r r",
    "R3P4/5k3/7P1/5e3/9/H8/9/4A4/3A1K3/9 CCEEHPPPR:aaccehhppppprr r r",
    "3e5/3k1c3/9/1e7/9/3E5/4P2P1/9/4K4/4A4 ACCEHHPPPRR:aachhppppprr r r",
    "5k3/1P7/9/1P7/e2P5/9/9/4RA3/9/3K3E1 ACCEHHPPR:aaccehhppppprr r r",
    "6P2/4k4/9/9/5P3/9/7H1/9/4A4/4K4 ACCEEHPPPRR:aacceehhppppprr r r",
    "1P7/9/5k3/9/9/9/9/6r2/4AH3/4K4 ACCEEHPPPPRR:aacceehhpppppr r r",
    "9/3a1k1P1/6H2/3p5/e8/9/9/4K4/9/9 AACCEEHPPPPRR:accehhpppprr r r",
    "3k5/5a3/9/9/8c/1r7/8p/1p7/1p7/5K3 AACCEEHHPPPPPRR:aceehhppr r r",
    "1P7/5k3/3C5/9/5P2P/9/9/1p1K5/8R/3A5 ACEEHHPPR:aacceehhpppprr r r",
    "9/5k3/e4a3/2p2P2h/8p/9/9/3K5/9/9 AACCEEHHPPPPRR:accehppprr r r",
    "4a4/4kh3/8r/3P1r3/9/3p5/2E5p/9/9/2hK5 AACCEHHPPPPRR:acceeppp r r",
    "8P/4ak3/3c5/3P4r/9/9/9/3AA4/1C1K5/2H3p2 CEEHPPPRR:aceehhppppr r r",
    "C3k4/7R1/6P2/9/9/2H6/1E7/3K3R1/9/9 AACEHPPPP:aacceehhppppprr r r",
    "5k3/9/9/9/1C7/6R2/9/9/4K2E1/8R AACEHHPPPPP:aacceehhppppprr r r",
    "8c/7P1/3k5/9/1P7/2E6/3C5/3A5/4KA3/9 CEHHPPPRR:aaceehhppppprr r r",
    "3a1k3/3a5/4hP3/3RpP3/3P5/1H7/9/3c5/9/5K3 AACCEEHPPR:ceehpppprr r r",
    "r3k4/9/2P6/1c7/7R1/9/9/9/1H7/3K5 AACCEEHPPPPR:aaceehhpppppr r r",
    "8h/3k1c1c1/9/5P2C/1p6e/9/3r4p/9/9/3K5 AACEEHHPPPPRR:aaehpppr r r",
    "9/3k5/9/7P1/2P1C4/9/6Cp1/RE3K3/4h3H/2r6 AAEHPPPR:aacceehppppr r r",
    "9/8R/5k3/7P1/5P3/2E6/9/9/9/3K5 AACCEHHPPPR:aacceehhppppprr r r",
    "5k3/7e1/3a5/9/4PH3/E6P1/7P1/4pK2p/5A3/9 ACCEHPPRR:accehhppprr r r",
    "9/3a4P/3k5/1r5h1/3P4e/3c5/9/3K4H/9/1p1p5 AACCEEHPPPRR:acehpppr r r",
    "9/4k4/9/7H1/9/9/6P2/6E2/3K2H2/1E1A5 ACCPPPPRR:aacceehhppppprr r r",
    "5a1e1/3k5/7r1/9/P1H6/8P/1cH6/9/8C/p4K3 AACEEPPPRR:acehhppppr r r",
]

# 生成带 ID 的随机残局列表（ID 从 END0051 开始）
RANDOM_ENDGAMES = [
    Endgame(id=f"END{i + 51:04d}", fen=fen, name=f"随机残局{i + 1}", category="随机生成")
    for i, fen in enumerate(_RANDOM_FENS)
]

# 所有残局
ALL_ENDGAMES = CLASSIC_ENDGAMES + MATE_DISTANCE_ENDGAMES + RANDOM_ENDGAMES


# ID 索引
_ENDGAME_BY_ID: dict[str, Endgame] = {e.id: e for e in ALL_ENDGAMES}


def get_endgame_by_id(endgame_id: str) -> Endgame | None:
    """通过 ID 获取残局"""
    return _ENDGAME_BY_ID.get(endgame_id)


def get_classic_endgames() -> list[Endgame]:
    """获取经典残局列表"""
    return CLASSIC_ENDGAMES.copy()


def get_random_endgames() -> list[Endgame]:
    """获取随机残局列表"""
    return RANDOM_ENDGAMES.copy()


def get_all_endgames() -> list[Endgame]:
    """获取所有残局列表"""
    return ALL_ENDGAMES.copy()


if __name__ == "__main__":
    print(f"Classic endgames: {len(CLASSIC_ENDGAMES)}")
    print(f"Random endgames: {len(RANDOM_ENDGAMES)}")
    print(f"Total: {len(ALL_ENDGAMES)}")
