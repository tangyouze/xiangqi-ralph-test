//! Xiangqi AI CLI
//!
//! 命令行界面，用于测试 AI
//!
//! 支持两种模式：
//! 1. 单次命令模式：每次执行一个命令
//! 2. Server 模式：长驻进程，通过 stdin/stdout 通信

use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use std::io::{self, BufRead, Write};
use std::time::Instant;
use xiangqi_ai::{get_legal_moves_from_fen, get_node_count, reset_node_count, get_depth_reached, reset_depth_reached, AIConfig, AIEngine, Board, IterativeDeepeningAI, Color};

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
        #[arg(long)]
        fen: String,
    },

    /// 选择最佳走法
    Best {
        /// FEN 字符串
        #[arg(long)]
        fen: String,

        /// AI 策略 (random, greedy, minimax, iterative, mcts, muses)
        #[arg(long, default_value = "muses")]
        strategy: String,

        /// 时间限制（秒）
        #[arg(long)]
        time_limit: Option<f64>,

        /// 返回的走法数量
        #[arg(long, default_value = "1")]
        n: usize,

        /// JSON 输出
        #[arg(long)]
        json: bool,
    },

    /// 评估局面分数
    Score {
        /// FEN 字符串
        #[arg(long)]
        fen: String,

        /// JSON 输出
        #[arg(long)]
        json: bool,
    },

    /// 启动 server 模式（stdin/stdout 通信）
    Server,
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

// Server 模式的请求和响应结构
#[derive(Serialize, Deserialize)]
struct ServerRequest {
    cmd: String,
    #[serde(default)]
    fen: String,
    #[serde(default)]
    strategy: Option<String>,
    #[serde(default)]
    time_limit: Option<f64>,
    #[serde(default)]
    n: Option<usize>,
}

#[derive(Serialize, Deserialize)]
struct ServerResponse {
    ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    moves: Option<Vec<MoveResult>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    legal_moves: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    depth: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    nodes: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    nps: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    elapsed_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
}

impl ServerResponse {
    fn success_moves(moves: Vec<MoveResult>, depth: u32, nodes: u64, nps: f64, elapsed_ms: f64) -> Self {
        Self {
            ok: true,
            moves: Some(moves),
            legal_moves: None,
            depth: Some(depth),
            nodes: Some(nodes),
            nps: Some(nps),
            elapsed_ms: Some(elapsed_ms),
            error: None,
        }
    }

    fn success_legal_moves(legal_moves: Vec<String>) -> Self {
        Self {
            ok: true,
            moves: None,
            legal_moves: Some(legal_moves),
            depth: None,
            nodes: None,
            nps: None,
            elapsed_ms: None,
            error: None,
        }
    }

    fn error(msg: &str) -> Self {
        Self {
            ok: false,
            moves: None,
            legal_moves: None,
            depth: None,
            nodes: None,
            nps: None,
            elapsed_ms: None,
            error: Some(msg.to_string()),
        }
    }
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
            time_limit,
            n,
            json,
        } => {
            let config = AIConfig {
                depth: 100, // 使用时间限制，深度设置足够大
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

            // 重置计数器
            reset_node_count();
            reset_depth_reached();
            let start = Instant::now();

            match ai.select_moves_fen(&fen, n) {
                Ok(moves) => {
                    let elapsed = start.elapsed().as_secs_f64();
                    let nodes = get_node_count();
                    let depth = get_depth_reached();
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
                            "Stats: depth={}, nodes={}, time={:.3}s, nps={:.0}",
                            depth, nodes, elapsed, nps
                        );
                    } else {
                        println!("Best moves (strategy={}):", strategy);
                        for (mv, score) in moves {
                            println!("  {} (score: {:.2})", mv, score);
                        }
                        println!(
                            "\nStats: depth={}, nodes={}, time={:.3}s, nps={:.0}",
                            depth, nodes, elapsed, nps
                        );
                    }
                }
                Err(e) => {
                    eprintln!("Error: {}", e);
                    std::process::exit(1);
                }
            }
        }

        Commands::Score { fen, json } => {
            match Board::from_fen(&fen) {
                Ok(board) => {
                    let color = board.current_turn();
                    let score = IterativeDeepeningAI::evaluate_static(&board, color);

                    if json {
                        println!(
                            "{{\"fen\": {:?}, \"color\": {:?}, \"score\": {:.2}}}",
                            fen,
                            if color == Color::Red { "red" } else { "black" },
                            score
                        );
                    } else {
                        let color_str = if color == Color::Red { "红方" } else { "黑方" };
                        println!("局面评估 ({} 视角): {:.2}", color_str, score);
                    }
                }
                Err(e) => {
                    eprintln!("Error: {}", e);
                    std::process::exit(1);
                }
            }
        }

        Commands::Server => {
            run_server();
        }
    }
}

/// Server 模式主循环
/// 从 stdin 读取 JSON 请求，返回 JSON 响应到 stdout
fn run_server() {
    let stdin = io::stdin();
    let mut stdout = io::stdout();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };

        // 空行跳过
        if line.trim().is_empty() {
            continue;
        }

        // 解析请求
        let request: ServerRequest = match serde_json::from_str(&line) {
            Ok(r) => r,
            Err(e) => {
                let response = ServerResponse::error(&format!("Invalid JSON: {}", e));
                println!("{}", serde_json::to_string(&response).unwrap());
                let _ = stdout.flush();
                continue;
            }
        };

        // 处理命令
        let response = match request.cmd.as_str() {
            "best" => handle_best_request(&request),
            "moves" => handle_moves_request(&request),
            "quit" => break,
            _ => ServerResponse::error(&format!("Unknown command: {}", request.cmd)),
        };

        // 返回响应
        println!("{}", serde_json::to_string(&response).unwrap());
        let _ = stdout.flush();
    }
}

/// 处理 best 命令
fn handle_best_request(request: &ServerRequest) -> ServerResponse {
    let strategy = request.strategy.as_deref().unwrap_or("muses");
    let time_limit = request.time_limit;
    let n = request.n.unwrap_or(5);

    let config = AIConfig {
        depth: 100,
        randomness: 0.0,
        seed: None,
        time_limit,
    };

    let ai = match AIEngine::from_strategy(strategy, &config) {
        Ok(ai) => ai,
        Err(e) => return ServerResponse::error(&format!("Invalid strategy: {}", e)),
    };

    reset_node_count();
    reset_depth_reached();
    let start = Instant::now();

    match ai.select_moves_fen(&request.fen, n) {
        Ok(moves) => {
            let elapsed = start.elapsed().as_secs_f64();
            let nodes = get_node_count();
            let depth = get_depth_reached();
            let nps = if elapsed > 0.0 { nodes as f64 / elapsed } else { 0.0 };

            let move_results: Vec<MoveResult> = moves
                .into_iter()
                .map(|(mv, score)| MoveResult { mv, score })
                .collect();

            ServerResponse::success_moves(move_results, depth, nodes, nps, elapsed * 1000.0)
        }
        Err(e) => ServerResponse::error(&format!("AI error: {}", e)),
    }
}

/// 处理 moves 命令
fn handle_moves_request(request: &ServerRequest) -> ServerResponse {
    match get_legal_moves_from_fen(&request.fen) {
        Ok(moves) => ServerResponse::success_legal_moves(moves),
        Err(e) => ServerResponse::error(&format!("Invalid FEN: {}", e)),
    }
}
