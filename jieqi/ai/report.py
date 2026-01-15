"""
AI 评估报告生成器

生成 HTML 格式的 AI 评估报告，可在 Streamlit 中查看或导出。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from jieqi.ai.unified import UnifiedAIEngine
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
    # === 揭棋特殊局面 ===
    ("red_hidden_advantage", "4k4/4x4/9/4X4/9/9/9/9/9/4K4 -:- r r"),
    ("black_hidden_advantage", "4k4/9/9/9/9/9/4x4/9/9/4K4 -:- r b"),
    ("multi_hidden_complex", "x2k2x1x/9/1x2x2x1/9/9/9/1X2X2X1/9/X2K2X1X/9 -:- r r"),
    # === AI 对抗测试 ===
    ("midgame_attack", "r2ak4/9/2h1e4/p3p4/9/6P2/P3P4/2H1E4/9/R2AK4 -:- r r"),
    (
        "complex_midgame",
        "r1eak4/4a4/4e1h2/p1h1p3p/4c4/2P6/P3P3P/4E1H2/4A4/R2AK2R1 -:- r r",
    ),
]


@dataclass
class ScenarioResult:
    """单个场景的评估结果"""

    name: str  # 场景名称
    fen: str  # FEN 字符串
    best_move: str  # AI 推荐走法
    score: float  # 评估分数
    time_ms: float  # 耗时（毫秒）
    candidates: list[tuple[str, float]] = field(default_factory=list)  # 候选走法


@dataclass
class EvalReport:
    """AI 评估报告"""

    ai_name: str
    backend: str  # python / rust
    timestamp: str
    config: dict  # depth, time_limit 等
    results: list[ScenarioResult]

    def to_html(self) -> str:
        """生成 HTML 报告"""
        # 计算统计
        total = len(self.results)
        total_time_ms = sum(r.time_ms for r in self.results)
        avg_score = sum(r.score for r in self.results) / total if total > 0 else 0

        # 构建场景行
        scenario_rows = []
        for r in self.results:
            score_class = "score-positive" if r.score >= 0 else "score-negative"
            nps = "-"  # 暂无 nodes 信息
            scenario_rows.append(
                f"""<tr>
                <td>{r.name}</td>
                <td><code>{r.best_move}</code></td>
                <td class="{score_class}">{r.score:+.0f}</td>
                <td>{r.time_ms:.0f}ms</td>
                <td>{nps}</td>
            </tr>"""
            )

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
        <p><b>AI:</b> {self.ai_name} ({self.backend})</p>
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
            <th>Scenario</th>
            <th>Best Move</th>
            <th>Score</th>
            <th>Time</th>
            <th>NPS</th>
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
    backend: str,
    scenarios: list[tuple[str, str]] | None = None,
    config: dict | None = None,
) -> EvalReport:
    """运行评估并生成报告

    Args:
        strategy: AI 策略名称
        backend: 后端类型 ("python" 或 "rust")
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
        backend=backend,
        strategy=strategy,
        depth=config.get("depth", 4),
        time_limit=config.get("time_limit"),
    )

    results: list[ScenarioResult] = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.info(f"Evaluating {strategy} ({backend}) on {len(scenarios)} scenarios...")

    for name, fen in scenarios:
        start = time.perf_counter()
        try:
            moves = engine.get_best_moves(fen, n=5)
            elapsed_ms = (time.perf_counter() - start) * 1000

            if moves:
                best_move, score = moves[0]
            else:
                best_move, score = "-", 0.0

            results.append(
                ScenarioResult(
                    name=name,
                    fen=fen,
                    best_move=best_move,
                    score=score,
                    time_ms=elapsed_ms,
                    candidates=moves,
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
        backend=backend,
        timestamp=timestamp,
        config=config,
        results=results,
    )
