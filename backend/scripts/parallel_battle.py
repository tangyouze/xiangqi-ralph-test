"""
Python vs Rust AI Parallel Battle

使用 multiprocessing 并行运行多局对战
"""

import multiprocessing as mp
import time
from dataclasses import dataclass
from typing import Literal

from jieqi.ai.unified import UnifiedAIEngine
from jieqi.fen import apply_move_to_fen, create_board_from_fen, parse_fen
from jieqi.types import GameResult


@dataclass
class GameConfig:
    """对局配置"""

    game_id: int
    python_strategy: str
    rust_strategy: str
    python_is_red: bool
    time_limit: float
    max_moves: int


def run_single_game(config: GameConfig) -> tuple[int, str, float, int]:
    """运行单局对战，返回 (game_id, winner, elapsed, moves)"""
    # 初始局面
    fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"

    # 创建引擎
    python_engine = UnifiedAIEngine(
        backend="python",
        strategy=config.python_strategy,
        depth=20,
        time_limit=config.time_limit,
    )

    rust_engine = UnifiedAIEngine(
        backend="rust",
        strategy=config.rust_strategy,
        depth=20,
        time_limit=config.time_limit,
    )

    start_time = time.time()
    moves = 0

    while moves < config.max_moves:
        state = parse_fen(fen)
        is_red_turn = state.turn.name == "RED"

        # 选择引擎
        if is_red_turn == config.python_is_red:
            engine = python_engine
            engine_name = "python"
        else:
            engine = rust_engine
            engine_name = "rust"

        # 获取走法
        try:
            best_moves = engine.get_best_moves(fen, n=1)
            if not best_moves:
                # 无合法走法
                winner = "rust" if engine_name == "python" else "python"
                return (config.game_id, winner, time.time() - start_time, moves)

            move_str, score = best_moves[0]
        except Exception as e:
            # 出错判负
            winner = "rust" if engine_name == "python" else "python"
            return (config.game_id, winner, time.time() - start_time, moves)

        # 应用走法
        try:
            fen = apply_move_to_fen(fen, move_str)
        except Exception as e:
            winner = "rust" if engine_name == "python" else "python"
            return (config.game_id, winner, time.time() - start_time, moves)

        moves += 1

        # 检查游戏结束
        board = create_board_from_fen(fen)
        new_state = parse_fen(fen)
        result = board.get_game_result(new_state.turn)

        if result == GameResult.RED_WIN:
            winner = "python" if config.python_is_red else "rust"
            return (config.game_id, winner, time.time() - start_time, moves)
        elif result == GameResult.BLACK_WIN:
            winner = "rust" if config.python_is_red else "python"
            return (config.game_id, winner, time.time() - start_time, moves)
        elif result == GameResult.DRAW:
            return (config.game_id, "draw", time.time() - start_time, moves)

    return (config.game_id, "draw", time.time() - start_time, moves)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Python vs Rust AI Parallel Battle")
    parser.add_argument("-n", "--games", type=int, default=20, help="Number of games")
    parser.add_argument("-t", "--time-limit", type=float, default=1.0, help="Time limit per move")
    parser.add_argument("-w", "--workers", type=int, default=None, help="Number of workers")
    parser.add_argument("--python-strategy", type=str, default="pvs", help="Python strategy")
    parser.add_argument("--rust-strategy", type=str, default="pvs", help="Rust strategy")
    args = parser.parse_args()

    n_games = args.games
    time_limit = args.time_limit
    n_workers = args.workers or min(mp.cpu_count(), n_games)
    python_strategy = args.python_strategy
    rust_strategy = args.rust_strategy

    print(f"Python ({python_strategy}) vs Rust ({rust_strategy}) Parallel Battle")
    print(f"Games: {n_games}, Time limit: {time_limit}s, Workers: {n_workers}")
    print("=" * 70)

    # 创建对局配置
    configs = [
        GameConfig(
            game_id=i,
            python_strategy=python_strategy,
            rust_strategy=rust_strategy,
            python_is_red=(i % 2 == 0),
            time_limit=time_limit,
            max_moves=200,
        )
        for i in range(n_games)
    ]

    # 并行运行
    start_time = time.time()
    results = {"python": 0, "rust": 0, "draw": 0}

    with mp.Pool(processes=n_workers) as pool:
        for game_id, winner, elapsed, moves in pool.imap_unordered(run_single_game, configs):
            results[winner] += 1
            color = "Red" if configs[game_id].python_is_red else "Black"
            print(f"Game {game_id + 1:2d}: Python={color:5s} | Winner: {winner:6s} | {elapsed:5.1f}s | {moves:3d} moves")

    total_time = time.time() - start_time

    print("=" * 70)
    print(f"Results: Python {results['python']} - {results['rust']} Rust (Draws: {results['draw']})")

    total_decisive = results["python"] + results["rust"]
    if total_decisive > 0:
        python_rate = results["python"] / total_decisive * 100
        rust_rate = results["rust"] / total_decisive * 100
        print(f"Win rate (excluding draws): Python {python_rate:.1f}% - Rust {rust_rate:.1f}%")

    print(f"Total time: {total_time:.1f}s ({total_time / n_games:.1f}s per game average)")


if __name__ == "__main__":
    main()
