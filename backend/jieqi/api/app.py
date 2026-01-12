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
    AvailableTypesResponse,
    CreateGameRequest,
    EvaluationResponse,
    ExecuteAIMoveRequest,
    GameMode,
    GameStateResponse,
    HistoryResponse,
    HiddenCount,
    MaterialScore,
    MoveHistoryItem,
    MoveModel,
    MoveRequest,
    MoveResponse,
    PendingRevealRequest,
    PieceCount,
    PieceModel,
    PositionModel,
    PositionScore,
    ReplayRequest,
    ReplayResponse,
)
from jieqi.evaluator import evaluate_game
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
            delay_reveal=request.delay_reveal,
            ai_time_limit=request.ai_time_limit,
            red_ai_time_limit=request.red_ai_time_limit,
            black_ai_time_limit=request.black_ai_time_limit,
        )
        return _game_to_response(game, request.mode, request.delay_reveal)

    @app.get("/games/{game_id}", response_model=GameStateResponse)
    def get_game(game_id: str):
        """获取游戏状态"""
        game = game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        mode = game_manager.get_mode(game_id) or GameMode.HUMAN_VS_HUMAN
        delay_reveal = game_manager.is_delay_reveal(game_id)
        return _game_to_response(game, mode, delay_reveal)

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

        # 执行走棋（传递 reveal_type 用于延迟分配模式）
        success = game.make_move(move, reveal_type=request.reveal_type)
        if not success:
            return MoveResponse(
                success=False,
                error="Invalid move",
            )

        mode = game_manager.get_mode(game_id) or GameMode.HUMAN_VS_HUMAN
        delay_reveal = game_manager.is_delay_reveal(game_id)

        # 如果是人机模式且轮到 AI，自动走棋
        ai_move_response = None
        pending_ai_reveal = None
        pending_ai_reveal_types = None

        if mode == GameMode.HUMAN_VS_AI and game.result == GameResult.ONGOING:
            ai_move = game_manager.get_ai_move(game_id)
            if ai_move:
                # 延迟分配模式下，如果 AI 要翻棋，需要用户选择类型
                if delay_reveal and ai_move.action_type == ActionType.REVEAL_AND_MOVE:
                    # 获取可选类型
                    piece = game.board.get_piece(ai_move.from_pos)
                    if piece:
                        available = game.board.get_available_types_unique(piece.color)
                        pending_ai_reveal = MoveModel(
                            action_type=ai_move.action_type.value,
                            from_pos=PositionModel(
                                row=ai_move.from_pos.row, col=ai_move.from_pos.col
                            ),
                            to_pos=PositionModel(row=ai_move.to_pos.row, col=ai_move.to_pos.col),
                        )
                        pending_ai_reveal_types = [t.value for t in available]
                else:
                    # 非翻棋走法，直接执行
                    game.make_move(ai_move)
                    ai_move_response = MoveModel(
                        action_type=ai_move.action_type.value,
                        from_pos=PositionModel(row=ai_move.from_pos.row, col=ai_move.from_pos.col),
                        to_pos=PositionModel(row=ai_move.to_pos.row, col=ai_move.to_pos.col),
                    )

        return MoveResponse(
            success=True,
            game_state=_game_to_response(game, mode, delay_reveal),
            ai_move=ai_move_response,
            pending_ai_reveal=pending_ai_reveal,
            pending_ai_reveal_types=pending_ai_reveal_types,
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

        # AI 走棋时使用随机分配
        success = game.make_move(ai_move)
        if not success:
            return MoveResponse(
                success=False,
                error="AI made an invalid move",
            )

        mode = game_manager.get_mode(game_id) or GameMode.AI_VS_AI
        delay_reveal = game_manager.is_delay_reveal(game_id)

        return MoveResponse(
            success=True,
            game_state=_game_to_response(game, mode, delay_reveal),
            ai_move=MoveModel(
                action_type=ai_move.action_type.value,
                from_pos=PositionModel(row=ai_move.from_pos.row, col=ai_move.from_pos.col),
                to_pos=PositionModel(row=ai_move.to_pos.row, col=ai_move.to_pos.col),
            ),
        )

    @app.post("/games/{game_id}/execute-ai-move", response_model=MoveResponse)
    def execute_ai_move(game_id: str, request: ExecuteAIMoveRequest):
        """执行 AI 走法（延迟分配模式下，用户选择翻棋类型后调用）"""
        game = game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        if game.result != GameResult.ONGOING:
            return MoveResponse(
                success=False,
                error="Game has already ended",
            )

        # 构造 AI 走法
        action_type = (
            ActionType.REVEAL_AND_MOVE
            if request.action_type == "reveal_and_move"
            else ActionType.MOVE
        )
        ai_move = JieqiMove(
            action_type=action_type,
            from_pos=Position(request.from_row, request.from_col),
            to_pos=Position(request.to_row, request.to_col),
        )

        # 执行走棋（传递用户选择的 reveal_type）
        success = game.make_move(ai_move, reveal_type=request.reveal_type)
        if not success:
            return MoveResponse(
                success=False,
                error="Failed to execute AI move",
            )

        mode = game_manager.get_mode(game_id) or GameMode.HUMAN_VS_AI
        delay_reveal = game_manager.is_delay_reveal(game_id)

        return MoveResponse(
            success=True,
            game_state=_game_to_response(game, mode, delay_reveal),
            ai_move=MoveModel(
                action_type=ai_move.action_type.value,
                from_pos=PositionModel(row=ai_move.from_pos.row, col=ai_move.from_pos.col),
                to_pos=PositionModel(row=ai_move.to_pos.row, col=ai_move.to_pos.col),
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

    @app.get("/games/{game_id}/evaluate", response_model=EvaluationResponse)
    def evaluate_position(game_id: str):
        """评估当前局面"""
        game = game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        result = evaluate_game(game)
        return EvaluationResponse(
            total=result["total"],
            material=MaterialScore(
                red=result["material"]["red"],
                black=result["material"]["black"],
                diff=result["material"]["diff"],
            ),
            position=PositionScore(
                red=result["position"]["red"],
                black=result["position"]["black"],
                diff=result["position"]["diff"],
            ),
            check=result["check"],
            hidden=HiddenCount(
                red=result["hidden"]["red"],
                black=result["hidden"]["black"],
            ),
            piece_count=PieceCount(
                red=result["piece_count"]["red"],
                black=result["piece_count"]["black"],
            ),
            win_probability=result["win_probability"],
            move_count=result["move_count"],
            current_turn=result["current_turn"],
        )

    @app.get("/games/{game_id}/history", response_model=HistoryResponse)
    def get_history(game_id: str):
        """获取走棋历史"""
        game = game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        history = game.get_move_history()
        moves = []
        for i, h in enumerate(history):
            captured = None
            if h["captured"]:
                c = h["captured"]
                captured = PieceModel(
                    color=c["color"],
                    position=PositionModel(row=c["position"]["row"], col=c["position"]["col"]),
                    state=c["state"],
                    type=c.get("type"),
                )
            moves.append(
                MoveHistoryItem(
                    move_number=i + 1,
                    move=MoveModel(
                        action_type=h["move"]["action_type"],
                        from_pos=PositionModel(
                            row=h["move"]["from"]["row"], col=h["move"]["from"]["col"]
                        ),
                        to_pos=PositionModel(
                            row=h["move"]["to"]["row"], col=h["move"]["to"]["col"]
                        ),
                    ),
                    notation=h["notation"],
                    captured=captured,
                    revealed_type=h["revealed_type"],
                )
            )

        return HistoryResponse(
            game_id=game_id,
            moves=moves,
            total_moves=len(moves),
        )

    @app.post("/games/{game_id}/replay", response_model=ReplayResponse)
    def replay_to_move(game_id: str, request: ReplayRequest):
        """复盘到指定步数"""
        game = game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        current_move = len(game.move_history)
        target_move = request.move_number

        if target_move < 0:
            return ReplayResponse(
                success=False,
                current_move_number=current_move,
                total_moves=current_move,
                error="Move number cannot be negative",
            )

        # 如果目标步数大于当前步数，无法前进（除非实现 redo）
        if target_move > current_move:
            return ReplayResponse(
                success=False,
                current_move_number=current_move,
                total_moves=current_move,
                error=f"Cannot go forward beyond current move ({current_move})",
            )

        # 后退到目标步数
        while len(game.move_history) > target_move:
            if not game.undo_move():
                break

        mode = game_manager.get_mode(game_id) or GameMode.HUMAN_VS_HUMAN
        delay_reveal = game_manager.is_delay_reveal(game_id)
        return ReplayResponse(
            success=True,
            game_state=_game_to_response(game, mode, delay_reveal),
            current_move_number=len(game.move_history),
            total_moves=target_move,  # 原始总步数
        )

    @app.post("/games/{game_id}/available-types", response_model=AvailableTypesResponse)
    def get_available_types(game_id: str, request: PendingRevealRequest):
        """获取翻棋时可选择的棋子类型（延迟分配模式）"""
        game = game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        if not game.config.delay_reveal:
            raise HTTPException(status_code=400, detail="This game is not in delay reveal mode")

        pos = Position(request.from_row, request.from_col)
        piece = game.board.get_piece(pos)
        if not piece:
            raise HTTPException(status_code=400, detail="No piece at this position")

        if not piece.is_hidden:
            raise HTTPException(status_code=400, detail="This piece is already revealed")

        # 获取可用类型
        available = game.board.get_available_types(piece.color)
        unique = game.board.get_available_types_unique(piece.color)

        return AvailableTypesResponse(
            position=PositionModel(row=pos.row, col=pos.col),
            available_types=[t.value for t in available],
            unique_types=[t.value for t in unique],
        )

    return app


def _game_to_response(game, mode: GameMode, delay_reveal: bool = False) -> GameStateResponse:
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
        delay_reveal=delay_reveal,
    )


# 创建应用实例
app = create_app()
