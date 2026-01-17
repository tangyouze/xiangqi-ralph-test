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
use xiangqi_ai::{get_legal_moves_from_fen, get_node_count, reset_node_count, get_depth_reached, reset_depth_reached, AIConfig, AIEngine, Board, IterativeDeepeningAI, Color, ActionType, HiddenPieceDistribution};

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

        /// AI 策略 (random, greedy, minimax, iterative, mcts, muses, it2)
        #[arg(long, default_value = "it2")]
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

    /// 搜索树调试（返回两层详细信息）
    Search {
        /// FEN 字符串
        #[arg(long)]
        fen: String,

        /// AI 策略
        #[arg(long, default_value = "it2")]
        strategy: String,

        /// 搜索深度
        #[arg(long, default_value = "2")]
        depth: u32,

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
    #[serde(default)]
    depth: Option<u32>,
}

// search 命令的响应结构
#[derive(Serialize, Deserialize)]
struct SearchMoveInfo {
    #[serde(rename = "move")]
    mv: String,
    #[serde(rename = "type")]
    move_type: String,
    eval: f64,
    score: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    opposite_top10: Option<Vec<SearchMoveBasic>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    opposite_bottom10: Option<Vec<SearchMoveBasic>>,
}

#[derive(Serialize, Deserialize, Clone)]
struct SearchMoveBasic {
    #[serde(rename = "move")]
    mv: String,
    #[serde(rename = "type")]
    move_type: String,
    eval: f64,
    score: f64,
}

#[derive(Serialize, Deserialize, Default)]
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
    // eval 命令的字段
    #[serde(skip_serializing_if = "Option::is_none")]
    eval: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    color: Option<String>,
    // search 命令的字段
    #[serde(skip_serializing_if = "Option::is_none")]
    fen: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    first_moves: Option<Vec<SearchMoveInfo>>,
}

impl ServerResponse {
    fn success_moves(moves: Vec<MoveResult>, depth: u32, nodes: u64, nps: f64, elapsed_ms: f64) -> Self {
        Self {
            ok: true,
            moves: Some(moves),
            depth: Some(depth),
            nodes: Some(nodes),
            nps: Some(nps),
            elapsed_ms: Some(elapsed_ms),
            ..Default::default()
        }
    }

    fn success_legal_moves(legal_moves: Vec<String>) -> Self {
        Self {
            ok: true,
            legal_moves: Some(legal_moves),
            ..Default::default()
        }
    }

    fn success_eval(eval_score: f64, color_str: &str) -> Self {
        Self {
            ok: true,
            eval: Some(eval_score),
            color: Some(color_str.to_string()),
            ..Default::default()
        }
    }

    fn success_search(fen: String, eval_score: f64, depth: u32, first_moves: Vec<SearchMoveInfo>, nodes: u64) -> Self {
        Self {
            ok: true,
            depth: Some(depth),
            nodes: Some(nodes),
            eval: Some(eval_score),
            fen: Some(fen),
            first_moves: Some(first_moves),
            ..Default::default()
        }
    }

    fn error(msg: &str) -> Self {
        Self {
            ok: false,
            error: Some(msg.to_string()),
            ..Default::default()
        }
    }
}

fn color_to_str(color: Color) -> &'static str {
    if color == Color::Red { "red" } else { "black" }
}

fn calc_nps(nodes: u64, elapsed_secs: f64) -> f64 {
    if elapsed_secs > 0.0 { nodes as f64 / elapsed_secs } else { 0.0 }
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
                    let nps = calc_nps(nodes, elapsed);

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
                            fen, color_to_str(color), score
                        );
                    } else {
                        let color_cn = if color == Color::Red { "红方" } else { "黑方" };
                        println!("局面评估 ({} 视角): {:.2}", color_cn, score);
                    }
                }
                Err(e) => {
                    eprintln!("Error: {}", e);
                    std::process::exit(1);
                }
            }
        }

        Commands::Search { fen, strategy, depth, json } => {
            match do_search(&fen, &strategy, depth) {
                Ok((eval_score, first_moves, nodes)) => {
                    if json {
                        let response = ServerResponse::success_search(
                            fen.clone(),
                            eval_score,
                            depth,
                            first_moves,
                            nodes,
                        );
                        println!("{}", serde_json::to_string_pretty(&response).unwrap());
                    } else {
                        println!("Search result (depth={}):", depth);
                        println!("Current eval: {:.2}", eval_score);
                        println!("\nFirst moves ({}):", first_moves.len());
                        for mv_info in &first_moves {
                            println!(
                                "  {} [{}]: eval={:.2}, score={:.2}",
                                mv_info.mv, mv_info.move_type, mv_info.eval, mv_info.score
                            );
                        }
                        println!("\nNodes: {}", nodes);
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
            "eval" => handle_eval_request(&request),
            "search" => handle_search_request(&request),
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
    let strategy = request.strategy.as_deref().unwrap_or("it2");
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
            let nps = calc_nps(nodes, elapsed);

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

/// 处理 eval 命令（静态评估）
fn handle_eval_request(request: &ServerRequest) -> ServerResponse {
    match Board::from_fen(&request.fen) {
        Ok(board) => {
            let color = board.current_turn();
            let score = IterativeDeepeningAI::evaluate_static(&board, color);
            ServerResponse::success_eval(score, color_to_str(color))
        }
        Err(e) => ServerResponse::error(&format!("Invalid FEN: {}", e)),
    }
}

/// 处理 search 命令（搜索树调试）
fn handle_search_request(request: &ServerRequest) -> ServerResponse {
    let strategy = request.strategy.as_deref().unwrap_or("it2");
    let depth = request.depth.unwrap_or(2);

    match do_search(&request.fen, strategy, depth) {
        Ok((eval_score, first_moves, nodes)) => {
            ServerResponse::success_search(request.fen.clone(), eval_score, depth, first_moves, nodes)
        }
        Err(e) => ServerResponse::error(&format!("Search error: {}", e)),
    }
}

/// 执行搜索并返回详细信息
fn do_search(fen: &str, strategy: &str, depth: u32) -> Result<(f64, Vec<SearchMoveInfo>, u64), String> {
    let board = Board::from_fen(fen)?;
    let color = board.current_turn();

    // 当前局面的静态评估
    let current_eval = IterativeDeepeningAI::evaluate_static(&board, color);

    // 获取所有合法走法
    let legal_moves = board.get_legal_moves(color);
    if legal_moves.is_empty() {
        return Ok((current_eval, Vec::new(), 0));
    }

    reset_node_count();

    // 创建 AI 进行搜索
    let config = AIConfig {
        depth,
        randomness: 0.0,
        seed: None,
        time_limit: None,
    };
    let ai = AIEngine::from_strategy(strategy, &config)?;

    // 获取所有走法的搜索分数
    let search_results = ai.select_moves_fen(fen, legal_moves.len())?;
    let search_map: std::collections::HashMap<String, f64> = search_results
        .into_iter()
        .collect();

    // 构建第一层走法信息
    let mut first_moves: Vec<SearchMoveInfo> = Vec::new();

    for mv in &legal_moves {
        let mv_str = mv.to_fen_str(None);
        let is_reveal = mv.action_type == ActionType::RevealAndMove;
        let move_type = if is_reveal { "chance" } else { "move" };

        // 走完后的静态评估
        let eval_after = if is_reveal {
            // 揭子走法：计算期望 eval（对所有可能类型加权平均）
            let distribution = HiddenPieceDistribution::from_board(&board, color);
            let possible_types = distribution.possible_types();

            if possible_types.is_empty() {
                let mut board_after = board.clone();
                board_after.make_move(mv);
                -IterativeDeepeningAI::evaluate_static(&board_after, board_after.current_turn())
            } else {
                let mut expected_eval = 0.0;
                for (piece_type, probability) in possible_types {
                    let mut board_after = board.clone();
                    board_after.make_move(mv);
                    // make_move 后修正 actual_type
                    if let Some(piece) = board_after.get_piece_mut(mv.to_pos) {
                        piece.actual_type = Some(piece_type);
                    }
                    let eval = -IterativeDeepeningAI::evaluate_static(&board_after, board_after.current_turn());
                    expected_eval += probability * eval;
                }
                expected_eval
            }
        } else {
            let mut board_after = board.clone();
            board_after.make_move(mv);
            -IterativeDeepeningAI::evaluate_static(&board_after, board_after.current_turn())
        };

        // 搜索分数
        let score = *search_map.get(&mv_str).unwrap_or(&eval_after);

        // 获取对手的应对（第二层）
        let mut board_after = board.clone();
        board_after.make_move(mv);
        let (opposite_top10, opposite_bottom10) = if depth > 1 {
            get_opposite_moves(&board_after, strategy, depth - 1)
        } else {
            (None, None)
        };

        first_moves.push(SearchMoveInfo {
            mv: mv_str,
            move_type: move_type.to_string(),
            eval: eval_after,
            score,
            opposite_top10,
            opposite_bottom10,
        });
    }

    // 按分数排序
    first_moves.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));

    let nodes = get_node_count();
    Ok((current_eval, first_moves, nodes))
}

/// 获取对手的应对走法（top10 和 bottom10）
fn get_opposite_moves(board: &Board, strategy: &str, depth: u32) -> (Option<Vec<SearchMoveBasic>>, Option<Vec<SearchMoveBasic>>) {
    let color = board.current_turn();
    let legal_moves = board.get_legal_moves(color);

    if legal_moves.is_empty() {
        return (None, None);
    }

    // depth=1 时直接用静态评估（叶子节点，不需要搜索）
    if depth <= 1 {
        let mut moves: Vec<SearchMoveBasic> = Vec::new();
        for mv in &legal_moves {
            let mv_str = mv.to_fen_str(None);
            let move_type = if mv_str.starts_with('+') { "chance" } else { "move" };

            let mut board_after = board.clone();
            board_after.make_move(mv);
            let eval = -IterativeDeepeningAI::evaluate_static(&board_after, board_after.current_turn());

            moves.push(SearchMoveBasic {
                mv: mv_str,
                move_type: move_type.to_string(),
                eval,
                score: eval, // 叶子节点：score = eval
            });
        }

        moves.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        let top10: Vec<SearchMoveBasic> = moves.iter().take(10).cloned().collect();
        let bottom10: Vec<SearchMoveBasic> = moves.iter().rev().take(10).cloned().collect();
        return (Some(top10), Some(bottom10));
    }

    // depth > 1 时使用 AI 搜索
    let fen = board.to_fen();
    let config = AIConfig {
        depth,
        randomness: 0.0,
        seed: None,
        time_limit: None,
    };

    let ai = match AIEngine::from_strategy(strategy, &config) {
        Ok(ai) => ai,
        Err(_) => return (None, None),
    };

    let search_results = match ai.select_moves_fen(&fen, legal_moves.len()) {
        Ok(r) => r,
        Err(_) => return (None, None),
    };

    // 构建走法信息
    let mut moves: Vec<SearchMoveBasic> = Vec::new();

    for (mv_str, score) in search_results {
        let move_type = if mv_str.starts_with('+') { "chance" } else { "move" };

        // 解析走法获取 eval
        let eval = if let Some(mv) = legal_moves.iter().find(|m| m.to_fen_str(None) == mv_str) {
            let mut board_after = board.clone();
            board_after.make_move(mv);
            -IterativeDeepeningAI::evaluate_static(&board_after, board_after.current_turn())
        } else {
            score
        };

        moves.push(SearchMoveBasic {
            mv: mv_str,
            move_type: move_type.to_string(),
            eval,
            score,
        });
    }

    // 按分数排序
    moves.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));

    // 取 top10 和 bottom10
    let top10: Vec<SearchMoveBasic> = moves.iter().take(10).cloned().collect();
    let bottom10: Vec<SearchMoveBasic> = moves.iter().rev().take(10).cloned().collect();

    (Some(top10), Some(bottom10))
}
