//! AI 策略模块
//!
//! 提供多种 AI 策略实现，包括随机、贪婪、迭代加深等

mod greedy;
mod iterative;
mod mcts;
mod muses;
mod random;

pub use greedy::GreedyAI;
pub use iterative::IterativeDeepeningAI;
pub use mcts::MCTSAI;
pub use muses::MusesAI;
pub use random::RandomAI;

use std::sync::atomic::{AtomicU64, Ordering as AtomicOrdering};

/// 全局节点计数器
pub static NODE_COUNT: AtomicU64 = AtomicU64::new(0);

/// 重置节点计数器
pub fn reset_node_count() {
    NODE_COUNT.store(0, AtomicOrdering::Relaxed);
}

/// 获取当前节点计数
pub fn get_node_count() -> u64 {
    NODE_COUNT.load(AtomicOrdering::Relaxed)
}

use crate::board::Board;
use crate::types::JieqiMove;
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
    /// 时间限制（秒）
    pub time_limit: Option<f64>,
}

impl Default for AIConfig {
    fn default() -> Self {
        AIConfig {
            depth: 3,
            randomness: 0.0,
            seed: None,
            time_limit: None,
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

/// 排序辅助函数
pub(crate) fn sort_and_truncate(scored: &mut Vec<ScoredMove>, n: usize) {
    scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
    scored.truncate(n);
}

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

    /// 创建 Muses AI
    pub fn muses(config: &AIConfig) -> Self {
        AIEngine {
            strategy: Box::new(MusesAI::new(config)),
        }
    }

    /// 从策略名称创建
    pub fn from_strategy(name: &str, config: &AIConfig) -> Result<Self, String> {
        match name.to_lowercase().as_str() {
            "random" => Ok(Self::random(config.seed)),
            "greedy" => Ok(Self::greedy(config)),
            "iterative" | "iterative_deepening" => Ok(Self::iterative_deepening(config)),
            "mcts" | "montecarlo" => Ok(Self::mcts(config)),
            "muses" => Ok(Self::muses(config)),
            _ => Err(format!(
                "Unknown strategy: {}. Available: random, greedy, iterative, mcts, muses",
                name
            )),
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
    fn test_capture_preference() {
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig::default();
        let ai = AIEngine::greedy(&config);
        let best = ai.select_best_move_fen(fen).unwrap().unwrap();
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
            depth: 1,
            seed: Some(42),
            ..Default::default()
        };
        let ai = AIEngine::mcts(&config);
        let best = ai.select_best_move_fen(fen).unwrap();
        assert!(best.is_some());
    }

    #[test]
    fn test_muses_ai() {
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig {
            depth: 2,
            ..Default::default()
        };
        let ai = AIEngine::muses(&config);
        let best = ai.select_best_move_fen(fen).unwrap().unwrap();
        assert_eq!(best, "e4e5");
    }

    #[test]
    fn test_all_strategies_from_name() {
        let config = AIConfig::default();
        let strategies = vec!["random", "greedy", "iterative", "mcts", "muses"];

        for name in strategies {
            let result = AIEngine::from_strategy(name, &config);
            assert!(result.is_ok(), "Failed to create strategy: {}", name);
        }
    }
}
