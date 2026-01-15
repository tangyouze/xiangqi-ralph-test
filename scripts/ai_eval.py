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
    backend: str = typer.Option("rust", "--backend", "-b", help="Backend: python or rust"),
    depth: int = typer.Option(4, "--depth", "-d", help="Search depth"),
    time_limit: float = typer.Option(1.0, "--time", "-t", help="Time limit in seconds"),
    output: str = typer.Option("data/reports", "--output", "-o", help="Output directory"),
) -> None:
    """Generate AI evaluation HTML report"""
    from jieqi.ai.report import EVAL_SCENARIOS, generate_report
    from jieqi.logging import logger

    output_path = Path(output)

    logger.info(f"Generating report for {strategy} ({backend})")
    logger.info(f"Config: depth={depth}, time_limit={time_limit}s")

    report = generate_report(
        strategy=strategy,
        backend=backend,
        scenarios=EVAL_SCENARIOS,
        config={"depth": depth, "time_limit": time_limit},
    )

    # 保存报告
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = report.timestamp.replace(" ", "_").replace(":", "-")
    report_path = output_path / f"{strategy}_{backend}_{timestamp}.html"
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
