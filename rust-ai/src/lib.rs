//! Xiangqi (Jieqi/Banqi) AI Engine
//!
//! 揭棋 AI 引擎 - 支持 FEN 输入输出

pub mod ai;
pub mod board;
pub mod fen;
pub mod test_positions;
pub mod types;

pub use ai::{
    get_depth_reached, get_node_count, reset_depth_reached, reset_node_count, strategies_help,
    AIConfig, AIEngine, AIStrategy, EvalDetail, HiddenPieceDistribution, PieceEval, ScoredMove,
    AVAILABLE_STRATEGIES, DEFAULT_STRATEGY, IT2AI,
};
pub use board::{get_legal_moves_from_fen, Board};
pub use fen::{apply_move_to_fen, parse_fen, pieces_to_fen, FenState};
pub use types::{ActionType, Color, GameResult, JieqiMove, PieceType, Position};
