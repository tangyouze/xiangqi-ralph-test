"""
Game Logs Viewer

功能:
- 列出所有日志文件
- 按策略、日期筛选
- 显示摘要统计
- 查看单局详情
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from engine.fen import fen_to_canvas_html
from engine.game_log import list_logs, load_game, load_summary
from engine.ui import apply_compact_style

# =============================================================================
# Session State
# =============================================================================


def init_session_state():
    """初始化 session state"""
    if "selected_log" not in st.session_state:
        st.session_state.selected_log = None
    if "selected_game_id" not in st.session_state:
        st.session_state.selected_game_id = None
    if "playback_step" not in st.session_state:
        st.session_state.playback_step = 0
    if "result_filter" not in st.session_state:
        st.session_state.result_filter = ["red_win", "black_win", "draw"]


# =============================================================================
# UI Components
# =============================================================================


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("Logs")

        # 获取所有日志
        logs = list_logs()

        if not logs:
            st.info("No logs found in data/game_logs/")
            return

        # 筛选
        strategies = sorted(set(lg["strategy"] for lg in logs))
        selected_strategy = st.selectbox(
            "Strategy",
            options=["All"] + strategies,
            index=0,
        )

        if selected_strategy != "All":
            logs = [lg for lg in logs if lg["strategy"] == selected_strategy]

        # 日志列表
        st.divider()
        for lg in logs[:20]:  # 最多显示 20 条
            label = f"{lg['date']} | {lg['strategy']}"
            if st.button(label, key=lg["run_id"], width="stretch"):
                st.session_state.selected_log = lg["path"]
                st.session_state.selected_game_id = None
                st.session_state.playback_step = 0
                st.rerun()

        if len(logs) > 20:
            st.caption(f"... and {len(logs) - 20} more")


def render_summary(summary: dict):
    """渲染摘要信息"""
    results = summary["results"]
    total = summary["total_games"]
    config = summary["config"]

    # 标题
    st.subheader(f"{config['red_strategy']} vs {config['black_strategy']}")

    # 统计
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pct = 100 * results["red_win"] / total if total > 0 else 0
        st.metric("Red Win", f"{results['red_win']}", f"{pct:.1f}%")
    with col2:
        pct = 100 * results["black_win"] / total if total > 0 else 0
        st.metric("Black Win", f"{results['black_win']}", f"{pct:.1f}%")
    with col3:
        pct = 100 * results["draw"] / total if total > 0 else 0
        st.metric("Draw", f"{results['draw']}", f"{pct:.1f}%")
    with col4:
        duration_min = summary.get("duration_seconds", 0) / 60
        st.metric("Duration", f"{duration_min:.1f} min")

    # 配置信息
    st.caption(
        f"Time: {config.get('time_limit', 0.2)}s | "
        f"Max Moves: {config.get('max_moves', 100)} | "
        f"Total: {total} games"
    )


def render_games_table(summary: dict):
    """渲染对局列表"""
    games = summary["games"]

    # 筛选选项
    st.subheader("Games")

    col1, col2, col3 = st.columns(3)
    with col1:
        show_red = st.checkbox("Red Win", value="red_win" in st.session_state.result_filter)
    with col2:
        show_black = st.checkbox("Black Win", value="black_win" in st.session_state.result_filter)
    with col3:
        show_draw = st.checkbox("Draw", value="draw" in st.session_state.result_filter)

    # 更新筛选
    filters = []
    if show_red:
        filters.append("red_win")
    if show_black:
        filters.append("black_win")
    if show_draw:
        filters.append("draw")
    st.session_state.result_filter = filters

    # 筛选对局
    filtered = [g for g in games if g["result"] in filters]

    if not filtered:
        st.info("No games match the filter")
        return

    # 结果图标
    result_icons = {"red_win": "🔴", "black_win": "⚫", "draw": "🤝"}

    # 显示表格
    for game in filtered[:50]:  # 最多显示 50 条
        icon = result_icons.get(game["result"], "?")
        label = f"{icon} {game['id']} {game['name']} ({game['moves']} moves)"
        if st.button(label, key=f"game_{game['id']}", width="stretch"):
            st.session_state.selected_game_id = game["id"]
            st.session_state.playback_step = 0
            st.rerun()

    if len(filtered) > 50:
        st.caption(f"... and {len(filtered) - 50} more")


def render_game_detail(log_path, game_id: str):
    """渲染单局详情"""
    try:
        game = load_game(log_path, game_id)
    except Exception as e:
        st.error(f"Failed to load game: {e}")
        return

    st.subheader(f"{game['endgame_id']}: {game['name']}")

    # 返回按钮
    if st.button("← Back to list"):
        st.session_state.selected_game_id = None
        st.rerun()

    # 基本信息
    result_text = {"red_win": "🔴 Red Win", "black_win": "⚫ Black Win", "draw": "🤝 Draw"}
    st.markdown(f"**Result:** {result_text.get(game['result'], game['result'])}")
    st.caption(
        f"Moves: {game['total_moves']} | "
        f"Duration: {game['duration_ms']:.0f}ms | "
        f"Category: {game['category']}"
    )

    history = game.get("history", [])
    if not history:
        st.info("No move history available")
        return

    # 回放控制
    total = len(history)
    step = st.session_state.playback_step

    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

    with col1:
        if st.button("⏮", key="detail_first"):
            st.session_state.playback_step = 0
            st.rerun()

    with col2:
        if st.button("◀", key="detail_prev"):
            if step > 0:
                st.session_state.playback_step = step - 1
                st.rerun()

    with col3:
        st.markdown(
            f"<div style='text-align: center; padding: 8px;'>Step {step + 1}/{total}</div>",
            unsafe_allow_html=True,
        )

    with col4:
        if st.button("▶", key="detail_next"):
            if step < total - 1:
                st.session_state.playback_step = step + 1
                st.rerun()

    with col5:
        if st.button("⏭", key="detail_last"):
            st.session_state.playback_step = total - 1
            st.rerun()

    # 当前步骤
    if 0 <= step < total:
        move_data = history[step]
        fen = move_data.get("fen_before") or game["start_fen"]
        move = move_data.get("move", "")

        col1, col2 = st.columns([1, 2])

        with col1:
            try:
                html = fen_to_canvas_html(fen, arrow=move)
                components.html(html, height=280)
            except Exception:
                st.error("Failed to render board")

        with col2:
            player = move_data.get("player", "")
            color_dot = "🔴" if player == "red" else "⚫"
            score = move_data.get("score", 0)

            st.markdown(f"{color_dot} **Move {move_data.get('move_num', step + 1)}** `{move}`")
            st.caption(f"Score: {score:+.0f}")

            # 候选走法
            candidates = move_data.get("candidates", [])
            if candidates:
                with st.expander("Candidates", expanded=False):
                    for i, c in enumerate(candidates[:5]):
                        marker = "→" if c["move"] == move else " "
                        st.text(f"{marker} {i + 1}. {c['move']:8} {c['score']:+.1f}")


# =============================================================================
# Main
# =============================================================================


def main():
    st.set_page_config(
        page_title="Game Logs",
        page_icon="📋",
        layout="wide",
    )
    apply_compact_style()

    st.title("📋 Game Logs")

    init_session_state()
    render_sidebar()

    # 主区域
    if st.session_state.selected_log is None:
        st.info("Select a log from the sidebar to view details")
        return

    # 加载摘要
    try:
        summary = load_summary(st.session_state.selected_log)
    except Exception as e:
        st.error(f"Failed to load log: {e}")
        return

    # 显示内容
    if st.session_state.selected_game_id:
        render_game_detail(st.session_state.selected_log, st.session_state.selected_game_id)
    else:
        render_summary(summary)
        st.divider()
        render_games_table(summary)


if __name__ == "__main__":
    main()
