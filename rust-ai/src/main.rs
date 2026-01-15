//! Xiangqi AI CLI
//!
//! 命令行界面，用于测试 AI

use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use std::time::Instant;
use xiangqi_ai::{get_legal_moves_from_fen, get_node_count, reset_node_count, AIConfig, AIEngine};

#[derive(Parser)]
#[command(name = "xiangqi-ai")]
#[command(about = "Xiangqi (Jieqi) AI Engine", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// 获取合法走法
    Moves {
        /// FEN 字符串
        #[arg(short, long)]
        fen: String,
    },

    /// 选择最佳走法
    Best {
        /// FEN 字符串
        #[arg(short, long)]
        fen: String,

        /// AI 策略 (random, greedy, minimax, iterative, mcts, positional, defensive, aggressive)
        #[arg(short, long, default_value = "greedy")]
        strategy: String,

        /// 搜索深度
        #[arg(short, long, default_value = "3")]
        depth: u32,

        /// 时间限制（秒）
        #[arg(short = 't', long)]
        time_limit: Option<f64>,

        /// 返回的走法数量
        #[arg(short, long, default_value = "1")]
        n: usize,

        /// JSON 输出
        #[arg(long)]
        json: bool,
    },

    /// 交互模式
    Play {
        /// AI 策略
        #[arg(short, long, default_value = "greedy")]
        strategy: String,

        /// 搜索深度
        #[arg(short, long, default_value = "3")]
        depth: u32,
    },
}

#[derive(Serialize, Deserialize)]
struct MoveResult {
    #[serde(rename = "move")]
    mv: String,
    score: f64,
}

#[derive(Serialize, Deserialize)]
struct MovesResponse {
    moves: Vec<MoveResult>,
    total: usize,
}

fn main() {
    env_logger::init();

    let cli = Cli::parse();

    match cli.command {
        Commands::Moves { fen } => match get_legal_moves_from_fen(&fen) {
            Ok(moves) => {
                println!("Legal moves ({}):", moves.len());
                for mv in &moves {
                    println!("  {}", mv);
                }
            }
            Err(e) => {
                eprintln!("Error: {}", e);
                std::process::exit(1);
            }
        },

        Commands::Best {
            fen,
            strategy,
            depth,
            time_limit,
            n,
            json,
        } => {
            let config = AIConfig {
                depth,
                randomness: 0.0,
                seed: None,
                time_limit,
            };

            let ai = match AIEngine::from_strategy(&strategy, &config) {
                Ok(ai) => ai,
                Err(e) => {
                    eprintln!("Error: {}", e);
                    std::process::exit(1);
                }
            };

            // 重置节点计数器
            reset_node_count();
            let start = Instant::now();

            match ai.select_moves_fen(&fen, n) {
                Ok(moves) => {
                    let elapsed = start.elapsed().as_secs_f64();
                    let nodes = get_node_count();
                    let nps = if elapsed > 0.0 {
                        nodes as f64 / elapsed
                    } else {
                        0.0
                    };

                    if json {
                        let response = MovesResponse {
                            total: moves.len(),
                            moves: moves
                                .into_iter()
                                .map(|(mv, score)| MoveResult { mv, score })
                                .collect(),
                        };
                        println!("{}", serde_json::to_string_pretty(&response).unwrap());
                        eprintln!(
                            "Stats: nodes={}, time={:.3}s, nps={:.0}",
                            nodes, elapsed, nps
                        );
                    } else {
                        println!("Best moves (strategy={}, depth={}):", strategy, depth);
                        for (mv, score) in moves {
                            println!("  {} (score: {:.2})", mv, score);
                        }
                        println!(
                            "\nStats: nodes={}, time={:.3}s, nps={:.0}",
                            nodes, elapsed, nps
                        );
                    }
                }
                Err(e) => {
                    eprintln!("Error: {}", e);
                    std::process::exit(1);
                }
            }
        }

        Commands::Play { strategy, depth } => {
            println!("Interactive mode not yet implemented.");
            println!("Strategy: {}, Depth: {}", strategy, depth);
            println!("\nUse 'best' command to get AI moves for a FEN position.");
        }
    }
}
