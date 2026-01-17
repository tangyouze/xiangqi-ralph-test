//! FEN 解析和生成
//!
//! 揭棋玩家视角 FEN (JFN v2)
//!
//! 格式: `<棋盘> <被吃子> <回合> <视角>`
//!
//! 棋盘符号：
//! - 红方明子：K(将) R(车) H(马) C(炮) E(象) A(士) P(兵)
//! - 黑方明子：k r h c e a p
//! - 红方暗子：X
//! - 黑方暗子：x
//! - 空格：数字 (1-9)

use crate::types::{get_position_piece_type, ActionType, Color, JieqiMove, PieceType, Position};

/// FEN 中的棋子（玩家视角）
#[derive(Debug, Clone)]
pub struct FenPiece {
    pub position: Position,
    pub color: Color,
    pub is_hidden: bool,
    /// 棋子类型，None 表示暗子（身份未知）
    pub piece_type: Option<PieceType>,
}

/// 被吃棋子信息
#[derive(Debug, Clone)]
pub struct CapturedPieceInfo {
    /// 棋子类型，None 表示未知
    pub piece_type: Option<PieceType>,
    /// 被吃时是否为暗子
    pub was_hidden: bool,
}

/// 被吃子信息
#[derive(Debug, Clone, Default)]
pub struct CapturedInfo {
    /// 红方被吃的子
    pub red_captured: Vec<CapturedPieceInfo>,
    /// 黑方被吃的子
    pub black_captured: Vec<CapturedPieceInfo>,
}

/// FEN 解析后的状态
#[derive(Debug, Clone)]
pub struct FenState {
    pub pieces: Vec<FenPiece>,
    pub captured: CapturedInfo,
    pub turn: Color,
    pub viewer: Color,
}

/// 解析 FEN 字符串
pub fn parse_fen(fen: &str) -> Result<FenState, String> {
    let parts: Vec<&str> = fen.split_whitespace().collect();
    if parts.len() != 4 {
        return Err(format!(
            "Invalid FEN format: expected '<board> <captured> <turn> <viewer>', got: {}",
            fen
        ));
    }

    let board_str = parts[0];
    let captured_str = parts[1];
    let turn_str = parts[2];
    let viewer_str = parts[3];

    let pieces = parse_board(board_str)?;
    let captured = parse_captured(captured_str)?;
    let turn = Color::from_fen_char(turn_str.chars().next().unwrap_or('r'))
        .ok_or_else(|| format!("Invalid turn: {}", turn_str))?;
    let viewer = Color::from_fen_char(viewer_str.chars().next().unwrap_or('r'))
        .ok_or_else(|| format!("Invalid viewer: {}", viewer_str))?;

    Ok(FenState {
        pieces,
        captured,
        turn,
        viewer,
    })
}

/// 解析棋盘字符串
fn parse_board(board_str: &str) -> Result<Vec<FenPiece>, String> {
    let rows: Vec<&str> = board_str.split('/').collect();
    if rows.len() != 10 {
        return Err(format!(
            "Invalid board: expected 10 rows, got {}",
            rows.len()
        ));
    }

    let mut pieces = Vec::new();

    for (row_idx, row_str) in rows.iter().enumerate() {
        // FEN 从上往下是 row 9 到 row 0
        let row = (9 - row_idx) as i8;
        let mut col: i8 = 0;

        for ch in row_str.chars() {
            if col >= 9 {
                break;
            }

            if ch.is_ascii_digit() {
                col += (ch as i8) - ('0' as i8);
            } else if ch == 'X' {
                // 红方暗子
                pieces.push(FenPiece {
                    position: Position::new(row, col),
                    color: Color::Red,
                    is_hidden: true,
                    piece_type: None,
                });
                col += 1;
            } else if ch == 'x' {
                // 黑方暗子
                pieces.push(FenPiece {
                    position: Position::new(row, col),
                    color: Color::Black,
                    is_hidden: true,
                    piece_type: None,
                });
                col += 1;
            } else if ch.is_ascii_alphabetic() {
                // 明子
                let piece_type = PieceType::from_fen_char(ch)
                    .ok_or_else(|| format!("Invalid piece char: {}", ch))?;
                let color = if ch.is_ascii_uppercase() {
                    Color::Red
                } else {
                    Color::Black
                };
                pieces.push(FenPiece {
                    position: Position::new(row, col),
                    color,
                    is_hidden: false,
                    piece_type: Some(piece_type),
                });
                col += 1;
            } else {
                return Err(format!("Invalid character in board: {}", ch));
            }
        }

        if col != 9 {
            return Err(format!("Row {} has {} columns, expected 9", row, col));
        }
    }

    Ok(pieces)
}

/// 解析被吃子字符串
fn parse_captured(captured_str: &str) -> Result<CapturedInfo, String> {
    let parts: Vec<&str> = captured_str.split(':').collect();
    if parts.len() != 2 {
        return Err(format!("Invalid captured format: {}", captured_str));
    }

    let red_str = parts[0];
    let black_str = parts[1];
    let mut info = CapturedInfo::default();

    // 解析红方被吃
    if red_str != "-" {
        for ch in red_str.chars() {
            if ch == '?' {
                info.red_captured.push(CapturedPieceInfo {
                    piece_type: None,
                    was_hidden: true,
                });
            } else {
                let piece_type = PieceType::from_fen_char(ch)
                    .ok_or_else(|| format!("Invalid captured piece: {}", ch))?;
                let was_hidden = ch.is_ascii_lowercase();
                info.red_captured.push(CapturedPieceInfo {
                    piece_type: Some(piece_type),
                    was_hidden,
                });
            }
        }
    }

    // 解析黑方被吃
    if black_str != "-" {
        for ch in black_str.chars() {
            if ch == '?' {
                info.black_captured.push(CapturedPieceInfo {
                    piece_type: None,
                    was_hidden: true,
                });
            } else {
                let piece_type = PieceType::from_fen_char(ch)
                    .ok_or_else(|| format!("Invalid captured piece: {}", ch))?;
                let was_hidden = ch.is_ascii_lowercase();
                info.black_captured.push(CapturedPieceInfo {
                    piece_type: Some(piece_type),
                    was_hidden,
                });
            }
        }
    }

    Ok(info)
}

/// 从棋子列表生成 FEN 字符串
#[allow(clippy::needless_range_loop)]
pub fn pieces_to_fen(
    pieces: &[FenPiece],
    captured: &CapturedInfo,
    turn: Color,
    viewer: Color,
) -> String {
    // 构建 10x9 的棋盘
    let mut board: [[Option<&FenPiece>; 9]; 10] = [[None; 9]; 10];
    for piece in pieces {
        let row = piece.position.row as usize;
        let col = piece.position.col as usize;
        if row < 10 && col < 9 {
            board[row][col] = Some(piece);
        }
    }

    let mut rows = Vec::new();

    // 从 row 9 到 row 0
    for row in (0..10).rev() {
        let mut row_str = String::new();
        let mut empty_count = 0;

        for col in 0..9 {
            if let Some(piece) = board[row][col] {
                if empty_count > 0 {
                    row_str.push_str(&empty_count.to_string());
                    empty_count = 0;
                }

                if piece.is_hidden {
                    row_str.push(match piece.color {
                        Color::Red => 'X',
                        Color::Black => 'x',
                    });
                } else if let Some(pt) = piece.piece_type {
                    let ch = pt.to_fen_char();
                    row_str.push(match piece.color {
                        Color::Red => ch.to_ascii_uppercase(),
                        Color::Black => ch,
                    });
                }
            } else {
                empty_count += 1;
            }
        }

        if empty_count > 0 {
            row_str.push_str(&empty_count.to_string());
        }

        rows.push(row_str);
    }

    let board_str = rows.join("/");

    // 被吃子字符串
    // 红方被吃 = 红子 = 大写; 黑方被吃 = 黑子 = 小写
    let red_captured_str = if captured.red_captured.is_empty() {
        "-".to_string()
    } else {
        captured
            .red_captured
            .iter()
            .map(|c| {
                if let Some(pt) = c.piece_type {
                    pt.to_fen_char().to_ascii_uppercase() // 红子始终大写
                } else {
                    '?'
                }
            })
            .collect()
    };

    let black_captured_str = if captured.black_captured.is_empty() {
        "-".to_string()
    } else {
        captured
            .black_captured
            .iter()
            .map(|c| {
                if let Some(pt) = c.piece_type {
                    pt.to_fen_char() // 黑子始终小写 (to_fen_char 返回小写)
                } else {
                    '?'
                }
            })
            .collect()
    };

    let captured_str = format!("{}:{}", red_captured_str, black_captured_str);

    format!(
        "{} {} {} {}",
        board_str,
        captured_str,
        turn.to_fen_char(),
        viewer.to_fen_char()
    )
}

/// 在 FEN 上执行走法，返回新的 FEN
pub fn apply_move_to_fen(
    fen: &str,
    move_str: &str,
    revealed_type: Option<PieceType>,
) -> Result<String, String> {
    let state = parse_fen(fen)?;
    let (mv, _) = JieqiMove::from_fen_str(move_str)
        .ok_or_else(|| format!("Invalid move string: {}", move_str))?;

    // 更新棋盘
    let mut new_pieces = Vec::new();
    let mut moved_piece: Option<FenPiece> = None;
    let mut captured_piece: Option<FenPiece> = None;

    for fp in state.pieces {
        if fp.position == mv.from_pos {
            moved_piece = Some(fp);
        } else if fp.position == mv.to_pos {
            captured_piece = Some(fp);
        } else {
            new_pieces.push(fp);
        }
    }

    let mut moved_piece = moved_piece.ok_or_else(|| format!("No piece at {:?}", mv.from_pos))?;

    // 处理揭子
    if mv.action_type == ActionType::RevealAndMove {
        moved_piece.is_hidden = false;
        if let Some(rt) = revealed_type {
            moved_piece.piece_type = Some(rt);
        } else {
            // 使用位置类型
            let pos_type = get_position_piece_type(mv.from_pos);
            moved_piece.piece_type = pos_type;
        }
    }

    moved_piece.position = mv.to_pos;
    new_pieces.push(moved_piece);

    // 更新被吃子信息
    let mut new_captured = state.captured;
    if let Some(cap) = captured_piece {
        let cap_info = CapturedPieceInfo {
            piece_type: cap.piece_type,
            was_hidden: cap.is_hidden,
        };
        match cap.color {
            Color::Red => new_captured.red_captured.push(cap_info),
            Color::Black => new_captured.black_captured.push(cap_info),
        }
    }

    // 切换回合
    let new_turn = state.turn.opposite();

    Ok(pieces_to_fen(
        &new_pieces,
        &new_captured,
        new_turn,
        state.viewer,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_initial_fen() {
        // 揭棋初始局面：将帅已揭，其他都是暗子
        let fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";
        let state = parse_fen(fen).unwrap();

        assert_eq!(state.pieces.len(), 32);
        assert_eq!(state.turn, Color::Red);
        assert_eq!(state.viewer, Color::Red);

        // 将帅是明子，其他都是暗子
        let mut hidden_count = 0;
        let mut king_count = 0;
        for piece in &state.pieces {
            if piece.is_hidden {
                hidden_count += 1;
                assert!(piece.piece_type.is_none());
            } else {
                king_count += 1;
                assert_eq!(piece.piece_type, Some(PieceType::King));
            }
        }
        assert_eq!(hidden_count, 30); // 30 个暗子
        assert_eq!(king_count, 2); // 2 个明将
    }

    #[test]
    fn test_parse_mid_game_fen() {
        let fen = "4k4/9/3R5/x1x3x1x/4X4/4x4/X1X3X1X/1C5C1/9/4K4 RP??:raHC r r";
        let state = parse_fen(fen).unwrap();

        assert_eq!(state.turn, Color::Red);
        assert_eq!(state.viewer, Color::Red);

        // 检查被吃子
        assert_eq!(state.captured.red_captured.len(), 4);
        assert_eq!(state.captured.black_captured.len(), 4);
    }

    #[test]
    fn test_fen_roundtrip() {
        // 揭棋初始局面
        let fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";
        let state = parse_fen(fen).unwrap();
        let regenerated = pieces_to_fen(&state.pieces, &state.captured, state.turn, state.viewer);
        assert_eq!(fen, regenerated);
    }

    #[test]
    fn test_apply_move() {
        let fen = "4k4/9/9/9/9/4R4/9/9/9/4K4 -:- r r";
        let new_fen = apply_move_to_fen(fen, "e4e5", None).unwrap();

        let state = parse_fen(&new_fen).unwrap();
        assert_eq!(state.turn, Color::Black);

        // 找车的新位置
        let rook = state
            .pieces
            .iter()
            .find(|p| p.piece_type == Some(PieceType::Rook))
            .unwrap();
        assert_eq!(rook.position, Position::new(5, 4));
    }
}
