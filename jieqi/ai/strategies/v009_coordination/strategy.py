"""
v009_coordination - 棋子协作 AI

ID: v009
名称: Coordination AI
描述: 在 v007 基础上增加棋子协作评估

改进方向：棋子协作
- 双车协作加分
- 炮马配合
- 保护链评估
- 相互支援能力

注意：AI 使用 FEN 接口，无法看到暗子的真实身份！
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.fen import create_board_from_fen, get_legal_moves_from_fen, parse_fen, parse_move
from jieqi.simulation import SimPiece, SimulationBoard
from jieqi.types import Color, GameResult, PieceType, Position

if TYPE_CHECKING:
    from jieqi.types import JieqiMove


AI_ID = "v009"
AI_NAME = "coordination"


PIECE_VALUES = {
    PieceType.KING: 10000,
    PieceType.ROOK: 900,
    PieceType.CANNON: 450,
    PieceType.HORSE: 400,
    PieceType.ELEPHANT: 200,
    PieceType.ADVISOR: 200,
    PieceType.PAWN: 100,
}

HIDDEN_PIECE_VALUE = 320


def get_piece_value(piece: SimPiece) -> int:
    """获取棋子价值"""
    if piece.is_hidden or piece.actual_type is None:
        return HIDDEN_PIECE_VALUE
    return PIECE_VALUES.get(piece.actual_type, 0)


def count_attackers(board: SimulationBoard, pos: Position, color: Color) -> int:
    """计算有多少对方棋子可以攻击这个位置"""
    count = 0
    for enemy in board.get_all_pieces(color.opposite):
        if pos in board.get_potential_moves(enemy):
            count += 1
    return count


def count_defenders(board: SimulationBoard, pos: Position, color: Color) -> int:
    """计算有多少己方棋子可以保护这个位置"""
    count = 0
    for ally in board.get_all_pieces(color):
        if ally.position != pos and pos in board.get_potential_moves(ally):
            count += 1
    return count


def count_hidden(board: SimulationBoard, color: Color) -> int:
    """统计某方隐藏棋子数量"""
    count = 0
    for piece in board.get_all_pieces(color):
        if piece.is_hidden:
            count += 1
    return count


def get_game_phase(board: SimulationBoard, my_color: Color) -> str:
    """判断游戏阶段"""
    my_hidden = count_hidden(board, my_color)
    enemy_hidden = count_hidden(board, my_color.opposite)
    total_hidden = my_hidden + enemy_hidden

    if total_hidden >= 20:
        return "early"
    elif total_hidden >= 10:
        return "mid"
    else:
        return "late"


def find_best_enemy_capture(board: SimulationBoard, enemy_color: Color) -> float:
    """找出对手能吃掉的最高价值棋子"""
    best_capture = 0.0

    for enemy in board.get_all_pieces(enemy_color):
        potential_moves = board.get_potential_moves(enemy)
        for target_pos in potential_moves:
            target = board.get_piece(target_pos)
            if target and target.color != enemy_color:
                value = get_piece_value(target)
                if value > best_capture:
                    best_capture = value

    return best_capture


def evaluate_coordination(board: SimulationBoard, my_color: Color) -> float:
    """评估棋子协作"""
    bonus = 0.0

    my_pieces = board.get_all_pieces(my_color)
    revealed_pieces = [p for p in my_pieces if not p.is_hidden]

    # 找出高价值棋子
    rooks = [p for p in revealed_pieces if p.actual_type == PieceType.ROOK]
    cannons = [p for p in revealed_pieces if p.actual_type == PieceType.CANNON]
    horses = [p for p in revealed_pieces if p.actual_type == PieceType.HORSE]

    # 双车协作
    if len(rooks) >= 2:
        r1, r2 = rooks[0], rooks[1]
        # 同行或同列的双车更强
        if r1.position.row == r2.position.row or r1.position.col == r2.position.col:
            bonus += 30

    # 炮马配合
    for cannon in cannons:
        for horse in horses:
            dist = abs(cannon.position.row - horse.position.row) + abs(
                cannon.position.col - horse.position.col
            )
            if dist <= 3:
                bonus += 15

    # 保护链 - 高价值棋子被保护
    for piece in revealed_pieces:
        if piece.actual_type in (PieceType.ROOK, PieceType.CANNON, PieceType.HORSE):
            defenders = count_defenders(board, piece.position, my_color)
            if defenders >= 1:
                bonus += 10
            if defenders >= 2:
                bonus += 5

    return bonus


@AIEngine.register(AI_NAME)
class CoordinationAI(AIStrategy):
    """棋子协作 AI

    强调棋子之间的配合
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "棋子协作策略 (v009)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self._rng = random.Random(self.config.seed)

    def select_moves_fen(self, fen: str, n: int = 10) -> list[tuple[str, float]]:
        """选择得分最高的 n 个走法"""
        legal_moves = get_legal_moves_from_fen(fen)
        if not legal_moves:
            return []

        state = parse_fen(fen)
        my_color = state.turn
        sim_board = create_board_from_fen(fen)

        # 计算每个走法的评分
        scored_moves: list[tuple[str, float]] = []
        for move_str in legal_moves:
            move, _ = parse_move(move_str)
            score = self._evaluate_move(sim_board, move, my_color)
            scored_moves.append((move_str, score))

        # 按分数降序排序
        scored_moves.sort(key=lambda x: x[1], reverse=True)

        # 处理同分情况
        result: list[tuple[str, float]] = []
        i = 0
        while i < len(scored_moves) and len(result) < n:
            current_score = scored_moves[i][1]
            same_score_moves = []
            while i < len(scored_moves) and scored_moves[i][1] == current_score:
                same_score_moves.append(scored_moves[i])
                i += 1
            self._rng.shuffle(same_score_moves)
            for move in same_score_moves:
                if len(result) < n:
                    result.append(move)

        return result

    def _evaluate_move(self, board: SimulationBoard, move: JieqiMove, my_color: Color) -> float:
        """评估走法得分"""
        score = 0.0

        target = board.get_piece(move.to_pos)

        # 1. 吃子得分
        if target is not None and target.color != my_color:
            capture_value = get_piece_value(target)
            score += capture_value

            if target.actual_type == PieceType.KING:
                return 100000

        piece = board.get_piece(move.from_pos)
        if piece is None:
            return score

        # 逃离危险加分
        old_attackers = count_attackers(board, move.from_pos, my_color)
        if old_attackers > 0:
            old_defenders = count_defenders(board, move.from_pos, my_color)
            if old_defenders < old_attackers:
                my_piece_value = get_piece_value(piece)
                score += my_piece_value * 0.35

        was_hidden = piece.is_hidden
        captured = board.make_move(move)

        # 2. 检查获胜
        result = board.get_game_result(my_color.opposite)
        if result == GameResult.RED_WIN and my_color == Color.RED:
            board.undo_move(move, captured, was_hidden)
            return 100000
        elif result == GameResult.BLACK_WIN and my_color == Color.BLACK:
            board.undo_move(move, captured, was_hidden)
            return 100000

        # 3. 将军加分
        if board.is_in_check(my_color.opposite):
            score += 60

        # 4. 防守评估（来自 v004）
        moved_piece = board.get_piece(move.to_pos)
        if moved_piece:
            my_piece_value = get_piece_value(moved_piece)
            attackers = count_attackers(board, move.to_pos, my_color)
            defenders = count_defenders(board, move.to_pos, my_color)

            if attackers > 0:
                if defenders >= attackers:
                    score -= my_piece_value * 0.2
                else:
                    score -= my_piece_value * 0.75

            if not moved_piece.is_hidden and moved_piece.actual_type == PieceType.ROOK:
                if attackers > 0:
                    score -= 150

        # 5. 揭子策略（来自 v007）
        if was_hidden:
            game_phase = get_game_phase(board, my_color)
            attackers = count_attackers(board, move.to_pos, my_color)
            defenders = count_defenders(board, move.to_pos, my_color)

            if attackers == 0:
                base_reveal_bonus = 25
            elif defenders >= attackers:
                base_reveal_bonus = 10
            else:
                base_reveal_bonus = -40

            if game_phase == "early":
                phase_multiplier = 0.7
            elif game_phase == "mid":
                phase_multiplier = 1.0
            else:
                phase_multiplier = 1.5

            score += base_reveal_bonus * phase_multiplier

        # 6. 棋子协作 - 核心改进
        # 走后的协作状态
        new_coordination = evaluate_coordination(board, my_color)
        score += new_coordination * 0.15

        # 7. 检查危险棋子
        for ally in board.get_all_pieces(my_color):
            if ally.position == move.to_pos:
                continue
            ally_value = get_piece_value(ally)
            ally_attackers = count_attackers(board, ally.position, my_color)
            if ally_attackers > 0:
                ally_defenders = count_defenders(board, ally.position, my_color)
                if ally_defenders < ally_attackers:
                    score -= ally_value * 0.1

        # 8. 1层前瞻：考虑对手的最佳吃子
        enemy_threat = find_best_enemy_capture(board, my_color.opposite)
        score -= enemy_threat * 0.55

        # 9. 吃子额外加成
        if captured:
            score += get_piece_value(captured) * 0.25

        # 10. 将帅安全评估
        king_pos = board.find_king(my_color)
        if king_pos:
            king_attackers = count_attackers(board, king_pos, my_color)
            if king_attackers > 0:
                score -= 100  # 将帅被威胁扣分

        # 11. 位置评估：过河和中心控制
        if moved_piece and not moved_piece.is_hidden:
            if not move.to_pos.is_on_own_side(my_color):
                score += 12
            if 3 <= move.to_pos.col <= 5:
                score += 6

        board.undo_move(move, captured, was_hidden)

        return score
