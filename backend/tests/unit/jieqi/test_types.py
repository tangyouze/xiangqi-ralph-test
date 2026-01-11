"""
揭棋类型测试
"""

import pytest
from jieqi.types import (
    ActionType,
    Color,
    GameResult,
    JieqiMove,
    PieceState,
    PieceType,
    Position,
    get_position_piece_type,
    get_piece_positions_by_type,
    INITIAL_POSITIONS,
)


class TestColor:
    """测试 Color 枚举"""

    def test_opposite_red(self):
        """红方的对手是黑方"""
        assert Color.RED.opposite == Color.BLACK

    def test_opposite_black(self):
        """黑方的对手是红方"""
        assert Color.BLACK.opposite == Color.RED


class TestPieceType:
    """测试 PieceType 枚举"""

    def test_all_piece_types(self):
        """确保所有棋子类型都存在"""
        assert len(PieceType) == 7
        assert PieceType.KING.value == "king"
        assert PieceType.ADVISOR.value == "advisor"
        assert PieceType.ELEPHANT.value == "elephant"
        assert PieceType.HORSE.value == "horse"
        assert PieceType.ROOK.value == "rook"
        assert PieceType.CANNON.value == "cannon"
        assert PieceType.PAWN.value == "pawn"


class TestPieceState:
    """测试 PieceState 枚举"""

    def test_states(self):
        """确保暗子和明子状态都存在"""
        assert PieceState.HIDDEN.value == "hidden"
        assert PieceState.REVEALED.value == "revealed"


class TestActionType:
    """测试 ActionType 枚举"""

    def test_action_types(self):
        """确保所有动作类型都存在"""
        assert ActionType.REVEAL_AND_MOVE.value == "reveal_and_move"
        assert ActionType.MOVE.value == "move"


class TestPosition:
    """测试 Position 类"""

    def test_is_valid_center(self):
        """棋盘中心是有效位置"""
        pos = Position(5, 4)
        assert pos.is_valid()

    def test_is_valid_corners(self):
        """棋盘四角是有效位置"""
        assert Position(0, 0).is_valid()
        assert Position(0, 8).is_valid()
        assert Position(9, 0).is_valid()
        assert Position(9, 8).is_valid()

    def test_is_valid_out_of_bounds(self):
        """棋盘外是无效位置"""
        assert not Position(-1, 4).is_valid()
        assert not Position(10, 4).is_valid()
        assert not Position(5, -1).is_valid()
        assert not Position(5, 9).is_valid()

    def test_is_in_palace_red(self):
        """红方九宫格测试"""
        # 红方九宫格: row 0-2, col 3-5
        assert Position(0, 3).is_in_palace(Color.RED)
        assert Position(1, 4).is_in_palace(Color.RED)
        assert Position(2, 5).is_in_palace(Color.RED)
        # 九宫格外
        assert not Position(0, 2).is_in_palace(Color.RED)
        assert not Position(3, 4).is_in_palace(Color.RED)

    def test_is_in_palace_black(self):
        """黑方九宫格测试"""
        # 黑方九宫格: row 7-9, col 3-5
        assert Position(7, 3).is_in_palace(Color.BLACK)
        assert Position(8, 4).is_in_palace(Color.BLACK)
        assert Position(9, 5).is_in_palace(Color.BLACK)
        # 九宫格外
        assert not Position(6, 4).is_in_palace(Color.BLACK)

    def test_is_on_own_side_red(self):
        """红方半场测试"""
        # 红方半场: row 0-4
        assert Position(0, 4).is_on_own_side(Color.RED)
        assert Position(4, 4).is_on_own_side(Color.RED)
        assert not Position(5, 4).is_on_own_side(Color.RED)

    def test_is_on_own_side_black(self):
        """黑方半场测试"""
        # 黑方半场: row 5-9
        assert Position(5, 4).is_on_own_side(Color.BLACK)
        assert Position(9, 4).is_on_own_side(Color.BLACK)
        assert not Position(4, 4).is_on_own_side(Color.BLACK)

    def test_add_offset(self):
        """位置加偏移量测试"""
        pos = Position(5, 4)
        new_pos = pos + (1, -1)
        assert new_pos == Position(6, 3)


class TestJieqiMove:
    """测试 JieqiMove 类"""

    def test_reveal_move_factory(self):
        """测试揭子走法工厂方法"""
        move = JieqiMove.reveal_move(Position(3, 0), Position(4, 0))
        assert move.action_type == ActionType.REVEAL_AND_MOVE
        assert move.from_pos == Position(3, 0)
        assert move.to_pos == Position(4, 0)

    def test_regular_move_factory(self):
        """测试普通走法工厂方法"""
        move = JieqiMove.regular_move(Position(0, 4), Position(1, 4))
        assert move.action_type == ActionType.MOVE
        assert move.from_pos == Position(0, 4)
        assert move.to_pos == Position(1, 4)

    def test_to_notation_reveal(self):
        """测试揭子走法记谱"""
        move = JieqiMove.reveal_move(Position(3, 0), Position(4, 0))
        notation = move.to_notation()
        assert notation == "R:03-04"

    def test_to_notation_move(self):
        """测试普通走法记谱"""
        move = JieqiMove.regular_move(Position(0, 4), Position(1, 4))
        notation = move.to_notation()
        assert notation == "M:40-41"

    def test_from_notation_reveal(self):
        """测试从记谱解析揭子走法"""
        move = JieqiMove.from_notation("R:03-04")
        assert move.action_type == ActionType.REVEAL_AND_MOVE
        assert move.from_pos == Position(3, 0)
        assert move.to_pos == Position(4, 0)

    def test_from_notation_move(self):
        """测试从记谱解析普通走法"""
        move = JieqiMove.from_notation("M:40-41")
        assert move.action_type == ActionType.MOVE
        assert move.from_pos == Position(0, 4)
        assert move.to_pos == Position(1, 4)


class TestGameResult:
    """测试 GameResult 枚举"""

    def test_all_results(self):
        """确保所有游戏结果都存在"""
        assert GameResult.ONGOING.value == "ongoing"
        assert GameResult.RED_WIN.value == "red_win"
        assert GameResult.BLACK_WIN.value == "black_win"
        assert GameResult.DRAW.value == "draw"


class TestInitialPositions:
    """测试初始位置定义"""

    def test_total_positions(self):
        """确保所有初始位置都定义了"""
        # 每方16个棋子，共32个
        assert len(INITIAL_POSITIONS) == 32

    def test_get_position_piece_type(self):
        """测试根据位置获取棋子类型"""
        # 红方帅位
        assert get_position_piece_type(Position(0, 4)) == PieceType.KING
        # 红方车位
        assert get_position_piece_type(Position(0, 0)) == PieceType.ROOK
        # 红方炮位
        assert get_position_piece_type(Position(2, 1)) == PieceType.CANNON
        # 红方兵位
        assert get_position_piece_type(Position(3, 0)) == PieceType.PAWN
        # 黑方将位
        assert get_position_piece_type(Position(9, 4)) == PieceType.KING
        # 非初始位置
        assert get_position_piece_type(Position(5, 4)) is None

    def test_get_piece_positions_by_type_rook_red(self):
        """测试获取红方车的初始位置"""
        positions = get_piece_positions_by_type(PieceType.ROOK, Color.RED)
        assert len(positions) == 2
        assert Position(0, 0) in positions
        assert Position(0, 8) in positions

    def test_get_piece_positions_by_type_pawn_black(self):
        """测试获取黑方卒的初始位置"""
        positions = get_piece_positions_by_type(PieceType.PAWN, Color.BLACK)
        assert len(positions) == 5
        assert Position(6, 0) in positions
        assert Position(6, 4) in positions
