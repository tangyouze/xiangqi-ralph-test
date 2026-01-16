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
from jieqi.types import ActionType, Color, GameResult

console = Console()
app = typer.Typer()

# 可用策略列表
AVAILABLE_STRATEGIES = ["random", "greedy", "minimax", "iterative", "mcts", "muses"]


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

        # 计时并获取最佳走法
        start_time = time.time()
        candidates = current_ai.get_best_moves(fen_before, n=5)
        elapsed_ms = (time.time() - start_time) * 1000

        if not candidates:
            break

        move_str, score = candidates[0]
        move, _ = parse_move(move_str)

        if move is None:
            break

        # 执行走法前检查是否是揭子走法
        piece = game.board.get_piece(move.from_pos)
        was_hidden = piece.is_hidden if piece else False

        # 执行走法
        success = game.make_move(move)
        if not success:
            break

        move_count += 1

        # 获取揭开的棋子类型
        revealed_type = None
        if was_hidden and move.action_type == ActionType.REVEAL_AND_MOVE:
            # 走法执行后，棋子已经揭开，从走法记录中获取
            if game.move_history:
                last_record = game.move_history[-1]
                revealed_type = last_record.revealed_type

        # 获取走完后的 FEN
        fen_after = to_fen(game.get_view(game.current_turn))

        # 估算搜索节点数（Rust AI 不返回这个，用时间估算）
        # 假设每秒搜索 10000 节点
        estimated_nodes = int(elapsed_ms * 10)
        nps = int(estimated_nodes / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0

        # 更新统计
        if player == "red":
            stats["red_nodes"] += estimated_nodes
        else:
            stats["black_nodes"] += estimated_nodes

        # 记录日志
        if log_file:
            move_record = {
                "type": "move",
                "move_num": move_count,
                "player": player,
                "ai_name": ai_name,
                "move": move_str,
                "score": score,
                "nodes": estimated_nodes,
                "nps": nps,
                "depth": 3,
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
    ai_red: str = typer.Option("muses", "--red", "-r", help="Red AI strategy"),
    ai_black: str = typer.Option("minimax", "--black", "-b", help="Black AI strategy"),
    num_games: int = typer.Option(10, "--games", "-n", help="Number of games"),
    max_moves: int = typer.Option(300, "--max-moves", "-m", help="Max moves per game"),
    seed: int | None = typer.Option(42, "--seed", "-s", help="Random seed"),
    time_limit: float = typer.Option(
        0.1, "--time", "-t", help="AI thinking time per move (seconds)"
    ),
    log_dir: str | None = typer.Option(None, "--log-dir", "-l", help="Log directory"),
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
    console.print(f"Log dir: {log_path}\n")

    # 运行对战
    results = {"red_win": 0, "black_win": 0, "draw": 0}
    total_moves = 0
    game_ids = []

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
        "minimax": "Minimax with alpha-beta pruning",
        "iterative": "Iterative deepening search",
        "mcts": "Monte Carlo Tree Search",
        "muses": "Advanced hybrid strategy (recommended)",
    }

    for name in AVAILABLE_STRATEGIES:
        table.add_row(name, descriptions.get(name, ""))

    console.print(table)


@app.command()
def compare(
    num_games: int = typer.Option(10, "--games", "-n", help="Number of games per direction"),
    max_moves: int = typer.Option(300, "--max-moves", "-m", help="Max moves per game"),
    seed: int | None = typer.Option(42, "--seed", "-s", help="Random seed"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output JSON file"),
    strategies_filter: str | None = typer.Option(
        None, "--filter", "-f", help="Comma-separated list of strategies to include"
    ),
    time_limit: float = typer.Option(
        0.1, "--time", "-t", help="AI thinking time per move (seconds)"
    ),
    workers: int = typer.Option(10, "--workers", "-w", help="Number of parallel workers"),
    log_dir: str | None = typer.Option(None, "--log-dir", "-l", help="Log directory"),
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
