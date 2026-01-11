"""
揭棋 FastAPI 应用

主应用和路由定义
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from jieqi.ai import AIEngine
from jieqi.api.game_manager import game_manager
from jieqi.api.models import (
    AIInfoResponse,
    AILevel,
    CreateGameRequest,
    GameMode,
    GameStateResponse,
    MoveModel,
    MoveRequest,
    MoveResponse,
    PieceModel,
    PositionModel,
)
from jieqi.types import ActionType, GameResult, JieqiMove, Position


# AI 策略描述
AI_STRATEGY_DESCRIPTIONS = {
    "random": "Random - picks a random legal move",
}


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="Jieqi API",
        description="揭棋 (Jieqi) - Chinese Chess variant with hidden pieces",
        version="0.1.0",
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 路由
    @app.get("/")
    def root():
        """API 根路径"""
        return {"message": "Jieqi API", "version": "0.1.0"}

    @app.get("/health")
    def health():
        """健康检查"""
        return {"status": "healthy"}

    @app.get("/ai/info", response_model=AIInfoResponse)
    def get_ai_info():
        """获取 AI 信息"""
        return AIInfoResponse(
            available_strategies=AIEngine.list_strategies(),
            levels=[level.value for level in AILevel],
            strategy_descriptions=AI_STRATEGY_DESCRIPTIONS,
        )

    @app.post("/games", response_model=GameStateResponse)
    def create_game(request: CreateGameRequest):
        """创建新游戏"""
        game = game_manager.create_game(
            mode=request.mode,
            ai_level=request.ai_level,
            ai_color=request.ai_color,
            ai_strategy=request.ai_strategy,
            seed=request.seed,
            red_ai_strategy=request.red_ai_strategy,
            black_ai_strategy=request.black_ai_strategy,
        )
        return _game_to_response(game, request.mode)

    @app.get("/games/{game_id}", response_model=GameStateResponse)
    def get_game(game_id: str):
        """获取游戏状态"""
        game = game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        mode = game_manager.get_mode(game_id) or GameMode.HUMAN_VS_HUMAN
        return _game_to_response(game, mode)

    @app.post("/games/{game_id}/move", response_model=MoveResponse)
    def make_move(game_id: str, request: MoveRequest):
        """执行走棋"""
        game = game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        if game.result != GameResult.ONGOING:
            return MoveResponse(
                success=False,
                error="Game has already ended",
            )

        # 构造走法
        action_type = (
            ActionType.REVEAL_AND_MOVE
            if request.action_type == "reveal_and_move"
            else ActionType.MOVE
        )
        move = JieqiMove(
            action_type=action_type,
            from_pos=Position(request.from_row, request.from_col),
            to_pos=Position(request.to_row, request.to_col),
        )

        # 执行走棋
        success = game.make_move(move)
        if not success:
            return MoveResponse(
                success=False,
                error="Invalid move",
            )

        mode = game_manager.get_mode(game_id) or GameMode.HUMAN_VS_HUMAN

        # 如果是人机模式且轮到 AI，自动走棋
        ai_move_response = None
        if mode == GameMode.HUMAN_VS_AI and game.result == GameResult.ONGOING:
            ai_move = game_manager.get_ai_move(game_id)
            if ai_move:
                game.make_move(ai_move)
                ai_move_response = MoveModel(
                    action_type=ai_move.action_type.value,
                    from_pos=PositionModel(
                        row=ai_move.from_pos.row, col=ai_move.from_pos.col
                    ),
                    to_pos=PositionModel(
                        row=ai_move.to_pos.row, col=ai_move.to_pos.col
                    ),
                )

        return MoveResponse(
            success=True,
            game_state=_game_to_response(game, mode),
            ai_move=ai_move_response,
        )

    @app.post("/games/{game_id}/ai-move", response_model=MoveResponse)
    def request_ai_move(game_id: str):
        """请求 AI 走棋（用于 AI vs AI 模式）"""
        game = game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        if game.result != GameResult.ONGOING:
            return MoveResponse(
                success=False,
                error="Game has already ended",
            )

        ai_move = game_manager.get_ai_move(game_id)
        if not ai_move:
            return MoveResponse(
                success=False,
                error="No AI available for current turn",
            )

        success = game.make_move(ai_move)
        if not success:
            return MoveResponse(
                success=False,
                error="AI made an invalid move",
            )

        mode = game_manager.get_mode(game_id) or GameMode.AI_VS_AI

        return MoveResponse(
            success=True,
            game_state=_game_to_response(game, mode),
            ai_move=MoveModel(
                action_type=ai_move.action_type.value,
                from_pos=PositionModel(
                    row=ai_move.from_pos.row, col=ai_move.from_pos.col
                ),
                to_pos=PositionModel(
                    row=ai_move.to_pos.row, col=ai_move.to_pos.col
                ),
            ),
        )

    @app.delete("/games/{game_id}")
    def delete_game(game_id: str):
        """删除游戏"""
        if game_manager.delete_game(game_id):
            return {"message": "Game deleted"}
        raise HTTPException(status_code=404, detail="Game not found")

    @app.get("/games")
    def list_games():
        """列出所有游戏"""
        return {"games": game_manager.list_games()}

    return app


def _game_to_response(game, mode: GameMode) -> GameStateResponse:
    """将游戏状态转换为 API 响应"""
    game_dict = game.to_dict()

    pieces = []
    for p in game_dict["board"]["pieces"]:
        piece = PieceModel(
            color=p["color"],
            position=PositionModel(row=p["position"]["row"], col=p["position"]["col"]),
            state=p["state"],
            type=p.get("type"),
        )
        pieces.append(piece)

    legal_moves = []
    for m in game_dict["legal_moves"]:
        move = MoveModel(
            action_type=m["action_type"],
            from_pos=PositionModel(row=m["from"]["row"], col=m["from"]["col"]),
            to_pos=PositionModel(row=m["to"]["row"], col=m["to"]["col"]),
        )
        legal_moves.append(move)

    return GameStateResponse(
        game_id=game_dict["game_id"],
        pieces=pieces,
        current_turn=game_dict["current_turn"],
        result=game_dict["result"],
        move_count=game_dict["move_count"],
        is_in_check=game_dict["is_in_check"],
        legal_moves=legal_moves,
        hidden_count=game_dict["hidden_count"],
        mode=mode.value,
    )


# 创建应用实例
app = create_app()
