//! 防守型 AI 策略

use super::{sort_and_truncate, AIConfig, AIStrategy, ScoredMove};
use crate::board::{Board, Piece};
use crate::types::{Color, GameResult, PieceType, Position, HIDDEN_PIECE_VALUE};
use rand::prelude::*;

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

    fn is_defending_king(&self, board: &Board, piece: &Piece, color: Color) -> bool {
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
            let was_hidden = board.get_piece(mv.from_pos).is_some_and(|p| p.is_hidden);
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

        sort_and_truncate(&mut scored, n);
        scored
    }
}
