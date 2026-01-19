//! 调试揭将问题
//!
//! 检查揭将后的局面和黑方合法走法

use xiangqi_ai::{Board, Color, MinimaxAI, PieceType};

fn main() {
    // 揭棋初始局面（将帅已揭）
    let opening_fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";

    println!("═══════════════════════════════════════════════");
    println!("调试揭将问题");
    println!("═══════════════════════════════════════════════\n");

    let board = Board::from_fen(opening_fen).unwrap();

    // 找到所有揭King的走法
    let moves = board.get_legal_moves(Color::Red);

    println!("寻找揭King的走法...\n");

    for mv in moves {
        let mut board_copy = board.clone();

        // 检查这个走法是否揭开King
        let piece_before = board_copy.get_piece(mv.from_pos).unwrap();
        let movement_type = piece_before.movement_type.unwrap();

        if movement_type == PieceType::King {
            println!("╔═══════════════════════════════════════════════╗");
            println!("║ 找到揭King走法");
            println!("╚═══════════════════════════════════════════════╝\n");

            println!("走法字符串: {}", mv.to_fen_str(None));
            println!(
                "从位置: ({}, {}) → 到位置: ({}, {})",
                mv.from_pos.row, mv.from_pos.col, mv.to_pos.row, mv.to_pos.col
            );
            println!("棋子类型(movement): {:?}", movement_type);
            println!("is_hidden: {}", piece_before.is_hidden);
            println!("actual_type: {:?}\n", piece_before.actual_type);

            // 执行走法
            board_copy.make_move(&mv);

            // 显示走法后的棋子状态
            let piece_after = board_copy.get_piece(mv.to_pos).unwrap();
            println!("走法后棋子状态:");
            println!("  is_hidden: {}", piece_after.is_hidden);
            println!("  actual_type: {:?}", piece_after.actual_type);
            println!("  movement_type: {:?}\n", piece_after.movement_type);

            // 显示棋盘上e列的所有棋子（看将的情况）
            println!("e列棋子分布:");
            for row in (0..=9).rev() {
                let pos = xiangqi_ai::Position::new(row, 4);
                if let Some(p) = board_copy.get_piece(pos) {
                    let state = if p.is_hidden { "暗" } else { "明" };
                    let ptype = if p.is_hidden {
                        format!("{:?}(movement)", p.movement_type.unwrap())
                    } else {
                        format!("{:?}(actual)", p.actual_type.unwrap())
                    };
                    println!("  e{}: {:?}方 {} {}", row, p.color, state, ptype);
                } else {
                    println!("  e{}: 空", row);
                }
            }
            println!();

            // 检查黑方走法
            let black_moves = board_copy.get_legal_moves(Color::Black);
            println!("执行后黑方合法走法数: {}", black_moves.len());

            if black_moves.len() <= 10 {
                println!("黑方合法走法:");
                for (i, m) in black_moves.iter().enumerate() {
                    println!("  {}. {}", i + 1, m.to_fen_str(None));
                }
            } else {
                println!("黑方前10个合法走法:");
                for (i, m) in black_moves.iter().take(10).enumerate() {
                    println!("  {}. {}", i + 1, m.to_fen_str(None));
                }
                println!("  ... 还有 {} 个", black_moves.len() - 10);
            }
            println!();

            // 评估分数
            let score_black = MinimaxAI::evaluate_static(&board_copy, Color::Black);
            let score_red = -score_black;
            println!("静态评估分数:");
            println!("  红方视角: {:.2}", score_red);
            println!("  黑方视角: {:.2}\n", score_black);

            // 检查游戏结果
            let result = board_copy.get_game_result(None);
            println!("游戏结果: {:?}", result);

            // 检查将的位置
            let red_king = board_copy.find_king(Color::Red);
            let black_king = board_copy.find_king(Color::Black);
            println!("红将位置: {:?}", red_king);
            println!("黑将位置: {:?}", black_king);

            println!("\n{}\n", "=".repeat(60));
        }
    }
}
