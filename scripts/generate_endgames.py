"""生成多样化的随机残局

确保：
1. 合法局面（通过 validate_fen）
2. 红方走
3. 黑方不被将军
4. 子力分布多样化
"""

import random
from collections import Counter

from engine.fen import validate_fen

# 棋子价值（用于评估子力优势）
PIECE_VALUES = {
    "K": 0,
    "A": 20,
    "E": 20,
    "H": 45,
    "R": 90,
    "C": 45,
    "P": 10,
    "k": 0,
    "a": 20,
    "e": 20,
    "h": 45,
    "r": 90,
    "c": 45,
    "p": 10,
}

# 残局配置：每种棋子最多数量
MAX_PIECES = {
    "A": 2,
    "E": 2,
    "H": 2,
    "R": 2,
    "C": 2,
    "P": 5,
    "a": 2,
    "e": 2,
    "h": 2,
    "r": 2,
    "c": 2,
    "p": 5,
}


def calculate_material(pieces: list[str]) -> tuple[int, int]:
    """计算双方子力总值"""
    red = sum(PIECE_VALUES.get(p, 0) for p in pieces if p.isupper())
    black = sum(PIECE_VALUES.get(p, 0) for p in pieces if p.islower())
    return red, black


def generate_pieces_for_advantage(advantage: str) -> list[str]:
    """根据优势类型生成棋子列表

    Args:
        advantage: "red", "black", "even"

    Returns:
        棋子列表（不含帅将）
    """
    # 随机选择棋子数量（残局通常 4-10 个棋子，不含帅将）
    total_pieces = random.randint(4, 10)

    # 定义可用棋子池
    red_pool = ["R", "R", "H", "H", "C", "C", "A", "A", "E", "E", "P", "P", "P", "P", "P"]
    black_pool = ["r", "r", "h", "h", "c", "c", "a", "a", "e", "e", "p", "p", "p", "p", "p"]

    max_attempts = 100
    for _ in range(max_attempts):
        # 随机分配红黑棋子数量
        if advantage == "red":
            red_count = random.randint(total_pieces // 2 + 1, min(total_pieces, 7))
            black_count = total_pieces - red_count
        elif advantage == "black":
            black_count = random.randint(total_pieces // 2 + 1, min(total_pieces, 7))
            red_count = total_pieces - black_count
        else:  # even
            half = total_pieces // 2
            red_count = half + random.randint(0, 1)
            black_count = total_pieces - red_count

        # 随机选择棋子
        red_pieces = random.sample(red_pool, min(red_count, len(red_pool)))
        black_pieces = random.sample(black_pool, min(black_count, len(black_pool)))

        # 检查是否符合优势要求
        pieces = red_pieces + black_pieces
        red_val, black_val = calculate_material(pieces)

        if advantage == "red" and red_val > black_val + 20:
            return pieces
        elif advantage == "black" and black_val > red_val + 20:
            return pieces
        elif advantage == "even" and abs(red_val - black_val) <= 30:
            return pieces

    # 如果多次尝试失败，返回一个基本配置
    return ["R", "H", "r", "h"]


def is_valid_position(piece: str, row: int, col: int) -> bool:
    """检查棋子位置是否合法"""
    # 帅将必须在九宫
    if piece in "Kk":
        if piece == "K":
            return 0 <= row <= 2 and 3 <= col <= 5
        else:
            return 7 <= row <= 9 and 3 <= col <= 5

    # 士必须在九宫
    if piece in "Aa":
        if piece == "A":
            return 0 <= row <= 2 and 3 <= col <= 5
        else:
            return 7 <= row <= 9 and 3 <= col <= 5

    # 象不能过河
    if piece in "Ee":
        if piece == "E":
            return 0 <= row <= 4
        else:
            return 5 <= row <= 9

    # 兵卒
    if piece in "Pp":
        if piece == "P":
            return row >= 3  # 红兵至少在第 3 行
        else:
            return row <= 6  # 黑卒至少在第 6 行

    # 其他棋子无位置限制
    return True


def generate_random_board(pieces: list[str]) -> str | None:
    """生成随机棋盘

    Returns:
        棋盘 FEN 字符串，失败返回 None
    """
    board = [[None for _ in range(9)] for _ in range(10)]

    # 先放置帅将
    all_pieces = ["K", "k"] + pieces

    for piece in all_pieces:
        placed = False
        for _ in range(100):
            if piece in "Kk":
                # 帅将在九宫
                if piece == "K":
                    row = random.randint(0, 2)
                    col = random.randint(3, 5)
                else:
                    row = random.randint(7, 9)
                    col = random.randint(3, 5)
            elif piece in "Aa":
                # 士在九宫
                if piece == "A":
                    row = random.randint(0, 2)
                    col = random.randint(3, 5)
                else:
                    row = random.randint(7, 9)
                    col = random.randint(3, 5)
            elif piece in "Ee":
                # 象不过河
                if piece == "E":
                    row = random.randint(0, 4)
                else:
                    row = random.randint(5, 9)
                col = random.randint(0, 8)
            elif piece in "Pp":
                # 兵卒
                if piece == "P":
                    row = random.randint(3, 9)
                else:
                    row = random.randint(0, 6)
                col = random.randint(0, 8)
            else:
                row = random.randint(0, 9)
                col = random.randint(0, 8)

            if board[row][col] is None and is_valid_position(piece, row, col):
                board[row][col] = piece
                placed = True
                break

        if not placed:
            return None

    # 转换为 FEN
    rows = []
    for row_idx in range(9, -1, -1):  # FEN 从上到下
        row_str = ""
        empty = 0
        for col in range(9):
            if board[row_idx][col] is None:
                empty += 1
            else:
                if empty > 0:
                    row_str += str(empty)
                    empty = 0
                row_str += board[row_idx][col]
        if empty > 0:
            row_str += str(empty)
        rows.append(row_str)

    return "/".join(rows)


def generate_hidden_pieces(pieces: list[str]) -> str:
    """生成暗子字符串

    暗子 = 总棋子 - 明子
    """
    # 完整棋子数量
    full = {
        "A": 2,
        "E": 2,
        "H": 2,
        "R": 2,
        "C": 2,
        "P": 5,
        "a": 2,
        "e": 2,
        "h": 2,
        "r": 2,
        "c": 2,
        "p": 5,
    }

    # 统计明子数量
    visible = Counter(pieces)

    # 计算暗子
    red_hidden = []
    black_hidden = []

    for piece, max_count in full.items():
        hidden_count = max_count - visible.get(piece, 0)
        if hidden_count > 0:
            if piece.isupper():
                red_hidden.extend([piece] * hidden_count)
            else:
                black_hidden.extend([piece] * hidden_count)

    red_str = "".join(sorted(red_hidden)) if red_hidden else "-"
    black_str = "".join(sorted(black_hidden)) if black_hidden else "-"

    return f"{red_str}:{black_str}"


def generate_valid_endgame(advantage: str) -> str:
    """生成一个有效的残局 FEN

    Args:
        advantage: "red", "black", "even"

    Returns:
        有效的 FEN 字符串
    """
    max_attempts = 1000
    for _ in range(max_attempts):
        pieces = generate_pieces_for_advantage(advantage)
        board_str = generate_random_board(pieces)
        if board_str is None:
            continue

        # 统计棋盘上的棋子（用于计算暗子）
        board_pieces = [c for c in board_str if c.isalpha()]
        hidden_str = generate_hidden_pieces(board_pieces)

        fen = f"{board_str} {hidden_str} r r"

        valid, msg = validate_fen(fen)
        if valid:
            return fen

    raise RuntimeError(f"Failed to generate valid endgame with advantage={advantage}")


def generate_diverse_endgames(count: int = 100) -> list[str]:
    """生成多样化的残局列表

    分布：
    - 40% 红方优势
    - 30% 黑方优势
    - 30% 势均力敌
    """
    red_count = int(count * 0.4)
    black_count = int(count * 0.3)
    even_count = count - red_count - black_count

    endgames = []

    print(f"Generating {red_count} red-advantage endgames...")
    for i in range(red_count):
        fen = generate_valid_endgame("red")
        endgames.append(fen)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{red_count}")

    print(f"Generating {black_count} black-advantage endgames...")
    for i in range(black_count):
        fen = generate_valid_endgame("black")
        endgames.append(fen)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{black_count}")

    print(f"Generating {even_count} even endgames...")
    for i in range(even_count):
        fen = generate_valid_endgame("even")
        endgames.append(fen)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{even_count}")

    # 打乱顺序
    random.shuffle(endgames)

    return endgames


def main():
    """生成残局并输出"""
    random.seed(42)  # 可重复性

    endgames = generate_diverse_endgames(100)

    # 输出为 Python 代码格式
    print("\n# Generated random endgames (copy to endgames.py)")
    print("_RANDOM_FENS = [")
    for fen in endgames:
        print(f'    "{fen}",')
    print("]")

    # 验证统计
    print("\n# Statistics:")
    red_adv = 0
    black_adv = 0
    even = 0
    for fen in endgames:
        board_pieces = [c for c in fen.split()[0] if c.isalpha()]
        red_val, black_val = calculate_material(board_pieces)
        diff = red_val - black_val
        if diff > 20:
            red_adv += 1
        elif diff < -20:
            black_adv += 1
        else:
            even += 1

    print(f"Red advantage: {red_adv}")
    print(f"Black advantage: {black_adv}")
    print(f"Even: {even}")


if __name__ == "__main__":
    main()
