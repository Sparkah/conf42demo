#!/usr/bin/env python3
"""
Presentation Demo Script
AI-Driven Engineering Quality: Task Estimation & Code Review

Run with: python scripts/presentation_demo.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from rich.markdown import Markdown

load_dotenv()

console = Console()

# Demo configuration
REPOS = {
    "back": Path(__file__).parent.parent.parent / "back",
    "front": Path(__file__).parent.parent.parent / "front",
    "sc": Path(__file__).parent.parent.parent / "sc",
}

SAMPLE_TASKS = [
    "Add a new leaderboard feature that shows top 10 players with pagination",
    "Implement wallet connection error handling with retry logic",
    "Add rate limiting to the NFT minting endpoint",
    "Create a caching layer for leaderboard queries",
]


def pause(message: str = "Press Enter to continue..."):
    """Pause for presenter."""
    console.print(f"\n[dim]{message}[/dim]")
    input()


def clear():
    """Clear screen."""
    console.clear()


def title_slide():
    """Show title slide."""
    clear()
    console.print(Panel(
        "[bold blue]AI-Driven Engineering Quality[/bold blue]\n\n"
        "[white]How We Use Machine Learning to Predict\n"
        "Delivery Time and Improve Code Reliability[/white]\n\n"
        "[dim]Demo System[/dim]",
        border_style="blue",
        padding=(2, 4),
    ))
    pause()


def demo_intro():
    """Introduce the demo."""
    clear()
    console.print(Panel(
        "[bold]The Problem[/bold]\n\n"
        "Engineering teams still plan with gut feel.\n\n"
        "• \"How long will this take?\" → 🤷 \"Maybe 2 days?\"\n"
        "• \"Is this PR risky?\" → 🤷 \"Looks fine to me\"\n"
        "• \"What could go wrong?\" → 🤷 \"We'll find out in prod\"\n\n"
        "[bold green]Our Solution[/bold green]\n\n"
        "A predictive pipeline that:\n"
        "• Estimates delivery time before coding starts\n"
        "• Quantifies code risk on every PR\n"
        "• Uses historical data + LLM analysis",
        title="Why This Matters",
        border_style="yellow",
    ))
    pause()


def demo_architecture():
    """Show system architecture."""
    clear()
    console.print(Panel(
        """[bold]System Architecture[/bold]

┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  [cyan]1. FEATURE EXTRACTION[/cyan]                                      │
│     ├── Git history: commits, churn, file ownership         │
│     ├── Static analysis: complexity, LOC, dependencies      │
│     └── Embeddings: commit messages → vectors               │
│                                                             │
│  [cyan]2. RAG RETRIEVAL[/cyan]                                           │
│     └── Find similar past work via semantic search          │
│                                                             │
│  [cyan]3. LLM ANALYSIS[/cyan]                                            │
│     ├── Task complexity reasoning                           │
│     ├── Risk factor identification                          │
│     └── Code smell detection                                │
│                                                             │
│  [cyan]4. OUTPUT[/cyan]                                                  │
│     ├── Time estimate with confidence                       │
│     ├── Risk score (0-100)                                  │
│     └── Actionable recommendations                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘""",
        title="How It Works",
        border_style="cyan",
    ))
    pause()


def demo_repo_analysis():
    """Analyze the repositories."""
    clear()
    console.print("[bold cyan]Step 1: Analyze Repository History[/bold cyan]\n")

    from src.analyzers.commit_analyzer import CommitAnalyzer

    all_commits = []

    table = Table(title="Repository Analysis", box=box.ROUNDED)
    table.add_column("Repo", style="cyan")
    table.add_column("Commits", style="green")
    table.add_column("Churn", style="yellow")
    table.add_column("Categories", style="magenta")

    for name, path in REPOS.items():
        if not path.exists():
            continue

        analyzer = CommitAnalyzer(path)
        commits = analyzer.analyze_commits()
        all_commits.extend(commits)

        categories = {}
        for c in commits:
            categories[c.category] = categories.get(c.category, 0) + 1
        top_cats = sorted(categories.items(), key=lambda x: -x[1])[:3]
        cat_str = ", ".join(f"{k}" for k, v in top_cats)

        table.add_row(
            name,
            str(len(commits)),
            f"{sum(c.total_churn for c in commits):,}",
            cat_str,
        )

    console.print(table)
    console.print(f"\n[green]Total: {len(all_commits)} commits indexed for RAG[/green]")
    pause()


def demo_code_metrics():
    """Show code metrics."""
    clear()
    console.print("[bold cyan]Step 2: Static Code Analysis[/bold cyan]\n")

    from src.analyzers.code_analyzer import CodeAnalyzer

    table = Table(title="Code Quality Metrics", box=box.ROUNDED)
    table.add_column("Repo", style="cyan")
    table.add_column("Files", style="green")
    table.add_column("Lines", style="yellow")
    table.add_column("Avg Complexity", style="magenta")
    table.add_column("Risk Score", style="red")

    for name, path in REPOS.items():
        if not path.exists():
            continue

        analyzer = CodeAnalyzer(path)
        summary = analyzer.get_repo_summary()

        risk_score = summary.get("avg_risk_score", 0)
        risk_color = "green" if risk_score < 30 else "yellow" if risk_score < 60 else "red"

        table.add_row(
            name,
            str(summary.get("total_files", 0)),
            f"{summary.get('total_loc', 0):,}",
            f"{summary.get('avg_complexity', 0):.1f}",
            f"[{risk_color}]{risk_score:.0f}/100[/{risk_color}]",
        )

    console.print(table)
    console.print("\n[dim]Metrics: cyclomatic complexity, nesting depth, file size[/dim]")
    pause()


def demo_task_estimation():
    """Demo task estimation."""
    clear()
    console.print("[bold cyan]Step 3: Task Estimation with RAG + LLM[/bold cyan]\n")

    from src.estimator.task_estimator import TaskEstimator

    task = SAMPLE_TASKS[0]
    console.print(Panel(task, title="Task", border_style="blue"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Finding similar past work...", total=None)
        time.sleep(0.5)

        estimator = TaskEstimator(chroma_path=str(Path(__file__).parent.parent / "data" / "chroma"))

        progress.add_task("Analyzing with LLM...", total=None)
        result = estimator.estimate_task(task)

    console.print()

    # Time estimate
    console.print(Panel(
        f"[bold]{result.estimated_hours_low:.1f} - {result.estimated_hours_high:.1f} hours[/bold]\n"
        f"Confidence: {result.confidence:.0%}",
        title="⏱️  Estimated Time",
        border_style="green",
    ))

    # Complexity
    complexity_color = "green" if result.complexity_score <= 3 else "yellow" if result.complexity_score <= 6 else "red"
    console.print(Panel(
        f"[bold {complexity_color}]{result.complexity_score}/10[/bold {complexity_color}]\n"
        f"{result.complexity_reasoning}",
        title="🧠 Complexity",
        border_style=complexity_color,
    ))

    # Similar work
    if result.similar_commits:
        table = Table(title="📚 Similar Past Work (RAG)", box=box.ROUNDED)
        table.add_column("Commit", style="cyan")
        table.add_column("Similarity", style="green")

        for commit in result.similar_commits[:3]:
            table.add_row(
                commit["message"][:60],
                f"{commit['similarity']:.0%}",
            )
        console.print(table)

    # Recommendations
    if result.recommendations:
        recs = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(result.recommendations[:3]))
        console.print(Panel(recs, title="💡 Recommendations", border_style="blue"))

    pause()


def demo_code_review():
    """Demo code review."""
    clear()
    console.print("[bold cyan]Step 4: AI Code Review[/bold cyan]\n")

    # Find a file to review
    review_file = REPOS["back"] / "src" / "nft" / "nft.service.ts"
    if not review_file.exists():
        console.print("[yellow]Demo file not found, skipping...[/yellow]")
        pause()
        return

    console.print(f"Reviewing: [cyan]{review_file.name}[/cyan]\n")

    from src.reviewer.code_reviewer import CodeReviewer

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Running static analysis...", total=None)
        time.sleep(0.3)
        progress.add_task("LLM code review...", total=None)

        reviewer = CodeReviewer()
        result = reviewer.review_file(review_file)

    # Scores
    risk_color = "green" if result.risk_score <= 30 else "yellow" if result.risk_score <= 60 else "red"
    quality_color = "green" if result.quality_score >= 70 else "yellow" if result.quality_score >= 40 else "red"

    scores_table = Table(box=box.ROUNDED, show_header=False)
    scores_table.add_column("Metric", style="bold")
    scores_table.add_column("Score")
    scores_table.add_row("Risk Score", f"[{risk_color}]{result.risk_score:.0f}/100[/{risk_color}]")
    scores_table.add_row("Quality Score", f"[{quality_color}]{result.quality_score:.0f}/100[/{quality_color}]")

    rec_display = {
        "approve": "[green]✅ APPROVE[/green]",
        "needs_discussion": "[yellow]💬 DISCUSS[/yellow]",
        "request_changes": "[red]❌ CHANGES NEEDED[/red]",
    }
    scores_table.add_row("Recommendation", rec_display.get(result.merge_recommendation, ""))
    console.print(scores_table)

    console.print(Panel(result.summary, title="Summary", border_style="blue"))

    # Issues
    if result.issues:
        issues_table = Table(title="Issues Found", box=box.ROUNDED)
        issues_table.add_column("Sev", style="bold", width=10)
        issues_table.add_column("Category", width=15)
        issues_table.add_column("Issue")

        for issue in result.issues[:5]:
            sev_icon = {"critical": "🔴", "warning": "🟡", "suggestion": "🔵"}.get(issue.severity, "⚪")
            issues_table.add_row(
                f"{sev_icon} {issue.severity.upper()}",
                issue.category,
                issue.message[:70] + "..." if len(issue.message) > 70 else issue.message,
            )
        console.print(issues_table)

    pause()


def demo_pr_comment():
    """Show what a PR comment looks like."""
    clear()
    console.print("[bold cyan]Step 5: Automated PR Comments[/bold cyan]\n")

    console.print("When integrated with GitHub/GitLab, the bot posts:\n")

    comment = """## 🤖 AI Code Review

✅ **APPROVE**

| Metric | Score |
|--------|-------|
| 🟢 Risk | **15/100** (Low Risk) |
| 🟢 Quality | **85/100** |
| 📁 Files Changed | 3 |

### Summary
Clean implementation of the leaderboard feature with proper error handling.
Minor suggestions for caching optimization.

### Issues Found
- 🟡 **WARNING** (performance): Database query could benefit from indexing
  - 💡 *Add index on score column for faster sorting*
- 🔵 **SUGGESTION** (maintainability): Consider extracting pagination logic
  - 💡 *Create a reusable pagination utility*

---
<sub>🤖 Generated by AI Engineering Quality Bot</sub>"""

    console.print(Panel(Markdown(comment), title="GitHub PR Comment", border_style="green"))
    pause()


def demo_summary():
    """Summary slide."""
    clear()
    console.print(Panel(
        "[bold]What We Built[/bold]\n\n"
        "✅ Feature extraction from Git history\n"
        "✅ Static code analysis (complexity, risk)\n"
        "✅ RAG over past commits for similar work\n"
        "✅ LLM-powered estimation & review\n"
        "✅ GitHub webhook integration\n\n"
        "[bold green]Results[/bold green]\n\n"
        "• More predictable delivery estimates\n"
        "• Catch issues before code review\n"
        "• PMs can prioritize by risk\n"
        "• Engineers see actionable fixes\n\n"
        "[bold cyan]Tech Stack[/bold cyan]\n\n"
        "Python • FastAPI • ChromaDB • Claude API",
        title="Summary",
        border_style="green",
        padding=(1, 2),
    ))
    pause()


def demo_questions():
    """Q&A slide."""
    clear()
    console.print(Panel(
        "[bold blue]Questions?[/bold blue]\n\n"
        "GitHub: [cyan]github.com/Sparkah/conf42demo[/cyan]\n\n"
        "Run the demo:\n"
        "  git clone https://github.com/Sparkah/conf42demo\n"
        "  cd conf42demo\n"
        "  pip install -e .\n"
        "  python scripts/presentation_demo.py",
        border_style="blue",
        padding=(2, 4),
    ))


def run_demo():
    """Run the full demo."""
    try:
        title_slide()
        demo_intro()
        demo_architecture()
        demo_repo_analysis()
        demo_code_metrics()
        demo_task_estimation()
        demo_code_review()
        demo_pr_comment()
        demo_summary()
        demo_questions()
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted[/yellow]")


if __name__ == "__main__":
    run_demo()
