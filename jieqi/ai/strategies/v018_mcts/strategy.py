"""
v018_mcts - 基础 Monte Carlo Tree Search (MCTS/UCT)

ID: v018
名称: mcts
描述: 使用 UCT (Upper Confidence Bound for Trees) 的蒙特卡洛树搜索

特点:
1. 适合处理揭棋中的不确定性（暗子）
2. 通过随机模拟评估局面
3. UCT 平衡探索与利用
4. 支持时间限制控制
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
from jieqi.types import Color, GameResult, JieqiMove

if TYPE_CHECKING:
    from jieqi.view import PlayerView


AI_ID = "v018"
AI_NAME = "mcts"


@dataclass
class MCTSNode:
    """MCTS 树节点"""

    move: JieqiMove | None  # 到达此节点的走法（根节点为 None）
    parent: MCTSNode | None  # 父节点
    color: Color  # 当前回合的颜色
    children: list[MCTSNode] = field(default_factory=list)
    untried_moves: list[JieqiMove] = field(default_factory=list)

    # 统计信息
    visits: int = 0
    wins: float = 0.0  # 从此节点开始的胜利次数

    def ucb1(self, exploration: float = 1.414) -> float:
        """计算 UCB1 值"""
        if self.visits == 0:
            return float("inf")
        exploit = self.wins / self.visits
        explore = exploration * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploit + explore

    def best_child(self, exploration: float = 1.414) -> MCTSNode:
        """选择 UCB1 值最高的子节点"""
        return max(self.children, key=lambda c: c.ucb1(exploration))

    def add_child(self, move: JieqiMove, color: Color) -> MCTSNode:
        """添加子节点"""
        child = MCTSNode(move=move, parent=self, color=color)
        self.children.append(child)
        return child

    def is_fully_expanded(self) -> bool:
        """是否已完全展开"""
        return len(self.untried_moves) == 0

    def is_terminal(self) -> bool:
        """是否为终端节点"""
        return self.is_fully_expanded() and len(self.children) == 0


@AIEngine.register(AI_NAME)
class MCTSAI(AIStrategy):
    """基础 MCTS AI

    使用 UCT (Upper Confidence Bound for Trees) 进行树搜索。
    揭棋中暗子的处理：按位置规则走，但不知道真实身份。
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "MCTS AI (v018) - 蒙特卡洛树搜索"

    # MCTS 参数
    DEFAULT_ITERATIONS = 10000  # 默认迭代次数
    DEFAULT_TIME_LIMIT = 5.0  # 默认时间限制（秒）
    EXPLORATION_CONSTANT = 1.414  # UCB1 探索常数
    MAX_PLAYOUT_DEPTH = 100  # 随机模拟最大深度

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self.time_limit = self.config.time_limit or self.DEFAULT_TIME_LIMIT
        self.max_iterations = (
            self.config.depth * 2000 if self.config.depth > 3 else self.DEFAULT_ITERATIONS
        )
        self._rng = random.Random(self.config.seed)
        self._evaluator = get_evaluator()
        self._iterations_done = 0

    def select_moves_fen(self, fen: str, n: int = 10) -> list[tuple[str, float]]:
        """选择得分最高的 n 个走法"""
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
        root = MCTSNode(move=None, parent=None, color=my_color)
        root.untried_moves = jieqi_moves[:]

        start_time = time.time()
        self._iterations_done = 0

        # MCTS 主循环
        while self._iterations_done < self.max_iterations:
            if time.time() - start_time > self.time_limit:
                break

            # 复制棋盘进行模拟
            board = sim_board.copy()

            # 1. Selection - 选择
            node = self._select(root, board)

            # 2. Expansion - 扩展
            if not node.is_terminal() and node.visits > 0:
                node = self._expand(node, board)

            # 3. Simulation - 模拟（Playout）
            result = self._simulate(board, node.color)

            # 4. Backpropagation - 回传
            self._backpropagate(node, result, my_color)

            self._iterations_done += 1

        # 收集结果：选择访问次数最多的子节点
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
                    win_rate = child.wins / child.visits
                    # 转换为 -1000 到 1000 的分数
                    score = (win_rate - 0.5) * 2000
                    result.append((move_str, score))

        return result

    def _select(self, node: MCTSNode, board: SimulationBoard) -> MCTSNode:
        """Selection 阶段：沿着树选择最优路径"""
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node

            # 选择 UCB1 值最高的子节点
            node = node.best_child(self.EXPLORATION_CONSTANT)

            # 在棋盘上执行走法
            if node.move:
                piece = board.get_piece(node.move.from_pos)
                if piece:
                    board.make_move(node.move)

        return node

    def _expand(self, node: MCTSNode, board: SimulationBoard) -> MCTSNode:
        """Expansion 阶段：扩展一个新节点"""
        if not node.untried_moves:
            # 获取当前局面的合法走法
            legal_moves = board.get_legal_moves(node.color)
            node.untried_moves = legal_moves

        if not node.untried_moves:
            return node

        # 随机选择一个未尝试的走法
        move = self._rng.choice(node.untried_moves)
        node.untried_moves.remove(move)

        # 执行走法
        piece = board.get_piece(move.from_pos)
        if piece:
            board.make_move(move)

        # 创建子节点
        child = node.add_child(move, node.color.opposite)

        # 获取子节点的合法走法
        child.untried_moves = board.get_legal_moves(child.color)

        return child

    def _simulate(self, board: SimulationBoard, current_color: Color) -> float:
        """Simulation 阶段：随机模拟到游戏结束"""
        color = current_color

        for _ in range(self.MAX_PLAYOUT_DEPTH):
            # 获取合法走法（只计算一次）
            legal_moves = board.get_legal_moves(color)

            # 用预计算的走法检查游戏是否结束
            result = board.get_game_result(color, legal_moves)
            if result != GameResult.ONGOING:
                if result == GameResult.RED_WIN:
                    return 1.0 if current_color == Color.RED else 0.0
                elif result == GameResult.BLACK_WIN:
                    return 1.0 if current_color == Color.BLACK else 0.0
                else:
                    return 0.5  # 和棋

            if not legal_moves:
                # 无走法，被困毙
                return 0.0 if color == current_color else 1.0

            # 随机选择走法（可以改进为启发式选择）
            move = self._select_playout_move(board, legal_moves, color)

            piece = board.get_piece(move.from_pos)
            if piece:
                board.make_move(move)

            color = color.opposite

        # 达到最大深度，使用评估函数
        raw_score = self._evaluator.evaluate(board, current_color)
        # 转换为 0-1 范围的胜率
        normalized = self._evaluator.normalize_score(raw_score)
        return self._evaluator.score_to_win_rate(normalized)

    def _select_playout_move(
        self, board: SimulationBoard, moves: list[JieqiMove], color: Color
    ) -> JieqiMove:
        """Playout 阶段的走法选择

        使用简单启发式：优先吃子，其次随机
        """
        # 分类走法
        captures = []
        others = []

        for move in moves:
            target = board.get_piece(move.to_pos)
            if target and target.color != color:
                # 吃子走法
                captures.append(move)
            else:
                others.append(move)

        # 80% 概率选择吃子（如果有）
        if captures and self._rng.random() < 0.8:
            return self._rng.choice(captures)

        # 否则随机选择
        return self._rng.choice(moves)

    def _backpropagate(self, node: MCTSNode, result: float, root_color: Color) -> None:
        """Backpropagation 阶段：回传结果"""
        while node is not None:
            node.visits += 1
            # 从该节点玩家的视角计算胜利
            if node.parent is None:
                # 根节点
                node.wins += result
            else:
                # 子节点：如果是对方回合，则反转结果
                if node.color == root_color:
                    node.wins += result
                else:
                    node.wins += 1.0 - result
            node = node.parent

    def get_evaluation(self, view: PlayerView) -> dict:
        """获取当前局面评估"""
        sim_board = SimulationBoard(view)
        return self._evaluator.format_evaluation(sim_board, view.viewer)
