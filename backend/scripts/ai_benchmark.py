"""
Python vs Rust AI 性能对比测试

比较两个后端的：
1. NPS (Nodes Per Second) - 搜索速度
2. 对战胜率
3. ELO 评分
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from jieqi.ai.unified import UnifiedAIEngine
from jieqi.fen import get_legal_moves_from_fen, apply_move_to_fen
from jieqi.types import PieceType

console = Console()
app = typer.Typer()

# 测试局面
TEST_POSITIONS = {
    "initial": "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r",
    "midgame": "xxxx1xxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXX1XXXX -:- r r",
    "endgame_rook": "4k4/9/9/9/9/9/9/9/4R4/3RK4 -:- r r",
    "endgame_cannon": "3ak4/9/9/9/9/9/9/5C3/4H4/4K4 -:- r r",
    "complex": "r1eak4/4a4/4e1h2/p1h1p3p/4c4/2P6/P3P3P/4E1H2/4A4/R2AK2R1 -:- r r",
}


def measure_nps(
    backend: str,
    strategy: str,
    fen: str,
    time_limit: float = 5.0,
    iterations: int = 3,
) -> dict:
    """测量单个位置的性能

    Args:
        time_limit: 思考时间限制（秒）
        iterations: 重复测试次数取平均

    Returns:
        dict with keys: time_per_call, best_move, score
    """
    # 使用时间限制而不是深度（深度设置为无限大）
    engine = UnifiedAIEngine(
        backend=backend,
        strategy=strategy,
        depth=100,  # 足够大的深度，让时间限制生效
        time_limit=time_limit,
    )

    # 多次测试取平均
    total_time = 0
    best_move = None
    best_score = 0

    for _ in range(iterations):
        start_time = time.time()
        moves = engine.get_best_moves(fen, n=5)
        elapsed = time.time() - start_time
        total_time += elapsed

        if moves:
            best_move = moves[0][0]
            best_score = moves[0][1]

    avg_time = total_time / iterations

    # 获取合法走法数量
    legal_moves = engine.get_legal_moves(fen)
    moves_count = len(legal_moves)

    # MPS = Moves per second（每秒能分析多少次）
    mps = 1 / avg_time if avg_time > 0 else 0

    return {
        "backend": backend,
        "strategy": strategy,
        "legal_moves": moves_count,
        "time_per_call": avg_time,
        "calls_per_second": mps,
        "best_move": best_move,
        "score": best_score,
    }


def run_game(
    red_backend: str,
    red_strategy: str,
    black_backend: str,
    black_strategy: str,
    max_moves: int = 200,
    time_limit: float = 5.0,
) -> dict:
    """运行一局对战

    使用残局（无暗子）避免揭子问题

    Returns:
        dict with keys: result, moves, red_time, black_time, history
    """
    # 使用残局（无暗子）
    fen = TEST_POSITIONS["endgame_rook"]

    # 使用时间限制而不是深度
    red_engine = UnifiedAIEngine(
        backend=red_backend,
        strategy=red_strategy,
        depth=100,
        time_limit=time_limit,
    )
    black_engine = UnifiedAIEngine(
        backend=black_backend,
        strategy=black_strategy,
        depth=100,
        time_limit=time_limit,
    )

    history = []
    red_total_time = 0
    black_total_time = 0
    move_count = 0
    current_turn = "red"  # FEN 中 'r r' 表示红方走，红方视角

    while move_count < max_moves:
        current_engine = red_engine if current_turn == "red" else black_engine

        # 获取合法走法
        legal_moves = current_engine.get_legal_moves(fen)
        if not legal_moves:
            # 无合法走法，当前方输
            result = "black_win" if current_turn == "red" else "red_win"
            break

        # AI 选择走法
        start_time = time.time()
        moves = current_engine.get_best_moves(fen, n=1)
        elapsed = time.time() - start_time

        if not moves:
            result = "black_win" if current_turn == "red" else "red_win"
            break

        best_move, score = moves[0]

        # 记录时间
        if current_turn == "red":
            red_total_time += elapsed
        else:
            black_total_time += elapsed

        # 执行走法
        try:
            # 残局无暗子，不需要处理揭子
            new_fen = apply_move_to_fen(fen, best_move, None)
            fen = new_fen
        except Exception as e:
            # 出错时结束游戏
            result = "error"
            break

        history.append(
            {
                "move_num": move_count + 1,
                "player": current_turn,
                "move": best_move,
                "score": score,
                "time": elapsed,
            }
        )

        move_count += 1

        # 检查是否结束（简化：只检查步数）
        # 真正的游戏结束判断需要检查将军、困毙等

        # 切换回合
        current_turn = "black" if current_turn == "red" else "red"

    # 超过最大步数算平局
    if move_count >= max_moves:
        result = "draw"
    elif "result" not in locals():
        result = "draw"

    return {
        "result": result,
        "moves": move_count,
        "red_time": red_total_time,
        "black_time": black_total_time,
        "red_avg_time": red_total_time / (move_count / 2) if move_count > 0 else 0,
        "black_avg_time": black_total_time / (move_count / 2) if move_count > 0 else 0,
        "history": history,
    }


def calculate_elo(results: list[dict], k: float = 32, initial: float = 1500) -> dict[str, float]:
    """从对战结果计算 ELO"""
    elo = {}

    # 收集所有参赛者
    for r in results:
        if r["red"] not in elo:
            elo[r["red"]] = initial
        if r["black"] not in elo:
            elo[r["black"]] = initial

    # 多轮迭代
    for _ in range(10):
        for r in results:
            red, black = r["red"], r["black"]
            result = r["result"]

            # 期望得分
            exp_red = 1 / (1 + 10 ** ((elo[black] - elo[red]) / 400))
            exp_black = 1 - exp_red

            # 实际得分
            if result == "red_win":
                actual_red, actual_black = 1, 0
            elif result == "black_win":
                actual_red, actual_black = 0, 1
            else:
                actual_red, actual_black = 0.5, 0.5

            # 更新
            elo[red] += k * (actual_red - exp_red)
            elo[black] += k * (actual_black - exp_black)

    return elo


@app.command()
def benchmark(
    time_limit: float = typer.Option(5.0, "--time", "-t", help="Time limit per move (seconds)"),
):
    """Benchmark performance for Python vs Rust backends"""

    console.print("\n[bold]AI Performance Benchmark[/bold]")
    console.print(f"Time limit: {time_limit}s per move\n")

    # 共同支持的策略
    # 注意：只有 iterative 策略能充分利用时间限制
    common_strategies = ["random", "greedy", "minimax", "iterative"]
    console.print(f"Strategies: {common_strategies}\n")

    # 测试每个位置和策略
    results = []

    table = Table(title="Performance Benchmark")
    table.add_column("Position", style="cyan")
    table.add_column("Strategy", style="yellow")
    table.add_column("Py Time(s)", justify="right")
    table.add_column("Rust Time(s)", justify="right")
    table.add_column("Speedup", justify="right", style="green")
    table.add_column("Py Best", justify="center")
    table.add_column("Rust Best", justify="center")
    table.add_column("Match", justify="center")

    for pos_name, fen in TEST_POSITIONS.items():
        for strategy in sorted(common_strategies):
            try:
                # Python benchmark
                py_result = measure_nps("python", strategy, fen, time_limit, iterations=1)

                # Rust benchmark
                rust_result = measure_nps("rust", strategy, fen, time_limit, iterations=1)

                # 实际用时（秒）
                py_time = py_result["time_per_call"]
                rust_time = rust_result["time_per_call"]

                py_best = py_result["best_move"] or "-"
                rust_best = rust_result["best_move"] or "-"

                # 比较最佳走法
                same_move = py_best == rust_best
                match_str = "[green]✓[/green]" if same_move else "[red]✗[/red]"

                table.add_row(
                    pos_name[:10],
                    strategy[:10],
                    f"{py_time:.2f}",
                    f"{rust_time:.2f}",
                    "-",  # 不再计算加速比，因为时间应该相同
                    py_best[:6],
                    rust_best[:6],
                    match_str,
                )

                results.append(
                    {
                        "position": pos_name,
                        "strategy": strategy,
                        "python_time": py_time,
                        "rust_time": rust_time,
                        "same_move": same_move,
                    }
                )

            except Exception as e:
                console.print(f"[red]Error {pos_name}/{strategy}: {e}[/red]")

    console.print(table)

    # 汇总统计
    if results:
        avg_py_time = sum(r["python_time"] for r in results) / len(results)
        avg_rust_time = sum(r["rust_time"] for r in results) / len(results)
        same_move_rate = sum(1 for r in results if r["same_move"]) / len(results) * 100

        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  Average Python Time: {avg_py_time:.2f}s/call")
        console.print(f"  Average Rust Time:   {avg_rust_time:.2f}s/call")
        console.print(f"  Same Move Rate:      {same_move_rate:.1f}%")


@app.command()
def battle(
    games: int = typer.Option(10, "--games", "-n", help="Number of games per matchup"),
    max_moves: int = typer.Option(100, "--max-moves", "-m", help="Max moves per game"),
    time_limit: float = typer.Option(5.0, "--time", "-t", help="Time limit per move (seconds)"),
    strategy: str = typer.Option("minimax", "--strategy", "-s", help="Strategy to use"),
):
    """Run Python vs Rust AI battles"""

    console.print("\n[bold]Python vs Rust AI Battle[/bold]")
    console.print(f"Strategy: {strategy}, Games: {games}, Time: {time_limit}s per move\n")

    battle_results = []

    # Python (Red) vs Rust (Black)
    console.print("[cyan]Python (Red) vs Rust (Black)[/cyan]")
    py_vs_rust = {"red_wins": 0, "black_wins": 0, "draws": 0}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Python vs Rust...", total=games)

        for i in range(games):
            result = run_game("python", strategy, "rust", strategy, max_moves, time_limit)

            if result["result"] == "red_win":
                py_vs_rust["red_wins"] += 1
            elif result["result"] == "black_win":
                py_vs_rust["black_wins"] += 1
            else:
                py_vs_rust["draws"] += 1

            battle_results.append(
                {
                    "red": f"python-{strategy}",
                    "black": f"rust-{strategy}",
                    "result": result["result"],
                }
            )

            progress.update(task, advance=1)

    # Rust (Red) vs Python (Black)
    console.print("\n[cyan]Rust (Red) vs Python (Black)[/cyan]")
    rust_vs_py = {"red_wins": 0, "black_wins": 0, "draws": 0}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Rust vs Python...", total=games)

        for i in range(games):
            result = run_game("rust", strategy, "python", strategy, max_moves, time_limit)

            if result["result"] == "red_win":
                rust_vs_py["red_wins"] += 1
            elif result["result"] == "black_win":
                rust_vs_py["black_wins"] += 1
            else:
                rust_vs_py["draws"] += 1

            battle_results.append(
                {
                    "red": f"rust-{strategy}",
                    "black": f"python-{strategy}",
                    "result": result["result"],
                }
            )

            progress.update(task, advance=1)

    # 计算 ELO
    elo = calculate_elo(battle_results)

    # 显示结果
    table = Table(title="Battle Results")
    table.add_column("Matchup", style="cyan")
    table.add_column("Red Wins", justify="right", style="red")
    table.add_column("Black Wins", justify="right", style="blue")
    table.add_column("Draws", justify="right")

    table.add_row(
        "Python(R) vs Rust(B)",
        str(py_vs_rust["red_wins"]),
        str(py_vs_rust["black_wins"]),
        str(py_vs_rust["draws"]),
    )
    table.add_row(
        "Rust(R) vs Python(B)",
        str(rust_vs_py["red_wins"]),
        str(rust_vs_py["black_wins"]),
        str(rust_vs_py["draws"]),
    )

    console.print(table)

    # 汇总
    py_total_wins = py_vs_rust["red_wins"] + rust_vs_py["black_wins"]
    rust_total_wins = py_vs_rust["black_wins"] + rust_vs_py["red_wins"]
    total_draws = py_vs_rust["draws"] + rust_vs_py["draws"]
    total_games = games * 2

    console.print("\n[bold]Overall Results:[/bold]")
    console.print(f"  Python Wins: {py_total_wins} ({py_total_wins / total_games * 100:.1f}%)")
    console.print(f"  Rust Wins:   {rust_total_wins} ({rust_total_wins / total_games * 100:.1f}%)")
    console.print(f"  Draws:       {total_draws} ({total_draws / total_games * 100:.1f}%)")

    console.print("\n[bold]ELO Ratings:[/bold]")
    for name, rating in sorted(elo.items(), key=lambda x: x[1], reverse=True):
        console.print(f"  {name}: {rating:.0f}")


@app.command()
def full_compare(
    games: int = typer.Option(5, "--games", "-n", help="Number of games per matchup"),
    max_moves: int = typer.Option(50, "--max-moves", "-m", help="Max moves per game"),
    time_limit: float = typer.Option(5.0, "--time", "-t", help="Time limit per move (seconds)"),
):
    """Full comparison of all Python and Rust strategies"""

    console.print("\n[bold]Full AI Comparison: Python vs Rust[/bold]")
    console.print(f"Games per matchup: {games}, Time: {time_limit}s per move\n")

    # 共同支持的策略（使用迭代加深进行公平时间比较）
    common = ["random", "greedy", "minimax", "iterative"]
    console.print(f"Testing strategies: {common}\n")

    all_results = []
    nps_data = {}

    # 为每个策略组合测试
    total_matchups = len(common) * 2  # Python vs Rust + Rust vs Python for each strategy
    current = 0

    for strategy in common:
        console.print(f"\n[yellow]Strategy: {strategy}[/yellow]")

        # 性能测试
        console.print("  Measuring performance...")
        fen = TEST_POSITIONS["endgame_rook"]  # 用残局测试

        py_perf = measure_nps("python", strategy, fen, time_limit, iterations=1)
        rust_perf = measure_nps("rust", strategy, fen, time_limit, iterations=1)

        py_time = py_perf["time_per_call"] * 1000
        rust_time = rust_perf["time_per_call"] * 1000
        nps_data[f"python-{strategy}"] = py_time
        nps_data[f"rust-{strategy}"] = rust_time

        speedup = py_time / rust_time if rust_time > 0 else 0
        console.print(
            f"    Python: {py_time:.1f}ms | Rust: {rust_time:.1f}ms | Speedup: {speedup:.1f}x"
        )

        # 对战测试
        for _ in range(games):
            # Python vs Rust
            result = run_game("python", strategy, "rust", strategy, max_moves, time_limit)
            all_results.append(
                {
                    "red": f"python-{strategy}",
                    "black": f"rust-{strategy}",
                    "result": result["result"],
                }
            )

            # Rust vs Python
            result = run_game("rust", strategy, "python", strategy, max_moves, time_limit)
            all_results.append(
                {
                    "red": f"rust-{strategy}",
                    "black": f"python-{strategy}",
                    "result": result["result"],
                }
            )

        current += 2
        console.print(f"    Completed battles")

    # 计算 ELO
    elo = calculate_elo(all_results)

    # 计算胜率
    win_counts = {}
    game_counts = {}

    for r in all_results:
        red, black = r["red"], r["black"]
        for player in [red, black]:
            if player not in win_counts:
                win_counts[player] = 0
                game_counts[player] = 0

        game_counts[red] += 1
        game_counts[black] += 1

        if r["result"] == "red_win":
            win_counts[red] += 1
        elif r["result"] == "black_win":
            win_counts[black] += 1
        else:
            win_counts[red] += 0.5
            win_counts[black] += 0.5

    # 最终报告
    console.print("\n" + "=" * 60)
    console.print("[bold]FINAL REPORT: Python vs Rust AI Comparison[/bold]")
    console.print("=" * 60)

    # 性能表格（时间 ms）
    perf_table = Table(title="Response Time (ms per call)")
    perf_table.add_column("Strategy", style="cyan")
    perf_table.add_column("Python (ms)", justify="right")
    perf_table.add_column("Rust (ms)", justify="right")
    perf_table.add_column("Speedup", justify="right", style="green")

    for strategy in common:
        py_t = nps_data.get(f"python-{strategy}", 0)
        rust_t = nps_data.get(f"rust-{strategy}", 0)
        speedup = py_t / rust_t if rust_t > 0 else 0
        perf_table.add_row(
            strategy,
            f"{py_t:.1f}",
            f"{rust_t:.1f}",
            f"{speedup:.1f}x",
        )

    console.print(perf_table)

    # ELO 排名
    elo_table = Table(title="ELO Rankings")
    elo_table.add_column("Rank", style="bold")
    elo_table.add_column("AI", style="cyan")
    elo_table.add_column("ELO", justify="right", style="yellow")
    elo_table.add_column("Win Rate", justify="right")
    elo_table.add_column("Time (ms)", justify="right")

    sorted_elo = sorted(elo.items(), key=lambda x: x[1], reverse=True)
    for rank, (name, rating) in enumerate(sorted_elo, 1):
        wins = win_counts.get(name, 0)
        total = game_counts.get(name, 1)
        win_rate = wins / total * 100
        time_ms = nps_data.get(name, 0)

        elo_table.add_row(
            str(rank),
            name,
            f"{rating:.0f}",
            f"{win_rate:.1f}%",
            f"{time_ms:.1f}",
        )

    console.print(elo_table)

    # 汇总
    py_total_elo = sum(elo.get(f"python-{s}", 1500) for s in common) / len(common)
    rust_total_elo = sum(elo.get(f"rust-{s}", 1500) for s in common) / len(common)

    py_avg_time = sum(nps_data.get(f"python-{s}", 0) for s in common) / len(common)
    rust_avg_time = sum(nps_data.get(f"rust-{s}", 0) for s in common) / len(common)

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Python Average ELO:  {py_total_elo:.0f}")
    console.print(f"  Rust Average ELO:    {rust_total_elo:.0f}")
    console.print(f"  Python Average Time: {py_avg_time:.1f} ms")
    console.print(f"  Rust Average Time:   {rust_avg_time:.1f} ms")
    speedup = py_avg_time / rust_avg_time if rust_avg_time > 0 else 0
    console.print(f"  Overall Speedup:     {speedup:.1f}x faster")


if __name__ == "__main__":
    app()
