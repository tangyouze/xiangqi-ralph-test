"""
类型定义单元测试
"""

import pytest

from xiangqi.types import Color, Move, PieceType, Position


class TestColor:
    """Color 枚举测试"""

    def test_color_values(self):
        """测试颜色值"""
        assert Color.RED.value == "red"
        assert Color.BLACK.value == "black"

    def test_color_opposite(self):
        """测试获取对方颜色"""
        assert Color.RED.opposite == Color.BLACK
        assert Color.BLACK.opposite == Color.RED


class TestPosition:
    """Position 测试"""

    def test_position_creation(self):
        """测试创建位置"""
        pos = Position(5, 4)
        assert pos.row == 5
        assert pos.col == 4

    def test_position_is_valid(self):
        """测试位置有效性检查"""
        # 有效位置
        assert Position(0, 0).is_valid()
        assert Position(9, 8).is_valid()
        assert Position(5, 4).is_valid()

        # 无效位置
        assert not Position(-1, 0).is_valid()
        assert not Position(0, -1).is_valid()
        assert not Position(10, 0).is_valid()
        assert not Position(0, 9).is_valid()

    def test_position_is_in_palace(self):
        """测试九宫格检查"""
        # 红方九宫格
        assert Position(0, 3).is_in_palace(Color.RED)
        assert Position(0, 4).is_in_palace(Color.RED)
        assert Position(0, 5).is_in_palace(Color.RED)
        assert Position(1, 4).is_in_palace(Color.RED)
        assert Position(2, 4).is_in_palace(Color.RED)
        assert not Position(3, 4).is_in_palace(Color.RED)
        assert not Position(0, 2).is_in_palace(Color.RED)

        # 黑方九宫格
        assert Position(7, 4).is_in_palace(Color.BLACK)
        assert Position(8, 4).is_in_palace(Color.BLACK)
        assert Position(9, 4).is_in_palace(Color.BLACK)
        assert not Position(6, 4).is_in_palace(Color.BLACK)

    def test_position_is_on_own_side(self):
        """测试己方半场检查"""
        # 红方半场
        assert Position(0, 0).is_on_own_side(Color.RED)
        assert Position(4, 8).is_on_own_side(Color.RED)
        assert not Position(5, 0).is_on_own_side(Color.RED)

        # 黑方半场
        assert Position(9, 0).is_on_own_side(Color.BLACK)
        assert Position(5, 8).is_on_own_side(Color.BLACK)
        assert not Position(4, 0).is_on_own_side(Color.BLACK)

    def test_position_add(self):
        """测试位置加法"""
        pos = Position(5, 4)
        new_pos = pos + (1, -1)
        assert new_pos == Position(6, 3)
        assert new_pos.row == 6
        assert new_pos.col == 3


class TestMove:
    """Move 测试"""

    def test_move_creation(self):
        """测试创建走法"""
        from_pos = Position(0, 0)
        to_pos = Position(0, 4)
        move = Move(from_pos, to_pos)
        assert move.from_pos == from_pos
        assert move.to_pos == to_pos

    def test_move_to_notation(self):
        """测试走法转记谱"""
        move = Move(Position(0, 4), Position(1, 4))
        notation = move.to_notation()
        assert notation == "40-41"

    def test_move_from_notation(self):
        """测试从记谱解析走法"""
        move = Move.from_notation("40-41")
        assert move.from_pos == Position(0, 4)
        assert move.to_pos == Position(1, 4)
