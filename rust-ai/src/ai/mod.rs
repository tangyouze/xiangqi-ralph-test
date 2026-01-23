//! AI 策略模块
//!
//! 提供 AI 策略实现：random, muses2, it2, it3

mod it2;
mod it3;
mod muses2;
mod random;

pub use it2::{EvalDetail, HiddenPieceDistribution, PieceEval, IT2AI};
pub use it3::IT3AI;
pub use muses2::Muses2AI;
pub use random::RandomAI;

use std::sync::atomic::{AtomicU32, AtomicU64, Ordering as AtomicOrdering};

/// 可用策略列表（添加新策略时只需修改这里）
pub const AVAILABLE_STRATEGIES: &[&str] = &["random", "muses2", "it2", "it3"];

/// 默认策略
pub const DEFAULT_STRATEGY: &str = "it2";

/// 获取可用策略的帮助字符串
pub fn strategies_help() -> String {
    AVAILABLE_STRATEGIES.join(", ")
}

/// 全局节点计数器
pub static NODE_COUNT: AtomicU64 = AtomicU64::new(0);

/// 全局搜索深度记录器
pub static DEPTH_REACHED: AtomicU32 = AtomicU32::new(0);

/// 每层节点计数（最大支持 50 层）
pub static DEPTH_NODES: [AtomicU64; 50] = {
    const INIT: AtomicU64 = AtomicU64::new(0);
    [INIT; 50]
};

/// 重置节点计数器
pub fn reset_node_count() {
    NODE_COUNT.store(0, AtomicOrdering::Relaxed);
}

/// 获取当前节点计数
pub fn get_node_count() -> u64 {
    NODE_COUNT.load(AtomicOrdering::Relaxed)
}

/// 重置深度记录器
pub fn reset_depth_reached() {
    DEPTH_REACHED.store(0, AtomicOrdering::Relaxed);
}

/// 获取搜索达到的深度
pub fn get_depth_reached() -> u32 {
    DEPTH_REACHED.load(AtomicOrdering::Relaxed)
}

/// 重置每层节点计数
pub fn reset_depth_nodes() {
    for counter in DEPTH_NODES.iter() {
        counter.store(0, AtomicOrdering::Relaxed);
    }
}

/// 增加指定深度的节点计数
#[inline]
pub fn add_depth_node(depth: usize) {
    if depth < DEPTH_NODES.len() {
        DEPTH_NODES[depth].fetch_add(1, AtomicOrdering::Relaxed);
    }
}

/// 获取每层节点统计（返回非零层的 Vec<(depth, count)>）
pub fn get_depth_nodes_stats() -> Vec<(usize, u64)> {
    DEPTH_NODES
        .iter()
        .enumerate()
        .filter_map(|(i, c)| {
            let count = c.load(AtomicOrdering::Relaxed);
            if count > 0 {
                Some((i, count))
            } else {
                None
            }
        })
        .collect()
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

    /// 创建 Muses2 AI
    pub fn muses2(config: &AIConfig) -> Self {
        AIEngine {
            strategy: Box::new(Muses2AI::new(config)),
        }
    }

    /// 创建 IT2 AI (Expectimax)
    pub fn it2(config: &AIConfig) -> Self {
        AIEngine {
            strategy: Box::new(IT2AI::new(config)),
        }
    }

    /// 创建 IT3 AI (Expectimax + 优化)
    pub fn it3(config: &AIConfig) -> Self {
        AIEngine {
            strategy: Box::new(IT3AI::new(config)),
        }
    }

    /// 从策略名称创建
    pub fn from_strategy(name: &str, config: &AIConfig) -> Result<Self, String> {
        match name.to_lowercase().as_str() {
            "random" => Ok(Self::random(config.seed)),
            "muses2" => Ok(Self::muses2(config)),
            "it2" => Ok(Self::it2(config)),
            "it3" => Ok(Self::it3(config)),
            _ => Err(format!(
                "Unknown strategy: {}. Available: {}",
                name,
                strategies_help()
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
        let fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";
        let ai = AIEngine::random(Some(42));
        let moves = ai.select_moves_fen(fen, 5).unwrap();
        assert_eq!(moves.len(), 5);
    }

    #[test]
    fn test_muses2_ai() {
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig {
            depth: 2,
            ..Default::default()
        };
        let ai = AIEngine::muses2(&config);
        let best = ai.select_best_move_fen(fen).unwrap().unwrap();
        assert_eq!(best, "e4e5");
    }

    #[test]
    fn test_it2_ai() {
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig {
            depth: 2,
            ..Default::default()
        };
        let ai = AIEngine::it2(&config);
        let best = ai.select_best_move_fen(fen).unwrap().unwrap();
        assert_eq!(best, "e4e5");
    }

    #[test]
    fn test_all_strategies_from_name() {
        let config = AIConfig::default();
        let strategies = vec!["random", "muses2", "it2", "it3"];

        for name in strategies {
            let result = AIEngine::from_strategy(name, &config);
            assert!(result.is_ok(), "Failed to create strategy: {}", name);
        }
    }
}
