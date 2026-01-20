"""残局对战脚本

运行指定 AI 策略在所有残局上的对战，并生成报告。
"""

from __future__ import annotations

import json
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from engine.battle import BattleResult, run_battle
from engine.games.endgames import (
    ALL_ENDGAMES,
    BASIC_ENDGAMES,
    CLASSIC_ENDGAMES,
    MATE_DISTANCE_ENDGAMES,
    RANDOM_ENDGAMES,
    Endgame,
)

console = Console()
app = typer.Typer(invoke_without_command=True)


@dataclass
class EndgameResult:
    """单个残局对战结果"""

    endgame_id: str
    endgame_name: str
    category: str
    fen: str
    result: str  # "red_win" | "black_win" | "draw"
    total_moves: int
    red_strategy: str
    black_strategy: str


def run_single_endgame(args: tuple) -> EndgameResult:
    """运行单个残局对战（用于多进程）"""
    endgame_id, endgame_name, category, fen, red_strategy, black_strategy, time_limit, max_moves = (
        args
    )

    try:
        battle_result = run_battle(
            start_fen=fen,
            red_strategy=red_strategy,
            black_strategy=black_strategy,
            time_limit=time_limit,
            max_moves=max_moves,
            max_repetitions=3,
        )
        return EndgameResult(
            endgame_id=endgame_id,
            endgame_name=endgame_name,
            category=category,
            fen=fen,
            result=battle_result.result,
            total_moves=battle_result.total_moves,
            red_strategy=red_strategy,
            black_strategy=black_strategy,
        )
    except Exception as e:
        # 出错时返回 draw
        return EndgameResult(
            endgame_id=endgame_id,
            endgame_name=endgame_name,
            category=category,
            fen=fen,
            result=f"error: {e!s}",
            total_moves=0,
            red_strategy=red_strategy,
            black_strategy=black_strategy,
        )


def generate_html_report(
    results: list[EndgameResult],
    red_strategy: str,
    black_strategy: str,
    time_limit: float,
    output_path: Path,
) -> None:
    """生成 HTML 报告"""
    # 统计
    total = len(results)
    red_wins = sum(1 for r in results if r.result == "red_win")
    black_wins = sum(1 for r in results if r.result == "black_win")
    draws = sum(1 for r in results if r.result == "draw")
    errors = sum(1 for r in results if r.result.startswith("error"))

    # 按类别分组
    categories: dict[str, list[EndgameResult]] = {}
    for r in results:
        if r.category not in categories:
            categories[r.category] = []
        categories[r.category].append(r)

    # 生成 HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>残局对战报告 - {red_strategy} vs {black_strategy}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-box {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .stat-box .value {{
            font-size: 28px;
            font-weight: bold;
        }}
        .stat-box .label {{ color: #666; font-size: 14px; }}
        .red {{ color: #dc3545; }}
        .black {{ color: #0d6efd; }}
        .draw {{ color: #ffc107; }}
        .error {{ color: #6c757d; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .result-red {{ background: #ffe5e5; }}
        .result-black {{ background: #e5f0ff; }}
        .result-draw {{ background: #fff8e5; }}
        .result-error {{ background: #f5f5f5; }}
        .fen {{ font-family: monospace; font-size: 12px; color: #666; }}
        .category-header {{
            background: #333;
            color: white;
            padding: 10px 15px;
            margin-top: 25px;
            border-radius: 6px 6px 0 0;
        }}
        .timestamp {{ color: #999; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>残局对战报告</h1>

    <div class="summary">
        <h2 style="margin-top: 0;">对战配置</h2>
        <p><strong>红方:</strong> <span class="red">{red_strategy}</span> vs <strong>黑方:</strong> <span class="black">{black_strategy}</span></p>
        <p><strong>思考时间:</strong> {time_limit}s / 步</p>
        <p><strong>残局总数:</strong> {total}</p>

        <div class="summary-grid">
            <div class="stat-box">
                <div class="value red">{red_wins}</div>
                <div class="label">红方胜</div>
            </div>
            <div class="stat-box">
                <div class="value black">{black_wins}</div>
                <div class="label">黑方胜</div>
            </div>
            <div class="stat-box">
                <div class="value draw">{draws}</div>
                <div class="label">和棋</div>
            </div>
            <div class="stat-box">
                <div class="value error">{errors}</div>
                <div class="label">错误</div>
            </div>
            <div class="stat-box">
                <div class="value">{red_wins / total * 100:.1f}%</div>
                <div class="label">红方胜率</div>
            </div>
        </div>
    </div>

    <h2>按类别统计</h2>
"""

    # 按类别显示
    for category, cat_results in sorted(categories.items()):
        cat_total = len(cat_results)
        cat_red = sum(1 for r in cat_results if r.result == "red_win")
        cat_black = sum(1 for r in cat_results if r.result == "black_win")
        cat_draw = sum(1 for r in cat_results if r.result == "draw")

        html += f"""
    <div class="category-header">
        {category} ({cat_total} 局) -
        <span class="red">红胜 {cat_red}</span> |
        <span class="black">黑胜 {cat_black}</span> |
        <span class="draw">和 {cat_draw}</span>
    </div>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>名称</th>
                <th>结果</th>
                <th>步数</th>
                <th>FEN</th>
            </tr>
        </thead>
        <tbody>
"""
        for r in cat_results:
            result_class = {
                "red_win": "result-red",
                "black_win": "result-black",
                "draw": "result-draw",
            }.get(r.result, "result-error")

            result_text = {
                "red_win": '<span class="red">红胜</span>',
                "black_win": '<span class="black">黑胜</span>',
                "draw": '<span class="draw">和棋</span>',
            }.get(r.result, f'<span class="error">{r.result}</span>')

            html += f"""            <tr class="{result_class}">
                <td>{r.endgame_id}</td>
                <td>{r.endgame_name}</td>
                <td>{result_text}</td>
                <td>{r.total_moves}</td>
                <td class="fen">{r.fen}</td>
            </tr>
"""
        html += """        </tbody>
    </table>
"""

    html += f"""
    <p class="timestamp">报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
</body>
</html>
"""

    output_path.write_text(html, encoding="utf-8")


def generate_pdf_report(html_path: Path, pdf_path: Path) -> bool:
    """从 HTML 生成 PDF 报告"""
    import os

    # macOS 上 weasyprint 需要 homebrew 库路径
    if "DYLD_LIBRARY_PATH" not in os.environ:
        homebrew_lib = "/opt/homebrew/lib"
        if Path(homebrew_lib).exists():
            os.environ["DYLD_LIBRARY_PATH"] = homebrew_lib

    try:
        from weasyprint import HTML

        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        return True
    except ImportError:
        console.print("[yellow]weasyprint 未安装，跳过 PDF 生成[/yellow]")
        console.print("[dim]安装命令: uv add weasyprint[/dim]")
        return False
    except Exception as e:
        console.print(f"[red]PDF 生成失败: {e}[/red]")
        console.print("[dim]macOS 用户请运行: brew install pango gobject-introspection[/dim]")
        return False


@app.callback()
def main(
    red: str = typer.Option("it2", "--red", help="红方策略"),
    black: str = typer.Option("it2", "--black", help="黑方策略"),
    time_limit: float = typer.Option(0.2, "--time", help="AI 思考时间（秒）"),
    max_moves: int = typer.Option(200, "--max-moves", help="最大步数"),
    workers: int = typer.Option(8, "--workers", help="并发数"),
    output_dir: str = typer.Option(None, "--output", help="输出目录"),
    category: str = typer.Option(
        "all",
        "--category",
        help="残局类别: all, classic, mate_distance, random, basic",
    ),
):
    """运行残局对战并生成报告"""
    # 选择残局
    endgames: list[Endgame] = []
    if category == "all":
        endgames = ALL_ENDGAMES
    elif category == "classic":
        endgames = CLASSIC_ENDGAMES
    elif category == "mate_distance":
        endgames = MATE_DISTANCE_ENDGAMES
    elif category == "random":
        endgames = RANDOM_ENDGAMES
    elif category == "basic":
        endgames = BASIC_ENDGAMES
    else:
        console.print(f"[red]未知类别: {category}[/red]")
        raise typer.Exit(1)

    # 设置输出目录
    if output_dir:
        out_path = Path(output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = Path(__file__).parent.parent / "data" / "endgame_reports" / timestamp
    out_path.mkdir(parents=True, exist_ok=True)

    console.print("\n[bold]残局对战测试[/bold]")
    console.print(f"红方: [red]{red}[/red] vs 黑方: [blue]{black}[/blue]")
    console.print(f"类别: {category}, 残局数: {len(endgames)}")
    console.print(f"时间限制: {time_limit}s, 并发: {workers}")
    console.print(f"输出目录: {out_path}")
    console.print()

    # 构建任务
    tasks = [(e.id, e.name, e.category, e.fen, red, black, time_limit, max_moves) for e in endgames]

    results: list[EndgameResult] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
        console=console,
    ) as progress:
        task = progress.add_task(f"[green]对战中...", total=len(tasks))

        if workers > 1:
            # 使用 spawn 方式创建进程，避免 fork 问题
            ctx = mp.get_context("spawn")
            with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as executor:
                futures = {executor.submit(run_single_endgame, t): t for t in tasks}
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    progress.update(task, advance=1)
        else:
            for t in tasks:
                result = run_single_endgame(t)
                results.append(result)
                progress.update(task, advance=1)

    # 按 ID 排序结果
    results.sort(key=lambda r: r.endgame_id)

    # 统计
    total = len(results)
    red_wins = sum(1 for r in results if r.result == "red_win")
    black_wins = sum(1 for r in results if r.result == "black_win")
    draws = sum(1 for r in results if r.result == "draw")
    errors = sum(1 for r in results if r.result.startswith("error"))

    # 显示结果
    table = Table(title="对战结果汇总")
    table.add_column("项目", style="cyan")
    table.add_column("数量", justify="right")
    table.add_column("比例", justify="right")

    table.add_row("红方胜", f"[red]{red_wins}[/red]", f"{red_wins / total * 100:.1f}%")
    table.add_row("黑方胜", f"[blue]{black_wins}[/blue]", f"{black_wins / total * 100:.1f}%")
    table.add_row("和棋", f"[yellow]{draws}[/yellow]", f"{draws / total * 100:.1f}%")
    if errors > 0:
        table.add_row("错误", f"[dim]{errors}[/dim]", f"{errors / total * 100:.1f}%")
    table.add_row("总计", str(total), "100%")

    console.print(table)

    # 保存 JSON
    json_path = out_path / "results.json"
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "red_strategy": red,
            "black_strategy": black,
            "time_limit": time_limit,
            "max_moves": max_moves,
            "category": category,
        },
        "summary": {
            "total": total,
            "red_wins": red_wins,
            "black_wins": black_wins,
            "draws": draws,
            "errors": errors,
            "red_win_rate": red_wins / total,
        },
        "results": [asdict(r) for r in results],
    }
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"\n[green]JSON 结果已保存: {json_path}[/green]")

    # 生成 HTML
    html_path = out_path / "report.html"
    generate_html_report(results, red, black, time_limit, html_path)
    console.print(f"[green]HTML 报告已保存: {html_path}[/green]")

    # 生成 PDF
    pdf_path = out_path / "report.pdf"
    if generate_pdf_report(html_path, pdf_path):
        console.print(f"[green]PDF 报告已保存: {pdf_path}[/green]")


if __name__ == "__main__":
    app()
