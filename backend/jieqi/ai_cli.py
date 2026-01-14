"""
揭棋 AI CLI

提供与 Rust AI 一致的命令行接口：
- moves: 获取合法走法
- best: 获取 AI 推荐走法
- list: 列出所有策略
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass

import typer

from jieqi.ai import AIConfig, AIEngine
from jieqi.fen import get_legal_moves_from_fen

app = typer.Typer(help="Xiangqi (Jieqi) AI Engine")


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
    output_json: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """获取合法走法"""
    try:
        legal_moves = get_legal_moves_from_fen(fen)

        if output_json:
            response = {"moves": legal_moves, "total": len(legal_moves)}
            print(json.dumps(response, indent=2))
        else:
            print(f"Legal moves ({len(legal_moves)}):")
            for mv in legal_moves:
                print(f"  {mv}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def best(
    fen: str = typer.Option(..., "--fen", "-f", help="FEN 字符串"),
    strategy: str = typer.Option("greedy", "--strategy", "-s", help="AI 策略"),
    depth: int = typer.Option(3, "--depth", "-d", help="搜索深度"),
    n: int = typer.Option(1, "--n", "-n", help="返回的走法数量"),
    output_json: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """选择最佳走法"""
    try:
        config = AIConfig(depth=depth)
        ai = AIEngine.create(strategy, config)
        moves_with_scores = ai.select_moves_fen(fen, n)

        if output_json:
            response = MovesResponse(
                total=len(moves_with_scores),
                moves=[MoveResult(move=mv, score=score) for mv, score in moves_with_scores],
            )
            print(json.dumps(asdict(response), indent=2))
        else:
            print(f"Best moves (strategy={strategy}, depth={depth}):")
            for mv, score in moves_with_scores:
                print(f"  {mv} (score: {score:.2f})")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command(name="list")
def list_strategies() -> None:
    """列出所有可用的 AI 策略"""
    strategies = AIEngine.list_strategies()
    print(f"Available strategies ({len(strategies)}):")
    for s in strategies:
        print(f"  {s['name']}: {s['description']}")


if __name__ == "__main__":
    app()
