"""
AI 对战日志系统

日志格式采用 JSONL（每行一个 JSON 对象），便于流式写入和后续分析。

日志类型：
1. game_start - 游戏开始
2. move - 每步走法详情
3. game_end - 游戏结束和汇总

日志存储：
- 位置: backend/battle_logs/
- 文件名: {timestamp}_{red_ai}_vs_{black_ai}.jsonl
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


# 默认日志目录
DEFAULT_LOG_DIR = Path(__file__).parent.parent.parent / "battle_logs"


@dataclass
class MoveRecord:
    """单步走法记录"""

    move_num: int  # 步数
    player: str  # "red" | "black"
    ai_name: str  # AI 名称
    move: str  # 走法字符串
    action_type: str  # "move" | "reveal_and_move"
    from_pos: tuple[int, int]  # (row, col)
    to_pos: tuple[int, int]  # (row, col)
    score: float  # 评分
    nodes: int  # 搜索节点数
    depth: int  # 搜索深度
    tt_hits: int  # TT 命中数
    tt_total: int  # TT 总查询数
    candidates: list[dict]  # 候选着法 [{move, score}, ...]
    elapsed_ms: float = 0.0  # 思考时间（毫秒）


@dataclass
class GameStartRecord:
    """游戏开始记录"""

    type: str = "game_start"
    timestamp: str = ""
    game_id: str = ""
    red_ai: str = ""
    black_ai: str = ""
    time_limit: float = 0.0
    max_moves: int = 0
    seed: int | None = None
    config: dict = field(default_factory=dict)  # 可扩展配置


@dataclass
class GameEndRecord:
    """游戏结束记录"""

    type: str = "game_end"
    timestamp: str = ""
    game_id: str = ""
    result: str = ""  # "red_win" | "black_win" | "draw" | "ongoing"
    total_moves: int = 0
    red_stats: dict = field(default_factory=dict)
    black_stats: dict = field(default_factory=dict)
    duration_seconds: float = 0.0


class BattleLogger:
    """对战日志记录器"""

    def __init__(
        self,
        red_ai: str,
        black_ai: str,
        log_dir: Path | str | None = None,
        time_limit: float = 1.0,
        max_moves: int = 1000,
        seed: int | None = None,
    ):
        self.red_ai = red_ai
        self.black_ai = black_ai
        self.time_limit = time_limit
        self.max_moves = max_moves
        self.seed = seed

        # 日志目录
        self.log_dir = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 生成游戏 ID 和文件名
        self.timestamp = datetime.now()
        self.game_id = self.timestamp.strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"{self.game_id}_{red_ai}_vs_{black_ai}.jsonl"

        # 统计信息
        self.move_count = 0
        self.red_total_nodes = 0
        self.black_total_nodes = 0
        self.red_max_depth = 0
        self.black_max_depth = 0
        self.start_time = datetime.now()

        # 写入游戏开始记录
        self._write_game_start()

    def _write_record(self, record: dict | Any) -> None:
        """写入一条记录"""
        if hasattr(record, "__dict__"):
            data = asdict(record) if hasattr(record, "__dataclass_fields__") else record.__dict__
        else:
            data = record

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def _write_game_start(self) -> None:
        """写入游戏开始记录"""
        record = GameStartRecord(
            type="game_start",
            timestamp=self.timestamp.isoformat(),
            game_id=self.game_id,
            red_ai=self.red_ai,
            black_ai=self.black_ai,
            time_limit=self.time_limit,
            max_moves=self.max_moves,
            seed=self.seed,
            config={},
        )
        self._write_record(record)

    def log_move(
        self,
        move_num: int,
        player: str,
        ai_name: str,
        move: Any,
        score: float,
        nodes: int,
        depth: int,
        tt_hits: int,
        tt_misses: int,
        candidates: list[tuple[Any, float]],
        elapsed_ms: float = 0.0,
    ) -> None:
        """记录一步走法"""
        self.move_count = move_num

        # 更新统计
        if player == "red":
            self.red_total_nodes += nodes
            self.red_max_depth = max(self.red_max_depth, depth)
        else:
            self.black_total_nodes += nodes
            self.black_max_depth = max(self.black_max_depth, depth)

        # 解析走法
        from_pos = (move.from_pos.row, move.from_pos.col) if hasattr(move, "from_pos") else (0, 0)
        to_pos = (move.to_pos.row, move.to_pos.col) if hasattr(move, "to_pos") else (0, 0)
        action_type = str(move.action_type.value) if hasattr(move, "action_type") else "unknown"

        record = {
            "type": "move",
            "move_num": move_num,
            "player": player,
            "ai_name": ai_name,
            "move": str(move),
            "action_type": action_type,
            "from_pos": from_pos,
            "to_pos": to_pos,
            "score": score,
            "nodes": nodes,
            "depth": depth,
            "tt_hits": tt_hits,
            "tt_total": tt_hits + tt_misses,
            "candidates": [{"move": str(m), "score": s} for m, s in candidates],
            "elapsed_ms": elapsed_ms,
        }
        self._write_record(record)

    def log_game_end(self, result: str) -> None:
        """记录游戏结束"""
        duration = (datetime.now() - self.start_time).total_seconds()

        red_moves = (self.move_count + 1) // 2
        black_moves = self.move_count // 2

        record = GameEndRecord(
            type="game_end",
            timestamp=datetime.now().isoformat(),
            game_id=self.game_id,
            result=result,
            total_moves=self.move_count,
            red_stats={
                "total_nodes": self.red_total_nodes,
                "avg_nodes": self.red_total_nodes / max(red_moves, 1),
                "max_depth": self.red_max_depth,
                "moves": red_moves,
            },
            black_stats={
                "total_nodes": self.black_total_nodes,
                "avg_nodes": self.black_total_nodes / max(black_moves, 1),
                "max_depth": self.black_max_depth,
                "moves": black_moves,
            },
            duration_seconds=duration,
        )
        self._write_record(record)

    @property
    def log_path(self) -> Path:
        """获取日志文件路径"""
        return self.log_file


def create_logger(
    red_ai: str,
    black_ai: str,
    log_dir: Path | str | None = None,
    **kwargs,
) -> BattleLogger:
    """创建对战日志记录器"""
    return BattleLogger(red_ai, black_ai, log_dir, **kwargs)
