//! 生成跨语言测试用例
//!
//! 使用 Python 引擎生成测试用例，Rust 来验证

use serde::{Deserialize, Serialize};
use std::fs::File;
use std::process::Command;

#[derive(Serialize, Deserialize, Debug, Clone)]
struct TestCase {
    id: String,
    fen: String,
    turn: String,
    expected_move_count: usize,
    is_in_check: bool,
    game_result: String,
    source: String,
}

fn main() {
    println!("使用 Python 生成测试用例...\n");

    // 调用 Python 脚本生成测试用例
    let output = Command::new("uv")
        .args(&["run", "python", "scripts/generate_test_cases.py"])
        .current_dir("/Users/tyz/private/jieqiai")
        .output();

    match output {
        Ok(result) => {
            if result.status.success() {
                println!("✓ Python 测试用例生成成功");
                println!("{}", String::from_utf8_lossy(&result.stdout));

                // 在 Rust 中验证这些测试用例
                validate_test_cases();
            } else {
                eprintln!("✗ Python 生成失败:");
                eprintln!("{}", String::from_utf8_lossy(&result.stderr));
            }
        }
        Err(e) => {
            eprintln!("✗ 无法运行 Python: {}", e);
            eprintln!("请先创建 Python 测试用例生成脚本");
        }
    }
}

fn validate_test_cases() {
    use xiangqi_ai::{Board, Color};

    println!("\n验证测试用例...");

    // 读取 test_cases.json
    let file = match File::open("test_cases.json") {
        Ok(f) => f,
        Err(e) => {
            eprintln!("无法打开 test_cases.json: {}", e);
            return;
        }
    };

    let test_cases: Vec<TestCase> = match serde_json::from_reader(file) {
        Ok(cases) => cases,
        Err(e) => {
            eprintln!("无法解析 JSON: {}", e);
            return;
        }
    };

    println!("共 {} 个测试用例\n", test_cases.len());

    let mut passed = 0;
    let mut failed = 0;

    for (i, case) in test_cases.iter().enumerate() {
        let board = match Board::from_fen(&case.fen) {
            Ok(b) => b,
            Err(e) => {
                eprintln!("✗ {} 无法解析FEN: {}", case.id, e);
                failed += 1;
                continue;
            }
        };

        let color = if case.turn == "red" {
            Color::Red
        } else {
            Color::Black
        };
        let moves = board.get_legal_moves(color);

        // 验证走法数量
        if moves.len() != case.expected_move_count {
            eprintln!(
                "✗ {} 走法数量不匹配: 期望 {}, 实际 {}",
                case.id,
                case.expected_move_count,
                moves.len()
            );
            failed += 1;
            continue;
        }

        // 验证将军状态
        let in_check = board.is_in_check(color);
        if in_check != case.is_in_check {
            eprintln!(
                "✗ {} 将军状态不匹配: 期望 {}, 实际 {}",
                case.id, case.is_in_check, in_check
            );
            failed += 1;
            continue;
        }

        passed += 1;
        if (i + 1) % 100 == 0 {
            println!("  已验证 {} 个用例...", i + 1);
        }
    }

    println!("\n验证结果:");
    println!("  ✓ 通过: {}", passed);
    println!("  ✗ 失败: {}", failed);
    println!("  总计: {}", test_cases.len());

    if failed == 0 {
        println!("\n🎉 所有测试用例通过！");
    }
}
