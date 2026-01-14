//! AI 策略模块
//!
//! 提供多种 AI 策略实现，包括随机、贪婪、Minimax 等

use crate::board::Board;
use crate::types::{ActionType, Color, GameResult, JieqiMove, PieceType, Position, HIDDEN_PIECE_VALUE};
use rand::prelude::*;
use std::cmp::Ordering;

/// AI 配置
#[derive(Debug, Clone)]
pub struct AIConfig {
    /// 搜索深度
    pub depth: u32,
    /// 随机性（0.0-1.0）
    pub randomness: f64,
    /// 随机种子
    pub seed: Option<u64>,
}

impl Default for AIConfig {
    fn default() -> Self {
        AIConfig {
            depth: 3,
            randomness: 0.0,
            seed: None,
        }
    }
}

/// 走法评分
#[derive(Debug, Clone)]
pub struct ScoredMove {
    pub mv: JieqiMove,
    pub score: f64,
}

/// AI 策略接口
pub trait AIStrategy {
    /// 选择走法（返回带评分的走法列表）
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove>;

    /// 选择最佳走法
    fn select_best_move(&self, board: &Board) -> Option<JieqiMove> {
        self.select_moves(board, 1).first().map(|sm| sm.mv)
    }
}

// ============================================================================
// 随机策略
// ============================================================================

/// 随机 AI - 随机选择合法走法
pub struct RandomAI {
    rng: StdRng,
}

impl RandomAI {
    pub fn new(seed: Option<u64>) -> Self {
        let rng = match seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        RandomAI { rng }
    }
}

impl AIStrategy for RandomAI {
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove> {
        let moves = board.get_legal_moves(board.current_turn());
        let mut rng = self.rng.clone();

        let mut scored: Vec<ScoredMove> = moves
            .into_iter()
            .map(|mv| ScoredMove {
                mv,
                score: rng.gen::<f64>(),
            })
            .collect();

        scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        scored.truncate(n);
        scored
    }
}

// ============================================================================
// 贪婪策略
// ============================================================================

/// 贪婪 AI - 优先吃子和安全走法
pub struct GreedyAI {
    rng: StdRng,
    randomness: f64,
}

impl GreedyAI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        GreedyAI {
            rng,
            randomness: config.randomness,
        }
    }

    /// 评估单个走法
    fn evaluate_move(&self, board: &Board, mv: &JieqiMove) -> f64 {
        let mut score = 0.0;
        let color = board.current_turn();

        // 检查是否吃子
        if let Some(target) = board.get_piece(mv.to_pos) {
            if target.color != color {
                // 吃子得分：被吃子的价值
                let target_value = if target.is_hidden {
                    HIDDEN_PIECE_VALUE as f64
                } else {
                    target.actual_type.map_or(0.0, |pt| pt.value() as f64)
                };
                score += target_value;

                // MVV-LVA: 用低价值棋子吃高价值棋子更好
                if let Some(attacker) = board.get_piece(mv.from_pos) {
                    let attacker_value = if attacker.is_hidden {
                        HIDDEN_PIECE_VALUE as f64
                    } else {
                        attacker.actual_type.map_or(0.0, |pt| pt.value() as f64)
                    };
                    score += (target_value - attacker_value) * 0.1;
                }
            }
        }

        // 揭子奖励
        if mv.action_type == ActionType::RevealAndMove {
            score += 50.0; // 适度的揭子奖励
        }

        // 位置奖励：控制中心
        let center_bonus = 10.0 - (4.0 - mv.to_pos.col as f64).abs() * 2.0;
        score += center_bonus;

        // 前进奖励（兵卒）
        if let Some(piece) = board.get_piece(mv.from_pos) {
            if piece.get_movement_type() == PieceType::Pawn {
                let forward = if color == Color::Red { 1.0 } else { -1.0 };
                let progress = (mv.to_pos.row - mv.from_pos.row) as f64 * forward;
                score += progress * 20.0;
            }
        }

        score
    }
}

impl AIStrategy for GreedyAI {
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove> {
        let moves = board.get_legal_moves(board.current_turn());
        let mut rng = self.rng.clone();

        let mut scored: Vec<ScoredMove> = moves
            .into_iter()
            .map(|mv| {
                let base_score = self.evaluate_move(board, &mv);
                let noise = if self.randomness > 0.0 {
                    rng.gen::<f64>() * self.randomness * 100.0
                } else {
                    0.0
                };
                ScoredMove {
                    mv,
                    score: base_score + noise,
                }
            })
            .collect();

        scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        scored.truncate(n);
        scored
    }
}

// ============================================================================
// Minimax 策略
// ============================================================================

/// Minimax AI - 使用 Alpha-Beta 剪枝
pub struct MinimaxAI {
    depth: u32,
    rng: StdRng,
    randomness: f64,
}

impl MinimaxAI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        MinimaxAI {
            depth: config.depth,
            rng,
            randomness: config.randomness,
        }
    }

    /// 评估局面
    fn evaluate_position(&self, board: &Board, color: Color) -> f64 {
        let mut score = 0.0;

        // 棋子价值
        for piece in board.get_all_pieces(None) {
            let value = if piece.is_hidden {
                HIDDEN_PIECE_VALUE as f64
            } else {
                piece.actual_type.map_or(0.0, |pt| pt.value() as f64)
            };

            if piece.color == color {
                score += value;
            } else {
                score -= value;
            }
        }

        // 位置奖励
        for piece in board.get_all_pieces(Some(color)) {
            // 中心控制
            let center_bonus = 5.0 - (4.0 - piece.position.col as f64).abs();
            score += center_bonus;

            // 前进奖励（兵）
            if piece.get_movement_type() == PieceType::Pawn {
                let progress = if color == Color::Red {
                    piece.position.row as f64
                } else {
                    (9 - piece.position.row) as f64
                };
                score += progress * 5.0;
            }
        }

        score
    }

    /// Negamax 搜索（带 Alpha-Beta 剪枝）
    ///
    /// 从当前玩家视角返回评估值（正值表示当前玩家有利）
    fn negamax(
        &self,
        board: &mut Board,
        depth: u32,
        mut alpha: f64,
        beta: f64,
    ) -> f64 {
        let current_color = board.current_turn();
        let legal_moves = board.get_legal_moves(current_color);

        // 终止条件
        if depth == 0 || legal_moves.is_empty() {
            let result = board.get_game_result(Some(&legal_moves));
            return match result {
                GameResult::RedWin => {
                    if current_color == Color::Red {
                        100000.0
                    } else {
                        -100000.0
                    }
                }
                GameResult::BlackWin => {
                    if current_color == Color::Black {
                        100000.0
                    } else {
                        -100000.0
                    }
                }
                GameResult::Draw => 0.0,
                GameResult::Ongoing => self.evaluate_position(board, current_color),
            };
        }

        let mut max_eval = f64::NEG_INFINITY;
        for mv in legal_moves {
            let was_hidden = board.get_piece(mv.from_pos).map_or(false, |p| p.is_hidden);
            let captured = board.make_move(&mv);

            // 递归调用，取负值（因为对手视角相反）
            let eval = -self.negamax(board, depth - 1, -beta, -alpha);

            board.undo_move(&mv, captured, was_hidden);

            max_eval = max_eval.max(eval);
            alpha = alpha.max(eval);
            if alpha >= beta {
                break; // Beta 剪枝
            }
        }
        max_eval
    }
}

impl AIStrategy for MinimaxAI {
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove> {
        let color = board.current_turn();
        let moves = board.get_legal_moves(color);
        let mut rng = self.rng.clone();

        let mut scored: Vec<ScoredMove> = moves
            .into_iter()
            .map(|mv| {
                let mut board_copy = board.clone();
                board_copy.make_move(&mv);

                // 使用 negamax 搜索：从对手视角取负值
                let base_score = -self.negamax(
                    &mut board_copy,
                    self.depth - 1,
                    f64::NEG_INFINITY,
                    f64::INFINITY,
                );

                let noise = if self.randomness > 0.0 {
                    rng.gen::<f64>() * self.randomness * 100.0
                } else {
                    0.0
                };

                ScoredMove {
                    mv,
                    score: base_score + noise,
                }
            })
            .collect();

        scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        scored.truncate(n);
        scored
    }
}

// ============================================================================
// Iterative Deepening 策略
// ============================================================================

/// Iterative Deepening AI - 迭代加深搜索
///
/// 从深度 1 开始逐步加深搜索，可以在任何时候停止并返回当前最佳结果
pub struct IterativeDeepeningAI {
    max_depth: u32,
    rng: StdRng,
    randomness: f64,
}

impl IterativeDeepeningAI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        IterativeDeepeningAI {
            max_depth: config.depth,
            rng,
            randomness: config.randomness,
        }
    }

    /// 评估局面
    fn evaluate_position(&self, board: &Board, color: Color) -> f64 {
        let mut score = 0.0;

        // 棋子价值
        for piece in board.get_all_pieces(None) {
            let value = if piece.is_hidden {
                HIDDEN_PIECE_VALUE as f64
            } else {
                piece.actual_type.map_or(0.0, |pt| pt.value() as f64)
            };

            if piece.color == color {
                score += value;
            } else {
                score -= value;
            }
        }

        // 位置奖励
        for piece in board.get_all_pieces(Some(color)) {
            // 中心控制
            let center_bonus = 5.0 - (4.0 - piece.position.col as f64).abs();
            score += center_bonus;

            // 前进奖励（兵）
            if piece.get_movement_type() == PieceType::Pawn {
                let progress = if color == Color::Red {
                    piece.position.row as f64
                } else {
                    (9 - piece.position.row) as f64
                };
                score += progress * 5.0;
            }

            // 活跃度奖励（车、炮、马）
            match piece.get_movement_type() {
                PieceType::Rook | PieceType::Cannon | PieceType::Horse => {
                    // 中心位置的大子更有活力
                    let activity = 3.0 - (4.5 - piece.position.row as f64).abs() * 0.5;
                    score += activity;
                }
                _ => {}
            }
        }

        score
    }

    /// Negamax 搜索
    fn negamax(&self, board: &mut Board, depth: u32, mut alpha: f64, beta: f64) -> f64 {
        let current_color = board.current_turn();
        let legal_moves = board.get_legal_moves(current_color);

        if depth == 0 || legal_moves.is_empty() {
            let result = board.get_game_result(Some(&legal_moves));
            return match result {
                GameResult::RedWin => {
                    if current_color == Color::Red {
                        100000.0 + depth as f64
                    } else {
                        -100000.0 - depth as f64
                    }
                }
                GameResult::BlackWin => {
                    if current_color == Color::Black {
                        100000.0 + depth as f64
                    } else {
                        -100000.0 - depth as f64
                    }
                }
                GameResult::Draw => 0.0,
                GameResult::Ongoing => self.evaluate_position(board, current_color),
            };
        }

        let mut max_eval = f64::NEG_INFINITY;
        for mv in legal_moves {
            let was_hidden = board.get_piece(mv.from_pos).map_or(false, |p| p.is_hidden);
            let captured = board.make_move(&mv);

            let eval = -self.negamax(board, depth - 1, -beta, -alpha);

            board.undo_move(&mv, captured, was_hidden);

            max_eval = max_eval.max(eval);
            alpha = alpha.max(eval);
            if alpha >= beta {
                break;
            }
        }
        max_eval
    }

    /// 迭代加深搜索
    fn iterative_deepening(&self, board: &Board) -> Vec<(JieqiMove, f64)> {
        let moves = board.get_legal_moves(board.current_turn());
        if moves.is_empty() {
            return Vec::new();
        }

        let mut best_moves: Vec<(JieqiMove, f64)> = moves.iter().map(|&mv| (mv, 0.0)).collect();

        // 从深度 1 开始迭代
        for depth in 1..=self.max_depth {
            let mut current_scores: Vec<(JieqiMove, f64)> = Vec::new();

            for &mv in &moves {
                let mut board_copy = board.clone();
                board_copy.make_move(&mv);

                let score = -self.negamax(&mut board_copy, depth - 1, f64::NEG_INFINITY, f64::INFINITY);

                current_scores.push((mv, score));
            }

            // 按分数排序
            current_scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(Ordering::Equal));
            best_moves = current_scores;
        }

        best_moves
    }
}

impl AIStrategy for IterativeDeepeningAI {
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

        scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        scored.truncate(n);
        scored
    }
}

// ============================================================================
// MCTS 策略
// ============================================================================

use std::collections::HashMap;

/// MCTS AI - Monte Carlo Tree Search (简化版)
///
/// 使用简化的 flat Monte Carlo 搜索，避免复杂的树结构
pub struct MCTSAI {
    iterations: u32,
    rng: StdRng,
}

impl MCTSAI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        MCTSAI {
            iterations: config.depth * 500, // depth * 500 simulations per move
            rng,
        }
    }

    /// 模拟（随机走棋直到游戏结束或达到最大步数）
    fn simulate(&self, board: &mut Board, rng: &mut StdRng, max_moves: u32) -> f64 {
        let start_color = board.current_turn();
        let mut moves_played = 0;

        loop {
            let legal_moves = board.get_legal_moves(board.current_turn());
            let result = board.get_game_result(Some(&legal_moves));

            match result {
                GameResult::RedWin => {
                    return if start_color == Color::Red { 1.0 } else { 0.0 };
                }
                GameResult::BlackWin => {
                    return if start_color == Color::Black { 1.0 } else { 0.0 };
                }
                GameResult::Draw => return 0.5,
                GameResult::Ongoing => {}
            }

            if moves_played >= max_moves || legal_moves.is_empty() {
                return self.quick_evaluate(board, start_color);
            }

            // 随机选择走法
            let mv = legal_moves[rng.gen_range(0..legal_moves.len())];
            board.make_move(&mv);
            moves_played += 1;
        }
    }

    /// 快速评估局面
    fn quick_evaluate(&self, board: &Board, color: Color) -> f64 {
        let mut my_material = 0.0;
        let mut opp_material = 0.0;

        for piece in board.get_all_pieces(None) {
            let value = if piece.is_hidden {
                HIDDEN_PIECE_VALUE as f64
            } else {
                piece.actual_type.map_or(0.0, |pt| pt.value() as f64)
            };

            if piece.color == color {
                my_material += value;
            } else {
                opp_material += value;
            }
        }

        let total = my_material + opp_material;
        if total == 0.0 {
            0.5
        } else {
            my_material / total
        }
    }

    /// 运行 Monte Carlo 搜索
    fn run_mcts(&self, board: &Board) -> Vec<(JieqiMove, f64)> {
        let legal_moves = board.get_legal_moves(board.current_turn());
        if legal_moves.is_empty() {
            return Vec::new();
        }

        let mut rng = self.rng.clone();
        let mut move_stats: HashMap<JieqiMove, (u32, f64)> = HashMap::new();

        // 对每个走法进行模拟
        for mv in &legal_moves {
            move_stats.insert(*mv, (0, 0.0));
        }

        // 均匀分配模拟次数给每个走法
        let sims_per_move = (self.iterations / legal_moves.len() as u32).max(1);

        for mv in &legal_moves {
            for _ in 0..sims_per_move {
                let mut sim_board = board.clone();
                sim_board.make_move(mv);

                // 从对手视角模拟
                let result = self.simulate(&mut sim_board, &mut rng, 30);
                // 转换为我方视角（1 - result 因为是对手走完后的结果）
                let my_result = 1.0 - result;

                if let Some(stats) = move_stats.get_mut(mv) {
                    stats.0 += 1;
                    stats.1 += my_result;
                }
            }
        }

        // 计算每个走法的平均得分
        let mut results: Vec<(JieqiMove, f64)> = move_stats
            .into_iter()
            .map(|(mv, (visits, wins))| {
                let score = if visits > 0 {
                    wins / visits as f64
                } else {
                    0.0
                };
                (mv, score)
            })
            .collect();

        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(Ordering::Equal));
        results
    }
}

impl AIStrategy for MCTSAI {
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove> {
        let results = self.run_mcts(board);

        let scored: Vec<ScoredMove> = results
            .into_iter()
            .take(n)
            .map(|(mv, score)| ScoredMove {
                mv,
                score: score * 100.0,
            })
            .collect();

        scored
    }
}

// ============================================================================
// Position-Aware 策略
// ============================================================================

/// Position-Aware AI - 增强位置评估
pub struct PositionalAI {
    depth: u32,
    rng: StdRng,
    randomness: f64,
}

impl PositionalAI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        PositionalAI {
            depth: config.depth,
            rng,
            randomness: config.randomness,
        }
    }

    /// 详细的位置评估
    fn evaluate_position(&self, board: &Board, color: Color) -> f64 {
        let mut score = 0.0;

        // 1. 棋子价值
        for piece in board.get_all_pieces(None) {
            let base_value = if piece.is_hidden {
                HIDDEN_PIECE_VALUE as f64
            } else {
                piece.actual_type.map_or(0.0, |pt| pt.value() as f64)
            };

            // 位置加成表
            let position_bonus = self.get_position_bonus(piece, board);

            let total_value = base_value + position_bonus;

            if piece.color == color {
                score += total_value;
            } else {
                score -= total_value;
            }
        }

        // 2. 王安全评估
        score += self.evaluate_king_safety(board, color);
        score -= self.evaluate_king_safety(board, color.opposite());

        // 3. 机动性评估
        let my_mobility = board.get_legal_moves(color).len() as f64;
        score += my_mobility * 2.0;

        score
    }

    /// 获取位置加成
    fn get_position_bonus(&self, piece: &crate::board::Piece, _board: &Board) -> f64 {
        let pos = piece.position;
        let is_red = piece.color == Color::Red;
        let row = if is_red { pos.row } else { 9 - pos.row } as f64;
        let col = pos.col as f64;

        match piece.get_movement_type() {
            PieceType::King => {
                // 王在中心位置稍微好一点
                let center_dist = (col - 4.0).abs();
                -center_dist * 5.0
            }
            PieceType::Rook => {
                // 车在中间列最好，过河后更好
                let column_bonus = 10.0 - (col - 4.0).abs() * 2.0;
                let cross_river_bonus = if row >= 5.0 { 20.0 } else { 0.0 };
                column_bonus + cross_river_bonus
            }
            PieceType::Cannon => {
                // 炮在中间位置好，但不要太靠前
                let column_bonus = 8.0 - (col - 4.0).abs() * 1.5;
                let row_bonus = if (2.0..=7.0).contains(&row) { 10.0 } else { 0.0 };
                column_bonus + row_bonus
            }
            PieceType::Horse => {
                // 马在中心位置好
                let center_bonus = 15.0 - (col - 4.0).abs() * 2.0 - (row - 4.5).abs() * 1.5;
                center_bonus.max(0.0)
            }
            PieceType::Elephant => {
                // 象守住象位最好
                if (col == 2.0 || col == 6.0) && row <= 4.0 {
                    10.0
                } else {
                    0.0
                }
            }
            PieceType::Advisor => {
                // 士守住九宫最好
                if col == 4.0 && row == 1.0 {
                    15.0 // 花心士
                } else {
                    5.0
                }
            }
            PieceType::Pawn => {
                // 兵越过河越好，中路兵更有价值
                let cross_river = row >= 5.0;
                let center_bonus = 10.0 - (col - 4.0).abs() * 2.0;
                let advance_bonus = row * 5.0;
                let total = if cross_river {
                    center_bonus + advance_bonus + 30.0
                } else {
                    advance_bonus
                };
                total
            }
        }
    }

    /// 评估王安全
    fn evaluate_king_safety(&self, board: &Board, color: Color) -> f64 {
        let mut safety = 0.0;

        // 检查王周围的防守棋子
        if let Some(king_pos) = board.find_king(color) {
            let defenders = self.count_defenders_near_king(board, king_pos, color);
            safety += defenders as f64 * 10.0;

            // 检查是否被将军
            if board.is_in_check(color) {
                safety -= 50.0;
            }
        }

        safety
    }

    /// 统计王周围的防守棋子数量
    fn count_defenders_near_king(&self, board: &Board, king_pos: Position, color: Color) -> i32 {
        let mut count = 0;
        for piece in board.get_all_pieces(Some(color)) {
            let dist = (piece.position.row - king_pos.row).abs()
                + (piece.position.col - king_pos.col).abs();
            if dist <= 2 && piece.get_movement_type() != PieceType::King {
                count += 1;
            }
        }
        count
    }

    /// Negamax 搜索
    fn negamax(&self, board: &mut Board, depth: u32, mut alpha: f64, beta: f64) -> f64 {
        let current_color = board.current_turn();
        let legal_moves = board.get_legal_moves(current_color);

        if depth == 0 || legal_moves.is_empty() {
            let result = board.get_game_result(Some(&legal_moves));
            return match result {
                GameResult::RedWin => {
                    if current_color == Color::Red {
                        100000.0 + depth as f64
                    } else {
                        -100000.0 - depth as f64
                    }
                }
                GameResult::BlackWin => {
                    if current_color == Color::Black {
                        100000.0 + depth as f64
                    } else {
                        -100000.0 - depth as f64
                    }
                }
                GameResult::Draw => 0.0,
                GameResult::Ongoing => self.evaluate_position(board, current_color),
            };
        }

        let mut max_eval = f64::NEG_INFINITY;
        for mv in legal_moves {
            let was_hidden = board.get_piece(mv.from_pos).map_or(false, |p| p.is_hidden);
            let captured = board.make_move(&mv);

            let eval = -self.negamax(board, depth - 1, -beta, -alpha);

            board.undo_move(&mv, captured, was_hidden);

            max_eval = max_eval.max(eval);
            alpha = alpha.max(eval);
            if alpha >= beta {
                break;
            }
        }
        max_eval
    }
}

impl AIStrategy for PositionalAI {
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove> {
        let moves = board.get_legal_moves(board.current_turn());
        let mut rng = self.rng.clone();

        let mut scored: Vec<ScoredMove> = moves
            .into_iter()
            .map(|mv| {
                let mut board_copy = board.clone();
                board_copy.make_move(&mv);

                let base_score =
                    -self.negamax(&mut board_copy, self.depth - 1, f64::NEG_INFINITY, f64::INFINITY);

                let noise = if self.randomness > 0.0 {
                    rng.gen::<f64>() * self.randomness * 100.0
                } else {
                    0.0
                };

                ScoredMove {
                    mv,
                    score: base_score + noise,
                }
            })
            .collect();

        scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        scored.truncate(n);
        scored
    }
}

// ============================================================================
// Defensive 策略
// ============================================================================

/// Defensive AI - 防守型策略
pub struct DefensiveAI {
    depth: u32,
    rng: StdRng,
    randomness: f64,
}

impl DefensiveAI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        DefensiveAI {
            depth: config.depth,
            rng,
            randomness: config.randomness,
        }
    }

    /// 防守型评估
    fn evaluate_position(&self, board: &Board, color: Color) -> f64 {
        let mut score = 0.0;

        // 棋子价值（防守型更看重己方棋子）
        for piece in board.get_all_pieces(None) {
            let value = if piece.is_hidden {
                HIDDEN_PIECE_VALUE as f64
            } else {
                piece.actual_type.map_or(0.0, |pt| pt.value() as f64)
            };

            if piece.color == color {
                score += value * 1.2; // 己方棋子价值加成
            } else {
                score -= value;
            }
        }

        // 王安全是最重要的
        if let Some(king_pos) = board.find_king(color) {
            // 检查王周围的防守
            let defenders = self.count_defenders(board, king_pos, color);
            score += defenders as f64 * 20.0;

            // 惩罚被将军状态
            if board.is_in_check(color) {
                score -= 100.0;
            }
        }

        // 防守棋子位置奖励
        for piece in board.get_all_pieces(Some(color)) {
            let is_defending = self.is_defending_king(board, piece, color);
            if is_defending {
                score += 15.0;
            }
        }

        score
    }

    fn count_defenders(&self, board: &Board, king_pos: Position, color: Color) -> i32 {
        let mut count = 0;
        for piece in board.get_all_pieces(Some(color)) {
            let dist = (piece.position.row - king_pos.row).abs()
                + (piece.position.col - king_pos.col).abs();
            if dist <= 3 && piece.get_movement_type() != PieceType::King {
                count += 1;
            }
        }
        count
    }

    fn is_defending_king(&self, board: &Board, piece: &crate::board::Piece, color: Color) -> bool {
        if let Some(king_pos) = board.find_king(color) {
            let dist = (piece.position.row - king_pos.row).abs()
                + (piece.position.col - king_pos.col).abs();
            dist <= 2
        } else {
            false
        }
    }

    fn negamax(&self, board: &mut Board, depth: u32, mut alpha: f64, beta: f64) -> f64 {
        let current_color = board.current_turn();
        let legal_moves = board.get_legal_moves(current_color);

        if depth == 0 || legal_moves.is_empty() {
            let result = board.get_game_result(Some(&legal_moves));
            return match result {
                GameResult::RedWin => {
                    if current_color == Color::Red { 100000.0 } else { -100000.0 }
                }
                GameResult::BlackWin => {
                    if current_color == Color::Black { 100000.0 } else { -100000.0 }
                }
                GameResult::Draw => 0.0,
                GameResult::Ongoing => self.evaluate_position(board, current_color),
            };
        }

        let mut max_eval = f64::NEG_INFINITY;
        for mv in legal_moves {
            let was_hidden = board.get_piece(mv.from_pos).map_or(false, |p| p.is_hidden);
            let captured = board.make_move(&mv);
            let eval = -self.negamax(board, depth - 1, -beta, -alpha);
            board.undo_move(&mv, captured, was_hidden);

            max_eval = max_eval.max(eval);
            alpha = alpha.max(eval);
            if alpha >= beta {
                break;
            }
        }
        max_eval
    }
}

impl AIStrategy for DefensiveAI {
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove> {
        let moves = board.get_legal_moves(board.current_turn());
        let mut rng = self.rng.clone();

        let mut scored: Vec<ScoredMove> = moves
            .into_iter()
            .map(|mv| {
                let mut board_copy = board.clone();
                board_copy.make_move(&mv);

                let base_score =
                    -self.negamax(&mut board_copy, self.depth - 1, f64::NEG_INFINITY, f64::INFINITY);

                let noise = if self.randomness > 0.0 {
                    rng.gen::<f64>() * self.randomness * 100.0
                } else {
                    0.0
                };

                ScoredMove { mv, score: base_score + noise }
            })
            .collect();

        scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        scored.truncate(n);
        scored
    }
}

// ============================================================================
// Aggressive 策略
// ============================================================================

/// Aggressive AI - 进攻型策略
pub struct AggressiveAI {
    depth: u32,
    rng: StdRng,
    randomness: f64,
}

impl AggressiveAI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        AggressiveAI {
            depth: config.depth,
            rng,
            randomness: config.randomness,
        }
    }

    /// 进攻型评估
    fn evaluate_position(&self, board: &Board, color: Color) -> f64 {
        let mut score = 0.0;

        // 棋子价值（进攻型更看重对方棋子被吃）
        for piece in board.get_all_pieces(None) {
            let value = if piece.is_hidden {
                HIDDEN_PIECE_VALUE as f64
            } else {
                piece.actual_type.map_or(0.0, |pt| pt.value() as f64)
            };

            if piece.color == color {
                score += value;
            } else {
                score -= value * 1.2; // 对方棋子损失加成
            }
        }

        // 进攻位置奖励
        for piece in board.get_all_pieces(Some(color)) {
            let is_red = color == Color::Red;
            let row = piece.position.row;
            let cross_river = if is_red { row >= 5 } else { row <= 4 };

            if cross_river {
                score += 15.0; // 过河奖励
            }

            // 攻击型棋子前进奖励
            match piece.get_movement_type() {
                PieceType::Rook | PieceType::Cannon | PieceType::Horse => {
                    let advance = if is_red { row as f64 } else { (9 - row) as f64 };
                    score += advance * 3.0;
                }
                PieceType::Pawn => {
                    let advance = if is_red { row as f64 } else { (9 - row) as f64 };
                    score += advance * 5.0;
                }
                _ => {}
            }
        }

        // 对对方王的压力
        if let Some(enemy_king_pos) = board.find_king(color.opposite()) {
            let attackers = self.count_attackers(board, enemy_king_pos, color);
            score += attackers as f64 * 25.0;

            // 将军奖励
            if board.is_in_check(color.opposite()) {
                score += 50.0;
            }
        }

        score
    }

    fn count_attackers(&self, board: &Board, king_pos: Position, color: Color) -> i32 {
        let mut count = 0;
        for piece in board.get_all_pieces(Some(color)) {
            let dist = (piece.position.row - king_pos.row).abs()
                + (piece.position.col - king_pos.col).abs();
            if dist <= 4 {
                count += 1;
            }
        }
        count
    }

    fn negamax(&self, board: &mut Board, depth: u32, mut alpha: f64, beta: f64) -> f64 {
        let current_color = board.current_turn();
        let legal_moves = board.get_legal_moves(current_color);

        if depth == 0 || legal_moves.is_empty() {
            let result = board.get_game_result(Some(&legal_moves));
            return match result {
                GameResult::RedWin => {
                    if current_color == Color::Red { 100000.0 } else { -100000.0 }
                }
                GameResult::BlackWin => {
                    if current_color == Color::Black { 100000.0 } else { -100000.0 }
                }
                GameResult::Draw => -50.0, // 进攻型 AI 不喜欢和棋
                GameResult::Ongoing => self.evaluate_position(board, current_color),
            };
        }

        let mut max_eval = f64::NEG_INFINITY;
        for mv in legal_moves {
            let was_hidden = board.get_piece(mv.from_pos).map_or(false, |p| p.is_hidden);
            let captured = board.make_move(&mv);
            let eval = -self.negamax(board, depth - 1, -beta, -alpha);
            board.undo_move(&mv, captured, was_hidden);

            max_eval = max_eval.max(eval);
            alpha = alpha.max(eval);
            if alpha >= beta {
                break;
            }
        }
        max_eval
    }
}

impl AIStrategy for AggressiveAI {
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove> {
        let moves = board.get_legal_moves(board.current_turn());
        let mut rng = self.rng.clone();

        let mut scored: Vec<ScoredMove> = moves
            .into_iter()
            .map(|mv| {
                let mut board_copy = board.clone();
                board_copy.make_move(&mv);

                let base_score =
                    -self.negamax(&mut board_copy, self.depth - 1, f64::NEG_INFINITY, f64::INFINITY);

                let noise = if self.randomness > 0.0 {
                    rng.gen::<f64>() * self.randomness * 100.0
                } else {
                    0.0
                };

                ScoredMove { mv, score: base_score + noise }
            })
            .collect();

        scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        scored.truncate(n);
        scored
    }
}

// ============================================================================
// AI 引擎
// ============================================================================

/// AI 引擎 - 统一的 AI 接口
pub struct AIEngine {
    strategy: Box<dyn AIStrategy>,
}

impl AIEngine {
    /// 创建随机 AI
    pub fn random(seed: Option<u64>) -> Self {
        AIEngine {
            strategy: Box::new(RandomAI::new(seed)),
        }
    }

    /// 创建贪婪 AI
    pub fn greedy(config: &AIConfig) -> Self {
        AIEngine {
            strategy: Box::new(GreedyAI::new(config)),
        }
    }

    /// 创建 Minimax AI
    pub fn minimax(config: &AIConfig) -> Self {
        AIEngine {
            strategy: Box::new(MinimaxAI::new(config)),
        }
    }

    /// 创建迭代加深 AI
    pub fn iterative_deepening(config: &AIConfig) -> Self {
        AIEngine {
            strategy: Box::new(IterativeDeepeningAI::new(config)),
        }
    }

    /// 创建 MCTS AI
    pub fn mcts(config: &AIConfig) -> Self {
        AIEngine {
            strategy: Box::new(MCTSAI::new(config)),
        }
    }

    /// 创建位置评估 AI
    pub fn positional(config: &AIConfig) -> Self {
        AIEngine {
            strategy: Box::new(PositionalAI::new(config)),
        }
    }

    /// 创建防守型 AI
    pub fn defensive(config: &AIConfig) -> Self {
        AIEngine {
            strategy: Box::new(DefensiveAI::new(config)),
        }
    }

    /// 创建进攻型 AI
    pub fn aggressive(config: &AIConfig) -> Self {
        AIEngine {
            strategy: Box::new(AggressiveAI::new(config)),
        }
    }

    /// 从策略名称创建
    pub fn from_strategy(name: &str, config: &AIConfig) -> Result<Self, String> {
        match name.to_lowercase().as_str() {
            "random" => Ok(Self::random(config.seed)),
            "greedy" => Ok(Self::greedy(config)),
            "minimax" | "alphabeta" => Ok(Self::minimax(config)),
            "iterative" | "iterative_deepening" => Ok(Self::iterative_deepening(config)),
            "mcts" | "montecarlo" => Ok(Self::mcts(config)),
            "positional" | "position" => Ok(Self::positional(config)),
            "defensive" | "defense" => Ok(Self::defensive(config)),
            "aggressive" | "attack" => Ok(Self::aggressive(config)),
            _ => Err(format!("Unknown strategy: {}. Available: random, greedy, minimax, iterative, mcts, positional, defensive, aggressive", name)),
        }
    }

    /// 从 FEN 选择走法（返回带评分的走法字符串）
    pub fn select_moves_fen(&self, fen: &str, n: usize) -> Result<Vec<(String, f64)>, String> {
        let board = Board::from_fen(fen)?;
        let moves = self.strategy.select_moves(&board, n);
        Ok(moves
            .into_iter()
            .map(|sm| (sm.mv.to_fen_str(None), sm.score))
            .collect())
    }

    /// 从 FEN 选择最佳走法
    pub fn select_best_move_fen(&self, fen: &str) -> Result<Option<String>, String> {
        let board = Board::from_fen(fen)?;
        Ok(self
            .strategy
            .select_best_move(&board)
            .map(|m| m.to_fen_str(None)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_random_ai() {
        let fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r";
        let ai = AIEngine::random(Some(42));
        let moves = ai.select_moves_fen(fen, 5).unwrap();

        assert_eq!(moves.len(), 5);
    }

    #[test]
    fn test_greedy_ai() {
        let fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r";
        let config = AIConfig::default();
        let ai = AIEngine::greedy(&config);
        let moves = ai.select_moves_fen(fen, 5).unwrap();

        assert_eq!(moves.len(), 5);
    }

    #[test]
    fn test_minimax_ai() {
        let fen = "4k4/9/9/9/9/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig {
            depth: 2,
            ..Default::default()
        };
        let ai = AIEngine::minimax(&config);
        let best = ai.select_best_move_fen(fen).unwrap();

        assert!(best.is_some());
    }

    #[test]
    fn test_capture_preference() {
        // 红方车可以吃黑方炮
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig::default();
        let ai = AIEngine::greedy(&config);
        let best = ai.select_best_move_fen(fen).unwrap().unwrap();

        // 贪婪 AI 应该选择吃炮
        assert_eq!(best, "e4e5");
    }

    #[test]
    fn test_iterative_deepening_ai() {
        let fen = "4k4/9/9/9/9/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig {
            depth: 2,
            ..Default::default()
        };
        let ai = AIEngine::iterative_deepening(&config);
        let best = ai.select_best_move_fen(fen).unwrap();

        assert!(best.is_some());
    }

    #[test]
    fn test_mcts_ai() {
        let fen = "4k4/9/9/9/9/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig {
            depth: 1, // 1000 iterations
            seed: Some(42),
            ..Default::default()
        };
        let ai = AIEngine::mcts(&config);
        let best = ai.select_best_move_fen(fen).unwrap();

        assert!(best.is_some());
    }

    #[test]
    fn test_positional_ai() {
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig {
            depth: 2,
            ..Default::default()
        };
        let ai = AIEngine::positional(&config);
        let best = ai.select_best_move_fen(fen).unwrap().unwrap();

        // 位置评估 AI 也应该选择吃炮
        assert_eq!(best, "e4e5");
    }

    #[test]
    fn test_defensive_ai() {
        let fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r";
        let config = AIConfig {
            depth: 2,
            ..Default::default()
        };
        let ai = AIEngine::defensive(&config);
        let moves = ai.select_moves_fen(fen, 3).unwrap();

        assert_eq!(moves.len(), 3);
    }

    #[test]
    fn test_aggressive_ai() {
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig {
            depth: 2,
            ..Default::default()
        };
        let ai = AIEngine::aggressive(&config);
        let best = ai.select_best_move_fen(fen).unwrap().unwrap();

        // 进攻型 AI 也应该选择吃炮
        assert_eq!(best, "e4e5");
    }

    #[test]
    fn test_all_strategies_from_name() {
        let config = AIConfig::default();
        let strategies = vec![
            "random", "greedy", "minimax", "iterative",
            "mcts", "positional", "defensive", "aggressive",
        ];

        for name in strategies {
            let result = AIEngine::from_strategy(name, &config);
            assert!(result.is_ok(), "Failed to create strategy: {}", name);
        }
    }
}
