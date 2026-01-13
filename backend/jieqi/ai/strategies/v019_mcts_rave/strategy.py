"""
v019_mcts_rave - MCTS with RAVE (Rapid Action Value Estimation)

ID: v019
名称: mcts_rave
描述: MCTS + RAVE，使用 AMAF 加速收敛

特点:
1. RAVE 通过共享走法统计加速学习
2. AMAF (All Moves As First) 提供快速的走法估计
3. 动态平衡 UCT 和 RAVE 估计
4. 适合揭棋中的策略学习
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.ai.evaluator import get_evaluator
from jieqi.fen import create_board_from_fen, get_legal_moves_from_fen, parse_fen, parse_move
from jieqi.simulation import SimulationBoard
from jieqi.types import ActionType, Color, GameResult, JieqiMove, PieceType, Position

if TYPE_CHECKING:
    pass


AI_ID = "v019"
AI_NAME = "mcts_rave"


def move_key(move: JieqiMove) -> tuple[int, int, int, int]:
    """生成走法的唯一键"""
    return (move.from_pos.row, move.from_pos.col, move.to_pos.row, move.to_pos.col)


@dataclass
class RAVENode:
    """MCTS+RAVE 树节点"""

    move: JieqiMove | None
    parent: RAVENode | None
    color: Color
    children: list[RAVENode] = field(default_factory=list)
    untried_moves: list[JieqiMove] = field(default_factory=list)

    # UCT 统计
    visits: int = 0
    wins: float = 0.0

    # RAVE 统计 (AMAF)
    rave_visits: int = 0
    rave_wins: float = 0.0

    def get_value(self, exploration: float, k: float) -> float:
        """计算综合 UCT + RAVE 值

        使用公式: beta * RAVE_value + (1-beta) * UCT_value
        其中 beta = sqrt(k / (3*N + k))，N 是访问次数
        """
        if self.visits == 0:
            return float("inf")

        # UCT 部分
        uct_exploit = self.wins / self.visits
        uct_explore = exploration * math.sqrt(math.log(self.parent.visits) / self.visits)
        uct_value = uct_exploit + uct_explore

        # RAVE 部分
        if self.rave_visits > 0:
            rave_value = self.rave_wins / self.rave_visits
            # 动态 beta：随着访问次数增加，更信任 UCT
            beta = math.sqrt(k / (3 * self.visits + k))
            return beta * rave_value + (1 - beta) * uct_value
        else:
            return uct_value

    def best_child(self, exploration: float, k: float) -> RAVENode:
        """选择综合值最高的子节点"""
        return max(self.children, key=lambda c: c.get_value(exploration, k))

    def add_child(self, move: JieqiMove, color: Color) -> RAVENode:
        """添加子节点"""
        child = RAVENode(move=move, parent=self, color=color)
        self.children.append(child)
        return child

    def is_fully_expanded(self) -> bool:
        return len(self.untried_moves) == 0

    def is_terminal(self) -> bool:
        return self.is_fully_expanded() and len(self.children) == 0


@AIEngine.register(AI_NAME)
class MCTSRaveAI(AIStrategy):
    """MCTS + RAVE AI

    RAVE (Rapid Action Value Estimation) 通过共享走法统计来加速收敛。
    特别适合揭棋这种走法模式相对固定的游戏。
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "MCTS+RAVE AI (v019) - 快速收敛的蒙特卡洛搜索"

    # MCTS 参数
    DEFAULT_ITERATIONS = 15000
    DEFAULT_TIME_LIMIT = 5.0
    EXPLORATION_CONSTANT = 1.0  # RAVE 下可以降低探索常数
    RAVE_K = 1000  # RAVE 平衡参数，越大越信任 RAVE
    MAX_PLAYOUT_DEPTH = 80

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self.time_limit = self.config.time_limit or self.DEFAULT_TIME_LIMIT
        self.max_iterations = (
            self.config.depth * 3000 if self.config.depth > 3 else self.DEFAULT_ITERATIONS
        )
        self._rng = random.Random(self.config.seed)
        self._evaluator = get_evaluator()
        self._iterations_done = 0

        # 全局 RAVE 表：记录每个走法的统计
        self._global_rave: dict[tuple, tuple[int, float]] = {}  # (visits, wins)

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

        # 清空全局 RAVE 表
        self._global_rave.clear()

        # 创建根节点
        root = RAVENode(move=None, parent=None, color=my_color)
        root.untried_moves = jieqi_moves[:]

        start_time = time.time()
        self._iterations_done = 0

        while self._iterations_done < self.max_iterations:
            if time.time() - start_time > self.time_limit:
                break

            board = sim_board.copy()

            # 1. Selection
            node = self._select(root, board)

            # 2. Expansion
            if not node.is_terminal() and node.visits > 0:
                node = self._expand(node, board)

            # 3. Simulation with move tracking
            result, played_moves = self._simulate(board, node.color, my_color)

            # 4. Backpropagation with RAVE update
            self._backpropagate(node, result, my_color, played_moves)

            self._iterations_done += 1

        if not root.children:
            shuffled = legal_moves[:]
            self._rng.shuffle(shuffled)
            return [(move, 0.0) for move in shuffled[:n]]

        # 选择访问次数最多的
        sorted_children = sorted(root.children, key=lambda c: c.visits, reverse=True)

        result = []
        for child in sorted_children[:n]:
            if child.visits > 0 and child.move:
                move_str = move_to_str.get(child.move)
                if move_str:
                    win_rate = child.wins / child.visits
                    score = (win_rate - 0.5) * 2000
                    result.append((move_str, score))

        return result

    def select_move(self, view: PlayerView) -> JieqiMove | None:
        candidates = self.select_moves(view, n=1)
        return candidates[0][0] if candidates else None

    def select_moves(self, view: PlayerView, n: int = 10) -> list[tuple[JieqiMove, float]]:
        if not view.legal_moves:
            return []

        if len(view.legal_moves) == 1:
            return [(view.legal_moves[0], 0.0)]

        my_color = view.viewer
        sim_board = SimulationBoard(view)

        # 清空全局 RAVE 表
        self._global_rave.clear()

        # 创建根节点
        root = RAVENode(move=None, parent=None, color=my_color)
        root.untried_moves = view.legal_moves[:]

        start_time = time.time()
        self._iterations_done = 0

        while self._iterations_done < self.max_iterations:
            if time.time() - start_time > self.time_limit:
                break

            board = sim_board.copy()

            # 1. Selection
            node = self._select(root, board)

            # 2. Expansion
            if not node.is_terminal() and node.visits > 0:
                node = self._expand(node, board)

            # 3. Simulation with move tracking
            result, played_moves = self._simulate(board, node.color, my_color)

            # 4. Backpropagation with RAVE update
            self._backpropagate(node, result, my_color, played_moves)

            self._iterations_done += 1

        if not root.children:
            shuffled = view.legal_moves[:]
            self._rng.shuffle(shuffled)
            return [(move, 0.0) for move in shuffled[:n]]

        # 选择访问次数最多的
        sorted_children = sorted(root.children, key=lambda c: c.visits, reverse=True)

        result = []
        for child in sorted_children[:n]:
            if child.visits > 0:
                win_rate = child.wins / child.visits
                score = (win_rate - 0.5) * 2000
                result.append((child.move, score))

        return result

    def _select(self, node: RAVENode, board: SimulationBoard) -> RAVENode:
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node

            node = node.best_child(self.EXPLORATION_CONSTANT, self.RAVE_K)

            if node.move:
                piece = board.get_piece(node.move.from_pos)
                if piece:
                    board.make_move(node.move)

        return node

    def _expand(self, node: RAVENode, board: SimulationBoard) -> RAVENode:
        if not node.untried_moves:
            legal_moves = board.get_legal_moves(node.color)
            node.untried_moves = legal_moves

        if not node.untried_moves:
            return node

        # 使用全局 RAVE 启发式选择扩展节点
        move = self._select_expand_move(node.untried_moves)
        node.untried_moves.remove(move)

        piece = board.get_piece(move.from_pos)
        if piece:
            board.make_move(move)

        child = node.add_child(move, node.color.opposite)
        child.untried_moves = board.get_legal_moves(child.color)

        # 初始化 RAVE 统计（从全局表获取）
        key = move_key(move)
        if key in self._global_rave:
            child.rave_visits, child.rave_wins = self._global_rave[key]

        return child

    def _select_expand_move(self, moves: list[JieqiMove]) -> JieqiMove:
        """使用全局 RAVE 启发式选择扩展走法"""
        # 优先选择 RAVE 胜率高的走法
        best_move = None
        best_score = -1.0

        for move in moves:
            key = move_key(move)
            if key in self._global_rave:
                visits, wins = self._global_rave[key]
                if visits > 0:
                    score = wins / visits
                    if score > best_score:
                        best_score = score
                        best_move = move

        # 如果没有 RAVE 信息，随机选择
        return best_move if best_move else self._rng.choice(moves)

    def _simulate(
        self, board: SimulationBoard, current_color: Color, root_color: Color
    ) -> tuple[float, list[tuple[Color, JieqiMove]]]:
        """模拟并记录走法"""
        color = current_color
        played_moves: list[tuple[Color, JieqiMove]] = []

        for _ in range(self.MAX_PLAYOUT_DEPTH):
            # 获取合法走法（只计算一次）
            legal_moves = board.get_legal_moves(color)

            # 用预计算的走法检查游戏是否结束
            result = board.get_game_result(color, legal_moves)
            if result != GameResult.ONGOING:
                if result == GameResult.RED_WIN:
                    return (1.0 if root_color == Color.RED else 0.0, played_moves)
                elif result == GameResult.BLACK_WIN:
                    return (1.0 if root_color == Color.BLACK else 0.0, played_moves)
                else:
                    return (0.5, played_moves)

            if not legal_moves:
                return (0.0 if color == root_color else 1.0, played_moves)

            move = self._select_playout_move(board, legal_moves, color)
            played_moves.append((color, move))

            piece = board.get_piece(move.from_pos)
            if piece:
                board.make_move(move)

            color = color.opposite

        # 达到深度限制，使用评估
        raw_score = self._evaluator.evaluate(board, root_color)
        normalized = self._evaluator.normalize_score(raw_score)
        return (self._evaluator.score_to_win_rate(normalized), played_moves)

    def _select_playout_move(
        self, board: SimulationBoard, moves: list[JieqiMove], color: Color
    ) -> JieqiMove:
        """启发式 playout 走法选择"""
        captures = []
        reveals = []
        others = []

        for move in moves:
            target = board.get_piece(move.to_pos)
            if target and target.color != color:
                captures.append(move)
            elif move.action_type == ActionType.REVEAL_AND_MOVE:
                reveals.append(move)
            else:
                others.append(move)

        # 优先级：吃子 > 揭子 > 其他
        if captures and self._rng.random() < 0.85:
            return self._rng.choice(captures)
        if reveals and self._rng.random() < 0.3:
            return self._rng.choice(reveals)

        return self._rng.choice(moves)

    def _backpropagate(
        self,
        node: RAVENode,
        result: float,
        root_color: Color,
        played_moves: list[tuple[Color, JieqiMove]],
    ) -> None:
        """回传并更新 RAVE 统计"""
        # 收集 playout 中每方走过的走法
        red_moves = {move_key(m) for c, m in played_moves if c == Color.RED}
        black_moves = {move_key(m) for c, m in played_moves if c == Color.BLACK}

        # 更新全局 RAVE 表
        for color, move in played_moves:
            key = move_key(move)
            visits, wins = self._global_rave.get(key, (0, 0.0))
            if color == root_color:
                self._global_rave[key] = (visits + 1, wins + result)
            else:
                self._global_rave[key] = (visits + 1, wins + (1.0 - result))

        # 回传树节点
        while node is not None:
            node.visits += 1
            if node.parent is None:
                node.wins += result
            else:
                if node.color == root_color:
                    node.wins += result
                else:
                    node.wins += 1.0 - result

            # 更新兄弟节点的 RAVE 统计（AMAF）
            if node.parent is not None:
                sibling_moves = red_moves if node.parent.color == Color.RED else black_moves
                for sibling in node.parent.children:
                    if sibling.move and move_key(sibling.move) in sibling_moves:
                        sibling.rave_visits += 1
                        if sibling.color == root_color:
                            sibling.rave_wins += result
                        else:
                            sibling.rave_wins += 1.0 - result

            node = node.parent

    def get_evaluation(self, view: PlayerView) -> dict:
        sim_board = SimulationBoard(view)
        return self._evaluator.format_evaluation(sim_board, view.viewer)
