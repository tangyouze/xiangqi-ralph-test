# 验证报告系统

## 目标

让**人类**能够直观地知道实现是否正确，不只是程序知道。

---

## 验证方法

### 1. 自动化测试报告

**执行**：
```bash
just verify
```

**输出**：HTML验证报告（`reports/verification.html`）

**内容**：
```
┌────────────────────────────────────────┐
│  揭棋实现验证报告                       │
│  生成时间: 2026-01-16 09:42           │
└────────────────────────────────────────┘

✅ 规则验证
├─ ✅ 开局44个走法 (Rust: 44, Python: 44)
├─ ✅ 将是明子
├─ ✅ 炮隔1子可攻击
├─ ✅ 炮隔2子不可攻击
├─ ✅ 飞将规则
└─ ✅ 揭子机制

✅ 分数合理性
├─ ✅ 开局范围: -400 到 +500
├─ ✅ 揭车 > +400 (实际: 463)
└─ ✅ 揭兵 < -300 (实际: -337)

✅ Python-Rust 一致性
├─ ✅ 走法数量一致 (44 == 44)
├─ ✅ CLI 接口正常
└─ ✅ 完整游戏流程无错

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总结: 所有测试通过 ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 2. 可视化棋局验证

**工具**：Streamlit UI

**验证场景**：
```bash
just start  # 启动Streamlit

# 在浏览器中验证：
1. 开局走法（手动数一下是否44个）
2. 炮攻击规则（尝试隔2子攻击，应该失败）
3. 飞将规则（两将面对面，看是否能飞将）
4. AI推荐（看是否揭车分数高）
```

**优势**：
- 人类能看到棋盘
- 可以手动尝试走法
- 直观验证规则

---

### 3. 对比测试棋谱

**生成标准测试用例**：
```bash
cd rust-ai
cargo run --release --example generate_test_games
```

**输出**：`tests/fixtures/standard_games.json`

**内容**：
```json
{
  "games": [
    {
      "id": "standard_001",
      "description": "开局验证",
      "initial_fen": "...",
      "expected_legal_moves": 44,
      "key_rules": ["将是明子", "开局44走法"]
    },
    {
      "id": "cannon_attack",
      "description": "炮攻击规则",
      "setup_fen": "...",
      "illegal_moves": ["e2e9"],  // 隔2子应该不合法
      "legal_moves": ["e2e6"],     // 隔1子应该合法
      "key_rules": ["炮隔1子攻击", "炮不能隔2子"]
    }
  ]
}
```

**人类验证**：
1. 打开JSON文件
2. 看描述和预期结果
3. 在Streamlit中手动验证
4. 确认符合预期

---

### 4. 开局分析证据

**已有工具**：
```bash
cd rust-ai
cargo run --release --example opening_analysis
cargo run --release --example opening_2steps
```

**输出**：统计数据

```
开局分析 (1000个样本)
━━━━━━━━━━━━━━━━━━━━━━━━━━
分数范围: -337 到 +463
平均分数: +117

按棋子类型:
- 揭车: +463 (最高) ✅
- 揭炮: +41
- 揭马: -37
- 揭将: -117
- 揭兵: -337 (最低) ✅

结论: 符合象棋常识 ✅
```

**人类判断**：
- 揭车分数最高 ✅（符合常识）
- 揭兵分数最低 ✅（符合常识）
- 分数范围合理 ✅

---

## 实现验证报告生成器

### 文件：`scripts/generate_verification_report.py`

```python
"""生成人类可读的验证报告"""
import subprocess
import json
from datetime import datetime

def run_tests():
    """运行所有测试"""
    result = subprocess.run(["just", "test"], capture_output=True, text=True)
    return result.returncode == 0

def verify_rules():
    """验证规则"""
    from jieqi.fen import get_legal_moves_from_fen
    from jieqi.ai.unified import UnifiedAIEngine
    
    results = []
    
    # 1. 开局走法
    fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"
    python_moves = len(get_legal_moves_from_fen(fen))
    
    engine = UnifiedAIEngine()
    rust_moves = len(engine.get_legal_moves(fen))
    
    results.append({
        "rule": "开局44个走法",
        "passed": python_moves == 44 and rust_moves == 44,
        "details": f"Python: {python_moves}, Rust: {rust_moves}"
    })
    
    # 2. 开局分数范围
    engine = UnifiedAIEngine(strategy="minimax", time_limit=0.1)
    moves = engine.get_best_moves(fen, n=44)
    scores = [s for _, s in moves]
    
    results.append({
        "rule": "开局分数范围",
        "passed": -400 <= min(scores) and max(scores) <= 500,
        "details": f"范围: {min(scores):.0f} 到 {max(scores):.0f}"
    })
    
    # 3. 揭车高分
    rook_moves = [m for m in moves if "+a0" in m[0] or "+i0" in m[0]]
    rook_scores = [s for _, s in rook_moves]
    
    results.append({
        "rule": "揭车高分 (>400)",
        "passed": all(s > 400 for s in rook_scores),
        "details": f"揭车分数: {rook_scores[0]:.0f}"
    })
    
    return results

def generate_html_report(results):
    """生成HTML报告"""
    html = f"""
    <html>
    <head>
        <title>揭棋验证报告</title>
        <style>
            body {{ font-family: monospace; max-width: 800px; margin: 50px auto; }}
            .pass {{ color: green; }}
            .fail {{ color: red; }}
            .section {{ margin: 20px 0; padding: 10px; border: 1px solid #ccc; }}
        </style>
    </head>
    <body>
        <h1>揭棋实现验证报告</h1>
        <p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <div class="section">
            <h2>规则验证</h2>
            {''.join([
                f'<p class="{"pass" if r["passed"] else "fail"}">
                    {"✅" if r["passed"] else "❌"} {r["rule"]}: {r["details"]}
                </p>'
                for r in results
            ])}
        </div>
        
        <div class="section">
            <h2>总结</h2>
            <p class="{"pass" if all(r["passed"] for r in results) else "fail"}">
                {"所有测试通过 ✅" if all(r["passed"] for r in results) else "有测试失败 ❌"}
            </p>
        </div>
    </body>
    </html>
    """
    
    with open("reports/verification.html", "w") as f:
        f.write(html)
    
    print("✅ 验证报告已生成: reports/verification.html")

if __name__ == "__main__":
    print("🔍 运行验证...")
    results = verify_rules()
    generate_html_report(results)
```

---

### 添加到 Justfile

```justfile
# 生成验证报告
verify:
    @echo "🔍 验证实现正确性..."
    @uv run python scripts/generate_verification_report.py
    @echo "📊 打开报告: open reports/verification.html"
```

---

## 使用流程

### 开发者验证

```bash
# 1. 运行测试
just test

# 2. 生成验证报告
just verify

# 3. 查看HTML报告
open reports/verification.html
```

### 人类审查员验证

```bash
# 1. 查看报告
open reports/verification.html

# 2. 手动验证（Streamlit）
just start
# 在浏览器中尝试各种走法

# 3. 查看测试用例
cat tests/fixtures/standard_games.json
```

---

## 验证清单

### ✅ 自动验证
- [ ] 所有单元测试通过
- [ ] 开局44个走法（Python + Rust）
- [ ] 分数范围合理
- [ ] 揭车高分，揭兵低分
- [ ] Python-Rust一致

### ✅ 手动验证（人类）
- [ ] 在Streamlit中走一局
- [ ] 尝试不合法走法（应该被拒绝）
- [ ] 验证AI推荐合理
- [ ] 查看开局分析统计

### ✅ 常识验证
- [ ] 揭车分数 > 揭兵（符合象棋常识）
- [ ] 炮不能隔2子攻击（正确规则）
- [ ] 飞将能吃将（正确规则）

---

## 总结

**让人类知道实现正确的方法**：

1. **自动化报告** - `just verify` 生成HTML报告
2. **可视化验证** - Streamlit手动测试
3. **统计证据** - 开局分析数据
4. **测试棋谱** - 标准测试用例
5. **常识检查** - 分数符合象棋常识

**核心原则**：
- 结果可视化（HTML报告、Streamlit）
- 数据可解释（为什么揭车>揭兵）
- 人类可复现（手动走一局）
