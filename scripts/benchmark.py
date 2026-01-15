#!/usr/bin/env python3
"""
棋盘表示和评估函数性能测试
"""

import time
from collections.abc import Callable

from jieqi.bitboard import (
    BitBoard,
    FastEvaluator,
    quick_material_eval,
)
from jieqi.board import JieqiBoard
from jieqi.game import JieqiGame
from jieqi.types import Color


def benchmark(func: Callable, iterations: int = 1000, name: str = "") -> float:
    """运行基准测试"""
    start = time.perf_counter()
    for _ in range(iterations):
        func()
    elapsed = time.perf_counter() - start
    per_call = elapsed / iterations * 1000  # ms
    print(f"{name or func.__name__}: {per_call:.4f} ms/call ({iterations} iterations)")
    return per_call


def main():
    print("=" * 60)
    print("揭棋性能基准测试")
    print("=" * 60)

    # 创建测试棋盘
    from jieqi.game import GameConfig

    board = JieqiBoard(seed=42)
    game = JieqiGame(config=GameConfig(seed=42))

    print("\n1. 棋盘创建性能")
    print("-" * 40)
    benchmark(lambda: JieqiBoard(seed=42), 100, "JieqiBoard 创建")
    benchmark(lambda: BitBoard.from_board(board), 1000, "BitBoard 从 Board 创建")

    print("\n2. 合法走法生成性能")
    print("-" * 40)
    benchmark(lambda: board.get_legal_moves(Color.RED), 100, "get_legal_moves (RED)")
    benchmark(lambda: board.get_legal_moves(Color.BLACK), 100, "get_legal_moves (BLACK)")

    print("\n3. 局面评估性能")
    print("-" * 40)

    # 老的评估方式（遍历棋子）
    def old_eval():
        score = 0
        for _piece in board.get_all_pieces(Color.RED):
            score += 100
        for _piece in board.get_all_pieces(Color.BLACK):
            score -= 100
        return score

    # 新的快速评估
    bb = BitBoard.from_board(board)
    evaluator = FastEvaluator(bb)

    benchmark(old_eval, 10000, "旧评估 (遍历棋子)")
    benchmark(lambda: quick_material_eval(board, Color.RED), 10000, "快速子力评估")
    benchmark(lambda: evaluator.evaluate(Color.RED), 10000, "BitBoard 完整评估")
    benchmark(lambda: evaluator.quick_evaluate(Color.RED), 10000, "BitBoard 快速评估")

    print("\n4. 走法执行性能")
    print("-" * 40)

    # 获取一些合法走法
    moves = board.get_legal_moves(Color.RED)
    if moves:
        move = moves[0]

        def make_undo_move():
            piece = board.get_piece(move.from_pos)
            was_hidden = piece.is_hidden if piece else False
            captured = board.make_move(move)
            board.undo_move(move, captured, was_hidden)

        benchmark(make_undo_move, 1000, "make_move + undo_move")

    print("\n5. 完整 AI 决策性能")
    print("-" * 40)

    # 模拟简单 AI 决策
    def simple_ai_decision():
        moves = game.get_legal_moves()
        best_score = float("-inf")
        best_move = None
        for move in moves:
            # 简单评估
            target = game.board.get_piece(move.to_pos)
            score = 0
            if target and target.color != game.current_turn:
                score = 100
            if score > best_score:
                best_score = score
                best_move = move
        return best_move

    def fast_ai_decision():
        moves = game.get_legal_moves()
        bb = BitBoard.from_board(game.board)
        evaluator = FastEvaluator(bb)
        best_score = float("-inf")
        best_move = None
        for move in moves:
            score = evaluator.quick_evaluate(game.current_turn)
            if score > best_score:
                best_score = score
                best_move = move
        return best_move

    benchmark(simple_ai_decision, 100, "简单 AI 决策")
    benchmark(fast_ai_decision, 100, "快速 AI 决策")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
