"""
搜索树可视化页面

展示 AI 搜索过程：
- 静态评估 vs 搜索评估
- MAX/MIN/CHANCE 节点
- 揭子走法的概率分布
"""

from __future__ import annotations

import streamlit as st

from jieqi.ai.unified import UnifiedAIEngine
from jieqi.fen import parse_move, to_fen
from jieqi.game import JieqiGame
from jieqi.types import Color

# =============================================================================
# 预设局面
# =============================================================================

PRESET_POSITIONS = {
    "Initial (all hidden)": "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r",
    "Mid-game (mixed)": "1pxxkxxAx/1p5r1/9/x1x1x1x1x/9/9/X1X1X1X1X/A8/9/1XXXKXXXX P:ap r r",
    "Simple capture": "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r",
}

# =============================================================================
# 核心函数
# =============================================================================


def get_legal_moves(fen: str) -> list[str]:
    """获取所有合法走法"""
    engine = UnifiedAIEngine()
    return engine.get_legal_moves(fen)


def get_search_scores(fen: str, time_limit: float = 0.5) -> list[tuple[str, float]]:
    """获取所有走法的搜索分数"""
    engine = UnifiedAIEngine(strategy="iterative", time_limit=time_limit)
    # 获取所有走法的分数
    moves = engine.get_best_moves(fen, n=100)
    return moves


def apply_move(fen: str, move: str) -> str | None:
    """执行走法，返回新 FEN"""
    try:
        game = JieqiGame.from_fen(fen)
        mv, reveal_type = parse_move(move)
        reveal_type_str = reveal_type.value if reveal_type else None
        success = game.make_move(mv, reveal_type=reveal_type_str)
        if success:
            return to_fen(game.get_view(game.current_turn))
        return None
    except Exception:
        return None


def is_reveal_move(move: str) -> bool:
    """判断是否是揭子走法（以 + 开头）"""
    return move.startswith("+")


def get_move_type(move: str) -> str:
    """获取走法类型"""
    return "CHANCE" if is_reveal_move(move) else "MOVE"


# =============================================================================
# UI
# =============================================================================


def init_session_state():
    """初始化 session state"""
    if "search_fen" not in st.session_state:
        st.session_state.search_fen = PRESET_POSITIONS["Initial (all hidden)"]
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "selected_move" not in st.session_state:
        st.session_state.selected_move = None
    if "layer2_results" not in st.session_state:
        st.session_state.layer2_results = None


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("Settings")

        # 预设局面选择
        preset = st.selectbox(
            "Preset Position",
            options=list(PRESET_POSITIONS.keys()),
            index=0,
        )

        if st.button("Load Preset"):
            st.session_state.search_fen = PRESET_POSITIONS[preset]
            st.session_state.search_results = None
            st.session_state.selected_move = None
            st.session_state.layer2_results = None

        st.divider()

        # FEN 输入
        fen_input = st.text_area(
            "FEN",
            value=st.session_state.search_fen,
            height=80,
        )
        st.session_state.search_fen = fen_input

        # 搜索时间
        time_limit = st.slider(
            "Search Time (s)",
            min_value=0.1,
            max_value=3.0,
            value=0.5,
            step=0.1,
        )

        st.divider()

        # 分析按钮
        if st.button("Analyze", type="primary", use_container_width=True):
            with st.spinner("Searching..."):
                try:
                    results = get_search_scores(fen_input, time_limit)
                    st.session_state.search_results = results
                    st.session_state.selected_move = None
                    st.session_state.layer2_results = None
                except Exception as e:
                    st.error(f"Error: {e}")


def render_current_position():
    """渲染当前局面评估"""
    results = st.session_state.search_results
    if results is None:
        st.info("Click 'Analyze' to start search")
        return

    st.subheader("Current Position")

    if results:
        best_move, best_score = results[0]
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Best Move", best_move)
        with col2:
            color = "green" if best_score > 0 else "red" if best_score < 0 else "gray"
            st.metric("Search Score", f"{best_score:+.1f}")

        # 当前玩家
        try:
            game = JieqiGame.from_fen(st.session_state.search_fen)
            turn = "Red (MAX)" if game.current_turn == Color.RED else "Black (MAX)"
            st.caption(f"Current turn: {turn}")
        except Exception:
            pass
    else:
        st.warning("No legal moves!")


def render_layer1():
    """渲染第 1 层走法"""
    results = st.session_state.search_results
    if results is None:
        return

    st.subheader("Layer 1 - MAX (pick highest)")

    # 构建表格数据
    table_data = []
    for move, score in results:
        move_type = get_move_type(move)
        table_data.append(
            {
                "Move": move,
                "Type": move_type,
                "Search Score": f"{score:+.1f}",
            }
        )

    # 显示表格
    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
    )

    # 选择走法展开第 2 层
    st.divider()
    move_options = [m for m, _ in results[:10]]  # 只显示前 10 个
    if move_options:
        selected = st.selectbox(
            "Select move to expand Layer 2",
            options=["(none)"] + move_options,
            index=0,
        )

        if selected != "(none)" and st.button("Expand Layer 2"):
            new_fen = apply_move(st.session_state.search_fen, selected)
            if new_fen:
                with st.spinner("Searching layer 2..."):
                    layer2 = get_search_scores(new_fen, 0.3)
                    st.session_state.selected_move = selected
                    st.session_state.layer2_results = layer2
            else:
                st.error("Failed to apply move")


def render_layer2():
    """渲染第 2 层走法"""
    if st.session_state.selected_move is None:
        return

    results = st.session_state.layer2_results
    if results is None:
        return

    move = st.session_state.selected_move
    move_type = get_move_type(move)

    st.subheader(f"Layer 2 - MIN (after {move})")

    if move_type == "CHANCE":
        st.caption("Note: CHANCE node - showing one possible outcome")

    # 构建表格数据
    table_data = []
    for mv, score in results[:15]:  # 显示前 15 个
        mv_type = get_move_type(mv)
        # MIN 节点：对手视角，分数取反显示
        table_data.append(
            {
                "Move": mv,
                "Type": mv_type,
                "Search Score": f"{score:+.1f}",
                "Our View": f"{-score:+.1f}",
            }
        )

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
    )

    if results:
        # MIN 选择最低分（对手最佳）
        best_opp_move, best_opp_score = results[0]
        st.caption(f"Opponent's best: {best_opp_move} (our view: {-best_opp_score:+.1f})")


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
            - **MOVE**: Regular move (revealed piece)
            - **CHANCE**: Reveal move (hidden piece) - AI considers all possible piece types
            - **Search Score**: Score after searching N layers ahead
            - **Our View**: Score from current player's perspective (negated for MIN layer)

            **MAX node**: Pick the move with highest score
            **MIN node**: Opponent picks the move that minimizes our score
            """
        )


if __name__ == "__main__":
    main()
