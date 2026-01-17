"""
AI 对战脚本

让两个 AI 对战多次，统计胜率。支持单场对战和矩阵对战。
"""

import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from jieqi.ai.unified import UnifiedAIEngine
from jieqi.fen import parse_move, to_fen
from jieqi.game import JieqiGame
from jieqi.types import ActionType, Color, GameResult, PieceType

console = Console()
app = typer.Typer()

# 可用策略列表
AVAILABLE_STRATEGIES = [
    "random",
    "greedy",
    "iterative",
    "mcts",
    "muses",
    "muses2",
    "muses3",
    "muses4",
    "it2",
]

# FEN 英文到中文映射
FEN_TO_CHINESE = {
    # 红方
    "R": "車",
    "H": "馬",
    "E": "象",
    "A": "士",
    "K": "帥",
    "C": "炮",
    "P": "兵",
    # 黑方
    "r": "车",
    "h": "马",
    "e": "相",
    "a": "仕",
    "k": "将",
    "c": "砲",
    "p": "卒",
    # 暗子
    "X": "暗",
    "x": "暗",
}

# PieceType 到中文映射（红方/黑方）
PIECE_TYPE_TO_CHINESE = {
    PieceType.ROOK: ("車", "车"),
    PieceType.HORSE: ("馬", "马"),
    PieceType.ELEPHANT: ("象", "相"),
    PieceType.ADVISOR: ("士", "仕"),
    PieceType.KING: ("帥", "将"),
    PieceType.CANNON: ("炮", "砲"),
    PieceType.PAWN: ("兵", "卒"),
}


def piece_to_chinese_colored(piece_type: PieceType, color: Color, is_hidden: bool = False) -> str:
    """将棋子转换为带颜色的中文名称

    Args:
        piece_type: 棋子类型
        color: 棋子颜色
        is_hidden: 是否是暗子（吃暗子时显示"暗x"）

    Returns:
        带 rich 颜色标记的中文名称，如 "[red]車[/red]" 或 "[blue]暗车[/blue]"
    """
    red_name, black_name = PIECE_TYPE_TO_CHINESE.get(piece_type, ("?", "?"))
    if color == Color.RED:
        name = red_name
        color_tag = "red"
    else:
        name = black_name
        color_tag = "blue"

    prefix = "暗" if is_hidden else ""
    return f"[{color_tag}]{prefix}{name}[/{color_tag}]"


def fen_to_chinese(fen: str) -> str:
    """将 FEN 棋盘部分转换为中文显示"""
    # 只转换棋盘部分（第一个空格之前）
    parts = fen.split(" ")
    board_part = parts[0]
    result = []
    for ch in board_part:
        if ch in FEN_TO_CHINESE:
            result.append(FEN_TO_CHINESE[ch])
        else:
            result.append(ch)
    return "".join(result)


def fen_to_board_table(fen: str) -> Table:
    """将 FEN 转换为 rich Table 棋盘显示"""
    # 解析棋盘部分
    parts = fen.split(" ")
    board_part = parts[0]
    rows = board_part.split("/")

    # 创建表格
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("", style="dim")  # 行号
    for col in "abcdefghi":
        table.add_column(col, justify="center", width=2)

    # 填充棋盘
    for row_idx, row_fen in enumerate(rows):
        row_num = 9 - row_idx
        cells = [str(row_num)]
        col = 0
        for ch in row_fen:
            if ch.isdigit():
                # 空格
                for _ in range(int(ch)):
                    cells.append("·")
                    col += 1
            elif ch in FEN_TO_CHINESE:
                piece = FEN_TO_CHINESE[ch]
                # 红方用红色，黑方用蓝色
                if ch.isupper():
                    cells.append(f"[red]{piece}[/red]")
                else:
                    cells.append(f"[blue]{piece}[/blue]")
                col += 1
        table.add_row(*cells)

    return table


# 被吃子解析用的映射（FEN中大写=红子, 小写=黑子）
RED_PIECE_CHINESE = {
    "R": "車",
    "H": "馬",
    "E": "象",
    "A": "士",
    "K": "帥",
    "C": "炮",
    "P": "兵",
}
BLACK_PIECE_CHINESE = {
    "r": "车",
    "h": "马",
    "e": "相",
    "a": "仕",
    "k": "将",
    "c": "砲",
    "p": "卒",
}


def parse_captured_pieces(fen: str) -> tuple[str, str]:
    """解析 FEN 中的被吃子信息，返回 (红方吃的黑子, 黑方吃的红子)

    FEN 被吃子格式: 红方被吃:黑方被吃
    - 大写 = 明子被吃
    - 小写 = 暗子被吃（吃的人知道身份）
    - ? = 暗子被吃（不知道身份）
    """
    parts = fen.split(" ")
    if len(parts) < 2:
        return "", ""

    captured_part = parts[1]  # 格式: 红方被吃:黑方被吃
    if captured_part == "-:-":
        return "", ""

    red_captured, black_captured = "", ""
    if ":" in captured_part:
        red_lost, black_lost = captured_part.split(":")
        # 红方被吃（红子）= 黑方吃的
        # 大小写表示明/暗，但都是红子
        for ch in red_lost:
            if ch == "?":
                black_captured += "暗"  # 未知被吃子
            elif ch.upper() in RED_PIECE_CHINESE:
                black_captured += RED_PIECE_CHINESE[ch.upper()]
        # 黑方被吃（黑子）= 红方吃的
        # 大小写表示明/暗，但都是黑子
        for ch in black_lost:
            if ch == "?":
                red_captured += "暗"  # 未知被吃子
            elif ch.lower() in BLACK_PIECE_CHINESE:
                red_captured += BLACK_PIECE_CHINESE[ch.lower()]

    return red_captured, black_captured


# 揭棋初始位置（暗子只能在这些位置）
# 红方初始位置
RED_STARTING_POSITIONS = {
    (0, 0),
    (0, 1),
    (0, 2),
    (0, 3),
    (0, 4),
    (0, 5),
    (0, 6),
    (0, 7),
    (0, 8),  # row 0
    (2, 1),
    (2, 7),  # row 2
    (3, 0),
    (3, 2),
    (3, 4),
    (3, 6),
    (3, 8),  # row 3
}
# 黑方初始位置
BLACK_STARTING_POSITIONS = {
    (9, 0),
    (9, 1),
    (9, 2),
    (9, 3),
    (9, 4),
    (9, 5),
    (9, 6),
    (9, 7),
    (9, 8),  # row 9
    (7, 1),
    (7, 7),  # row 7
    (6, 0),
    (6, 2),
    (6, 4),
    (6, 6),
    (6, 8),  # row 6
}

# 每种棋子的最大数量
PIECE_MAX_COUNTS = {
    "K": 1,
    "k": 1,  # 将/帅
    "A": 2,
    "a": 2,  # 士/仕
    "E": 2,
    "e": 2,  # 象/相
    "H": 2,
    "h": 2,  # 马
    "R": 2,
    "r": 2,  # 车
    "C": 2,
    "c": 2,  # 炮
    "P": 5,
    "p": 5,  # 兵/卒
}


def validate_fen(fen: str, move_num: int = 0) -> None:
    """验证 FEN 是否合法，不合法则抛出异常

    检查项：
    1. 棋盘格式正确（10行，每行9列）
    2. 暗子只能在初始位置
    3. 每种棋子数量不超过最大值
    4. 必须有且只有1个将/帅
    5. 棋盘棋子 + 被吃棋子 <= 32
    """
    parts = fen.split(" ")
    if len(parts) != 4:
        raise ValueError(f"[Move #{move_num}] Invalid FEN format: {fen}")

    board_str, captured_str, turn, viewer = parts

    # 解析棋盘
    rows = board_str.split("/")
    if len(rows) != 10:
        raise ValueError(f"[Move #{move_num}] FEN must have 10 rows, got {len(rows)}: {fen}")

    # 统计棋子
    piece_counts: dict[str, int] = {}
    hidden_red = 0
    hidden_black = 0
    board_pieces = 0

    for row_idx, row_str in enumerate(rows):
        # FEN 从上到下是 row 9 到 row 0
        row = 9 - row_idx
        col = 0

        for ch in row_str:
            if col >= 9:
                raise ValueError(f"[Move #{move_num}] Row {row} has too many columns: {fen}")

            if ch.isdigit():
                col += int(ch)
            elif ch == "X":
                # 红方暗子
                if (row, col) not in RED_STARTING_POSITIONS:
                    raise ValueError(
                        f"[Move #{move_num}] Red hidden piece at invalid position ({row}, {col}): {fen}"
                    )
                hidden_red += 1
                board_pieces += 1
                col += 1
            elif ch == "x":
                # 黑方暗子
                if (row, col) not in BLACK_STARTING_POSITIONS:
                    raise ValueError(
                        f"[Move #{move_num}] Black hidden piece at invalid position ({row}, {col}): {fen}"
                    )
                hidden_black += 1
                board_pieces += 1
                col += 1
            elif ch.isalpha():
                # 明子
                piece_counts[ch] = piece_counts.get(ch, 0) + 1
                board_pieces += 1
                col += 1
            else:
                raise ValueError(f"[Move #{move_num}] Invalid character '{ch}' in FEN: {fen}")

        if col != 9:
            raise ValueError(f"[Move #{move_num}] Row {row} has {col} columns, expected 9: {fen}")

    # 检查每种棋子数量
    for piece, count in piece_counts.items():
        max_count = PIECE_MAX_COUNTS.get(piece)
        if max_count and count > max_count:
            raise ValueError(
                f"[Move #{move_num}] Too many '{piece}' pieces: {count} > {max_count}: {fen}"
            )

    # 检查将/帅存在（可能是暗子）
    red_king = piece_counts.get("K", 0)
    black_king = piece_counts.get("k", 0)
    if red_king > 1:
        raise ValueError(f"[Move #{move_num}] Multiple red kings: {fen}")
    if black_king > 1:
        raise ValueError(f"[Move #{move_num}] Multiple black kings: {fen}")

    # 统计被吃棋子
    captured_count = 0
    if captured_str != "-:-":
        red_lost, black_lost = captured_str.split(":")
        if red_lost != "-":
            captured_count += len(red_lost)
        if black_lost != "-":
            captured_count += len(black_lost)

    # 检查总数
    total_pieces = board_pieces + captured_count
    if total_pieces > 32:
        raise ValueError(
            f"[Move #{move_num}] Total pieces ({board_pieces} on board + {captured_count} captured = {total_pieces}) exceeds 32: {fen}"
        )

    # 红方总数检查（棋盘上明子 + 暗子 + 被吃）
    red_on_board = sum(count for piece, count in piece_counts.items() if piece.isupper())
    red_captured = len(captured_str.split(":")[0]) if captured_str.split(":")[0] != "-" else 0
    red_total = red_on_board + hidden_red + red_captured
    if red_total > 16:
        raise ValueError(
            f"[Move #{move_num}] Red pieces ({red_on_board} revealed + {hidden_red} hidden + {red_captured} captured = {red_total}) exceeds 16: {fen}"
        )

    black_on_board = sum(count for piece, count in piece_counts.items() if piece.islower())
    black_captured = len(captured_str.split(":")[1]) if captured_str.split(":")[1] != "-" else 0
    black_total = black_on_board + hidden_black + black_captured
    if black_total > 16:
        raise ValueError(
            f"[Move #{move_num}] Black pieces ({black_on_board} revealed + {hidden_black} hidden + {black_captured} captured = {black_total}) exceeds 16: {fen}"
        )


def calculate_elo(
    results: dict[str, dict[str, dict]],
    strategies_list: list[str],
    k: float = 32,
    initial_elo: float = 1500,
) -> dict[str, float]:
    """计算 Elo 评分

    Args:
        results: 对战结果矩阵
        strategies_list: 策略列表
        k: K-factor，控制评分变化幅度
        initial_elo: 初始 Elo 评分

    Returns:
        各策略的 Elo 评分
    """
    elo = dict.fromkeys(strategies_list, initial_elo)

    # 多轮迭代以稳定 Elo
    for _ in range(10):
        for s1 in strategies_list:
            for s2 in strategies_list:
                if s1 == s2:
                    continue

                wins = results[s1][s2]["wins"]
                losses = results[s1][s2]["losses"]
                draws = results[s1][s2]["draws"]
                total = wins + losses + draws

                if total == 0:
                    continue

                # 期望得分
                expected = 1 / (1 + 10 ** ((elo[s2] - elo[s1]) / 400))

                # 实际得分（wins=1, draws=0.5, losses=0）
                actual = (wins + draws * 0.5) / total

                # 更新 Elo
                elo[s1] += k * (actual - expected)

    return elo


def run_single_game_with_log(
    red_strategy: str,
    black_strategy: str,
    time_limit: float,
    max_moves: int,
    seed: int | None,
    log_dir: Path | None,
    game_index: int = 0,
    verbose: bool = False,
) -> tuple[str, int, dict, str]:
    """运行单场对战并记录日志

    Args:
        red_strategy: 红方策略
        black_strategy: 黑方策略
        time_limit: AI 思考时间限制（秒）
        max_moves: 最大步数
        seed: 随机种子
        log_dir: 日志目录
        game_index: 游戏索引（用于生成唯一 game_id）
        verbose: 是否输出每步详情

    Returns:
        (result, moves, stats, game_id)
    """
    # 创建 AI 引擎
    red_ai = UnifiedAIEngine(strategy=red_strategy, time_limit=time_limit)
    black_ai = UnifiedAIEngine(strategy=black_strategy, time_limit=time_limit)

    try:
        return _run_game_impl(
            red_ai,
            black_ai,
            red_strategy,
            black_strategy,
            time_limit,
            max_moves,
            seed,
            log_dir,
            game_index,
            verbose,
        )
    finally:
        # 确保关闭 Rust server 进程
        if hasattr(red_ai, "_backend") and hasattr(red_ai._backend, "close"):
            red_ai._backend.close()
        if hasattr(black_ai, "_backend") and hasattr(black_ai._backend, "close"):
            black_ai._backend.close()


def _run_game_impl(
    red_ai: UnifiedAIEngine,
    black_ai: UnifiedAIEngine,
    red_strategy: str,
    black_strategy: str,
    time_limit: float,
    max_moves: int,
    seed: int | None,
    log_dir: Path | None,
    game_index: int = 0,
    verbose: bool = False,
) -> tuple[str, int, dict, str]:
    """实际执行对战逻辑"""

    # 创建游戏
    game = JieqiGame()

    # 生成唯一的 game_id
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    game_id = f"{timestamp}_{game_index:03d}"

    # 设置日志文件
    log_file = None
    if log_dir:
        log_file = log_dir / f"{game_id}_{red_strategy}_vs_{black_strategy}.jsonl"
        # 写入游戏开始记录
        game_start_record = {
            "type": "game_start",
            "timestamp": datetime.now().isoformat(),
            "game_id": game_id,
            "red_ai": red_strategy,
            "black_ai": black_strategy,
            "time_limit": time_limit,
            "max_moves": max_moves,
            "seed": seed,
        }
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(game_start_record, ensure_ascii=False) + "\n")

    # 统计信息
    stats = {"red_nodes": 0, "black_nodes": 0, "total_moves": 0}
    move_count = 0
    start_game_time = time.time()

    while game.result == GameResult.ONGOING and move_count < max_moves:
        current_turn = game.current_turn
        current_ai = red_ai if current_turn == Color.RED else black_ai
        ai_name = red_strategy if current_turn == Color.RED else black_strategy
        player = "red" if current_turn == Color.RED else "black"

        # 获取当前视角的 FEN
        view = game.get_view(current_turn)
        fen_before = to_fen(view)

        # 验证输入 FEN
        validate_fen(fen_before, move_count + 1)

        # 计时并获取最佳走法
        start_time = time.time()
        if verbose:
            # verbose 模式获取搜索统计
            candidates, nodes, nps = current_ai.get_best_moves_with_stats(fen_before, n=20)
        else:
            candidates = current_ai.get_best_moves(fen_before, n=20)
            nodes, nps = 0, 0.0
        elapsed_ms = (time.time() - start_time) * 1000

        if not candidates:
            break

        # 选择走法：避免重复局面导致和棋
        move_str, score = None, None
        move = None
        selected_index = 0  # 从 top-N 中选的第几个（0-based）
        for idx, (candidate_str, candidate_score) in enumerate(candidates):
            candidate_move, _ = parse_move(candidate_str)
            if candidate_move is None:
                continue

            # 模拟执行，检查是否会导致重复局面
            piece = game.board.get_piece(candidate_move.from_pos)
            was_hidden_temp = piece.is_hidden if piece else False
            success = game.make_move(candidate_move)
            if not success:
                continue

            # 检查重复次数（如果已经出现 max-1 次，这步会触发和棋）
            would_draw = game.get_position_count() >= game.config.max_repetitions
            game.undo_move()  # 撤销模拟

            if would_draw and len(candidates) > 1:
                # 跳过会导致和棋的走法（如果还有其他选择）
                continue

            # 选择这个走法
            move_str, score = candidate_str, candidate_score
            move = candidate_move
            selected_index = idx
            break

        # 如果所有走法都会导致和棋，选第一个
        if move is None:
            move_str, score = candidates[0]
            move, _ = parse_move(move_str)
            selected_index = 0

        if move is None:
            raise RuntimeError(f"AI {ai_name} returned unparseable move: {move_str}")

        # 执行走法前检查是否是揭子走法
        piece = game.board.get_piece(move.from_pos)
        was_hidden = piece.is_hidden if piece else False

        # 执行走法前检查目标位置是否有棋子（吃子）
        target_piece = game.board.get_piece(move.to_pos)
        captured_info = None
        if target_piece:
            captured_info = {
                "type": target_piece.actual_type,  # 可能为 None（暗子）
                "color": target_piece.color,
                "was_hidden": target_piece.is_hidden,
            }

        # 执行走法
        success = game.make_move(move)
        if not success:
            raise RuntimeError(f"AI {ai_name} returned illegal move: {move_str}, FEN: {fen_before}")

        move_count += 1

        # 获取揭开的棋子类型
        revealed_type = None
        if was_hidden and move.action_type == ActionType.REVEAL_AND_MOVE:
            # 走法执行后，棋子已经揭开，从走法记录中获取
            if game.move_history:
                last_record = game.move_history[-1]
                revealed_type = last_record.revealed_type

        # 如果吃了暗子，从走法记录中获取揭开后的类型
        if captured_info and captured_info["was_hidden"] and game.move_history:
            last_record = game.move_history[-1]
            if last_record.captured and last_record.captured.actual_type:
                captured_info["type"] = last_record.captured.actual_type

        # 获取走完后的 FEN（保持当前方视角，与输入 FEN 一致）
        fen_after = to_fen(game.get_view(current_turn))

        # 验证输出 FEN
        validate_fen(fen_after, move_count)

        # 更新统计（使用 Rust AI 返回的真实节点数）
        if player == "red":
            stats["red_nodes"] += nodes
        else:
            stats["black_nodes"] += nodes

        # Verbose 输出
        if verbose:
            color_tag = "red" if player == "red" else "blue"

            # 构建揭子信息（revealed_type 是字符串如 "rook"，需要转换为 PieceType）
            reveal_str = ""
            if revealed_type:
                # 揭的是自己的棋子
                revealed_piece_type = PieceType(revealed_type)
                reveal_str = f" 揭:{piece_to_chinese_colored(revealed_piece_type, current_turn)}"

            # 构建吃子信息
            capture_str = ""
            if captured_info and captured_info["type"]:
                capture_str = f" 吃:{piece_to_chinese_colored(captured_info['type'], captured_info['color'], captured_info['was_hidden'])}"

            # 输出格式:
            # #步数 颜色 AI名称
            #       输入FEN
            #       走法 选第几个/总数 score 耗时 nodes nps [揭:xxx] [吃:xxx]
            console.print(f"#{move_count:3d} [{color_tag}]{player:5}[/{color_tag}] {ai_name}")
            console.print(f"    [dim]IN:  {fen_before}[/dim]")
            # 格式化 nodes 和 nps
            nodes_str = f"{nodes:,}" if nodes > 0 else "0"
            nps_str = f"{nps:,.0f}" if nps > 0 else "0"
            console.print(
                f"    {move_str:8} {selected_index + 1}/{len(candidates)}  score={score:7.1f}  {elapsed_ms:5.0f}ms  "
                f"[dim]nodes={nodes_str} nps={nps_str}[/dim]{reveal_str}{capture_str}"
            )
            console.print(fen_to_board_table(fen_after))
            # 显示累计吃掉的棋子
            red_captured, black_captured = parse_captured_pieces(fen_after)
            if red_captured or black_captured:
                captured_parts = []
                if red_captured:
                    captured_parts.append(f"[red]红吃:[/red] [blue]{red_captured}[/blue]")
                if black_captured:
                    captured_parts.append(f"[blue]黑吃:[/blue] [red]{black_captured}[/red]")
                console.print("    " + "  ".join(captured_parts))
            console.print(f"    [dim]FEN: {fen_after}[/dim]")

        # 记录日志
        if log_file:
            move_record = {
                "type": "move",
                "move_num": move_count,
                "player": player,
                "ai_name": ai_name,
                "move": move_str,
                "score": score,
                "nodes": nodes,
                "nps": nps,
                "elapsed_ms": elapsed_ms,
                "revealed_type": revealed_type,
                "fen_after": fen_after,
                "candidates": [{"move": m, "score": s} for m, s in candidates],
            }
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(move_record, ensure_ascii=False) + "\n")

    # 确定结果
    result_map = {
        GameResult.RED_WIN: "red_win",
        GameResult.BLACK_WIN: "black_win",
        GameResult.DRAW: "draw",
        GameResult.ONGOING: "draw",  # 超过最大步数算和棋
    }
    result = result_map.get(game.result, "draw")

    # 记录游戏结束
    if log_file:
        game_end_record = {
            "type": "game_end",
            "timestamp": datetime.now().isoformat(),
            "game_id": game_id,
            "result": result,
            "total_moves": move_count,
            "duration_seconds": time.time() - start_game_time,
            "red_stats": {"total_nodes": stats["red_nodes"]},
            "black_stats": {"total_nodes": stats["black_nodes"]},
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(game_end_record, ensure_ascii=False) + "\n")

    stats["total_moves"] = move_count

    return result, move_count, stats, game_id


def run_single_game_task(args: tuple) -> tuple[str, str, str, int, str]:
    """运行单局对战（用于多进程，每局一个任务）

    Args:
        args: (red, black, time_limit, max_moves, seed, log_dir, game_index)

    Returns:
        (red, black, result, moves, game_id)
    """
    red, black, time_limit, max_moves, seed, log_dir_str, game_index = args
    log_dir = Path(log_dir_str) if log_dir_str else None

    result, moves, _stats, game_id = run_single_game_with_log(
        red, black, time_limit, max_moves, seed, log_dir, game_index
    )
    return red, black, result, moves, game_id


def run_matchup_games(args: tuple) -> tuple[str, str, list[str], dict, list[str]]:
    """运行一组对战（用于多进程）

    Args:
        args: (red, black, num_games, max_moves, seed, time_limit, log_dir)

    Returns:
        (red, black, results, stats, game_ids)
    """
    red, black, num_games, max_moves, seed, time_limit, log_dir_str = args
    log_dir = Path(log_dir_str) if log_dir_str else None

    results = []
    game_ids = []
    total_moves = 0
    total_red_nodes = 0
    total_black_nodes = 0

    for i in range(num_games):
        game_seed = (seed + i * 2) if seed else None
        result, moves, game_stats, game_id = run_single_game_with_log(
            red, black, time_limit, max_moves, game_seed, log_dir, i
        )
        results.append(result)
        game_ids.append(game_id)
        total_moves += moves
        total_red_nodes += game_stats.get("red_nodes", 0)
        total_black_nodes += game_stats.get("black_nodes", 0)

    stats = {
        "avg_moves": total_moves / num_games if num_games > 0 else 0,
        "total_red_nodes": total_red_nodes,
        "total_black_nodes": total_black_nodes,
    }

    return red, black, results, stats, game_ids


@app.command()
def battle(
    ai_red: str = typer.Option("muses", "--red", help="Red AI strategy"),
    ai_black: str = typer.Option("minimax", "--black", help="Black AI strategy"),
    num_games: int = typer.Option(10, "--games", help="Number of games"),
    max_moves: int = typer.Option(300, "--max-moves", help="Max moves per game"),
    seed: int | None = typer.Option(42, "--seed", help="Random seed"),
    time_limit: float = typer.Option(0.1, "--time", help="AI thinking time per move (seconds)"),
    log_dir: str | None = typer.Option(None, "--log-dir", help="Log directory"),
    verbose: bool = typer.Option(False, "--verbose", help="Show each move in detail"),
):
    """Run AI vs AI battle with logging"""
    # 验证策略
    if ai_red not in AVAILABLE_STRATEGIES:
        console.print(f"[red]Unknown AI: {ai_red}. Available: {AVAILABLE_STRATEGIES}[/red]")
        raise typer.Exit(1)
    if ai_black not in AVAILABLE_STRATEGIES:
        console.print(f"[red]Unknown AI: {ai_black}. Available: {AVAILABLE_STRATEGIES}[/red]")
        raise typer.Exit(1)

    # 设置日志目录
    if log_dir:
        log_path = Path(log_dir)
    else:
        log_path = Path(__file__).parent.parent / "data" / "battle_logs"
    log_path.mkdir(parents=True, exist_ok=True)

    console.print("\n[bold]Jieqi AI Battle[/bold]")
    console.print(f"Red: [red]{ai_red}[/red] vs Black: [blue]{ai_black}[/blue]")
    console.print(f"Games: {num_games}, Max moves: {max_moves}, Time: {time_limit}s")
    console.print(f"Log dir: {log_path}")
    if verbose:
        console.print("[yellow]Verbose mode: ON[/yellow]")
    console.print()

    # 运行对战
    results = {"red_win": 0, "black_win": 0, "draw": 0}
    total_moves = 0
    game_ids = []

    if verbose:
        # Verbose 模式：直接输出每步详情，不用进度条
        for i in range(num_games):
            if num_games > 1:
                console.print(f"\n[bold cyan]--- Game {i + 1}/{num_games} ---[/bold cyan]")
            game_seed = (seed + i * 2) if seed else None
            result, moves, stats, game_id = run_single_game_with_log(
                ai_red, ai_black, time_limit, max_moves, game_seed, log_path, i, verbose=True
            )
            results[result] += 1
            total_moves += moves
            game_ids.append(game_id)

            # 显示本局结果
            result_text = {
                "red_win": f"[red]{ai_red} wins![/red]",
                "black_win": f"[blue]{ai_black} wins![/blue]",
                "draw": "[yellow]Draw[/yellow]",
            }
            console.print(f"\n>>> Result: {result_text[result]} ({moves} moves)")
    else:
        # 正常模式：用进度条
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"[cyan]{ai_red} vs {ai_black}...", total=num_games)

            for i in range(num_games):
                game_seed = (seed + i * 2) if seed else None
                result, moves, stats, game_id = run_single_game_with_log(
                    ai_red, ai_black, time_limit, max_moves, game_seed, log_path, i
                )
                results[result] += 1
                total_moves += moves
                game_ids.append(game_id)
                progress.update(task, advance=1)

    # 显示结果
    table = Table(title="Battle Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row(
        "Red Wins", f"[red]{results['red_win']}[/red] ({results['red_win'] / num_games * 100:.1f}%)"
    )
    table.add_row(
        "Black Wins",
        f"[blue]{results['black_win']}[/blue] ({results['black_win'] / num_games * 100:.1f}%)",
    )
    table.add_row("Draws", f"{results['draw']} ({results['draw'] / num_games * 100:.1f}%)")
    table.add_row("Avg Moves", f"{total_moves / num_games:.1f}")

    console.print(table)
    console.print(f"\n[green]Logs saved to: {log_path}[/green]")


@app.command()
def list_ai():
    """List available AI strategies"""
    table = Table(title="Available AI Strategies")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    descriptions = {
        "random": "Random move selection (weakest)",
        "greedy": "Greedy capture strategy",
        "iterative": "Iterative deepening with alpha-beta pruning",
        "mcts": "Monte Carlo Tree Search",
        "muses": "Advanced hybrid strategy (recommended)",
    }

    for name in AVAILABLE_STRATEGIES:
        table.add_row(name, descriptions.get(name, ""))

    console.print(table)


@app.command()
def compare(
    num_games: int = typer.Option(10, "--games", help="Number of games per direction"),
    max_moves: int = typer.Option(300, "--max-moves", help="Max moves per game"),
    seed: int | None = typer.Option(42, "--seed", help="Random seed"),
    output: str | None = typer.Option(None, "--output", help="Output JSON file"),
    strategies_filter: str | None = typer.Option(
        None, "--filter", help="Comma-separated list of strategies to include"
    ),
    time_limit: float = typer.Option(0.1, "--time", help="AI thinking time per move (seconds)"),
    workers: int = typer.Option(10, "--workers", help="Number of parallel workers"),
    log_dir: str | None = typer.Option(None, "--log-dir", help="Log directory"),
):
    """Run round-robin comparison between AI strategies (red vs black and black vs red)"""
    # 获取策略列表
    if strategies_filter:
        selected = [s.strip() for s in strategies_filter.split(",")]
        strategies_list = [s for s in selected if s in AVAILABLE_STRATEGIES]
    else:
        strategies_list = AVAILABLE_STRATEGIES.copy()

    if len(strategies_list) < 2:
        console.print("[red]Need at least 2 strategies to compare[/red]")
        raise typer.Exit(1)

    # 设置日志目录
    if log_dir:
        log_path = Path(log_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = Path(__file__).parent.parent / "data" / "battle_logs" / f"compare_{timestamp}"
    log_path.mkdir(parents=True, exist_ok=True)

    # 计算对战组数：每对互换红黑
    num_pairs = len(strategies_list) * (len(strategies_list) - 1)
    total_games = num_pairs * num_games

    console.print("\n[bold]AI Round-Robin Comparison[/bold]")
    console.print(f"Strategies: {strategies_list}")
    console.print(f"Games per direction: {num_games}")
    console.print(f"Total matchups: {num_pairs} (each pair plays both directions)")
    console.print(f"Total games: {total_games}")
    console.print(f"Time limit: {time_limit}s/move, Workers: {workers}")
    console.print(f"Log dir: {log_path}")
    console.print()

    # 结果矩阵
    results: dict[str, dict[str, dict]] = {
        s1: {s2: {"wins": 0, "losses": 0, "draws": 0} for s2 in strategies_list}
        for s1 in strategies_list
    }

    # 构建所有单局任务（每局一个任务，方便实时进度更新）
    game_args = []
    game_index = 0
    for idx, s1 in enumerate(strategies_list):
        for jdx, s2 in enumerate(strategies_list):
            if s1 != s2:
                for i in range(num_games):
                    game_seed = (seed + idx * 1000 + jdx * 100 + i * 2) if seed else None
                    game_args.append(
                        (s1, s2, time_limit, max_moves, game_seed, str(log_path), game_index)
                    )
                    game_index += 1

    all_game_ids = []
    start_time = time.time()

    # 实时统计
    wins_count = {s: 0 for s in strategies_list}
    losses_count = {s: 0 for s in strategies_list}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
        TextColumn("•"),
        TextColumn("[yellow]{task.fields[status]}[/yellow]"),
        console=console,
        refresh_per_second=4,
    ) as progress:
        task = progress.add_task(
            "[green]Running battles...", total=total_games, status="starting..."
        )

        if workers > 1:
            # 多进程模式：每局一个任务
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(run_single_game_task, args): args for args in game_args}
                for future in as_completed(futures):
                    ai_red, ai_black, result, moves, game_id = future.result()

                    # 更新结果
                    if result == "red_win":
                        results[ai_red][ai_black]["wins"] += 1
                        wins_count[ai_red] += 1
                        losses_count[ai_black] += 1
                    elif result == "black_win":
                        results[ai_red][ai_black]["losses"] += 1
                        wins_count[ai_black] += 1
                        losses_count[ai_red] += 1
                    else:
                        results[ai_red][ai_black]["draws"] += 1

                    all_game_ids.append(game_id)

                    # 生成状态文本
                    elapsed = time.time() - start_time
                    completed = len(all_game_ids)
                    speed = completed / elapsed if elapsed > 0 else 0
                    eta = (total_games - completed) / speed if speed > 0 else 0

                    # 显示各策略胜负
                    status_parts = []
                    for s in strategies_list:
                        status_parts.append(f"{s[:3]}:{wins_count[s]}W")
                    status = " ".join(status_parts) + f" | {speed:.1f}g/s ETA:{eta:.0f}s"

                    progress.update(task, advance=1, status=status)
        else:
            # 单进程模式
            for args in game_args:
                ai_red, ai_black, result, moves, game_id = run_single_game_task(args)

                if result == "red_win":
                    results[ai_red][ai_black]["wins"] += 1
                    wins_count[ai_red] += 1
                    losses_count[ai_black] += 1
                elif result == "black_win":
                    results[ai_red][ai_black]["losses"] += 1
                    wins_count[ai_black] += 1
                    losses_count[ai_red] += 1
                else:
                    results[ai_red][ai_black]["draws"] += 1

                all_game_ids.append(game_id)

                elapsed = time.time() - start_time
                completed = len(all_game_ids)
                speed = completed / elapsed if elapsed > 0 else 0
                eta = (total_games - completed) / speed if speed > 0 else 0
                status_parts = []
                for s in strategies_list:
                    status_parts.append(f"{s[:3]}:{wins_count[s]}W")
                status = " ".join(status_parts) + f" | {speed:.1f}g/s ETA:{eta:.0f}s"
                progress.update(task, advance=1, status=status)

    # 计算综合得分（作为红方的胜率）
    scores: dict[str, float] = {}
    for s in strategies_list:
        total_wins = sum(results[s][opp]["wins"] for opp in strategies_list if opp != s)
        total_losses = sum(results[s][opp]["losses"] for opp in strategies_list if opp != s)
        total_draws = sum(results[s][opp]["draws"] for opp in strategies_list if opp != s)
        total = total_wins + total_losses + total_draws
        scores[s] = (total_wins + total_draws * 0.5) / total if total > 0 else 0

    # 计算 Elo 评分
    elo = calculate_elo(results, strategies_list)

    # 按得分排序
    sorted_strategies = sorted(strategies_list, key=lambda s: scores[s], reverse=True)

    # 显示结果矩阵
    console.print("\n[bold]Win Matrix (row=Red, col=Black)[/bold]")

    table = Table()
    table.add_column("AI", style="cyan")
    for s in sorted_strategies:
        table.add_column(s[:8], justify="center")
    table.add_column("Score", style="yellow", justify="right")

    for s1 in sorted_strategies:
        row = [s1]
        for s2 in sorted_strategies:
            if s1 == s2:
                row.append("-")
            else:
                wins = results[s1][s2]["wins"]
                total = wins + results[s1][s2]["losses"] + results[s1][s2]["draws"]
                rate = wins / total * 100 if total > 0 else 0
                if rate >= 70:
                    row.append(f"[green]{rate:.0f}%[/green]")
                elif rate >= 50:
                    row.append(f"[yellow]{rate:.0f}%[/yellow]")
                else:
                    row.append(f"[red]{rate:.0f}%[/red]")
        row.append(f"{scores[s1] * 100:.1f}%")
        table.add_row(*row)

    console.print(table)

    # 排名
    console.print("\n[bold]Final Rankings (Win Rate | Elo):[/bold]")
    for i, s in enumerate(sorted_strategies, 1):
        console.print(f"  {i:2}. {s:12} - {scores[s] * 100:.1f}% | Elo: {elo[s]:.0f}")

    # 保存 JSON
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "strategies": sorted_strategies,
        "num_games_per_direction": num_games,
        "max_moves": max_moves,
        "time_limit": time_limit,
        "total_games": total_games,
        "log_dir": str(log_path),
        "results": {
            s1: {
                s2: {
                    "wins": results[s1][s2]["wins"],
                    "losses": results[s1][s2]["losses"],
                    "draws": results[s1][s2]["draws"],
                    "win_rate": (
                        results[s1][s2]["wins"]
                        / (
                            results[s1][s2]["wins"]
                            + results[s1][s2]["losses"]
                            + results[s1][s2]["draws"]
                        )
                        if (
                            results[s1][s2]["wins"]
                            + results[s1][s2]["losses"]
                            + results[s1][s2]["draws"]
                        )
                        > 0
                        else 0
                    ),
                }
                for s2 in sorted_strategies
            }
            for s1 in sorted_strategies
        },
        "scores": {s: scores[s] for s in sorted_strategies},
        "elo": {s: elo[s] for s in sorted_strategies},
        "rankings": [
            {"rank": i, "name": s, "score": scores[s], "elo": elo[s]}
            for i, s in enumerate(sorted_strategies, 1)
        ],
    }

    if output:
        output_path = Path(output)
    else:
        output_path = log_path / "summary.json"

    output_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
    console.print(f"\n[green]Results saved to: {output_path}[/green]")
    console.print(f"[green]Battle logs saved to: {log_path}[/green]")
    console.print(f"[green]Total log files: {len(all_game_ids)}[/green]")


if __name__ == "__main__":
    app()
