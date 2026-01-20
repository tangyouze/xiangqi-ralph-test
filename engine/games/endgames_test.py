"""残局 FEN 验证测试"""

import pytest

from engine.games.endgames import (
    ALL_ENDGAMES,
    BASIC_ENDGAMES,
    BOTH_SINGLE_ENDGAMES,
    CLASSIC_ENDGAMES,
    KINGS_ONLY_ENDGAMES,
    MATE_DISTANCE_ENDGAMES,
    RANDOM_ENDGAMES,
    RED_SINGLE_ENDGAMES,
    validate_fen,
)


class TestEndgameFENValidation:
    """验证所有残局 FEN 合法性"""

    def test_all_endgames_valid(self):
        """所有残局 FEN 必须合法"""
        errors = []
        for eg in ALL_ENDGAMES:
            valid, msg = validate_fen(eg.fen)
            if not valid:
                errors.append(f"{eg.id} ({eg.name}): {msg}")

        assert not errors, f"Found {len(errors)} invalid FENs:\n" + "\n".join(errors)

    def test_classic_endgames_count(self):
        """经典残局数量检查"""
        assert len(CLASSIC_ENDGAMES) == 28

    def test_mate_distance_endgames_count(self):
        """Mate Distance 测试残局数量检查"""
        assert len(MATE_DISTANCE_ENDGAMES) == 16

    def test_random_endgames_count(self):
        """随机残局数量检查"""
        assert len(RANDOM_ENDGAMES) == 100

    def test_basic_endgames_count(self):
        """基础残局数量检查"""
        # 20 kings only + 6×20 red single + 6×6×20 both single
        assert len(KINGS_ONLY_ENDGAMES) == 20
        assert len(RED_SINGLE_ENDGAMES) == 120  # 6 types × 20
        assert len(BOTH_SINGLE_ENDGAMES) == 720  # 36 combos × 20
        assert len(BASIC_ENDGAMES) == 860

    def test_total_endgames_count(self):
        """总残局数量检查"""
        expected = (
            len(CLASSIC_ENDGAMES)
            + len(MATE_DISTANCE_ENDGAMES)
            + len(RANDOM_ENDGAMES)
            + len(BASIC_ENDGAMES)
        )
        assert len(ALL_ENDGAMES) == expected

    def test_unique_ids(self):
        """ID 唯一性检查"""
        ids = [eg.id for eg in ALL_ENDGAMES]
        assert len(ids) == len(set(ids)), "Found duplicate IDs"

    def test_id_format(self):
        """ID 格式检查 (ENDxxxx 或 BASxxxx)"""
        for eg in ALL_ENDGAMES:
            assert eg.id.startswith("END") or eg.id.startswith("BAS"), f"Invalid ID prefix: {eg.id}"
            assert len(eg.id) == 7, f"Invalid ID length: {eg.id}"
            assert eg.id[3:].isdigit(), f"Invalid ID number: {eg.id}"
