"""显示某局某步的棋盘状态"""

from jieqi.ai import AIEngine
from jieqi.ai.base import AIConfig
from jieqi.game import GameConfig, JieqiGame
from jieqi.types import Color, GameResult, PieceType


# 棋子符号映射
PIECE_SYMBOLS = {
    # 红方
    (Color.RED, PieceType.KING): "帥",
    (Color.RED, PieceType.ADVISOR): "仕",
    (Color.RED, PieceType.ELEPHANT): "相",
    (Color.RED, PieceType.HORSE): "傌",
    (Color.RED, PieceType.ROOK): "俥",
    (Color.RED, PieceType.CANNON): "炮",
    (Color.RED, PieceType.PAWN): "兵",
    # 黑方
    (Color.BLACK, PieceType.KING): "將",
    (Color.BLACK, PieceType.ADVISOR): "士",
    (Color.BLACK, PieceType.ELEPHANT): "象",
    (Color.BLACK, PieceType.HORSE): "馬",
    (Color.BLACK, PieceType.ROOK): "車",
    (Color.BLACK, PieceType.CANNON): "砲",
    (Color.BLACK, PieceType.PAWN): "卒",
}


def show_board(game: JieqiGame):
    """打印棋盘 ASCII"""
    board = game.board
    print("\n  ９ ８ ７ ６ ５ ４ ３ ２ １")
    print("  ─────────────────────────")

    for row in range(10):
        line = f"{row}│"
        for col in range(9):
            from jieqi.types import Position

            pos = Position(row, col)
            piece = board.get_piece(pos)
            if piece:
                if piece.is_hidden:
                    line += "？"
                else:
                    symbol = PIECE_SYMBOLS.get((piece.color, piece.actual_type), "?")
                    line += symbol
            else:
                line += "・"
            line += " " if col < 8 else ""
        line += "│"
        print(line)

    print("  ─────────────────────────")
    print(f"  当前回合: {game.current_turn.name}, 结果: {game.result.name}")


def replay_to_move(seed: int, target_move: int, red_time: float = 1.5, black_time: float = 15.0):
    """重放到指定步数"""
    red_ai = AIEngine.create("advanced", AIConfig(time_limit=red_time, seed=seed * 1000))
    black_ai = AIEngine.create("advanced", AIConfig(time_limit=black_time, seed=seed * 1000 + 1))
    game = JieqiGame(config=GameConfig(seed=seed))

    print(f"=== Game seed={seed}, replay to move {target_move} ===")

    # 先显示初始棋盘
    if target_move == 0:
        print("\n初始棋盘:")
        show_board(game)
        return

    for move_num in range(target_move):
        current = game.current_turn
        ai = red_ai if current == Color.RED else black_ai
        view = game.get_view(current)

        candidates = ai.select_moves(view, n=1)
        if not candidates:
            print(f"Move {move_num + 1}: No candidates!")
            break

        move = candidates[0][0]
        game.make_move(move)

        history = game.get_move_history()
        notation = history[-1].get("notation", "?") if history else "?"
        color = "红" if current == Color.RED else "黑"

        print(f"Move {move_num + 1}: [{color}] {notation}")

        if game.result != GameResult.ONGOING:
            print(f"\n游戏结束: {game.result.name}")
            show_board(game)
            return

    print(f"\n第 {target_move} 步后的棋盘:")
    show_board(game)


if __name__ == "__main__":
    import sys

    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    target_move = int(sys.argv[2]) if len(sys.argv) > 2 else 11
    replay_to_move(seed, target_move)
