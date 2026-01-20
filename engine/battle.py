"""统一的对战核心逻辑

提供 CLI 和 Web UI 共用的对战引擎，包含：
- 避免重复局面的走法选择
- 完整的对战流程
- 统一的结果格式
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.fen import apply_move_with_capture, parse_fen
from engine.rust_ai import UnifiedAIEngine
from engine.types import Color


@dataclass
class MoveResult:
    """单步走法结果"""

    move_num: int
    player: str  # "red" | "black"
    fen_before: str
    fen_after: str
    move: str
    score: float
    eval_before: float
    eval_after: float
    candidates: list[dict]  # [{"move": str, "score": float}, ...]
    captured: dict | None  # {"type": str, "color": str, "was_hidden": bool}
    revealed_type: str | None
    selected_index: int  # 从 candidates 中选的第几个
    nodes: int
    nps: float
    time_ms: float
    depth: int


@dataclass
class BattleResult:
    """对战结果"""

    result: str  # "red_win" | "black_win" | "draw"
    history: list[MoveResult]
    total_moves: int


def select_move_avoiding_repetition(
    current_fen: str,
    candidates: list[tuple[str, float]],
    position_counts: dict[str, int],
    max_repetitions: int = 3,
) -> tuple[str, float, int]:
    """选择走法，避免重复局面

    遍历候选走法，模拟执行，检查是否会导致重复。
    如果会导致和棋且还有其他选择，跳过该走法。

    Args:
        current_fen: 当前 FEN
        candidates: 候选走法列表 [(move_str, score), ...]
        position_counts: 历史局面计数 {board_part: count}
        max_repetitions: 最大重复次数（默认 3）

    Returns:
        (move_str, score, selected_index)
    """
    for idx, (move_str, score) in enumerate(candidates):
        try:
            new_fen, _ = apply_move_with_capture(current_fen, move_str)
            board_part = new_fen.split(" ")[0]
            current_count = position_counts.get(board_part, 0)

            if current_count + 1 >= max_repetitions and len(candidates) > 1:
                continue  # 跳过会导致和棋的走法

            return move_str, score, idx
        except Exception:
            continue

    # 所有走法都会导致和棋，选第一个
    return candidates[0][0], candidates[0][1], 0


def run_single_step(
    current_fen: str,
    strategy: str,
    time_limit: float = 0.2,
    position_counts: dict[str, int] | None = None,
    max_repetitions: int = 3,
) -> MoveResult | None:
    """执行单步走法

    Args:
        current_fen: 当前 FEN
        strategy: AI 策略
        time_limit: 思考时间
        position_counts: 历史局面计数（可选）
        max_repetitions: 重复次数限制

    Returns:
        MoveResult 或 None（如果无法走棋）
    """
    state = parse_fen(current_fen)
    player = "red" if state.turn == Color.RED else "black"
    ai = UnifiedAIEngine(strategy=strategy, time_limit=time_limit)

    if position_counts is None:
        position_counts = {}

    # 获取静态评估
    try:
        eval_before, _ = ai.get_eval(current_fen)
    except Exception:
        eval_before = 0.0

    # 获取候选走法
    try:
        stats = ai.get_best_moves_full_stats(current_fen, n=20)
        candidates = stats["moves"]
        nodes = stats["nodes"]
        nps = stats["nps"]
        depth = stats["depth"]
        elapsed_ms = stats["elapsed_ms"]
    except Exception:
        return None

    if not candidates:
        return None

    # 选择走法：避免重复
    move_str, score, selected_index = select_move_avoiding_repetition(
        current_fen, candidates, position_counts, max_repetitions
    )

    # 执行走法
    try:
        new_fen, captured_info = apply_move_with_capture(current_fen, move_str)
    except Exception:
        return None

    # 获取走法后评估
    try:
        eval_after, _ = ai.get_eval(new_fen)
    except Exception:
        eval_after = 0.0

    # 解析揭子类型
    revealed_type = None
    if "=" in move_str:
        revealed_type = move_str.split("=")[1].lower()

    return MoveResult(
        move_num=0,  # 调用者负责设置
        player=player,
        fen_before=current_fen,
        fen_after=new_fen,
        move=move_str,
        score=score,
        eval_before=eval_before,
        eval_after=eval_after,
        candidates=[{"move": m, "score": s} for m, s in candidates],
        captured=captured_info,
        revealed_type=revealed_type,
        selected_index=selected_index,
        nodes=nodes,
        nps=nps,
        time_ms=elapsed_ms,
        depth=depth,
    )


def run_battle(
    start_fen: str,
    red_strategy: str,
    black_strategy: str,
    time_limit: float = 0.2,
    max_moves: int = 200,
    max_repetitions: int = 3,
    progress_callback=None,
) -> BattleResult:
    """运行完整对弈

    Args:
        start_fen: 起始 FEN
        red_strategy: 红方 AI 策略
        black_strategy: 黑方 AI 策略
        time_limit: AI 思考时间限制
        max_moves: 最大步数
        max_repetitions: 重复多少次判和
        progress_callback: 进度回调 (move_num, player, move_str, score)

    Returns:
        BattleResult
    """
    red_ai = UnifiedAIEngine(strategy=red_strategy, time_limit=time_limit)
    black_ai = UnifiedAIEngine(strategy=black_strategy, time_limit=time_limit)

    history: list[MoveResult] = []
    position_counts: dict[str, int] = {}  # board_part -> count
    current_fen = start_fen
    result = "ongoing"

    # 记录初始局面
    board_part = current_fen.split(" ")[0]
    position_counts[board_part] = 1

    move_count = 0

    while move_count < max_moves:
        state = parse_fen(current_fen)
        current_turn = state.turn
        current_ai = red_ai if current_turn == Color.RED else black_ai
        player = "red" if current_turn == Color.RED else "black"

        # 获取静态评估
        try:
            eval_before, _ = current_ai.get_eval(current_fen)
        except Exception:
            eval_before = 0.0

        # 获取候选走法
        try:
            stats = current_ai.get_best_moves_full_stats(current_fen, n=20)
            candidates = stats["moves"]
            nodes = stats["nodes"]
            nps = stats["nps"]
            depth = stats["depth"]
            elapsed_ms = stats["elapsed_ms"]
        except Exception:
            result = "draw"
            break

        if not candidates:
            result = "black_win" if player == "red" else "red_win"
            break

        # 选择走法：避免重复
        move_str, score, selected_index = select_move_avoiding_repetition(
            current_fen, candidates, position_counts, max_repetitions
        )

        # 执行走法
        try:
            new_fen, captured_info = apply_move_with_capture(current_fen, move_str)
        except Exception:
            result = "draw"
            break

        # 获取走法后评估
        try:
            eval_after, _ = current_ai.get_eval(new_fen)
        except Exception:
            eval_after = 0.0

        move_count += 1

        # 解析揭子类型
        revealed_type = None
        if "=" in move_str:
            revealed_type = move_str.split("=")[1].lower()

        # 记录步骤
        step = MoveResult(
            move_num=move_count,
            player=player,
            fen_before=current_fen,
            fen_after=new_fen,
            move=move_str,
            score=score,
            eval_before=eval_before,
            eval_after=eval_after,
            candidates=[{"move": m, "score": s} for m, s in candidates],
            captured=captured_info,
            revealed_type=revealed_type,
            selected_index=selected_index,
            nodes=nodes,
            nps=nps,
            time_ms=elapsed_ms,
            depth=depth,
        )
        history.append(step)

        if progress_callback:
            progress_callback(move_count, player, move_str, score)

        # 检查游戏结束
        if captured_info and captured_info.get("type") == "king":
            result = "red_win" if player == "red" else "black_win"
            break

        # 更新局面计数
        board_part = new_fen.split(" ")[0]
        position_counts[board_part] = position_counts.get(board_part, 0) + 1
        if position_counts[board_part] >= max_repetitions:
            result = "draw"
            break

        current_fen = new_fen

    if result == "ongoing":
        result = "draw"

    return BattleResult(
        result=result,
        history=history,
        total_moves=move_count,
    )
