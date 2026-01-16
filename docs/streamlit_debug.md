# Streamlit 端到端测试与调试

## 目标

为每个FEN提供可视化调试界面，方便人工验证规则正确性。

---

## 快速开始

```bash
# 启动调试界面
just start

# 浏览器打开
http://localhost:6704

# 选择"Debug"页面
```

---

## Debug模式设计

### 页面：`pages/4_Debug.py`

**功能**：
1. 输入任意FEN
2. 显示棋盘
3. 显示所有合法走法
4. 显示Rust AI推荐
5. 显示Python/Rust对比

**界面布局**：
```
┌────────────────────────────────────┐
│  FEN调试工具                        │
├────────────────────────────────────┤
│  [FEN输入框]                        │
│  [预设测试用例 ▼]                   │
│     - 开局                          │
│     - 炮攻击测试                    │
│     - 飞将测试                      │
│  [加载]                             │
├──────────────┬─────────────────────┤
│              │                     │
│  棋盘显示     │  信息面板           │
│  (9x10)      │  - 当前回合         │
│              │  - 合法走法数       │
│              │  - Python: 44      │
│              │  - Rust: 44        │
│              │  - AI推荐 (top 5)  │
└──────────────┴─────────────────────┘
```

---

## 端到端测试流程

### 测试用例 1: 开局验证

**步骤**：
1. 选择预设"开局"
2. 点击"加载"
3. **人工验证**：
   - 看棋盘上e0和e9的将是明子吗？✅
   - 看合法走法数：Python 44 == Rust 44？✅
   - 看AI推荐：揭车分数最高吗？✅

**预期结果**：
```
合法走法: Python 44, Rust 44 ✅
AI推荐 (Rust Minimax):
  1. +a0a1  score: 463  (揭车)
  2. +i0i1  score: 463  (揭车)
  3. +b0b1  score: 450  (揭炮)
  ...
```

---

### 测试用例 2: 炮攻击规则

**FEN**：
```
4k4/9/9/4p4/9/9/4P4/9/4C4/9 -:- r r
```

**步骤**：
1. 粘贴上述FEN
2. 点击"加载"
3. **人工验证**：
   - 点击e2的炮
   - 看高亮的目标位置
   - 能走到e6吗？✅（隔1子）
   - 能走到e9吗？❌（隔2子，应该不行）

**预期结果**：
```
炮 (e2) 的合法走法:
  - e6 (吃兵) ✅
  - e0, e1, e3 (空位) ✅
  [不包含 e9] ✅
```

---

### 测试用例 3: 飞将规则

**FEN**：
```
4k4/9/9/9/9/9/9/9/9/4K4 -:- b b
```

**步骤**：
1. 粘贴上述FEN
2. 点击"加载"
3. **人工验证**：
   - 黑方回合
   - 点击e9的将
   - 能走到e0吗？✅（飞将）

**预期结果**：
```
黑将 (e9) 的合法走法:
  - e0 (飞将吃红将) ✅
```

---

## 实现要点

### 1. FEN加载器

```python
# pages/4_Debug.py

def load_fen(fen: str):
    """加载FEN并显示信息"""
    # Python
    python_moves = get_legal_moves_from_fen(fen)
    
    # Rust
    engine = UnifiedAIEngine()
    rust_moves = engine.get_legal_moves(fen)
    
    # AI推荐
    ai_moves = UnifiedAIEngine(strategy="minimax", time_limit=0.5).get_best_moves(fen, n=5)
    
    return {
        "python_count": len(python_moves),
        "rust_count": len(rust_moves),
        "ai_recommendations": ai_moves
    }
```

### 2. 预设测试用例

```python
TEST_CASES = {
    "开局": {
        "fen": "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r",
        "description": "验证开局44个走法",
        "expected": {"moves": 44, "kings_visible": True}
    },
    "炮攻击": {
        "fen": "4k4/9/9/4p4/9/9/4P4/9/4C4/9 -:- r r",
        "description": "验证炮只能隔1子攻击",
        "expected": {"e2_can_hit_e6": True, "e2_cannot_hit_e9": True}
    },
    "飞将": {
        "fen": "4k4/9/9/9/9/9/9/9/9/4K4 -:- b b",
        "description": "验证飞将规则",
        "expected": {"e9_can_capture_e0": True}
    }
}
```

### 3. 棋盘可视化

复用现有的`render_board()`，但添加信息显示：

```python
# 显示合法走法高亮
if selected_piece:
    legal_targets = get_legal_targets(selected_piece)
    # 高亮显示
```

---

## 使用场景

### 场景1: 开发新规则

```python
# 1. 修改规则代码
# 2. 启动Debug页面
# 3. 选择相关测试用例
# 4. 人工验证是否正确
```

### 场景2: 调试Bug

```python
# 1. 发现某FEN有问题
# 2. 复制FEN到Debug页面
# 3. 查看Python/Rust对比
# 4. 查看AI推荐
# 5. 定位问题
```

### 场景3: 验证实现

```python
# 1. 遍历所有预设测试用例
# 2. 逐个人工验证
# 3. 确认所有期望结果
# 4. ✅ 实现正确
```

---

## 验证清单

### 每个FEN都要检查：

- [ ] FEN能正确加载
- [ ] 棋盘显示正确
- [ ] Python走法数正确
- [ ] Rust走法数正确
- [ ] Python == Rust
- [ ] AI推荐合理
- [ ] 人工验证符合预期

---

## 下一步

1. 实现`pages/4_Debug.py`
2. 添加预设测试用例
3. 添加到Streamlit导航
4. 编写使用文档
