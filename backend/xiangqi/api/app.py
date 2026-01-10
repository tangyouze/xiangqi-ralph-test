"""
FastAPI 应用

主应用和路由定义
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from xiangqi.ai import AIEngine
from xiangqi.api.game_manager import game_manager
from xiangqi.api.models import (
    AIInfoResponse,
    AILevel,
    AIStrategy,
    CreateGameRequest,
    GameMode,
    GameStateResponse,
    MoveModel,
    MoveRequest,
    MoveResponse,
    PieceModel,
    PositionModel,
)
from xiangqi.types import GameResult


# AI 策略描述
AI_STRATEGY_DESCRIPTIONS = {
    "random": "Random - picks a random legal move",
    "greedy": "Greedy - picks the best move for the current turn only",
    "defensive": "Defensive - considers opponent's counter-attacks",
    "aggressive": "Aggressive - prioritizes captures and checks",
    "minimax": "Minimax - deep search with alpha-beta pruning",
}


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="Xiangqi API",
        description="Chinese Chess (Xiangqi) game engine API",
        version="0.2.0",
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
        return {"message": "Xiangqi API", "version": "0.2.0"}

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
            search_depth=request.search_depth,
            red_ai_strategy=request.red_ai_strategy,
            red_search_depth=request.red_search_depth,
            black_ai_strategy=request.black_ai_strategy,
            black_search_depth=request.black_search_depth,
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

        # 检查游戏是否结束
        if game.result != GameResult.ONGOING:
            return MoveResponse(success=False, error="Game has ended")

        # 检查是否是 AI 的回合
        if game_manager.is_ai_turn(game_id):
            return MoveResponse(success=False, error="It's AI's turn")

        # 执行走棋
        success = game_manager.make_move(
            game_id,
            request.from_pos.row,
            request.from_pos.col,
            request.to_pos.row,
            request.to_pos.col,
        )

        if not success:
            return MoveResponse(success=False, error="Invalid move")

        # 如果游戏还在进行且是 AI 回合，让 AI 走棋
        ai_move = None
        if game.result == GameResult.ONGOING and game_manager.is_ai_turn(game_id):
            ai_move_obj = game_manager.get_ai_move(game_id)
            if ai_move_obj:
                game_manager.make_move(
                    game_id,
                    ai_move_obj.from_pos.row,
                    ai_move_obj.from_pos.col,
                    ai_move_obj.to_pos.row,
                    ai_move_obj.to_pos.col,
                )
                ai_move = MoveModel(
                    from_pos=PositionModel(
                        row=ai_move_obj.from_pos.row, col=ai_move_obj.from_pos.col
                    ),
                    to_pos=PositionModel(row=ai_move_obj.to_pos.row, col=ai_move_obj.to_pos.col),
                )

        mode = game_manager.get_mode(game_id) or GameMode.HUMAN_VS_HUMAN
        return MoveResponse(
            success=True,
            game_state=_game_to_response(game, mode),
            ai_move=ai_move,
        )

    @app.post("/games/{game_id}/ai-move", response_model=MoveResponse)
    def request_ai_move(game_id: str):
        """请求 AI 走棋（用于 AI vs AI 模式）"""
        game = game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        if game.result != GameResult.ONGOING:
            return MoveResponse(success=False, error="Game has ended")

        if not game_manager.is_ai_turn(game_id):
            return MoveResponse(success=False, error="Not AI's turn")

        ai_move_obj = game_manager.get_ai_move(game_id)
        if not ai_move_obj:
            return MoveResponse(success=False, error="AI could not find a move")

        success = game_manager.make_move(
            game_id,
            ai_move_obj.from_pos.row,
            ai_move_obj.from_pos.col,
            ai_move_obj.to_pos.row,
            ai_move_obj.to_pos.col,
        )

        ai_move = MoveModel(
            from_pos=PositionModel(row=ai_move_obj.from_pos.row, col=ai_move_obj.from_pos.col),
            to_pos=PositionModel(row=ai_move_obj.to_pos.row, col=ai_move_obj.to_pos.col),
        )

        mode = game_manager.get_mode(game_id) or GameMode.HUMAN_VS_HUMAN
        return MoveResponse(
            success=success,
            game_state=_game_to_response(game, mode),
            ai_move=ai_move,
        )

    @app.delete("/games/{game_id}")
    def delete_game(game_id: str):
        """删除游戏"""
        if not game_manager.delete_game(game_id):
            raise HTTPException(status_code=404, detail="Game not found")
        return {"message": "Game deleted"}

    @app.get("/games")
    def list_games():
        """列出所有游戏"""
        return {"games": game_manager.list_games()}

    return app


def _game_to_response(game, mode: GameMode) -> GameStateResponse:
    """将游戏对象转换为响应模型"""
    pieces = []
    for piece in game.board:
        pieces.append(
            PieceModel(
                type=piece.piece_type.value,
                color=piece.color.value,
                position=PositionModel(row=piece.position.row, col=piece.position.col),
            )
        )

    legal_moves = []
    for move in game.get_legal_moves():
        legal_moves.append(
            MoveModel(
                from_pos=PositionModel(row=move.from_pos.row, col=move.from_pos.col),
                to_pos=PositionModel(row=move.to_pos.row, col=move.to_pos.col),
            )
        )

    return GameStateResponse(
        game_id=game.game_id,
        mode=mode.value,
        pieces=pieces,
        current_turn=game.current_turn.value,
        result=game.result.value,
        is_in_check=game.is_in_check(),
        legal_moves=legal_moves,
        move_count=len(game.move_history),
    )


# 创建默认应用实例
app = create_app()
