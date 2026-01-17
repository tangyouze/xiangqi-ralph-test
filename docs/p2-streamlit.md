# Streamlit 揭棋应用

## 功能需求

### Game 页面 (核心功能)

#### 1. 游戏模式
- Human vs AI：人类走红方，AI 走黑方

#### 2. 棋盘显示
- 9x10 的标准中国象棋棋盘
- 棋子区分颜色：
  - 红方：红色边框和文字
  - 黑方：黑色/深灰边框和文字
- 暗子显示为"暗"字，用虚线边框
- 可走位置用绿色高亮

#### 3. AI 设置
- Strategy 选择：it2 (默认), muses, iterative, random 等
- Time 滑块：0.1 - 10 秒

#### 4. AI 统计显示
每步 AI 走完后显示：
- Move：走法 (如 `+e0e1`)
- Score：评分
- Nodes：搜索节点数
- NPS：每秒节点数

#### 5. 游戏信息
- 当前步数
- 轮到谁走
- 红/黑方剩余暗子数
- 游戏结果（红胜/黑胜/和棋）

#### 6. 走子历史 (可选)
- 可折叠的走法列表

#### 7. 被吃棋子 (可选)
- 显示双方被吃的棋子

---

## 技术实现

### 棋子样式
由于 Streamlit 的 `st.button` 不支持自定义 HTML 属性，需要通过以下方式实现棋子颜色：

**方案 A：JavaScript 注入**
```python
# 收集每个按钮的样式信息
piece_styles = {"cell_9_0": "red", "cell_9_1": "black-hidden", ...}

# 注入 JavaScript 在页面加载后修改按钮样式
st.markdown(f"""
<script>
const styles = {json.dumps(piece_styles)};
// 遍历并应用样式...
</script>
""", unsafe_allow_html=True)
```

**方案 B：使用 streamlit-extras 或自定义组件**

### 文件结构
```
streamlit_app.py      # 主入口（简单介绍页）
pages/
  1_Game.py           # 游戏页面（核心功能）
```

### 依赖
- streamlit
- jieqi (本地模块)

---

## TODO

- [ ] 修复棋子颜色样式（Streamlit button 不支持自定义属性）
- [ ] 添加走子动画
- [ ] 保存/加载游戏
