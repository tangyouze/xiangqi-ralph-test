//! 开局2步分数分析
//!
//! 红方走1步 → 黑方走1步 → 评估分数

use rand::prelude::*;
use std::collections::HashMap;
use xiangqi_ai::{Board, Color, IT2AI};

fn main() {
    let opening_fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";

    println!("═══════════════════════════════════════════════");
    println!("开局2步分数分析（红1步→黑1步，采样500次）");
    println!("═══════════════════════════════════════════════\n");

    let board = Board::from_fen(opening_fen).unwrap();
    let opening_score = IT2AI::evaluate_static(&board, Color::Red);
    println!("开局评估（红方视角）: {:.2}\n", opening_score);

    let red_moves = board.get_legal_moves(Color::Red);
    println!("红方合法走法: {}\n", red_moves.len());

    let mut rng = rand::thread_rng();
    let sample_size = 500;

    println!("开始随机采样 {} 次（红1步+黑1步）...\n", sample_size);

    let mut scores = Vec::new();
    let mut piece_scores: HashMap<String, Vec<f64>> = HashMap::new();

    for _ in 0..sample_size {
        // 红方随机走一步
        let red_move = red_moves.choose(&mut rng).unwrap();
        let mut board_after_red = board.clone();

        let red_piece = board_after_red.get_piece(red_move.from_pos).unwrap();
        let red_type = red_piece.movement_type.unwrap();

        board_after_red.make_move(red_move);

        // 黑方随机走一步
        let black_moves = board_after_red.get_legal_moves(Color::Black);
        if black_moves.is_empty() {
            continue;
        }

        let black_move = black_moves.choose(&mut rng).unwrap();
        board_after_red.make_move(black_move);

        // 轮到红方，从红方视角评估
        let score = IT2AI::evaluate_static(&board_after_red, Color::Red);

        scores.push(score);

        let key = format!("{:?}", red_type);
        piece_scores.entry(key).or_insert_with(Vec::new).push(score);
    }

    if scores.is_empty() {
        println!("没有有效的采样结果");
        return;
    }

    scores.sort_by(|a, b| a.partial_cmp(b).unwrap());

    println!("═══════════════════════════════════════════════");
    println!("统计结果（2步后）");
    println!("═══════════════════════════════════════════════\n");

    println!("分数范围:");
    println!("  最小: {:.2}", scores[0]);
    println!("  最大: {:.2}", scores[scores.len() - 1]);
    println!("  中位数: {:.2}", scores[scores.len() / 2]);
    println!(
        "  平均: {:.2}",
        scores.iter().sum::<f64>() / scores.len() as f64
    );
    println!("  范围: {:.2}\n", scores[scores.len() - 1] - scores[0]);

    // 分数分布
    println!("分数分布:");
    let ranges = [
        (-2000.0, -1000.0, "巨大劣势"),
        (-1000.0, -500.0, "严重劣势"),
        (-500.0, -300.0, "明显劣势"),
        (-300.0, -100.0, "小劣"),
        (-100.0, 0.0, "略劣"),
        (0.0, 100.0, "略优"),
        (100.0, 300.0, "小优"),
        (300.0, 500.0, "明显优势"),
        (500.0, 1000.0, "严重优势"),
        (1000.0, 2000.0, "巨大优势"),
    ];

    for (low, high, label) in ranges {
        let count = scores.iter().filter(|&&s| s >= low && s < high).count();
        if count > 0 {
            let pct = count as f64 / scores.len() as f64 * 100.0;
            println!(
                "  [{:>6.0}, {:>6.0}) {}: {:>4} ({:>5.1}%)",
                low, high, label, count, pct
            );
        }
    }

    // 按红方第一步棋子类型统计
    println!("\n按红方第一步棋子类型统计:");
    let mut piece_stats: Vec<_> = piece_scores
        .iter()
        .map(|(piece, scores_vec)| {
            let avg = scores_vec.iter().sum::<f64>() / scores_vec.len() as f64;
            let min = scores_vec.iter().cloned().fold(f64::INFINITY, f64::min);
            let max = scores_vec.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
            (piece.clone(), scores_vec.len(), avg, min, max)
        })
        .collect();
    piece_stats.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap());

    for (piece, count, avg, min, max) in piece_stats {
        println!(
            "  {:<8} - {} 次 | 平均: {:>7.2} | 最小: {:>7.2} | 最大: {:>7.2}",
            piece, count, avg, min, max
        );
    }
}
