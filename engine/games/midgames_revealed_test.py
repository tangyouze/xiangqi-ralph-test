"""测试全明子中局局面"""

import pytest

from engine.fen import validate_fen
from engine.games.midgames_revealed import (
    ALL_MIDGAME_POSITIONS,
    ADVANTAGE_POSITIONS,
    BIG_ADVANTAGE_POSITIONS,
    BIG_DISADVANTAGE_POSITIONS,
    DISADVANTAGE_POSITIONS,
    EQUAL_POSITIONS,
    Advantage,
    generate_position,
    get_position_by_id,
    get_positions_by_advantage,
)


class TestPositionGeneration:
    """测试局面生成"""

    def test_big_advantage_count(self):
        """大优局面数量"""
        assert len(BIG_ADVANTAGE_POSITIONS) == 10

    def test_advantage_count(self):
        """优势局面数量"""
        assert len(ADVANTAGE_POSITIONS) == 10

    def test_equal_count(self):
        """均势局面数量"""
        assert len(EQUAL_POSITIONS) == 10

    def test_disadvantage_count(self):
        """劣势局面数量"""
        assert len(DISADVANTAGE_POSITIONS) == 10

    def test_big_disadvantage_count(self):
        """大劣局面数量"""
        assert len(BIG_DISADVANTAGE_POSITIONS) == 10

    def test_total_count(self):
        """总数量"""
        assert len(ALL_MIDGAME_POSITIONS) == 50


class TestPositionValidity:
    """测试局面有效性"""

    @pytest.mark.parametrize("position", BIG_ADVANTAGE_POSITIONS)
    def test_big_advantage_fen_valid(self, position):
        """大优局面 FEN 有效"""
        valid, msg = validate_fen(position.fen)
        assert valid, f"{position.id}: {msg}"
        assert position.red_rooks == 2
        assert position.black_rooks == 0

    @pytest.mark.parametrize("position", ADVANTAGE_POSITIONS)
    def test_advantage_fen_valid(self, position):
        """优势局面 FEN 有效"""
        valid, msg = validate_fen(position.fen)
        assert valid, f"{position.id}: {msg}"
        assert position.red_rooks == 2
        assert position.black_rooks == 1

    @pytest.mark.parametrize("position", EQUAL_POSITIONS)
    def test_equal_fen_valid(self, position):
        """均势局面 FEN 有效"""
        valid, msg = validate_fen(position.fen)
        assert valid, f"{position.id}: {msg}"
        assert position.red_rooks == 1
        assert position.black_rooks == 1

    @pytest.mark.parametrize("position", DISADVANTAGE_POSITIONS)
    def test_disadvantage_fen_valid(self, position):
        """劣势局面 FEN 有效"""
        valid, msg = validate_fen(position.fen)
        assert valid, f"{position.id}: {msg}"
        assert position.red_rooks == 1
        assert position.black_rooks == 2

    @pytest.mark.parametrize("position", BIG_DISADVANTAGE_POSITIONS)
    def test_big_disadvantage_fen_valid(self, position):
        """大劣局面 FEN 有效"""
        valid, msg = validate_fen(position.fen)
        assert valid, f"{position.id}: {msg}"
        assert position.red_rooks == 0
        assert position.black_rooks == 2


class TestHelperFunctions:
    """测试辅助函数"""

    def test_get_by_id(self):
        """按 ID 获取"""
        pos = get_position_by_id("MIDS0001")
        assert pos is not None
        assert pos.advantage == Advantage.BIG_ADVANTAGE

    def test_get_by_id_not_found(self):
        """ID 不存在"""
        pos = get_position_by_id("NONEXISTENT")
        assert pos is None

    def test_get_by_advantage(self):
        """按优势等级获取"""
        positions = get_positions_by_advantage(Advantage.EQUAL)
        assert len(positions) == 10
        for p in positions:
            assert p.advantage == Advantage.EQUAL

    def test_generate_position_deterministic(self):
        """相同 seed 生成相同局面"""
        fen1 = generate_position(Advantage.EQUAL, 200)
        fen2 = generate_position(Advantage.EQUAL, 200)
        assert fen1 == fen2
