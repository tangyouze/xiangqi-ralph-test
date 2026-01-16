"""
AI 分析页面

AI 测试界面：
- 选择/输入 FEN 局面
- 可视化棋盘
- 选择 AI 后端（Python/Rust）
- 查看 AI 推荐走法
"""

from __future__ import annotations

import streamlit as st

from jieqi.ai.unified import UnifiedAIEngine
from jieqi.fen import parse_fen
from jieqi.types import Color, PieceType

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

# 预设测试局面 - 按难度和类型分类
TEST_POSITIONS = {
    # === 基础局面 ===
    "初始局面": "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r",
    "揭棋中局（双方有暗子）": "xxxx1xxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXX1XXXX -:- r r",
    # === 杀法练习 ===
    "双车杀王": "4k4/9/9/9/9/9/9/9/4R4/3RK4 -:- r r",
    "马后炮": "3ak4/9/9/9/9/9/9/5C3/4H4/4K4 -:- r r",
    "铁门栓": "3k5/4a4/4R4/9/9/9/9/9/9/4K4 -:- r r",
    "闷杀（重炮杀）": "4k4/4C4/4C4/9/9/9/9/9/9/4K4 -:- r r",
    "车马冷着": "3k5/9/4H4/9/9/9/9/4R4/9/4K4 -:- r r",
    # === 残局 ===
    "车炮对决": "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r",
    "兵临城下": "4k4/9/9/9/9/9/4P4/9/9/4K4 -:- r r",
    "车兵对车": "4k4/9/4r4/9/9/9/4P4/9/4R4/4K4 -:- r r",
    "双炮胁士": "3ak4/4a4/9/9/9/9/9/4C4/4C4/4K4 -:- r r",
    # === 揭棋特殊局面 ===
    "红方有优势暗子": "4k4/4x4/9/4X4/9/9/9/9/9/4K4 -:- r r",
    "黑方有优势暗子": "4k4/9/9/9/9/9/4x4/9/9/4K4 -:- r b",
    "多暗子复杂局面": "x2k2x1x/9/1x2x2x1/9/9/9/1X2X2X1/9/X2K2X1X/9 -:- r r",
    # === AI 对抗测试 ===
    "中局对攻": "r2ak4/9/2h1e4/p3p4/9/6P2/P3P4/2H1E4/9/R2AK4 -:- r r",
    "复杂中局": "r1eak4/4a4/4e1h2/p1h1p3p/4c4/2P6/P3P3P/4E1H2/4A4/R2AK2R1 -:- r r",
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
            # 暗子 - 用不同符号区分红黑
            symbol = "暗" if piece.color == Color.RED else "暗"
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
            font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #f5e6d3 0%, #e8d4b8 100%);
            padding: 15px;
            border-radius: 12px;
            display: inline-block;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .board-table {
            border-collapse: collapse;
            background: #d4b896;
        }
        .board-table td {
            width: 52px;
            height: 52px;
            text-align: center;
            vertical-align: middle;
            border: 1px solid #8b6914;
            font-size: 26px;
            position: relative;
        }
        .board-table .river {
            background: #d4e5f7;
            font-size: 14px;
            color: #666;
        }
        .piece {
            display: inline-block;
            width: 42px;
            height: 42px;
            line-height: 42px;
            border-radius: 50%;
            font-weight: bold;
            font-size: 22px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .piece.red {
            background: linear-gradient(145deg, #fff5f5, #ffe0e0);
            color: #c00;
            border: 2px solid #c00;
        }
        .piece.black {
            background: linear-gradient(145deg, #f5f5f5, #e0e0e0);
            color: #000;
            border: 2px solid #333;
        }
        .piece.red-hidden {
            background: linear-gradient(145deg, #ffdddd, #ffaaaa);
            color: #900;
            border: 3px dashed #c00;
            font-size: 18px;
        }
        .piece.black-hidden {
            background: linear-gradient(145deg, #aaaaaa, #777777);
            color: #fff;
            border: 3px dashed #333;
            font-size: 18px;
        }
        .highlight-from {
            background: #fff59d !important;
            box-shadow: inset 0 0 8px #ffc107;
        }
        .highlight-to {
            background: #a5d6a7 !important;
            box-shadow: inset 0 0 8px #4caf50;
        }
        .row-label, .col-label {
            font-size: 12px;
            color: #666;
            width: 28px;
            border: none !important;
            background: transparent !important;
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
    st.set_page_config(page_title="AI Analysis", page_icon="🔍", layout="wide")

    st.title("AI Analysis Dashboard")
    st.markdown("Test AI on various positions (Rust backend)")

    # 侧边栏 - 配置
    with st.sidebar:
        st.header("Configuration")

        # 选择预设局面或自定义
        position_choice = st.selectbox("Select Position", list(TEST_POSITIONS.keys()) + ["Custom"])

        if position_choice == "Custom":
            fen = st.text_input("FEN String", value=TEST_POSITIONS["初始局面"])
        else:
            fen = TEST_POSITIONS[position_choice]
            st.code(fen, language=None)

        st.divider()

        # AI 配置
        st.subheader("AI Settings")

        depth = st.slider("Depth", 1, 5, 3)

        # 获取可用策略（仅 Rust 后端）
        try:
            engine = UnifiedAIEngine()
            available_strategies = engine.list_strategies()
        except Exception as e:
            st.error(f"Error loading strategies: {e}")
            available_strategies = ["greedy"]

        strategy = st.selectbox("Strategy", available_strategies)
        top_n = st.slider("Top N Moves", 1, 10, 5)

    # 主内容区
    col_board, col_analysis = st.columns([1, 1])

    with col_board:
        st.subheader("Board")

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
        st.subheader("AI Analysis")

        # 运行 AI（仅 Rust 后端）
        if st.button("Run AI Analysis", type="primary"):
            with st.spinner(f"Running Rust AI ({strategy})..."):
                try:
                    engine = UnifiedAIEngine(
                        strategy=strategy,
                        depth=depth,
                    )
                    moves = engine.get_best_moves(fen, top_n)

                    st.session_state["ai_moves"] = moves
                    st.session_state["ai_strategy"] = strategy

                except Exception as e:
                    st.error(f"AI Error: {e}")
                    st.session_state["ai_moves"] = []

    # 显示 AI 结果
    ai_moves = st.session_state.get("ai_moves", [])

    with col_board:
        # 渲染棋盘（根据选中的走法高亮）
        selected_idx = st.session_state.get("selected_move_idx", -1)
        if ai_moves and selected_idx >= 0 and selected_idx < len(ai_moves):
            # 只高亮选中的走法
            highlight = [ai_moves[selected_idx]]
        else:
            # 高亮所有走法或无高亮
            highlight = ai_moves if ai_moves else None
        board_html = render_board_html(fen, highlight)
        st.markdown(board_html, unsafe_allow_html=True)

    with col_analysis:
        if ai_moves:
            ai_strategy = st.session_state.get("ai_strategy", "")

            st.success(f"Found {len(ai_moves)} moves (strategy={ai_strategy})")

            # 走法选择器
            move_options = ["All Moves"] + [
                f"{i + 1}. {m} ({s:.1f})" for i, (m, s) in enumerate(ai_moves)
            ]
            selected = st.selectbox("Highlight Move", move_options, key="move_selector")

            if selected != "All Moves":
                # 解析选中的走法索引
                idx = int(selected.split(".")[0]) - 1
                st.session_state["selected_move_idx"] = idx
            else:
                st.session_state["selected_move_idx"] = -1

            # 显示走法表格
            st.markdown("### Recommended Moves")

            for i, (move, score) in enumerate(ai_moves, 1):
                # 解析走法
                is_reveal = move.startswith("+")
                move_type = "Reveal" if is_reveal else "Move"

                # 高亮选中的走法
                selected_idx = st.session_state.get("selected_move_idx", -1)
                is_selected = selected_idx == i - 1

                col_rank, col_move, col_score, col_type = st.columns([1, 2, 2, 1])
                with col_rank:
                    if i == 1:
                        rank_text = "1"
                    elif i == 2:
                        rank_text = "2"
                    elif i == 3:
                        rank_text = "3"
                    else:
                        rank_text = str(i)

                    if is_selected:
                        st.markdown(f"**-> {rank_text}**")
                    else:
                        st.markdown(f"**{rank_text}**")
                with col_move:
                    st.code(move)
                with col_score:
                    # 格式化分数显示
                    if abs(score) >= 10000:
                        score_text = "WIN" if score > 0 else "LOSE"
                    else:
                        score_text = f"{score:.1f}"
                    st.metric("Score", score_text)
                with col_type:
                    st.caption(move_type)
        else:
            st.info("Click 'Run AI Analysis' to get AI recommendations")

    # 合法走法统计
    with st.expander("Legal Moves Analysis"):
        try:
            engine = UnifiedAIEngine()
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


if __name__ == "__main__":
    main()
