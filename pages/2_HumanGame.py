"""
人机对战页面 - 简化版

功能：
- 人执红，AI 执黑
- 点击按钮选择走法
- AI 自动响应
"""

from __future__ import annotations

import streamlit as st

from engine.fen import get_legal_moves_from_fen, apply_move_with_capture, parse_fen
from engine.games.endgames import ALL_ENDGAMES
from engine.games.midgames_revealed import ALL_MIDGAME_POSITIONS
from engine.rust_ai import UnifiedAIEngine, DEFAULT_STRATEGY
from engine.types import Color

# =============================================================================
# 常量
# =============================================================================

AVAILABLE_STRATEGIES = ["it2", "muses3", "muses2", "muses", "iterative", "greedy", "random"]

# 棋子符号（中文）
PIECE_CN = {
    "R": "車",
    "H": "馬",
    "E": "象",
    "A": "士",
    "K": "帥",
    "C": "炮",
    "P": "兵",
    "r": "车",
    "h": "马",
    "e": "相",
    "a": "仕",
    "k": "将",
    "c": "砲",
    "p": "卒",
    "X": "暗",
    "x": "暗",
}

COL_CHARS = "abcdefghi"

# 揭棋标准开局 FEN
STANDARD_FEN = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"


# =============================================================================
# Session State
# =============================================================================


def init_state():
    if "fen" not in st.session_state:
        st.session_state.fen = STANDARD_FEN
    if "selected" not in st.session_state:
        st.session_state.selected = None
    if "history" not in st.session_state:
        st.session_state.history = []
    if "message" not in st.session_state:
        st.session_state.message = ""
    if "game_over" not in st.session_state:
        st.session_state.game_over = None
    if "ai_pending" not in st.session_state:
        st.session_state.ai_pending = False
    if "strategy" not in st.session_state:
        st.session_state.strategy = DEFAULT_STRATEGY
    if "time_limit" not in st.session_state:
        st.session_state.time_limit = 1.0
    if "endgame_idx" not in st.session_state:
        st.session_state.endgame_idx = -1


def reset_game():
    idx = st.session_state.endgame_idx
    # idx = -1 表示标准开局
    # idx = 0~(len(ALL_ENDGAMES)-1) 表示残局
    # idx >= len(ALL_ENDGAMES) 表示中局
    if idx < 0:
        st.session_state.fen = STANDARD_FEN
    elif idx < len(ALL_ENDGAMES):
        st.session_state.fen = ALL_ENDGAMES[idx].fen
    else:
        midgame_idx = idx - len(ALL_ENDGAMES)
        st.session_state.fen = ALL_MIDGAME_POSITIONS[midgame_idx].fen
    st.session_state.selected = None
    st.session_state.history = []
    st.session_state.message = ""
    st.session_state.game_over = None
    st.session_state.ai_pending = False


# =============================================================================
# 游戏逻辑
# =============================================================================


def get_piece(fen: str, col: int, row: int) -> str | None:
    """获取位置的棋子"""
    rows = fen.split()[0].split("/")
    if row < 0 or row >= len(rows):
        return None
    c = 0
    for ch in rows[row]:
        if ch.isdigit():
            c += int(ch)
        else:
            if c == col:
                return ch
            c += 1
    return None


def get_targets(fen: str, col: int, row: int) -> list[tuple[int, int]]:
    """获取合法目标"""
    moves = get_legal_moves_from_fen(fen)
    pos = f"{COL_CHARS[col]}{9 - row}"
    targets = []
    for m in moves:
        clean = m.lstrip("+").split("=")[0]
        if clean[:2] == pos:
            targets.append((COL_CHARS.index(clean[2]), 9 - int(clean[3])))
    return targets


def make_move(fen: str, fc, fr, tc, tr) -> str:
    """生成走法字符串，暗子需要 + 前缀"""
    piece = get_piece(fen, fc, fr)
    base = f"{COL_CHARS[fc]}{9 - fr}{COL_CHARS[tc]}{9 - tr}"
    # 暗子走法需要 + 前缀
    if piece in ("X", "x"):
        return "+" + base
    return base


def check_over(fen: str, history: list, check_draw: bool = False) -> str | None:
    """检查游戏是否结束

    Args:
        check_draw: 是否检查和棋（只对 AI 强制）
    """
    board = fen.split()[0]
    if "K" not in board:
        return "black_win"
    if "k" not in board:
        return "red_win"
    if not get_legal_moves_from_fen(fen):
        return "black_win" if parse_fen(fen).turn == Color.RED else "red_win"

    # 和棋判断：同一局面出现3次（只对 AI 强制）
    if check_draw and len(history) >= 6:
        fen_board = fen.split()[0]
        count = sum(1 for h_fen, _, _ in history if h_fen.split()[0] == fen_board)
        if count >= 3:
            return "draw"

    return None


def ai_move():
    if not st.session_state.ai_pending:
        return
    st.session_state.ai_pending = False

    fen = st.session_state.fen
    ai = UnifiedAIEngine(strategy=st.session_state.strategy, time_limit=st.session_state.time_limit)
    # 获取多个候选走法，避免选择会导致和棋的走法
    moves = ai.get_best_moves(fen, n=5)

    chosen_move = None
    chosen_score = 0
    for move, score in moves:
        new_fen, _ = apply_move_with_capture(fen, move)
        # 模拟这步棋后的历史
        test_history = st.session_state.history + [(new_fen, move, "black")]
        over = check_over(new_fen, test_history, check_draw=True)
        if over != "draw":
            # 选择第一个不会导致和棋的走法
            chosen_move = move
            chosen_score = score
            break

    # 如果所有走法都会和棋，只能选第一个
    if chosen_move is None and moves:
        chosen_move, chosen_score = moves[0]

    if chosen_move:
        new_fen, _ = apply_move_with_capture(fen, chosen_move)
        st.session_state.fen = new_fen
        st.session_state.history.append((new_fen, chosen_move, "black"))
        st.session_state.message = f"AI: {chosen_move} ({chosen_score:+.0f})"
        over = check_over(new_fen, st.session_state.history, check_draw=True)
        if over:
            st.session_state.game_over = over


def handle_click(col: int, row: int):
    if st.session_state.game_over:
        return

    state = parse_fen(st.session_state.fen)
    if state.turn != Color.RED:
        return

    fen = st.session_state.fen
    sel = st.session_state.selected

    if sel is None:
        # 选择棋子
        piece = get_piece(fen, col, row)
        if piece and piece.isupper():
            targets = get_targets(fen, col, row)
            if targets:
                st.session_state.selected = (col, row)
                st.session_state.message = f"Selected {PIECE_CN.get(piece, piece)}"
            else:
                st.session_state.message = "No moves"
        else:
            st.session_state.message = "Click red piece"
    else:
        # 执行走法或切换
        fc, fr = sel
        targets = get_targets(fen, fc, fr)

        if (col, row) in targets:
            move = make_move(fen, fc, fr, col, row)
            new_fen, _ = apply_move_with_capture(fen, move)
            st.session_state.fen = new_fen
            st.session_state.history.append((new_fen, move, "red"))
            st.session_state.selected = None
            st.session_state.message = f"You: {move}"
            over = check_over(new_fen, st.session_state.history)
            if over:
                st.session_state.game_over = over
            else:
                st.session_state.ai_pending = True
        else:
            piece = get_piece(fen, col, row)
            if piece and piece.isupper():
                new_targets = get_targets(fen, col, row)
                if new_targets:
                    st.session_state.selected = (col, row)
                    st.session_state.message = f"Selected {PIECE_CN.get(piece, piece)}"
                else:
                    st.session_state.selected = None
                    st.session_state.message = "No moves"
            else:
                st.session_state.selected = None
                st.session_state.message = "Cancelled"


# =============================================================================
# UI
# =============================================================================


def render_board():
    """渲染棋盘 - 传统象棋棋盘样式"""
    fen = st.session_state.fen
    sel = st.session_state.selected
    targets = get_targets(fen, sel[0], sel[1]) if sel else []

    # 棋盘 CSS - 圆形棋子样式，限制宽度
    st.markdown(
        """
    <style>
    /* 限制棋盘区域宽度 */
    [data-testid="stMainBlockContainer"] > div {
        max-width: 600px !important;
    }
    /* 强制按钮变成圆形棋子 */
    [data-testid="stHorizontalBlock"] {
        gap: 0 !important;
        justify-content: center !important;
    }
    .stButton > button {
        border-radius: 50% !important;
        width: 48px !important;
        height: 48px !important;
        min-width: 48px !important;
        max-width: 48px !important;
        min-height: 48px !important;
        padding: 0 !important;
        font-size: 20px !important;
        font-weight: bold !important;
        box-shadow: 2px 2px 4px rgba(0,0,0,0.3) !important;
    }
    /* 红方棋子 */
    .stButton [data-testid="stBaseButton-primary"] {
        background: linear-gradient(145deg, #fff8dc, #ffe4b5) !important;
        border: 3px solid #c41e3a !important;
        color: #c41e3a !important;
    }
    /* 黑方棋子 */
    .stButton [data-testid="stBaseButton-secondary"] {
        background: linear-gradient(145deg, #fff8dc, #ffe4b5) !important;
        border: 2px solid #654321 !important;
        color: #1a1a1a !important;
    }
    /* 空位 */
    .stButton [data-testid="stBaseButton-secondary"]:has(p:empty),
    .stButton button:has(p:empty) {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    .board-label {
        text-align: center;
        font-weight: bold;
        color: #8b4513;
        font-size: 12px;
        line-height: 48px;
        width: 24px !important;
    }
    /* 楚河汉界 */
    .river-row {
        text-align: center;
        font-size: 16px;
        color: #8b4513;
        font-weight: bold;
        letter-spacing: 12px;
        padding: 4px 0;
        background: #f5deb3;
        max-width: 500px;
        margin: 0 auto;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # 使用固定宽度列配置
    col_widths = [0.3] + [1] * 9 + [0.3]

    # 列标签
    label_cols = st.columns(col_widths)
    label_cols[0].write("")
    for i, c in enumerate("abcdefghi"):
        label_cols[i + 1].markdown(f"<div class='board-label'>{c}</div>", unsafe_allow_html=True)
    label_cols[10].write("")

    # 棋盘行
    for row in range(10):
        # 楚河汉界 - 在第5行之前
        if row == 5:
            st.markdown(
                "<div class='river-row'>楚 河 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 汉 界</div>",
                unsafe_allow_html=True,
            )

        cols = st.columns(col_widths)
        cols[0].markdown(f"<div class='board-label'>{9 - row}</div>", unsafe_allow_html=True)

        for col in range(9):
            piece = get_piece(fen, col, row)
            is_selected = sel == (col, row)
            is_target = (col, row) in targets

            if piece:
                is_red = piece.isupper()
                label = PIECE_CN.get(piece, piece)
                btn_type = "primary" if is_red else "secondary"
            else:
                label = "●" if is_target else ""
                btn_type = "secondary"

            # 选中标记
            if is_selected:
                label = f"○{label}"

            with cols[col + 1]:
                if st.button(label, key=f"btn_{row}_{col}", type=btn_type, width="stretch"):
                    handle_click(col, row)
                    st.rerun()

        cols[10].markdown(f"<div class='board-label'>{9 - row}</div>", unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.subheader("Game")

        # 按钮行
        col1, col2 = st.columns(2)
        with col1:
            if st.button("New", type="primary", width="stretch"):
                reset_game()
                st.rerun()
        with col2:
            if st.button("Undo", width="stretch", disabled=len(st.session_state.history) < 2):
                st.session_state.history.pop()
                st.session_state.history.pop()
                if st.session_state.history:
                    st.session_state.fen = st.session_state.history[-1][0]
                else:
                    reset_game()
                st.session_state.selected = None
                st.session_state.game_over = None
                st.rerun()

        st.divider()

        # 走法历史
        st.subheader("History")
        if st.session_state.history:
            history_text = []
            for i, (_, move, side) in enumerate(st.session_state.history):
                prefix = "R" if side == "red" else "B"
                history_text.append(f"{i + 1}. {prefix}: {move}")
            # 显示最近10步
            st.text("\n".join(history_text[-10:]))
        else:
            st.caption("No moves yet")

        st.divider()

        # 设置
        st.subheader("Settings")

        # 合并所有局面：标准开局 + 残局 + 中局
        all_positions = list(ALL_ENDGAMES) + list(ALL_MIDGAME_POSITIONS)
        options = ["Standard (揭棋开局)"]
        for p in ALL_ENDGAMES:
            options.append(f"{p.id} - {p.name}")
        for p in ALL_MIDGAME_POSITIONS:
            options.append(f"{p.id} - {p.advantage.value}")

        # 确保索引有效（-1 表示标准开局，对应 options[0]）
        current_idx = st.session_state.endgame_idx + 1  # -1 -> 0, 0 -> 1, ...
        if current_idx < 0 or current_idx >= len(options):
            current_idx = 0

        selected_idx = st.selectbox(
            "Position",
            options=range(len(options)),
            format_func=lambda i: options[i],
            index=current_idx,
            key="position_selector",
        )

        # 选择变化时更新
        new_endgame_idx = selected_idx - 1  # 0 -> -1 (Standard), 1 -> 0, ...
        if new_endgame_idx != st.session_state.endgame_idx:
            st.session_state.endgame_idx = new_endgame_idx
            reset_game()
            st.rerun()

        # FEN 输入（可手动编辑）
        fen_input = st.text_area(
            "FEN",
            value=st.session_state.fen,
            height=60,
        )
        if fen_input != st.session_state.fen:
            st.session_state.fen = fen_input
            st.session_state.selected = None
            st.session_state.history = []
            st.session_state.message = ""
            st.session_state.game_over = None

        st.divider()

        # AI 设置
        st.session_state.strategy = st.selectbox("AI Strategy", AVAILABLE_STRATEGIES)
        st.session_state.time_limit = st.slider("Think Time (s)", 0.1, 3.0, 1.0, step=0.1)


def main():
    st.set_page_config(page_title="Human vs AI", layout="wide")

    init_state()
    render_sidebar()

    # AI 回合处理（先处理，避免 spinner 导致布局抖动）
    if st.session_state.ai_pending:
        ai_move()
        st.rerun()

    # 标题栏 - 固定高度避免抖动
    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        st.markdown("### Human vs AI")
    with col2:
        state = parse_fen(st.session_state.fen)
        turn = "Red (You)" if state.turn == Color.RED else "Black (AI)"
        moves = len(st.session_state.history)
        st.markdown(f"**Turn:** {turn} | **Moves:** {moves}")
    with col3:
        if st.session_state.game_over:
            if st.session_state.game_over == "red_win":
                st.success("You Win!")
            elif st.session_state.game_over == "draw":
                st.warning("Draw!")
            else:
                st.error("AI Wins!")
        else:
            # 占位符，保持布局稳定
            st.markdown("&nbsp;", unsafe_allow_html=True)

    # 状态消息 - 固定高度
    msg_container = st.container()
    with msg_container:
        if not st.session_state.game_over and st.session_state.message:
            st.caption(st.session_state.message)
        else:
            st.caption(" ")  # 占位符

    render_board()

    # FEN 信息折叠
    with st.expander("FEN"):
        st.code(st.session_state.fen, language=None)


if __name__ == "__main__":
    main()
