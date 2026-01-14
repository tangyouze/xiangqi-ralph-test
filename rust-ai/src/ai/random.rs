//! 随机 AI 策略

use super::{sort_and_truncate, AIStrategy, ScoredMove};
use crate::board::Board;
use rand::prelude::*;

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

        sort_and_truncate(&mut scored, n);
        scored
    }
}
