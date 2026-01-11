"""
揭棋 API 数据模型

Pydantic 模型用于请求和响应验证
"""

from enum import Enum
from pydantic import BaseModel


class GameMode(str, Enum):
    """游戏模式"""

    HUMAN_VS_HUMAN = "human_vs_human"
    HUMAN_VS_AI = "human_vs_ai"
    AI_VS_AI = "ai_vs_ai"


class AILevel(str, Enum):
    """AI 难度等级"""

    RANDOM = "random"


# AI 策略类型现在从 AIEngine 动态获取，不再使用枚举


class PositionModel(BaseModel):
    """位置模型"""

    row: int
    col: int


class MoveModel(BaseModel):
    """走法模型"""

    action_type: str  # "reveal_and_move" or "move"
    from_pos: PositionModel
    to_pos: PositionModel


class PieceModel(BaseModel):
    """棋子模型"""

    color: str
    position: PositionModel
    state: str  # "hidden" or "revealed"
    type: str | None = None  # 只有明子才有


class CreateGameRequest(BaseModel):
    """创建游戏请求"""

    mode: GameMode = GameMode.HUMAN_VS_AI
    ai_level: AILevel | None = AILevel.RANDOM
    ai_color: str | None = "black"  # AI 执黑
    ai_strategy: str | None = None  # AI 策略名称（从 /ai/info 获取可用列表）
    seed: int | None = None  # 随机种子，用于复现
    # AI vs AI 模式下指定双方 AI 策略
    red_ai_strategy: str | None = None
    black_ai_strategy: str | None = None


class MoveRequest(BaseModel):
    """走棋请求"""

    action_type: str  # "reveal_and_move" or "move"
    from_row: int
    from_col: int
    to_row: int
    to_col: int


class MoveResponse(BaseModel):
    """走棋响应"""

    success: bool
    game_state: "GameStateResponse | None" = None
    error: str | None = None
    ai_move: MoveModel | None = None


class GameStateResponse(BaseModel):
    """游戏状态响应"""

    game_id: str
    pieces: list[PieceModel]
    current_turn: str
    result: str
    move_count: int
    is_in_check: bool
    legal_moves: list[MoveModel]
    hidden_count: dict[str, int]
    mode: str


class AIInfoResponse(BaseModel):
    """AI 信息响应"""

    available_strategies: list[dict[str, str]]
    levels: list[str]
    strategy_descriptions: dict[str, str]


# 更新前向引用
MoveResponse.model_rebuild()
