//! 位置评估 AI 策略

use super::{sort_and_truncate, AIConfig, AIStrategy, ScoredMove};
use crate::board::{Board, Piece};
use crate::types::{Color, GameResult, PieceType, Position, HIDDEN_PIECE_VALUE};
use rand::prelude::*;

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
    fn get_position_bonus(&self, piece: &Piece, _board: &Board) -> f64 {
        let pos = piece.position;
        let is_red = piece.color == Color::Red;
        let row = if is_red { pos.row } else { 9 - pos.row } as f64;
        let col = pos.col as f64;

        match piece.get_movement_type() {
            PieceType::King => {
                let center_dist = (col - 4.0).abs();
                -center_dist * 5.0
            }
            PieceType::Rook => {
                let column_bonus = 10.0 - (col - 4.0).abs() * 2.0;
                let cross_river_bonus = if row >= 5.0 { 20.0 } else { 0.0 };
                column_bonus + cross_river_bonus
            }
            PieceType::Cannon => {
                let column_bonus = 8.0 - (col - 4.0).abs() * 1.5;
                let row_bonus = if (2.0..=7.0).contains(&row) {
                    10.0
                } else {
                    0.0
                };
                column_bonus + row_bonus
            }
            PieceType::Horse => {
                let center_bonus = 15.0 - (col - 4.0).abs() * 2.0 - (row - 4.5).abs() * 1.5;
                center_bonus.max(0.0)
            }
            PieceType::Elephant => {
                if (col == 2.0 || col == 6.0) && row <= 4.0 {
                    10.0
                } else {
                    0.0
                }
            }
            PieceType::Advisor => {
                if col == 4.0 && row == 1.0 {
                    15.0
                } else {
                    5.0
                }
            }
            PieceType::Pawn => {
                let cross_river = row >= 5.0;
                let center_bonus = 10.0 - (col - 4.0).abs() * 2.0;
                let advance_bonus = row * 5.0;
                if cross_river {
                    center_bonus + advance_bonus + 30.0
                } else {
                    advance_bonus
                }
            }
        }
    }

    /// 评估王安全
    fn evaluate_king_safety(&self, board: &Board, color: Color) -> f64 {
        let mut safety = 0.0;

        if let Some(king_pos) = board.find_king(color) {
            let defenders = self.count_defenders_near_king(board, king_pos, color);
            safety += defenders as f64 * 10.0;

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
