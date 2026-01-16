"""
揭棋 AI 综合平台

Streamlit 多页面应用，包含：
- Game: 揭棋游戏界面
- AI Analysis: AI 分析仪表板
- AI Tournament: AI 策略对战比较

运行方式：
    just start
    # 或
    uv run streamlit run streamlit_app.py --server.port 6704
"""

import streamlit as st


def main():
    st.set_page_config(
        page_title="Jieqi AI Platform",
        page_icon="♟️",
        layout="wide",
    )

    # 自定义 CSS 样式
    st.markdown(
        """
        <style>
        /* 全局样式 */
        .main {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        /* 标题样式 */
        .title-container {
            background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(255,255,255,0.85));
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            margin-bottom: 30px;
            text-align: center;
        }
        
        .main-title {
            font-size: 42px;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        .subtitle {
            font-size: 18px;
            color: #666;
            margin-top: 5px;
        }
        
        /* 卡片样式 */
        .feature-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            height: 100%;
            border-left: 4px solid #667eea;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        }
        
        .card-icon {
            font-size: 36px;
            margin-bottom: 10px;
        }
        
        .card-title {
            font-size: 22px;
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
        }
        
        .card-content {
            font-size: 14px;
            color: #666;
            line-height: 1.6;
        }
        
        /* 按钮样式 */
        .stButton > button {
            width: 100%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        /* Expander 样式 */
        .streamlit-expanderHeader {
            background: rgba(255,255,255,0.9);
            border-radius: 8px;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 标题区域
    st.markdown(
        """
        <div class="title-container">
            <div class="main-title">♟️ 揭棋 AI 对战平台</div>
            <div class="subtitle">Jieqi (Dark Chess) AI Platform - 智能对战 · 策略分析 · 竞技排名</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # 功能介绍卡片
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="feature-card">
                <div class="card-icon">🎮</div>
                <div class="card-title">对弈游戏</div>
                <div class="card-content">
                    <strong>三种对战模式：</strong><br>
                    · 人人对弈<br>
                    · 人机对弈<br>
                    · AI 对战<br><br>
                    <strong>特色功能：</strong><br>
                    交互式棋盘、AI 策略选择、走棋历史记录
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("进入游戏 →", key="btn_game"):
            st.switch_page("pages/1_Game.py")

    with col2:
        st.markdown(
            """
            <div class="feature-card">
                <div class="card-icon">🔍</div>
                <div class="card-title">AI 分析</div>
                <div class="card-content">
                    <strong>局面分析：</strong><br>
                    · 预设局面测试<br>
                    · Python/Rust 双引擎<br>
                    · Top N 走法推荐<br><br>
                    <strong>可视化：</strong><br>
                    精美棋盘渲染、走法高亮显示
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("开始分析 →", key="btn_analysis"):
            st.switch_page("pages/2_AI_Analysis.py")

    with col3:
        st.markdown(
            """
            <div class="feature-card">
                <div class="card-icon">🏆</div>
                <div class="card-title">AI 竞技场</div>
                <div class="card-content">
                    <strong>策略对比：</strong><br>
                    · AI vs AI 对战<br>
                    · 胜率热力图<br>
                    · Elo 等级分<br><br>
                    <strong>数据统计：</strong><br>
                    算法性能分析、排名系统
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("查看竞技 →", key="btn_tournament"):
            st.switch_page("pages/3_AI_Tournament.py")

    st.markdown("---")

    # 快速开始指南
    with st.expander("📖 快速上手指南"):
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown(
                """
                ### 🎯 开始使用
                
                1. **对弈游戏** - 选择对战模式，开始一局揭棋
                   - 支持人人、人机、AI对战
                   - 实时 AI 策略推荐
                
                2. **AI 分析** - 测试特定局面
                   - 预设残局、杀法练习
                   - 多种 AI 引擎对比
                
                3. **AI 竞技场** - 评估策略强度
                   - 批量对战测试
                   - 数据可视化分析
                """
            )
        
        with col_b:
            st.markdown(
                """
                ### 🎲 关于揭棋
                
                **揭棋**是中国象棋的变体玩法：
                
                - 🎭 **暗棋开局**：棋子初始状态全部暗面朝下
                - 🔍 **揭子显形**：首次移动时揭示棋子类型
                - 🎯 **策略深度**：增加不确定性和心理博弈
                - ⚔️ **规则相同**：遵循象棋基本规则
                
                揭棋结合了运气与策略，每一局都是全新的挑战！
                """
            )


if __name__ == "__main__":
    main()
