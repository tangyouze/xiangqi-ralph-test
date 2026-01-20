"""game_log 模块单元测试"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from engine import game_log
from engine.game_log import (
    GameConfig,
    GameDetail,
    GameResult,
    list_logs,
    load_game,
    load_summary,
    save_log,
    search_logs,
)


@pytest.fixture
def temp_log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """使用临时目录替代真实日志目录"""
    log_dir = tmp_path / "game_logs"
    log_dir.mkdir()
    monkeypatch.setattr(game_log, "LOG_DIR", log_dir)
    return log_dir


@pytest.fixture
def sample_config() -> GameConfig:
    """示例对局配置"""
    return GameConfig(
        red_strategy="muses",
        black_strategy="greedy",
        time_limit=0.5,
        max_moves=80,
    )


@pytest.fixture
def sample_results() -> list[GameResult]:
    """示例对局结果列表"""
    return [
        GameResult(
            id="eg001",
            name="Basic Endgame",
            category="basic",
            result="red_win",
            moves=15,
            time_ms=1234.5,
        ),
        GameResult(
            id="eg002",
            name="Hard Endgame",
            category="hard",
            result="black_win",
            moves=28,
            time_ms=2345.6,
        ),
        GameResult(
            id="eg003",
            name="Draw Endgame",
            category="medium",
            result="draw",
            moves=100,
            time_ms=3456.7,
        ),
    ]


@pytest.fixture
def sample_game_details() -> dict[str, GameDetail]:
    """示例对局详情"""
    return {
        "eg001": GameDetail(
            endgame_id="eg001",
            name="Basic Endgame",
            category="basic",
            start_fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
            result="red_win",
            total_moves=15,
            duration_ms=1234.5,
            final_fen="r2akabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
            history=[{"move": "a0a1", "fen": "..."}],
        ),
        "eg002": GameDetail(
            endgame_id="eg002",
            name="Hard Endgame",
            category="hard",
            start_fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR b",
            result="black_win",
            total_moves=28,
            duration_ms=2345.6,
            final_fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR b",
            history=[{"move": "b0b1", "fen": "..."}],
        ),
        "eg003": GameDetail(
            endgame_id="eg003",
            name="Draw Endgame",
            category="medium",
            start_fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
            result="draw",
            total_moves=100,
            duration_ms=3456.7,
            final_fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
            history=[],
        ),
    }


class TestSaveLog:
    """save_log() 测试"""

    def test_creates_txt_and_zip_files(
        self,
        temp_log_dir: Path,
        sample_config: GameConfig,
        sample_results: list[GameResult],
        sample_game_details: dict[str, GameDetail],
    ):
        """验证同时创建 .txt 和 .zip 文件"""
        run_id = "20260120_120000_muses_vs_greedy"

        txt_path, zip_path = save_log(
            run_id=run_id,
            config=sample_config,
            results=sample_results,
            game_details=sample_game_details,
            duration_seconds=120.5,
        )

        assert txt_path.exists(), "txt 文件应存在"
        assert zip_path.exists(), "zip 文件应存在"
        assert txt_path.suffix == ".txt"
        assert zip_path.suffix == ".zip"

    def test_txt_content_includes_summary(
        self,
        temp_log_dir: Path,
        sample_config: GameConfig,
        sample_results: list[GameResult],
        sample_game_details: dict[str, GameDetail],
    ):
        """验证 txt 文件包含正确的摘要信息"""
        run_id = "20260120_120000_muses_vs_greedy"

        txt_path, _ = save_log(
            run_id=run_id,
            config=sample_config,
            results=sample_results,
            game_details=sample_game_details,
            duration_seconds=120.5,
        )

        content = txt_path.read_text(encoding="utf-8")

        # 验证关键内容
        assert "Jieqi Game Log" in content
        assert run_id in content
        assert "muses vs greedy" in content
        assert "Total:     3" in content
        assert "Red Win:   1" in content
        assert "Black Win: 1" in content
        assert "Draw:      1" in content

    def test_zip_contains_summary_and_game_files(
        self,
        temp_log_dir: Path,
        sample_config: GameConfig,
        sample_results: list[GameResult],
        sample_game_details: dict[str, GameDetail],
    ):
        """验证 zip 文件包含 summary.json 和每局详情"""
        run_id = "20260120_120000_muses_vs_greedy"

        _, zip_path = save_log(
            run_id=run_id,
            config=sample_config,
            results=sample_results,
            game_details=sample_game_details,
            duration_seconds=120.5,
        )

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "summary.json" in names
            assert "eg001.json" in names
            assert "eg002.json" in names
            assert "eg003.json" in names

    def test_zip_summary_json_structure(
        self,
        temp_log_dir: Path,
        sample_config: GameConfig,
        sample_results: list[GameResult],
        sample_game_details: dict[str, GameDetail],
    ):
        """验证 summary.json 的结构正确"""
        run_id = "20260120_120000_muses_vs_greedy"

        _, zip_path = save_log(
            run_id=run_id,
            config=sample_config,
            results=sample_results,
            game_details=sample_game_details,
            duration_seconds=120.5,
        )

        with zipfile.ZipFile(zip_path, "r") as zf:
            with zf.open("summary.json") as f:
                summary = json.load(f)

        assert summary["run_id"] == run_id
        assert summary["config"]["red_strategy"] == "muses"
        assert summary["config"]["black_strategy"] == "greedy"
        assert summary["total_games"] == 3
        assert summary["results"]["red_win"] == 1
        assert summary["results"]["black_win"] == 1
        assert summary["results"]["draw"] == 1
        assert summary["duration_seconds"] == 120.5

    def test_empty_results(
        self,
        temp_log_dir: Path,
        sample_config: GameConfig,
    ):
        """验证空结果列表也能正常保存"""
        run_id = "20260120_120000_muses_vs_greedy"

        txt_path, zip_path = save_log(
            run_id=run_id,
            config=sample_config,
            results=[],
            game_details={},
            duration_seconds=0,
        )

        assert txt_path.exists()
        assert zip_path.exists()

        content = txt_path.read_text(encoding="utf-8")
        assert "Total:     0" in content


class TestListLogs:
    """list_logs() 测试"""

    def test_empty_directory(self, temp_log_dir: Path):
        """空目录返回空列表"""
        logs = list_logs()
        assert logs == []

    def test_lists_zip_files_only(self, temp_log_dir: Path):
        """只列出 .zip 文件"""
        # 创建多种文件
        (temp_log_dir / "20260120_120000_it2_vs_muses.zip").touch()
        (temp_log_dir / "20260120_120000_it2_vs_muses.txt").touch()
        (temp_log_dir / "random_file.json").touch()

        logs = list_logs()

        assert len(logs) == 1
        assert logs[0]["run_id"] == "20260120_120000_it2_vs_muses"

    def test_parses_date_correctly(self, temp_log_dir: Path):
        """正确解析日期"""
        (temp_log_dir / "20260115_143000_greedy_vs_random.zip").touch()

        logs = list_logs()

        assert len(logs) == 1
        assert logs[0]["date"] == "2026-01-15"

    def test_parses_strategy_correctly(self, temp_log_dir: Path):
        """正确解析策略"""
        (temp_log_dir / "20260120_120000_muses2_vs_muses3.zip").touch()

        logs = list_logs()

        assert len(logs) == 1
        assert logs[0]["strategy"] == "muses2_vs_muses3"

    def test_sorted_by_run_id_descending(self, temp_log_dir: Path):
        """按 run_id 降序排列"""
        (temp_log_dir / "20260118_100000_a_vs_b.zip").touch()
        (temp_log_dir / "20260120_100000_a_vs_b.zip").touch()
        (temp_log_dir / "20260119_100000_a_vs_b.zip").touch()

        logs = list_logs()

        assert len(logs) == 3
        assert logs[0]["run_id"].startswith("20260120")
        assert logs[1]["run_id"].startswith("20260119")
        assert logs[2]["run_id"].startswith("20260118")

    def test_nonexistent_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """不存在的目录返回空列表"""
        nonexistent = tmp_path / "does_not_exist"
        monkeypatch.setattr(game_log, "LOG_DIR", nonexistent)

        logs = list_logs()

        assert logs == []


class TestLoadSummary:
    """load_summary() 测试"""

    def test_reads_summary_from_zip(
        self,
        temp_log_dir: Path,
        sample_config: GameConfig,
        sample_results: list[GameResult],
        sample_game_details: dict[str, GameDetail],
    ):
        """从 zip 正确读取 summary.json"""
        run_id = "20260120_120000_test_vs_test"

        _, zip_path = save_log(
            run_id=run_id,
            config=sample_config,
            results=sample_results,
            game_details=sample_game_details,
            duration_seconds=60,
        )

        summary = load_summary(zip_path)

        assert summary["run_id"] == run_id
        assert summary["total_games"] == 3
        assert len(summary["games"]) == 3

    def test_invalid_zip_raises_error(self, temp_log_dir: Path):
        """无效 zip 文件抛出异常"""
        invalid_zip = temp_log_dir / "invalid.zip"
        invalid_zip.write_text("not a zip file")

        with pytest.raises(zipfile.BadZipFile):
            load_summary(invalid_zip)


class TestLoadGame:
    """load_game() 测试"""

    def test_reads_game_detail(
        self,
        temp_log_dir: Path,
        sample_config: GameConfig,
        sample_results: list[GameResult],
        sample_game_details: dict[str, GameDetail],
    ):
        """正确读取单局详情"""
        run_id = "20260120_120000_test_vs_test"

        _, zip_path = save_log(
            run_id=run_id,
            config=sample_config,
            results=sample_results,
            game_details=sample_game_details,
            duration_seconds=60,
        )

        game = load_game(zip_path, "eg001")

        assert game["endgame_id"] == "eg001"
        assert game["name"] == "Basic Endgame"
        assert game["result"] == "red_win"
        assert game["total_moves"] == 15

    def test_nonexistent_game_raises_error(
        self,
        temp_log_dir: Path,
        sample_config: GameConfig,
        sample_results: list[GameResult],
        sample_game_details: dict[str, GameDetail],
    ):
        """不存在的游戏 ID 抛出异常"""
        run_id = "20260120_120000_test_vs_test"

        _, zip_path = save_log(
            run_id=run_id,
            config=sample_config,
            results=sample_results,
            game_details=sample_game_details,
            duration_seconds=60,
        )

        with pytest.raises(KeyError):
            load_game(zip_path, "nonexistent")


class TestSearchLogs:
    """search_logs() 测试"""

    def test_filter_by_strategy(self, temp_log_dir: Path):
        """按策略过滤"""
        (temp_log_dir / "20260120_100000_muses_vs_greedy.zip").touch()
        (temp_log_dir / "20260120_110000_it2_vs_mcts.zip").touch()
        (temp_log_dir / "20260120_120000_muses2_vs_muses.zip").touch()

        logs = search_logs(strategy="muses")

        assert len(logs) == 2
        strategies = [lg["strategy"] for lg in logs]
        assert "muses_vs_greedy" in strategies
        assert "muses2_vs_muses" in strategies

    def test_filter_by_strategy_case_insensitive(self, temp_log_dir: Path):
        """策略过滤不区分大小写"""
        (temp_log_dir / "20260120_100000_MUSES_vs_greedy.zip").touch()

        logs = search_logs(strategy="muses")

        assert len(logs) == 1

    def test_filter_by_date_from(self, temp_log_dir: Path):
        """按起始日期过滤"""
        (temp_log_dir / "20260115_100000_a_vs_b.zip").touch()
        (temp_log_dir / "20260118_100000_a_vs_b.zip").touch()
        (temp_log_dir / "20260120_100000_a_vs_b.zip").touch()

        logs = search_logs(date_from="2026-01-18")

        assert len(logs) == 2
        dates = [lg["date"] for lg in logs]
        assert "2026-01-18" in dates
        assert "2026-01-20" in dates

    def test_filter_by_date_to(self, temp_log_dir: Path):
        """按结束日期过滤"""
        (temp_log_dir / "20260115_100000_a_vs_b.zip").touch()
        (temp_log_dir / "20260118_100000_a_vs_b.zip").touch()
        (temp_log_dir / "20260120_100000_a_vs_b.zip").touch()

        logs = search_logs(date_to="2026-01-18")

        assert len(logs) == 2
        dates = [lg["date"] for lg in logs]
        assert "2026-01-15" in dates
        assert "2026-01-18" in dates

    def test_filter_by_date_range(self, temp_log_dir: Path):
        """按日期范围过滤"""
        (temp_log_dir / "20260115_100000_a_vs_b.zip").touch()
        (temp_log_dir / "20260118_100000_a_vs_b.zip").touch()
        (temp_log_dir / "20260120_100000_a_vs_b.zip").touch()
        (temp_log_dir / "20260125_100000_a_vs_b.zip").touch()

        logs = search_logs(date_from="2026-01-17", date_to="2026-01-21")

        assert len(logs) == 2
        dates = [lg["date"] for lg in logs]
        assert "2026-01-18" in dates
        assert "2026-01-20" in dates

    def test_filter_combined(self, temp_log_dir: Path):
        """组合过滤：策略 + 日期"""
        (temp_log_dir / "20260115_100000_muses_vs_greedy.zip").touch()
        (temp_log_dir / "20260118_100000_muses_vs_it2.zip").touch()
        (temp_log_dir / "20260120_100000_it2_vs_mcts.zip").touch()

        logs = search_logs(strategy="muses", date_from="2026-01-17")

        assert len(logs) == 1
        assert logs[0]["strategy"] == "muses_vs_it2"

    def test_no_filters_returns_all(self, temp_log_dir: Path):
        """无过滤条件返回全部"""
        (temp_log_dir / "20260115_100000_a_vs_b.zip").touch()
        (temp_log_dir / "20260118_100000_c_vs_d.zip").touch()

        logs = search_logs()

        assert len(logs) == 2

    def test_no_matches_returns_empty(self, temp_log_dir: Path):
        """无匹配返回空列表"""
        (temp_log_dir / "20260120_100000_muses_vs_greedy.zip").touch()

        logs = search_logs(strategy="nonexistent")

        assert logs == []
