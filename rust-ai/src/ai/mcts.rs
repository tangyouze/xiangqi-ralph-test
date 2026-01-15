//! MCTS AI 策略

use super::{AIConfig, AIStrategy, ScoredMove};
use crate::board::Board;
use crate::types::{Color, GameResult, JieqiMove, HIDDEN_PIECE_VALUE};
use rand::prelude::*;
use std::cmp::Ordering;
use std::collections::HashMap;

/// MCTS AI - Monte Carlo Tree Search (简化版)
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
            iterations: config.depth * 500,
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
                    return if start_color == Color::Black {
                        1.0
                    } else {
                        0.0
                    };
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
                // 转换为我方视角
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
