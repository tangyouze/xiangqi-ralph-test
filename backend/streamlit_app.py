"""
揭棋 AI 综合平台

Streamlit 多页面应用，包含：
- Game: 揭棋游戏界面
- AI Analysis: AI 分析仪表板
- AI Tournament: AI 策略对战比较

运行方式：
    cd backend && source .venv/bin/activate
    streamlit run streamlit_app.py --server.port 6710
"""

import streamlit as st


def main():
    st.set_page_config(
        page_title="Jieqi AI Platform",
        page_icon="♟️",
        layout="wide",
    )

    st.title("♟️ Jieqi AI Platform")
    st.markdown("Welcome to the Jieqi (揭棋) AI Platform!")

    st.markdown("---")

    # 功能介绍
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🎮 Game")
        st.markdown(
            """
            Play Jieqi with different modes:
            - Human vs Human
            - Human vs AI
            - AI vs AI

            Features button-based interactive board,
            AI strategy selection, and move history.
            """
        )
        if st.button("Go to Game", key="btn_game"):
            st.switch_page("pages/1_Game.py")

    with col2:
        st.markdown("### 🔍 AI Analysis")
        st.markdown(
            """
            Analyze AI recommendations:
            - Test preset positions
            - Compare Python/Rust backends
            - View top N moves with scores

            Beautiful board visualization with
            move highlighting.
            """
        )
        if st.button("Go to AI Analysis", key="btn_analysis"):
            st.switch_page("pages/2_AI_Analysis.py")

    with col3:
        st.markdown("### 🏆 AI Tournament")
        st.markdown(
            """
            Compare AI strategies:
            - Run AI vs AI battles
            - View win rate heatmaps
            - Elo rating calculations

            Statistical analysis and rankings.
            """
        )
        if st.button("Go to AI Tournament", key="btn_tournament"):
            st.switch_page("pages/3_AI_Tournament.py")

    st.markdown("---")

    # 快速开始指南
    with st.expander("Quick Start Guide"):
        st.markdown(
            """
            ### Getting Started

            1. **Play a Game**: Click on "Game" to start playing Jieqi.
               Choose your game mode and AI opponent settings.

            2. **Analyze Positions**: Use "AI Analysis" to test specific
               board positions and see AI recommendations.

            3. **Compare AIs**: Run tournaments in "AI Tournament" to
               evaluate different AI strategies.

            ### About Jieqi (揭棋)

            Jieqi is a variant of Chinese Chess (Xiangqi) where pieces start
            face-down (hidden). When a piece moves for the first time, it
            reveals its type. This adds an element of uncertainty and
            strategic depth to the game.
            """
        )


if __name__ == "__main__":
    main()
