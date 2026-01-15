//! 迭代加深 AI 策略

use super::{sort_and_truncate, AIConfig, AIStrategy, ScoredMove};
use crate::board::Board;
use crate::types::{Color, GameResult, JieqiMove, PieceType, HIDDEN_PIECE_VALUE};
use rand::prelude::*;
use std::cmp::Ordering as CmpOrdering;
use std::sync::atomic::Ordering as AtomicOrdering;
use std::time::{Duration, Instant};

use super::minimax::NODE_COUNT;

/// Iterative Deepening AI - 迭代加深搜索
pub struct IterativeDeepeningAI {
    max_depth: u32,
    rng: StdRng,
    randomness: f64,
    time_limit: Option<Duration>,
}

impl IterativeDeepeningAI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        // 如果设置了时间限制，允许无限加深；否则使用配置的深度
        let max_depth = if config.time_limit.is_some() {
            50 // 会被时间限制打断
        } else {
            config.depth
        };
        IterativeDeepeningAI {
            max_depth,
            rng,
            randomness: config.randomness,
            time_limit: config.time_limit.map(Duration::from_secs_f64),
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
        // 节点计数
        NODE_COUNT.fetch_add(1, AtomicOrdering::Relaxed);

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
        let start_time = Instant::now();

        // 从深度 1 开始迭代
        for depth in 1..=self.max_depth {
            // 检查时间限制
            if let Some(limit) = self.time_limit {
                if start_time.elapsed() >= limit {
                    break;
                }
            }

            let mut current_scores: Vec<(JieqiMove, f64)> = Vec::new();

            for &mv in &moves {
                // 每个走法也检查时间限制
                if let Some(limit) = self.time_limit {
                    if start_time.elapsed() >= limit {
                        break;
                    }
                }

                let mut board_copy = board.clone();
                board_copy.make_move(&mv);

                let score =
                    -self.negamax(&mut board_copy, depth - 1, f64::NEG_INFINITY, f64::INFINITY);

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

        sort_and_truncate(&mut scored, n);
        scored
    }
}
