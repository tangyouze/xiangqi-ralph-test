//! Xiangqi (Jieqi/Banqi) AI Engine
//!
//! 揭棋 AI 引擎 - 支持 FEN 输入输出

pub mod ai;
pub mod board;
pub mod fen;
pub mod types;

pub use ai::{AIConfig, AIEngine, AIStrategy, ScoredMove};
pub use board::{get_legal_moves_from_fen, Board};
pub use fen::{apply_move_to_fen, parse_fen, pieces_to_fen, FenState};
pub use types::{ActionType, Color, GameResult, JieqiMove, PieceType, Position};
