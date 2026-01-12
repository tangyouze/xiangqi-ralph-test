"""调试为什么某些对局4步就和棋"""

from jieqi.ai import AIEngine
from jieqi.ai.base import AIConfig
from jieqi.game import GameConfig, JieqiGame
from jieqi.types import Color, GameResult


def debug_game(seed: int, red_time: float = 0.15, black_time: float = 5.0):
    """调试单局对战"""
    red_ai = AIEngine.create("advanced", AIConfig(time_limit=red_time, seed=seed * 1000))
    black_ai = AIEngine.create(
        "advanced", AIConfig(time_limit=black_time, seed=seed * 1000 + 1)
    )
    game = JieqiGame(config=GameConfig(seed=seed))

    print(f"=== Debug Game seed={seed} ===")
    print(f"Initial position count: {game.get_position_count()}")

    moves = 0
    max_moves = 10

    while game.result == GameResult.ONGOING and moves < max_moves:
        current = game.current_turn
        ai = red_ai if current == Color.RED else black_ai
        view = game.get_view(current)

        candidates = ai.select_moves(view, n=10)
        print(f"\nMove {moves + 1} ({current.name}):")
        print(f"  Candidates: {len(candidates)}")

        # 检查每个候选是否会导致和棋
        for i, (move, score) in enumerate(candidates[:5]):
            game.make_move(move)
            is_draw = game.result == GameResult.DRAW
            pos_count = game.get_position_count()
            game.undo_move()
            print(f"  [{i}] {move} score={score:.0f} would_draw={is_draw} pos_count_after={pos_count}")

        # 选择第一个不会导致和棋的
        move = None
        for candidate_move, _score in candidates:
            game.make_move(candidate_move)
            is_draw = game.result == GameResult.DRAW
            is_repeated = game.get_position_count() >= 2
            game.undo_move()
            if not (is_draw or is_repeated):
                move = candidate_move
                break

        if move is None and candidates:
            move = candidates[0][0]
            print(f"  -> All candidates would cause draw/repeat, using first: {move}")

        if move is None:
            print("  -> No move available!")
            break

        game.make_move(move)
        moves += 1

        history = game.get_move_history()
        if history:
            notation = history[-1].get("notation", "?")
            print(f"  -> Played: {notation}")
            print(f"  -> Position count: {game.get_position_count()}")
            print(f"  -> Game result: {game.result}")

    print(f"\n=== Final: {game.result.name} after {moves} moves ===")


if __name__ == "__main__":
    debug_game(17)
    print("\n" + "=" * 60 + "\n")
    debug_game(20)
