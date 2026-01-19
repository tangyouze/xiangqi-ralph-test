//! 详细分析 e 列上的棋子

use xiangqi_ai::{Board, Color, Position};

fn main() {
    // 揭棋初始局面（将帅已揭）
    let fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";

    let mut board = Board::from_fen(fen).unwrap();

    println!("=== 开局 e 列分析 ===\n");

    // 显示 e 列的所有棋子
    for row in (0..=9).rev() {
        let pos = Position::new(row, 4); // e 列 = col 4
        if let Some(piece) = board.get_piece(pos) {
            println!(
                "e{}: {:?} 方 {} 棋子 (movement: {:?})",
                row,
                piece.color,
                if piece.is_hidden { "暗" } else { "明" },
                piece.movement_type
            );
        } else {
            println!("e{}: 空", row);
        }
    }

    println!("\n=== 执行 +b2e2 后 ===\n");

    // 执行走法
    let (mv, _) = xiangqi_ai::JieqiMove::from_fen_str("+b2e2").unwrap();
    board.make_move(&mv);

    // 再次显示 e 列
    for row in (0..=9).rev() {
        let pos = Position::new(row, 4);
        if let Some(piece) = board.get_piece(pos) {
            let type_str = if piece.is_hidden {
                format!("{:?} 暗子", piece.movement_type.unwrap())
            } else {
                format!("{:?} 明子", piece.actual_type.unwrap())
            };
            println!("e{}: {:?} 方 {}", row, piece.color, type_str);
        } else {
            println!("e{}: 空", row);
        }
    }

    println!("\n=== 炮的攻击分析 ===\n");

    // 炮在 e2，看看能攻击哪些位置
    if let Some(cannon) = board.get_piece(Position::new(2, 4)) {
        let attacks = board.get_potential_moves(cannon);
        println!("炮在 e2 可以移动/攻击的位置:");
        for pos in attacks {
            println!("  - {}{}", (b'a' + pos.col as u8) as char, pos.row);
        }
    }
}
