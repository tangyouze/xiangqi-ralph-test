"""Python vs Rust Muses 对战测试"""

import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from jieqi.ai.unified import UnifiedAIEngine
from jieqi.fen import apply_move_to_fen, parse_fen
from jieqi.types import Color

INITIAL_FEN = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"


def run_single_game(args):
    """运行单场对战"""
    game_id, red_backend, black_backend, time_limit = args

    red_ai = UnifiedAIEngine(backend=red_backend, strategy="muses", time_limit=time_limit)
    black_ai = UnifiedAIEngine(backend=black_backend, strategy="muses", time_limit=time_limit)

    fen = INITIAL_FEN
    move_count = 0
    max_moves = 200

    while move_count < max_moves:
        state = parse_fen(fen)
        current_ai = red_ai if state.turn == Color.RED else black_ai

        try:
            moves = current_ai.get_best_moves(fen, n=1)
            if not moves:
                # 无走法，对方胜
                winner = "black" if state.turn == Color.RED else "red"
                return game_id, winner, move_count, red_backend, black_backend

            move_str, _ = moves[0]
            fen = apply_move_to_fen(fen, move_str)
            move_count += 1
        except Exception:
            # 出错，对方胜
            winner = "black" if state.turn == Color.RED else "red"
            return game_id, winner, move_count, red_backend, black_backend

    return game_id, "draw", move_count, red_backend, black_backend


def main():
    num_games = 10
    time_limit = 1.0
    num_workers = 10

    print(f"Running {num_games} games: Python muses vs Rust muses")
    print(f"Time limit: {time_limit}s per move, Workers: {num_workers}")
    print("-" * 60)

    # 统计: python_wins, rust_wins, draws
    stats = {"python": 0, "rust": 0, "draw": 0}
    total_moves = 0
    start = time.time()

    # 准备任务：交替先手
    tasks = []
    for i in range(num_games):
        if i % 2 == 0:
            red_backend, black_backend = "python", "rust"
        else:
            red_backend, black_backend = "rust", "python"
        tasks.append((i, red_backend, black_backend, time_limit))

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(run_single_game, task) for task in tasks]

        for future in as_completed(futures):
            game_id, winner, moves, red_be, black_be = future.result()
            total_moves += moves

            # 统计胜利
            if winner == "red":
                stats[red_be] += 1
            elif winner == "black":
                stats[black_be] += 1
            else:
                stats["draw"] += 1

            winner_backend = (
                red_be if winner == "red" else (black_be if winner == "black" else "draw")
            )
            print(
                f"Game {game_id + 1:2d}: {winner.upper():5s} wins | "
                f"Red={red_be:6s} Black={black_be:6s} | "
                f"{moves:3d} moves | Winner: {winner_backend}"
            )

    elapsed = time.time() - start
    print("-" * 60)
    print(f"Results: Python {stats['python']} - Rust {stats['rust']} - Draw {stats['draw']}")
    print(f"Total time: {elapsed:.1f}s, Avg moves: {total_moves / num_games:.1f}")


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
