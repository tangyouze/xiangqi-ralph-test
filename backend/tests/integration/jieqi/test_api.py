"""
揭棋 API 集成测试
"""

import pytest
from fastapi.testclient import TestClient
from jieqi.api.app import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestRootEndpoints:
    """测试根端点"""

    def test_root(self, client: TestClient):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Jieqi API"
        assert "version" in data

    def test_health(self, client: TestClient):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAIInfo:
    """测试 AI 信息端点"""

    def test_get_ai_info(self, client: TestClient):
        """测试获取 AI 信息"""
        response = client.get("/ai/info")
        assert response.status_code == 200
        data = response.json()
        assert "available_strategies" in data
        assert "levels" in data
        assert "strategy_descriptions" in data


class TestGameCreation:
    """测试游戏创建"""

    def test_create_default_game(self, client: TestClient):
        """测试创建默认游戏"""
        response = client.post("/games", json={})
        assert response.status_code == 200
        data = response.json()
        assert "game_id" in data
        assert data["current_turn"] == "red"
        assert data["result"] == "ongoing"
        assert len(data["pieces"]) == 32

    def test_create_game_with_seed(self, client: TestClient):
        """测试使用种子创建游戏"""
        response = client.post("/games", json={"seed": 42})
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] is not None

    def test_create_ai_vs_ai_game(self, client: TestClient):
        """测试创建 AI vs AI 游戏"""
        response = client.post("/games", json={"mode": "ai_vs_ai"})
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "ai_vs_ai"


class TestGameState:
    """测试游戏状态"""

    def test_get_game(self, client: TestClient):
        """测试获取游戏状态"""
        # 先创建游戏
        create_response = client.post("/games", json={"seed": 42})
        game_id = create_response.json()["game_id"]

        # 获取游戏状态
        response = client.get(f"/games/{game_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == game_id

    def test_get_nonexistent_game(self, client: TestClient):
        """测试获取不存在的游戏"""
        response = client.get("/games/nonexistent-id")
        assert response.status_code == 404

    def test_game_has_hidden_pieces(self, client: TestClient):
        """测试游戏有暗子"""
        response = client.post("/games", json={})
        data = response.json()

        hidden_pieces = [p for p in data["pieces"] if p["state"] == "hidden"]
        revealed_pieces = [p for p in data["pieces"] if p["state"] == "revealed"]

        # 30 个暗子（每方15个），2个明子（将/帅）
        assert len(hidden_pieces) == 30
        assert len(revealed_pieces) == 2

    def test_game_has_legal_moves(self, client: TestClient):
        """测试游戏有合法走法"""
        response = client.post("/games", json={})
        data = response.json()

        assert len(data["legal_moves"]) > 0
        # 所有红方暗子都应该有揭子走法
        for move in data["legal_moves"]:
            assert move["action_type"] in ["reveal_and_move", "move"]


class TestMakeMove:
    """测试走棋"""

    def test_make_valid_move(self, client: TestClient):
        """测试有效走棋"""
        # 创建游戏
        create_response = client.post("/games", json={"seed": 42})
        game_id = create_response.json()["game_id"]
        legal_moves = create_response.json()["legal_moves"]

        # 选择第一个合法走法
        move = legal_moves[0]
        move_request = {
            "action_type": move["action_type"],
            "from_row": move["from_pos"]["row"],
            "from_col": move["from_pos"]["col"],
            "to_row": move["to_pos"]["row"],
            "to_col": move["to_pos"]["col"],
        }

        response = client.post(f"/games/{game_id}/move", json=move_request)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["game_state"] is not None

    def test_make_invalid_move(self, client: TestClient):
        """测试无效走棋"""
        # 创建游戏
        create_response = client.post("/games", json={})
        game_id = create_response.json()["game_id"]

        # 尝试无效走法
        move_request = {
            "action_type": "move",  # 帅的位置应该用 move，但目标无效
            "from_row": 0,
            "from_col": 4,
            "to_row": 5,
            "to_col": 4,
        }

        response = client.post(f"/games/{game_id}/move", json=move_request)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] is not None

    def test_reveal_move_reveals_piece(self, client: TestClient):
        """测试揭子走法会揭开暗子"""
        # 创建游戏
        create_response = client.post("/games", json={"seed": 42})
        game_id = create_response.json()["game_id"]
        initial_state = create_response.json()

        # 找一个揭子走法
        reveal_moves = [
            m for m in initial_state["legal_moves"] if m["action_type"] == "reveal_and_move"
        ]
        assert len(reveal_moves) > 0

        move = reveal_moves[0]
        move_request = {
            "action_type": move["action_type"],
            "from_row": move["from_pos"]["row"],
            "from_col": move["from_pos"]["col"],
            "to_row": move["to_pos"]["row"],
            "to_col": move["to_pos"]["col"],
        }

        response = client.post(f"/games/{game_id}/move", json=move_request)
        data = response.json()

        # 检查移动后的棋子是明子
        moved_piece = None
        for p in data["game_state"]["pieces"]:
            if (
                p["position"]["row"] == move["to_pos"]["row"]
                and p["position"]["col"] == move["to_pos"]["col"]
            ):
                moved_piece = p
                break

        assert moved_piece is not None
        assert moved_piece["state"] == "revealed"
        assert moved_piece["type"] is not None


class TestAIMove:
    """测试 AI 走棋"""

    def test_ai_vs_ai_move(self, client: TestClient):
        """测试 AI vs AI 走棋"""
        # 创建 AI vs AI 游戏
        create_response = client.post("/games", json={"mode": "ai_vs_ai"})
        game_id = create_response.json()["game_id"]

        # 请求 AI 走棋
        response = client.post(f"/games/{game_id}/ai-move")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["ai_move"] is not None

    def test_multiple_ai_moves(self, client: TestClient):
        """测试多次 AI 走棋"""
        # 创建 AI vs AI 游戏
        create_response = client.post("/games", json={"mode": "ai_vs_ai"})
        game_id = create_response.json()["game_id"]

        # 连续请求多次 AI 走棋
        for i in range(10):
            response = client.post(f"/games/{game_id}/ai-move")
            data = response.json()
            if not data["success"]:
                # 游戏可能结束了
                break
            assert data["ai_move"] is not None


class TestGameDeletion:
    """测试游戏删除"""

    def test_delete_game(self, client: TestClient):
        """测试删除游戏"""
        # 创建游戏
        create_response = client.post("/games", json={})
        game_id = create_response.json()["game_id"]

        # 删除游戏
        response = client.delete(f"/games/{game_id}")
        assert response.status_code == 200

        # 确认游戏已删除
        get_response = client.get(f"/games/{game_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_game(self, client: TestClient):
        """测试删除不存在的游戏"""
        response = client.delete("/games/nonexistent-id")
        assert response.status_code == 404


class TestListGames:
    """测试游戏列表"""

    def test_list_games(self, client: TestClient):
        """测试列出游戏"""
        # 创建几个游戏
        game_ids = []
        for _ in range(3):
            response = client.post("/games", json={})
            game_ids.append(response.json()["game_id"])

        # 列出游戏
        response = client.get("/games")
        assert response.status_code == 200
        data = response.json()
        assert "games" in data

        # 验证创建的游戏在列表中
        for game_id in game_ids:
            assert game_id in data["games"]

        # 清理
        for game_id in game_ids:
            client.delete(f"/games/{game_id}")
