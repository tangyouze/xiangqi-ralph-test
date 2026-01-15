"""
揭棋 AI CLI

统一的命令行接口，支持 Python 和 Rust 后端：
- moves: 获取合法走法
- best: 获取 AI 推荐走法
- list: 列出所有策略

## 使用示例

```bash
# 使用 Python 后端（默认）
python -m jieqi.ai_cli best --fen "..." --strategy greedy --n 5

# 使用 Rust 后端
python -m jieqi.ai_cli best --fen "..." --backend rust --strategy minimax --n 5

# 列出策略
python -m jieqi.ai_cli list --backend python
python -m jieqi.ai_cli list --backend rust
```
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass

import typer

from jieqi.ai.unified import UnifiedAIEngine

app = typer.Typer(help="Xiangqi (Jieqi) AI Engine - 支持 Python/Rust 后端")


@dataclass
class MoveResult:
    """单个走法结果"""

    move: str
    score: float


@dataclass
class MovesResponse:
    """走法响应"""

    moves: list[MoveResult]
    total: int


@app.command()
def moves(
    fen: str = typer.Option(..., "--fen", "-f", help="FEN 字符串"),
    backend: str = typer.Option("python", "--backend", "-b", help="后端 (python/rust)"),
    output_json: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """获取合法走法"""
    try:
        engine = UnifiedAIEngine(backend=backend)  # type: ignore
        legal_moves = engine.get_legal_moves(fen)

        if output_json:
            response = {"backend": backend, "moves": legal_moves, "total": len(legal_moves)}
            print(json.dumps(response, indent=2))
        else:
            print(f"Legal moves ({len(legal_moves)}, backend={backend}):")
            for mv in legal_moves:
                print(f"  {mv}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from None


@app.command()
def best(
    fen: str = typer.Option(..., "--fen", "-f", help="FEN 字符串"),
    backend: str = typer.Option("python", "--backend", "-b", help="后端 (python/rust)"),
    strategy: str = typer.Option("greedy", "--strategy", "-s", help="AI 策略"),
    n: int = typer.Option(1, "--n", "-n", help="返回的走法数量"),
    output_json: bool = typer.Option(False, "--json", help="JSON 输出"),
    time_limit: float | None = typer.Option(None, "--time", "-t", help="时间限制（秒）"),
) -> None:
    """选择最佳走法"""
    try:
        engine = UnifiedAIEngine(backend=backend, strategy=strategy, time_limit=time_limit)  # type: ignore
        moves_with_scores = engine.get_best_moves(fen, n)

        if output_json:
            response = {
                "backend": backend,
                "strategy": strategy,
                "time_limit": time_limit,
                "total": len(moves_with_scores),
                "moves": [{"move": mv, "score": score} for mv, score in moves_with_scores],
            }
            print(json.dumps(response, indent=2))
        else:
            time_str = f", time={time_limit}s" if time_limit else ""
            print(f"Best moves (backend={backend}, strategy={strategy}{time_str}):")
            for mv, score in moves_with_scores:
                print(f"  {mv} (score: {score:.2f})")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from None


@app.command(name="list")
def list_strategies(
    backend: str = typer.Option("python", "--backend", "-b", help="后端 (python/rust)"),
) -> None:
    """列出所有可用的 AI 策略"""
    try:
        engine = UnifiedAIEngine(backend=backend)  # type: ignore
        strategies = engine.list_strategies()

        print(f"Available strategies for {backend} backend ({len(strategies)}):")
        for s in strategies:
            print(f"  {s}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from None


@app.command()
def backends() -> None:
    """列出所有可用的后端"""
    backends_list = UnifiedAIEngine.list_backends()
    print(f"Available backends ({len(backends_list)}):")
    for b in backends_list:
        print(f"  {b}")


if __name__ == "__main__":
    app()
