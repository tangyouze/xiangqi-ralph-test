"""
揭棋 AI 对战平台

运行方式：
    just streamlit
    # 或
    uv run streamlit run streamlit_app.py --server.port 6704
"""

import streamlit as st

from engine.ui import apply_compact_style


def main():
    st.set_page_config(
        page_title="Jieqi AI",
        page_icon="♟️",
        layout="wide",
    )
    apply_compact_style()

    st.title("♟️ 揭棋 AI 对战平台")
    st.markdown("点击左侧 **Game** 开始游戏")

    st.markdown("---")

    st.markdown(
        """
        ### 关于揭棋

        **揭棋**是中国象棋的变体玩法：

        - 🎭 **暗棋开局**：棋子初始状态全部暗面朝下
        - 🔍 **揭子显形**：首次移动时揭示棋子类型
        - 🎯 **策略深度**：增加不确定性和心理博弈

        ### 使用说明

        1. 点击左侧 **Game** 进入游戏
        2. 选择 AI 策略和思考时间
        3. 点击 **New Game** 开始
        4. 点击棋子选择，再点击目标位置移动
        """
    )


if __name__ == "__main__":
    main()
