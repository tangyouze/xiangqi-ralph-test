//! Minimax AI 策略

use super::{sort_and_truncate, AIConfig, AIStrategy, ScoredMove};
use crate::board::Board;
use crate::types::{Color, GameResult, PieceType, HIDDEN_PIECE_VALUE};
use rand::prelude::*;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

/// 全局节点计数器
pub static NODE_COUNT: AtomicU64 = AtomicU64::new(0);

/// Minimax AI - 使用 Alpha-Beta 剪枝
pub struct MinimaxAI {
    depth: u32,
    rng: StdRng,
    randomness: f64,
    time_limit: Option<Duration>,
    start_time: Option<Instant>,
}

impl MinimaxAI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        // 如果设置了时间限制，使用较大的深度（会被时间打断）
        let depth = if config.time_limit.is_some() && config.depth > 10 {
            10 // 带时间限制时，限制最大深度避免卡死
        } else {
            config.depth.min(6) // 无时间限制时，最大深度 6
        };
        MinimaxAI {
            depth,
            rng,
            randomness: config.randomness,
            time_limit: config.time_limit.map(Duration::from_secs_f64),
            start_time: None,
        }
    }

    /// 检查是否超时
    fn is_timeout(&self) -> bool {
        if let (Some(limit), Some(start)) = (self.time_limit, self.start_time) {
            start.elapsed() >= limit
        } else {
            false
        }
    }

    /// 评估局面（公开方法）
    pub fn evaluate_position(&self, board: &Board, color: Color) -> f64 {
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

    /// 静态评估一个棋盘局面（不搜索）
    pub fn evaluate_static(board: &Board, color: Color) -> f64 {
        let config = AIConfig {
            depth: 1,
            randomness: 0.0,
            seed: None,
            time_limit: None,
        };
        let ai = MinimaxAI::new(&config);
        ai.evaluate_position(board, color)
    }

    /// Negamax 搜索（带 Alpha-Beta 剪枝）
    fn negamax(&self, board: &mut Board, depth: u32, mut alpha: f64, beta: f64) -> f64 {
        // 节点计数
        NODE_COUNT.fetch_add(1, Ordering::Relaxed);

        // 超时检查（每 1000 个节点检查一次）
        if NODE_COUNT.load(Ordering::Relaxed) % 1000 == 0 && self.is_timeout() {
            return 0.0; // 超时返回中性分数
        }

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
            // 超时检查
            if self.is_timeout() {
                break;
            }

            let was_hidden = board.get_piece(mv.from_pos).is_some_and(|p| p.is_hidden);
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
        // 设置开始时间（通过可变引用绕过 borrow checker）
        let mut ai = MinimaxAI {
            depth: self.depth,
            rng: self.rng.clone(),
            randomness: self.randomness,
            time_limit: self.time_limit,
            start_time: Some(Instant::now()),
        };

        let color = board.current_turn();
        let moves = board.get_legal_moves(color);

        let mut scored: Vec<ScoredMove> = moves
            .into_iter()
            .filter_map(|mv| {
                // 超时检查
                if ai.is_timeout() {
                    return None;
                }

                let mut board_copy = board.clone();
                board_copy.make_move(&mv);

                // 使用 negamax 搜索：从对手视角取负值
                let base_score = -ai.negamax(
                    &mut board_copy,
                    ai.depth - 1,
                    f64::NEG_INFINITY,
                    f64::INFINITY,
                );

                let noise = if ai.randomness > 0.0 {
                    ai.rng.gen::<f64>() * ai.randomness * 100.0
                } else {
                    0.0
                };

                Some(ScoredMove {
                    mv,
                    score: base_score + noise,
                })
            })
            .collect();

        sort_and_truncate(&mut scored, n);
        scored
    }
}
