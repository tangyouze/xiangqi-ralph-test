"""重放一局对战，查看结束原因"""

from jieqi.ai import AIEngine
from jieqi.ai.base import AIConfig
from jieqi.game import GameConfig, JieqiGame
from jieqi.types import Color, GameResult


def replay_game(seed: int, red_time: float = 1.5, black_time: float = 15.0, max_moves: int = 20):
    """重放一局对战"""
    red_ai = AIEngine.create("advanced", AIConfig(time_limit=red_time, seed=seed * 1000))
    black_ai = AIEngine.create("advanced", AIConfig(time_limit=black_time, seed=seed * 1000 + 1))
    game = JieqiGame(config=GameConfig(seed=seed))

    print(f"=== Replay Game seed={seed} ===")
    print(f"Red: {red_time}s, Black: {black_time}s")

    moves = 0

    while game.result == GameResult.ONGOING and moves < max_moves:
        current = game.current_turn
        ai = red_ai if current == Color.RED else black_ai
        view = game.get_view(current)

        print(f"\nMove {moves + 1} ({current.name}):")
        print(f"  Legal moves: {len(view.legal_moves)}")

        candidates = ai.select_moves(view, n=3)
        if not candidates:
            print("  No candidates!")
            break

        move = candidates[0][0]
        game.make_move(move)
        moves += 1

        history = game.get_move_history()
        if history:
            notation = history[-1].get("notation", "?")
            print(f"  Played: {notation}")

        print(f"  Result: {game.result.name}")

        # 如果游戏结束，打印棋盘状态
        if game.result != GameResult.ONGOING:
            print("\n=== Game Over ===")
            print(f"Result: {game.result.name}")
            # 打印简单的棋盘表示
            board = game.board
            print("\nFinal board (viewer: RED):")
            red_view = game.get_view(Color.RED)
            for row in range(10):
                line = ""
                for col in range(9):
                    from jieqi.types import Position

                    pos = Position(row, col)
                    piece = board.get_piece(pos)
                    if piece:
                        if piece.is_hidden:
                            line += "? "
                        else:
                            line += f"{piece.piece_type.value[0]} "
                    else:
                        line += ". "
                print(line)
            break


if __name__ == "__main__":
    import sys

    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    replay_game(seed)
