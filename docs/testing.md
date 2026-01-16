# 测试策略

## 测试架构（基于接口分层）

```
┌──────────────────────────────────────┐
│  Layer 3: 集成测试                   │
│  验证: Python 通过 CLI 调用 Rust     │
└──────────────┬───────────────────────┘
               │
    ┌──────────┴──────────┐
    ▼                     ▼
┌─────────┐          ┌──────────┐
│ Layer 2 │          │ Layer 1  │
│ Python  │          │ Rust     │
│ 引擎    │          │ 内核     │
└─────────┘          └──────────┘
```

---

## 快速开始

```bash
# 运行所有测试（<5秒）
just test

# 只测 Rust
just test-rust

# 只测 Python
just test-python
```

---

## Layer 1: Rust 内核测试

### 验证内容
- Minimax 算法正确
- 评估函数计算
- 开局分数范围（-400 到 +500）

### 测试文件
`rust-ai/src/ai/minimax.rs`

```rust
#[test]
fn test_opening_evaluation() {
    let fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";
    let ai = MinimaxAI::new(Config::default());
    let moves = ai.select_moves_fen(fen, 44);
    
    let scores: Vec<f64> = moves.iter().map(|(_, s)| *s).collect();
    assert!(-400.0 <= *scores.iter().min().unwrap());
    assert!(*scores.iter().max().unwrap() <= 500.0);
}

#[test]
fn test_reveal_scores() {
    // 揭车 > 400，揭兵 < -300
}
```

### 执行
```bash
cd rust-ai && cargo test
```

**预期时间**：<1秒

---

## Layer 2: Python 引擎测试

### 验证内容
- FEN 解析正确
- 走法生成（44个）
- 象棋规则（炮、飞将）

### 测试文件
`tests/unit/jieqi/test_board.py`

```python
OPENING_FEN = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"

def test_opening_moves():
    """验证开局走法数量"""
    moves = get_legal_moves_from_fen(OPENING_FEN)
    assert len(moves) == 44

def test_cannon_rule():
    """验证炮攻击规则"""
    fen = "4k4/9/9/4p4/9/9/4P4/9/4C4/9 -:- r r"
    board = create_board_from_fen(fen)
    moves = board.get_legal_moves(Color.RED)
    
    # 能打e6（隔1子），不能打e9（隔2子）
    assert any(m.to_pos == Position(6, 4) for m in moves)
    assert not any(m.to_pos == Position(9, 4) for m in moves)

def test_flying_general():
    """验证飞将规则"""
    fen = "4k4/9/9/9/9/9/9/9/9/4K4 -:- b b"
    board = create_board_from_fen(fen)
    moves = board.get_legal_moves(Color.BLACK)
    
    # 黑将可以飞将
    assert any(m.from_pos == Position(9, 4) and m.to_pos == Position(0, 4) 
               for m in moves)
```

### 执行
```bash
uv run pytest tests/unit -v
```

**预期时间**：<1秒

---

## Layer 3: 集成测试

### 3.1 CLI 接口测试

**验证 Rust CLI 正常工作**

`tests/integration/test_cli_interface.py`

```python
def test_cli_json_output():
    """验证 CLI 输出格式"""
    result = subprocess.run([
        "cargo", "run", "--release", "--",
        "best", OPENING_FEN,
        "--strategy", "minimax",
        "--time-limit", "0.1",  # 限时0.1秒
        "--n", "5",
        "--json"
    ], cwd="rust-ai", capture_output=True, text=True)
    
    data = json.loads(result.stdout)
    assert "moves" in data
    assert len(data["moves"]) == 5

def test_all_strategies():
    """验证所有策略都能调用"""
    for strategy in ["minimax", "muses", "greedy"]:
        result = subprocess.run([
            "cargo", "run", "--release", "--",
            "best", OPENING_FEN,
            "--strategy", strategy,
            "--time-limit", "0.1",
            "--n", "1",
            "--json"
        ], cwd="rust-ai", capture_output=True, text=True)
        
        assert result.returncode == 0
```

**预期时间**：<2秒

---

### 3.2 UnifiedAIEngine 测试

**验证 Python 包装器正确**

`tests/integration/test_unified_engine.py`

```python
def test_engine_get_best_moves():
    """验证 UnifiedAIEngine 调用 Rust"""
    engine = UnifiedAIEngine(strategy="minimax", time_limit=0.1)
    moves = engine.get_best_moves(OPENING_FEN, n=5)
    
    assert len(moves) == 5
    assert all(isinstance(m, tuple) and len(m) == 2 for m in moves)
    
    # 分数降序
    scores = [s for _, s in moves]
    assert scores == sorted(scores, reverse=True)

def test_different_strategies():
    """验证不同策略返回结果"""
    minimax = UnifiedAIEngine(strategy="minimax", time_limit=0.1)
    muses = UnifiedAIEngine(strategy="muses", time_limit=0.1)
    
    minimax_moves = minimax.get_best_moves(OPENING_FEN, n=3)
    muses_moves = muses.get_best_moves(OPENING_FEN, n=3)
    
    assert len(minimax_moves) == 3
    assert len(muses_moves) == 3
```

**预期时间**：<2秒

---

### 3.3 端到端游戏测试

**验证完整游戏流程**

`tests/integration/test_full_game.py`

```python
def test_game_with_ai():
    """验证 Python 引擎 + Rust AI 协作"""
    game = JieqiGame()
    engine = UnifiedAIEngine(strategy="minimax", time_limit=0.1)
    
    # 模拟10回合
    for _ in range(10):
        if game.result != GameResult.ONGOING:
            break
        
        # 获取AI推荐
        view = game.get_view(game.current_turn)
        fen = to_fen(view)
        moves = engine.get_best_moves(fen, n=1)
        
        assert len(moves) > 0
        
        # 执行
        move_str, score = moves[0]
        move, revealed = parse_move(move_str)
        success = game.make_move(move, reveal_type=revealed.value if revealed else None)
        
        assert success, f"走法{move_str}不合法"
    
    assert len(game.move_history) > 0
```

**预期时间**：<1秒

---

## Justfile 配置

```justfile
# 所有测试（<5秒）
test:
    @echo "🧪 运行所有测试..."
    @cd rust-ai && cargo test --lib --quiet
    @cd rust-ai && cargo build --release --quiet
    @uv run pytest tests/ -v

# 只测 Rust
test-rust:
    cd rust-ai && cargo test

# 只测 Python
test-python:
    uv run pytest tests/ -v

# 覆盖率
test-coverage:
    uv run pytest tests/ --cov=jieqi --cov-report=html
```

---

## 测试清单

### ✅ Layer 1: Rust 内核
- [ ] Minimax 评估正确
- [ ] 开局分数范围（-400 到 +500）
- [ ] 揭车 > 400，揭兵 < -300

### ✅ Layer 2: Python 引擎
- [ ] FEN 解析
- [ ] 开局44个走法
- [ ] 炮攻击规则
- [ ] 飞将规则

### ✅ Layer 3: 集成
- [ ] CLI JSON 格式正确
- [ ] 所有策略可调用
- [ ] UnifiedAIEngine 正确包装
- [ ] 完整游戏流程无错

---

## CI 配置

`.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup
        run: |
          curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
          pip install uv && uv sync
      
      - name: Run all tests
        run: just test
```

---

## 总结

**统一命令**：`just test`

**预期时间**：< 5秒（所有测试）

**使用 time-limit**：测试用 `--time-limit 0.1`（0.1秒限时）

**测试原则**：
- 使用时间限制（不用depth）
- 分层独立，接口为界
- 快速反馈
