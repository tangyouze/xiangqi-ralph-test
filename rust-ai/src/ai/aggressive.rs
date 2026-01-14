//! 进攻型 AI 策略

use super::{sort_and_truncate, AIConfig, AIStrategy, ScoredMove};
use crate::board::Board;
use crate::types::{Color, GameResult, PieceType, Position, HIDDEN_PIECE_VALUE};
use rand::prelude::*;

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
