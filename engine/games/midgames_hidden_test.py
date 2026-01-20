"""测试带暗子的局面"""

import pytest

from engine.fen import validate_fen
from engine.games.midgames_hidden import (
    ALL_HIDDEN_POSITIONS,
    MIDGAME_HIDDEN_POSITIONS,
    REVEAL_DECISION_POSITIONS,
    SIMPLE_HIDDEN_POSITIONS,
    get_position_by_id,
    get_positions_by_category,
)


class TestHiddenPositionsValid:
    """测试所有暗子局面的 FEN 有效性"""

    @pytest.mark.parametrize("position", SIMPLE_HIDDEN_POSITIONS)
    def test_simple_hidden_fen_valid(self, position):
        """简单暗子局面 FEN 有效"""
        valid, msg = validate_fen(position.fen)
        assert valid, f"{position.id} ({position.name}): {msg}"

    @pytest.mark.parametrize("position", REVEAL_DECISION_POSITIONS)
    def test_reveal_decision_fen_valid(self, position):
        """揭子决策局面 FEN 有效"""
        valid, msg = validate_fen(position.fen)
        assert valid, f"{position.id} ({position.name}): {msg}"

    @pytest.mark.parametrize("position", MIDGAME_HIDDEN_POSITIONS)
    def test_midgame_hidden_fen_valid(self, position):
        """中局暗子局面 FEN 有效"""
        valid, msg = validate_fen(position.fen)
        assert valid, f"{position.id} ({position.name}): {msg}"


class TestHiddenPositionsCount:
    """测试局面数量"""

    def test_total_count(self):
        """总数正确"""
        expected = (
            len(SIMPLE_HIDDEN_POSITIONS)
            + len(REVEAL_DECISION_POSITIONS)
            + len(MIDGAME_HIDDEN_POSITIONS)
        )
        assert len(ALL_HIDDEN_POSITIONS) == expected

    def test_has_simple_positions(self):
        """有简单暗子局面"""
        assert len(SIMPLE_HIDDEN_POSITIONS) >= 3

    def test_has_reveal_decision_positions(self):
        """有揭子决策局面"""
        assert len(REVEAL_DECISION_POSITIONS) >= 1


class TestHelperFunctions:
    """测试辅助函数"""

    def test_get_by_id(self):
        """按 ID 获取"""
        pos = get_position_by_id("SIMP0001")
        assert pos is not None
        assert pos.name == "红方单暗"

    def test_get_by_id_not_found(self):
        """ID 不存在"""
        pos = get_position_by_id("NONEXISTENT")
        assert pos is None

    def test_get_by_category(self):
        """按类别获取"""
        positions = get_positions_by_category("单暗子")
        assert len(positions) >= 2
