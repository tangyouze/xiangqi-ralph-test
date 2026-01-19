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


# 经典残局（50 个，红方 10 步内必胜）
_CLASSIC_DATA = [
    # 1. 单车杀将
    ("4k4/9/9/9/9/9/9/9/4R4/4K4 -:- r r", "白脸将", "单车杀将"),
    ("3k5/9/9/9/9/9/9/9/3R5/4K4 -:- r r", "车赶将", "单车杀将"),
    ("4k4/4a4/9/9/9/9/9/4R4/9/4K4 -:- r r", "车入宫", "单车杀将"),
    ("3ak4/9/9/9/9/9/9/9/4R4/4K4 -:- r r", "逼士", "单车杀将"),
    ("4k4/9/4e4/9/9/9/9/4R4/9/4K4 -:- r r", "绕象", "单车杀将"),
    # 2. 双车杀将
    ("4k4/9/9/9/9/9/4R4/9/4R4/4K4 -:- r r", "双车错", "双车杀将"),
    ("3k5/9/9/9/9/9/3R5/9/4R4/4K4 -:- r r", "交替将", "双车杀将"),
    ("4k4/4a4/9/9/9/9/9/4R4/3R5/4K4 -:- r r", "破士", "双车杀将"),
    ("4k4/9/9/9/9/R3R4/9/9/9/4K4 -:- r r", "双车夹击", "双车杀将"),
    ("3ak4/4a4/9/9/9/9/9/3R5/4R4/4K4 -:- r r", "穿双士", "双车杀将"),
    # 3. 车马杀将
    ("4k4/9/9/9/9/4H4/9/4R4/9/4K4 -:- r r", "车马配合", "车马杀将"),
    ("3k5/9/9/9/4H4/9/9/3R5/9/4K4 -:- r r", "马控逃路", "车马杀将"),
    ("4k4/4a4/9/9/9/3H5/9/4R4/9/4K4 -:- r r", "马挂角", "车马杀将"),
    ("4k4/9/9/9/9/9/3H5/4R4/9/4K4 -:- r r", "闷杀", "车马杀将"),
    ("4k4/9/4e4/9/9/4H4/9/4R4/9/4K4 -:- r r", "马跳象", "车马杀将"),
    # 4. 车炮杀将
    ("4k4/9/9/9/4C4/9/9/4R4/9/4K4 -:- r r", "车炮配合", "车炮杀将"),
    ("3ak4/4a4/9/9/4C4/9/9/4R4/9/4K4 -:- r r", "铁门栓", "车炮杀将"),
    ("4k4/9/9/9/9/9/4C4/4R4/9/4K4 -:- r r", "炮架子", "车炮杀将"),
    ("4k4/4a4/9/9/4C4/9/9/3R5/9/4K4 -:- r r", "侧车攻", "车炮杀将"),
    ("3k5/4a4/9/9/9/4C4/9/3R5/9/4K4 -:- r r", "追将", "车炮杀将"),
    # 5. 车兵杀将
    ("4k4/9/9/4P4/9/9/9/4R4/9/4K4 -:- r r", "兵控逃路", "车兵杀将"),
    ("4k4/4a4/4P4/9/9/9/9/4R4/9/4K4 -:- r r", "兵破防", "车兵杀将"),
    ("3k5/9/9/3P5/9/9/9/3R5/9/4K4 -:- r r", "车兵赶将", "车兵杀将"),
    ("4k4/9/4e4/4P4/9/9/9/4R4/9/4K4 -:- r r", "兵堵象", "车兵杀将"),
    ("4k4/4a4/9/9/4P4/9/9/4R4/9/4K4 -:- r r", "兵进杀", "车兵杀将"),
    # 6. 马炮杀将
    ("4k4/9/9/9/9/9/4H4/4C4/9/4K4 -:- r r", "马后炮", "马炮杀将"),
    ("3k5/9/9/9/9/3H5/9/3C5/9/4K4 -:- r r", "侧杀", "马炮杀将"),
    ("4k4/4a4/9/9/9/4H4/9/4C4/9/4K4 -:- r r", "逼士", "马炮杀将"),
    ("4k4/9/9/9/9/4H4/4C4/9/9/4K4 -:- r r", "炮进", "马炮杀将"),
    ("4k4/9/4e4/9/9/4H4/9/4C4/9/4K4 -:- r r", "跳象", "马炮杀将"),
    # 7. 双马杀将
    ("4k4/9/9/9/9/3H5/4H4/9/9/4K4 -:- r r", "双马围困", "双马杀将"),
    ("3k5/9/9/9/9/2H6/3H5/9/9/4K4 -:- r r", "角杀", "双马杀将"),
    ("4k4/4a4/9/9/9/3H5/4H4/9/9/4K4 -:- r r", "破士", "双马杀将"),
    ("4k4/9/9/9/4H4/9/3H5/9/9/4K4 -:- r r", "马梯", "双马杀将"),
    ("4k4/9/9/9/3H5/4H4/9/9/9/4K4 -:- r r", "中控", "双马杀将"),
    # 8. 双炮杀将
    ("4k4/9/9/9/4C4/9/4C4/9/9/4K4 -:- r r", "重炮", "双炮杀将"),
    ("4k4/4a4/9/9/4C4/9/4C4/9/9/4K4 -:- r r", "士为架", "双炮杀将"),
    ("3k5/9/9/9/3C5/9/3C5/9/9/4K4 -:- r r", "侧重炮", "双炮杀将"),
    ("4k4/4a4/4a4/9/4C4/9/4C4/9/9/4K4 -:- r r", "双士架", "双炮杀将"),
    ("4k4/9/9/9/C8/9/4C4/9/9/4K4 -:- r r", "交叉炮", "双炮杀将"),
    # 9. 炮兵杀将
    ("4k4/9/4P4/9/4C4/9/9/9/9/4K4 -:- r r", "兵架炮", "炮兵杀将"),
    ("4k4/4a4/4P4/9/4C4/9/9/9/9/4K4 -:- r r", "逼杀", "炮兵杀将"),
    ("3k5/9/3P5/9/3C5/9/9/9/9/4K4 -:- r r", "侧攻", "炮兵杀将"),
    ("4k4/9/9/4P4/4C4/9/9/9/9/4K4 -:- r r", "兵进", "炮兵杀将"),
    ("4k4/4a4/9/4P4/4C4/9/9/9/9/4K4 -:- r r", "破士", "炮兵杀将"),
    # 10. 综合杀法
    ("4k4/9/9/9/4C4/4H4/9/4R4/9/4K4 -:- r r", "车马炮", "综合杀法"),
    ("3ak4/4a4/9/9/4C4/4H4/9/4R4/9/4K4 -:- r r", "破全防", "综合杀法"),
    ("4k4/9/9/4P4/4C4/4H4/9/9/9/4K4 -:- r r", "三子杀", "综合杀法"),
    ("4k4/4a4/4e4/9/4C4/4H4/9/4R4/9/4K4 -:- r r", "全攻", "综合杀法"),
    ("3k5/4a4/9/9/3C5/3H5/9/3R5/9/4K4 -:- r r", "侧攻", "综合杀法"),
]

# 生成带 ID 的经典残局列表
CLASSIC_ENDGAMES = [
    Endgame(id=f"END{i + 1:04d}", fen=fen, name=name, category=cat)
    for i, (fen, name, cat) in enumerate(_CLASSIC_DATA)
]

# 随机残局 FEN 数据（100 个，自动生成）
_RANDOM_FENS = [
    "1R1a5/9/e2k5/9/9/7rR/2c6/4AK3/9/H8 AEEHCCPPPPP:aehhrcppppp r r",
    "2H1a4/3k5/8e/3c5/3C5/4R4/7P1/5K3/2h6/4A1E2 AEHRCPPPP:aehrrcppppp r r",
    "2R4P1/4r4/5k3/9/9/4P4/9/5A3/3K5/9 AEEHHRCCPPP:aaeehhrccppppp r r",
    "2c2k3/1R7/9/9/9/4C3C/9/3A1A3/3K5/9 EEHHRPPPPP:aaeehhrrcppppp r r",
    "3a1k3/9/9/9/R1h6/6H2/9/9/3AKA3/9 EEHRCCPPPPP:aeehrrccppppp r r",
    "3a3c1/4k4/9/3C5/9/9/9/3K5/5A3/5C3 AEEHHRRPPPPP:aeehhrrcppppp r r",
    "3a5/3k5/9/9/9/6R1C/3H5/5A3/9/4K4 AEEHRCPPPPP:aeehhrrccppppp r r",
    "3a5/9/5k3/9/9/9/5C3/3KAC3/9/9 AEEHHRRPPPPP:aeehhrrccppppp r r",
    "3k2h2/9/5a2R/9/9/9/9/5K3/2rA5/8H AEEHRCCPPPPP:aeehrccppppp r r",
    "3k3C1/9/5a3/9/9/9/c8/4C4/4K4/9 AAEEHHRRPPPPP:aeehhrrcppppp r r",
    "3k4P/9/5a3/9/2C1C4/9/9/9/4K4/4A4 AEEHHRRPPPP:aeehhrrccppppp r r",
    "3k5/3a2H2/9/9/9/9/8R/2h1KA1r1/3A5/9 EEHRCCPPPPP:aeehrccppppp r r",
    "3k5/5H3/9/5C3/9/9/9/4K4/9/4AA3 EEHRRCPPPPP:aaeehhrrccppppp r r",
    "3k5/9/2P6/6P1C/9/9/2P6/4C4/5K3/9 AAEEHHRRPP:aaeehhrrccppppp r r",
    "3k5/9/9/8P/3P3P1/9/9/R8/7r1/5K3 AAEEHHRCCPP:aaeehhrccppppp r r",
    "3k5/9/9/P8/7R1/9/9/9/5A3/4KA3 EEHHRCCPPPP:aaeehhrrccppppp r r",
    "3ka4/9/1H4H2/9/9/9/9/9/9/5K3 AAEERRCCPPPPP:aeehhrrccppppp r r",
    "4C4/3k1P2c/3a5/3P3P1/2C6/9/3p5/9/9/3AK4 AEEHHRRPP:aeehhrrcpppp r r",
    "4C4/9/4k4/9/9/8C/9/5K3/5A3/5A3 EEHHRRPPPPP:aaeehhrrccppppp r r",
    "4R4/4a4/3k5/9/9/9/3R5/4K4/9/8r AAEEHHCCPPPPP:aeehhrccppppp r r",
    "4a2C1/9/3k5/9/9/9/9/9/9/C3K4 AAEEHHRRPPPPP:aeehhrrccppppp r r",
    "4a4/3k5/3R5/5P1p1/8P/1P7/9/5K3/3A5/4A4 EEHHRCCPP:aeehhrrccpppp r r",
    "4a4/4k4/9/9/3R5/9/9/5K3/3R5/3A5 AEEHHCCPPPPP:aeehhrrccppppp r r",
    "4a4/R4k3/8H/9/9/9/9/9/9/3KH4 AAEERCCPPPPP:aeehhrrccppppp r r",
    "4k1C2/4a4/6R2/9/9/9/9/9/9/c2K5 AAEEHHRCPPPPP:aeehhrrcppppp r r",
    "4k2C1/9/1hc6/9/9/9/3R5/9/3KH4/5A3 AEEHRCPPPPP:aaeehrrcppppp r r",
    "4k4/3C5/9/8H/9/5c3/9/5KH2/3A5/5A3 EERRCPPPPP:aaeehhrrcppppp r r",
    "4k4/3a5/9/9/4c4/9/9/C8/1C7/5K3 AAEEHHRRPPPPP:aeehhrrcppppp r r",
    "4k4/5a3/9/3r2R2/9/7R1/9/5A3/5K3/9 AEEHHCCPPPPP:aeehhrccppppp r r",
    "4k4/6C2/9/9/2H6/9/9/5K3/8H/9 AAEERRCPPPPP:aaeehhrrccppppp r r",
    "4k4/9/5a3/9/4C4/9/C8/9/9/3K5 AAEEHHRRPPPPP:aeehhrrccppppp r r",
    "4k4/9/5a3/9/9/9/3R5/4A4/H8/3A1K3 EEHRCCPPPPP:aeehhrrccppppp r r",
    "4k4/9/9/1C7/9/9/5C3/5A3/9/5K3 AEEHHRRPPPPP:aaeehhrrccppppp r r",
    "4k4/9/9/9/1h5H1/9/9/r2K3c1/5C3/5A1R1 AEEHRCPPPPP:aaeehrcppppp r r",
    "4k4/9/9/9/6R2/8R/9/5A3/5K3/9 AEEHHCCPPPPP:aaeehhrrccppppp r r",
    "4k4/9/C2H2H2/9/9/9/9/4AK3/3A5/9 EERRCPPPPP:aaeehhrrccppppp r r",
    "5H3/3k5/4h4/9/9/R8/9/9/9/4KA3 AEEHRCCPPPPP:aaeehrrccppppp r r",
    "5R3/4k4/8H/9/9/9/9/9/9/3K5 AAEEHRCCPPPPP:aaeehhrrccppppp r r",
    "5a2P/9/4k4/9/9/5P3/6P2/3K5/3p5/7R1 AAEEHHRCCPP:aeehhrrccpppp r r",
    "5a3/4c4/3H1k3/C8/9/9/9/9/4KA3/9 AEEHRRCPPPPP:aeehhrrcppppp r r",
    "5a3/5k3/9/4p3P/9/9/PPC6/7c1/3K5/9 AAEEHHRRCPP:aeehhrrcpppp r r",
    "5k3/1C7/9/6H2/9/6HC1/h8/3K1c3/4A4/4A4 EERRPPPPP:aaeehrrcppppp r r",
    "5k3/1H7/9/9/1c7/8h/9/9/C1RA1A3/4K4 EEHRCPPPPP:aaeehrrcppppp r r",
    "5k3/2R6/8P/1p7/9/9/5P3/5A3/1r2K4/3A5 EEHHRCCPPP:aaeehhrccpppp r r",
    "5k3/8C/9/9/9/8C/9/3A5/4K4/4c4 AEEHHRRPPPPP:aaeehhrrcppppp r r",
    "5k3/9/3P5/9/9/9/1R7/4K4/4A4/9 AEEHHRCCPPPP:aaeehhrrccppppp r r",
    "5k3/9/3a5/9/7r1/9/R8/3R1A3/4K4/4A4 EEHHCCPPPPP:aeehhrccppppp r r",
    "5k3/9/4a4/9/1R7/9/R8/3A5/3K5/3A5 EEHHCCPPPPP:aeehhrrccppppp r r",
    "5k3/c8/3a5/1C7/9/2C6/9/3K5/9/9 AAEEHHRRPPPPP:aeehhrrcppppp r r",
    "6e2/9/3k1a3/9/4C1P2/P2R5/9/1h1AE3c/4p4/5K3 AEHHRCPPP:aehrrcpppp r r",
    "7P1/1c1k4P/9/9/9/9/9/9/4KA3/2C2A3 EEHHRRCPPP:aaeehhrrcppppp r r",
    "8H/3k1R3/9/9/9/9/4C4/2h6/3AK4/5c3 AEEHRCPPPPP:aaeehrrcppppp r r",
    "8P/3Ck4/5a3/6CP1/7p1/4c4/9/3K1A3/4A4/9 EEHHRRPPP:aeehhrrcpppp r r",
    "8P/5k3/4R3e/9/9/9/c8/3K5/4A4/5A3 EEHHRCCPPPP:aaehhrrcppppp r r",
    "9/1H1k5/9/9/9/9/9/9/5K2h/7H1 AAEERRCCPPPPP:aaeehrrccppppp r r",
    "9/1R1k5/9/9/3R5/r8/9/4K4/9/9 AAEEHHCCPPPPP:aaeehhrccppppp r r",
    "9/2Ca5/2hk5/9/9/9/9/9/5K2H/1c1AA4 EEHRRCPPPPP:aeehrrcppppp r r",
    "9/2H6/4k1r2/2h6/9/9/6R2/1H1K5/9/9 AAEERCCPPPPP:aaeehrccppppp r r",
    "9/2r2k3/R8/6P2/9/9/2P6/4AA3/4Kp3/9 EEHHRCCPPP:aaeehhrccpppp r r",
    "9/3a5/4k4/9/2R6/7R1/9/9/3A1K3/4A4 EEHHCCPPPPP:aeehhrrccppppp r r",
    "9/3a5/5k3/9/6h2/4C4/9/4A1H2/3K5/1C7 AEEHRRPPPPP:aeehrrccppppp r r",
    "9/3k1a3/2C6/4H4/9/9/3c5/3AK3C/9/4A4 EEHRRPPPPP:aeehhrrcppppp r r",
    "9/3k2R2/3a5/9/9/3P5/2P6/4K4/9/9 AAEEHHRCCPPP:aeehhrrccppppp r r",
    "9/3k3PP/8C/9/7p1/9/P8/9/5K3/9 AAEEHHRRCPP:aaeehhrrccpppp r r",
    "9/3k5/3c5/9/2P5C/9/9/5A3/4A4/5K3 EEHHRRCPPPP:aaeehhrrcppppp r r",
    "9/3k5/9/8H/7H1/9/9/9/9/5K3 AAEERRCCPPPPP:aaeehhrrccppppp r r",
    "9/3k5/9/8R/3R5/9/9/4K4/5A3/9 AEEHHCCPPPPP:aaeehhrrccppppp r r",
    "9/4a2P1/4k3e/4C4/9/RP7/9/9/5K3/1r7 AAEEHHRCPPP:aehhrccppppp r r",
    "9/4a4/5k3/9/4P4/P8/5p3/3K5/9/R8 AAEEHHRCCPPP:aeehhrrccpppp r r",
    "9/4aC3/5k3/9/3C5/9/9/9/3K5/9 AAEEHHRRPPPPP:aeehhrrccppppp r r",
    "9/4k4/8C/9/7C1/9/9/5K3/4AA1c1/9 EEHHRRPPPPP:aaeehhrrcppppp r r",
    "9/4k4/9/9/3R5/4R4/9/3K5/3A5/4A4 EEHHCCPPPPP:aaeehhrrccppppp r r",
    "9/4k4/9/9/7P1/9/9/2r6/1p1K1A1R1/9 AEEHHRCCPPPP:aaeehhrccpppp r r",
    "9/4k4/9/9/8C/8c/9/3RC4/3K1A3/9 AEEHHRPPPPP:aaeehhrrcppppp r r",
    "9/4k4/9/9/8H/9/5H3/9/9/2hK5 AAEERRCCPPPPP:aaeehrrccppppp r r",
    "9/4k4/9/9/9/3h3H1/R8/9/7r1/3K5 AAEEHRCCPPPPP:aaeehrccppppp r r",
    "9/4k4/9/9/9/6R2/9/2R6/5K3/9 AAEEHHCCPPPPP:aaeehhrrccppppp r r",
    "9/4ka3/2C6/C8/9/2p6/4P4/5K3/5A3/6c2 AEEHHRRPPPP:aeehhrrcpppp r r",
    "9/4kc3/5a3/4R1Cr1/5C3/9/9/9/3A5/3K5 AEEHHRPPPPP:aeehhrcppppp r r",
    "9/5C3/4k4/9/9/9/9/C4K3/9/5A3 AEEHHRRPPPPP:aaeehhrrccppppp r r",
    "9/5P3/C2k5/9/9/9/C8/5K3/8p/9 AAEEHHRRPPPP:aaeehhrrccpppp r r",
    "9/5h3/3k5/9/9/5R3/9/9/9/H4K3 AAEEHRCCPPPPP:aaeehrrccppppp r r",
    "9/5k3/1r7/9/3R4C/9/9/9/9/3HK4 AAEEHRCPPPPP:aaeehhrccppppp r r",
    "9/5k3/5P3/7c1/9/1C2P4/8P/3K5/2C6/9 AAEEHHRRPP:aaeehhrrcppppp r r",
    "9/5k3/9/9/9/9/8P/2RK5/9/9 AAEEHHRCCPPPP:aaeehhrrccppppp r r",
    "9/5k3/9/9/9/9/9/4A4/3KRR3/3A5 EEHHCCPPPPP:aaeehhrrccppppp r r",
    "9/5k3/9/9/9/P8/7p1/3RA4/9/4K4 AEEHHRCCPPPP:aaeehhrrccpppp r r",
    "9/9/3k1a3/9/7P1/9/9/5A3/4K4/3A4R EEHHRCCPPPP:aeehhrrccppppp r r",
    "9/9/3k2P2/8r/5P1p1/9/6R2/9/4K4/9 AAEEHHRCCPPP:aaeehhrccpppp r r",
    "9/9/3k5/2h6/2R6/9/9/4K4/4r4/H1H6 AAEERCCPPPPP:aaeehrccppppp r r",
    "9/9/3kP4/9/6P2/5P2R/9/3AAK3/p8/9 EEHHRCCPP:aaeehhrrccpppp r r",
    "9/9/4k4/9/9/2C6/9/5K3/9/1H5R1 AAEEHRCPPPPP:aaeehhrrccppppp r r",
    "9/9/5k3/4H4/9/9/9/3HA4/9/4K4 AEERRCCPPPPP:aaeehhrrccppppp r r",
    "9/PR3k3/7Pe/9/9/4H4/9/3KE4/4A2p1/2R6 AEHCCPPP:aaehhrrccpppp r r",
    "9/R2k5/9/8c/9/9/9/9/4K4/2C1A4 AEEHHRCPPPPP:aaeehhrrcppppp r r",
    "C8/3a5/5k3/2h6/9/9/9/4A4/3AK4/2H3c2 EEHRRCPPPPP:aeehrrcppppp r r",
    "H6h1/1C7/3k5/9/9/9/9/5A3/5K3/1R2A4 EEHRCPPPPP:aaeehrrccppppp r r",
    "P8/1P3k2R/9/9/1p7/9/6P2/9/9/3KA4 AEEHHRCCPP:aaeehhrrccpppp r r",
    "P8/5k3/1P2R4/9/6e2/8c/7r1/2H1A4/3A5/3K5 EEHRCCPPP:aaehhrcppppp r r",
    "c8/4ka3/9/8H/9/9/9/1C7/9/3KA2R1 AEEHRCPPPPP:aeehhrrcppppp r r",
]

# 生成带 ID 的随机残局列表（ID 从 END0051 开始）
RANDOM_ENDGAMES = [
    Endgame(id=f"END{i + 51:04d}", fen=fen, name=f"随机残局{i + 1}", category="随机生成")
    for i, fen in enumerate(_RANDOM_FENS)
]

# 所有残局
ALL_ENDGAMES = CLASSIC_ENDGAMES + RANDOM_ENDGAMES


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
