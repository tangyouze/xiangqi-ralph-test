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
        move = current_ai.select_move(game)

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


if __name__ == "__main__":
    app()
