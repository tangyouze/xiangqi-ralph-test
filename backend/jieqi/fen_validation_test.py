"""
FEN 接口验证测试

核心验证：FEN 接口与原始接口的行为一致性

测试方法：
1. 从 PlayerView 生成 FEN
2. 用 FEN 接口获取合法走法
3. 对比原始接口的合法走法
4. 验证数量和内容一致

验证点：
- 合法走法数量一致
- 合法走法内容一致（转换后）
- 走法执行后状态一致
"""

import pytest

from jieqi.fen import (
    apply_move_to_fen,
    create_board_from_fen,
    get_legal_moves_from_fen,
    move_to_str,
    parse_fen,
    parse_move,
    to_fen,
)
from jieqi.game import JieqiGame
from jieqi.simulation import SimulationBoard
from jieqi.types import ActionType, Color, PieceType


def moves_to_str_set(moves: list) -> set[str]:
    """将 JieqiMove 列表转换为走法字符串集合"""
    result = set()
    for move in moves:
        result.add(move_to_str(move))
    return result


class TestLegalMovesConsistency:
    """验证合法走法的一致性"""

    def test_initial_position(self):
        """初始局面：全暗子，44 个合法走法"""
        game = JieqiGame()
        view = game.get_view(Color.RED)

        # 原始接口
        original_moves = view.legal_moves
        original_count = len(original_moves)
        original_set = moves_to_str_set(original_moves)

        # FEN 接口
        fen = to_fen(view)
        fen_moves = get_legal_moves_from_fen(fen)
        fen_count = len(fen_moves)
        fen_set = set(fen_moves)

        # 验证
        assert original_count == fen_count, f"走法数量不一致: 原始={original_count}, FEN={fen_count}"
        assert original_set == fen_set, f"走法内容不一致:\n原始: {original_set}\nFEN: {fen_set}"

    def test_initial_position_black_view(self):
        """初始局面黑方视角"""
        game = JieqiGame()
        # 红方先走一步
        view = game.get_view(Color.RED)
        move = view.legal_moves[0]
        game.make_move(move)

        # 黑方视角
        view = game.get_view(Color.BLACK)
        original_moves = view.legal_moves
        original_set = moves_to_str_set(original_moves)

        fen = to_fen(view)
        fen_moves = get_legal_moves_from_fen(fen)
        fen_set = set(fen_moves)

        assert original_set == fen_set

    def test_mid_game_mixed_pieces(self):
        """中局：混合明暗子"""
        game = JieqiGame()

        # 走几步揭子
        for _ in range(10):
            view = game.get_view(game.current_turn)
            if not view.legal_moves:
                break
            # 优先选揭子走法
            reveal_moves = [m for m in view.legal_moves if m.action_type == ActionType.REVEAL_AND_MOVE]
            move = reveal_moves[0] if reveal_moves else view.legal_moves[0]
            game.make_move(move)

        # 验证当前局面
        view = game.get_view(game.current_turn)
        original_set = moves_to_str_set(view.legal_moves)

        fen = to_fen(view)
        fen_set = set(get_legal_moves_from_fen(fen))

        assert original_set == fen_set, f"中局走法不一致:\n原始: {len(original_set)}\nFEN: {len(fen_set)}"

    def test_after_many_moves(self):
        """走很多步后的局面"""
        game = JieqiGame()

        # 走 20 步
        for _ in range(20):
            view = game.get_view(game.current_turn)
            if not view.legal_moves:
                break
            game.make_move(view.legal_moves[0])

        # 验证
        view = game.get_view(game.current_turn)
        if view.legal_moves:  # 游戏还没结束
            original_set = moves_to_str_set(view.legal_moves)
            fen = to_fen(view)
            fen_set = set(get_legal_moves_from_fen(fen))
            assert original_set == fen_set


class TestSimulationBoardConsistency:
    """验证 SimulationBoard 从 FEN 创建的一致性"""

    def test_initial_board_piece_count(self):
        """初始棋盘棋子数量"""
        game = JieqiGame()
        view = game.get_view(Color.RED)

        # 原始方式
        original_board = SimulationBoard(view)
        original_red = len(original_board.get_all_pieces(Color.RED))
        original_black = len(original_board.get_all_pieces(Color.BLACK))

        # FEN 方式
        fen = to_fen(view)
        fen_board = create_board_from_fen(fen)
        fen_red = len(fen_board.get_all_pieces(Color.RED))
        fen_black = len(fen_board.get_all_pieces(Color.BLACK))

        assert original_red == fen_red == 16
        assert original_black == fen_black == 16

    def test_board_legal_moves(self):
        """棋盘合法走法"""
        game = JieqiGame()
        view = game.get_view(Color.RED)

        original_board = SimulationBoard(view)
        original_moves = original_board.get_legal_moves(Color.RED)

        fen = to_fen(view)
        fen_board = create_board_from_fen(fen)
        fen_moves = fen_board.get_legal_moves(Color.RED)

        assert len(original_moves) == len(fen_moves)
        assert moves_to_str_set(original_moves) == moves_to_str_set(fen_moves)

    def test_board_after_move(self):
        """执行走法后棋盘状态"""
        game = JieqiGame()
        view = game.get_view(Color.RED)
        move = view.legal_moves[0]

        # 原始方式：执行走法
        original_board = SimulationBoard(view)
        original_board.make_move(move)
        original_moves_after = original_board.get_legal_moves(Color.BLACK)

        # FEN 方式：执行走法
        fen = to_fen(view)
        fen_board = create_board_from_fen(fen)
        fen_board.make_move(move)
        fen_moves_after = fen_board.get_legal_moves(Color.BLACK)

        assert len(original_moves_after) == len(fen_moves_after)


class TestApplyMoveConsistency:
    """验证 apply_move_to_fen 的正确性"""

    def test_apply_move_piece_count(self):
        """执行走法后棋子数量"""
        fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"

        moves = get_legal_moves_from_fen(fen)
        move_str = moves[0]  # 取第一个走法

        # 执行走法
        new_fen = apply_move_to_fen(fen, move_str)

        # 解析新 FEN
        state = parse_fen(new_fen)

        # 验证：非吃子走法，棋子数应该不变
        assert len(state.pieces) == 32  # 初始 32 个棋子

        # 验证：轮到黑方
        assert state.turn == Color.BLACK

    def test_apply_reveal_move(self):
        """执行揭子走法"""
        fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"

        # 找一个揭子走法
        moves = get_legal_moves_from_fen(fen)
        reveal_move = next((m for m in moves if m.startswith("+")), None)

        if reveal_move:
            # 执行揭子（模拟揭出车）
            new_fen = apply_move_to_fen(fen, reveal_move, revealed_type=PieceType.ROOK)

            # 解析新 FEN
            state = parse_fen(new_fen)

            # 找到揭开的棋子
            move, _ = parse_move(reveal_move)
            revealed_piece = next(
                (p for p in state.pieces if p.position == move.to_pos), None
            )

            # 验证：揭子后变成明子
            assert revealed_piece is not None
            assert revealed_piece.is_hidden is False
            assert revealed_piece.piece_type == PieceType.ROOK


class TestMultipleGamesConsistency:
    """多局游戏的一致性验证"""

    def test_random_games(self):
        """随机走多局游戏，验证每步的一致性"""
        import random

        rng = random.Random(42)

        for game_idx in range(5):  # 5 局游戏
            game = JieqiGame()

            for move_idx in range(30):  # 每局最多 30 步
                view = game.get_view(game.current_turn)

                if not view.legal_moves:
                    break

                # 验证当前局面
                original_set = moves_to_str_set(view.legal_moves)
                fen = to_fen(view)
                fen_set = set(get_legal_moves_from_fen(fen))

                assert original_set == fen_set, (
                    f"Game {game_idx}, Move {move_idx}: 走法不一致\n"
                    f"原始: {len(original_set)}\nFEN: {len(fen_set)}"
                )

                # 随机选一步走
                move = rng.choice(view.legal_moves)
                game.make_move(move)


class TestSpecialPositions:
    """特殊局面测试"""

    def test_check_position(self):
        """将军局面：只有应将的走法合法"""
        # 构造一个将军局面的 FEN
        # 红方车将军黑方
        fen = "4k4/4R4/9/9/9/9/9/9/9/4K4 -:- b r"

        moves = get_legal_moves_from_fen(fen)
        board = create_board_from_fen(fen)

        # 验证黑方被将军
        assert board.is_in_check(Color.BLACK)

        # 验证所有走法都是应将的
        for move_str in moves:
            move, _ = parse_move(move_str)
            # 执行走法后不应该被将军
            captured = board.make_move(move)
            assert not board.is_in_check(Color.BLACK), f"走法 {move_str} 没有解除将军"
            board.undo_move(move, captured, False)

    def test_king_face_to_face(self):
        """将帅对脸局面

        规则：将帅不能在同一列且中间无子（对脸）
        当前已对脸时，帅可以：
        1. 左右移动（打破对脸）
        2. 不能向前移动到仍然对脸的位置
        """
        # 将帅同列，中间无子（对脸）
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 -:- r r"

        board = create_board_from_fen(fen)
        moves = get_legal_moves_from_fen(fen)

        # 红方帅的走法
        king_moves = [m for m in moves if m.startswith("e0")]

        # 验证帅有合法走法（可以左右移动打破对脸，或上移）
        assert len(king_moves) > 0, "帅应该有合法走法"

        # 所有走法执行后都不应该保持对脸
        for move_str in king_moves:
            move, _ = parse_move(move_str)
            captured = board.make_move(move)
            # 验证执行后不是非法状态
            # 如果移动后仍在 e 列，需要检查是否吃掉了黑将
            if move.to_pos.col == 4:
                # 向上移动，需要确保不会造成对脸（除非吃掉黑将）
                black_king = board.find_king(Color.BLACK)
                if black_king:
                    # 黑将还在，检查是否还是对脸
                    assert black_king.col != move.to_pos.col, f"走法 {move_str} 后仍然对脸"
            board.undo_move(move, captured, False)


class TestMoveExecution:
    """走法执行测试"""

    def test_capture_move(self):
        """吃子走法"""
        # 红方车可以吃黑方炮
        fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r"

        moves = get_legal_moves_from_fen(fen)

        # 找吃子走法
        capture_move = "e4e5"  # 红车吃黑炮
        assert capture_move in moves

        # 执行吃子
        new_fen = apply_move_to_fen(fen, capture_move)
        state = parse_fen(new_fen)

        # 验证：炮被吃了
        cannon = next((p for p in state.pieces if p.piece_type == PieceType.CANNON), None)
        assert cannon is None, "炮应该被吃掉了"

    def test_regular_move_no_capture(self):
        """普通走法（不吃子）"""
        fen = "4k4/9/9/9/9/4R4/9/9/9/4K4 -:- r r"

        # 车向前走一步
        move_str = "e4e5"
        new_fen = apply_move_to_fen(fen, move_str)

        state = parse_fen(new_fen)

        # 找车的新位置
        rook = next((p for p in state.pieces if p.piece_type == PieceType.ROOK), None)
        assert rook is not None
        assert rook.position.row == 5
        assert rook.position.col == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
