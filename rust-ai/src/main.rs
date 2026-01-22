//! Xiangqi AI CLI
//!
//! 命令行界面，用于测试 AI
//!
//! 支持两种模式：
//! 1. 单次命令模式：每次执行一个命令
//! 2. Server 模式：长驻进程，通过 stdin/stdout 通信

use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::io::{self, BufRead, Write};
use std::time::Instant;
use xiangqi_ai::{
    get_depth_reached, get_legal_moves_from_fen, get_node_count, reset_depth_reached,
    reset_node_count, AIConfig, AIEngine, ActionType, Board, Color, HiddenPieceDistribution,
    JieqiMove, IT2AI,
};

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

        /// JSON 输出
        #[arg(long)]
        json: bool,
    },

    /// 选择最佳走法
    Best {
        /// FEN 字符串
        #[arg(long)]
        fen: String,

        /// AI 策略 (random, muses2, it2)
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
    fen_after: String,
    /// fen_after 的真实静态评估（从当前走棋方视角）
    real_eval: f64,
    /// 揭子走法的概率分布（仅 type=chance 时有值）
    #[serde(skip_serializing_if = "Option::is_none")]
    chance_breakdown: Option<Vec<ChanceOutcome>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    opposite_top10: Option<Vec<SearchMoveBasic>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    opposite_bottom10: Option<Vec<SearchMoveBasic>>,
}

/// 揭子走法的概率分布
#[derive(Serialize, Deserialize, Clone)]
struct ChanceOutcome {
    /// 棋子类型 (a=仕, e=象, h=马, r=车, c=炮, p=兵)
    piece: String,
    /// 概率 (0.0 - 1.0)
    prob: f64,
    /// 揭成该类型后的静态评估
    eval: f64,
    /// 揭成该类型后的 FEN
    fen: String,
}

#[derive(Serialize, Deserialize, Clone)]
struct SearchMoveBasic {
    #[serde(rename = "move")]
    mv: String,
    #[serde(rename = "type")]
    move_type: String,
    eval: f64,
    score: f64,
    fen_after: String,
    /// fen_after 的真实静态评估（从当前走棋方视角）
    real_eval: f64,
    /// 揭子走法的概率分布（仅 type=chance 时有值）
    #[serde(skip_serializing_if = "Option::is_none")]
    chance_breakdown: Option<Vec<ChanceOutcome>>,
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
    fn success_moves(
        moves: Vec<MoveResult>,
        depth: u32,
        nodes: u64,
        nps: f64,
        elapsed_ms: f64,
    ) -> Self {
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

    fn success_search(
        fen: String,
        eval_score: f64,
        depth: u32,
        first_moves: Vec<SearchMoveInfo>,
        nodes: u64,
    ) -> Self {
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
    if color == Color::Red {
        "red"
    } else {
        "black"
    }
}

fn calc_nps(nodes: u64, elapsed_secs: f64) -> f64 {
    if elapsed_secs > 0.0 {
        nodes as f64 / elapsed_secs
    } else {
        0.0
    }
}

fn main() {
    env_logger::init();

    let cli = Cli::parse();

    match cli.command {
        Commands::Moves { fen, json } => match get_legal_moves_from_fen(&fen) {
            Ok(moves) => {
                if json {
                    let move_strs: Vec<String> = moves.iter().map(|m| m.to_string()).collect();
                    println!("{}", serde_json::to_string(&move_strs).unwrap());
                } else {
                    println!("Legal moves ({}):", moves.len());
                    for mv in &moves {
                        println!("  {}", mv);
                    }
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

        Commands::Score { fen, json } => match Board::from_fen(&fen) {
            Ok(board) => {
                let color = board.current_turn();
                let score = IT2AI::evaluate_static(&board, color);

                if json {
                    println!(
                        "{{\"fen\": {:?}, \"color\": {:?}, \"score\": {:.2}}}",
                        fen,
                        color_to_str(color),
                        score
                    );
                } else {
                    let color_cn = if color == Color::Red {
                        "红方"
                    } else {
                        "黑方"
                    };
                    println!("局面评估 ({} 视角): {:.2}", color_cn, score);
                }
            }
            Err(e) => {
                eprintln!("Error: {}", e);
                std::process::exit(1);
            }
        },

        Commands::Search {
            fen,
            strategy,
            depth,
            json,
        } => match do_search(&fen, &strategy, depth) {
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
        },

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
            "eval_detail" => {
                // 直接返回 JSON，不经过 ServerResponse
                let json_str = handle_eval_detail_request(&request);
                println!("{}", json_str);
                let _ = stdout.flush();
                continue;
            }
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
            let score = IT2AI::evaluate_static(&board, color);
            ServerResponse::success_eval(score, color_to_str(color))
        }
        Err(e) => ServerResponse::error(&format!("Invalid FEN: {}", e)),
    }
}

/// 处理 eval_detail 命令（详细评估）
fn handle_eval_detail_request(request: &ServerRequest) -> String {
    match Board::from_fen(&request.fen) {
        Ok(board) => {
            let color = board.current_turn();
            let detail = IT2AI::evaluate_detail(&board, color);

            // 构建每个棋子的 JSON
            let pieces_json: Vec<serde_json::Value> = detail
                .pieces
                .iter()
                .map(|p| {
                    json!({
                        "position": p.position,
                        "color": p.color,
                        "type": p.piece_type,
                        "is_hidden": p.is_hidden,
                        "material": p.material,
                        "pst": p.pst,
                        "value": p.value
                    })
                })
                .collect();

            // 暗子池构成
            let red_pool = HiddenPieceDistribution::from_board(&board, Color::Red);
            let black_pool = HiddenPieceDistribution::from_board(&board, Color::Black);

            let red_pool_json: Vec<serde_json::Value> = red_pool
                .breakdown()
                .iter()
                .map(|(name, count, unit, total)| {
                    json!({
                        "type": name,
                        "count": count,
                        "unit_value": unit,
                        "total_value": total
                    })
                })
                .collect();

            let black_pool_json: Vec<serde_json::Value> = black_pool
                .breakdown()
                .iter()
                .map(|(name, count, unit, total)| {
                    json!({
                        "type": name,
                        "count": count,
                        "unit_value": unit,
                        "total_value": total
                    })
                })
                .collect();

            json!({
                "ok": true,
                "fen": request.fen,
                "pov": detail.pov,
                "pieces": pieces_json,
                "hidden_pool": {
                    "red": {
                        "count": red_pool.total_count(),
                        "expected_value": red_pool.expected_value(),
                        "breakdown": red_pool_json
                    },
                    "black": {
                        "count": black_pool.total_count(),
                        "expected_value": black_pool.expected_value(),
                        "breakdown": black_pool_json
                    }
                },
                "summary": {
                    "red": {
                        "material": detail.material_red,
                        "pst": detail.pst_red,
                        "hidden_ev": detail.hidden_ev_red,
                        "capture": detail.capture_red,
                        "total": detail.material_red + detail.pst_red + detail.hidden_ev_red + detail.capture_red
                    },
                    "black": {
                        "material": detail.material_black,
                        "pst": detail.pst_black,
                        "hidden_ev": detail.hidden_ev_black,
                        "capture": detail.capture_black,
                        "total": detail.material_black + detail.pst_black + detail.hidden_ev_black + detail.capture_black
                    }
                },
                "total": detail.total
            })
            .to_string()
        }
        Err(e) => json!({
            "ok": false,
            "error": format!("Invalid FEN: {}", e)
        })
        .to_string(),
    }
}

/// 处理 search 命令（搜索树调试）
fn handle_search_request(request: &ServerRequest) -> ServerResponse {
    let strategy = request.strategy.as_deref().unwrap_or("it2");
    let depth = request.depth.unwrap_or(2);

    match do_search(&request.fen, strategy, depth) {
        Ok((eval_score, first_moves, nodes)) => ServerResponse::success_search(
            request.fen.clone(),
            eval_score,
            depth,
            first_moves,
            nodes,
        ),
        Err(e) => ServerResponse::error(&format!("Search error: {}", e)),
    }
}

/// 执行搜索并返回详细信息
fn do_search(
    fen: &str,
    strategy: &str,
    depth: u32,
) -> Result<(f64, Vec<SearchMoveInfo>, u64), String> {
    let board = Board::from_fen(fen)?;
    let color = board.current_turn();

    // 当前局面的静态评估
    let current_eval = IT2AI::evaluate_static(&board, color);

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
    let search_map: std::collections::HashMap<String, f64> = search_results.into_iter().collect();

    // 构建第一层走法信息
    let mut first_moves: Vec<SearchMoveInfo> = Vec::new();

    for mv in &legal_moves {
        let mv_str = mv.to_fen_str(None);
        let is_reveal = mv.action_type == ActionType::RevealAndMove;
        let move_type = if is_reveal { "chance" } else { "move" };

        // 走完后的静态评估（和 chance_breakdown）
        let (eval_after, chance_breakdown) = if is_reveal {
            // 揭子走法：计算期望 eval（对所有可能类型加权平均）
            let distribution = HiddenPieceDistribution::from_board(&board, color);
            let possible_types = distribution.possible_types();

            if possible_types.is_empty() {
                let mut board_after = board.clone();
                board_after.make_move(mv);
                (
                    -IT2AI::evaluate_static(&board_after, board_after.current_turn()),
                    None,
                )
            } else {
                let mut expected_eval = 0.0;
                let mut breakdown: Vec<ChanceOutcome> = Vec::new();
                for (piece_type, probability) in &possible_types {
                    let mut board_after = board.clone();
                    board_after.make_move(mv);
                    if let Some(piece) = board_after.get_piece_mut(mv.to_pos) {
                        piece.actual_type = Some(*piece_type);
                    }
                    let eval = IT2AI::evaluate_static(&board_after, Color::Red);
                    let fen = board_after.to_fen();
                    expected_eval += probability * eval;
                    breakdown.push(ChanceOutcome {
                        piece: piece_type.to_fen_char().to_string(),
                        prob: *probability,
                        eval,
                        fen,
                    });
                }
                (expected_eval, Some(breakdown))
            }
        } else {
            let mut board_after = board.clone();
            board_after.make_move(mv);
            (IT2AI::evaluate_static(&board_after, Color::Red), None)
        };

        // 搜索分数
        let score = *search_map.get(&mv_str).unwrap_or(&eval_after);

        // 获取对手的应对（第二层）
        let mut board_after = board.clone();
        board_after.make_move(mv);

        // 揭子走法：随机选择一个合法的棋子类型用于展示
        if is_reveal {
            let distribution = HiddenPieceDistribution::from_board(&board, color);
            let possible_types = distribution.possible_types();
            if let Some((piece_type, _)) = possible_types.first() {
                if let Some(piece) = board_after.get_piece_mut(mv.to_pos) {
                    piece.actual_type = Some(*piece_type);
                }
            }
        }

        let fen_after = board_after.to_fen();

        // 计算 fen_after 的真实静态评估（红方视角）
        let real_eval = IT2AI::evaluate_static(&board_after, Color::Red);

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
            fen_after,
            real_eval,
            chance_breakdown,
            opposite_top10,
            opposite_bottom10,
        });
    }

    // 按分数排序
    first_moves.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });

    let nodes = get_node_count();
    Ok((current_eval, first_moves, nodes))
}

/// 获取对手的应对走法（top10 和 bottom10）
fn get_opposite_moves(
    board: &Board,
    strategy: &str,
    depth: u32,
) -> (Option<Vec<SearchMoveBasic>>, Option<Vec<SearchMoveBasic>>) {
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
            let is_reveal = mv.action_type == ActionType::RevealAndMove;
            let move_type = if is_reveal { "chance" } else { "move" };

            let mut board_after = board.clone();
            board_after.make_move(mv);

            // 计算 eval、real_eval、fen_after 和 chance_breakdown
            let (eval, real_eval, fen_after, chance_breakdown) = if is_reveal {
                let distribution = HiddenPieceDistribution::from_board(board, color);
                let possible_types = distribution.possible_types();
                if possible_types.is_empty() {
                    let e = IT2AI::evaluate_static(&board_after, Color::Red);
                    (e, e, board_after.to_fen(), None)
                } else {
                    let mut expected_eval = 0.0;
                    let mut breakdown: Vec<ChanceOutcome> = Vec::new();
                    let mut first_eval = 0.0;
                    let mut first_fen = String::new();
                    for (i, (piece_type, probability)) in possible_types.iter().enumerate() {
                        let mut temp_board = board.clone();
                        temp_board.make_move(mv);
                        if let Some(piece) = temp_board.get_piece_mut(mv.to_pos) {
                            piece.actual_type = Some(*piece_type);
                        }
                        let e = IT2AI::evaluate_static(&temp_board, Color::Red);
                        let fen = temp_board.to_fen();
                        expected_eval += probability * e;
                        if i == 0 {
                            first_eval = e;
                            first_fen = fen.clone();
                        }
                        breakdown.push(ChanceOutcome {
                            piece: piece_type.to_fen_char().to_string(),
                            prob: *probability,
                            eval: e,
                            fen,
                        });
                    }
                    (expected_eval, first_eval, first_fen, Some(breakdown))
                }
            } else {
                let e = IT2AI::evaluate_static(&board_after, Color::Red);
                (e, e, board_after.to_fen(), None)
            };

            moves.push(SearchMoveBasic {
                mv: mv_str,
                move_type: move_type.to_string(),
                eval,
                score: eval, // 叶子节点：score = eval (期望值)
                fen_after,
                real_eval, // 第一个可能类型的静态评估
                chance_breakdown,
            });
        }

        moves.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
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
        let is_reveal = mv_str.starts_with('+');
        let move_type = if is_reveal { "chance" } else { "move" };

        // 生成走后 FEN、真实评估和 chance_breakdown
        let (fen_after, real_eval, chance_breakdown) =
            if let Some((mv, _)) = JieqiMove::from_fen_str(&mv_str) {
                let mut board_after = board.clone();
                board_after.make_move(&mv);

                let (chance_breakdown, real_eval, fen_str) = if is_reveal {
                    let distribution = HiddenPieceDistribution::from_board(board, color);
                    let possible_types = distribution.possible_types();
                    if possible_types.is_empty() {
                        let e = IT2AI::evaluate_static(&board_after, Color::Red);
                        (None, e, board_after.to_fen())
                    } else {
                        let mut breakdown: Vec<ChanceOutcome> = Vec::new();
                        let mut first_eval = 0.0;
                        let mut first_fen = String::new();
                        for (i, (piece_type, probability)) in possible_types.iter().enumerate() {
                            let mut temp_board = board.clone();
                            temp_board.make_move(&mv);
                            if let Some(piece) = temp_board.get_piece_mut(mv.to_pos) {
                                piece.actual_type = Some(*piece_type);
                            }
                            let e = IT2AI::evaluate_static(&temp_board, Color::Red);
                            let fen = temp_board.to_fen();
                            if i == 0 {
                                first_eval = e;
                                first_fen = fen.clone();
                            }
                            breakdown.push(ChanceOutcome {
                                piece: piece_type.to_fen_char().to_string(),
                                prob: *probability,
                                eval: e,
                                fen,
                            });
                        }
                        (Some(breakdown), first_eval, first_fen)
                    }
                } else {
                    let e = IT2AI::evaluate_static(&board_after, Color::Red);
                    (None, e, board_after.to_fen())
                };

                (fen_str, real_eval, chance_breakdown)
            } else {
                (String::new(), 0.0, None)
            };

        // depth=1 时，score 就是评估值；depth>1 时，score 是搜索分数
        // 为保持评估函数一致，eval 使用 score（AI 搜索返回的值）
        moves.push(SearchMoveBasic {
            mv: mv_str,
            move_type: move_type.to_string(),
            eval: score, // 使用 AI 搜索返回的 score 作为 eval
            score,
            fen_after,
            real_eval,
            chance_breakdown,
        });
    }

    // 按分数排序
    moves.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });

    // 取 top10 和 bottom10
    let top10: Vec<SearchMoveBasic> = moves.iter().take(10).cloned().collect();
    let bottom10: Vec<SearchMoveBasic> = moves.iter().rev().take(10).cloned().collect();

    (Some(top10), Some(bottom10))
}
