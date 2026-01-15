"""
v020_mcts_eval - MCTS with Evaluation Function (Policy-Value Style)

ID: v020
名称: mcts_eval
描述: MCTS + 评估函数混合，使用评估函数代替完全随机 playout

特点:
1. 浅层 playout + 评估函数（类似 AlphaGo 的 Value Network 思路）
2. 更多迭代次数，更深的搜索
3. Progressive Widening 处理高分支因子
4. 支持更长时间的深度搜索
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.ai.evaluator import PIECE_BASE_VALUES, get_evaluator
from jieqi.fen import create_board_from_fen, get_legal_moves_from_fen, parse_fen, parse_move
from jieqi.simulation import SimulationBoard
from jieqi.types import ActionType, Color, GameResult, JieqiMove, PieceType

if TYPE_CHECKING:
    from jieqi.view import PlayerView


AI_ID = "v020"
AI_NAME = "mcts_eval"


@dataclass
class EvalNode:
    """MCTS+Eval 树节点"""

    move: JieqiMove | None
    parent: EvalNode | None
    color: Color
    children: list[EvalNode] = field(default_factory=list)
    untried_moves: list[JieqiMove] = field(default_factory=list)

    # 统计
    visits: int = 0
    value_sum: float = 0.0  # 累计评分

    # Progressive Widening
    expansion_count: int = 0

    # 缓存
    _move_priority: float = 0.0  # 走法先验优先级

    @property
    def value(self) -> float:
        """平均价值"""
        if self.visits == 0:
            return 0.0
        return self.value_sum / self.visits

    def puct(self, exploration: float, parent_visits: int) -> float:
        """计算 PUCT 值（类似 AlphaGo）

        PUCT = Q + c * P * sqrt(N_parent) / (1 + N)
        """
        if self.visits == 0:
            return float("inf")

        q = self.value
        u = exploration * self._move_priority * math.sqrt(parent_visits) / (1 + self.visits)
        return q + u

    def best_child(self, exploration: float) -> EvalNode:
        """选择 PUCT 值最高的子节点"""
        return max(self.children, key=lambda c: c.puct(exploration, self.visits))

    def add_child(self, move: JieqiMove, color: Color, priority: float = 1.0) -> EvalNode:
        """添加子节点"""
        child = EvalNode(move=move, parent=self, color=color)
        child._move_priority = priority
        self.children.append(child)
        self.expansion_count += 1
        return child

    def should_expand(self) -> bool:
        """Progressive Widening: 是否应该扩展更多子节点

        扩展条件: N_children < C * N^alpha
        """
        if not self.untried_moves:
            return False
        # 参数：alpha = 0.5, C = 2
        max_children = 2.0 * math.sqrt(max(1, self.visits))
        return len(self.children) < max_children

    def is_terminal(self) -> bool:
        return len(self.untried_moves) == 0 and len(self.children) == 0


@AIEngine.register(AI_NAME)
class MCTSEvalAI(AIStrategy):
    """MCTS + 评估函数 AI

    使用评估函数代替完全随机 playout，类似 AlphaGo 的 Policy-Value 思路。
    支持更多迭代和更深搜索。
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "MCTS+Eval AI (v020) - 评估函数混合的深度搜索"

    # 搜索参数
    DEFAULT_ITERATIONS = 20000
    DEFAULT_TIME_LIMIT = 8.0
    EXPLORATION_CONSTANT = 2.0  # PUCT 探索常数
    PLAYOUT_DEPTH = 8  # 浅层 playout 深度
    EVAL_WEIGHT = 0.7  # 评估函数权重（vs playout 结果）

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self.time_limit = self.config.time_limit or self.DEFAULT_TIME_LIMIT
        # 更多迭代次数
        self.max_iterations = (
            self.config.depth * 5000 if self.config.depth > 3 else self.DEFAULT_ITERATIONS
        )
        self._rng = random.Random(self.config.seed)
        self._evaluator = get_evaluator()
        self._iterations_done = 0

    def select_moves_fen(self, fen: str, n: int = 10) -> list[tuple[str, float]]:
        """基于 FEN 返回 Top-N 候选走法"""
        legal_moves = get_legal_moves_from_fen(fen)
        if not legal_moves:
            return []

        if len(legal_moves) == 1:
            return [(legal_moves[0], 0.0)]

        state = parse_fen(fen)
        my_color = state.turn
        sim_board = create_board_from_fen(fen)

        # 解析走法
        parsed_moves = [(move_str, parse_move(move_str)[0]) for move_str in legal_moves]
        move_to_str = {m: s for s, m in parsed_moves}
        jieqi_moves = [m for _, m in parsed_moves]

        # 创建根节点
        root = EvalNode(move=None, parent=None, color=my_color)

        # 按优先级排序初始走法
        prioritized = self._prioritize_moves(sim_board, jieqi_moves, my_color)
        root.untried_moves = [m for m, _ in prioritized]

        start_time = time.time()
        self._iterations_done = 0

        while self._iterations_done < self.max_iterations:
            if time.time() - start_time > self.time_limit:
                break

            board = sim_board.copy()

            # 1. Selection
            node, path = self._select(root, board)

            # 2. Expansion (Progressive Widening)
            if node.should_expand():
                node = self._expand(node, board)

            # 3. Evaluation (浅层 playout + 评估)
            value = self._evaluate_node(board, node.color, my_color)

            # 4. Backpropagation
            self._backpropagate(node, value, my_color)

            self._iterations_done += 1

        if not root.children:
            shuffled = legal_moves[:]
            self._rng.shuffle(shuffled)
            return [(move, 0.0) for move in shuffled[:n]]

        # 按访问次数排序
        sorted_children = sorted(root.children, key=lambda c: c.visits, reverse=True)

        result = []
        for child in sorted_children[:n]:
            if child.visits > 0 and child.move:
                move_str = move_to_str.get(child.move)
                if move_str:
                    # 使用平均 value（已归一化到 0-1）
                    score = (child.value - 0.5) * 2000
                    result.append((move_str, score))

        return result

    def _prioritize_moves(
        self, board: SimulationBoard, moves: list[JieqiMove], color: Color
    ) -> list[tuple[JieqiMove, float]]:
        """为走法分配优先级（先验概率）"""
        scored = []

        for move in moves:
            priority = 1.0

            piece = board.get_piece(move.from_pos)
            target = board.get_piece(move.to_pos)

            # 吃子优先
            if target and target.color != color:
                victim_value = (
                    PIECE_BASE_VALUES.get(target.actual_type, 100) if target.actual_type else 100
                )
                priority += victim_value / 50

            # 吃将/帅最高优先
            if target and target.actual_type == PieceType.KING:
                priority += 100

            # 揭子走法中等优先
            if move.action_type == ActionType.REVEAL_AND_MOVE:
                priority += 0.5
                # 在对方阵地揭子更好
                if piece and not move.to_pos.is_on_own_side(color):
                    priority += 0.5

            # 车、炮、马走法优先
            if piece and piece.actual_type in [PieceType.ROOK, PieceType.CANNON, PieceType.HORSE]:
                priority += 0.3

            scored.append((move, priority))

        # 按优先级排序并归一化
        scored.sort(key=lambda x: -x[1])
        total = sum(p for _, p in scored)
        if total > 0:
            scored = [(m, p / total) for m, p in scored]

        return scored

    def _select(self, node: EvalNode, board: SimulationBoard) -> tuple[EvalNode, list[EvalNode]]:
        """Selection 阶段"""
        path = [node]

        while node.children:
            if node.should_expand():
                break

            node = node.best_child(self.EXPLORATION_CONSTANT)
            path.append(node)

            if node.move:
                piece = board.get_piece(node.move.from_pos)
                if piece:
                    board.make_move(node.move)

        return node, path

    def _expand(self, node: EvalNode, board: SimulationBoard) -> EvalNode:
        """Expansion 阶段（Progressive Widening）"""
        if not node.untried_moves:
            legal_moves = board.get_legal_moves(node.color)
            prioritized = self._prioritize_moves(board, legal_moves, node.color)
            node.untried_moves = [m for m, _ in prioritized]

        if not node.untried_moves:
            return node

        # 选择优先级最高的未尝试走法
        move = node.untried_moves.pop(0)

        # 计算先验优先级
        board.get_piece(move.from_pos)
        target = board.get_piece(move.to_pos)
        priority = 1.0
        if target and target.color != node.color:
            priority += 2.0
        if move.action_type == ActionType.REVEAL_AND_MOVE:
            priority += 0.5

        piece_at_from = board.get_piece(move.from_pos)
        if piece_at_from:
            board.make_move(move)

        child = node.add_child(move, node.color.opposite, priority)
        child.untried_moves = board.get_legal_moves(child.color)

        return child

    def _evaluate_node(
        self, board: SimulationBoard, current_color: Color, root_color: Color
    ) -> float:
        """评估节点：浅层 playout + 评估函数"""
        # 检查游戏是否结束
        result = board.get_game_result(current_color)
        if result != GameResult.ONGOING:
            if result == GameResult.RED_WIN:
                return 1.0 if root_color == Color.RED else 0.0
            elif result == GameResult.BLACK_WIN:
                return 1.0 if root_color == Color.BLACK else 0.0
            else:
                return 0.5

        # 浅层 playout
        playout_value = self._shallow_playout(board.copy(), current_color, root_color)

        # 静态评估
        raw_score = self._evaluator.evaluate(board, root_color)
        normalized = self._evaluator.normalize_score(raw_score)
        eval_value = self._evaluator.score_to_win_rate(normalized)

        # 混合
        return self.EVAL_WEIGHT * eval_value + (1 - self.EVAL_WEIGHT) * playout_value

    def _shallow_playout(
        self, board: SimulationBoard, current_color: Color, root_color: Color
    ) -> float:
        """浅层 playout"""
        color = current_color

        for _ in range(self.PLAYOUT_DEPTH):
            # 获取合法走法（只计算一次）
            legal_moves = board.get_legal_moves(color)

            # 用预计算的走法检查游戏是否结束
            result = board.get_game_result(color, legal_moves)
            if result != GameResult.ONGOING:
                if result == GameResult.RED_WIN:
                    return 1.0 if root_color == Color.RED else 0.0
                elif result == GameResult.BLACK_WIN:
                    return 1.0 if root_color == Color.BLACK else 0.0
                else:
                    return 0.5

            if not legal_moves:
                return 0.0 if color == root_color else 1.0

            # 启发式选择
            move = self._select_playout_move(board, legal_moves, color)

            piece = board.get_piece(move.from_pos)
            if piece:
                board.make_move(move)

            color = color.opposite

        # 使用评估函数
        raw_score = self._evaluator.evaluate(board, root_color)
        normalized = self._evaluator.normalize_score(raw_score)
        return self._evaluator.score_to_win_rate(normalized)

    def _select_playout_move(
        self, board: SimulationBoard, moves: list[JieqiMove], color: Color
    ) -> JieqiMove:
        """启发式 playout 走法选择"""
        # 分类走法
        king_captures = []
        captures = []
        checks = []
        others = []

        enemy_king_pos = board.find_king(color.opposite)

        for move in moves:
            target = board.get_piece(move.to_pos)
            if target and target.color != color:
                if target.actual_type == PieceType.KING:
                    king_captures.append(move)
                else:
                    captures.append(move)
            elif move.to_pos == enemy_king_pos:
                checks.append(move)
            else:
                others.append(move)

        # 优先级：吃将 > 吃子 > 将军 > 其他
        if king_captures:
            return self._rng.choice(king_captures)
        if captures and self._rng.random() < 0.9:
            # 按 MVV-LVA 排序
            captures.sort(
                key=lambda m: PIECE_BASE_VALUES.get(
                    board.get_piece(m.to_pos).actual_type if board.get_piece(m.to_pos) else None, 0
                ),
                reverse=True,
            )
            return captures[0] if self._rng.random() < 0.7 else self._rng.choice(captures)
        if checks and self._rng.random() < 0.5:
            return self._rng.choice(checks)

        return self._rng.choice(moves)

    def _backpropagate(self, node: EvalNode, value: float, root_color: Color) -> None:
        """回传"""
        while node is not None:
            node.visits += 1
            # 从该节点玩家的视角
            if node.parent is None:
                node.value_sum += value
            else:
                if node.color == root_color:
                    node.value_sum += value
                else:
                    node.value_sum += 1.0 - value
            node = node.parent

    def get_evaluation(self, view: PlayerView) -> dict:
        sim_board = SimulationBoard(view)
        return self._evaluator.format_evaluation(sim_board, view.viewer)
