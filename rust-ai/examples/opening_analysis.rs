//! 开局走法分数范围分析（过滤吃将局面）

use std::collections::HashMap;
use xiangqi_ai::{Board, MinimaxAI, AIEngine, AIConfig, Color};

fn main() {
    let opening_fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r";
    
    println!("═══════════════════════════════════════════════");
    println!("开局分数范围分析（过滤吃将局面）");
    println!("═══════════════════════════════════════════════");
    println!("开局 FEN: {}", opening_fen);
    println!();
    
    for depth in 1..=4 {
        let (min_score, max_score, count, normal_count) = analyze_depth(opening_fen, depth, 10);
        
        println!("深度 {}:", depth);
        println!("  总局面数: {}", count);
        println!("  正常局面: {} ({:.1}%)", normal_count, normal_count as f64 / count as f64 * 100.0);
        println!("  最大分数: {:.2}", max_score);
        println!("  最小分数: {:.2}", min_score);
        println!("  分数范围: {:.2}", max_score - min_score);
        println!();
    }
}

fn analyze_depth(fen: &str, depth: u32, branch_factor: usize) -> (f64, f64, usize, usize) {
    let mut min_score = f64::INFINITY;
    let mut max_score = f64::NEG_INFINITY;
    let mut count = 0;
    let mut normal_count = 0; // 非吃将局面
    
    let mut positions_to_explore = vec![(fen.to_string(), depth)];
    let mut visited: HashMap<String, f64> = HashMap::new();
    
    while let Some((current_fen, remaining_depth)) = positions_to_explore.pop() {
        if visited.contains_key(&current_fen) {
            continue;
        }
        
        let board = match Board::from_fen(&current_fen) {
            Ok(b) => b,
            Err(_) => continue,
        };
        
        let current_color = board.current_turn();
        
        if remaining_depth == 0 {
            // 检查是否还有两个将
            let has_both_kings = board.find_king(Color::Red).is_some() 
                && board.find_king(Color::Black).is_some();
            
            let score = MinimaxAI::evaluate_static(&board, current_color);
            visited.insert(current_fen.clone(), score);
            
            if has_both_kings {
                // 只统计正常局面（双将还在）
                min_score = min_score.min(score);
                max_score = max_score.max(score);
                normal_count += 1;
            }
            
            count += 1;
            
            if count % 1000 == 0 {
                print!("\r  已评估: {} 个局面...", count);
                use std::io::Write;
                std::io::stdout().flush().unwrap();
            }
        } else {
            let config = AIConfig {
                depth: 1,
                randomness: 0.0,
                seed: None,
                time_limit: None,
            };
            
            let ai = AIEngine::minimax(&config);
            
            match ai.select_moves_fen(&current_fen, branch_factor) {
                Ok(moves) => {
                    for (move_str, _score) in moves {
                        if let Ok(new_fen) = apply_move(&current_fen, &move_str) {
                            positions_to_explore.push((new_fen, remaining_depth - 1));
                        }
                    }
                }
                Err(_) => continue,
            }
        }
    }
    
    if count > 0 {
        println!("\r  已评估: {} 个局面 ✓    ", count);
    }
    
    (min_score, max_score, count, normal_count)
}

fn apply_move(fen: &str, move_str: &str) -> Result<String, String> {
    use xiangqi_ai::apply_move_to_fen;
    apply_move_to_fen(fen, move_str, None)
}
