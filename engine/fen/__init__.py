"""
揭棋玩家视角 FEN (JFN v2)

设计目标：
1. 输入输出都用字符串，接口干净
2. FEN 包含完整信息（棋盘 + 被吃的子）
3. 从玩家视角表示，正确处理信息不对称

## 格式

    <棋盘> <被吃子> <回合> <视角>

### 棋盘部分

从 row 9 到 row 0（黑方底线到红方底线），每行用 `/` 分隔。

符号约定：
- 红方明子：K(将) R(车) H(马) C(炮) E(象) A(士) P(兵)
- 黑方明子：k r h c e a p
- 红方暗子：X
- 黑方暗子：x
- 空格：数字 (1-9)

### 被吃子部分

格式：`红方被吃:黑方被吃`

符号规则（用大小写区分明子/暗子）：
- 大写 `R` = 明子被吃（双方都知道）
- 小写 `r` = 暗子被吃，我知道身份（我吃的）
- `?` = 暗子被吃，我不知道身份
- 空被吃用 `-`

### 回合和视角

- 回合：`r`（红方走）或 `b`（黑方走）
- 视角：`r`（红方视角）或 `b`（黑方视角）

## 走法格式

- 明子走法：`a0a1`（从 a0 到 a1）
- 揭子走法：`+a0a1`（揭子并走）
- 揭子走法执行后：`+a0a1=R`（揭出了车）

## 示例

初始局面（红方视角）：
    xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r

中局（红方视角）：
    4k4/9/3R5/x1x3x1x/4X4/4x4/X1X3X1X/1C5C1/9/4K4 RP??:raHC r r
"""

# Types
from engine.fen.types import (
    CHAR_TO_COL,
    CHAR_TO_PIECE,
    COL_TO_CHAR,
    FULL_PIECE_COUNT,
    PIECE_SYMBOLS,
    PIECE_TO_CHAR,
    CapturedInfo,
    CapturedPieceInfo,
    FenPiece,
    FenState,
)

# Generate
from engine.fen.generate import to_fen

# Parse
from engine.fen.parse import move_to_str, parse_fen, parse_move

# Board conversion
from engine.fen.board import (
    apply_move_with_capture,
    create_board_from_fen,
    fen_from_pieces,
    get_legal_moves_from_fen,
    simulation_board_to_fen,
)

# Move
from engine.fen.move import apply_move_to_fen

# Validate
from engine.fen.validate import (
    _parse_captured_counts,
    fix_fen_captured,
    validate_fen,
)

# Display
from engine.fen.display import (
    EMPTY_SYMBOL,
    PIECE_SYMBOLS_CN,
    fen_to_ascii,
    fen_to_ascii_cn,
    fen_to_canvas_html,
)

__all__ = [
    # Types
    "PIECE_TO_CHAR",
    "CHAR_TO_PIECE",
    "COL_TO_CHAR",
    "CHAR_TO_COL",
    "PIECE_SYMBOLS",
    "FULL_PIECE_COUNT",
    "FenPiece",
    "CapturedPieceInfo",
    "CapturedInfo",
    "FenState",
    # Generate
    "to_fen",
    # Parse
    "parse_fen",
    "move_to_str",
    "parse_move",
    # Board
    "fen_from_pieces",
    "create_board_from_fen",
    "get_legal_moves_from_fen",
    "simulation_board_to_fen",
    "apply_move_with_capture",
    # Move
    "apply_move_to_fen",
    # Validate
    "validate_fen",
    "fix_fen_captured",
    "_parse_captured_counts",
    # Display
    "PIECE_SYMBOLS_CN",
    "EMPTY_SYMBOL",
    "fen_to_ascii",
    "fen_to_ascii_cn",
    "fen_to_canvas_html",
]
