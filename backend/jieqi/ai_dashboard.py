"""
揭棋 AI 测试仪表板

使用 Streamlit 构建的 AI 测试界面：
- 选择/输入 FEN 局面
- 可视化棋盘
- 选择 AI 后端（Python/Rust）
- 查看 AI 推荐走法

运行方式：
    cd backend && source .venv/bin/activate
    streamlit run jieqi/ai_dashboard.py --server.port 6710
"""

from __future__ import annotations

import streamlit as st

from jieqi.ai.unified import UnifiedAIEngine
from jieqi.fen import parse_fen
from jieqi.types import Color, PieceType, Position

# =============================================================================
# 常量和配置
# =============================================================================

# 棋子 Unicode 符号
PIECE_SYMBOLS = {
    (Color.RED, PieceType.KING): "帥",
    (Color.RED, PieceType.ROOK): "俥",
    (Color.RED, PieceType.HORSE): "傌",
    (Color.RED, PieceType.CANNON): "炮",
    (Color.RED, PieceType.ELEPHANT): "相",
    (Color.RED, PieceType.ADVISOR): "仕",
    (Color.RED, PieceType.PAWN): "兵",
    (Color.BLACK, PieceType.KING): "將",
    (Color.BLACK, PieceType.ROOK): "車",
    (Color.BLACK, PieceType.HORSE): "馬",
    (Color.BLACK, PieceType.CANNON): "砲",
    (Color.BLACK, PieceType.ELEPHANT): "象",
    (Color.BLACK, PieceType.ADVISOR): "士",
    (Color.BLACK, PieceType.PAWN): "卒",
}

# 预设测试局面
TEST_POSITIONS = {
    "初始局面": "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r",
    "车炮对决": "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r",
    "双车杀王": "4k4/9/9/9/9/9/9/9/4R4/3RK4 -:- r r",
    "马后炮": "3ak4/9/9/9/9/9/9/5C3/4H4/4K4 -:- r r",
    "兵临城下": "4k4/9/9/9/9/9/4P4/9/9/4K4 -:- r r",
    "揭棋中局1": "4k4/4x4/9/4X4/9/9/9/9/9/4K4 -:- r r",
    "揭棋中局2": "xxxx1xxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXX1XXXX -:- r r",
}

# 列号映射
COL_CHARS = "abcdefghi"


# =============================================================================
# 棋盘渲染
# =============================================================================


def render_board_html(fen: str, highlight_moves: list[tuple[str, float]] | None = None) -> str:
    """渲染棋盘为 HTML

    Args:
        fen: FEN 字符串
        highlight_moves: 需要高亮的走法 [(move_str, score), ...]

    Returns:
        HTML 字符串
    """
    state = parse_fen(fen)

    # 构建棋盘数组
    board: list[list[str]] = [["" for _ in range(9)] for _ in range(10)]

    for piece in state.pieces:
        row, col = piece.position.row, piece.position.col
        if piece.is_hidden:
            # 暗子
            symbol = "？" if piece.color == Color.RED else "？"
            color_class = "red-hidden" if piece.color == Color.RED else "black-hidden"
        else:
            # 明子
            symbol = PIECE_SYMBOLS.get((piece.color, piece.piece_type), "?")
            color_class = "red" if piece.color == Color.RED else "black"

        board[row][col] = f'<span class="piece {color_class}">{symbol}</span>'

    # 解析高亮走法
    highlight_from: set[tuple[int, int]] = set()
    highlight_to: set[tuple[int, int]] = set()

    if highlight_moves:
        for move_str, _ in highlight_moves:
            # 解析走法字符串
            mv = move_str.lstrip("+")
            if len(mv) >= 4:
                from_col = COL_CHARS.index(mv[0]) if mv[0] in COL_CHARS else -1
                from_row = int(mv[1]) if mv[1].isdigit() else -1
                to_col = COL_CHARS.index(mv[2]) if mv[2] in COL_CHARS else -1
                to_row = int(mv[3]) if mv[3].isdigit() else -1

                if from_row >= 0 and from_col >= 0:
                    highlight_from.add((from_row, from_col))
                if to_row >= 0 and to_col >= 0:
                    highlight_to.add((to_row, to_col))

    # 生成 HTML
    html = """
    <style>
        .board-container {
            font-family: 'Noto Sans SC', sans-serif;
            background: #f0d9b5;
            padding: 10px;
            border-radius: 8px;
            display: inline-block;
        }
        .board-table {
            border-collapse: collapse;
        }
        .board-table td {
            width: 50px;
            height: 50px;
            text-align: center;
            vertical-align: middle;
            border: 1px solid #b58863;
            font-size: 28px;
            position: relative;
        }
        .board-table .river {
            background: #d4e5f7;
            font-size: 14px;
            color: #666;
        }
        .piece {
            display: inline-block;
            width: 40px;
            height: 40px;
            line-height: 40px;
            border-radius: 50%;
            font-weight: bold;
        }
        .piece.red {
            background: #fff;
            color: #c00;
            border: 2px solid #c00;
        }
        .piece.black {
            background: #fff;
            color: #000;
            border: 2px solid #000;
        }
        .piece.red-hidden {
            background: #ffcccc;
            color: #c00;
            border: 2px dashed #c00;
        }
        .piece.black-hidden {
            background: #cccccc;
            color: #000;
            border: 2px dashed #000;
        }
        .highlight-from {
            background: #ffeb3b !important;
        }
        .highlight-to {
            background: #4caf50 !important;
        }
        .row-label, .col-label {
            font-size: 12px;
            color: #666;
            width: 25px;
            border: none !important;
        }
    </style>
    <div class="board-container">
        <table class="board-table">
    """

    # 从 row 9 到 row 0（上到下）
    for row in range(9, -1, -1):
        html += "<tr>"
        html += f'<td class="row-label">{row}</td>'

        for col in range(9):
            cell_class = ""
            if (row, col) in highlight_from:
                cell_class = "highlight-from"
            elif (row, col) in highlight_to:
                cell_class = "highlight-to"

            content = board[row][col]

            # 楚河汉界
            if row == 4 or row == 5:
                if not content:
                    if row == 4 and col == 4:
                        content = "楚河"
                    elif row == 5 and col == 4:
                        content = "漢界"

            html += f'<td class="{cell_class}">{content}</td>'

        html += "</tr>"

    # 列标签
    html += '<tr><td class="row-label"></td>'
    for col in range(9):
        html += f'<td class="col-label">{COL_CHARS[col]}</td>'
    html += "</tr>"

    html += """
        </table>
    </div>
    """

    return html


# =============================================================================
# Streamlit App
# =============================================================================


def main():
    st.set_page_config(page_title="揭棋 AI 测试", page_icon="♟️", layout="wide")

    st.title("♟️ 揭棋 AI 测试仪表板")
    st.markdown("测试不同 AI 后端（Python/Rust）在各种局面下的表现")

    # 侧边栏 - 配置
    with st.sidebar:
        st.header("⚙️ Configuration")

        # 选择预设局面或自定义
        position_choice = st.selectbox("Select Position", list(TEST_POSITIONS.keys()) + ["Custom"])

        if position_choice == "Custom":
            fen = st.text_input("FEN String", value=TEST_POSITIONS["初始局面"])
        else:
            fen = TEST_POSITIONS[position_choice]
            st.code(fen, language=None)

        st.divider()

        # AI 配置
        st.subheader("🤖 AI Settings")

        col1, col2 = st.columns(2)
        with col1:
            backend = st.selectbox("Backend", ["python", "rust"])
        with col2:
            depth = st.slider("Depth", 1, 5, 3)

        # 获取可用策略
        try:
            engine = UnifiedAIEngine(backend=backend)  # type: ignore
            available_strategies = engine.list_strategies()
        except Exception as e:
            st.error(f"Error loading strategies: {e}")
            available_strategies = ["greedy"]

        strategy = st.selectbox("Strategy", available_strategies)
        top_n = st.slider("Top N Moves", 1, 10, 5)

    # 主内容区
    col_board, col_analysis = st.columns([1, 1])

    with col_board:
        st.subheader("📋 Board")

        # 解析 FEN 显示基本信息
        try:
            state = parse_fen(fen)
            turn_str = "Red" if state.turn == Color.RED else "Black"
            viewer_str = "Red" if state.viewer == Color.RED else "Black"
            st.info(f"**Turn:** {turn_str} | **Viewer:** {viewer_str}")
        except Exception as e:
            st.error(f"Invalid FEN: {e}")
            return

    with col_analysis:
        st.subheader("🎯 AI Analysis")

        # 运行 AI
        if st.button("🚀 Run AI Analysis", type="primary"):
            with st.spinner(f"Running {backend} AI ({strategy})..."):
                try:
                    engine = UnifiedAIEngine(
                        backend=backend,  # type: ignore
                        strategy=strategy,
                        depth=depth,
                    )
                    moves = engine.get_best_moves(fen, top_n)

                    st.session_state["ai_moves"] = moves
                    st.session_state["ai_backend"] = backend
                    st.session_state["ai_strategy"] = strategy

                except Exception as e:
                    st.error(f"AI Error: {e}")
                    st.session_state["ai_moves"] = []

    # 显示 AI 结果
    ai_moves = st.session_state.get("ai_moves", [])

    with col_board:
        # 渲染棋盘（带高亮）
        board_html = render_board_html(fen, ai_moves if ai_moves else None)
        st.markdown(board_html, unsafe_allow_html=True)

    with col_analysis:
        if ai_moves:
            ai_backend = st.session_state.get("ai_backend", "")
            ai_strategy = st.session_state.get("ai_strategy", "")

            st.success(f"✅ Found {len(ai_moves)} moves (backend={ai_backend}, strategy={ai_strategy})")

            # 显示走法表格
            st.markdown("### Recommended Moves")

            for i, (move, score) in enumerate(ai_moves, 1):
                # 解析走法
                is_reveal = move.startswith("+")
                move_type = "揭子" if is_reveal else "走子"

                col_rank, col_move, col_score, col_type = st.columns([1, 2, 2, 1])
                with col_rank:
                    if i == 1:
                        st.markdown(f"**🥇 {i}**")
                    elif i == 2:
                        st.markdown(f"**🥈 {i}**")
                    elif i == 3:
                        st.markdown(f"**🥉 {i}**")
                    else:
                        st.markdown(f"**{i}**")
                with col_move:
                    st.code(move)
                with col_score:
                    st.metric("Score", f"{score:.1f}")
                with col_type:
                    st.caption(move_type)
        else:
            st.info("Click 'Run AI Analysis' to get AI recommendations")

    # 合法走法统计
    with st.expander("📊 Legal Moves Analysis"):
        try:
            engine = UnifiedAIEngine(backend=backend)  # type: ignore
            legal_moves = engine.get_legal_moves(fen)

            reveal_moves = [m for m in legal_moves if m.startswith("+")]
            regular_moves = [m for m in legal_moves if not m.startswith("+")]

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Moves", len(legal_moves))
            with col2:
                st.metric("Reveal Moves", len(reveal_moves))
            with col3:
                st.metric("Regular Moves", len(regular_moves))

            if reveal_moves:
                st.markdown("**Reveal Moves:**")
                st.code(" ".join(reveal_moves[:20]) + ("..." if len(reveal_moves) > 20 else ""))

            if regular_moves:
                st.markdown("**Regular Moves:**")
                st.code(" ".join(regular_moves[:20]) + ("..." if len(regular_moves) > 20 else ""))

        except Exception as e:
            st.error(f"Error: {e}")

    # 比较两个后端
    with st.expander("🔄 Compare Backends"):
        if st.button("Compare Python vs Rust"):
            with st.spinner("Comparing..."):
                col_py, col_rust = st.columns(2)

                with col_py:
                    st.markdown("### Python Backend")
                    try:
                        py_engine = UnifiedAIEngine(backend="python", strategy=strategy, depth=depth)
                        py_moves = py_engine.get_best_moves(fen, top_n)
                        for move, score in py_moves:
                            st.write(f"- `{move}` (score: {score:.1f})")
                    except Exception as e:
                        st.error(f"Error: {e}")

                with col_rust:
                    st.markdown("### Rust Backend")
                    try:
                        rust_engine = UnifiedAIEngine(backend="rust", strategy=strategy, depth=depth)
                        rust_moves = rust_engine.get_best_moves(fen, top_n)
                        for move, score in rust_moves:
                            st.write(f"- `{move}` (score: {score:.1f})")
                    except Exception as e:
                        st.error(f"Error: {e}")


if __name__ == "__main__":
    main()
