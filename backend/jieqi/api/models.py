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
    # 延迟分配模式：翻棋时决定身份
    delay_reveal: bool = False
    # AI 思考时间限制（秒）
    ai_time_limit: int | None = None  # Human vs AI 模式
    red_ai_time_limit: int | None = None  # AI vs AI 模式
    black_ai_time_limit: int | None = None  # AI vs AI 模式


class MoveRequest(BaseModel):
    """走棋请求"""

    action_type: str  # "reveal_and_move" or "move"
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    # 延迟分配模式下，指定翻出的棋子类型
    reveal_type: str | None = None  # "rook", "horse", "cannon", etc.


class MoveResponse(BaseModel):
    """走棋响应"""

    success: bool
    game_state: "GameStateResponse | None" = None
    error: str | None = None
    ai_move: MoveModel | None = None
    # 延迟分配模式：AI 的翻棋走法需要用户选择类型
    pending_ai_reveal: MoveModel | None = None
    pending_ai_reveal_types: list[str] | None = None  # 可选择的类型列表


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
    delay_reveal: bool = False  # 是否为延迟分配模式


class AIInfoResponse(BaseModel):
    """AI 信息响应"""

    available_strategies: list[dict[str, str]]
    levels: list[str]
    strategy_descriptions: dict[str, str]


class MaterialScore(BaseModel):
    """子力分数"""

    red: int
    black: int
    diff: int


class PositionScore(BaseModel):
    """位置分数"""

    red: int
    black: int
    diff: int


class HiddenCount(BaseModel):
    """暗子数量"""

    red: int
    black: int


class PieceCount(BaseModel):
    """棋子数量"""

    red: int
    black: int


class EvaluationResponse(BaseModel):
    """局面评估响应"""

    total: int  # 总分（厘兵单位）
    material: MaterialScore  # 子力分数
    position: PositionScore  # 位置分数
    check: int  # 将军分数
    hidden: HiddenCount  # 暗子数量
    piece_count: PieceCount  # 棋子数量
    win_probability: float  # 胜率估计 (0-1)
    move_count: int  # 当前步数
    current_turn: str  # 当前走棋方


class MoveHistoryItem(BaseModel):
    """走棋历史项"""

    move_number: int
    move: MoveModel
    notation: str
    captured: PieceModel | None = None
    revealed_type: str | None = None


class HistoryResponse(BaseModel):
    """历史记录响应"""

    game_id: str
    moves: list[MoveHistoryItem]
    total_moves: int


class ReplayRequest(BaseModel):
    """复盘请求"""

    move_number: int  # 要跳转到的步数 (0 = 开局)


class ReplayResponse(BaseModel):
    """复盘响应"""

    success: bool
    game_state: GameStateResponse | None = None
    current_move_number: int
    total_moves: int
    error: str | None = None


class AvailableTypesResponse(BaseModel):
    """可用棋子类型响应（延迟分配模式）"""

    position: PositionModel
    available_types: list[str]  # 可选择的棋子类型列表
    unique_types: list[str]  # 去重后的类型列表（用于 UI 显示）


class PendingRevealRequest(BaseModel):
    """待揭子位置请求"""

    from_row: int
    from_col: int


class ExecuteAIMoveRequest(BaseModel):
    """执行 AI 走法请求（延迟分配模式）"""

    # AI 走法信息
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    action_type: str
    # 用户选择的棋子类型
    reveal_type: str | None = None


# 更新前向引用
MoveResponse.model_rebuild()
ReplayResponse.model_rebuild()
