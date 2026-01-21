"""FEN 验证和修复"""

from __future__ import annotations

from engine.fen.types import FULL_PIECE_COUNT, PIECE_SYMBOLS
from engine.types import Color


def _parse_board_positions(board_str: str) -> dict[tuple[int, int], str]:
    """解析棋盘字符串为位置->棋子的字典

    Args:
        board_str: FEN 棋盘部分

    Returns:
        {(row, col): piece_char} 字典，row 0-9 (0是底部红方)，col 0-8
    """
    positions: dict[tuple[int, int], str] = {}
    rows = board_str.split("/")
    for row_idx, row in enumerate(rows):
        row_num = 9 - row_idx  # FEN 从上到下，转为从下到上
        col = 0
        for char in row:
            if char.isdigit():
                col += int(char)
            else:
                positions[(row_num, col)] = char
                col += 1
    return positions


def _can_red_attack_position(
    positions: dict[tuple[int, int], str], target_row: int, target_col: int
) -> tuple[bool, str]:
    """检查红方是否能攻击到指定位置

    Args:
        positions: 棋盘位置字典
        target_row: 目标行 (0-9)
        target_col: 目标列 (0-8)

    Returns:
        (can_attack, attacker_description)
    """
    target = (target_row, target_col)

    for (row, col), piece in positions.items():
        # 只检查红方棋子（大写）
        if not piece.isupper():
            continue

        # 车 - 直线攻击
        if piece == "R":
            if row == target_row:  # 同行
                # 检查中间无子
                min_col, max_col = min(col, target_col), max(col, target_col)
                blocked = False
                for c in range(min_col + 1, max_col):
                    if (row, c) in positions:
                        blocked = True
                        break
                if not blocked:
                    return True, f"车({row},{col})"
            elif col == target_col:  # 同列
                min_row, max_row = min(row, target_row), max(row, target_row)
                blocked = False
                for r in range(min_row + 1, max_row):
                    if (r, col) in positions:
                        blocked = True
                        break
                if not blocked:
                    return True, f"车({row},{col})"

        # 马 - 日字跳（需检查蹩腿）
        elif piece == "H":
            # 马的 8 个可能位置及对应的蹩腿位置
            horse_moves = [
                ((2, 1), (1, 0)),  # 上右
                ((2, -1), (1, 0)),  # 上左
                ((-2, 1), (-1, 0)),  # 下右
                ((-2, -1), (-1, 0)),  # 下左
                ((1, 2), (0, 1)),  # 右上
                ((-1, 2), (0, 1)),  # 右下
                ((1, -2), (0, -1)),  # 左上
                ((-1, -2), (0, -1)),  # 左下
            ]
            for (dr, dc), (br, bc) in horse_moves:
                if (row + dr, col + dc) == target:
                    # 检查蹩腿
                    block_pos = (row + br, col + bc)
                    if block_pos not in positions:
                        return True, f"马({row},{col})"

        # 炮 - 需要一个炮架
        elif piece == "C":
            if row == target_row:  # 同行
                min_col, max_col = min(col, target_col), max(col, target_col)
                count = 0
                for c in range(min_col + 1, max_col):
                    if (row, c) in positions:
                        count += 1
                if count == 1:  # 正好一个炮架
                    return True, f"炮({row},{col})"
            elif col == target_col:  # 同列
                min_row, max_row = min(row, target_row), max(row, target_row)
                count = 0
                for r in range(min_row + 1, max_row):
                    if (r, col) in positions:
                        count += 1
                if count == 1:
                    return True, f"炮({row},{col})"

        # 兵 - 前进或左右（过河后）
        elif piece == "P":
            # 红兵在 row 0-4 为己方，5-9 为过河
            # 红兵只能向上走 (row+1) 或过河后左右
            if row + 1 == target_row and col == target_col:
                # 向前一步
                return True, f"兵({row},{col})"
            if row >= 5:  # 过河
                if row == target_row and abs(col - target_col) == 1:
                    # 左右一步
                    return True, f"兵({row},{col})"

        # 帅 - 对面将军（已在 validate_fen 中检查，这里也加上）
        elif piece == "K":
            if col == target_col:
                min_row, max_row = min(row, target_row), max(row, target_row)
                blocked = False
                for r in range(min_row + 1, max_row):
                    if (r, col) in positions:
                        blocked = True
                        break
                if not blocked:
                    return True, f"帅({row},{col})"

    return False, ""


def _parse_captured_counts(captured_str: str) -> tuple[int, int, str | None]:
    """解析被吃棋子字符串，返回数量（用于验证）

    Args:
        captured_str: 如 "RP??:raHC" 或 "-:-"

    Returns:
        (red_captured_count, black_captured_count, error_msg)
        - red_captured_count: 红方被吃的棋子数
        - black_captured_count: 黑方被吃的棋子数
        - error_msg: 错误信息，None 表示无错误
    """
    if ":" not in captured_str:
        return 0, 0, f"被吃棋子格式错误，缺少冒号: {captured_str}"

    red_lost, black_lost = captured_str.split(":", 1)

    # 统计红方被吃（红方丢失的棋子）
    red_captured = 0
    if red_lost != "-":
        for ch in red_lost:
            if ch in "RHEACP?" or ch.isupper():
                red_captured += 1
            elif ch.islower():
                # 小写也是被吃的棋子（暗子被吃，对方知道身份）
                red_captured += 1
            else:
                return 0, 0, f"红方被吃棋子非法字符: {ch}"

    # 统计黑方被吃（黑方丢失的棋子）
    black_captured = 0
    if black_lost != "-":
        for ch in black_lost:
            if ch in "rheacp?" or ch.islower():
                black_captured += 1
            elif ch.isupper():
                # 大写也是被吃的棋子（暗子被吃，对方知道身份）
                black_captured += 1
            else:
                return 0, 0, f"黑方被吃棋子非法字符: {ch}"

    return red_captured, black_captured, None


def validate_fen(fen: str) -> tuple[bool, str]:
    """验证 FEN 是否合法

    Args:
        fen: FEN 字符串

    Returns:
        (is_valid, error_message)
    """
    parts = fen.split()
    if len(parts) != 4:
        return False, f"FEN 格式错误：需要 4 部分，实际 {len(parts)} 部分"

    board_str, captured_str, turn_str, viewer_str = parts

    # 验证棋盘
    rows = board_str.split("/")
    if len(rows) != 10:
        return False, f"棋盘行数错误：需要 10 行，实际 {len(rows)} 行"

    piece_count: dict[str, int] = {}
    has_red_king = False
    has_black_king = False
    red_king_pos = None
    black_king_pos = None

    for row_idx, row in enumerate(rows):
        col = 0
        for char in row:
            if char.isdigit():
                col += int(char)
            elif char in PIECE_SYMBOLS or char in "XxKkAaEeHhRrCcPp":
                if char == "K":
                    has_red_king = True
                    red_king_pos = (9 - row_idx, col)
                elif char == "k":
                    has_black_king = True
                    black_king_pos = (9 - row_idx, col)

                piece_count[char] = piece_count.get(char, 0) + 1
                col += 1
            else:
                return False, f"非法字符：{char}"

        if col != 9:
            return False, f"第 {9 - row_idx} 行列数错误：需要 9 列，实际 {col} 列"

    # 检查帅将
    if not has_red_king:
        return False, "缺少红方帅"
    if not has_black_king:
        return False, "缺少黑方将"

    # 检查棋子数量是否超标
    for piece, max_count in FULL_PIECE_COUNT.items():
        if piece_count.get(piece, 0) > max_count:
            return False, f"{piece} 数量超标：最多 {max_count}，实际 {piece_count[piece]}"

    # 检查暗子数量是否合理（暗子数 <= 未翻开的棋子数）
    # 红方：已翻开明子 + 暗子 <= 16
    red_revealed = sum(piece_count.get(p, 0) for p in ["K", "A", "E", "H", "R", "C", "P"])
    red_hidden = piece_count.get("X", 0)
    red_max_hidden = 16 - red_revealed  # 最多能有多少暗子
    if red_hidden > red_max_hidden:
        return (
            False,
            f"红方暗子数量错误: 明子{red_revealed}个，暗子{red_hidden}个，"
            f"暗子最多{red_max_hidden}个",
        )

    # 黑方同理
    black_revealed = sum(piece_count.get(p, 0) for p in ["k", "a", "e", "h", "r", "c", "p"])
    black_hidden = piece_count.get("x", 0)
    black_max_hidden = 16 - black_revealed
    if black_hidden > black_max_hidden:
        return (
            False,
            f"黑方暗子数量错误: 明子{black_revealed}个，暗子{black_hidden}个，"
            f"暗子最多{black_max_hidden}个",
        )

    # 检查帅将是否对面（同列且中间无子）
    if red_king_pos and black_king_pos and red_king_pos[1] == black_king_pos[1]:
        col = red_king_pos[1]
        # 检查中间是否有棋子
        has_blocker = False
        for row_idx, row in enumerate(rows):
            row_num = 9 - row_idx
            if red_king_pos[0] < row_num < black_king_pos[0]:
                # 解析这一行，检查 col 位置
                c = 0
                for char in row:
                    if char.isdigit():
                        c += int(char)
                    else:
                        if c == col:
                            has_blocker = True
                            break
                        c += 1
                    if c > col:
                        break
        if not has_blocker:
            return False, "帅将对面（非法局面）"

    # 验证回合（必须是红方走）
    if turn_str != "r":
        return False, f"必须是红方走，当前是：{'黑方' if turn_str == 'b' else turn_str}"

    # 验证视角
    if viewer_str not in ("r", "b"):
        return False, f"视角标记错误：{viewer_str}"

    # 验证棋子数量一致性：每方恰好 16 个棋子（棋盘 + 被吃 = 16）
    red_captured, black_captured, err = _parse_captured_counts(captured_str)
    if err:
        return False, err

    # 统计棋盘上的棋子
    red_on_board = sum(v for k, v in piece_count.items() if k.isupper() or k == "X")
    black_on_board = sum(v for k, v in piece_count.items() if k.islower() or k == "x")

    red_total = red_on_board + red_captured
    black_total = black_on_board + black_captured

    if red_total != 16:
        return (
            False,
            f"红方棋子数错误: 棋盘{red_on_board} + 被吃{red_captured} = {red_total}, 应为16",
        )
    if black_total != 16:
        return (
            False,
            f"黑方棋子数错误: 棋盘{black_on_board} + 被吃{black_captured} = {black_total}, 应为16",
        )

    # 检查黑方是否被将军（红方能否直接吃将）
    if black_king_pos:
        positions = _parse_board_positions(board_str)
        can_attack, attacker = _can_red_attack_position(
            positions, black_king_pos[0], black_king_pos[1]
        )
        if can_attack:
            return False, f"黑方被将军（{attacker}可吃将），非法局面"

    return True, "OK"


def fix_fen_captured(fen: str) -> str:
    """修复 FEN 的被吃棋子部分，使每方棋子总数 = 16

    Args:
        fen: FEN 字符串

    Returns:
        修复后的 FEN 字符串
    """
    parts = fen.split()
    if len(parts) != 4:
        return fen

    board_str, _, turn_str, viewer_str = parts

    # 统计棋盘上的棋子
    piece_count: dict[str, int] = {}
    for char in board_str:
        if char.isalpha() and char not in "Xx":
            piece_count[char] = piece_count.get(char, 0) + 1
        elif char in "Xx":
            # 暗子也计入
            piece_count[char] = piece_count.get(char, 0) + 1

    # 计算缺失的棋子（被吃的）
    red_missing = []
    black_missing = []

    for piece, max_count in FULL_PIECE_COUNT.items():
        on_board = piece_count.get(piece, 0)
        missing = max_count - on_board
        if missing > 0:
            if piece.isupper():
                red_missing.extend([piece] * missing)
            else:
                black_missing.extend([piece.upper()] * missing)

    # 生成被吃棋子字符串
    red_captured_str = "".join(sorted(red_missing)) if red_missing else "-"
    black_captured_str = "".join(sorted(black_missing)).lower() if black_missing else "-"

    captured_str = f"{red_captured_str}:{black_captured_str}"

    return f"{board_str} {captured_str} {turn_str} {viewer_str}"


def validate_captured_perspective(captured_str: str, viewer: Color) -> None:
    """验证被吃子是否符合视角规则。

    规则：
    - viewer 方被吃的子：只能是大写或 '?'（不能有小写，因为小写表示"我吃的我知道"）
    - 对方被吃的子：只能是大写或小写（不能有 '?'，因为是 viewer 吃的，viewer 知道）

    Args:
        captured_str: 被吃子字符串，格式为 "红方被吃:黑方被吃"
        viewer: 视角颜色

    Raises:
        ValueError: 如果不符合视角规则
    """
    parts = captured_str.split(":")
    red_captured = parts[0] if len(parts) > 0 else "-"
    black_captured = parts[1] if len(parts) > 1 else "-"

    viewer_captured = red_captured if viewer == Color.RED else black_captured
    opponent_captured = black_captured if viewer == Color.RED else red_captured

    # viewer 方被吃的子不能有小写（小写表示"我吃的我知道"，但这是对方吃的）
    for ch in viewer_captured:
        if ch != "-" and ch != "?" and ch.islower():
            raise ValueError(
                f"Invalid FEN: viewer ({viewer.name})'s captured pieces cannot contain "
                f"lowercase '{ch}' (lowercase means 'I captured it and I know', "
                f"but these were captured by opponent)"
            )

    # 对方被吃的子不能有 '?'（viewer 吃的，viewer 肯定知道）
    if "?" in opponent_captured:
        raise ValueError(
            f"Invalid FEN: opponent's captured pieces cannot contain '?' "
            f"(viewer captured them and knows what they are)"
        )
