//! IT2 (Iterative Deepening v2) - Expectimax 概率处理
//!
//! 核心改进：揭子走法使用 Chance 节点处理概率

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

    /// 评估局面（子力 + 吃子潜力）
    fn evaluate(&self, board: &Board, color: Color) -> f64 {
        let mut score = 0.0;

        // 计算双方的暗子期望价值
        let my_ev = HiddenPieceDistribution::from_board(board, color).expected_value() as f64;
        let opp_ev =
            HiddenPieceDistribution::from_board(board, color.opposite()).expected_value() as f64;

        // 棋子价值
        for piece in board.get_all_pieces(None) {
            let value = if piece.is_hidden {
                // 使用动态期望价值
                if piece.color == color {
                    my_ev
                } else {
                    opp_ev
                }
            } else {
                piece.actual_type.map_or(0.0, |pt| pt.value() as f64)
            };

            if piece.color == color {
                score += value;
            } else {
                score -= value;
            }
        }

        // 吃子潜力（capture gain）
        let capture_weight = 0.3;
        let my_best_capture = self.best_capture_value(board, color, my_ev);
        let opp_best_capture = self.best_capture_value(board, color.opposite(), opp_ev);
        score += capture_weight * (my_best_capture - opp_best_capture);

        score
    }

    /// 计算某方最佳吃子价值
    fn best_capture_value(&self, board: &Board, color: Color, hidden_ev: f64) -> f64 {
        let moves = board.get_legal_moves(color);
        let mut best_gain: f64 = 0.0;

        for mv in &moves {
            if let Some(victim) = board.get_piece(mv.to_pos) {
                // 被吃子的价值
                let victim_value = if victim.is_hidden {
                    hidden_ev
                } else {
                    victim.actual_type.map_or(0.0, |pt| pt.value() as f64)
                };
                if victim_value > best_gain {
                    best_gain = victim_value;
                }
            }
        }

        best_gain
    }

    /// 终局评估
    fn terminal_eval(&self, board: &Board, color: Color) -> f64 {
        let result = board.get_game_result(None);
        match result {
            GameResult::RedWin => {
                if color == Color::Red {
                    100000.0
                } else {
                    -100000.0
                }
            }
            GameResult::BlackWin => {
                if color == Color::Black {
                    100000.0
                } else {
                    -100000.0
                }
            }
            GameResult::Draw => 0.0,
            GameResult::Ongoing => self.evaluate(board, color),
        }
    }

    /// Expectimax 搜索（Negamax 风格）
    fn expectimax(&self, board: &mut Board, depth: i32, mut alpha: f64, beta: f64) -> f64 {
        // 节点计数
        NODE_COUNT.fetch_add(1, AtomicOrdering::Relaxed);

        let current_color = board.current_turn();
        let legal_moves = board.get_legal_moves(current_color);

        // 终止条件
        if depth <= 0 || legal_moves.is_empty() {
            return self.terminal_eval(board, current_color);
        }

        let mut max_eval = f64::NEG_INFINITY;

        for mv in &legal_moves {
            let eval = if mv.action_type == ActionType::RevealAndMove {
                // 揭子走法：进入 Chance 节点
                self.chance_node(board, mv, depth, alpha, beta, current_color)
            } else {
                // 普通走法：直接递归
                self.apply_move_and_recurse(board, mv, depth, alpha, beta)
            };

            max_eval = max_eval.max(eval);
            alpha = alpha.max(eval);

            if alpha >= beta {
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
        depth: i32,
        alpha: f64,
        beta: f64,
        color: Color,
    ) -> f64 {
        // 计算揭子方的剩余暗子分布
        let distribution = HiddenPieceDistribution::from_board(board, color);
        let possible_types = distribution.possible_types();

        if possible_types.is_empty() {
            // 理论上不应该发生，作为 fallback 直接递归
            return self.apply_move_and_recurse(board, mv, depth, alpha, beta);
        }

        let mut expected_value = 0.0;

        for (piece_type, probability) in possible_types {
            // 1. 模拟揭成该类型
            let reveal_state = board.simulate_reveal(mv.from_pos, piece_type);

            // 2. 执行走棋
            let was_hidden = reveal_state.is_some();
            let captured = board.make_move(mv);

            // 3. 递归搜索（对手视角，取负值）
            let child_value = -self.expectimax(board, depth - 1, -beta, -alpha);

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
        depth: i32,
        alpha: f64,
        beta: f64,
    ) -> f64 {
        let was_hidden = board
            .get_piece(mv.from_pos)
            .map_or(false, |p| p.is_hidden);
        let captured = board.make_move(mv);

        let value = -self.expectimax(board, depth - 1, -beta, -alpha);

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
                let score = if mv.action_type == ActionType::RevealAndMove {
                    self.chance_node(
                        &mut board_copy,
                        &mv,
                        depth as i32,
                        f64::NEG_INFINITY,
                        f64::INFINITY,
                        board.current_turn(),
                    )
                } else {
                    board_copy.make_move(&mv);
                    -self.expectimax(
                        &mut board_copy,
                        (depth - 1) as i32,
                        f64::NEG_INFINITY,
                        f64::INFINITY,
                    )
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
