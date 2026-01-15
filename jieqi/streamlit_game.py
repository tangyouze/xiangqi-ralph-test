"""
揭棋游戏 Streamlit 应用

完整的揭棋游戏界面，支持：
- Human vs Human, Human vs AI, AI vs AI 三种模式
- Button 网格交互
- AI 策略选择
- 走子历史和被吃子显示
"""

from __future__ import annotations

import time
from enum import Enum

import streamlit as st

from jieqi.ai.unified import UnifiedAIEngine
from jieqi.fen import parse_move, to_fen
from jieqi.game import GameConfig, JieqiGame
from jieqi.types import ActionType, Color, GameResult, JieqiMove, PieceType, Position

# =============================================================================
# 常量
# =============================================================================


class GameMode(Enum):
    """游戏模式"""

    HUMAN_VS_HUMAN = "Human vs Human"
    HUMAN_VS_AI = "Human vs AI"
    AI_VS_AI = "AI vs AI"


# 棋子显示符号
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


# =============================================================================
# Session State 管理
# =============================================================================


def init_session_state():
    """初始化 session state"""
    if "game" not in st.session_state:
        st.session_state.game = None
    if "selected_pos" not in st.session_state:
        st.session_state.selected_pos = None
    if "legal_targets" not in st.session_state:
        st.session_state.legal_targets = []
    if "game_mode" not in st.session_state:
        st.session_state.game_mode = GameMode.HUMAN_VS_AI
    if "ai_backend" not in st.session_state:
        st.session_state.ai_backend = "python"
    if "ai_strategy" not in st.session_state:
        st.session_state.ai_strategy = "greedy"
    if "ai_depth" not in st.session_state:
        st.session_state.ai_depth = 3
    if "ai_thinking" not in st.session_state:
        st.session_state.ai_thinking = False
    if "pending_reveal" not in st.session_state:
        st.session_state.pending_reveal = None  # 待选择揭棋类型的走法
    if "message" not in st.session_state:
        st.session_state.message = None
    if "auto_play" not in st.session_state:
        st.session_state.auto_play = False
    if "delay_reveal" not in st.session_state:
        st.session_state.delay_reveal = False


def create_new_game():
    """创建新游戏"""
    config = GameConfig(
        delay_reveal=st.session_state.delay_reveal,
    )
    st.session_state.game = JieqiGame(config=config)
    st.session_state.selected_pos = None
    st.session_state.legal_targets = []
    st.session_state.pending_reveal = None
    st.session_state.message = "Game started! Red moves first."
    st.session_state.auto_play = False


def get_piece_at(row: int, col: int) -> dict | None:
    """获取指定位置的棋子信息"""
    game: JieqiGame = st.session_state.game
    if game is None:
        return None

    piece = game.board.get_piece(Position(row, col))
    if piece is None:
        return None

    return {
        "color": piece.color,
        "is_hidden": piece.is_hidden,
        "actual_type": piece.actual_type,
        "position": Position(row, col),
    }


def get_legal_moves_for_piece(pos: Position) -> list[tuple[Position, ActionType]]:
    """获取某个棋子的合法走法目标"""
    game: JieqiGame = st.session_state.game
    if game is None:
        return []

    legal_moves = game.get_legal_moves()
    return [(m.to_pos, m.action_type) for m in legal_moves if m.from_pos == pos]


def handle_cell_click(row: int, col: int):
    """处理格子点击"""
    game: JieqiGame = st.session_state.game
    if game is None or game.result != GameResult.ONGOING:
        return

    pos = Position(row, col)
    piece = get_piece_at(row, col)
    selected = st.session_state.selected_pos

    # 如果正在等待揭棋类型选择，忽略点击
    if st.session_state.pending_reveal is not None:
        return

    # Human vs AI 模式下，只能走自己的颜色
    mode = st.session_state.game_mode
    if mode == GameMode.HUMAN_VS_AI:
        # 人类只能走红方
        if game.current_turn == Color.BLACK:
            return

    # 检查是否点击了合法目标
    if selected is not None:
        for target, action_type in st.session_state.legal_targets:
            if target == pos:
                # 执行走法
                execute_move(selected, pos, action_type)
                return

    # 选择自己的棋子
    if piece is not None and piece["color"] == game.current_turn:
        st.session_state.selected_pos = pos
        st.session_state.legal_targets = get_legal_moves_for_piece(pos)
    else:
        # 取消选择
        st.session_state.selected_pos = None
        st.session_state.legal_targets = []


def execute_move(from_pos: Position, to_pos: Position, action_type: ActionType):
    """执行走法"""
    game: JieqiGame = st.session_state.game
    if game is None:
        return

    move = JieqiMove(action_type, from_pos, to_pos)

    # 延迟分配模式下的揭棋需要选择类型
    if action_type == ActionType.REVEAL_AND_MOVE and st.session_state.delay_reveal:
        # 获取可选类型
        available = get_available_reveal_types(from_pos)
        if len(available) > 1:
            st.session_state.pending_reveal = {
                "move": move,
                "available_types": available,
            }
            return

    # 直接执行
    success = game.make_move(move)
    if success:
        st.session_state.selected_pos = None
        st.session_state.legal_targets = []
        update_game_message()

        # 检查是否需要 AI 走棋
        check_ai_turn()
    else:
        st.session_state.message = "Invalid move!"


def execute_move_with_reveal_type(reveal_type: str):
    """执行带揭棋类型的走法"""
    game: JieqiGame = st.session_state.game
    pending = st.session_state.pending_reveal

    if game is None or pending is None:
        return

    move = pending["move"]
    success = game.make_move(move, reveal_type=reveal_type)

    st.session_state.pending_reveal = None
    st.session_state.selected_pos = None
    st.session_state.legal_targets = []

    if success:
        update_game_message()
        check_ai_turn()
    else:
        st.session_state.message = "Move failed!"


def get_available_reveal_types(pos: Position) -> list[str]:
    """获取揭棋可选类型"""
    game: JieqiGame = st.session_state.game
    if game is None:
        return []

    # 从棋盘获取可分配的类型
    piece = game.board.get_piece(pos)
    if piece is None or not piece.is_hidden:
        return []

    available = game.board.get_available_types(piece.color)
    return [pt.value for pt in available]


def update_game_message():
    """更新游戏消息"""
    game: JieqiGame = st.session_state.game
    if game is None:
        return

    if game.result == GameResult.RED_WIN:
        st.session_state.message = "Game Over! Red wins!"
    elif game.result == GameResult.BLACK_WIN:
        st.session_state.message = "Game Over! Black wins!"
    elif game.result == GameResult.DRAW:
        st.session_state.message = "Game Over! Draw!"
    elif game.is_in_check():
        turn = "Red" if game.current_turn == Color.RED else "Black"
        st.session_state.message = f"{turn}'s turn - CHECK!"
    else:
        turn = "Red" if game.current_turn == Color.RED else "Black"
        st.session_state.message = f"{turn}'s turn"


def check_ai_turn():
    """检查是否需要 AI 走棋"""
    game: JieqiGame = st.session_state.game
    mode = st.session_state.game_mode

    if game is None or game.result != GameResult.ONGOING:
        return

    need_ai = False
    if mode == GameMode.HUMAN_VS_AI and game.current_turn == Color.BLACK:
        need_ai = True
    elif mode == GameMode.AI_VS_AI:
        need_ai = True

    if need_ai:
        st.session_state.ai_thinking = True


def make_ai_move():
    """AI 走棋"""
    game: JieqiGame = st.session_state.game
    if game is None or game.result != GameResult.ONGOING:
        st.session_state.ai_thinking = False
        return

    try:
        # 获取当前局面 FEN（从当前玩家视角）
        view = game.get_view(game.current_turn)
        fen = to_fen(view)

        # 创建 AI 引擎
        engine = UnifiedAIEngine(
            backend=st.session_state.ai_backend,  # type: ignore
            strategy=st.session_state.ai_strategy,
            depth=st.session_state.ai_depth,
        )

        # 获取最佳走法
        moves = engine.get_best_moves(fen, n=1)
        if not moves:
            st.session_state.message = "AI has no legal moves!"
            st.session_state.ai_thinking = False
            return

        move_str, score = moves[0]

        # 解析走法
        move, revealed_type = parse_move(move_str)

        # 执行走法（revealed_type 转换为字符串）
        reveal_type_str = revealed_type.value if revealed_type else None
        success = game.make_move(move, reveal_type=reveal_type_str)
        if success:
            update_game_message()
        else:
            st.session_state.message = f"AI move failed: {move_str}"

    except Exception as e:
        st.session_state.message = f"AI error: {e}"

    st.session_state.ai_thinking = False


# =============================================================================
# UI 渲染
# =============================================================================


def render_board():
    """渲染棋盘（Button 网格）"""
    game: JieqiGame = st.session_state.game
    if game is None:
        st.info("Click 'New Game' to start!")
        return

    selected = st.session_state.selected_pos
    legal_targets = {t[0] for t in st.session_state.legal_targets}

    # 棋盘样式
    st.markdown(
        """
        <style>
        .stButton > button {
            width: 52px !important;
            height: 52px !important;
            padding: 0 !important;
            font-size: 24px !important;
            border-radius: 50% !important;
            margin: 1px !important;
        }
        .stButton > button:disabled {
            opacity: 1 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 列标签
    col_labels = st.columns([1] + [1] * 9)
    col_labels[0].write("")  # 空白
    for i, c in enumerate("abcdefghi"):
        col_labels[i + 1].markdown(f"<center>{c}</center>", unsafe_allow_html=True)

    # 棋盘（从 row 9 到 row 0）
    for row in range(9, -1, -1):
        cols = st.columns([1] + [1] * 9)

        # 行号
        cols[0].markdown(
            f"<div style='text-align:center;padding-top:12px;'>{row}</div>",
            unsafe_allow_html=True,
        )

        for col in range(9):
            pos = Position(row, col)
            piece = get_piece_at(row, col)

            # 确定按钮样式
            is_selected = selected == pos
            is_target = pos in legal_targets

            # 按钮文本
            if piece is not None:
                if piece["is_hidden"]:
                    # 暗子
                    btn_text = "暗" if piece["color"] == Color.RED else "暗"
                else:
                    # 明子
                    btn_text = PIECE_SYMBOLS.get((piece["color"], piece["actual_type"]), "?")
            else:
                btn_text = "·" if is_target else ""

            # 按钮颜色 key
            key = f"cell_{row}_{col}"

            with cols[col + 1]:
                # 使用不同类型的按钮来表示状态
                if is_selected:
                    btn_type = "primary"
                elif is_target:
                    btn_type = "secondary"
                else:
                    btn_type = "secondary"

                # 判断是否可点击
                can_click = game.result == GameResult.ONGOING
                if st.session_state.game_mode == GameMode.HUMAN_VS_AI:
                    can_click = can_click and game.current_turn == Color.RED

                if st.button(
                    btn_text,
                    key=key,
                    type=btn_type,  # type: ignore
                    disabled=not can_click,
                    use_container_width=True,
                ):
                    handle_cell_click(row, col)
                    st.rerun()


def render_reveal_selector():
    """渲染揭棋类型选择器"""
    pending = st.session_state.pending_reveal
    if pending is None:
        return

    st.warning("Select piece type for reveal:")
    available = pending["available_types"]

    # 类型名称映射
    type_names = {
        "king": "帥/將",
        "rook": "俥/車",
        "horse": "傌/馬",
        "cannon": "炮/砲",
        "elephant": "相/象",
        "advisor": "仕/士",
        "pawn": "兵/卒",
    }

    cols = st.columns(len(available))
    for i, pt in enumerate(available):
        name = type_names.get(pt, pt)
        if cols[i].button(name, key=f"reveal_{pt}"):
            execute_move_with_reveal_type(pt)
            st.rerun()


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("Game Settings")

        # 游戏模式
        mode_options = [m.value for m in GameMode]
        selected_mode = st.selectbox(
            "Game Mode",
            mode_options,
            index=mode_options.index(st.session_state.game_mode.value),
        )
        st.session_state.game_mode = GameMode(selected_mode)

        # 揭棋模式
        st.session_state.delay_reveal = st.checkbox(
            "Delay Reveal Mode",
            value=st.session_state.delay_reveal,
            help="If enabled, piece type is assigned when revealed",
        )

        st.divider()

        # AI 设置
        st.subheader("AI Settings")

        col1, col2 = st.columns(2)
        with col1:
            st.session_state.ai_backend = st.selectbox(
                "Backend",
                ["python", "rust"],
                index=0 if st.session_state.ai_backend == "python" else 1,
            )
        with col2:
            st.session_state.ai_depth = st.slider(
                "Depth",
                1,
                5,
                st.session_state.ai_depth,
            )

        # 获取可用策略
        try:
            engine = UnifiedAIEngine(backend=st.session_state.ai_backend)  # type: ignore
            strategies = engine.list_strategies()
        except Exception:
            strategies = ["greedy"]

        current_idx = (
            strategies.index(st.session_state.ai_strategy)
            if st.session_state.ai_strategy in strategies
            else 0
        )
        st.session_state.ai_strategy = st.selectbox(
            "Strategy",
            strategies,
            index=current_idx,
        )

        st.divider()

        # 新游戏按钮
        if st.button("New Game", type="primary", use_container_width=True):
            create_new_game()
            st.rerun()

        # AI vs AI 自动对战控制
        if st.session_state.game_mode == GameMode.AI_VS_AI:
            st.divider()
            st.subheader("Auto Play")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Start", use_container_width=True):
                    st.session_state.auto_play = True
            with col2:
                if st.button("Stop", use_container_width=True):
                    st.session_state.auto_play = False


def render_game_info():
    """渲染游戏信息"""
    game: JieqiGame = st.session_state.game
    if game is None:
        return

    # 状态消息
    if st.session_state.message:
        if "wins" in st.session_state.message or "Draw" in st.session_state.message:
            st.success(st.session_state.message)
        elif "CHECK" in st.session_state.message:
            st.warning(st.session_state.message)
        else:
            st.info(st.session_state.message)

    # 游戏统计
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Moves", len(game.move_history))
    with col2:
        turn = "Red" if game.current_turn == Color.RED else "Black"
        st.metric("Turn", turn)
    with col3:
        st.metric("Red Hidden", game.get_hidden_count(Color.RED))
    with col4:
        st.metric("Black Hidden", game.get_hidden_count(Color.BLACK))


def render_move_history():
    """渲染走子历史"""
    game: JieqiGame = st.session_state.game
    if game is None or not game.move_history:
        return

    with st.expander("Move History", expanded=False):
        history_text = []
        for i, record in enumerate(game.move_history, 1):
            turn = "Red" if i % 2 == 1 else "Black"
            history_text.append(f"{i}. [{turn}] {record.notation}")

        st.text("\n".join(history_text[-20:]))  # 显示最近 20 步


def render_captured_pieces():
    """渲染被吃棋子"""
    game: JieqiGame = st.session_state.game
    if game is None or not game.captured_pieces:
        return

    with st.expander("Captured Pieces", expanded=False):
        red_captured = []
        black_captured = []

        for cap in game.captured_pieces:
            if cap.actual_type:
                symbol = PIECE_SYMBOLS.get((cap.color, cap.actual_type), "?")
            else:
                symbol = "暗"

            if cap.color == Color.RED:
                red_captured.append(symbol)
            else:
                black_captured.append(symbol)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Red lost:** {' '.join(red_captured) or '-'}")
        with col2:
            st.markdown(f"**Black lost:** {' '.join(black_captured) or '-'}")


# =============================================================================
# Main
# =============================================================================


def main():
    st.set_page_config(
        page_title="Jieqi Game",
        page_icon="♟️",
        layout="wide",
    )

    st.title("♟️ 揭棋 (Jieqi) Game")

    # 初始化
    init_session_state()

    # 侧边栏
    render_sidebar()

    # 主内容
    col_board, col_info = st.columns([2, 1])

    with col_board:
        render_board()
        render_reveal_selector()

    with col_info:
        render_game_info()
        render_move_history()
        render_captured_pieces()

    # AI 思考
    if st.session_state.ai_thinking:
        with st.spinner("AI is thinking..."):
            make_ai_move()
            st.rerun()

    # AI vs AI 自动对战
    if (
        st.session_state.auto_play
        and st.session_state.game_mode == GameMode.AI_VS_AI
        and st.session_state.game is not None
        and st.session_state.game.result == GameResult.ONGOING
    ):
        time.sleep(0.5)  # 延迟以便观察
        st.session_state.ai_thinking = True
        st.rerun()


if __name__ == "__main__":
    main()
