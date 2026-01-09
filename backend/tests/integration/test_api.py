"""
API 集成测试
"""

import pytest
from fastapi.testclient import TestClient

from xiangqi.api.app import create_app


@pytest.fixture
def client():
    """创建测试客户端"""
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestHealthEndpoints:
    """健康检查端点测试"""

    def test_root(self, client):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Xiangqi API"
        assert "version" in data

    def test_health(self, client):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAIEndpoints:
    """AI 信息端点测试"""

    def test_get_ai_info(self, client):
        """测试获取 AI 信息"""
        response = client.get("/ai/info")
        assert response.status_code == 200
        data = response.json()
        assert "available_strategies" in data
        assert "random" in data["available_strategies"]
        assert "minimax" in data["available_strategies"]
        assert "levels" in data


class TestGameEndpoints:
    """游戏端点测试"""

    def test_create_game_human_vs_human(self, client):
        """测试创建人对人游戏"""
        response = client.post(
            "/games",
            json={"mode": "human_vs_human"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "game_id" in data
        assert data["mode"] == "human_vs_human"
        assert data["current_turn"] == "red"
        assert data["result"] == "ongoing"
        assert len(data["pieces"]) == 32

    def test_create_game_human_vs_ai(self, client):
        """测试创建人对 AI 游戏"""
        response = client.post(
            "/games",
            json={
                "mode": "human_vs_ai",
                "ai_level": "easy",
                "ai_color": "black",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "human_vs_ai"

    def test_create_game_ai_vs_ai(self, client):
        """测试创建 AI 对 AI 游戏"""
        response = client.post(
            "/games",
            json={
                "mode": "ai_vs_ai",
                "ai_level": "random",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "ai_vs_ai"

    def test_get_game(self, client):
        """测试获取游戏状态"""
        # 先创建游戏
        create_response = client.post(
            "/games",
            json={"mode": "human_vs_human"},
        )
        game_id = create_response.json()["game_id"]

        # 获取游戏
        response = client.get(f"/games/{game_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == game_id

    def test_get_nonexistent_game(self, client):
        """测试获取不存在的游戏"""
        response = client.get("/games/nonexistent-id")
        assert response.status_code == 404

    def test_list_games(self, client):
        """测试列出游戏"""
        # 创建几个游戏
        client.post("/games", json={"mode": "human_vs_human"})
        client.post("/games", json={"mode": "human_vs_human"})

        response = client.get("/games")
        assert response.status_code == 200
        data = response.json()
        assert "games" in data
        assert len(data["games"]) >= 2

    def test_delete_game(self, client):
        """测试删除游戏"""
        # 创建游戏
        create_response = client.post(
            "/games",
            json={"mode": "human_vs_human"},
        )
        game_id = create_response.json()["game_id"]

        # 删除游戏
        response = client.delete(f"/games/{game_id}")
        assert response.status_code == 200

        # 验证已删除
        get_response = client.get(f"/games/{game_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_game(self, client):
        """测试删除不存在的游戏"""
        response = client.delete("/games/nonexistent-id")
        assert response.status_code == 404


class TestMoveEndpoints:
    """走棋端点测试"""

    def test_make_valid_move(self, client):
        """测试执行有效走棋"""
        # 创建游戏
        create_response = client.post(
            "/games",
            json={"mode": "human_vs_human"},
        )
        game_id = create_response.json()["game_id"]

        # 红车前进两步
        response = client.post(
            f"/games/{game_id}/move",
            json={"from": {"row": 0, "col": 0}, "to": {"row": 2, "col": 0}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["game_state"]["current_turn"] == "black"

    def test_make_invalid_move(self, client):
        """测试执行无效走棋"""
        # 创建游戏
        create_response = client.post(
            "/games",
            json={"mode": "human_vs_human"},
        )
        game_id = create_response.json()["game_id"]

        # 帅不能走两步
        response = client.post(
            f"/games/{game_id}/move",
            json={"from": {"row": 0, "col": 4}, "to": {"row": 2, "col": 4}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_move_on_nonexistent_game(self, client):
        """测试在不存在的游戏上走棋"""
        response = client.post(
            "/games/nonexistent-id/move",
            json={"from": {"row": 0, "col": 0}, "to": {"row": 2, "col": 0}},
        )
        assert response.status_code == 404

    def test_human_vs_ai_move_triggers_ai(self, client):
        """测试人 vs AI 模式，人走棋后 AI 自动响应"""
        # 创建人 vs AI 游戏
        create_response = client.post(
            "/games",
            json={
                "mode": "human_vs_ai",
                "ai_level": "random",
                "ai_color": "black",
            },
        )
        game_id = create_response.json()["game_id"]

        # 人（红方）走棋
        response = client.post(
            f"/games/{game_id}/move",
            json={"from": {"row": 0, "col": 0}, "to": {"row": 2, "col": 0}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # AI 应该自动走棋了
        assert data["ai_move"] is not None
        # 现在应该是红方的回合（AI 走完了）
        assert data["game_state"]["current_turn"] == "red"


class TestAIMoveEndpoint:
    """AI 走棋端点测试"""

    def test_request_ai_move_in_ai_vs_ai(self, client):
        """测试在 AI vs AI 模式请求 AI 走棋"""
        # 创建 AI vs AI 游戏
        create_response = client.post(
            "/games",
            json={
                "mode": "ai_vs_ai",
                "ai_level": "random",
            },
        )
        game_id = create_response.json()["game_id"]

        # 请求 AI 走棋
        response = client.post(f"/games/{game_id}/ai-move")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["ai_move"] is not None

    def test_request_ai_move_not_ai_turn(self, client):
        """测试非 AI 回合请求 AI 走棋"""
        # 创建人 vs 人游戏
        create_response = client.post(
            "/games",
            json={"mode": "human_vs_human"},
        )
        game_id = create_response.json()["game_id"]

        # 请求 AI 走棋应该失败
        response = client.post(f"/games/{game_id}/ai-move")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
