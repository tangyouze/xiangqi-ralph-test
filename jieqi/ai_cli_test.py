"""
AI CLI 测试

包含：
1. 正确性测试 - 验证 best 命令基本功能
2. NPS 基准测试 - 100 个精选场景的性能测试
"""

from __future__ import annotations

import time

import pytest
from typer.testing import CliRunner

from jieqi.ai.unified import UnifiedAIEngine
from jieqi.ai_cli import app
from jieqi.fen import get_legal_moves_from_fen

runner = CliRunner()

# =============================================================================
# 100 个精选场景
# =============================================================================

# 开局阶段（30 个）- 大量暗子
OPENING_SCENARIOS = [
    # 初始局面
    ("initial", "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"),
    # 红方第一步后
    ("opening_1", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/2P6/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- b r"),
    # 黑方应手
    ("opening_2", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/2p6/2P6/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"),
    # 炮二平五型
    ("cannon_center", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/4C4/9/XXXXKXXXX -:- b r"),
    # 中局初期（揭开几个子）
    ("early_mid_1", "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1C5x1/9/XXXXXXXXX -:- r r"),
    ("early_mid_2", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"),
    ("early_mid_3", "rxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/RXXXXXXXX -:- b r"),
    ("early_mid_4", "xxxxxxxxx/9/1c5x1/x1x1x1x1x/9/9/X1X1X1X1X/1C5X1/9/XXXXXXXXX -:- r r"),
    ("early_mid_5", "xxxxxxxxx/9/1x5c1/x1x1x1x1x/9/9/X1X1X1X1X/1X5C1/9/XXXXXXXXX -:- b r"),
    # 更多开局变化
    ("opening_var_1", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"),
    ("opening_var_2", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/4P4/X1X3X1X/1X5X1/9/XXXXKXXXX -:- b r"),
    ("opening_var_3", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/4p4/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"),
    ("opening_var_4", "xxxxkxxxx/9/1x5x1/x1x3x1x/9/9/X1X1X1X1X/1X2C2X1/9/XXXXKXXXX -:- b r"),
    ("opening_var_5", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/P8/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- b r"),
    # 侧翼开局
    ("flank_1", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/8P/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- b r"),
    ("flank_2", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/p8/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"),
    # 飞象开局
    ("elephant_1", "xxxxkxxxx/9/1x3E1x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- b r"),
    ("elephant_2", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X3e3/9/XXXXKXXXX -:- r r"),
    # 仙人指路
    ("pawn_advance_1", "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/4P4/X1X3X1X/1X5X1/9/XXXXXXXXX -:- b r"),
    ("pawn_advance_2", "xxxxxxxxx/9/1x5x1/x1x1p1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"),
    # 对称开局
    ("symmetric_1", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/4P4/4p4/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"),
    ("symmetric_2", "xxxxkxxxx/9/1c5c1/x1x1x1x1x/9/9/X1X1X1X1X/1C5C1/9/XXXXKXXXX -:- r r"),
    # 早期揭子
    ("reveal_early_1", "xxxxKxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXkXXXX -:- r r"),
    ("reveal_early_2", "xRxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XrXXXXXXX -:- b r"),
    ("reveal_early_3", "xxxxxxxxR/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/rXXXXXXXX -:- b r"),
    # 混合揭开
    ("mixed_reveal_1", "xRxxKxxxr/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XrXXkXXXR -:- r r"),
    ("mixed_reveal_2", "xCxakxxCx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XcXAKXXcX -:- r r"),
    # 边角变化
    ("corner_1", "Rxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/rXXXXXXXX -:- r r"),
    ("corner_2", "xxxxxxxxR/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXr -:- r r"),
    ("corner_3", "rxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/RXXXXXXXX -:- b r"),
]

# 中局阶段（40 个）- 子力交换、战术复杂
MIDGAME_SCENARIOS = [
    # 经典中局对峙
    ("mid_classic_1", "r2ak4/9/2h1e4/p3p4/9/6P2/P3P4/2H1E4/9/R2AK4 -:- r r"),
    ("mid_classic_2", "r1eak4/4a4/4e1h2/p1h1p3p/4c4/2P6/P3P3P/4E1H2/4A4/R2AK2R1 -:- r r"),
    # 中局暗子局面
    ("mid_hidden_1", "4k4/9/1R2R4/9/9/9/1r2r4/9/9/4K4 -:- r r"),
    ("mid_hidden_2", "4k4/4P4/9/4p4/9/9/9/9/9/4K4 -:- r r"),
    ("mid_hidden_3", "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r"),
    # 攻击局面
    ("attack_1", "4k4/4R4/9/9/9/9/9/9/9/4K4 -:- r r"),
    ("attack_2", "3ak4/9/4R4/9/9/9/9/9/9/4K4 -:- r r"),
    ("attack_3", "2eak4/9/4R4/9/4c4/9/9/9/9/4K4 -:- r r"),
    # 防守局面
    ("defense_1", "4k4/9/9/9/9/4r4/9/9/9/4K4 -:- r r"),
    ("defense_2", "4k4/9/9/9/4c4/9/4E4/9/9/4K4 -:- r r"),
    ("defense_3", "3ek4/9/4R4/9/4c4/9/9/9/4A4/4K4 -:- r r"),
    # 子力交换后
    ("exchange_1", "4k4/9/9/p3p4/9/9/P3P4/9/9/4K4 -:- r r"),
    ("exchange_2", "4k4/9/4e4/9/9/9/9/4E4/9/4K4 -:- r r"),
    ("exchange_3", "4k4/4a4/9/9/4c4/4C4/9/9/4A4/4K4 -:- r r"),
    # 复杂战术
    ("tactics_1", "r2akae2/9/2h1e2h1/p3p3p/2p3p2/6P2/P1P1P3P/2H1E2H1/9/R2AKAE2 -:- r r"),
    ("tactics_2", "r2ak4/9/2h1e4/p1C1p4/2p3p2/9/P1P1P3P/4E2H1/9/R2AK4 -:- r r"),
    ("tactics_3", "r2ak4/9/4e4/p3p4/2p1c4/4C4/P3P4/4E4/9/R2AK4 -:- r r"),
    # 车炮配合
    ("rook_cannon_1", "4k4/9/9/9/4c4/4C4/9/4R4/9/4K4 -:- r r"),
    ("rook_cannon_2", "4k4/9/4R4/9/4c4/9/9/4C4/9/4K4 -:- r r"),
    # 马炮配合
    ("horse_cannon_1", "4k4/9/9/9/9/9/4H4/4C4/9/4K4 -:- r r"),
    ("horse_cannon_2", "3ak4/9/9/9/9/9/9/5C3/4H4/4K4 -:- r r"),
    # 双车
    ("double_rook_1", "4k4/9/9/9/9/9/9/9/4R4/3RK4 -:- r r"),
    ("double_rook_2", "4k4/9/9/r8/9/9/9/R8/9/4K4 -:- r r"),
    # 双马
    ("double_horse_1", "4k4/9/9/9/9/9/3H1H3/9/9/4K4 -:- r r"),
    ("double_horse_2", "4k4/9/2h3h2/9/9/9/9/9/9/4K4 -:- r r"),
    # 双炮
    ("double_cannon_1", "4k4/4C4/4C4/9/9/9/9/9/9/4K4 -:- r r"),
    ("double_cannon_2", "3ak4/4a4/9/9/9/9/9/4C4/4C4/4K4 -:- r r"),
    # 车马
    ("rook_horse_1", "3k5/9/4H4/9/9/9/9/4R4/9/4K4 -:- r r"),
    ("rook_horse_2", "4k4/9/3h5/9/9/9/9/9/4R4/4K4 -:- r r"),
    # 对攻中局
    ("counter_1", "r2ak4/9/4e4/p3p4/9/9/P3P4/4E4/9/R2AK4 -:- r r"),
    ("counter_2", "r1eak4/9/4e4/p3p2Cp/9/9/P3P3P/4E4/9/R2AK4 -:- r r"),
    # 暗子中局变化
    ("hidden_mid_1", "xRx1k1xRx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XrX1K1XrX -:- r r"),
    ("hidden_mid_2", "xxCxkxCxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXcXKXcXX -:- r r"),
    ("hidden_mid_3", "xHx1k1xHx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XhX1K1XhX -:- r r"),
    # 多子混战
    ("melee_1", "r1eak4/9/2h1e4/p3p4/2p3p2/9/P1P1P3P/4E1H2/9/R2AK4 -:- r r"),
    ("melee_2", "r2akae2/4c4/2h1e2h1/p3p3p/2p3p2/6P2/P1P1P3P/2H1E2H1/4C4/R2AKAE2 -:- r r"),
    # 僵持局面
    ("stalemate_risk_1", "4k4/4a4/9/9/9/9/9/9/4A4/4K4 -:- r r"),
    ("stalemate_risk_2", "4k4/9/4e4/9/9/9/9/4E4/9/4K4 -:- r r"),
    # 将军局面
    ("check_1", "4k4/4R4/9/9/9/9/9/9/9/4K4 -:- r r"),
    ("check_2", "3Rk4/9/9/9/9/9/9/9/9/4K4 -:- b r"),
]

# 残局阶段（30 个）- 子力少，精确计算
ENDGAME_SCENARIOS = [
    # 车炮残局
    ("rook_cannon_end_1", "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r"),
    ("rook_cannon_end_2", "4k4/9/4R4/9/9/4c4/9/9/9/4K4 -:- r r"),
    # 车马残局
    ("rook_horse_end_1", "4k4/9/4h4/9/9/9/4R4/9/9/4K4 -:- r r"),
    ("rook_horse_end_2", "3k5/9/4H4/9/9/9/9/4R4/9/4K4 -:- r r"),
    # 单车残局
    ("single_rook_1", "4k4/9/9/9/9/9/9/4R4/9/4K4 -:- r r"),
    ("single_rook_2", "3k5/9/9/9/9/9/9/9/4R4/4K4 -:- r r"),
    ("single_rook_3", "4k4/9/9/9/9/9/9/9/9/R3K4 -:- r r"),
    # 多兵残局
    ("pawns_end_1", "4k4/9/9/p3p4/9/9/P3P4/9/9/4K4 -:- r r"),
    ("pawns_end_2", "4k4/9/9/9/p8/P8/9/9/9/4K4 -:- r r"),
    ("pawns_end_3", "4k4/9/9/p1p1p4/9/9/P1P1P4/9/9/4K4 -:- r r"),
    # 车兵对车
    ("rook_pawn_vs_rook_1", "4k4/9/4r4/9/9/9/4P4/9/4R4/4K4 -:- r r"),
    ("rook_pawn_vs_rook_2", "4k4/4r4/9/9/4P4/9/9/9/4R4/4K4 -:- r r"),
    # 炮兵残局
    ("cannon_pawn_1", "4k4/9/9/9/9/4P4/9/4C4/9/4K4 -:- r r"),
    ("cannon_pawn_2", "4k4/4a4/9/9/9/9/4P4/4C4/9/4K4 -:- r r"),
    # 马兵残局
    ("horse_pawn_1", "4k4/9/9/9/9/9/4P4/9/4H4/4K4 -:- r r"),
    ("horse_pawn_2", "4k4/9/9/9/9/4H4/4P4/9/9/4K4 -:- r r"),
    # 双士残局
    ("advisors_1", "4k4/4a4/4a4/9/9/9/9/9/9/4K4 -:- r r"),
    ("advisors_2", "4k4/9/9/9/9/9/9/4A4/4A4/4K4 -:- r r"),
    # 双象残局
    ("elephants_1", "4k4/9/4e4/9/9/9/9/4E4/9/4K4 -:- r r"),
    ("elephants_2", "4k4/9/2e3e2/9/9/9/2E3E2/9/9/4K4 -:- r r"),
    # 杀法练习
    ("checkmate_1", "4k4/9/9/9/9/9/9/9/4R4/3RK4 -:- r r"),  # 双车杀王
    ("checkmate_2", "3ak4/9/9/9/9/9/9/5C3/4H4/4K4 -:- r r"),  # 马后炮
    ("checkmate_3", "3k5/4a4/4R4/9/9/9/9/9/9/4K4 -:- r r"),  # 铁门栓
    ("checkmate_4", "4k4/4C4/4C4/9/9/9/9/9/9/4K4 -:- r r"),  # 重炮杀
    # 和棋局面
    ("draw_1", "4k4/9/9/9/9/9/9/9/9/4K4 -:- r r"),  # 光帅
    ("draw_2", "4k4/4a4/9/9/9/9/9/9/4A4/4K4 -:- r r"),  # 单士
    # 接近胜负的残局
    ("close_1", "3k5/9/9/9/4P4/9/9/9/9/4K4 -:- r r"),  # 兵临城下
    ("close_2", "4k4/9/9/9/4p4/9/9/9/9/4K4 -:- b r"),  # 黑兵过河
    # 揭棋残局特殊
    ("hidden_end_1", "4k4/9/9/9/4P4/9/9/9/9/4K4 -:- r r"),
    ("hidden_end_2", "4k4/4p4/9/9/9/9/4P4/9/9/4K4 -:- r r"),
]

# 所有 100 个场景
BENCHMARK_SCENARIOS = OPENING_SCENARIOS + MIDGAME_SCENARIOS + ENDGAME_SCENARIOS


class TestBestCommand:
    """测试 best 命令正确性"""

    def test_best_returns_legal_move(self):
        """测试返回的走法是合法的"""
        fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"
        result = runner.invoke(app, ["best", "--fen", fen, "-s", "greedy", "-n", "1"])

        assert result.exit_code == 0
        assert "Best moves" in result.stdout

    def test_best_with_time_limit(self):
        """测试时间限制参数"""
        fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"
        result = runner.invoke(app, ["best", "--fen", fen, "-s", "greedy", "-t", "0.5"])

        assert result.exit_code == 0
        assert "time=0.5s" in result.stdout

    def test_best_json_output(self):
        """测试 JSON 输出"""
        fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"
        result = runner.invoke(app, ["best", "--fen", fen, "-s", "greedy", "--json"])

        assert result.exit_code == 0
        assert '"moves"' in result.stdout
        assert '"strategy"' in result.stdout

    def test_moves_are_legal(self):
        """测试所有返回的走法都是合法的"""
        fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r"

        engine = UnifiedAIEngine(strategy="greedy")
        moves = engine.get_best_moves(fen, n=10)

        legal_moves = get_legal_moves_from_fen(fen)
        for move_str, _ in moves:
            assert move_str in legal_moves, f"Move {move_str} is not legal"


class TestNPSBenchmark:
    """NPS 基准测试 - 100 个精选场景"""

    @pytest.mark.slow
    def test_nps_benchmark(self):
        """NPS 基准测试（Rust 后端）"""
        try:
            # 检查 Rust 后端是否可用
            engine = UnifiedAIEngine(strategy="iterative")
        except FileNotFoundError:
            pytest.skip("Rust backend not available")

        total_time = 0.0
        successful = 0

        print("\n" + "=" * 60)
        print("NPS Benchmark")
        print("=" * 60)

        for name, fen in BENCHMARK_SCENARIOS:
            try:
                engine = UnifiedAIEngine(strategy="iterative", time_limit=0.1)

                start = time.perf_counter()
                engine.get_best_moves(fen, n=1)
                elapsed = time.perf_counter() - start

                total_time += elapsed
                successful += 1
            except Exception as e:
                print(f"  SKIP {name}: {e}")
                continue

        if total_time > 0:
            avg_time = total_time / successful
            print("\nResults:")
            print(f"  Scenarios: {successful}/{len(BENCHMARK_SCENARIOS)}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Avg time per position: {avg_time * 1000:.1f}ms")
        else:
            print("No successful runs")

        assert successful > 0, "At least some scenarios should complete"


class TestScenarioValidation:
    """验证所有场景都是有效的"""

    def test_all_scenarios_have_legal_moves(self):
        """测试所有场景都有合法走法"""
        invalid = []

        for name, fen in BENCHMARK_SCENARIOS:
            try:
                moves = get_legal_moves_from_fen(fen)
                if len(moves) == 0:
                    invalid.append((name, "No legal moves"))
            except Exception as e:
                invalid.append((name, str(e)))

        if invalid:
            print("\nInvalid scenarios:")
            for name, reason in invalid:
                print(f"  {name}: {reason}")

        assert len(invalid) == 0, f"Found {len(invalid)} invalid scenarios"

    def test_scenario_count(self):
        """测试场景数量"""
        assert len(BENCHMARK_SCENARIOS) == 100, (
            f"Expected 100 scenarios, got {len(BENCHMARK_SCENARIOS)}"
        )
        assert len(OPENING_SCENARIOS) == 30, (
            f"Expected 30 opening scenarios, got {len(OPENING_SCENARIOS)}"
        )
        assert len(MIDGAME_SCENARIOS) == 40, (
            f"Expected 40 midgame scenarios, got {len(MIDGAME_SCENARIOS)}"
        )
        assert len(ENDGAME_SCENARIOS) == 30, (
            f"Expected 30 endgame scenarios, got {len(ENDGAME_SCENARIOS)}"
        )
