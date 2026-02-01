"""
CLI interface for AI Engineering Quality system.
"""

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from dotenv import load_dotenv

from src.analyzers.commit_analyzer import CommitAnalyzer
from src.analyzers.code_analyzer import CodeAnalyzer

load_dotenv()

app = typer.Typer(
    name="aeq",
    help="AI Engineering Quality - Task estimation and code review",
    add_completion=False,
)
console = Console()


def check_api_key() -> bool:
    """Check if any API key is available."""
    return bool(os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))


@app.command()
def analyze(
    repo_path: Path = typer.Argument(..., help="Path to git repository"),
    output_dir: Path = typer.Option("./data", help="Output directory for analysis"),
):
    """Analyze a repository's commit history."""
    if not repo_path.exists():
        console.print(f"[red]Repository not found: {repo_path}[/red]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Analyzing commits...", total=None)

        analyzer = CommitAnalyzer(repo_path)
        commits = analyzer.analyze_commits()

        output_path = output_dir / f"{repo_path.name}_commits.json"
        analyzer.save_to_json(commits, output_path)

    # Display summary
    table = Table(title=f"Commit Analysis: {repo_path.name}", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Commits", str(len(commits)))
    table.add_row("Date Range", f"{commits[0].timestamp.date()} to {commits[-1].timestamp.date()}")
    table.add_row("Total Churn", f"{sum(c.total_churn for c in commits):,} lines")

    # Category breakdown
    categories = {}
    for c in commits:
        categories[c.category] = categories.get(c.category, 0) + 1
    table.add_row("Categories", ", ".join(f"{k}: {v}" for k, v in sorted(categories.items())))

    console.print(table)
    console.print(f"\n[green]Saved to {output_path}[/green]")


@app.command()
def index(
    repos: list[Path] = typer.Argument(..., help="Paths to repositories to index"),
    data_dir: Path = typer.Option("./data", help="Data directory"),
):
    """Index repositories for task estimation."""
    from src.estimator.task_estimator import TaskEstimator

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Indexing repositories...", total=len(repos))

        estimator = TaskEstimator(chroma_path=str(data_dir / "chroma"))
        total_indexed = 0

        for repo_path in repos:
            if not (repo_path / ".git").exists():
                console.print(f"[yellow]Skipping {repo_path} (not a git repo)[/yellow]")
                progress.advance(task)
                continue

            analyzer = CommitAnalyzer(repo_path)
            commits = analyzer.analyze_commits()

            count = estimator.index_commits(commits, repo_path.name)
            total_indexed += count
            progress.advance(task)

    console.print(f"\n[green]Indexed {total_indexed} commits from {len(repos)} repos[/green]")


@app.command()
def estimate(
    task_description: str = typer.Argument(..., help="Description of the task to estimate"),
    data_dir: Path = typer.Option("./data", help="Data directory with indexed commits"),
):
    """Estimate difficulty and time for a task."""
    if not check_api_key():
        console.print("[red]Error: Set OPENROUTER_API_KEY or ANTHROPIC_API_KEY[/red]")
        console.print("Example: export OPENROUTER_API_KEY=your-key")
        raise typer.Exit(1)

    from src.estimator.task_estimator import TaskEstimator

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Analyzing task...", total=None)

        estimator = TaskEstimator(chroma_path=str(data_dir / "chroma"))
        result = estimator.estimate_task(task_description)

    # Display results
    console.print()
    console.print(Panel(task_description, title="Task", border_style="blue"))

    # Time estimate
    time_panel = Panel(
        f"[bold]{result.estimated_hours_low:.1f} - {result.estimated_hours_high:.1f} hours[/bold]\n"
        f"Confidence: {result.confidence:.0%}",
        title="Estimated Time",
        border_style="green",
    )
    console.print(time_panel)

    # Complexity
    complexity_color = "green" if result.complexity_score <= 3 else "yellow" if result.complexity_score <= 6 else "red"
    console.print(
        Panel(
            f"[bold {complexity_color}]{result.complexity_score}/10[/bold {complexity_color}]\n"
            f"{result.complexity_reasoning}",
            title="Complexity",
            border_style=complexity_color,
        )
    )

    # Risk
    risk_color = "green" if result.risk_score <= 30 else "yellow" if result.risk_score <= 60 else "red"
    risk_factors = "\n".join(f"  - {f}" for f in result.risk_factors) if result.risk_factors else "  None identified"
    console.print(
        Panel(
            f"[bold {risk_color}]{result.risk_score:.0f}/100[/bold {risk_color}]\n{risk_factors}",
            title="Risk Assessment",
            border_style=risk_color,
        )
    )

    # Similar work
    if result.similar_commits:
        table = Table(title="Similar Past Work", box=box.ROUNDED)
        table.add_column("Commit", style="cyan")
        table.add_column("Files", style="yellow")
        table.add_column("Churn", style="magenta")
        table.add_column("Similarity", style="green")

        for commit in result.similar_commits[:3]:
            table.add_row(
                commit["message"][:50] + "..." if len(commit["message"]) > 50 else commit["message"],
                str(commit["files_changed"]),
                str(commit["total_churn"]),
                f"{commit['similarity']:.0%}",
            )
        console.print(table)

    # Recommendations
    if result.recommendations:
        recs = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(result.recommendations))
        console.print(Panel(recs, title="Recommendations", border_style="blue"))


@app.command()
def review(
    path: Path = typer.Argument(..., help="File or repository to review"),
    diff: bool = typer.Option(False, "--diff", "-d", help="Review git diff instead of file"),
):
    """Review code for quality and risk."""
    if not check_api_key():
        console.print("[red]Error: Set OPENROUTER_API_KEY or ANTHROPIC_API_KEY[/red]")
        console.print("Example: export OPENROUTER_API_KEY=your-key")
        raise typer.Exit(1)

    from src.reviewer.code_reviewer import CodeReviewer

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Reviewing code...", total=None)

        reviewer = CodeReviewer()

        if diff:
            result = reviewer.review_diff(path)
        else:
            result = reviewer.review_file(path)

    # Display results
    console.print()

    # Scores
    risk_color = "green" if result.risk_score <= 30 else "yellow" if result.risk_score <= 60 else "red"
    quality_color = "green" if result.quality_score >= 70 else "yellow" if result.quality_score >= 40 else "red"

    scores_table = Table(box=box.ROUNDED, show_header=False)
    scores_table.add_column("Metric", style="bold")
    scores_table.add_column("Score")
    scores_table.add_row("Risk Score", f"[{risk_color}]{result.risk_score:.0f}/100[/{risk_color}]")
    scores_table.add_row("Quality Score", f"[{quality_color}]{result.quality_score:.0f}/100[/{quality_color}]")
    scores_table.add_row(
        "Recommendation",
        f"[bold]{'[green]APPROVE' if result.merge_recommendation == 'approve' else '[yellow]DISCUSS' if result.merge_recommendation == 'needs_discussion' else '[red]REQUEST CHANGES'}[/bold]",
    )
    console.print(scores_table)

    # Summary
    console.print(Panel(result.summary, title="Summary", border_style="blue"))

    # Issues
    if result.issues:
        issues_table = Table(title="Issues Found", box=box.ROUNDED)
        issues_table.add_column("Severity", style="bold")
        issues_table.add_column("Category")
        issues_table.add_column("Message")
        issues_table.add_column("Suggestion", style="dim")

        for issue in result.issues:
            severity_color = "red" if issue.severity == "critical" else "yellow" if issue.severity == "warning" else "blue"
            issues_table.add_row(
                f"[{severity_color}]{issue.severity.upper()}[/{severity_color}]",
                issue.category,
                issue.message[:60] + "..." if len(issue.message) > 60 else issue.message,
                (issue.suggestion[:40] + "..." if issue.suggestion and len(issue.suggestion) > 40 else issue.suggestion) or "",
            )
        console.print(issues_table)
    else:
        console.print("[green]No issues found![/green]")


@app.command()
def metrics(
    repo_path: Path = typer.Argument(..., help="Path to repository"),
):
    """Show code metrics for a repository."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Analyzing code...", total=None)

        analyzer = CodeAnalyzer(repo_path)
        summary = analyzer.get_repo_summary()

    table = Table(title=f"Code Metrics: {repo_path.name}", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Files", str(summary.get("total_files", 0)))
    table.add_row("Total Lines", f"{summary.get('total_loc', 0):,}")
    table.add_row("Avg Complexity", f"{summary.get('avg_complexity', 0):.1f}")
    table.add_row("Avg Risk Score", f"{summary.get('avg_risk_score', 0):.0f}/100")
    table.add_row("Languages", ", ".join(summary.get("languages", [])))

    console.print(table)

    if summary.get("high_risk_files"):
        console.print("\n[yellow]High Risk Files:[/yellow]")
        for f in summary["high_risk_files"][:5]:
            console.print(f"  - {f}")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to listen on"),
):
    """Start the webhook server for GitHub integration."""
    import uvicorn

    if not check_api_key():
        console.print("[yellow]Warning: No LLM API key set. Reviews will fail.[/yellow]")

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        console.print("[yellow]Warning: GITHUB_TOKEN not set. Cannot post PR comments.[/yellow]")
        console.print("Set it with: export GITHUB_TOKEN=ghp_...")

    console.print(Panel(
        f"[bold green]Starting webhook server[/bold green]\n\n"
        f"Listening on: http://{host}:{port}\n"
        f"Webhook URL:  http://{host}:{port}/webhook/github\n\n"
        "To expose publicly, use ngrok:\n"
        f"  ngrok http {port}",
        title="Webhook Server",
        border_style="green",
    ))

    from src.api.github_webhook import app as webhook_app
    uvicorn.run(webhook_app, host=host, port=port)


@app.command()
def demo():
    """Run interactive demo for presentation."""
    api_status = "[green]configured[/green]" if check_api_key() else "[red]not set[/red]"
    github_status = "[green]configured[/green]" if os.getenv("GITHUB_TOKEN") else "[red]not set[/red]"

    console.print(Panel(
        "[bold blue]AI Engineering Quality Demo[/bold blue]\n\n"
        "This demo shows how AI can help with:\n"
        "  1. Task estimation based on historical data\n"
        "  2. Code review with risk scoring\n"
        "  3. Codebase quality metrics\n"
        "  4. Automated PR reviews via webhooks\n\n"
        f"LLM API Key: {api_status}\n"
        f"GitHub Token: {github_status}",
        title="Welcome",
        border_style="blue",
    ))

    console.print("\n[bold]Available commands:[/bold]")
    console.print("  aeq analyze <repo>     - Analyze commit history")
    console.print("  aeq index <repos>      - Index repos for estimation")
    console.print("  aeq estimate <task>    - Estimate a task")
    console.print("  aeq review <file>      - Review code")
    console.print("  aeq review -d <repo>   - Review git diff")
    console.print("  aeq metrics <repo>     - Show code metrics")
    console.print("  aeq serve              - Start webhook server")
    console.print("  aeq present            - Run presentation demo")


@app.command()
def present():
    """Run the full presentation demo (interactive)."""
    import subprocess
    import sys

    script_path = Path(__file__).parent.parent / "scripts" / "presentation_demo.py"
    subprocess.run([sys.executable, str(script_path)])


if __name__ == "__main__":
    app()
