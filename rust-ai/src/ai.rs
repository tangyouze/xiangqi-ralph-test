//! AI 策略模块
//!
//! 提供多种 AI 策略实现，包括随机、贪婪、Minimax 等

use crate::board::Board;
use crate::types::{ActionType, Color, GameResult, JieqiMove, PieceType, HIDDEN_PIECE_VALUE};
use rand::prelude::*;
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
}

impl Default for AIConfig {
    fn default() -> Self {
        AIConfig {
            depth: 3,
            randomness: 0.0,
            seed: None,
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

// ============================================================================
// 随机策略
// ============================================================================

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

        scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        scored.truncate(n);
        scored
    }
}

// ============================================================================
// 贪婪策略
// ============================================================================

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
    fn evaluate_move(&self, board: &Board, mv: &JieqiMove) -> f64 {
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
            score += 50.0; // 适度的揭子奖励
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

        scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        scored.truncate(n);
        scored
    }
}

// ============================================================================
// Minimax 策略
// ============================================================================

/// Minimax AI - 使用 Alpha-Beta 剪枝
pub struct MinimaxAI {
    depth: u32,
    rng: StdRng,
    randomness: f64,
}

impl MinimaxAI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        MinimaxAI {
            depth: config.depth,
            rng,
            randomness: config.randomness,
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
        }

        score
    }

    /// Negamax 搜索（带 Alpha-Beta 剪枝）
    ///
    /// 从当前玩家视角返回评估值（正值表示当前玩家有利）
    fn negamax(
        &self,
        board: &mut Board,
        depth: u32,
        mut alpha: f64,
        beta: f64,
    ) -> f64 {
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
            let was_hidden = board.get_piece(mv.from_pos).map_or(false, |p| p.is_hidden);
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
        let color = board.current_turn();
        let moves = board.get_legal_moves(color);
        let mut rng = self.rng.clone();

        let mut scored: Vec<ScoredMove> = moves
            .into_iter()
            .map(|mv| {
                let mut board_copy = board.clone();
                board_copy.make_move(&mv);

                // 使用 negamax 搜索：从对手视角取负值
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

        scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        scored.truncate(n);
        scored
    }
}

// ============================================================================
// AI 引擎
// ============================================================================

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

    /// 创建 Minimax AI
    pub fn minimax(config: &AIConfig) -> Self {
        AIEngine {
            strategy: Box::new(MinimaxAI::new(config)),
        }
    }

    /// 从策略名称创建
    pub fn from_strategy(name: &str, config: &AIConfig) -> Result<Self, String> {
        match name.to_lowercase().as_str() {
            "random" => Ok(Self::random(config.seed)),
            "greedy" => Ok(Self::greedy(config)),
            "minimax" | "alphabeta" => Ok(Self::minimax(config)),
            _ => Err(format!("Unknown strategy: {}", name)),
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
    fn test_minimax_ai() {
        let fen = "4k4/9/9/9/9/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig {
            depth: 2,
            ..Default::default()
        };
        let ai = AIEngine::minimax(&config);
        let best = ai.select_best_move_fen(fen).unwrap();

        assert!(best.is_some());
    }

    #[test]
    fn test_capture_preference() {
        // 红方车可以吃黑方炮
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig::default();
        let ai = AIEngine::greedy(&config);
        let best = ai.select_best_move_fen(fen).unwrap().unwrap();

        // 贪婪 AI 应该选择吃炮
        assert_eq!(best, "e4e5");
    }
}
