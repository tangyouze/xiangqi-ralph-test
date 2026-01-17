# Xiangqi AI (Rust)

揭棋 AI 引擎 - 使用 Rust 实现的象棋变体 AI。

## Features

- FEN 字符串解析和生成
- 完整的揭棋规则实现
- 多种 AI 策略：
  - Random: 随机选择
  - Greedy: 贪婪策略（优先吃子）
  - Minimax: Alpha-Beta 剪枝搜索

## Build

```bash
cargo build --release
```

## Usage

### 获取合法走法

```bash
./target/release/xiangqi-ai moves --fen "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"
```

### 获取 AI 推荐走法

```bash
# 使用贪婪策略
./target/release/xiangqi-ai best --fen "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r" --strategy greedy

# 使用 Minimax 策略（深度 3）
./target/release/xiangqi-ai best --fen "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r" --strategy minimax --depth 3

# JSON 输出
./target/release/xiangqi-ai best --fen "..." --strategy greedy --json
```

## FEN Format

揭棋 FEN 格式：`<棋盘> <被吃子> <回合> <视角>`

### 棋盘符号

- 红方明子：K(将) R(车) H(马) C(炮) E(象) A(士) P(兵)
- 黑方明子：k r h c e a p
- 红方暗子：X
- 黑方暗子：x
- 空格：数字 (1-9)

### 走法格式

- 明子走法：`a0a1`（从 a0 到 a1）
- 揭子走法：`+a0a1`（揭子并走）

## API

```rust
use xiangqi_ai::{AIEngine, AIConfig, get_legal_moves_from_fen};

// 获取合法走法
let moves = get_legal_moves_from_fen(fen)?;

// 创建 AI
let config = AIConfig { depth: 3, ..Default::default() };
let ai = AIEngine::minimax(&config);

// 获取 AI 推荐走法
let best_moves = ai.select_moves_fen(fen, 5)?;
```

## License

MIT
