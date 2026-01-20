"""对局日志系统

存储和读取对局日志:
- .txt 文件: 人类可读摘要
- .zip 文件: 详细数据 (程序读取)
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

import arrow

LOG_DIR = Path("data/game_logs")


@dataclass
class GameConfig:
    """对局配置"""

    red_strategy: str
    black_strategy: str
    time_limit: float = 0.2
    max_moves: int = 100


@dataclass
class GameResult:
    """单局结果摘要"""

    id: str
    name: str
    category: str
    result: str  # red_win | black_win | draw
    moves: int
    time_ms: float = 0


@dataclass
class GameDetail:
    """单局详情"""

    endgame_id: str
    name: str
    category: str
    start_fen: str
    result: str
    total_moves: int
    duration_ms: float
    final_fen: str
    history: list[dict]


# =============================================================================
# 日志保存
# =============================================================================


def save_log(
    run_id: str,
    config: GameConfig,
    results: list[GameResult],
    game_details: dict[str, GameDetail],
    duration_seconds: float = 0,
) -> tuple[Path, Path]:
    """
    保存日志

    Args:
        run_id: 运行 ID (如 20260120_143000_it2_vs_it2)
        config: 对局配置
        results: 每局结果摘要列表
        game_details: 每局详情 {endgame_id: GameDetail}
        duration_seconds: 总耗时

    Returns:
        (txt_path, zip_path)
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    txt_path = LOG_DIR / f"{run_id}.txt"
    zip_path = LOG_DIR / f"{run_id}.zip"

    # 统计
    red_win = sum(1 for r in results if r.result == "red_win")
    black_win = sum(1 for r in results if r.result == "black_win")
    draw = sum(1 for r in results if r.result == "draw")
    total = len(results)

    # 写 txt
    _write_txt_summary(
        txt_path, run_id, config, results, red_win, black_win, draw, duration_seconds
    )

    # 写 zip
    _write_zip_details(
        zip_path, run_id, config, results, game_details, red_win, black_win, draw, duration_seconds
    )

    return txt_path, zip_path


def _write_txt_summary(
    path: Path,
    run_id: str,
    config: GameConfig,
    results: list[GameResult],
    red_win: int,
    black_win: int,
    draw: int,
    duration_seconds: float,
) -> None:
    """写人类可读摘要"""
    total = len(results)
    timestamp = arrow.now().format("YYYY-MM-DD HH:mm:ss")
    duration_min = duration_seconds / 60 if duration_seconds > 0 else 0

    lines = [
        "=" * 50,
        "Jieqi Game Log",
        "=" * 50,
        f"Run ID:    {run_id}",
        f"Time:      {timestamp}",
        f"Strategy:  {config.red_strategy} vs {config.black_strategy}",
        f"Settings:  time={config.time_limit}s, max_moves={config.max_moves}",
        f"Duration:  {duration_min:.1f} min",
        "-" * 50,
        "",
        "SUMMARY",
        f"  Total:     {total}",
        f"  Red Win:   {red_win} ({100 * red_win / total:.1f}%)" if total > 0 else "  Red Win:   0",
        f"  Black Win: {black_win} ({100 * black_win / total:.1f}%)"
        if total > 0
        else "  Black Win: 0",
        f"  Draw:      {draw} ({100 * draw / total:.1f}%)" if total > 0 else "  Draw:      0",
        "",
        "-" * 50,
        "RESULTS",
        "-" * 50,
        f"  {'ID':<8} {'Name':<16} {'Result':<8} {'Moves':<6}",
        "-" * 50,
    ]

    # 结果列表
    result_icons = {"red_win": "🔴", "black_win": "⚫", "draw": "🤝"}
    for r in results:
        icon = result_icons.get(r.result, "?")
        lines.append(f"  {r.id:<8} {r.name:<16} {icon:<8} {r.moves:<6}")

    # 和棋列表
    draws = [r for r in results if r.result == "draw"]
    if draws:
        lines.extend(["", "-" * 50, f"DRAWS ({len(draws)}):"])
        for r in draws[:50]:  # 最多显示 50 条
            lines.append(f"  {r.id} {r.name} ({r.moves} moves)")
        if len(draws) > 50:
            lines.append(f"  ... and {len(draws) - 50} more")

    # 黑胜列表
    black_wins = [r for r in results if r.result == "black_win"]
    if black_wins:
        lines.extend(["", "-" * 50, f"BLACK WINS ({len(black_wins)}):"])
        for r in black_wins[:50]:
            lines.append(f"  {r.id} {r.name} ({r.moves} moves)")
        if len(black_wins) > 50:
            lines.append(f"  ... and {len(black_wins) - 50} more")

    lines.extend(["", "=" * 50, f"Details: {run_id}.zip", "=" * 50])

    path.write_text("\n".join(lines), encoding="utf-8")


def _write_zip_details(
    path: Path,
    run_id: str,
    config: GameConfig,
    results: list[GameResult],
    game_details: dict[str, GameDetail],
    red_win: int,
    black_win: int,
    draw: int,
    duration_seconds: float,
) -> None:
    """写 ZIP 详情"""
    timestamp = arrow.now().isoformat()

    # summary.json
    summary = {
        "run_id": run_id,
        "timestamp": timestamp,
        "config": asdict(config),
        "total_games": len(results),
        "results": {"red_win": red_win, "black_win": black_win, "draw": draw},
        "duration_seconds": duration_seconds,
        "games": [asdict(r) for r in results],
    }

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 写 summary.json
        zf.writestr("summary.json", json.dumps(summary, ensure_ascii=False, indent=2))

        # 写每局详情
        for endgame_id, detail in game_details.items():
            detail_dict = asdict(detail)
            zf.writestr(f"{endgame_id}.json", json.dumps(detail_dict, ensure_ascii=False, indent=2))


# =============================================================================
# 日志读取
# =============================================================================


def list_logs() -> list[dict]:
    """
    列出所有日志

    Returns:
        [{"run_id": "...", "path": Path, "strategy": "it2_vs_it2", "date": "2026-01-20"}, ...]
    """
    if not LOG_DIR.exists():
        return []

    logs = []
    for f in LOG_DIR.glob("*.zip"):
        run_id = f.stem
        parts = run_id.split("_")

        # 解析日期: YYYYMMDD
        date_str = ""
        if len(parts) >= 1 and len(parts[0]) == 8:
            try:
                date_str = f"{parts[0][:4]}-{parts[0][4:6]}-{parts[0][6:8]}"
            except Exception:
                pass

        # 解析策略: 从第三部分开始
        strategy = "_".join(parts[2:]) if len(parts) > 2 else "unknown"

        logs.append({"run_id": run_id, "path": f, "strategy": strategy, "date": date_str})

    return sorted(logs, key=lambda x: x["run_id"], reverse=True)


def load_summary(zip_path: Path) -> dict:
    """从 zip 读取 summary.json"""
    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open("summary.json") as f:
            return json.load(f)


def load_game(zip_path: Path, endgame_id: str) -> dict:
    """从 zip 读取单局详情"""
    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open(f"{endgame_id}.json") as f:
            return json.load(f)


def search_logs(
    strategy: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """搜索日志"""
    logs = list_logs()

    if strategy:
        logs = [lg for lg in logs if strategy.lower() in lg["strategy"].lower()]

    if date_from:
        logs = [lg for lg in logs if lg["date"] >= date_from]

    if date_to:
        logs = [lg for lg in logs if lg["date"] <= date_to]

    return logs


# =============================================================================
# 辅助函数
# =============================================================================


def generate_run_id(red_strategy: str, black_strategy: str) -> str:
    """生成运行 ID"""
    timestamp = arrow.now().format("YYYYMMDD_HHmmss")
    return f"{timestamp}_{red_strategy}_vs_{black_strategy}"
