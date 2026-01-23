#!/usr/bin/env python3
"""导出测试局面到 JSON 文件

从 engine/games/ 中的各模块导出测试局面，供 Rust 测试使用。
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from engine.games.endgames import (
    ALL_ENDGAMES,
    CLASSIC_ENDGAMES,
    RANDOM_ENDGAMES,
)
from engine.games.midgames_hidden import ALL_HIDDEN_POSITIONS
from engine.games.midgames_revealed import ALL_MIDGAME_POSITIONS


def export_positions(output_path: Path) -> dict:
    """导出测试局面到 JSON"""
    positions = []

    # 1. 经典残局（全部 28 个）
    for eg in CLASSIC_ENDGAMES:
        positions.append({
            "id": eg.id,
            "fen": eg.fen,
            "name": eg.name,
            "category": "endgame_classic",
            "has_hidden": False,
        })

    # 2. 随机残局（抽样 20 个）
    for i, eg in enumerate(RANDOM_ENDGAMES):
        if i >= 20:
            break
        positions.append({
            "id": eg.id,
            "fen": eg.fen,
            "name": eg.name,
            "category": "endgame_random",
            "has_hidden": False,
        })

    # 3. 暗子局面（全部 8 个）
    for pos in ALL_HIDDEN_POSITIONS:
        positions.append({
            "id": pos.id,
            "fen": pos.fen,
            "name": pos.name,
            "category": f"hidden_{pos.category}",
            "has_hidden": True,
        })

    # 4. 明子中局（抽样 20 个）
    for i, pos in enumerate(ALL_MIDGAME_POSITIONS):
        if i >= 20:
            break
        positions.append({
            "id": pos.id,
            "fen": pos.fen,
            "name": f"{pos.advantage.value} (seed={pos.seed})",
            "category": "midgame_revealed",
            "has_hidden": False,
        })

    data = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_count": len(positions),
        "positions": positions,
    }

    # 写入 JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return data


def main():
    project_root = Path(__file__).parent.parent
    output_path = project_root / "data" / "test_positions.json"

    data = export_positions(output_path)

    print(f"Exported {data['total_count']} positions to {output_path}")
    
    # 统计
    categories = {}
    for pos in data["positions"]:
        cat = pos["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\nBy category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
