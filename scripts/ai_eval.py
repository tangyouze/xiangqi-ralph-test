"""
AI 评估脚本

功能：
- report: 生成 AI 评估 HTML 报告
"""

from pathlib import Path

import typer

app = typer.Typer(help="AI Evaluation Tools")


@app.command()
def report(
    strategy: str = typer.Option("muses", "--strategy", "-s", help="AI strategy name"),
    time_limit: float = typer.Option(0.5, "--time", "-t", help="Time limit in seconds"),
    output: str = typer.Option("data/reports", "--output", "-o", help="Output directory"),
    winrate: bool = typer.Option(False, "--winrate/--no-winrate", help="Test win rate"),
    winrate_games: int = typer.Option(5, "--winrate-games", help="Number of games"),
    winrate_time: float = typer.Option(1.0, "--winrate-time", help="Time per move"),
    workers: int = typer.Option(4, "--workers", "-w", help="Parallel workers"),
) -> None:
    """Generate AI evaluation HTML report"""
    from jieqi.ai.report import EVAL_SCENARIOS, generate_report
    from jieqi.logging import logger

    output_path = Path(output)

    logger.info(f"Generating report for {strategy}")
    logger.info(f"Config: time_limit={time_limit}s")
    if winrate:
        logger.info(
            f"Win rate test: {winrate_games} games, {winrate_time}s/move, {workers} workers"
        )

    report = generate_report(
        strategy=strategy,
        scenarios=EVAL_SCENARIOS,
        config={
            "time_limit": time_limit,
            "test_winrate": winrate,
            "winrate_games": winrate_games,
            "winrate_time_limit": winrate_time,
            "max_workers": workers,
        },
    )

    # 保存报告
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = report.timestamp.replace(" ", "_").replace(":", "-")
    report_path = output_path / f"{strategy}_{timestamp}.html"
    report.save(report_path)

    logger.info(f"Report saved to: {report_path}")
    print(f"\nReport saved to: {report_path}")
    print(f"Open with: open {report_path}")


@app.command()
def list_scenarios() -> None:
    """List all evaluation scenarios"""
    from jieqi.ai.report import EVAL_SCENARIOS

    print(f"Total scenarios: {len(EVAL_SCENARIOS)}\n")
    for name, fen in EVAL_SCENARIOS:
        print(f"  {name}")
        print(f"    {fen}\n")


if __name__ == "__main__":
    app()
