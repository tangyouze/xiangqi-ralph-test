"""
不同时间限制的 AI 对战测试
"""

import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

from jieqi.ai import AIEngine
from jieqi.ai.base import AIConfig
from jieqi.game import GameConfig, JieqiGame
from jieqi.types import Color, GameResult

# 棋谱保存目录
GAME_LOG_DIR = Path(__file__).parent.parent / "data" / "battle_logs"
GAME_LOG_DIR.mkdir(parents=True, exist_ok=True)


def would_cause_draw(game: JieqiGame, move) -> bool:
    """预判走这步是否会导致和棋或增加重复局面"""
    game.make_move(move)
    is_draw = game.result == GameResult.DRAW
    is_repeated = game.get_position_count() >= 2
    game.undo_move()
    return is_draw or is_repeated


def run_single_game(args):
    """单局对战，返回结果和棋谱"""
    red_time, black_time, seed = args
    red_ai = AIEngine.create("advanced", AIConfig(time_limit=red_time, seed=seed * 1000))
    black_ai = AIEngine.create(
        "advanced", AIConfig(time_limit=black_time, seed=seed * 1000 + 1)
    )
    # 给棋盘也传入 seed，确保可复现
    game = JieqiGame(config=GameConfig(seed=seed))
    moves = 0
    max_moves = 500

    # 记录棋谱
    notations = []

    while game.result == GameResult.ONGOING and moves < max_moves:
        current = game.current_turn
        ai = red_ai if current == Color.RED else black_ai
        view = game.get_view(current)

        # 使用 Top-N 候选，规避和棋
        move = None
        candidates = ai.select_moves(view, n=10)
        for candidate_move, _score in candidates:
            if not would_cause_draw(game, candidate_move):
                move = candidate_move
                break
        if move is None and candidates:
            move = candidates[0][0]

        if move is None:
            # AI 无法返回着法，视为该方输（对方赢）
            if current == Color.RED:
                result = "black"
            else:
                result = "red"
            notations.append(f"# [{current.name}] AI returned no moves")
            return (seed, result, moves, notations)

        game.make_move(move)
        moves += 1

        # 记录棋谱
        history = game.get_move_history()
        if history:
            notation = history[-1].get("notation", "?")
            color = "红" if current == Color.RED else "黑"
            notations.append(f"{moves}. [{color}] {notation}")

    if game.result == GameResult.RED_WIN:
        result = "red"
    elif game.result == GameResult.BLACK_WIN:
        result = "black"
    else:
        result = "draw"
        notations.append(f"# Draw: {game.result.name}")

    return (seed, result, moves, notations)


def battle_with_progress(red_time, black_time, games=100, workers=None, log_file=None):
    """并行对战测试，带实时进度输出和棋谱记录"""
    if workers is None:
        workers = max(1, int(os.cpu_count() * 0.7))

    args = [(red_time, black_time, i) for i in range(games)]

    red_wins = 0
    black_wins = 0
    draws = 0
    total_moves = 0
    completed = 0

    # 所有棋谱
    all_games = []

    print(f"Starting {games} games with {workers} workers...", flush=True)
    print(f"Logs will be saved to: {log_file}", flush=True)
    print("-" * 60, flush=True)

    with mp.Pool(workers) as pool:
        # 使用 imap_unordered 实时获取结果
        for seed, result, moves, notations in pool.imap_unordered(run_single_game, args):
            completed += 1
            total_moves += moves

            if result == "red":
                red_wins += 1
                symbol = "R"
            elif result == "black":
                black_wins += 1
                symbol = "B"
            else:
                draws += 1
                symbol = "D"

            # 记录这局棋谱
            game_record = {
                "seed": seed,
                "result": result,
                "moves": moves,
                "notations": notations,
            }
            all_games.append(game_record)

            # 每局输出一行日志
            win_rate = (
                black_wins / (red_wins + black_wins) * 100
                if (red_wins + black_wins) > 0
                else 0
            )
            print(
                f"[{completed:3d}/{games}] Game {seed:3d}: {symbol} ({moves:3d} moves) | "
                f"R:{red_wins} B:{black_wins} D:{draws} | "
                f"Long time win rate: {win_rate:.1f}%",
                flush=True,
            )

            # 实时保存棋谱到文件
            if log_file:
                save_data = {
                    "config": {
                        "red_time": red_time,
                        "black_time": black_time,
                        "total_games": games,
                    },
                    "progress": {
                        "completed": completed,
                        "red_wins": red_wins,
                        "black_wins": black_wins,
                        "draws": draws,
                    },
                    "games": sorted(all_games, key=lambda x: x["seed"]),
                }
                with open(log_file, "w") as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)

    avg_moves = total_moves / games
    return red_wins, black_wins, draws, avg_moves, all_games


if __name__ == "__main__":
    cpu_count = os.cpu_count()
    workers = max(1, int(cpu_count * 0.7))

    # 可以通过命令行参数指定
    red_time = float(sys.argv[1]) if len(sys.argv) > 1 else 0.15
    black_time = float(sys.argv[2]) if len(sys.argv) > 2 else 5
    games = int(sys.argv[3]) if len(sys.argv) > 3 else 100

    # 日志文件
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = GAME_LOG_DIR / f"battle_{red_time}s_vs_{black_time}s_{timestamp}.json"

    print(f"CPU: {cpu_count} cores, using {workers} workers")
    print("=" * 60)
    print(f"Battle: {red_time}s (Red) vs {black_time}s (Black)")
    print(f"Games: {games}")
    print("=" * 60)

    start = time.time()
    r, b, d, avg, all_games = battle_with_progress(
        red_time, black_time, games, workers, log_file
    )
    elapsed = time.time() - start

    print("=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Red({red_time}s): {r} wins")
    print(f"Black({black_time}s): {b} wins")
    print(f"Draws: {d}")
    print(f"Avg moves: {avg:.0f}")
    print(f"Elapsed: {elapsed:.0f}s")
    if r + b > 0:
        print(f"\nLonger time ({black_time}s) win rate: {b / (r + b) * 100:.1f}%")
    print(f"Draw rate: {d / games * 100:.1f}%")
    print(f"\nGame logs saved to: {log_file}")
