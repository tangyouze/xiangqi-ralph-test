"""
AI 对战调试页面

功能：
- 选择残局或输入 FEN 作为起始局面
- 红方/黑方各自选择 AI 策略
- 快速运行完整对弈
- 回放 Debug：逐步查看每步详细信息
- 键盘控制：←/→ 前进后退
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from engine.battle import run_battle
from engine.fen import fen_to_canvas_html
from engine.games.endgames import ALL_ENDGAMES
from engine.games.midgames_revealed import ALL_MIDGAME_POSITIONS
from engine.rust_ai import DEFAULT_STRATEGY
from engine.types import Color, PieceType

# =============================================================================
# 常量
# =============================================================================

AVAILABLE_STRATEGIES = [
    "it2",
    "muses3",
    "muses2",
    "muses",
    "iterative",
    "mcts",
    "greedy",
    "random",
]

# 棋子中文名映射
PIECE_TYPE_TO_CHINESE = {
    PieceType.ROOK: ("車", "车"),
    PieceType.HORSE: ("馬", "马"),
    PieceType.ELEPHANT: ("象", "相"),
    PieceType.ADVISOR: ("士", "仕"),
    PieceType.KING: ("帥", "将"),
    PieceType.CANNON: ("炮", "砲"),
    PieceType.PAWN: ("兵", "卒"),
}

# FEN 中被吃子解析
RED_PIECE_CHINESE = {"R": "車", "H": "馬", "E": "象", "A": "士", "K": "帥", "C": "炮", "P": "兵"}
BLACK_PIECE_CHINESE = {"r": "车", "h": "马", "e": "相", "a": "仕", "k": "将", "c": "砲", "p": "卒"}


# =============================================================================
# Session State
# =============================================================================


def init_session_state():
    """初始化 session state"""
    # 设置
    if "red_strategy" not in st.session_state:
        st.session_state.red_strategy = DEFAULT_STRATEGY
    if "black_strategy" not in st.session_state:
        st.session_state.black_strategy = DEFAULT_STRATEGY
    if "time_limit" not in st.session_state:
        st.session_state.time_limit = 0.2  # 降低默认时间，加快对弈
    if "battle_fen" not in st.session_state:
        st.session_state.battle_fen = ALL_ENDGAMES[0].fen
    if "endgame_idx" not in st.session_state:
        st.session_state.endgame_idx = 0

    # 对弈状态
    if "battle_history" not in st.session_state:
        st.session_state.battle_history = []
    if "battle_result" not in st.session_state:
        st.session_state.battle_result = None
    if "playback_idx" not in st.session_state:
        st.session_state.playback_idx = 0
    if "is_running" not in st.session_state:
        st.session_state.is_running = False


# =============================================================================
# 辅助函数
# =============================================================================


def piece_to_chinese(piece_type: PieceType, color: Color, is_hidden: bool = False) -> str:
    """棋子转中文名"""
    red_name, black_name = PIECE_TYPE_TO_CHINESE.get(piece_type, ("?", "?"))
    name = red_name if color == Color.RED else black_name
    prefix = "暗" if is_hidden else ""
    return f"{prefix}{name}"


def parse_captured_pieces(fen: str) -> tuple[str, str]:
    """解析 FEN 中的被吃子信息，返回 (红方吃的黑子, 黑方吃的红子)"""
    parts = fen.split(" ")
    if len(parts) < 2:
        return "", ""

    captured_part = parts[1]
    if captured_part == "-:-":
        return "", ""

    red_captured, black_captured = "", ""
    if ":" in captured_part:
        red_lost, black_lost = captured_part.split(":")
        # 红方被吃 = 黑方吃的
        for ch in red_lost:
            if ch == "?":
                black_captured += "暗"
            elif ch.upper() in RED_PIECE_CHINESE:
                black_captured += RED_PIECE_CHINESE[ch.upper()]
        # 黑方被吃 = 红方吃的
        for ch in black_lost:
            if ch == "?":
                red_captured += "暗"
            elif ch.lower() in BLACK_PIECE_CHINESE:
                red_captured += BLACK_PIECE_CHINESE[ch.lower()]

    return red_captured, black_captured


# =============================================================================
# UI 渲染
# =============================================================================


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        # 局面类型选择
        position_type = st.radio(
            "Position Type",
            ["Endgame", "Midgame"],
            horizontal=True,
            key="position_type",
        )

        if position_type == "Endgame":
            # 残局选择
            options = [f"{e.id} - {e.name}" for e in ALL_ENDGAMES]
            positions = ALL_ENDGAMES
        else:
            # 中局选择
            options = [f"{p.id} - {p.advantage.value}" for p in ALL_MIDGAME_POSITIONS]
            positions = ALL_MIDGAME_POSITIONS

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

        # 选择变化时更新 FEN
        if selected_idx != st.session_state.endgame_idx:
            st.session_state.endgame_idx = selected_idx
            st.session_state.battle_fen = positions[selected_idx].fen
            st.session_state.battle_history = []
            st.session_state.battle_result = None
            st.session_state.playback_idx = 0
            st.rerun()

        # AI 设置（紧凑布局）
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.red_strategy = st.selectbox(
                "Red",
                AVAILABLE_STRATEGIES,
                index=AVAILABLE_STRATEGIES.index(st.session_state.red_strategy),
            )
        with col2:
            st.session_state.black_strategy = st.selectbox(
                "Black",
                AVAILABLE_STRATEGIES,
                index=AVAILABLE_STRATEGIES.index(st.session_state.black_strategy),
            )

        # Run Battle 按钮
        if st.button("Run Battle", type="primary", width="stretch"):
            st.session_state.is_running = True
            st.rerun()

        # 显示对弈结果
        if st.session_state.battle_result:
            result = st.session_state.battle_result
            moves = len(st.session_state.battle_history) - 1
            if result == "red_win":
                st.success(f"Red wins! ({moves} moves)")
            elif result == "black_win":
                st.success(f"Black wins! ({moves} moves)")
            else:
                st.warning(f"Draw ({moves} moves)")

        # 高级选项（折叠）
        with st.expander("Advanced"):
            st.session_state.time_limit = st.slider(
                "Time (s)",
                0.1,
                5.0,
                st.session_state.time_limit,
                step=0.1,
            )
            fen_input = st.text_area(
                "FEN",
                value=st.session_state.battle_fen,
                height=60,
            )
            if fen_input != st.session_state.battle_fen:
                st.session_state.battle_fen = fen_input
                st.session_state.battle_history = []
                st.session_state.battle_result = None
                st.session_state.playback_idx = 0


def render_playback_controls():
    """渲染回放控制"""
    history = st.session_state.battle_history
    if not history:
        return

    total = len(history) - 1  # 排除初始状态
    idx = st.session_state.playback_idx

    # 按钮控制
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

    with col1:
        if st.button("⏮", key="btn_first", width="stretch"):
            st.session_state.playback_idx = 0
            st.rerun()

    with col2:
        if st.button("◀", key="btn_prev", width="stretch"):
            if idx > 0:
                st.session_state.playback_idx = idx - 1
                st.rerun()

    with col3:
        st.markdown(
            f"<div style='text-align: center; padding: 8px;'>Step: {idx}/{total}</div>",
            unsafe_allow_html=True,
        )

    with col4:
        if st.button("▶", key="btn_next", width="stretch"):
            if idx < total:
                st.session_state.playback_idx = idx + 1
                st.rerun()

    with col5:
        if st.button("⏭", key="btn_last", width="stretch"):
            st.session_state.playback_idx = total
            st.rerun()

    # 键盘监听 JavaScript
    keyboard_js = f"""
    <script>
    (function() {{
        if (window._jieqi_keyboard_listener) return;
        window._jieqi_keyboard_listener = true;

        document.addEventListener('keydown', function(e) {{
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            let newIdx = {idx};
            const total = {total};

            if (e.key === 'ArrowLeft') {{
                newIdx = Math.max(0, newIdx - 1);
            }} else if (e.key === 'ArrowRight') {{
                newIdx = Math.min(total, newIdx + 1);
            }} else if (e.key === 'Home') {{
                newIdx = 0;
            }} else if (e.key === 'End') {{
                newIdx = total;
            }} else {{
                return;
            }}

            if (newIdx !== {idx}) {{
                // 通过 URL 参数触发更新
                const url = new URL(window.location);
                url.searchParams.set('pidx', newIdx);
                window.location.href = url.toString();
            }}
        }});
    }})();
    </script>
    """
    components.html(keyboard_js, height=0)

    # 处理 URL 参数
    params = st.query_params
    if "pidx" in params:
        try:
            new_idx = int(params["pidx"])
            if 0 <= new_idx <= total and new_idx != idx:
                st.session_state.playback_idx = new_idx
                # 清除参数
                del st.query_params["pidx"]
                st.rerun()
        except ValueError:
            pass


def render_debug_info():
    """渲染 debug 信息"""
    history = st.session_state.battle_history
    if not history:
        # 没有对战记录时，显示当前选择的初始棋盘
        try:
            html = fen_to_canvas_html(st.session_state.battle_fen)
            components.html(html, height=280)
        except Exception:
            st.error("Invalid FEN")
        st.caption("Click 'Run Battle' to start")
        return

    idx = st.session_state.playback_idx
    step = history[idx]

    if idx == 0:
        # 初始局面：只显示棋盘
        try:
            html = fen_to_canvas_html(step["fen_after"])
            components.html(html, height=280)
        except Exception:
            pass
        st.caption("Initial position")
        return

    # 详细信息
    player = step["player"]
    move_num = step["move_num"]
    move = step["move"]
    score = step["score"]
    eval_before = step.get("eval_before", 0.0)
    candidates = step["candidates"]

    # 找出排名
    rank = next((i + 1 for i, c in enumerate(candidates) if c["move"] == move), 1)

    # 揭子/吃子信息
    extra = ""
    if step["revealed_type"]:
        try:
            pt = PieceType(step["revealed_type"])
            color = Color.RED if player == "red" else Color.BLACK
            extra += f" 揭:{piece_to_chinese(pt, color)}"
        except ValueError:
            pass
    if step["captured"] and step["captured"]["type"]:
        try:
            pt = PieceType(step["captured"]["type"])
            color = Color(step["captured"]["color"])
            was_hidden = step["captured"]["was_hidden"]
            extra += f" 吃:{piece_to_chinese(pt, color, was_hidden)}"
        except (ValueError, KeyError):
            pass

    # GitHub 风格紧凑布局：棋盘在左，信息在右
    color_dot = "🔴" if player == "red" else "⚫"

    col1, col2 = st.columns([1, 2])

    with col1:
        # 小棋盘（带箭头）
        try:
            html = fen_to_canvas_html(step["fen_before"], arrow=move)
            components.html(html, height=280)
        except Exception:
            pass

    with col2:
        # 紧凑信息
        st.markdown(
            f"{color_dot} **Step {move_num}** `{move}` {extra}",
        )
        st.caption(f"eval={eval_before:+.0f} → score={score:+.0f} ({rank}/{len(candidates)})")

        # 候选走法（默认折叠）
        with st.expander("Details", expanded=False):
            st.caption(
                f"depth={step.get('depth', 0)}  {step['time_ms']:.0f}ms  nodes={step['nodes']:,}"
            )
            red_cap, black_cap = parse_captured_pieces(step["fen_after"])
            if red_cap or black_cap:
                st.caption(f"红吃:{red_cap or '-'} | 黑吃:{black_cap or '-'}")
            for i, c in enumerate(candidates[:5]):
                marker = "→" if c["move"] == move else " "
                st.text(f"{marker} {i + 1}. {c['move']:8} {c['score']:+.1f}")


# =============================================================================
# Main
# =============================================================================


def main():
    st.set_page_config(
        page_title="Jieqi AI Battle",
        page_icon="🎮",
        layout="wide",
    )

    st.title("🎮 Jieqi AI Battle")

    init_session_state()
    render_sidebar()

    # 运行对弈
    if st.session_state.is_running:
        st.session_state.is_running = False

        # 使用 status 容器显示实时进度
        status_container = st.status(
            f"⚔️ Battle: {st.session_state.red_strategy} vs {st.session_state.black_strategy}",
            expanded=True,
        )
        progress_placeholder = status_container.empty()
        moves_log = status_container.container()

        # 用于存储最近几步的走法
        recent_moves = []

        def update_progress(move_num, player, move_str, score):
            """进度回调：更新 UI 显示"""
            recent_moves.append(f"#{move_num} {player}: {move_str} ({score:+.0f})")
            # 只显示最近 8 步
            if len(recent_moves) > 8:
                recent_moves.pop(0)

            progress_placeholder.markdown(f"**Move #{move_num}** - {player.upper()} thinking...")
            moves_log.text("\n".join(recent_moves))

        battle_result = run_battle(
            start_fen=st.session_state.battle_fen,
            red_strategy=st.session_state.red_strategy,
            black_strategy=st.session_state.black_strategy,
            time_limit=st.session_state.time_limit,
            progress_callback=update_progress,
        )

        # 转换为兼容格式：添加初始状态到 history
        history = [
            {
                "move_num": 0,
                "player": None,
                "fen_before": None,
                "fen_after": st.session_state.battle_fen,
                "move": None,
                "score": None,
                "candidates": [],
                "revealed_type": None,
                "captured": None,
            }
        ]
        for step in battle_result.history:
            history.append(
                {
                    "move_num": step.move_num,
                    "player": step.player,
                    "fen_before": step.fen_before,
                    "fen_after": step.fen_after,
                    "move": step.move,
                    "score": step.score,
                    "eval_before": step.eval_before,
                    "eval_after": step.eval_after,
                    "depth": step.depth,
                    "nodes": step.nodes,
                    "nps": step.nps,
                    "time_ms": step.time_ms,
                    "candidates": step.candidates,
                    "revealed_type": step.revealed_type,
                    "captured": step.captured,
                }
            )
        result = battle_result.result

        # 更新最终状态
        result_text = {
            "red_win": "🔴 Red wins!",
            "black_win": "⚫ Black wins!",
            "draw": "🤝 Draw",
        }.get(result, result)
        status_container.update(
            label=f"✅ {result_text} ({battle_result.total_moves} moves)", state="complete"
        )

        st.session_state.battle_history = history
        st.session_state.battle_result = result
        st.session_state.playback_idx = len(history) - 1  # 跳到最后一步
        st.rerun()

    # 主区域
    render_playback_controls()
    render_debug_info()


if __name__ == "__main__":
    main()
