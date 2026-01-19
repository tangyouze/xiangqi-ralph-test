//! 调试黑方无合法走法的问题

use xiangqi_ai::{Board, Color, Position};

fn main() {
    // 中局局面（将帅已揭，红炮在 e2）
    let fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/4C2X1/9/XXXXKXXXX -:- b r";

    println!("FEN: {}", fen);
    println!();

    let board = Board::from_fen(fen).unwrap();

    // 检查黑方是否被将军
    let black_king_pos = board.find_king(Color::Black);
    println!("黑将位置: {:?}", black_king_pos);

    let is_in_check = board.is_in_check(Color::Black);
    println!("黑方是否被将军: {}", is_in_check);
    println!();

    // 获取黑方所有棋子
    let black_pieces = board.get_all_pieces(Some(Color::Black));
    println!("黑方棋子数: {}", black_pieces.len());
    println!();

    // 尝试获取每个棋子的潜在走法
    println!("每个黑方棋子的潜在走法:");
    for (i, piece) in black_pieces.iter().enumerate().take(5) {
        let potential = board.get_potential_moves(piece);
        println!(
            "  棋子{} at {}{} ({:?}): {} 个潜在走法",
            i + 1,
            (b'a' + piece.position.col as u8) as char,
            piece.position.row,
            piece.movement_type,
            potential.len()
        );
        if potential.len() > 0 && potential.len() <= 5 {
            for p in potential {
                print!("    {}{}", (b'a' + p.col as u8) as char, p.row);
            }
            println!();
        }
    }
    println!();

    // 获取合法走法（会过滤掉导致被将军的走法）
    let legal_moves = board.get_legal_moves(Color::Black);
    println!("合法走法数: {}", legal_moves.len());

    // 检查炮的攻击范围
    println!("\n红炮在 e2 的攻击分析:");
    if let Some(cannon) = board.get_piece(Position::new(2, 4)) {
        println!("  炮的颜色: {:?}", cannon.color);
        println!("  炮的类型: {:?}", cannon.actual_type);

        // 检查炮是否能攻击黑将
        if let Some(king_pos) = black_king_pos {
            let is_attacked = board.is_position_attacked(king_pos, Color::Red);
            println!(
                "  炮是否攻击到黑将 ({}{}): {}",
                (b'a' + king_pos.col as u8) as char,
                king_pos.row,
                is_attacked
            );
        }
    }
}
