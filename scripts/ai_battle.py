"""
AI 对战脚本

让两个 AI 对战多次，统计胜率
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

# 导入 AI 策略以触发注册
from jieqi.ai import strategies  # noqa: F401
from jieqi.ai.base import AIConfig, AIEngine
from jieqi.fen import parse_move, to_fen
from jieqi.game import JieqiGame
from jieqi.types import Color, GameResult

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


def would_cause_draw(game: JieqiGame, move) -> bool:
    """预判走这步是否会导致和棋或增加重复局面

    检测：
    1. 走完后是否立即和棋（重复3次）
    2. 走完后的局面是否已经出现过（避免走入重复）
    """
    game.make_move(move)
    is_draw = game.result == GameResult.DRAW
    # 检查当前局面是否已经出现过（出现2次就危险了）
    is_repeated = game.get_position_count() >= 2
    game.undo_move()
    return is_draw or is_repeated


def run_single_game(
    ai_red: str,
    ai_black: str,
    max_moves: int = 1000,
    seed: int | None = None,
    avoid_draw: bool = True,
    time_limit: float | None = None,
) -> tuple[GameResult, int, dict]:
    """运行单场对战

    Args:
        ai_red: 红方 AI 名称
        ai_black: 黑方 AI 名称
        max_moves: 最大步数
        seed: 随机种子
        avoid_draw: 是否启用和棋规避（使用 Top-N 候选）
        time_limit: AI 思考时间限制（秒）

    Returns:
        (结果, 步数, 统计信息)
    """
    game = JieqiGame()

    red_config = AIConfig(seed=seed, time_limit=time_limit)
    black_config = AIConfig(seed=seed + 1 if seed else None, time_limit=time_limit)
    red_ai = AIEngine.create(ai_red, red_config)
    black_ai = AIEngine.create(ai_black, black_config)

    # 统计信息
    stats = {"red_nodes": 0, "black_nodes": 0, "red_depth": 0, "black_depth": 0}

    move_count = 0

    while game.result == GameResult.ONGOING and move_count < max_moves:
        current_ai = red_ai if game.current_turn == Color.RED else black_ai
        # 使用统一的 FEN 接口
        view = game.get_view(game.current_turn)
        fen = to_fen(view)

        # 选择走法
        move = None
        if avoid_draw:
            # 使用 Top-N 候选，规避和棋
            candidates = current_ai.select_moves_fen(fen, n=10)
            for move_str, _score in candidates:
                candidate_move, _ = parse_move(move_str)
                if not would_cause_draw(game, candidate_move):
                    move = candidate_move
                    break
            # 如果所有候选都会和棋，选第一个
            if move is None and candidates:
                move, _ = parse_move(candidates[0][0])
        else:
            candidates = current_ai.select_moves_fen(fen, n=1)
            if candidates:
                move, _ = parse_move(candidates[0][0])

        if move is None:
            # 无合法走法，当前方输
            if game.current_turn == Color.RED:
                return GameResult.BLACK_WIN, move_count, stats
            else:
                return GameResult.RED_WIN, move_count, stats

        # 收集统计信息
        nodes = getattr(current_ai, "_nodes_evaluated", 0)
        depth = 0
        if hasattr(current_ai, "_best_move_at_depth") and current_ai._best_move_at_depth:
            depth = max(current_ai._best_move_at_depth.keys())

        if game.current_turn == Color.RED:
            stats["red_nodes"] += nodes
            stats["red_depth"] = max(stats["red_depth"], depth)
        else:
            stats["black_nodes"] += nodes
            stats["black_depth"] = max(stats["black_depth"], depth)

        success = game.make_move(move)
        if not success:
            # 走棋失败（不应该发生）
            console.print(f"[red]Error: Move failed at step {move_count}[/red]")
            break

        move_count += 1

    # 超过最大步数算平局
    if game.result == GameResult.ONGOING:
        return GameResult.DRAW, move_count, stats

    return game.result, move_count, stats


def run_battle(
    ai_red: str,
    ai_black: str,
    num_games: int = 100,
    max_moves: int = 1000,
    seed: int | None = None,
    avoid_draw: bool = True,
    time_limit: float | None = None,
) -> dict:
    """运行多场对战

    Args:
        ai_red: 红方 AI 名称
        ai_black: 黑方 AI 名称
        num_games: 对战场数
        max_moves: 每场最大步数
        seed: 随机种子
        avoid_draw: 是否启用和棋规避
        time_limit: AI 思考时间限制（秒）

    Returns:
        统计结果
    """
    battle_stats = {
        "red_wins": 0,
        "black_wins": 0,
        "draws": 0,
        "total_moves": 0,
        "total_red_nodes": 0,
        "total_black_nodes": 0,
        "max_red_depth": 0,
        "max_black_depth": 0,
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
            result, moves, game_stats = run_single_game(
                ai_red, ai_black, max_moves, game_seed, avoid_draw, time_limit
            )

            battle_stats["total_moves"] += moves
            battle_stats["total_red_nodes"] += game_stats["red_nodes"]
            battle_stats["total_black_nodes"] += game_stats["black_nodes"]
            battle_stats["max_red_depth"] = max(
                battle_stats["max_red_depth"], game_stats["red_depth"]
            )
            battle_stats["max_black_depth"] = max(
                battle_stats["max_black_depth"], game_stats["black_depth"]
            )
            battle_stats["games"].append({"result": result, "moves": moves, "stats": game_stats})

            if result == GameResult.RED_WIN:
                battle_stats["red_wins"] += 1
            elif result == GameResult.BLACK_WIN:
                battle_stats["black_wins"] += 1
            else:
                battle_stats["draws"] += 1

            progress.update(task, advance=1)

    battle_stats["avg_moves"] = battle_stats["total_moves"] / num_games
    return battle_stats


@app.command()
def battle(
    ai_red: str = typer.Option("random", "--red", "-r", help="Red AI strategy"),
    ai_black: str = typer.Option("random", "--black", "-b", help="Black AI strategy"),
    num_games: int = typer.Option(100, "--games", "-n", help="Number of games"),
    max_moves: int = typer.Option(
        1000, "--max-moves", "-m", help="Max moves per game (draw if exceeded)"
    ),
    seed: int | None = typer.Option(None, "--seed", "-s", help="Random seed for reproducibility"),
    avoid_draw: bool = typer.Option(
        True, "--avoid-draw/--no-avoid-draw", help="Avoid draw by choosing alternative moves"
    ),
    time_limit: float = typer.Option(
        1.0, "--time", "-t", help="AI thinking time limit per move (seconds)"
    ),
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

    console.print("\n[bold]Jieqi AI Battle[/bold]")
    console.print(f"Red: [red]{ai_red}[/red] vs Black: [blue]{ai_black}[/blue]")
    console.print(
        f"Games: {num_games}, Max moves: {max_moves}, Time: {time_limit}s, "
        f"Avoid draw: {avoid_draw}\n"
    )

    stats = run_battle(ai_red, ai_black, num_games, max_moves, seed, avoid_draw, time_limit)

    # 显示结果
    table = Table(title="Battle Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row(
        "Red Wins", f"[red]{stats['red_wins']}[/red] ({stats['red_wins'] / num_games * 100:.1f}%)"
    )
    table.add_row(
        "Black Wins",
        f"[blue]{stats['black_wins']}[/blue] ({stats['black_wins'] / num_games * 100:.1f}%)",
    )
    table.add_row("Draws", f"{stats['draws']} ({stats['draws'] / num_games * 100:.1f}%)")
    table.add_row("Avg Moves", f"{stats['avg_moves']:.1f}")

    # 搜索统计
    avg_red_nodes = stats["total_red_nodes"] / max(stats["total_moves"], 1)
    avg_black_nodes = stats["total_black_nodes"] / max(stats["total_moves"], 1)
    table.add_row("Red Avg Nodes/Move", f"{avg_red_nodes:,.0f}")
    table.add_row("Black Avg Nodes/Move", f"{avg_black_nodes:,.0f}")
    table.add_row("Red Max Depth", f"{stats['max_red_depth']}")
    table.add_row("Black Max Depth", f"{stats['max_black_depth']}")

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
    strategy_list = AIEngine.list_strategies()

    table = Table(title="Available AI Strategies")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for s in strategy_list:
        table.add_row(s["name"], s["description"])

    console.print(table)


@app.command()
def verbose_battle(
    ai_red: str = typer.Option("muses", "--red", "-r", help="Red AI strategy"),
    ai_black: str = typer.Option("muses2", "--black", "-b", help="Black AI strategy"),
    max_moves: int = typer.Option(100, "--max-moves", "-m", help="Max moves per game"),
    seed: int | None = typer.Option(42, "--seed", "-s", help="Random seed"),
    time_limit: float = typer.Option(
        1.0, "--time", "-t", help="AI thinking time per move (seconds)"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Only output to log file, no console output"
    ),
    log_dir: str | None = typer.Option(
        None, "--log-dir", "-l", help="Log directory (default: battle_logs/)"
    ),
):
    """Run a single game with detailed logging to JSONL file"""
    import time

    from jieqi.ai.battle_log import BattleLogger

    # 创建日志记录器
    logger = BattleLogger(
        red_ai=ai_red,
        black_ai=ai_black,
        log_dir=log_dir,
        time_limit=time_limit,
        max_moves=max_moves,
        seed=seed,
    )

    game = JieqiGame()
    red_ai_instance = AIEngine.create(ai_red, AIConfig(seed=seed, time_limit=time_limit))
    black_ai_instance = AIEngine.create(
        ai_black, AIConfig(seed=seed + 1 if seed else None, time_limit=time_limit)
    )

    if not quiet:
        console.print(f"\n[bold]Battle: {ai_red} vs {ai_black}[/bold]")
        console.print(f"Time limit: {time_limit}s, Max moves: {max_moves}")
        console.print(f"Log file: {logger.log_path}\n")

    move_count = 0

    while game.result == GameResult.ONGOING and move_count < max_moves:
        current_ai = red_ai_instance if game.current_turn == Color.RED else black_ai_instance
        ai_name = ai_red if game.current_turn == Color.RED else ai_black
        player = "red" if game.current_turn == Color.RED else "black"

        view = game.get_view(game.current_turn)

        if not view.legal_moves:
            break

        # 计时
        start_time = time.time()
        candidates = current_ai.select_moves(view, n=5)
        elapsed_ms = (time.time() - start_time) * 1000

        if not candidates:
            break

        best_move, best_score = candidates[0]

        # 收集统计
        nodes = getattr(current_ai, "_nodes_evaluated", 0)
        depth = 0
        if hasattr(current_ai, "_best_move_at_depth") and current_ai._best_move_at_depth:
            depth = max(current_ai._best_move_at_depth.keys())

        tt_hits = getattr(current_ai, "_tt", None)
        tt_hits_count = tt_hits.hits if tt_hits else 0
        tt_misses_count = tt_hits.misses if tt_hits else 0

        move_count += 1

        # 记录到日志
        logger.log_move(
            move_num=move_count,
            player=player,
            ai_name=ai_name,
            move=best_move,
            score=best_score,
            nodes=nodes,
            depth=depth,
            tt_hits=tt_hits_count,
            tt_misses=tt_misses_count,
            candidates=candidates,
            elapsed_ms=elapsed_ms,
        )

        # 简洁的控制台输出
        if not quiet:
            color = "[red]R[/red]" if player == "red" else "[blue]B[/blue]"
            console.print(
                f"  {move_count:3}. {color} {ai_name:10} | "
                f"score={best_score:+7.1f} | nodes={nodes:>6,} | depth={depth} | "
                f"{elapsed_ms:.0f}ms"
            )

        game.make_move(best_move)

    # 确定结果
    if game.result == GameResult.RED_WIN:
        result = "red_win"
    elif game.result == GameResult.BLACK_WIN:
        result = "black_win"
    elif game.result == GameResult.DRAW:
        result = "draw"
    else:
        result = "ongoing"

    # 记录游戏结束
    logger.log_game_end(result)

    if not quiet:
        console.print(f"\n[bold]Result: {result}[/bold]")
        console.print(f"[green]Log saved to: {logger.log_path}[/green]")


def _run_matchup_games(args: tuple) -> tuple[str, str, list[GameResult], dict]:
    """单个对战组合的多场比赛（用于多进程）"""
    ai_red, ai_black, num_games, max_moves, seed, time_limit = args
    results = []
    total_moves = 0
    total_red_nodes = 0
    total_black_nodes = 0
    max_red_depth = 0
    max_black_depth = 0

    for game_idx in range(num_games):
        game_seed = (seed + game_idx * 2) if seed else None
        result, moves, game_stats = run_single_game(
            ai_red, ai_black, max_moves, game_seed, True, time_limit
        )
        results.append(result)
        total_moves += moves
        total_red_nodes += game_stats.get("red_nodes", 0)
        total_black_nodes += game_stats.get("black_nodes", 0)
        max_red_depth = max(max_red_depth, game_stats.get("red_depth", 0))
        max_black_depth = max(max_black_depth, game_stats.get("black_depth", 0))

    stats = {
        "avg_moves": total_moves / num_games if num_games > 0 else 0,
        "total_red_nodes": total_red_nodes,
        "total_black_nodes": total_black_nodes,
        "avg_red_nodes": total_red_nodes / max(total_moves, 1),
        "avg_black_nodes": total_black_nodes / max(total_moves, 1),
        "max_red_depth": max_red_depth,
        "max_black_depth": max_black_depth,
    }
    return ai_red, ai_black, results, stats


@app.command()
def compare(
    num_games: int = typer.Option(10, "--games", "-n", help="Number of games per matchup"),
    max_moves: int = typer.Option(500, "--max-moves", "-m", help="Max moves per game"),
    seed: int | None = typer.Option(42, "--seed", "-s", help="Random seed"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output JSON file"),
    strategies_filter: str | None = typer.Option(
        None, "--filter", "-f", help="Comma-separated list of strategies to include"
    ),
    time_limit: float = typer.Option(
        1.0, "--time", "-t", help="AI thinking time limit per move (seconds)"
    ),
    workers: int = typer.Option(4, "--workers", "-w", help="Number of parallel workers"),
):
    """Run round-robin comparison between all AI strategies"""
    import json
    from concurrent.futures import ProcessPoolExecutor, as_completed

    # 获取策略列表
    all_strategies = AIEngine.get_strategy_names()

    if strategies_filter:
        selected = [s.strip() for s in strategies_filter.split(",")]
        strategies_list = [s for s in selected if s in all_strategies]
    else:
        strategies_list = all_strategies

    total_matchups = len(strategies_list) * (len(strategies_list) - 1)
    total_games = total_matchups * num_games

    console.print("\n[bold]AI Round-Robin Comparison[/bold]")
    console.print(f"Strategies: {len(strategies_list)}")
    console.print(f"Games per matchup: {num_games}")
    console.print(f"Total matchups: {total_matchups}")
    console.print(f"Total games: {total_games}")
    console.print(f"Time limit: {time_limit}s, Workers: {workers}\n")

    # 结果矩阵：results[row_ai][col_ai] = win_rate (row as red vs col as black)
    results: dict[str, dict[str, dict]] = {
        s1: {s2: {"wins": 0, "losses": 0, "draws": 0} for s2 in strategies_list}
        for s1 in strategies_list
    }

    # 所有对战组合
    matchup_args = []
    for idx, s1 in enumerate(strategies_list):
        for jdx, s2 in enumerate(strategies_list):
            if s1 != s2:
                matchup_seed = (seed + idx * 1000 + jdx * 100) if seed else None
                matchup_args.append((s1, s2, num_games, max_moves, matchup_seed, time_limit))

    completed = 0

    def process_matchup_result(ai_red: str, ai_black: str, game_results: list, stats: dict):
        """处理一个对战组合的结果"""
        nonlocal completed
        wins = sum(1 for r in game_results if r == GameResult.RED_WIN)
        losses = sum(1 for r in game_results if r == GameResult.BLACK_WIN)
        draws = len(game_results) - wins - losses

        results[ai_red][ai_black]["wins"] += wins
        results[ai_red][ai_black]["losses"] += losses
        results[ai_red][ai_black]["draws"] += draws
        results[ai_black][ai_red]["wins"] += losses
        results[ai_black][ai_red]["losses"] += wins
        results[ai_black][ai_red]["draws"] += draws

        completed += 1
        # 打印进度（包含节点统计）
        red_nps = stats.get("avg_red_nodes", 0)
        black_nps = stats.get("avg_black_nodes", 0)
        red_depth = stats.get("max_red_depth", 0)
        black_depth = stats.get("max_black_depth", 0)
        console.print(
            f"  [{completed:3}/{len(matchup_args)}] "
            f"[cyan]{ai_red:12}[/cyan] vs [magenta]{ai_black:12}[/magenta]: "
            f"[green]{wins}W[/green]-[red]{losses}L[/red]-{draws}D | "
            f"moves={stats['avg_moves']:.0f} | "
            f"nodes/move: {red_nps:,.0f} vs {black_nps:,.0f} | "
            f"depth: {red_depth} vs {black_depth}"
        )

    if workers > 1:
        # 多进程模式
        console.print(f"[bold]Running with {workers} workers...[/bold]\n")
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_run_matchup_games, args): args for args in matchup_args}
            for future in as_completed(futures):
                ai_red, ai_black, game_results, stats = future.result()
                process_matchup_result(ai_red, ai_black, game_results, stats)
    else:
        # 单进程模式
        console.print("[bold]Running in single process mode...[/bold]\n")
        for args in matchup_args:
            ai_red, ai_black, game_results, stats = _run_matchup_games(args)
            process_matchup_result(ai_red, ai_black, game_results, stats)

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
                total = (
                    results[s1][s2]["wins"] + results[s1][s2]["losses"] + results[s1][s2]["draws"]
                )
                rate = wins / total * 100 if total > 0 else 0
                # 颜色编码
                if rate >= 70:
                    cell = f"[green]{rate:.0f}%[/green]"
                elif rate >= 50:
                    cell = f"[yellow]{rate:.0f}%[/yellow]"
                else:
                    cell = f"[red]{rate:.0f}%[/red]"
                row.append(cell)
        row.append(f"{scores[s1] * 100:.1f}%")
        table.add_row(*row)

    console.print(table)

    # 排名
    console.print("\n[bold]Final Rankings (Win Rate | Elo):[/bold]")
    sorted(strategies_list, key=lambda s: elo[s], reverse=True)
    for i, s in enumerate(sorted_strategies, 1):
        console.print(f"  {i:2}. {s:15} - {scores[s] * 100:.1f}% | Elo: {elo[s]:.0f}")

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
