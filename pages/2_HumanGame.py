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
from engine.rust_ai import UnifiedAIEngine, DEFAULT_STRATEGY
from engine.types import Color

# =============================================================================
# 常量
# =============================================================================

AVAILABLE_STRATEGIES = ["it2", "muses3", "muses2", "muses", "iterative", "greedy", "random"]

# 棋子符号（中文）
PIECE_CN = {
    "R": "車", "H": "馬", "E": "象", "A": "士", "K": "帥", "C": "炮", "P": "兵",
    "r": "车", "h": "马", "e": "相", "a": "仕", "k": "将", "c": "砲", "p": "卒",
    "X": "暗", "x": "暗",
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
    st.session_state.fen = STANDARD_FEN if idx < 0 else ALL_ENDGAMES[idx].fen
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
    base = f"{COL_CHARS[fc]}{9-fr}{COL_CHARS[tc]}{9-tr}"
    # 暗子走法需要 + 前缀
    if piece in ("X", "x"):
        return "+" + base
    return base


def check_over(fen: str) -> str | None:
    board = fen.split()[0]
    if "K" not in board:
        return "black_win"
    if "k" not in board:
        return "red_win"
    if not get_legal_moves_from_fen(fen):
        return "black_win" if parse_fen(fen).turn == Color.RED else "red_win"
    return None


def ai_move():
    if not st.session_state.ai_pending:
        return
    st.session_state.ai_pending = False

    fen = st.session_state.fen
    ai = UnifiedAIEngine(strategy=st.session_state.strategy, time_limit=st.session_state.time_limit)
    moves = ai.get_best_moves(fen, n=1)
    if moves:
        move, score = moves[0]
        new_fen, _ = apply_move_with_capture(fen, move)
        st.session_state.fen = new_fen
        st.session_state.history.append((new_fen, move, "black"))
        st.session_state.message = f"AI: {move} ({score:+.0f})"
        over = check_over(new_fen)
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
            over = check_over(new_fen)
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
    """渲染棋盘按钮网格"""
    fen = st.session_state.fen
    sel = st.session_state.selected
    targets = get_targets(fen, sel[0], sel[1]) if sel else []

    # 自定义 CSS
    st.markdown("""
    <style>
    .board-btn {
        width: 40px !important;
        height: 40px !important;
        padding: 0 !important;
        margin: 1px !important;
        font-size: 18px !important;
        border-radius: 50% !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 列标签
    cols = st.columns([0.5] + [1] * 9 + [0.5])
    cols[0].write("")
    for i, c in enumerate("abcdefghi"):
        cols[i + 1].markdown(f"<center>{c}</center>", unsafe_allow_html=True)

    # 棋盘行
    for row in range(10):
        cols = st.columns([0.5] + [1] * 9 + [0.5])
        cols[0].markdown(f"<center>{9-row}</center>", unsafe_allow_html=True)

        for col in range(9):
            piece = get_piece(fen, col, row)
            is_selected = sel == (col, row)
            is_target = (col, row) in targets

            # 按钮样式
            if piece:
                is_red = piece.isupper()
                label = PIECE_CN.get(piece, piece)
                btn_type = "primary" if is_red else "secondary"
            else:
                label = "·" if is_target else " "
                btn_type = "secondary"

            # 高亮选中
            if is_selected:
                label = f"[{label}]"

            with cols[col + 1]:
                if st.button(label, key=f"btn_{row}_{col}", type=btn_type, use_container_width=True):
                    handle_click(col, row)
                    st.rerun()

        cols[10].markdown(f"<center>{9-row}</center>", unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.subheader("Settings")

        # 位置选择
        options = ["Standard"] + [f"{e.id}" for e in ALL_ENDGAMES[:50]]  # 只显示前50个
        idx = st.selectbox("Position", range(len(options)), format_func=lambda i: options[i])
        if idx - 1 != st.session_state.endgame_idx:
            st.session_state.endgame_idx = idx - 1
            reset_game()
            st.rerun()

        # AI 设置
        st.session_state.strategy = st.selectbox("AI", AVAILABLE_STRATEGIES)
        st.session_state.time_limit = st.slider("Time (s)", 0.1, 3.0, 1.0)

        # 按钮
        if st.button("New Game", type="primary", use_container_width=True):
            reset_game()
            st.rerun()

        if st.button("Undo", use_container_width=True, disabled=len(st.session_state.history) < 2):
            st.session_state.history.pop()
            st.session_state.history.pop()
            if st.session_state.history:
                st.session_state.fen = st.session_state.history[-1][0]
            else:
                reset_game()
            st.session_state.selected = None
            st.rerun()


def main():
    st.set_page_config(page_title="Human vs AI", layout="wide")
    st.title("Human vs AI")
    st.caption("Red = You, Black = AI")

    init_state()
    render_sidebar()
    ai_move()

    # 状态显示
    if st.session_state.game_over:
        if st.session_state.game_over == "red_win":
            st.success("You win!")
        else:
            st.error("AI wins!")
    elif st.session_state.message:
        st.info(st.session_state.message)

    render_board()

    # 信息
    with st.expander("Info"):
        state = parse_fen(st.session_state.fen)
        st.write(f"Turn: {'Red' if state.turn == Color.RED else 'Black'}")
        st.write(f"Moves: {len(st.session_state.history)}")
        st.code(st.session_state.fen)


if __name__ == "__main__":
    main()
