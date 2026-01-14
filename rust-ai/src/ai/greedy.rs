//! 贪婪 AI 策略

use super::{sort_and_truncate, AIConfig, AIStrategy, ScoredMove};
use crate::board::Board;
use crate::types::{ActionType, Color, PieceType, HIDDEN_PIECE_VALUE};
use rand::prelude::*;

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
    fn evaluate_move(&self, board: &Board, mv: &crate::types::JieqiMove) -> f64 {
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
            score += 50.0;
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

        sort_and_truncate(&mut scored, n);
        scored
    }
}
