"""
AI Tournament 页面

AI 策略比较仪表板：
- 运行 AI vs AI 对战
- 展示胜率热力图
- Elo 评分计算
- 统计分析
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from jieqi.ai.base import AIConfig, AIEngine
from jieqi.fen import parse_move, to_fen
from jieqi.game import JieqiGame
from jieqi.types import Color, GameResult

# 导入 AI 策略
from jieqi.ai import strategies  # noqa: F401


# 数据目录
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
RESULTS_FILE = DATA_DIR / "ai_comparison.json"


def would_cause_draw(game: JieqiGame, move) -> bool:
    """预判走这步是否会导致和棋或增加重复局面

    检测：
    1. 走完后是否立即和棋（重复3次）
    2. 走完后的局面是否已经出现过（避免走入重复）
    """
    game.make_move(move)
    is_draw = game.result == GameResult.DRAW
    # 检查当前局面是否已经出现过（出现2次就危险了）
    is_repeated = game.get_position_count() >= 2
    game.undo_move()
    return is_draw or is_repeated


def run_single_game(
    ai_red: str,
    ai_black: str,
    max_moves: int = 500,
    seed: int | None = None,
    avoid_draw: bool = True,
    red_time: float | None = None,
    black_time: float | None = None,
) -> tuple[GameResult, int]:
    """运行单场对战"""
    game = JieqiGame()

    red_ai = AIEngine.create(ai_red, AIConfig(seed=seed, time_limit=red_time))
    black_ai = AIEngine.create(
        ai_black, AIConfig(seed=seed + 1 if seed else None, time_limit=black_time)
    )

    move_count = 0

    while game.result == GameResult.ONGOING and move_count < max_moves:
        current_ai = red_ai if game.current_turn == Color.RED else black_ai
        view = game.get_view(game.current_turn)
        fen = to_fen(view)

        # 选择走法
        move = None
        if avoid_draw:
            # 使用 Top-N 候选，规避和棋
            candidates = current_ai.select_moves_fen(fen, n=10)
            for move_str, _score in candidates:
                candidate_move, _ = parse_move(move_str)
                if not would_cause_draw(game, candidate_move):
                    move = candidate_move
                    break
            # 如果所有候选都会和棋，选第一个
            if move is None and candidates:
                move, _ = parse_move(candidates[0][0])
        else:
            candidates = current_ai.select_moves_fen(fen, n=1)
            if candidates:
                move, _ = parse_move(candidates[0][0])

        if move is None:
            if game.current_turn == Color.RED:
                return GameResult.BLACK_WIN, move_count
            else:
                return GameResult.RED_WIN, move_count

        success = game.make_move(move)
        if not success:
            break

        move_count += 1

    if game.result == GameResult.ONGOING:
        return GameResult.DRAW, move_count

    return game.result, move_count


def calculate_elo(results: dict, k: float = 32, initial_elo: float = 1500) -> dict[str, float]:
    """计算 Elo 评分"""
    strategies_list = list(results.keys())
    elo = {s: initial_elo for s in strategies_list}

    # 多轮迭代以稳定 Elo
    for _ in range(10):
        for s1 in strategies_list:
            for s2 in strategies_list:
                if s1 == s2:
                    continue

                wins = results[s1][s2]["wins"]
                losses = results[s1][s2]["losses"]
                draws = results[s1][s2]["draws"]
                total = wins + losses + draws

                if total == 0:
                    continue

                # 期望得分
                expected = 1 / (1 + 10 ** ((elo[s2] - elo[s1]) / 400))

                # 实际得分（wins=1, draws=0.5, losses=0）
                actual = (wins + draws * 0.5) / total

                # 更新 Elo
                elo[s1] += k * (actual - expected)

    return elo


def run_comparison(
    strategies_list: list[str],
    num_games: int,
    max_moves: int,
    seed: int,
    progress_bar,
    red_time: float | None = None,
    black_time: float | None = None,
):
    """运行 AI 对战比较"""
    results = {
        s1: {s2: {"wins": 0, "losses": 0, "draws": 0} for s2 in strategies_list}
        for s1 in strategies_list
    }

    total_matchups = len(strategies_list) * (len(strategies_list) - 1)
    current_matchup = 0

    for s1 in strategies_list:
        for s2 in strategies_list:
            if s1 == s2:
                continue

            for game_idx in range(num_games):
                game_seed = seed + current_matchup * num_games + game_idx * 2
                result, _ = run_single_game(
                    s1, s2, max_moves, game_seed, red_time=red_time, black_time=black_time
                )

                if result == GameResult.RED_WIN:
                    results[s1][s2]["wins"] += 1
                    results[s2][s1]["losses"] += 1
                elif result == GameResult.BLACK_WIN:
                    results[s1][s2]["losses"] += 1
                    results[s2][s1]["wins"] += 1
                else:
                    results[s1][s2]["draws"] += 1
                    results[s2][s1]["draws"] += 1

            current_matchup += 1
            progress_bar.progress(current_matchup / total_matchups)

    return results


def display_results(data: dict):
    """显示比较结果"""
    strategies_list = data["strategies"]
    results = data["results"]
    scores = data["scores"]
    elo = data.get("elo", {})

    # 按得分排序
    sorted_strategies = sorted(strategies_list, key=lambda s: scores.get(s, 0), reverse=True)

    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["Heatmap", "Rankings", "Analysis"])

    with tab1:
        st.subheader("Win Rate Heatmap")
        st.caption("Row = Red player, Column = Black player. Values show Red's win rate.")

        # 构建胜率矩阵
        matrix_data = []
        for s1 in sorted_strategies:
            row = []
            for s2 in sorted_strategies:
                if s1 == s2:
                    row.append(None)
                else:
                    total = (
                        results[s1][s2]["wins"]
                        + results[s1][s2]["losses"]
                        + results[s1][s2]["draws"]
                    )
                    win_rate = results[s1][s2]["wins"] / total * 100 if total > 0 else 0
                    row.append(win_rate)
            matrix_data.append(row)

        df = pd.DataFrame(matrix_data, index=sorted_strategies, columns=sorted_strategies)

        # 创建热力图
        fig = go.Figure(
            data=go.Heatmap(
                z=df.values,
                x=sorted_strategies,
                y=sorted_strategies,
                colorscale=[
                    [0, "rgb(255, 100, 100)"],  # 红色 - 低胜率
                    [0.5, "rgb(255, 255, 150)"],  # 黄色 - 50%
                    [1, "rgb(100, 255, 100)"],  # 绿色 - 高胜率
                ],
                zmin=0,
                zmax=100,
                text=[[f"{v:.0f}%" if v is not None else "-" for v in row] for row in df.values],
                texttemplate="%{text}",
                textfont={"size": 12},
                hovertemplate="Red: %{y}<br>Black: %{x}<br>Win Rate: %{z:.1f}%<extra></extra>",
            )
        )

        fig.update_layout(
            xaxis_title="Black Player",
            yaxis_title="Red Player",
            height=600,
        )

        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Rankings")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Win Rate Ranking")

            ranking_data = []
            for i, s in enumerate(sorted_strategies, 1):
                total_wins = sum(results[s][opp]["wins"] for opp in sorted_strategies if opp != s)
                total_losses = sum(
                    results[s][opp]["losses"] for opp in sorted_strategies if opp != s
                )
                total_draws = sum(results[s][opp]["draws"] for opp in sorted_strategies if opp != s)

                ranking_data.append(
                    {
                        "Rank": i,
                        "Strategy": s,
                        "Score": f"{scores[s] * 100:.1f}%",
                        "W/L/D": f"{total_wins}/{total_losses}/{total_draws}",
                    }
                )

            st.dataframe(pd.DataFrame(ranking_data), hide_index=True, use_container_width=True)

        with col2:
            st.markdown("### Elo Ratings")

            if elo:
                elo_sorted = sorted(elo.items(), key=lambda x: x[1], reverse=True)
                elo_data = [
                    {"Rank": i, "Strategy": name, "Elo": f"{rating:.0f}"}
                    for i, (name, rating) in enumerate(elo_sorted, 1)
                ]
                st.dataframe(pd.DataFrame(elo_data), hide_index=True, use_container_width=True)

    with tab3:
        st.subheader("Statistical Analysis")

        col1, col2 = st.columns(2)

        with col1:
            # 得分分布柱状图
            fig = px.bar(
                x=sorted_strategies,
                y=[scores[s] * 100 for s in sorted_strategies],
                labels={"x": "Strategy", "y": "Win Rate (%)"},
                title="Win Rate by Strategy",
                color=[scores[s] * 100 for s in sorted_strategies],
                color_continuous_scale="RdYlGn",
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Elo 分布
            if elo:
                elo_sorted = sorted(elo.items(), key=lambda x: x[1], reverse=True)
                fig = px.bar(
                    x=[s for s, _ in elo_sorted],
                    y=[e for _, e in elo_sorted],
                    labels={"x": "Strategy", "y": "Elo Rating"},
                    title="Elo Ratings",
                    color=[e for _, e in elo_sorted],
                    color_continuous_scale="Blues",
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

        # 详细对战结果
        st.markdown("### Head-to-Head Results")

        h2h_data = []
        for s1 in sorted_strategies:
            for s2 in sorted_strategies:
                if s1 >= s2:  # 避免重复
                    continue
                wins_1 = results[s1][s2]["wins"]
                wins_2 = results[s2][s1]["wins"]
                draws = results[s1][s2]["draws"]

                h2h_data.append(
                    {
                        "Matchup": f"{s1} vs {s2}",
                        f"{s1} Wins": wins_1,
                        f"{s2} Wins": wins_2,
                        "Draws": draws,
                        "Total": wins_1 + wins_2 + draws,
                    }
                )

        if h2h_data:
            st.dataframe(pd.DataFrame(h2h_data), hide_index=True, use_container_width=True)


def main():
    st.set_page_config(
        page_title="AI Tournament",
        page_icon="🏆",
        layout="wide",
    )

    st.title("🏆 AI Tournament")

    # 侧边栏配置
    st.sidebar.header("Settings")

    all_strategies = AIEngine.get_strategy_names()

    # 策略选择
    selected_strategies = st.sidebar.multiselect(
        "Select Strategies",
        all_strategies,
        default=all_strategies[:5] if len(all_strategies) >= 5 else all_strategies,
    )

    num_games = st.sidebar.slider("Games per matchup", 1, 50, 10)
    max_moves = st.sidebar.slider("Max moves per game", 100, 1000, 500)
    seed = st.sidebar.number_input("Random seed", value=42)

    # AI 思考时间设置
    st.sidebar.markdown("---")
    st.sidebar.subheader("AI Thinking Time")
    time_options = [1, 3, 5, 15, 30]
    red_time = st.sidebar.select_slider(
        "Red AI Time (seconds)",
        options=time_options,
        value=3,
    )
    black_time = st.sidebar.select_slider(
        "Black AI Time (seconds)",
        options=time_options,
        value=3,
    )

    # 运行比较
    if st.sidebar.button("Run Comparison", type="primary"):
        if len(selected_strategies) < 2:
            st.error("Please select at least 2 strategies")
            return

        with st.spinner("Running AI battles..."):
            progress_bar = st.progress(0)
            results = run_comparison(
                selected_strategies,
                num_games,
                max_moves,
                seed,
                progress_bar,
                red_time=float(red_time),
                black_time=float(black_time),
            )

            # 计算得分和 Elo
            scores = {}
            for s in selected_strategies:
                total_wins = sum(results[s][opp]["wins"] for opp in selected_strategies if opp != s)
                total_losses = sum(
                    results[s][opp]["losses"] for opp in selected_strategies if opp != s
                )
                total_draws = sum(
                    results[s][opp]["draws"] for opp in selected_strategies if opp != s
                )
                total_games = total_wins + total_losses + total_draws
                scores[s] = (total_wins + total_draws * 0.5) / total_games if total_games > 0 else 0

            elo = calculate_elo(results)

            # 保存结果
            output_data = {
                "strategies": selected_strategies,
                "num_games": num_games,
                "max_moves": max_moves,
                "red_time": red_time,
                "black_time": black_time,
                "results": results,
                "scores": scores,
                "elo": elo,
            }
            RESULTS_FILE.write_text(json.dumps(output_data, indent=2))
            st.success(f"Results saved to {RESULTS_FILE}")

    # 显示结果
    if RESULTS_FILE.exists():
        data = json.loads(RESULTS_FILE.read_text())
        display_results(data)
    else:
        st.info("No comparison data available. Run a comparison first!")


if __name__ == "__main__":
    main()
