//! 评估局面工具
//!
//! 用法:
//!   cargo run --release --example eval_position -- --fen "..." --strategy minimax

use clap::Parser;
use xiangqi_ai::Board;

#[derive(Parser)]
#[command(about = "评估指定局面的静态分数")]
struct Args {
    /// FEN 字符串
    #[arg(short, long)]
    fen: String,

    /// AI 策略 (minimax, muses)
    #[arg(short, long, default_value = "minimax")]
    strategy: String,

    /// 是否显示详细信息
    #[arg(short, long)]
    verbose: bool,
}

fn main() {
    let args = Args::parse();

    // 解析 FEN
    let board = match Board::from_fen(&args.fen) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("FEN 解析错误: {}", e);
            std::process::exit(1);
        }
    };

    let current_color = board.current_turn();

    if args.verbose {
        println!("FEN: {}", args.fen);
        println!("当前回合: {:?}", current_color);
        println!("策略: {}", args.strategy);
        println!();

        // 显示棋盘信息
        let my_pieces = board.get_all_pieces(Some(current_color));
        let enemy_pieces = board.get_all_pieces(Some(current_color.opposite()));
        println!("棋盘信息:");
        println!("  {:?} 方棋子数: {}", current_color, my_pieces.len());
        println!(
            "  {:?} 方棋子数: {}",
            current_color.opposite(),
            enemy_pieces.len()
        );
        println!();
    }

    // 直接调用静态评估
    use xiangqi_ai::IT2AI;
    let score = IT2AI::evaluate_static(&board, current_color);

    println!("═══════════════════════════════════");
    println!("静态局面评估 ({:?} 视角)", current_color);
    println!("═══════════════════════════════════");
    println!("评估分数: {:.2}", score);
    println!("═══════════════════════════════════");

    if args.verbose {
        println!("\n分数解释:");
        println!("  > 0   : {:?} 方占优", current_color);
        println!("  = 0   : 势均力敌");
        println!("  < 0   : {:?} 方占优", current_color.opposite());
        println!();
        println!("分数参考:");
        println!("  ±100  : 相当于一个兵的优势");
        println!("  ±320  : 相当于一个暗子的期望价值");
        println!("  ±400  : 相当于一个马的优势");
        println!("  ±900  : 相当于一个车的优势");
        println!();
        println!("位置奖励:");
        println!("  中心控制: 1-5 分");
        println!("  兵前进奖励: row × 5 分");
    }
}
