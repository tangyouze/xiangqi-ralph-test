"""
AI 评估报告生成器

生成 HTML 格式的 AI 评估报告，可在 Streamlit 中查看或导出。
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from jieqi.ai.unified import UnifiedAIEngine
from jieqi.fen import apply_move_to_fen, parse_fen
from jieqi.logging import logger

# 默认评估场景
EVAL_SCENARIOS: list[tuple[str, str]] = [
    # === 基础局面 ===
    ("initial", "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"),
    ("midgame_hidden", "xxxx1xxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXX1XXXX -:- r r"),
    # === 杀法练习 ===
    ("double_rook_mate", "4k4/9/9/9/9/9/9/9/4R4/3RK4 -:- r r"),
    ("horse_cannon_mate", "3ak4/9/9/9/9/9/9/5C3/4H4/4K4 -:- r r"),
    ("iron_bolt", "3k5/4a4/4R4/9/9/9/9/9/9/4K4 -:- r r"),
    ("smothered_mate", "4k4/4C4/4C4/9/9/9/9/9/9/4K4 -:- r r"),
    ("rook_horse_cold", "3k5/9/4H4/9/9/9/9/4R4/9/4K4 -:- r r"),
    # === 残局 ===
    ("rook_vs_cannon", "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r"),
    ("pawn_advance", "4k4/9/9/9/9/9/4P4/9/9/4K4 -:- r r"),
    ("rook_pawn_vs_rook", "4k4/9/4r4/9/9/9/4P4/9/4R4/4K4 -:- r r"),
    ("double_cannon_advisor", "3ak4/4a4/9/9/9/9/9/4C4/4C4/4K4 -:- r r"),
    # === 揭棋特殊局面（暗子必须在标准初始位置）===
    ("hidden_opening", "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"),
    ("partial_revealed", "xxxx1xxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1C5C1/9/XXXX1XXXX -:- r r"),
    (
        "mixed_hidden_revealed",
        "xr1k1r2x/9/1x2e2x1/x1x1x1x1x/9/9/X1X1X1X1X/1X2E2X1/9/XR1K1R2X -:- r r",
    ),
    # === AI 对抗测试 ===
    ("midgame_attack", "r2ak4/9/2h1e4/p3p4/9/6P2/P3P4/2H1E4/9/R2AK4 -:- r r"),
    (
        "complex_midgame",
        "r1eak4/4a4/4e1h2/p1h1p3p/4c4/2P6/P3P3P/4E1H2/4A4/R2AK2R1 -:- r r",
    ),
]


def play_game(
    fen: str,
    ai_engine: UnifiedAIEngine,
    random_engine: UnifiedAIEngine,
    max_moves: int = 200,
) -> str:
    """从给定局面开始下一局棋

    Args:
        fen: 起始 FEN
        ai_engine: 测试的 AI（红方）
        random_engine: random AI（黑方）
        max_moves: 最大步数

    Returns:
        "win" / "draw" / "loss"
    """
    current_fen = fen
    move_count = 0

    while move_count < max_moves:
        # 解析当前局面
        try:
            state = parse_fen(current_fen)
        except Exception:
            return "draw"

        # 检查是否有王（对于揭棋，未揭开的棋子可能是王，所以只在明确没有王时才判负）
        # 如果有任何暗子，假设王还存在
        has_red_hidden = any(p.piece_type is None and p.color.value == "red" for p in state.pieces)
        has_black_hidden = any(
            p.piece_type is None and p.color.value == "black" for p in state.pieces
        )
        has_red_king = has_red_hidden or any(
            p.piece_type and p.piece_type.value == "king" and p.color.value == "red"
            for p in state.pieces
        )
        has_black_king = has_black_hidden or any(
            p.piece_type and p.piece_type.value == "king" and p.color.value == "black"
            for p in state.pieces
        )

        if not has_red_king:
            return "loss"
        if not has_black_king:
            return "win"

        # 当前回合的 AI
        if state.turn.value == "red":
            engine = ai_engine
        else:
            engine = random_engine

        # 获取走法
        try:
            move = engine.get_best_move(current_fen)
            if move is None:
                # 无合法走法
                if state.turn.value == "red":
                    return "loss"
                else:
                    return "win"

            move_str, _ = move
            current_fen = apply_move_to_fen(current_fen, move_str)
            move_count += 1
        except Exception:
            return "draw"

    return "draw"


def _run_single_game(
    fen: str,
    red_strategy: str,
    black_strategy: str,
    time_limit: float,
    max_moves: int = 100,
) -> str:
    """运行单局游戏（用于并行执行）"""
    red_engine = UnifiedAIEngine(
        strategy=red_strategy,
        time_limit=time_limit,
    )
    black_engine = UnifiedAIEngine(
        strategy=black_strategy,
        time_limit=time_limit if black_strategy != "random" else 0.1,
    )
    return play_game(fen, red_engine, black_engine, max_moves=max_moves)


def test_win_rate(
    fen: str,
    strategy: str,
    num_games: int = 5,
    time_limit: float = 1.0,
    max_workers: int = 4,
) -> WinRateResult:
    """测试 AI 对 random 的胜率（并行执行）

    Args:
        fen: 起始局面
        strategy: AI 策略名称
        num_games: 对局数
        time_limit: 每步时间限制
        max_workers: 并行线程数

    Returns:
        胜率结果
    """
    result = WinRateResult()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_run_single_game, fen, strategy, "random", time_limit)
            for _ in range(num_games)
        ]
        for future in as_completed(futures):
            outcome = future.result()
            if outcome == "win":
                result.wins += 1
            elif outcome == "loss":
                result.losses += 1
            else:
                result.draws += 1

    return result


def test_win_rate_vs_self(
    fen: str,
    strategy: str,
    num_games: int = 5,
    time_limit: float = 1.0,
    max_workers: int = 4,
) -> WinRateResult:
    """测试 AI 对自己的胜率（红方视角，并行执行）

    Args:
        fen: 起始局面
        strategy: AI 策略名称
        num_games: 对局数
        time_limit: 每步时间限制
        max_workers: 并行线程数

    Returns:
        胜率结果（红方视角）
    """
    result = WinRateResult()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_run_single_game, fen, strategy, strategy, time_limit)
            for _ in range(num_games)
        ]
        for future in as_completed(futures):
            outcome = future.result()
            if outcome == "win":
                result.wins += 1
            elif outcome == "loss":
                result.losses += 1
            else:
                result.draws += 1

    return result


@dataclass
class WinRateResult:
    """胜率测试结果"""

    wins: int = 0
    draws: int = 0
    losses: int = 0

    @property
    def total(self) -> int:
        return self.wins + self.draws + self.losses

    @property
    def win_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.wins / self.total * 100


@dataclass
class ScenarioResult:
    """单个场景的评估结果"""

    name: str  # 场景名称
    fen: str  # FEN 字符串
    best_move: str  # AI 推荐走法
    score: float  # 评估分数
    time_ms: float  # 耗时（毫秒）
    candidates: list[tuple[str, float]] = field(default_factory=list)  # 候选走法
    win_rate: WinRateResult | None = None  # 对战 random 的胜率
    win_rate_vs_self: WinRateResult | None = None  # 对战自己的胜率


@dataclass
class EvalReport:
    """AI 评估报告"""

    ai_name: str
    timestamp: str
    config: dict  # depth, time_limit 等
    results: list[ScenarioResult]

    def to_html(self) -> str:
        """生成 HTML 报告"""
        # 计算统计
        total = len(self.results)
        total_time_ms = sum(r.time_ms for r in self.results)

        # 构建场景行
        scenario_rows = []
        has_winrate = any(r.win_rate is not None for r in self.results)
        has_winrate_self = any(r.win_rate_vs_self is not None for r in self.results)
        for r in self.results:
            score_class = "score-positive" if r.score >= 0 else "score-negative"
            # 1000 表示将杀
            score_str = f"{r.score:+.0f}" + (" (M)" if abs(r.score) >= 1000 else "")
            # vs random 胜率
            if r.win_rate:
                wr = r.win_rate
                winrate_str = f"{wr.win_rate:.0f}% ({wr.wins}W/{wr.draws}D/{wr.losses}L)"
            else:
                winrate_str = "-"
            # vs self 胜率
            if r.win_rate_vs_self:
                wrs = r.win_rate_vs_self
                winrate_self_str = f"{wrs.win_rate:.0f}% ({wrs.wins}W/{wrs.draws}D/{wrs.losses}L)"
            else:
                winrate_self_str = "-"
            winrate_col = f"<td>{winrate_str}</td>" if has_winrate else ""
            winrate_self_col = f"<td>{winrate_self_str}</td>" if has_winrate_self else ""
            scenario_rows.append(
                f"""<tr>
                <td><b>{r.name}</b><br><code class="fen">{r.fen}</code></td>
                <td><code>{r.best_move}</code></td>
                <td class="{score_class}">{score_str}</td>
                <td>{r.time_ms:.0f}ms</td>
                {winrate_col}
                {winrate_self_col}
            </tr>"""
            )

        # 计算平均分
        avg_score = sum(r.score for r in self.results) / total if total > 0 else 0

        # 配置信息
        depth = self.config.get("depth", "-")
        time_limit = self.config.get("time_limit", "-")
        if time_limit and time_limit != "-":
            time_limit = f"{time_limit}s"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AI Evaluation Report - {self.ai_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 24px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        tr:nth-child(even) {{ background: #fafafa; }}
        code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }}
        code.fen {{ font-size: 11px; color: #666; display: block; margin-top: 4px; }}
        .score-positive {{ color: #22863a; font-weight: 600; }}
        .score-negative {{ color: #cb2431; font-weight: 600; }}
        .summary {{ background: #e8f4f8; padding: 16px; margin: 16px 0; border-radius: 6px; }}
        .summary p {{ margin: 8px 0; }}
        .summary b {{ color: #333; }}
    </style>
</head>
<body>
    <h1>AI Evaluation Report</h1>

    <div class="summary">
        <p><b>AI:</b> {self.ai_name}</p>
        <p><b>Time:</b> {self.timestamp}</p>
        <p><b>Config:</b> depth={depth}, time_limit={time_limit}</p>
    </div>

    <h2>Summary</h2>
    <table>
        <tr><td><b>Total Scenarios</b></td><td>{total}</td></tr>
        <tr><td><b>Avg Score</b></td><td>{avg_score:+.1f}</td></tr>
        <tr><td><b>Total Time</b></td><td>{total_time_ms / 1000:.2f}s</td></tr>
    </table>

    <h2>Scenario Results</h2>
    <table>
        <tr>
            <th>Scenario / FEN</th>
            <th>Best Move</th>
            <th>Score</th>
            <th>Time</th>
            {"<th>vs Random</th>" if has_winrate else ""}
            {"<th>vs Self</th>" if has_winrate_self else ""}
        </tr>
        {"".join(scenario_rows)}
    </table>
</body>
</html>"""

    def save(self, path: Path) -> None:
        """保存为 HTML 文件"""
        path.write_text(self.to_html(), encoding="utf-8")


def generate_report(
    strategy: str,
    scenarios: list[tuple[str, str]] | None = None,
    config: dict | None = None,
) -> EvalReport:
    """运行评估并生成报告

    Args:
        strategy: AI 策略名称
        scenarios: 评估场景列表 [(name, fen), ...]
        config: AI 配置 {"depth": 4, "time_limit": 1.0}

    Returns:
        评估报告
    """
    if scenarios is None:
        scenarios = EVAL_SCENARIOS

    if config is None:
        config = {"depth": 4, "time_limit": 1.0}

    # 创建 AI 引擎
    engine = UnifiedAIEngine(
        strategy=strategy,
        depth=config.get("depth", 4),
        time_limit=config.get("time_limit"),
    )

    results: list[ScenarioResult] = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.info(f"Evaluating {strategy} on {len(scenarios)} scenarios...")

    # 是否测试胜率
    test_winrate = config.get("test_winrate", False)
    winrate_games = config.get("winrate_games", 5)
    winrate_time_limit = config.get("winrate_time_limit", 1.0)
    max_workers = config.get("max_workers", 4)

    for name, fen in scenarios:
        start = time.perf_counter()
        try:
            moves = engine.get_best_moves(fen, n=5)
            elapsed_ms = (time.perf_counter() - start) * 1000

            if moves:
                best_move, score = moves[0]
            else:
                best_move, score = "-", 0.0

            # 测试胜率
            win_rate_result = None
            win_rate_vs_self_result = None
            if test_winrate:
                logger.info(f"  Testing win rate for {name}...")
                win_rate_result = test_win_rate(
                    fen=fen,
                    strategy=strategy,
                    num_games=winrate_games,
                    time_limit=winrate_time_limit,
                    max_workers=max_workers,
                )
                win_rate_vs_self_result = test_win_rate_vs_self(
                    fen=fen,
                    strategy=strategy,
                    num_games=winrate_games,
                    time_limit=winrate_time_limit,
                    max_workers=max_workers,
                )
                logger.info(
                    f"  vs Random: {win_rate_result.win_rate:.0f}% "
                    f"({win_rate_result.wins}W/{win_rate_result.draws}D/"
                    f"{win_rate_result.losses}L) | "
                    f"vs Self: {win_rate_vs_self_result.win_rate:.0f}% "
                    f"({win_rate_vs_self_result.wins}W/{win_rate_vs_self_result.draws}D/"
                    f"{win_rate_vs_self_result.losses}L)"
                )

            results.append(
                ScenarioResult(
                    name=name,
                    fen=fen,
                    best_move=best_move,
                    score=score,
                    time_ms=elapsed_ms,
                    candidates=moves,
                    win_rate=win_rate_result,
                    win_rate_vs_self=win_rate_vs_self_result,
                )
            )
            logger.debug(f"  {name}: {best_move} ({score:+.0f}) in {elapsed_ms:.0f}ms")

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(
                ScenarioResult(
                    name=name,
                    fen=fen,
                    best_move=f"ERROR: {e}",
                    score=0.0,
                    time_ms=elapsed_ms,
                )
            )
            logger.error(f"  {name}: ERROR - {e}")

    return EvalReport(
        ai_name=strategy,
        timestamp=timestamp,
        config=config,
        results=results,
    )
