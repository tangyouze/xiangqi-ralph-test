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

import time

import streamlit as st
import streamlit.components.v1 as components

from engine.fen import apply_move_with_capture, fen_to_canvas_html, parse_fen
from engine.games.endgames import ALL_ENDGAMES
from engine.rust_ai import DEFAULT_STRATEGY, UnifiedAIEngine
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
# 核心功能
# =============================================================================


def run_full_battle(
    start_fen: str,
    red_strategy: str,
    black_strategy: str,
    time_limit: float,
    max_moves: int = 200,
    progress_callback=None,
):
    """运行完整对弈，返回 (battle_history, result)

    基于 FEN 进行对弈，不需要 JieqiGame。
    progress_callback: 回调函数 (move_num, player, move_str, score) 用于更新进度
    """
    # 创建 AI 引擎
    red_ai = UnifiedAIEngine(strategy=red_strategy, time_limit=time_limit)
    black_ai = UnifiedAIEngine(strategy=black_strategy, time_limit=time_limit)

    history = []

    # 记录初始状态（步数 0）
    history.append(
        {
            "move_num": 0,
            "player": None,
            "strategy": None,
            "fen_before": None,
            "fen_after": start_fen,
            "move": None,
            "score": None,
            "nodes": 0,
            "nps": 0.0,
            "time_ms": 0.0,
            "candidates": [],
            "revealed_type": None,
            "captured": None,
        }
    )

    current_fen = start_fen
    move_count = 0
    result = "ongoing"

    # 用于检测重复局面
    repetition_count = {}

    while move_count < max_moves:
        # 解析当前回合
        state = parse_fen(current_fen)
        current_turn = state.turn
        current_ai = red_ai if current_turn == Color.RED else black_ai
        strategy_name = red_strategy if current_turn == Color.RED else black_strategy
        player = "red" if current_turn == Color.RED else "black"

        # 计时并获取最佳走法
        start_time = time.time()
        try:
            candidates, nodes, nps = current_ai.get_best_moves_with_stats(current_fen, n=20)
        except Exception:
            # AI 报错，可能是游戏结束
            result = "draw"
            break
        elapsed_ms = (time.time() - start_time) * 1000

        if not candidates:
            # 没有合法走法，判断输赢
            # 当前方无走法 = 当前方输
            result = "black_win" if player == "red" else "red_win"
            break

        # 选择走法
        move_str, score = candidates[0]

        # 检查是否是揭子走法
        is_reveal = move_str.startswith("+")
        revealed_type = None
        if is_reveal and "=" in move_str:
            # 走法中包含揭子类型，如 "+a0a1=R"
            revealed_type = move_str.split("=")[1].lower()

        # 应用走法得到新 FEN
        try:
            new_fen, captured_info = apply_move_with_capture(current_fen, move_str)
        except Exception:
            # 走法执行失败
            result = "draw"
            break

        move_count += 1

        # 记录这一步
        step = {
            "move_num": move_count,
            "player": player,
            "strategy": strategy_name,
            "fen_before": current_fen,
            "fen_after": new_fen,
            "move": move_str,
            "score": score,
            "nodes": nodes,
            "nps": nps,
            "time_ms": elapsed_ms,
            "candidates": [{"move": m, "score": s} for m, s in candidates],
            "revealed_type": revealed_type,
            "captured": captured_info,
        }
        history.append(step)

        # 回调进度更新
        if progress_callback:
            progress_callback(move_count, player, move_str, score)

        # 检查游戏是否结束（通过吃将判断）
        if captured_info and captured_info.get("type") == "king":
            # 吃到将/帅，游戏结束
            result = "red_win" if player == "red" else "black_win"
            break

        # 检测重复局面
        board_part = new_fen.split(" ")[0]  # 只比较棋盘部分
        repetition_count[board_part] = repetition_count.get(board_part, 0) + 1
        if repetition_count[board_part] >= 3:
            # 三次重复，判和
            result = "draw"
            break

        current_fen = new_fen

    # 如果还没结束但达到最大步数
    if result == "ongoing":
        result = "draw"

    return history, result


# =============================================================================
# UI 渲染
# =============================================================================


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("Settings")

        # 残局选择
        options = [f"{e.id} - {e.name} ({e.category})" for e in ALL_ENDGAMES]
        selected_idx = st.selectbox(
            "Position",
            options=range(len(options)),
            format_func=lambda i: options[i],
            index=st.session_state.endgame_idx,
            key="endgame_selector",
        )

        # 选择变化时更新 FEN
        if selected_idx != st.session_state.endgame_idx:
            st.session_state.endgame_idx = selected_idx
            st.session_state.battle_fen = ALL_ENDGAMES[selected_idx].fen
            st.session_state.battle_history = []
            st.session_state.battle_result = None
            st.session_state.playback_idx = 0
            st.rerun()

        st.divider()

        # FEN 输入
        fen_input = st.text_area(
            "FEN",
            value=st.session_state.battle_fen,
            height=80,
        )
        if fen_input != st.session_state.battle_fen:
            st.session_state.battle_fen = fen_input
            st.session_state.battle_history = []
            st.session_state.battle_result = None
            st.session_state.playback_idx = 0

        # 棋盘预览
        try:
            html = fen_to_canvas_html(st.session_state.battle_fen)
            components.html(html, height=230)
        except Exception:
            st.error("Invalid FEN")

        st.divider()

        # AI 设置
        st.subheader("AI Settings")

        col1, col2 = st.columns(2)
        with col1:
            st.session_state.red_strategy = st.selectbox(
                "Red AI",
                AVAILABLE_STRATEGIES,
                index=AVAILABLE_STRATEGIES.index(st.session_state.red_strategy),
            )
        with col2:
            st.session_state.black_strategy = st.selectbox(
                "Black AI",
                AVAILABLE_STRATEGIES,
                index=AVAILABLE_STRATEGIES.index(st.session_state.black_strategy),
            )

        st.session_state.time_limit = st.slider(
            "Time (s)",
            0.1,
            5.0,
            st.session_state.time_limit,
            step=0.1,
        )

        st.divider()

        # Run Battle 按钮
        if st.button("Run Battle", type="primary", width="stretch"):
            st.session_state.is_running = True
            st.rerun()

        # 显示对弈结果
        if st.session_state.battle_result:
            result = st.session_state.battle_result
            if result == "red_win":
                st.success(f"Result: Red wins! ({len(st.session_state.battle_history) - 1} moves)")
            elif result == "black_win":
                st.success(
                    f"Result: Black wins! ({len(st.session_state.battle_history) - 1} moves)"
                )
            else:
                st.warning(f"Result: Draw ({len(st.session_state.battle_history) - 1} moves)")


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
        if st.button("|<", key="btn_first", width="stretch"):
            st.session_state.playback_idx = 0
            st.rerun()

    with col2:
        if st.button("<", key="btn_prev", width="stretch"):
            if idx > 0:
                st.session_state.playback_idx = idx - 1
                st.rerun()

    with col3:
        st.markdown(
            f"<div style='text-align: center; padding: 8px;'>Step: {idx}/{total}</div>",
            unsafe_allow_html=True,
        )

    with col4:
        if st.button(">", key="btn_next", width="stretch"):
            if idx < total:
                st.session_state.playback_idx = idx + 1
                st.rerun()

    with col5:
        if st.button(">|", key="btn_last", width="stretch"):
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
        st.info("Click 'Run Battle' to start")
        return

    idx = st.session_state.playback_idx
    step = history[idx]

    # 当前步的棋盘
    fen_to_show = step["fen_after"]
    try:
        html = fen_to_canvas_html(fen_to_show)
        components.html(html, height=230)
    except Exception:
        st.error("Cannot render board")

    if idx == 0:
        st.caption("Initial position")
        return

    # 详细信息
    player = step["player"]
    strategy = step["strategy"]
    move_num = step["move_num"]

    # 标题行：#步数 颜色 策略
    color_tag = "red" if player == "red" else "blue"
    st.markdown(
        f"**#{move_num}** <span style='color:{color_tag}'>{player.upper()}</span> {strategy}",
        unsafe_allow_html=True,
    )

    # IN: FEN
    st.code(f"IN:  {step['fen_before']}", language=None)

    # 走法信息
    move = step["move"]
    score = step["score"]
    time_ms = step["time_ms"]
    nodes = step["nodes"]
    nps = step["nps"]
    candidates = step["candidates"]

    # 找出这步在候选中的排名
    rank = 1
    for i, c in enumerate(candidates):
        if c["move"] == move:
            rank = i + 1
            break

    # 揭子信息
    reveal_str = ""
    if step["revealed_type"]:
        try:
            pt = PieceType(step["revealed_type"])
            color = Color.RED if player == "red" else Color.BLACK
            reveal_str = f" 揭:{piece_to_chinese(pt, color)}"
        except ValueError:
            pass

    # 吃子信息
    capture_str = ""
    if step["captured"] and step["captured"]["type"]:
        try:
            pt = PieceType(step["captured"]["type"])
            color = Color(step["captured"]["color"])
            was_hidden = step["captured"]["was_hidden"]
            capture_str = f" 吃:{piece_to_chinese(pt, color, was_hidden)}"
        except (ValueError, KeyError):
            pass

    # 格式化数字
    nodes_str = f"{nodes:,}" if nodes else "0"
    nps_str = f"{nps:,.0f}" if nps else "0"

    st.markdown(
        f"`{move}` {rank}/{len(candidates)}  score=**{score:+.1f}**  {time_ms:.0f}ms  "
        f"nodes={nodes_str} nps={nps_str}{reveal_str}{capture_str}"
    )

    # 被吃子累计
    red_captured, black_captured = parse_captured_pieces(step["fen_after"])
    if red_captured or black_captured:
        parts = []
        if red_captured:
            parts.append(f"红吃: {red_captured}")
        if black_captured:
            parts.append(f"黑吃: {black_captured}")
        st.caption(" | ".join(parts))

    # FEN
    st.code(f"FEN: {step['fen_after']}", language=None)

    # 候选走法展开
    with st.expander(f"Candidates (Top {min(10, len(candidates))})", expanded=False):
        for i, c in enumerate(candidates[:10]):
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

        history, result = run_full_battle(
            st.session_state.battle_fen,
            st.session_state.red_strategy,
            st.session_state.black_strategy,
            st.session_state.time_limit,
            progress_callback=update_progress,
        )

        # 更新最终状态
        result_text = {
            "red_win": "🔴 Red wins!",
            "black_win": "⚫ Black wins!",
            "draw": "🤝 Draw",
        }.get(result, result)
        status_container.update(
            label=f"✅ {result_text} ({len(history) - 1} moves)", state="complete"
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
