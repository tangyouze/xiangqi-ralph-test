//! 开局第一步分数分析（大规模采样）
//!
//! 随机走1000次，统计分数分布

use rand::prelude::*;
use std::collections::HashMap;
use xiangqi_ai::{Board, Color, IT2AI};

fn main() {
    // 正确的开局FEN：将/帅是明子
    let opening_fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";

    println!("═══════════════════════════════════════════════");
    println!("开局第一步静态评估分数（1000次随机采样）");
    println!("═══════════════════════════════════════════════\n");

    let board = Board::from_fen(opening_fen).unwrap();

    // 开局静态评估
    let opening_score = IT2AI::evaluate_static(&board, Color::Red);
    println!("开局局面评估（红方视角）: {:.2}\n", opening_score);

    // 获取所有合法走法
    let moves = board.get_legal_moves(Color::Red);
    println!("红方合法走法总数: {}\n", moves.len());

    // 随机采样1000次
    let mut rng = rand::thread_rng();
    let sample_size = 1000;

    println!("开始随机采样 {} 次...\n", sample_size);

    let mut scores = Vec::new();
    let mut move_scores: HashMap<String, Vec<f64>> = HashMap::new();
    let mut piece_type_scores: HashMap<String, Vec<f64>> = HashMap::new();

    for _ in 0..sample_size {
        // 随机选择一个走法
        let mv = moves.choose(&mut rng).unwrap();

        let mut board_copy = board.clone();

        // 记录揭开前的位置
        let revealed_piece = board_copy.get_piece(mv.from_pos).unwrap();
        let revealed_type = revealed_piece.movement_type.unwrap();

        board_copy.make_move(mv);

        // 从黑方视角评估（因为走完后轮到黑方）
        let score_black = IT2AI::evaluate_static(&board_copy, Color::Black);

        // 转换为红方视角（取负）
        let score_red = -score_black;

        scores.push(score_red);

        // 记录每个走法的分数
        let move_str = mv.to_fen_str(None);
        move_scores
            .entry(move_str)
            .or_insert_with(Vec::new)
            .push(score_red);

        // 记录每种棋子类型的分数
        let piece_name = format!("{:?}", revealed_type);
        piece_type_scores
            .entry(piece_name)
            .or_insert_with(Vec::new)
            .push(score_red);
    }

    // 统计
    scores.sort_by(|a, b| a.partial_cmp(b).unwrap());

    println!("═══════════════════════════════════════════════");
    println!("统计结果");
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
        (-1000.0, -500.0, "严重劣势"),
        (-500.0, -300.0, "明显劣势"),
        (-300.0, -100.0, "小劣"),
        (-100.0, 0.0, "略劣"),
        (0.0, 100.0, "略优"),
        (100.0, 300.0, "小优"),
        (300.0, 500.0, "明显优势"),
        (500.0, 1000.0, "巨大优势"),
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

    // 按棋子类型统计
    println!("\n按棋子类型统计:");
    let mut piece_stats: Vec<_> = piece_type_scores
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

    // 显示最常见的走法
    println!("\n最常见的10个走法:");
    let mut move_counts: Vec<_> = move_scores
        .iter()
        .map(|(mv, scores_vec)| {
            (
                mv.clone(),
                scores_vec.len(),
                scores_vec.iter().sum::<f64>() / scores_vec.len() as f64,
            )
        })
        .collect();
    move_counts.sort_by(|a, b| b.1.cmp(&a.1));

    for (i, (mv, count, avg_score)) in move_counts.iter().take(10).enumerate() {
        println!(
            "  {:2}. {} - {} 次 (平均分: {:.2})",
            i + 1,
            mv,
            count,
            avg_score
        );
    }
}
