//! IT2 (Iterative Deepening v2) - Expectimax 概率处理
//!
//! ## 核心特点
//! - 揭子走法使用 Chance 节点处理概率
//! - Negamax 框架 + Alpha-Beta 剪枝
//!
//! ## 评估函数设计
//! 内部总是计算"红方价值 - 黑方价值"，最后根据视角翻转符号。
//! 这样所有变量都是 red/black，避免 my/opp 的混淆。
//!
//! ```text
//! evaluate(board, Red)   →  raw_score
//! evaluate(board, Black) → -raw_score
//! ```
//!
//! 暗子期望值按颜色固定计算：
//! - red_hidden_ev: 红方暗子池的期望价值
//! - black_hidden_ev: 黑方暗子池的期望价值
//!
//! 吃子潜力：
//! - 红方吃黑方 → 被吃暗子用 black_hidden_ev
//! - 黑方吃红方 → 被吃暗子用 red_hidden_ev

use super::{sort_and_truncate, AIConfig, AIStrategy, ScoredMove, DEPTH_REACHED, NODE_COUNT};
use crate::board::Board;
use crate::types::{ActionType, Color, GameResult, JieqiMove, PieceType};
use rand::prelude::*;
use std::cmp::Ordering as CmpOrdering;
use std::sync::atomic::Ordering as AtomicOrdering;
use std::time::{Duration, Instant};

/// 棋子类型数量
const PIECE_TYPE_COUNT: usize = 7;

/// 初始棋子数量：King, Advisor, Elephant, Horse, Rook, Cannon, Pawn
const INITIAL_COUNT: [u8; PIECE_TYPE_COUNT] = [1, 2, 2, 2, 2, 2, 5];

/// 棋子价值
const PIECE_VALUES: [i32; PIECE_TYPE_COUNT] = [100000, 200, 200, 400, 900, 450, 100];

/// Mate score (胜负分)
const MATE_SCORE: f64 = 100000.0;

/// Ply penalty multiplier for Mate Distance Bonus
/// 乘以 10 让不同步数的胜负分数差距更明显
const PLY_PENALTY: i32 = 10;

/// 所有棋子类型
const ALL_PIECE_TYPES: [PieceType; PIECE_TYPE_COUNT] = [
    PieceType::King,
    PieceType::Advisor,
    PieceType::Elephant,
    PieceType::Horse,
    PieceType::Rook,
    PieceType::Cannon,
    PieceType::Pawn,
];

/// 棋子类型转索引
#[inline]
fn piece_type_to_index(pt: PieceType) -> usize {
    match pt {
        PieceType::King => 0,
        PieceType::Advisor => 1,
        PieceType::Elephant => 2,
        PieceType::Horse => 3,
        PieceType::Rook => 4,
        PieceType::Cannon => 5,
        PieceType::Pawn => 6,
    }
}

/// PST (Piece-Square Table) - 从红方视角，row 0 是红方底线
/// 每格分数单位：兵=100 时，PST 分数约 0-30
type PstTable = [[i32; 9]; 10];

/// 将/帅：待在九宫，中心稍好
const PST_KING: PstTable = [
    [0, 0, 0, 5, 10, 5, 0, 0, 0],
    [0, 0, 0, 5, 10, 5, 0, 0, 0],
    [0, 0, 0, 5, 5, 5, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
];

/// 士/仕：守在九宫
const PST_ADVISOR: PstTable = [
    [0, 0, 0, 10, 0, 10, 0, 0, 0],
    [0, 0, 0, 0, 15, 0, 0, 0, 0],
    [0, 0, 0, 10, 0, 10, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
];

/// 象/相：守住己方阵地
const PST_ELEPHANT: PstTable = [
    [0, 0, 10, 0, 0, 0, 10, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [5, 0, 0, 0, 15, 0, 0, 0, 5],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 10, 0, 0, 0, 10, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
];

/// 马：中心和前方价值高
const PST_HORSE: PstTable = [
    [0, 0, 5, 10, 10, 10, 5, 0, 0],
    [0, 5, 10, 15, 15, 15, 10, 5, 0],
    [5, 10, 15, 20, 20, 20, 15, 10, 5],
    [5, 10, 15, 20, 25, 20, 15, 10, 5],
    [5, 10, 15, 20, 25, 20, 15, 10, 5],
    [5, 10, 15, 20, 25, 20, 15, 10, 5],
    [10, 15, 20, 25, 30, 25, 20, 15, 10],
    [10, 15, 20, 25, 30, 25, 20, 15, 10],
    [5, 10, 15, 20, 25, 20, 15, 10, 5],
    [0, 5, 10, 15, 20, 15, 10, 5, 0],
];

/// 车：开放线、前方价值高
const PST_ROOK: PstTable = [
    [10, 10, 10, 15, 15, 15, 10, 10, 10],
    [10, 15, 15, 20, 20, 20, 15, 15, 10],
    [10, 15, 15, 20, 20, 20, 15, 15, 10],
    [10, 15, 15, 20, 20, 20, 15, 15, 10],
    [10, 15, 15, 20, 20, 20, 15, 15, 10],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [20, 25, 25, 30, 30, 30, 25, 25, 20],
    [20, 25, 25, 30, 30, 30, 25, 25, 20],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
];

/// 炮：中间位置价值高
const PST_CANNON: PstTable = [
    [10, 10, 10, 15, 15, 15, 10, 10, 10],
    [10, 15, 15, 20, 20, 20, 15, 15, 10],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [10, 15, 15, 20, 20, 20, 15, 15, 10],
    [5, 10, 10, 15, 15, 15, 10, 10, 5],
];

/// 兵/卒：过河后价值大增，越前越好
const PST_PAWN: PstTable = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [5, 0, 10, 0, 15, 0, 10, 0, 5],
    [10, 0, 15, 0, 20, 0, 15, 0, 10],
    [15, 20, 25, 30, 35, 30, 25, 20, 15],
    [20, 25, 30, 35, 40, 35, 30, 25, 20],
    [25, 30, 35, 40, 45, 40, 35, 30, 25],
    [30, 35, 40, 45, 50, 45, 40, 35, 30],
    [35, 40, 45, 50, 55, 50, 45, 40, 35],
];

/// 获取 PST 分数
#[inline]
fn get_pst_score(piece_type: PieceType, row: usize, col: usize, is_red: bool) -> i32 {
    // 黑方需要翻转棋盘（row 9 变 row 0）
    let r = if is_red { row } else { 9 - row };

    match piece_type {
        PieceType::King => PST_KING[r][col],
        PieceType::Advisor => PST_ADVISOR[r][col],
        PieceType::Elephant => PST_ELEPHANT[r][col],
        PieceType::Horse => PST_HORSE[r][col],
        PieceType::Rook => PST_ROOK[r][col],
        PieceType::Cannon => PST_CANNON[r][col],
        PieceType::Pawn => PST_PAWN[r][col],
    }
}

/// 剩余暗子池的概率分布
#[derive(Debug, Clone)]
pub struct HiddenPieceDistribution {
    /// 每种棋子类型剩余数量
    remaining: [u8; PIECE_TYPE_COUNT],
    /// 剩余暗子总数
    total: u8,
}

impl HiddenPieceDistribution {
    /// 从棋盘状态计算某方的剩余暗子分布
    pub fn from_board(board: &Board, color: Color) -> Self {
        let mut revealed: [u8; PIECE_TYPE_COUNT] = [0; PIECE_TYPE_COUNT];
        let mut hidden_count: u8 = 0;

        for piece in board.get_all_pieces(Some(color)) {
            if piece.is_hidden {
                hidden_count += 1;
            } else if let Some(pt) = piece.actual_type {
                let idx = piece_type_to_index(pt);
                revealed[idx] += 1;
            }
        }

        let mut remaining = [0u8; PIECE_TYPE_COUNT];
        for i in 0..PIECE_TYPE_COUNT {
            remaining[i] = INITIAL_COUNT[i].saturating_sub(revealed[i]);
        }

        HiddenPieceDistribution {
            remaining,
            total: hidden_count,
        }
    }

    /// 返回所有可能的棋子类型及其概率（过滤掉概率为0的）
    pub fn possible_types(&self) -> Vec<(PieceType, f64)> {
        if self.total == 0 {
            return Vec::new();
        }

        let total_remaining: u8 = self.remaining.iter().sum();
        if total_remaining == 0 {
            return Vec::new();
        }

        ALL_PIECE_TYPES
            .iter()
            .enumerate()
            .filter_map(|(i, &pt)| {
                if self.remaining[i] > 0 {
                    Some((pt, self.remaining[i] as f64 / total_remaining as f64))
                } else {
                    None
                }
            })
            .collect()
    }

    /// 计算期望价值
    /// 除了车和炮，其他暗子价值打 7 折（鼓励揭车/炮）
    pub fn expected_value(&self) -> i32 {
        let total_remaining: u8 = self.remaining.iter().sum();
        if total_remaining == 0 {
            return 300; // 默认值
        }

        let mut sum: i64 = 0;
        for i in 0..PIECE_TYPE_COUNT {
            let base_value = PIECE_VALUES[i] as i64;
            // 车(4)和炮(5)保持原价值，其他打7折
            let value = if i == 4 || i == 5 {
                base_value
            } else {
                base_value * 7 / 10
            };
            sum += (self.remaining[i] as i64) * value;
        }

        (sum / total_remaining as i64) as i32
    }
}

/// 搜索上下文（减少参数传递）
#[derive(Clone, Copy)]
struct SearchContext {
    /// 剩余搜索深度
    depth: i32,
    /// 从根节点开始的步数
    ply: i32,
    /// Alpha-Beta 窗口
    alpha: f64,
    beta: f64,
}

impl SearchContext {
    fn new(depth: i32) -> Self {
        Self {
            depth,
            ply: 0,
            alpha: f64::NEG_INFINITY,
            beta: f64::INFINITY,
        }
    }

    /// 进入下一层（对手视角）
    fn next_ply(&self) -> Self {
        Self {
            depth: self.depth - 1,
            ply: self.ply + 1,
            alpha: -self.beta,
            beta: -self.alpha,
        }
    }
}

/// IT2 AI - Expectimax 搜索
pub struct IT2AI {
    max_depth: u32,
    rng: StdRng,
    randomness: f64,
    time_limit: Option<Duration>,
}

impl IT2AI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        // 如果设置了时间限制，允许无限加深；否则使用配置的深度
        let max_depth = if config.time_limit.is_some() {
            50
        } else {
            config.depth
        };
        IT2AI {
            max_depth,
            rng,
            randomness: config.randomness,
            time_limit: config.time_limit.map(Duration::from_secs_f64),
        }
    }

    /// 评估函数（从 color 视角）
    ///
    /// 内部逻辑：总是计算"红方价值 - 黑方价值"，最后根据视角翻转符号
    /// 这样避免 my/opp 的混淆，所有变量都是 red/black
    fn evaluate(&self, board: &Board, color: Color) -> f64 {
        // 按颜色固定计算暗子期望（不依赖 color 参数）
        let red_hidden_ev =
            HiddenPieceDistribution::from_board(board, Color::Red).expected_value() as f64;
        let black_hidden_ev =
            HiddenPieceDistribution::from_board(board, Color::Black).expected_value() as f64;

        // 内部总是计算：红方价值 - 黑方价值
        let mut raw_score = 0.0;

        for piece in board.get_all_pieces(None) {
            let (value, pst) = if piece.is_hidden {
                // 暗子：根据颜色使用对应的期望值
                let ev = if piece.color == Color::Red {
                    red_hidden_ev
                } else {
                    black_hidden_ev
                };
                (ev, 0.0)
            } else if let Some(pt) = piece.actual_type {
                // 明子：实际价值 + PST
                let pos = piece.position;
                let pst_score = get_pst_score(
                    pt,
                    pos.row as usize,
                    pos.col as usize,
                    piece.color == Color::Red,
                ) as f64;
                (pt.value() as f64, pst_score)
            } else {
                (0.0, 0.0)
            };

            // 总是：红方加分，黑方减分
            if piece.color == Color::Red {
                raw_score += value + pst;
            } else {
                raw_score -= value + pst;
            }
        }

        // 吃子潜力（capture gain）
        // 红方吃黑方的子 → 被吃的暗子用 black_hidden_ev
        // 黑方吃红方的子 → 被吃的暗子用 red_hidden_ev
        let capture_weight = 0.3;
        let red_capture = self.best_capture_value(board, Color::Red, black_hidden_ev);
        let black_capture = self.best_capture_value(board, Color::Black, red_hidden_ev);
        raw_score += capture_weight * (red_capture - black_capture);

        // 最后根据视角翻转符号
        if color == Color::Red {
            raw_score
        } else {
            -raw_score
        }
    }

    /// 计算某方最佳吃子价值
    /// - attacker: 进攻方（谁在吃子）
    /// - victim_hidden_ev: 被吃方暗子的期望价值（attacker 吃的是对方的子）
    fn best_capture_value(&self, board: &Board, attacker: Color, victim_hidden_ev: f64) -> f64 {
        let moves = board.get_legal_moves(attacker);
        let mut best_gain: f64 = 0.0;

        for mv in &moves {
            if let Some(victim) = board.get_piece(mv.to_pos) {
                // 被吃子的价值
                let victim_value = if victim.is_hidden {
                    victim_hidden_ev
                } else {
                    victim.actual_type.map_or(0.0, |pt| pt.value() as f64)
                };

                // 排除吃 King（吃 King = 游戏结束，不应计入吃子潜力）
                if victim.actual_type == Some(PieceType::King) {
                    continue;
                }

                if victim_value > best_gain {
                    best_gain = victim_value;
                }
            }
        }

        best_gain
    }

    /// 终局评估
    /// ply: 从根节点开始的步数（半回合数），用于 Mate Distance Bonus
    fn terminal_eval(&self, board: &Board, color: Color, ply: i32) -> f64 {
        let result = board.get_game_result(None);
        let ply_bonus = (ply * PLY_PENALTY) as f64;

        match result {
            GameResult::RedWin => {
                if color == Color::Red {
                    // 赢得越快分数越高（ply 小 → 扣分少 → 分数高）
                    MATE_SCORE - ply_bonus
                } else {
                    // 输得越慢分数越高（负数越接近 0）
                    -MATE_SCORE + ply_bonus
                }
            }
            GameResult::BlackWin => {
                if color == Color::Black {
                    MATE_SCORE - ply_bonus
                } else {
                    -MATE_SCORE + ply_bonus
                }
            }
            GameResult::Draw => 0.0,
            GameResult::Ongoing => self.evaluate(board, color),
        }
    }

    /// Expectimax 搜索（Negamax 风格）
    fn expectimax(&self, board: &mut Board, ctx: SearchContext) -> f64 {
        // 节点计数
        NODE_COUNT.fetch_add(1, AtomicOrdering::Relaxed);

        let current_color = board.current_turn();
        let legal_moves = board.get_legal_moves(current_color);

        // 终止条件
        if ctx.depth <= 0 || legal_moves.is_empty() {
            return self.terminal_eval(board, current_color, ctx.ply);
        }

        let mut max_eval = f64::NEG_INFINITY;
        let mut alpha = ctx.alpha;

        for mv in &legal_moves {
            let eval = if mv.action_type == ActionType::RevealAndMove {
                // 揭子走法：进入 Chance 节点
                self.chance_node(board, mv, ctx, current_color)
            } else {
                // 普通走法：直接递归
                self.apply_move_and_recurse(board, mv, ctx)
            };

            max_eval = max_eval.max(eval);
            alpha = alpha.max(eval);

            if alpha >= ctx.beta {
                break; // Beta 剪枝
            }
        }

        max_eval
    }

    /// Chance 节点：处理揭子走法的概率
    fn chance_node(
        &self,
        board: &mut Board,
        mv: &JieqiMove,
        ctx: SearchContext,
        color: Color,
    ) -> f64 {
        // 计算揭子方的剩余暗子分布
        let distribution = HiddenPieceDistribution::from_board(board, color);
        let possible_types = distribution.possible_types();

        if possible_types.is_empty() {
            // 理论上不应该发生，作为 fallback 直接递归
            return self.apply_move_and_recurse(board, mv, ctx);
        }

        let mut expected_value = 0.0;
        let next_ctx = ctx.next_ply();

        for (piece_type, probability) in possible_types {
            // 1. 模拟揭成该类型
            let reveal_state = board.simulate_reveal(mv.from_pos, piece_type);

            // 2. 执行走棋
            let was_hidden = reveal_state.is_some();
            let captured = board.make_move(mv);

            // 3. 递归搜索（对手视角）
            let child_value = -self.expectimax(board, next_ctx);

            // 4. 撤销走棋
            board.undo_move(mv, captured, was_hidden);

            // 5. 恢复揭子模拟
            if let Some(state) = reveal_state {
                board.restore_simulated_reveal(mv.from_pos, state);
            }

            // 6. 累加期望值
            expected_value += probability * child_value;
        }

        expected_value
    }

    /// 普通走法的应用和递归
    fn apply_move_and_recurse(
        &self,
        board: &mut Board,
        mv: &JieqiMove,
        ctx: SearchContext,
    ) -> f64 {
        let was_hidden = board.get_piece(mv.from_pos).map_or(false, |p| p.is_hidden);
        let captured = board.make_move(mv);

        // next_ply: depth-1, ply+1, 窗口翻转
        let value = -self.expectimax(board, ctx.next_ply());

        board.undo_move(mv, captured, was_hidden);

        value
    }

    /// 迭代加深搜索
    fn iterative_deepening(&self, board: &Board) -> Vec<(JieqiMove, f64)> {
        let moves = board.get_legal_moves(board.current_turn());
        if moves.is_empty() {
            return Vec::new();
        }

        let mut best_moves: Vec<(JieqiMove, f64)> = moves.iter().map(|&mv| (mv, 0.0)).collect();
        let start_time = Instant::now();

        // 从深度 1 开始迭代
        for depth in 1..=self.max_depth {
            // 检查时间限制
            if let Some(limit) = self.time_limit {
                if start_time.elapsed() >= limit {
                    break;
                }
            }

            // 记录达到的深度
            DEPTH_REACHED.store(depth, AtomicOrdering::Relaxed);

            let mut current_scores: Vec<(JieqiMove, f64)> = Vec::new();

            for &mv in &moves {
                // 每个走法也检查时间限制
                if let Some(limit) = self.time_limit {
                    if start_time.elapsed() >= limit {
                        break;
                    }
                }

                let mut board_copy = board.clone();

                // 揭子走法使用 Chance 节点
                let root_ctx = SearchContext::new(depth as i32);
                let score = if mv.action_type == ActionType::RevealAndMove {
                    self.chance_node(&mut board_copy, &mv, root_ctx, board.current_turn())
                } else {
                    board_copy.make_move(&mv);
                    // 走了一步后进入下一层
                    -self.expectimax(&mut board_copy, root_ctx.next_ply())
                };

                current_scores.push((mv, score));
            }

            // 只有完成整个深度的搜索才更新 best_moves
            if current_scores.len() == moves.len() {
                // 按分数排序
                current_scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(CmpOrdering::Equal));
                best_moves = current_scores;
            }
        }

        best_moves
    }
}

impl AIStrategy for IT2AI {
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove> {
        let mut rng = self.rng.clone();
        let results = self.iterative_deepening(board);

        let mut scored: Vec<ScoredMove> = results
            .into_iter()
            .map(|(mv, score)| {
                let noise = if self.randomness > 0.0 {
                    rng.gen::<f64>() * self.randomness * 100.0
                } else {
                    0.0
                };
                ScoredMove {
                    mv,
                    score: score + noise,
                }
            })
            .collect();

        sort_and_truncate(&mut scored, n);
        scored
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hidden_piece_distribution() {
        // 揭棋初始局面：将帅已揭，其他暗子
        let fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";
        let board = Board::from_fen(fen).unwrap();

        let dist = HiddenPieceDistribution::from_board(&board, Color::Red);
        assert_eq!(dist.total, 15); // 15 个暗子（将已揭）

        let possible = dist.possible_types();
        assert_eq!(possible.len(), 6); // 6 种可能（不含将）

        // 验证概率
        let total_prob: f64 = possible.iter().map(|(_, p)| p).sum();
        assert!((total_prob - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_expected_value() {
        // 揭棋初始局面
        let fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";
        let board = Board::from_fen(fen).unwrap();

        let dist = HiddenPieceDistribution::from_board(&board, Color::Red);
        let ev = dist.expected_value();

        // 期望价值（车炮原价，其他7折）
        // Advisor: 2*140 + Elephant: 2*140 + Horse: 2*280 + Rook: 2*900 + Cannon: 2*450 + Pawn: 5*70
        // = 280 + 280 + 560 + 1800 + 900 + 350 = 4170
        // 4170 / 15 = 278
        assert_eq!(ev, 278);
    }

    #[test]
    fn test_it2_basic() {
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig {
            depth: 2,
            ..Default::default()
        };
        let ai = IT2AI::new(&config);
        let board = Board::from_fen(fen).unwrap();
        let moves = ai.select_moves(&board, 5);

        assert!(!moves.is_empty());
        // 最佳走法应该是吃炮
        assert_eq!(moves[0].mv.to_fen_str(None), "e4e5");
    }
}
