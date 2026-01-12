"""
AI 对战脚本

让两个 AI 对战多次，统计胜率
"""

import sys
from pathlib import Path

# 添加 backend 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from jieqi.game import JieqiGame
from jieqi.types import Color, GameResult
from jieqi.ai.base import AIEngine, AIConfig

# 导入 AI 策略以触发注册
from jieqi.ai import strategies  # noqa: F401

console = Console()
app = typer.Typer()


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
    elo = {s: initial_elo for s in strategies_list}

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


def run_single_game(
    ai_red: str,
    ai_black: str,
    max_moves: int = 1000,
    seed: int | None = None,
) -> tuple[GameResult, int]:
    """运行单场对战

    Returns:
        (结果, 步数)
    """
    game = JieqiGame()

    red_ai = AIEngine.create(ai_red, AIConfig(seed=seed))
    black_ai = AIEngine.create(ai_black, AIConfig(seed=seed + 1 if seed else None))

    move_count = 0

    while game.result == GameResult.ONGOING and move_count < max_moves:
        current_ai = red_ai if game.current_turn == Color.RED else black_ai
        # AI 使用 PlayerView 而不是直接访问 game
        view = game.get_view(game.current_turn)
        move = current_ai.select_move(view)

        if move is None:
            # 无合法走法，当前方输
            if game.current_turn == Color.RED:
                return GameResult.BLACK_WIN, move_count
            else:
                return GameResult.RED_WIN, move_count

        success = game.make_move(move)
        if not success:
            # 走棋失败（不应该发生）
            console.print(f"[red]Error: Move failed at step {move_count}[/red]")
            break

        move_count += 1

    # 超过最大步数算平局
    if game.result == GameResult.ONGOING:
        return GameResult.DRAW, move_count

    return game.result, move_count


def run_battle(
    ai_red: str,
    ai_black: str,
    num_games: int = 100,
    max_moves: int = 1000,
    seed: int | None = None,
) -> dict:
    """运行多场对战

    Returns:
        统计结果
    """
    stats = {
        "red_wins": 0,
        "black_wins": 0,
        "draws": 0,
        "total_moves": 0,
        "games": [],
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]{ai_red} vs {ai_black}...", total=num_games)

        for i in range(num_games):
            game_seed = seed + i * 2 if seed else None
            result, moves = run_single_game(ai_red, ai_black, max_moves, game_seed)

            stats["total_moves"] += moves
            stats["games"].append({"result": result, "moves": moves})

            if result == GameResult.RED_WIN:
                stats["red_wins"] += 1
            elif result == GameResult.BLACK_WIN:
                stats["black_wins"] += 1
            else:
                stats["draws"] += 1

            progress.update(task, advance=1)

    stats["avg_moves"] = stats["total_moves"] / num_games
    return stats


@app.command()
def battle(
    ai_red: str = typer.Option("random", "--red", "-r", help="Red AI strategy"),
    ai_black: str = typer.Option("random", "--black", "-b", help="Black AI strategy"),
    num_games: int = typer.Option(100, "--games", "-n", help="Number of games"),
    max_moves: int = typer.Option(1000, "--max-moves", "-m", help="Max moves per game (draw if exceeded)"),
    seed: int | None = typer.Option(None, "--seed", "-s", help="Random seed for reproducibility"),
):
    """Run AI vs AI battle"""

    # 列出可用策略
    available = AIEngine.get_strategy_names()
    if ai_red not in available:
        console.print(f"[red]Unknown AI: {ai_red}. Available: {available}[/red]")
        raise typer.Exit(1)
    if ai_black not in available:
        console.print(f"[red]Unknown AI: {ai_black}. Available: {available}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Jieqi AI Battle[/bold]")
    console.print(f"Red: [red]{ai_red}[/red] vs Black: [blue]{ai_black}[/blue]")
    console.print(f"Games: {num_games}, Max moves: {max_moves}\n")

    stats = run_battle(ai_red, ai_black, num_games, max_moves, seed)

    # 显示结果
    table = Table(title="Battle Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Red Wins", f"[red]{stats['red_wins']}[/red] ({stats['red_wins']/num_games*100:.1f}%)")
    table.add_row("Black Wins", f"[blue]{stats['black_wins']}[/blue] ({stats['black_wins']/num_games*100:.1f}%)")
    table.add_row("Draws", f"{stats['draws']} ({stats['draws']/num_games*100:.1f}%)")
    table.add_row("Avg Moves", f"{stats['avg_moves']:.1f}")

    console.print(table)

    # 显示胜负分布
    console.print("\n[bold]Move distribution:[/bold]")
    move_ranges = {"<100": 0, "100-300": 0, "300-500": 0, "500-1000": 0, "1000 (draw)": 0}
    for game in stats["games"]:
        moves = game["moves"]
        if moves >= 1000:
            move_ranges["1000 (draw)"] += 1
        elif moves >= 500:
            move_ranges["500-1000"] += 1
        elif moves >= 300:
            move_ranges["300-500"] += 1
        elif moves >= 100:
            move_ranges["100-300"] += 1
        else:
            move_ranges["<100"] += 1

    for range_name, count in move_ranges.items():
        bar = "█" * (count * 40 // num_games)
        console.print(f"  {range_name:12} {bar} {count}")


@app.command()
def list_ai():
    """List available AI strategies"""
    strategies = AIEngine.list_strategies()

    table = Table(title="Available AI Strategies")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for s in strategies:
        table.add_row(s["name"], s["description"])

    console.print(table)


@app.command()
def compare(
    num_games: int = typer.Option(10, "--games", "-n", help="Number of games per matchup"),
    max_moves: int = typer.Option(500, "--max-moves", "-m", help="Max moves per game"),
    seed: int | None = typer.Option(42, "--seed", "-s", help="Random seed"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output JSON file"),
    strategies_filter: str | None = typer.Option(None, "--filter", "-f", help="Comma-separated list of strategies to include"),
):
    """Run round-robin comparison between all AI strategies"""
    import json
    from itertools import combinations
    from concurrent.futures import ProcessPoolExecutor, as_completed

    # 获取策略列表
    all_strategies = AIEngine.get_strategy_names()

    if strategies_filter:
        selected = [s.strip() for s in strategies_filter.split(",")]
        strategies_list = [s for s in selected if s in all_strategies]
    else:
        strategies_list = all_strategies

    console.print(f"\n[bold]AI Round-Robin Comparison[/bold]")
    console.print(f"Strategies: {len(strategies_list)}")
    console.print(f"Games per matchup: {num_games}")
    console.print(f"Matchups: {len(strategies_list) * (len(strategies_list) - 1)}\n")

    # 结果矩阵：results[row_ai][col_ai] = win_rate (row as red vs col as black)
    results: dict[str, dict[str, dict]] = {
        s1: {s2: {"wins": 0, "losses": 0, "draws": 0} for s2 in strategies_list}
        for s1 in strategies_list
    }

    # 所有对战组合
    matchups = []
    for s1 in strategies_list:
        for s2 in strategies_list:
            if s1 != s2:
                matchups.append((s1, s2))

    total_matchups = len(matchups)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Running matchups...", total=total_matchups)

        for idx, (ai_red, ai_black) in enumerate(matchups):
            # 运行多场对战
            for game_idx in range(num_games):
                game_seed = (seed + idx * num_games + game_idx * 2) if seed else None
                result, _ = run_single_game(ai_red, ai_black, max_moves, game_seed)

                if result == GameResult.RED_WIN:
                    results[ai_red][ai_black]["wins"] += 1
                    results[ai_black][ai_red]["losses"] += 1
                elif result == GameResult.BLACK_WIN:
                    results[ai_red][ai_black]["losses"] += 1
                    results[ai_black][ai_red]["wins"] += 1
                else:
                    results[ai_red][ai_black]["draws"] += 1
                    results[ai_black][ai_red]["draws"] += 1

            progress.update(task, advance=1)

    # 计算胜率和综合得分
    scores: dict[str, float] = {}
    for s in strategies_list:
        total_wins = sum(results[s][opp]["wins"] for opp in strategies_list if opp != s)
        total_losses = sum(results[s][opp]["losses"] for opp in strategies_list if opp != s)
        total_draws = sum(results[s][opp]["draws"] for opp in strategies_list if opp != s)
        total_games = total_wins + total_losses + total_draws
        scores[s] = (total_wins + total_draws * 0.5) / total_games if total_games > 0 else 0

    # 计算 Elo 评分
    elo = calculate_elo(results, strategies_list)

    # 按得分排序
    sorted_strategies = sorted(strategies_list, key=lambda s: scores[s], reverse=True)

    # 显示结果表格
    console.print("\n[bold]Win Matrix (row=Red, col=Black)[/bold]")

    # 构建表格
    table = Table()
    table.add_column("AI", style="cyan")
    for s in sorted_strategies:
        table.add_column(s[:8], justify="center")
    table.add_column("Score", style="yellow", justify="right")

    for s1 in sorted_strategies:
        row = [s1[:10]]
        for s2 in sorted_strategies:
            if s1 == s2:
                row.append("-")
            else:
                wins = results[s1][s2]["wins"]
                total = results[s1][s2]["wins"] + results[s1][s2]["losses"] + results[s1][s2]["draws"]
                rate = wins / total * 100 if total > 0 else 0
                # 颜色编码
                if rate >= 70:
                    cell = f"[green]{rate:.0f}%[/green]"
                elif rate >= 50:
                    cell = f"[yellow]{rate:.0f}%[/yellow]"
                else:
                    cell = f"[red]{rate:.0f}%[/red]"
                row.append(cell)
        row.append(f"{scores[s1]*100:.1f}%")
        table.add_row(*row)

    console.print(table)

    # 排名
    console.print("\n[bold]Final Rankings (Win Rate | Elo):[/bold]")
    elo_sorted = sorted(strategies_list, key=lambda s: elo[s], reverse=True)
    for i, s in enumerate(sorted_strategies, 1):
        console.print(f"  {i:2}. {s:15} - {scores[s]*100:.1f}% | Elo: {elo[s]:.0f}")

    # 保存 JSON
    output_data = {
        "strategies": sorted_strategies,
        "num_games": num_games,
        "max_moves": max_moves,
        "results": {
            s1: {
                s2: {
                    "wins": results[s1][s2]["wins"],
                    "losses": results[s1][s2]["losses"],
                    "draws": results[s1][s2]["draws"],
                    "win_rate": results[s1][s2]["wins"] / num_games if num_games > 0 else 0,
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
        output_path.write_text(json.dumps(output_data, indent=2))
        console.print(f"\n[green]Results saved to {output}[/green]")
    else:
        # 默认保存到 data 目录
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        default_output = data_dir / "ai_comparison.json"
        default_output.write_text(json.dumps(output_data, indent=2))
        console.print(f"\n[green]Results saved to {default_output}[/green]")

    return output_data


if __name__ == "__main__":
    app()
