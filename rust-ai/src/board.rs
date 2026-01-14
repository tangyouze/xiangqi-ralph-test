//! 揭棋模拟棋盘（优化版）
//!
//! 使用数组而非 HashMap 存储棋子，提高性能。

use crate::fen::parse_fen;
use crate::types::{
    get_position_piece_type, ActionType, Color, GameResult, JieqiMove, PieceType, Position,
};

/// 模拟棋子
#[derive(Debug, Clone, Copy)]
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
    #[inline]
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

/// 模拟棋盘（优化版：使用数组存储）
#[derive(Clone)]
pub struct Board {
    /// 90 个格子的棋子数组 (10行 x 9列)
    squares: [Option<Piece>; 90],
    viewer: Color,
    current_turn: Color,
    /// 缓存红方将的位置
    red_king_pos: Option<Position>,
    /// 缓存黑方将的位置
    black_king_pos: Option<Position>,
}

impl Board {
    /// 从 FEN 字符串创建棋盘
    pub fn from_fen(fen: &str) -> Result<Board, String> {
        let state = parse_fen(fen)?;
        let mut squares = [None; 90];
        let mut red_king_pos = None;
        let mut black_king_pos = None;

        for fp in state.pieces {
            let movement_type = if fp.is_hidden {
                get_position_piece_type(fp.position)
            } else {
                fp.piece_type
            };

            let piece = Piece {
                color: fp.color,
                position: fp.position,
                is_hidden: fp.is_hidden,
                actual_type: fp.piece_type,
                movement_type,
            };

            // 缓存将的位置
            if movement_type == Some(PieceType::King) || fp.piece_type == Some(PieceType::King) {
                match fp.color {
                    Color::Red => red_king_pos = Some(fp.position),
                    Color::Black => black_king_pos = Some(fp.position),
                }
            }

            squares[fp.position.to_index()] = Some(piece);
        }

        Ok(Board {
            squares,
            viewer: state.viewer,
            current_turn: state.turn,
            red_king_pos,
            black_king_pos,
        })
    }

    /// 获取当前回合
    #[inline]
    pub fn current_turn(&self) -> Color {
        self.current_turn
    }

    /// 设置当前回合（用于 Null Move Pruning）
    #[inline]
    pub fn set_turn(&mut self, color: Color) {
        self.current_turn = color;
    }

    /// 获取局面哈希（用于置换表）
    pub fn get_position_hash(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();

        // 哈希所有棋子
        for (i, square) in self.squares.iter().enumerate() {
            if let Some(piece) = square {
                i.hash(&mut hasher);
                piece.color.hash(&mut hasher);
                piece.is_hidden.hash(&mut hasher);
                piece.actual_type.hash(&mut hasher);
            }
        }

        // 哈希当前回合
        self.current_turn.hash(&mut hasher);

        hasher.finish()
    }

    /// 获取某位置的棋子
    #[inline]
    pub fn get_piece(&self, pos: Position) -> Option<&Piece> {
        if !pos.is_valid() {
            return None;
        }
        self.squares[pos.to_index()].as_ref()
    }

    /// 获取某位置的棋子（可变）
    #[inline]
    fn get_piece_mut(&mut self, pos: Position) -> Option<&mut Piece> {
        if !pos.is_valid() {
            return None;
        }
        self.squares[pos.to_index()].as_mut()
    }

    /// 检查位置是否有棋子
    #[inline]
    fn has_piece(&self, pos: Position) -> bool {
        pos.is_valid() && self.squares[pos.to_index()].is_some()
    }

    /// 获取所有棋子
    pub fn get_all_pieces(&self, color: Option<Color>) -> Vec<&Piece> {
        self.squares
            .iter()
            .filter_map(|p| p.as_ref())
            .filter(|p| color.map_or(true, |c| p.color == c))
            .collect()
    }

    /// 找到将的位置（使用缓存）
    #[inline]
    pub fn find_king(&self, color: Color) -> Option<Position> {
        match color {
            Color::Red => self.red_king_pos,
            Color::Black => self.black_king_pos,
        }
    }

    /// 执行走棋，返回被吃的棋子
    pub fn make_move(&mut self, mv: &JieqiMove) -> Option<Piece> {
        let from_idx = mv.from_pos.to_index();
        let to_idx = mv.to_pos.to_index();

        let mut piece = self.squares[from_idx].take()?;

        // 揭子走法：标记为明子
        if mv.action_type == ActionType::RevealAndMove {
            piece.is_hidden = false;
            piece.actual_type = piece.movement_type;
        }

        // 记录被吃的棋子
        let captured = self.squares[to_idx].take();

        // 更新将的位置缓存
        if piece.get_movement_type() == PieceType::King {
            match piece.color {
                Color::Red => self.red_king_pos = Some(mv.to_pos),
                Color::Black => self.black_king_pos = Some(mv.to_pos),
            }
        }

        // 如果吃掉了将，清除缓存
        if let Some(ref cap) = captured {
            if cap.get_movement_type() == PieceType::King {
                match cap.color {
                    Color::Red => self.red_king_pos = None,
                    Color::Black => self.black_king_pos = None,
                }
            }
        }

        // 移动棋子
        piece.position = mv.to_pos;
        self.squares[to_idx] = Some(piece);

        // 切换回合
        self.current_turn = self.current_turn.opposite();

        captured
    }

    /// 撤销走棋
    pub fn undo_move(&mut self, mv: &JieqiMove, captured: Option<Piece>, was_hidden: bool) {
        let from_idx = mv.from_pos.to_index();
        let to_idx = mv.to_pos.to_index();

        let mut piece = self.squares[to_idx].take().expect("No piece at to_pos");

        // 恢复暗子状态
        if was_hidden {
            piece.is_hidden = true;
            piece.actual_type = None;
        }

        // 更新将的位置缓存
        if piece.get_movement_type() == PieceType::King {
            match piece.color {
                Color::Red => self.red_king_pos = Some(mv.from_pos),
                Color::Black => self.black_king_pos = Some(mv.from_pos),
            }
        }

        piece.position = mv.from_pos;
        self.squares[from_idx] = Some(piece);

        // 恢复被吃的棋子
        if let Some(cap) = captured {
            // 恢复将的缓存
            if cap.get_movement_type() == PieceType::King {
                match cap.color {
                    Color::Red => self.red_king_pos = Some(mv.to_pos),
                    Color::Black => self.black_king_pos = Some(mv.to_pos),
                }
            }
            self.squares[to_idx] = Some(cap);
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

    #[inline]
    fn can_move_to(&self, piece: &Piece, pos: Position) -> bool {
        if !pos.is_valid() {
            return false;
        }
        match self.get_piece(pos) {
            None => true,
            Some(target) => target.color != piece.color,
        }
    }

    fn get_king_moves(&self, piece: &Piece) -> Vec<Position> {
        let mut moves = Vec::with_capacity(8);
        let pos = piece.position;

        // 王可以走的方向：上下左右
        let directions: [(i8, i8); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

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
                    if self.has_piece(Position::new(row, pos.col)) {
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
        let mut moves = Vec::with_capacity(4);
        let pos = piece.position;

        // 士可以走的方向：斜向
        let directions: [(i8, i8); 4] = [(1, 1), (1, -1), (-1, 1), (-1, -1)];

        for (dr, dc) in directions {
            let new_pos = pos.offset(dr, dc);
            if !new_pos.is_in_palace(piece.color) {
                continue;
            }
            if self.can_move_to(piece, new_pos) {
                moves.push(new_pos);
            }
        }

        moves
    }

    fn get_elephant_moves(&self, piece: &Piece) -> Vec<Position> {
        let mut moves = Vec::with_capacity(4);
        let pos = piece.position;

        // 象可以走的方向：田字形
        let directions: [((i8, i8), (i8, i8)); 4] = [
            ((2, 2), (1, 1)),
            ((2, -2), (1, -1)),
            ((-2, 2), (-1, 1)),
            ((-2, -2), (-1, -1)),
        ];

        for ((dr, dc), (er, ec)) in directions {
            let new_pos = pos.offset(dr, dc);
            let eye_pos = pos.offset(er, ec);

            // 象不能过河
            if !new_pos.is_on_own_side(piece.color) {
                continue;
            }

            // 检查象眼
            if self.has_piece(eye_pos) {
                continue;
            }

            if new_pos.is_valid() && self.can_move_to(piece, new_pos) {
                moves.push(new_pos);
            }
        }

        moves
    }

    fn get_horse_moves(&self, piece: &Piece) -> Vec<Position> {
        let mut moves = Vec::with_capacity(8);
        let pos = piece.position;

        // 马可以走的方向：日字形
        let directions: [((i8, i8), (i8, i8)); 8] = [
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
            if self.has_piece(leg_pos) {
                continue;
            }

            if new_pos.is_valid() && self.can_move_to(piece, new_pos) {
                moves.push(new_pos);
            }
        }

        moves
    }

    fn get_rook_moves(&self, piece: &Piece) -> Vec<Position> {
        let mut moves = Vec::with_capacity(17);
        let pos = piece.position;

        // 车可以走的方向：上下左右任意距离
        let directions: [(i8, i8); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

        for (dr, dc) in directions {
            let mut new_pos = pos.offset(dr, dc);
            while new_pos.is_valid() {
                match self.get_piece(new_pos) {
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
        let mut moves = Vec::with_capacity(17);
        let pos = piece.position;

        // 炮可以走的方向：上下左右任意距离
        let directions: [(i8, i8); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

        for (dr, dc) in directions {
            let mut new_pos = pos.offset(dr, dc);
            let mut found_platform = false;

            while new_pos.is_valid() {
                match self.get_piece(new_pos) {
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
        let mut moves = Vec::with_capacity(3);
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
            self.is_position_attacked(king_pos, color.opposite())
        } else {
            true // 没有将就是被将死了
        }
    }

    /// 检测某位置是否被某方攻击（优化版：不生成完整走法列表）
    pub fn is_position_attacked(&self, target_pos: Position, attacker_color: Color) -> bool {
        // 检查车/炮攻击（直线）
        for (dr, dc) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
            let mut pos = target_pos.offset(dr, dc);
            let mut found_screen = false;
            while pos.is_valid() {
                if let Some(piece) = self.get_piece(pos) {
                    if piece.color == attacker_color {
                        let pt = piece.get_movement_type();
                        if !found_screen && pt == PieceType::Rook {
                            return true;
                        }
                        if found_screen && pt == PieceType::Cannon {
                            return true;
                        }
                        // 将的飞将检查
                        if !found_screen && pt == PieceType::King {
                            return true;
                        }
                    }
                    found_screen = true;
                }
                pos = pos.offset(dr, dc);
            }
        }

        // 检查马攻击
        let horse_attacks: [((i8, i8), (i8, i8)); 8] = [
            ((2, 1), (1, 0)),
            ((2, -1), (1, 0)),
            ((-2, 1), (-1, 0)),
            ((-2, -1), (-1, 0)),
            ((1, 2), (0, 1)),
            ((1, -2), (0, -1)),
            ((-1, 2), (0, 1)),
            ((-1, -2), (0, -1)),
        ];
        for ((dr, dc), (lr, lc)) in horse_attacks {
            let horse_pos = target_pos.offset(dr, dc);
            let leg_pos = target_pos.offset(lr, lc);
            if let Some(piece) = self.get_piece(horse_pos) {
                if piece.color == attacker_color
                    && piece.get_movement_type() == PieceType::Horse
                    && !self.has_piece(leg_pos)
                {
                    return true;
                }
            }
        }

        // 检查兵攻击
        let pawn_attacks: [(i8, i8); 3] = if attacker_color == Color::Red {
            // 红兵可以从下方或左右攻击
            [(-1, 0), (0, -1), (0, 1)]
        } else {
            // 黑卒可以从上方或左右攻击
            [(1, 0), (0, -1), (0, 1)]
        };
        for (dr, dc) in pawn_attacks {
            let pawn_pos = target_pos.offset(dr, dc);
            if let Some(piece) = self.get_piece(pawn_pos) {
                if piece.color == attacker_color && piece.get_movement_type() == PieceType::Pawn {
                    // 检查兵是否真的能攻击到这里
                    let is_red = piece.color == Color::Red;
                    let crossed = if is_red {
                        piece.position.row >= 5
                    } else {
                        piece.position.row <= 4
                    };
                    // 前进方向攻击总是可以
                    let forward = if is_red { 1 } else { -1 };
                    if dr == -forward {
                        return true;
                    }
                    // 左右攻击只有过河后才行
                    if crossed && dc != 0 {
                        return true;
                    }
                }
            }
        }

        false
    }

    /// 检测将是否被攻击（使用优化版）
    #[inline]
    pub fn is_king_attacked(&self, king_pos: Position, king_color: Color) -> bool {
        self.is_position_attacked(king_pos, king_color.opposite())
    }

    /// 获取所有合法走法（优化版：不克隆棋盘）
    pub fn get_legal_moves(&self, color: Color) -> Vec<JieqiMove> {
        // 使用 unsafe 来绕过借用检查，避免 clone
        // 这是安全的，因为我们会正确地 undo_move
        let board_ptr = self as *const Board as *mut Board;
        unsafe { (*board_ptr).get_legal_moves_mut(color) }
    }

    /// 获取所有合法走法（可变版本）
    fn get_legal_moves_mut(&mut self, color: Color) -> Vec<JieqiMove> {
        let mut moves = Vec::with_capacity(50);

        let king_pos = match self.find_king(color) {
            Some(pos) => pos,
            None => return moves,
        };

        // 收集我方棋子信息（避免借用冲突）
        let my_pieces: Vec<(Position, bool, PieceType)> = self
            .squares
            .iter()
            .filter_map(|p| p.as_ref())
            .filter(|p| p.color == color)
            .map(|p| (p.position, p.is_hidden, p.get_movement_type()))
            .collect();

        for (from_pos, is_hidden, movement_type) in my_pieces {
            let action_type = if is_hidden {
                ActionType::RevealAndMove
            } else {
                ActionType::Move
            };
            let is_king = movement_type == PieceType::King;

            // 获取潜在走法
            let potential_moves = if let Some(p) = self.get_piece(from_pos) {
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

                let in_check = self.is_position_attacked(check_king_pos, color.opposite());

                self.undo_move(&mv, captured, is_hidden);

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
                match self.current_turn {
                    Color::Red => GameResult::BlackWin,
                    Color::Black => GameResult::RedWin,
                }
            } else {
                GameResult::Draw
            }
        } else {
            GameResult::Ongoing
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

        // 检查是否有飞将的走法
        let fly_move = moves
            .iter()
            .find(|m| m.to_pos == Position::new(9, 4))
            .is_some();
        assert!(fly_move, "Should have flying general move");
    }

    #[test]
    fn test_position_index() {
        // 测试位置索引转换
        for row in 0..10 {
            for col in 0..9 {
                let pos = Position::new(row, col);
                let idx = pos.to_index();
                let restored = Position::from_index(idx);
                assert_eq!(pos, restored);
            }
        }
    }
}
