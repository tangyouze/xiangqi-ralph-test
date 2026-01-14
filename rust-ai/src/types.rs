//! 揭棋核心类型定义
//!
//! 定义揭棋中所有基础数据类型

use std::fmt;

/// 棋子颜色/阵营
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Color {
    Red,
    Black,
}

impl Color {
    /// 获取对方阵营
    pub fn opposite(&self) -> Color {
        match self {
            Color::Red => Color::Black,
            Color::Black => Color::Red,
        }
    }

    /// 从 FEN 字符解析
    pub fn from_fen_char(c: char) -> Option<Color> {
        match c {
            'r' => Some(Color::Red),
            'b' => Some(Color::Black),
            _ => None,
        }
    }

    /// 转换为 FEN 字符
    pub fn to_fen_char(&self) -> char {
        match self {
            Color::Red => 'r',
            Color::Black => 'b',
        }
    }
}

impl fmt::Display for Color {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Color::Red => write!(f, "Red"),
            Color::Black => write!(f, "Black"),
        }
    }
}

/// 棋子类型
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PieceType {
    /// 将/帅
    King,
    /// 士/仕
    Advisor,
    /// 象/相
    Elephant,
    /// 马
    Horse,
    /// 车
    Rook,
    /// 炮
    Cannon,
    /// 卒/兵
    Pawn,
}

impl PieceType {
    /// 从 FEN 字符解析（小写）
    pub fn from_fen_char(c: char) -> Option<PieceType> {
        match c.to_ascii_lowercase() {
            'k' => Some(PieceType::King),
            'a' => Some(PieceType::Advisor),
            'e' => Some(PieceType::Elephant),
            'h' => Some(PieceType::Horse),
            'r' => Some(PieceType::Rook),
            'c' => Some(PieceType::Cannon),
            'p' => Some(PieceType::Pawn),
            _ => None,
        }
    }

    /// 转换为 FEN 字符（小写）
    pub fn to_fen_char(&self) -> char {
        match self {
            PieceType::King => 'k',
            PieceType::Advisor => 'a',
            PieceType::Elephant => 'e',
            PieceType::Horse => 'h',
            PieceType::Rook => 'r',
            PieceType::Cannon => 'c',
            PieceType::Pawn => 'p',
        }
    }

    /// 获取棋子的评估值
    pub fn value(&self) -> i32 {
        match self {
            PieceType::King => 100000,
            PieceType::Rook => 900,
            PieceType::Cannon => 450,
            PieceType::Horse => 400,
            PieceType::Elephant => 200,
            PieceType::Advisor => 200,
            PieceType::Pawn => 100,
        }
    }
}

impl fmt::Display for PieceType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let name = match self {
            PieceType::King => "King",
            PieceType::Advisor => "Advisor",
            PieceType::Elephant => "Elephant",
            PieceType::Horse => "Horse",
            PieceType::Rook => "Rook",
            PieceType::Cannon => "Cannon",
            PieceType::Pawn => "Pawn",
        };
        write!(f, "{}", name)
    }
}

/// 棋盘位置 (row, col)
///
/// row: 0-9 (0 是红方底线，9 是黑方底线)
/// col: 0-8 (从左到右)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Position {
    pub row: i8,
    pub col: i8,
}

impl Position {
    pub fn new(row: i8, col: i8) -> Self {
        Position { row, col }
    }

    /// 检查位置是否在棋盘范围内
    pub fn is_valid(&self) -> bool {
        (0..=9).contains(&self.row) && (0..=8).contains(&self.col)
    }

    /// 检查位置是否在九宫格内
    pub fn is_in_palace(&self, color: Color) -> bool {
        if !(3..=5).contains(&self.col) {
            return false;
        }
        match color {
            Color::Red => (0..=2).contains(&self.row),
            Color::Black => (7..=9).contains(&self.row),
        }
    }

    /// 检查位置是否在己方半场
    pub fn is_on_own_side(&self, color: Color) -> bool {
        match color {
            Color::Red => (0..=4).contains(&self.row),
            Color::Black => (5..=9).contains(&self.row),
        }
    }

    /// 位置加偏移量
    pub fn offset(&self, row_delta: i8, col_delta: i8) -> Position {
        Position {
            row: self.row + row_delta,
            col: self.col + col_delta,
        }
    }

    /// 从 FEN 坐标解析（如 "a0"）
    pub fn from_fen_str(s: &str) -> Option<Position> {
        if s.len() != 2 {
            return None;
        }
        let chars: Vec<char> = s.chars().collect();
        let col = match chars[0] {
            'a'..='i' => (chars[0] as i8) - ('a' as i8),
            _ => return None,
        };
        let row = match chars[1] {
            '0'..='9' => (chars[1] as i8) - ('0' as i8),
            _ => return None,
        };
        Some(Position { row, col })
    }

    /// 转换为 FEN 坐标（如 "a0"）
    pub fn to_fen_str(&self) -> String {
        let col_char = (b'a' + self.col as u8) as char;
        format!("{}{}", col_char, self.row)
    }
}

impl fmt::Display for Position {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.to_fen_str())
    }
}

/// 动作类型
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ActionType {
    /// 揭子并走棋
    RevealAndMove,
    /// 明子走棋
    Move,
}

/// 揭棋走法
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct JieqiMove {
    pub action_type: ActionType,
    pub from_pos: Position,
    pub to_pos: Position,
}

impl JieqiMove {
    /// 创建普通走法
    pub fn regular_move(from: Position, to: Position) -> Self {
        JieqiMove {
            action_type: ActionType::Move,
            from_pos: from,
            to_pos: to,
        }
    }

    /// 创建揭子走法
    pub fn reveal_move(from: Position, to: Position) -> Self {
        JieqiMove {
            action_type: ActionType::RevealAndMove,
            from_pos: from,
            to_pos: to,
        }
    }

    /// 从 FEN 走法字符串解析
    ///
    /// 格式：
    /// - 明子走法：`a0a1`
    /// - 揭子走法：`+a0a1`
    /// - 揭子走法执行后：`+a0a1=R`
    pub fn from_fen_str(s: &str) -> Option<(JieqiMove, Option<PieceType>)> {
        let mut s = s.trim();
        let mut revealed_type = None;

        // 检查是否有揭示结果
        if let Some(idx) = s.find('=') {
            let type_char = s.chars().nth(idx + 1)?;
            revealed_type = PieceType::from_fen_char(type_char);
            s = &s[..idx];
        }

        // 检查是否是揭子走法
        let action_type = if s.starts_with('+') {
            s = &s[1..];
            ActionType::RevealAndMove
        } else {
            ActionType::Move
        };

        // 解析坐标：a0a1 格式
        if s.len() != 4 {
            return None;
        }

        let from_pos = Position::from_fen_str(&s[0..2])?;
        let to_pos = Position::from_fen_str(&s[2..4])?;

        Some((
            JieqiMove {
                action_type,
                from_pos,
                to_pos,
            },
            revealed_type,
        ))
    }

    /// 转换为 FEN 走法字符串
    pub fn to_fen_str(&self, revealed_type: Option<PieceType>) -> String {
        let prefix = match self.action_type {
            ActionType::RevealAndMove => "+",
            ActionType::Move => "",
        };

        let suffix = match revealed_type {
            Some(pt) => format!("={}", pt.to_fen_char().to_ascii_uppercase()),
            None => String::new(),
        };

        format!(
            "{}{}{}{}",
            prefix,
            self.from_pos.to_fen_str(),
            self.to_pos.to_fen_str(),
            suffix
        )
    }
}

impl fmt::Display for JieqiMove {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.to_fen_str(None))
    }
}

/// 游戏结果
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameResult {
    Ongoing,
    RedWin,
    BlackWin,
    Draw,
}

/// 根据位置获取该位置对应的棋子类型（用于暗子的走法规则）
pub fn get_position_piece_type(pos: Position) -> Option<PieceType> {
    // 红方底线 (row 0)
    if pos.row == 0 {
        return match pos.col {
            0 | 8 => Some(PieceType::Rook),
            1 | 7 => Some(PieceType::Horse),
            2 | 6 => Some(PieceType::Elephant),
            3 | 5 => Some(PieceType::Advisor),
            4 => Some(PieceType::King),
            _ => None,
        };
    }
    // 红方炮位 (row 2)
    if pos.row == 2 && (pos.col == 1 || pos.col == 7) {
        return Some(PieceType::Cannon);
    }
    // 红方兵位 (row 3)
    if pos.row == 3 && pos.col % 2 == 0 {
        return Some(PieceType::Pawn);
    }
    // 黑方底线 (row 9)
    if pos.row == 9 {
        return match pos.col {
            0 | 8 => Some(PieceType::Rook),
            1 | 7 => Some(PieceType::Horse),
            2 | 6 => Some(PieceType::Elephant),
            3 | 5 => Some(PieceType::Advisor),
            4 => Some(PieceType::King),
            _ => None,
        };
    }
    // 黑方炮位 (row 7)
    if pos.row == 7 && (pos.col == 1 || pos.col == 7) {
        return Some(PieceType::Cannon);
    }
    // 黑方卒位 (row 6)
    if pos.row == 6 && pos.col % 2 == 0 {
        return Some(PieceType::Pawn);
    }
    None
}

/// 暗子的期望价值（用于评估）
pub const HIDDEN_PIECE_VALUE: i32 = 320;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_position_from_fen_str() {
        assert_eq!(Position::from_fen_str("a0"), Some(Position::new(0, 0)));
        assert_eq!(Position::from_fen_str("e4"), Some(Position::new(4, 4)));
        assert_eq!(Position::from_fen_str("i9"), Some(Position::new(9, 8)));
        assert_eq!(Position::from_fen_str("j0"), None);
    }

    #[test]
    fn test_position_to_fen_str() {
        assert_eq!(Position::new(0, 0).to_fen_str(), "a0");
        assert_eq!(Position::new(4, 4).to_fen_str(), "e4");
        assert_eq!(Position::new(9, 8).to_fen_str(), "i9");
    }

    #[test]
    fn test_move_from_fen_str() {
        let (m, rt) = JieqiMove::from_fen_str("a0a1").unwrap();
        assert_eq!(m.action_type, ActionType::Move);
        assert_eq!(m.from_pos, Position::new(0, 0));
        assert_eq!(m.to_pos, Position::new(1, 0));
        assert!(rt.is_none());

        let (m, rt) = JieqiMove::from_fen_str("+e3e4").unwrap();
        assert_eq!(m.action_type, ActionType::RevealAndMove);
        assert!(rt.is_none());

        let (m, rt) = JieqiMove::from_fen_str("+e3e4=R").unwrap();
        assert_eq!(m.action_type, ActionType::RevealAndMove);
        assert_eq!(rt, Some(PieceType::Rook));
    }

    #[test]
    fn test_position_piece_type() {
        // 红方底线
        assert_eq!(
            get_position_piece_type(Position::new(0, 0)),
            Some(PieceType::Rook)
        );
        assert_eq!(
            get_position_piece_type(Position::new(0, 4)),
            Some(PieceType::King)
        );
        // 红方炮位
        assert_eq!(
            get_position_piece_type(Position::new(2, 1)),
            Some(PieceType::Cannon)
        );
        // 红方兵位
        assert_eq!(
            get_position_piece_type(Position::new(3, 0)),
            Some(PieceType::Pawn)
        );
        // 黑方底线
        assert_eq!(
            get_position_piece_type(Position::new(9, 4)),
            Some(PieceType::King)
        );
        // 空位
        assert_eq!(get_position_piece_type(Position::new(4, 4)), None);
    }
}
