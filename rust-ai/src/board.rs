//! 揭棋模拟棋盘
//!
//! Board 用于 AI 进行走棋模拟和合法走法生成。
//! 暗子在模拟中保持 piece_type = None，评估时使用期望值。

use crate::fen::parse_fen;
use crate::types::{
    get_position_piece_type, ActionType, Color, GameResult, JieqiMove, PieceType, Position,
};
use std::collections::HashMap;

/// 模拟棋子
#[derive(Debug, Clone)]
pub struct Piece {
    pub color: Color,
    pub position: Position,
    pub is_hidden: bool,
    /// 明子时的实际类型，暗子时为 None
    pub actual_type: Option<PieceType>,
    /// 暗子的走法类型（由位置决定）
    pub movement_type: Option<PieceType>,
}

impl Piece {
    /// 获取走法类型
    pub fn get_movement_type(&self) -> PieceType {
        if self.is_hidden {
            self.movement_type
                .expect("Hidden piece must have movement_type")
        } else {
            self.actual_type
                .expect("Revealed piece must have actual_type")
        }
    }
}

/// 模拟棋盘
pub struct Board {
    pieces: HashMap<Position, Piece>,
    viewer: Color,
    current_turn: Color,
}

impl Board {
    /// 从 FEN 字符串创建棋盘
    pub fn from_fen(fen: &str) -> Result<Board, String> {
        let state = parse_fen(fen)?;
        let mut pieces = HashMap::new();

        for fp in state.pieces {
            let movement_type = if fp.is_hidden {
                get_position_piece_type(fp.position)
            } else {
                fp.piece_type
            };

            pieces.insert(
                fp.position,
                Piece {
                    color: fp.color,
                    position: fp.position,
                    is_hidden: fp.is_hidden,
                    actual_type: fp.piece_type,
                    movement_type,
                },
            );
        }

        Ok(Board {
            pieces,
            viewer: state.viewer,
            current_turn: state.turn,
        })
    }

    /// 获取当前回合
    pub fn current_turn(&self) -> Color {
        self.current_turn
    }

    /// 获取某位置的棋子
    pub fn get_piece(&self, pos: Position) -> Option<&Piece> {
        self.pieces.get(&pos)
    }

    /// 获取所有棋子
    pub fn get_all_pieces(&self, color: Option<Color>) -> Vec<&Piece> {
        self.pieces
            .values()
            .filter(|p| color.map_or(true, |c| p.color == c))
            .collect()
    }

    /// 找到将的位置
    pub fn find_king(&self, color: Color) -> Option<Position> {
        for piece in self.pieces.values() {
            if piece.color != color {
                continue;
            }
            // 明子：使用 actual_type
            if piece.actual_type == Some(PieceType::King) {
                return Some(piece.position);
            }
            // 暗子：使用 movement_type（在将的初始位置）
            if piece.is_hidden && piece.movement_type == Some(PieceType::King) {
                return Some(piece.position);
            }
        }
        None
    }

    /// 执行走棋，返回被吃的棋子
    pub fn make_move(&mut self, mv: &JieqiMove) -> Option<Piece> {
        let mut piece = self.pieces.remove(&mv.from_pos)?;

        // 揭子走法：标记为明子
        if mv.action_type == ActionType::RevealAndMove {
            piece.is_hidden = false;
            // 使用位置类型作为"已知"类型
            piece.actual_type = piece.movement_type;
        }

        // 移动棋子
        let captured = self.pieces.remove(&mv.to_pos);
        piece.position = mv.to_pos;
        self.pieces.insert(mv.to_pos, piece);

        // 切换回合
        self.current_turn = self.current_turn.opposite();

        captured
    }

    /// 撤销走棋
    pub fn undo_move(&mut self, mv: &JieqiMove, captured: Option<Piece>, was_hidden: bool) {
        let mut piece = self.pieces.remove(&mv.to_pos).expect("No piece at to_pos");

        piece.position = mv.from_pos;

        // 恢复暗子状态
        if was_hidden {
            piece.is_hidden = true;
            piece.actual_type = None;
        }

        self.pieces.insert(mv.from_pos, piece);

        if let Some(mut cap) = captured {
            cap.position = mv.to_pos;
            self.pieces.insert(mv.to_pos, cap);
        }

        // 恢复回合
        self.current_turn = self.current_turn.opposite();
    }

    /// 获取棋子的所有可能目标位置
    pub fn get_potential_moves(&self, piece: &Piece) -> Vec<Position> {
        let movement_type = piece.get_movement_type();

        match movement_type {
            PieceType::King => self.get_king_moves(piece),
            PieceType::Advisor => self.get_advisor_moves(piece),
            PieceType::Elephant => self.get_elephant_moves(piece),
            PieceType::Horse => self.get_horse_moves(piece),
            PieceType::Rook => self.get_rook_moves(piece),
            PieceType::Cannon => self.get_cannon_moves(piece),
            PieceType::Pawn => self.get_pawn_moves(piece),
        }
    }

    fn can_move_to(&self, piece: &Piece, pos: Position) -> bool {
        if !pos.is_valid() {
            return false;
        }
        match self.pieces.get(&pos) {
            None => true,
            Some(target) => target.color != piece.color,
        }
    }

    fn get_king_moves(&self, piece: &Piece) -> Vec<Position> {
        let mut moves = Vec::new();
        let pos = piece.position;

        // 王可以走的方向：上下左右
        let directions = [(1, 0), (-1, 0), (0, 1), (0, -1)];

        for (dr, dc) in directions {
            let new_pos = pos.offset(dr, dc);
            if new_pos.is_in_palace(piece.color) && self.can_move_to(piece, new_pos) {
                moves.push(new_pos);
            }
        }

        // 飞将
        if let Some(enemy_king_pos) = self.find_king(piece.color.opposite()) {
            if enemy_king_pos.col == pos.col {
                let min_row = pos.row.min(enemy_king_pos.row);
                let max_row = pos.row.max(enemy_king_pos.row);
                let mut has_piece = false;
                for row in (min_row + 1)..max_row {
                    if self.pieces.contains_key(&Position::new(row, pos.col)) {
                        has_piece = true;
                        break;
                    }
                }
                if !has_piece {
                    moves.push(enemy_king_pos);
                }
            }
        }

        moves
    }

    fn get_advisor_moves(&self, piece: &Piece) -> Vec<Position> {
        let mut moves = Vec::new();
        let pos = piece.position;

        // 士可以走的方向：斜向
        let directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)];

        for (dr, dc) in directions {
            let new_pos = pos.offset(dr, dc);
            if piece.is_hidden {
                // 暗子士必须在九宫内
                if !new_pos.is_in_palace(piece.color) {
                    continue;
                }
            }
            if new_pos.is_valid() && self.can_move_to(piece, new_pos) {
                // 明子士也必须在九宫内
                if !piece.is_hidden && !new_pos.is_in_palace(piece.color) {
                    continue;
                }
                moves.push(new_pos);
            }
        }

        moves
    }

    fn get_elephant_moves(&self, piece: &Piece) -> Vec<Position> {
        let mut moves = Vec::new();
        let pos = piece.position;

        // 象可以走的方向：田字形
        // (目标偏移, 象眼偏移)
        let directions = [
            ((2, 2), (1, 1)),
            ((2, -2), (1, -1)),
            ((-2, 2), (-1, 1)),
            ((-2, -2), (-1, -1)),
        ];

        for ((dr, dc), (er, ec)) in directions {
            let new_pos = pos.offset(dr, dc);
            let eye_pos = pos.offset(er, ec);

            // 暗子象不能过河
            if piece.is_hidden && !new_pos.is_on_own_side(piece.color) {
                continue;
            }
            // 明子象也不能过河
            if !piece.is_hidden && !new_pos.is_on_own_side(piece.color) {
                continue;
            }

            // 检查象眼
            if self.pieces.contains_key(&eye_pos) {
                continue;
            }

            if new_pos.is_valid() && self.can_move_to(piece, new_pos) {
                moves.push(new_pos);
            }
        }

        moves
    }

    fn get_horse_moves(&self, piece: &Piece) -> Vec<Position> {
        let mut moves = Vec::new();
        let pos = piece.position;

        // 马可以走的方向：日字形
        // (目标偏移, 马腿偏移)
        let directions = [
            ((2, 1), (1, 0)),
            ((2, -1), (1, 0)),
            ((-2, 1), (-1, 0)),
            ((-2, -1), (-1, 0)),
            ((1, 2), (0, 1)),
            ((1, -2), (0, -1)),
            ((-1, 2), (0, 1)),
            ((-1, -2), (0, -1)),
        ];

        for ((dr, dc), (lr, lc)) in directions {
            let new_pos = pos.offset(dr, dc);
            let leg_pos = pos.offset(lr, lc);

            // 检查马腿
            if self.pieces.contains_key(&leg_pos) {
                continue;
            }

            if new_pos.is_valid() && self.can_move_to(piece, new_pos) {
                moves.push(new_pos);
            }
        }

        moves
    }

    fn get_rook_moves(&self, piece: &Piece) -> Vec<Position> {
        let mut moves = Vec::new();
        let pos = piece.position;

        // 车可以走的方向：上下左右任意距离
        let directions = [(1, 0), (-1, 0), (0, 1), (0, -1)];

        for (dr, dc) in directions {
            let mut new_pos = pos.offset(dr, dc);
            while new_pos.is_valid() {
                match self.pieces.get(&new_pos) {
                    None => {
                        moves.push(new_pos);
                    }
                    Some(target) => {
                        if target.color != piece.color {
                            moves.push(new_pos);
                        }
                        break;
                    }
                }
                new_pos = new_pos.offset(dr, dc);
            }
        }

        moves
    }

    fn get_cannon_moves(&self, piece: &Piece) -> Vec<Position> {
        let mut moves = Vec::new();
        let pos = piece.position;

        // 炮可以走的方向：上下左右任意距离
        let directions = [(1, 0), (-1, 0), (0, 1), (0, -1)];

        for (dr, dc) in directions {
            let mut new_pos = pos.offset(dr, dc);
            let mut found_platform = false;

            while new_pos.is_valid() {
                match self.pieces.get(&new_pos) {
                    None => {
                        if !found_platform {
                            moves.push(new_pos);
                        }
                    }
                    Some(target) => {
                        if !found_platform {
                            found_platform = true;
                        } else {
                            if target.color != piece.color {
                                moves.push(new_pos);
                            }
                            break;
                        }
                    }
                }
                new_pos = new_pos.offset(dr, dc);
            }
        }

        moves
    }

    fn get_pawn_moves(&self, piece: &Piece) -> Vec<Position> {
        let mut moves = Vec::new();
        let pos = piece.position;

        let is_red = piece.color == Color::Red;
        let forward = if is_red { 1 } else { -1 };
        let crossed_river = if is_red { pos.row >= 5 } else { pos.row <= 4 };

        // 向前走
        let forward_pos = pos.offset(forward, 0);
        if forward_pos.is_valid() && self.can_move_to(piece, forward_pos) {
            moves.push(forward_pos);
        }

        // 过河后可以左右走
        if crossed_river {
            for dc in [-1, 1] {
                let side_pos = pos.offset(0, dc);
                if side_pos.is_valid() && self.can_move_to(piece, side_pos) {
                    moves.push(side_pos);
                }
            }
        }

        moves
    }

    /// 检查是否被将军
    pub fn is_in_check(&self, color: Color) -> bool {
        if let Some(king_pos) = self.find_king(color) {
            self.is_king_attacked(king_pos, color)
        } else {
            true // 没有将就是被将死了
        }
    }

    /// 检测将是否被攻击
    pub fn is_king_attacked(&self, king_pos: Position, king_color: Color) -> bool {
        let enemy_color = king_color.opposite();

        // 检查所有敌方棋子是否能攻击到将的位置
        for piece in self.pieces.values() {
            if piece.color != enemy_color {
                continue;
            }

            let targets = self.get_potential_moves(piece);
            if targets.contains(&king_pos) {
                return true;
            }
        }

        false
    }

    /// 获取所有合法走法
    pub fn get_legal_moves(&self, color: Color) -> Vec<JieqiMove> {
        // 使用克隆的方式来进行走法合法性检查
        let mut board_copy = self.clone();
        board_copy.get_legal_moves_mut(color)
    }

    /// 获取所有合法走法（可变版本）
    fn get_legal_moves_mut(&mut self, color: Color) -> Vec<JieqiMove> {
        let mut moves = Vec::new();

        let king_pos = match self.find_king(color) {
            Some(pos) => pos,
            None => return moves,
        };

        let my_pieces: Vec<Piece> = self
            .pieces
            .values()
            .filter(|p| p.color == color)
            .cloned()
            .collect();

        for piece in &my_pieces {
            let action_type = if piece.is_hidden {
                ActionType::RevealAndMove
            } else {
                ActionType::Move
            };
            let was_hidden = piece.is_hidden;
            let from_pos = piece.position;
            let is_king = piece.get_movement_type() == PieceType::King;

            // 获取潜在走法（需要重新获取棋子引用）
            let potential_moves = if let Some(p) = self.pieces.get(&from_pos) {
                self.get_potential_moves(p)
            } else {
                continue;
            };

            for to_pos in potential_moves {
                let mv = JieqiMove {
                    action_type,
                    from_pos,
                    to_pos,
                };

                let captured = self.make_move(&mv);

                // 检查走后是否被将军
                let check_king_pos = if is_king {
                    to_pos
                } else {
                    self.find_king(color).unwrap_or(king_pos)
                };

                let in_check = self.is_king_attacked(check_king_pos, color);

                self.undo_move(&mv, captured, was_hidden);

                if !in_check {
                    moves.push(mv);
                }
            }
        }

        moves
    }

    /// 获取所有合法走法（字符串格式）
    pub fn get_legal_moves_str(&self, color: Color) -> Vec<String> {
        self.get_legal_moves(color)
            .iter()
            .map(|m| m.to_fen_str(None))
            .collect()
    }

    /// 判断游戏结果
    pub fn get_game_result(&self, legal_moves: Option<&[JieqiMove]>) -> GameResult {
        let red_king = self.find_king(Color::Red);
        let black_king = self.find_king(Color::Black);

        if red_king.is_none() {
            return GameResult::BlackWin;
        }
        if black_king.is_none() {
            return GameResult::RedWin;
        }

        let moves = match legal_moves {
            Some(m) => m.to_vec(),
            None => self.get_legal_moves(self.current_turn),
        };

        if moves.is_empty() {
            if self.is_in_check(self.current_turn) {
                // 被将死
                match self.current_turn {
                    Color::Red => GameResult::BlackWin,
                    Color::Black => GameResult::RedWin,
                }
            } else {
                // 无子可走但没被将军
                GameResult::Draw
            }
        } else {
            GameResult::Ongoing
        }
    }

    /// 复制棋盘
    pub fn clone(&self) -> Board {
        Board {
            pieces: self.pieces.clone(),
            viewer: self.viewer,
            current_turn: self.current_turn,
        }
    }
}

/// 从 FEN 获取所有合法走法
pub fn get_legal_moves_from_fen(fen: &str) -> Result<Vec<String>, String> {
    let board = Board::from_fen(fen)?;
    let state = parse_fen(fen)?;
    Ok(board.get_legal_moves_str(state.turn))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_initial_board() {
        let fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r";
        let board = Board::from_fen(fen).unwrap();

        assert_eq!(board.get_all_pieces(Some(Color::Red)).len(), 16);
        assert_eq!(board.get_all_pieces(Some(Color::Black)).len(), 16);
        assert_eq!(board.current_turn(), Color::Red);
    }

    #[test]
    fn test_legal_moves_initial() {
        let fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r";
        let board = Board::from_fen(fen).unwrap();
        let moves = board.get_legal_moves(Color::Red);

        // 初始局面红方应该有 44 个合法走法
        assert_eq!(moves.len(), 44);
    }

    #[test]
    fn test_check_detection() {
        // 红方车将军黑方
        let fen = "4k4/4R4/9/9/9/9/9/9/9/4K4 -:- b r";
        let board = Board::from_fen(fen).unwrap();

        assert!(board.is_in_check(Color::Black));
        assert!(!board.is_in_check(Color::Red));
    }

    #[test]
    fn test_king_facing() {
        // 将帅对脸
        let fen = "4k4/9/9/9/9/9/9/9/9/4K4 -:- r r";
        let board = Board::from_fen(fen).unwrap();
        let moves = board.get_legal_moves(Color::Red);

        // 帅可以左右移动或向上移动（飞将吃掉黑将）
        assert!(moves.len() > 0);

        // 检查是否有飞将的走法
        let fly_move = moves
            .iter()
            .find(|m| m.to_pos == Position::new(9, 4))
            .is_some();
        assert!(fly_move, "Should have flying general move");
    }

    #[test]
    fn test_rook_moves() {
        let fen = "4k4/9/9/9/9/4R4/9/9/9/4K4 -:- r r";
        let board = Board::from_fen(fen).unwrap();

        let rook = board.get_piece(Position::new(4, 4)).unwrap();
        let moves = board.get_potential_moves(rook);

        // 车在中间应该能走很多位置
        assert!(moves.len() > 10);
    }

    #[test]
    fn test_capture_move() {
        // 红方车可以吃黑方炮
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let board = Board::from_fen(fen).unwrap();
        let moves = board.get_legal_moves_str(Color::Red);

        assert!(moves.contains(&"e4e5".to_string()));
    }
}
