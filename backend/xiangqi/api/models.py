"""
API 请求/响应模型

Pydantic models for API validation.
"""

from enum import Enum
from pydantic import BaseModel, Field


class GameMode(str, Enum):
    """游戏模式"""

    HUMAN_VS_HUMAN = "human_vs_human"
    HUMAN_VS_AI = "human_vs_ai"
    AI_VS_AI = "ai_vs_ai"


class AILevel(str, Enum):
    """AI 难度等级"""

    RANDOM = "random"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class PositionModel(BaseModel):
    """棋盘位置"""

    row: int = Field(ge=0, le=9)
    col: int = Field(ge=0, le=8)


class MoveRequest(BaseModel):
    """走棋请求"""

    from_pos: PositionModel = Field(alias="from")
    to_pos: PositionModel = Field(alias="to")

    class Config:
        populate_by_name = True


class CreateGameRequest(BaseModel):
    """创建游戏请求"""

    mode: GameMode = GameMode.HUMAN_VS_AI
    ai_level: AILevel = AILevel.EASY
    # AI 执红还是执黑（仅 human_vs_ai 模式）
    ai_color: str = "black"


class PieceModel(BaseModel):
    """棋子信息"""

    type: str
    color: str
    position: PositionModel


class MoveModel(BaseModel):
    """走法信息"""

    from_pos: PositionModel = Field(alias="from")
    to_pos: PositionModel = Field(alias="to")

    class Config:
        populate_by_name = True


class GameStateResponse(BaseModel):
    """游戏状态响应"""

    game_id: str
    mode: str
    pieces: list[PieceModel]
    current_turn: str
    result: str
    is_in_check: bool
    legal_moves: list[MoveModel]
    move_count: int


class MoveResponse(BaseModel):
    """走棋响应"""

    success: bool
    game_state: GameStateResponse | None = None
    error: str | None = None
    ai_move: MoveModel | None = None


class AIInfoResponse(BaseModel):
    """AI 信息响应"""

    available_strategies: list[str]
    levels: list[str]
