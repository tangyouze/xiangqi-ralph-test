//! 生成走法后的FEN

use xiangqi_ai::{apply_move_to_fen, get_legal_moves_from_fen};

fn main() {
    // 揭棋初始局面（将帅已揭）
    let start = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";
    
    println!("开局FEN:");
    println!("{}", start);
    println!();
    
    match apply_move_to_fen(start, "+b2e2", None) {
        Ok(new_fen) => {
            println!("走 +b2e2 后的FEN:");
            println!("{}", new_fen);
            println!();
            
            // 检查黑方合法走法
            match get_legal_moves_from_fen(&new_fen) {
                Ok(moves) => {
                    println!("黑方合法走法数量: {}", moves.len());
                    if moves.len() <= 20 {
                        println!("所有走法:");
                        for (i, m) in moves.iter().enumerate() {
                            println!("  {}. {}", i+1, m);
                        }
                    } else {
                        println!("前20个走法:");
                        for (i, m) in moves.iter().take(20).enumerate() {
                            println!("  {}. {}", i+1, m);
                        }
                        println!("  ... 还有 {} 个", moves.len() - 20);
                    }
                }
                Err(e) => println!("获取走法错误: {}", e),
            }
        }
        Err(e) => {
            eprintln!("生成FEN错误: {}", e);
        }
    }
}
