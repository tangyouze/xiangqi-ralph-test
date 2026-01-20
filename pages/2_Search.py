"""
搜索树可视化页面

展示 AI 搜索过程：
- 静态评估 vs 搜索评估
- MAX/MIN/CHANCE 节点
- 对手最佳/最差应对
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from engine.fen import fen_to_canvas_html
from engine.games.endgames import ALL_ENDGAMES
from engine.games.midgames_revealed import ALL_MIDGAME_POSITIONS
from engine.game import JieqiGame
from engine.rust_ai import DEFAULT_STRATEGY, UnifiedAIEngine
from engine.types import Color


# =============================================================================
# UI
# =============================================================================


def init_session_state():
    """初始化 session state"""
    if "search_fen" not in st.session_state:
        st.session_state.search_fen = ALL_ENDGAMES[0].fen
    if "search_tree" not in st.session_state:
        st.session_state.search_tree = None
    if "selected_move_idx" not in st.session_state:
        st.session_state.selected_move_idx = None
    if "endgame_idx" not in st.session_state:
        st.session_state.endgame_idx = 0
    if "search_depth" not in st.session_state:
        st.session_state.search_depth = 2
    if "pending_analyze" not in st.session_state:
        st.session_state.pending_analyze = False


def do_analyze():
    """执行分析"""
    try:
        engine = UnifiedAIEngine(strategy=DEFAULT_STRATEGY)
        tree = engine.get_search_tree(
            st.session_state.search_fen, depth=st.session_state.search_depth
        )
        st.session_state.search_tree = tree
        st.session_state.selected_move_idx = None
    except Exception as e:
        st.error(f"Error: {e}")


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("Settings")

        # 合并所有局面：残局 + 中局
        all_positions = list(ALL_ENDGAMES) + list(ALL_MIDGAME_POSITIONS)
        options = []
        for p in ALL_ENDGAMES:
            options.append(f"{p.id} - {p.name} ({p.category})")
        for p in ALL_MIDGAME_POSITIONS:
            options.append(f"{p.id} - {p.advantage.value}")

        # 确保索引有效
        current_idx = st.session_state.endgame_idx
        if current_idx < 0 or current_idx >= len(options):
            current_idx = 0
            st.session_state.endgame_idx = 0

        selected_idx = st.selectbox(
            "Position",
            options=range(len(options)),
            format_func=lambda i: options[i],
            index=current_idx,
            key="position_selector",
        )

        # 选择变化时更新 FEN 并触发分析
        if selected_idx != st.session_state.endgame_idx:
            st.session_state.endgame_idx = selected_idx
            st.session_state.search_fen = all_positions[selected_idx].fen
            st.session_state.search_tree = None
            st.session_state.selected_move_idx = None
            st.session_state.pending_analyze = True
            st.rerun()

        st.divider()

        # FEN 输入（可手动编辑）
        fen_input = st.text_area(
            "FEN",
            value=st.session_state.search_fen,
            height=80,
        )
        # FEN 变化时触发分析
        if fen_input != st.session_state.search_fen:
            st.session_state.search_fen = fen_input
            st.session_state.search_tree = None
            st.session_state.selected_move_idx = None
            st.session_state.pending_analyze = True

        # 图形化棋盘展示（如果有搜索结果，显示最佳走法箭头）
        try:
            best_move = None
            tree = st.session_state.search_tree
            if tree and tree.get("first_moves"):
                best_move = tree["first_moves"][0]["move"]
            html = fen_to_canvas_html(st.session_state.search_fen, arrow=best_move)
            components.html(html, height=230)
        except Exception:
            pass  # FEN 无效时不显示

        st.divider()

        # 搜索深度
        depth = st.slider(
            "Search Depth",
            min_value=1,
            max_value=5,
            value=st.session_state.search_depth,
            step=1,
        )
        if depth != st.session_state.search_depth:
            st.session_state.search_depth = depth

        st.divider()

        # 分析按钮
        if st.button("Analyze", type="primary", width="stretch"):
            with st.spinner("Searching..."):
                do_analyze()

        # 自动分析（FEN 变化后）
        if st.session_state.pending_analyze:
            st.session_state.pending_analyze = False
            with st.spinner("Searching..."):
                do_analyze()


def render_current_position():
    """渲染当前局面评估"""
    tree = st.session_state.search_tree
    if tree is None:
        st.info("Click 'Analyze' to start search")
        return

    st.subheader("Current Position")

    first_moves = tree.get("first_moves", [])
    if first_moves:
        best = first_moves[0]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Static Eval", f"{tree.get('eval', 0):+.1f}")
        with col2:
            st.metric("Best Move", best["move"])
        with col3:
            st.metric("Best Score", f"{best['score']:+.1f}")
        with col4:
            st.metric("Nodes", f"{tree.get('nodes', 0):,}")

        # 当前玩家
        try:
            game = JieqiGame.from_fen(st.session_state.search_fen)
            turn = "Red (MAX)" if game.current_turn == Color.RED else "Black (MAX)"
            st.caption(f"Current turn: {turn} | Depth: {tree.get('depth', 0)}")
        except Exception:
            pass
    else:
        st.warning("No legal moves!")


def render_layer1():
    """渲染第 1 层走法"""
    tree = st.session_state.search_tree
    if tree is None:
        return

    first_moves = tree.get("first_moves", [])
    if not first_moves:
        return

    st.subheader("Layer 1 - All Moves (sorted by score)")

    # 构建表格数据
    table_data = []
    for i, mv in enumerate(first_moves):
        move_type = mv.get("type", "move").upper()
        eval_score = mv.get("eval", 0)
        search_score = mv.get("score", 0)
        # 标记 eval 和 score 差异大的走法（可能是陷阱）
        diff = abs(search_score - eval_score)
        trap_marker = "⚠️" if diff > 100 else ""
        table_data.append(
            {
                "#": i + 1,
                "Move": mv["move"],
                "Type": move_type,
                "Eval": f"{eval_score:+.1f}",
                "Score": f"{search_score:+.1f}",
                "Diff": f"{trap_marker}{diff:+.1f}" if diff > 50 else "",
            }
        )

    # 显示表格
    st.dataframe(
        table_data,
        width="stretch",
        hide_index=True,
        height=400,
    )

    # 选择走法展开第 2 层
    st.divider()
    move_options = [(i, m["move"]) for i, m in enumerate(first_moves[:15])]
    if move_options:
        selected = st.selectbox(
            "Select move to view opponent's responses",
            options=["(none)"] + [f"{i + 1}. {m}" for i, m in move_options],
            index=0,
        )

        if selected != "(none)":
            # 解析选中的索引
            idx = int(selected.split(".")[0]) - 1
            st.session_state.selected_move_idx = idx


def render_layer2():
    """渲染第 2 层走法（对手应对）"""
    tree = st.session_state.search_tree
    if tree is None:
        return

    idx = st.session_state.selected_move_idx
    if idx is None:
        st.info("Select a move from Layer 1 to see opponent's responses")
        return

    first_moves = tree.get("first_moves", [])
    if idx >= len(first_moves):
        return

    mv_info = first_moves[idx]
    move = mv_info["move"]
    move_type = mv_info.get("type", "move").upper()

    st.subheader(f"Layer 2 - After {move}")

    if move_type == "CHANCE":
        st.caption("CHANCE node - showing one possible outcome")

    # 显示当前走法的详细信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Move", move)
    with col2:
        st.metric("Eval (after)", f"{mv_info.get('eval', 0):+.1f}")
    with col3:
        st.metric("Score", f"{mv_info.get('score', 0):+.1f}")

    st.divider()

    # 对手最佳应对
    top10 = mv_info.get("opposite_top10", [])
    bottom10 = mv_info.get("opposite_bottom10", [])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Opponent's Best Responses (Top 10)**")
        if top10:
            data = []
            for m in top10:
                data.append(
                    {
                        "Move": m["move"],
                        "Type": m.get("type", "move").upper(),
                        "Eval": f"{m.get('eval', 0):+.1f}",
                        "Score": f"{m.get('score', 0):+.1f}",
                        "Our View": f"{-m.get('score', 0):+.1f}",
                    }
                )
            st.dataframe(data, width="stretch", hide_index=True)
        else:
            st.caption("No data (depth=1?)")

    with col2:
        st.markdown("**Opponent's Worst Responses (Bottom 10)**")
        if bottom10:
            data = []
            for m in bottom10:
                data.append(
                    {
                        "Move": m["move"],
                        "Type": m.get("type", "move").upper(),
                        "Eval": f"{m.get('eval', 0):+.1f}",
                        "Score": f"{m.get('score', 0):+.1f}",
                        "Our View": f"{-m.get('score', 0):+.1f}",
                    }
                )
            st.dataframe(data, width="stretch", hide_index=True)
        else:
            st.caption("No data (depth=1?)")


def main():
    st.set_page_config(
        page_title="Search Visualization",
        page_icon="🔍",
        layout="wide",
    )

    st.title("🔍 Search Tree Visualization")

    init_session_state()
    render_sidebar()

    # 主区域
    render_current_position()

    col1, col2 = st.columns(2)

    with col1:
        render_layer1()

    with col2:
        render_layer2()

    # 说明
    with st.expander("About Search Scores"):
        st.markdown(
            """
            **Column explanations:**
            - **Eval**: Static evaluation after this move (no further search)
            - **Score**: Search score (after looking N moves ahead)
            - **Diff**: Difference between Eval and Score. Large diff (⚠️) may indicate a trap move!
            - **Our View**: Score from current player's perspective (negated for opponent moves)

            **Node types:**
            - **MOVE**: Regular move with a revealed piece
            - **CHANCE**: Reveal move (hidden piece) - AI considers all possible piece types

            **Interpreting the data:**
            - A move with high Eval but low Score is a "trap" - looks good but opponent has a strong response
            - A move with low Eval but high Score is an "investment" - short-term sacrifice for long-term gain
            - Opponent's best responses show why a move's Score might differ from its Eval
            """
        )


if __name__ == "__main__":
    main()
