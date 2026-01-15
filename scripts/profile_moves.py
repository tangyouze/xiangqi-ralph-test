#!/usr/bin/env python3
"""
分析走法生成的性能瓶颈
"""

import time
from jieqi.board import JieqiBoard
from jieqi.types import Color, ActionType, JieqiMove
from jieqi.bitboard import FastMoveGenerator


def profile_legal_moves():
    board = JieqiBoard(seed=42)

    # 分解 get_legal_moves 的各个步骤
    iterations = 100

    # Step 1: 获取所有棋子
    start = time.perf_counter()
    for _ in range(iterations):
        pieces = board.get_all_pieces(Color.RED)
    elapsed = time.perf_counter() - start
    print(f"get_all_pieces: {elapsed / iterations * 1000:.4f} ms")

    # Step 2: 获取潜在走法
    start = time.perf_counter()
    for _ in range(iterations):
        all_moves = []
        for piece in board.get_all_pieces(Color.RED):
            moves = piece.get_potential_moves(board)
            all_moves.extend(moves)
    elapsed = time.perf_counter() - start
    print(f"get_potential_moves (all pieces): {elapsed / iterations * 1000:.4f} ms")

    # Step 3: 验证每个走法
    pieces = board.get_all_pieces(Color.RED)
    test_moves = []
    for piece in pieces:
        action_type = ActionType.REVEAL_AND_MOVE if piece.is_hidden else ActionType.MOVE
        for to_pos in piece.get_potential_moves(board):
            test_moves.append(JieqiMove(action_type, piece.position, to_pos))

    print(f"\n候选走法数量: {len(test_moves)}")

    start = time.perf_counter()
    for _ in range(iterations):
        for move in test_moves:
            board.is_valid_move(move, Color.RED)
    elapsed = time.perf_counter() - start
    print(f"is_valid_move (all moves): {elapsed / iterations * 1000:.4f} ms")
    print(f"is_valid_move (per move): {elapsed / iterations / len(test_moves) * 1000:.4f} ms")

    # Step 4: 分解 is_valid_move
    move = test_moves[0]
    piece = board.get_piece(move.from_pos)

    # 4a: make_move + undo
    start = time.perf_counter()
    for _ in range(1000):
        was_hidden = piece.is_hidden
        captured = board.make_move(move)
        board.undo_move(move, captured, was_hidden)
    elapsed = time.perf_counter() - start
    print(f"\nmake_move + undo_move: {elapsed / 1000 * 1000:.4f} ms")

    # 4b: is_in_check 对比
    print("\n=== is_in_check 性能对比 ===")

    start = time.perf_counter()
    for _ in range(1000):
        board.is_in_check(Color.RED)
    elapsed = time.perf_counter() - start
    print(f"is_in_check (原始): {elapsed / 1000 * 1000:.4f} ms")

    # 新的快速检查
    fast_gen = FastMoveGenerator(board)
    start = time.perf_counter()
    for _ in range(1000):
        fast_gen.is_in_check_fast(Color.RED)
    elapsed = time.perf_counter() - start
    print(f"is_in_check_fast (优化): {elapsed / 1000 * 1000:.4f} ms")

    # 验证结果一致
    old_result = board.is_in_check(Color.RED)
    new_result = fast_gen.is_in_check_fast(Color.RED)
    print(f"\n结果一致性: old={old_result}, new={new_result}, match={old_result == new_result}")


if __name__ == "__main__":
    profile_legal_moves()
