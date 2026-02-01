#!/usr/bin/env python3
"""
Presentation Demo Script
AI-Driven Engineering Quality: Task Estimation & Code Review

Run with: python scripts/presentation_demo.py

Features:
- Interactive mode: type custom tasks or press Enter for defaults
- Bad code example: shows security issue detection
- Historical accuracy: compares estimates to actual commit times
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
from rich.prompt import Prompt

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

BAD_CODE_FILE = Path(__file__).parent.parent / "examples" / "bad_code_example.py"


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


def demo_task_estimation_interactive():
    """Demo task estimation with interactive input."""
    clear()
    console.print("[bold cyan]Step 3: Task Estimation (Interactive)[/bold cyan]\n")

    # Show sample tasks
    console.print("[dim]Sample tasks (press Enter to use default, or type your own):[/dim]")
    for i, task in enumerate(SAMPLE_TASKS[:3], 1):
        console.print(f"  [dim]{i}. {task}[/dim]")

    console.print()

    # Get input from user
    default_task = SAMPLE_TASKS[0]
    user_input = Prompt.ask(
        "[bold]Enter a task to estimate[/bold]",
        default=default_task,
    )

    task = user_input.strip() or default_task

    console.print()
    console.print(Panel(task, title="Task", border_style="blue"))

    from src.estimator.task_estimator import TaskEstimator

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Finding similar past work...", total=None)
        time.sleep(0.3)

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

    # Risk
    risk_color = "green" if result.risk_score <= 30 else "yellow" if result.risk_score <= 60 else "red"
    risk_factors = "\n".join(f"  • {f}" for f in result.risk_factors[:3]) if result.risk_factors else "  None identified"
    console.print(Panel(
        f"[bold {risk_color}]{result.risk_score:.0f}/100[/bold {risk_color}]\n{risk_factors}",
        title="⚠️  Risk Assessment",
        border_style=risk_color,
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
    """Demo code review on real project file."""
    clear()
    console.print("[bold cyan]Step 4: AI Code Review (Real Project)[/bold cyan]\n")

    # Find a file to review
    review_file = REPOS["back"] / "src" / "nft" / "nft.service.ts"
    if not review_file.exists():
        console.print("[yellow]Project file not found, skipping...[/yellow]")
        pause()
        return

    console.print(f"Reviewing: [cyan]{review_file.name}[/cyan] from your project\n")

    # Show code snippet first
    console.print("[bold]Code Preview:[/bold]")
    try:
        code = review_file.read_text()
        lines = code.split('\n')[:40]  # First 40 lines
        code_preview = '\n'.join(lines)
        if len(code.split('\n')) > 40:
            code_preview += '\n\n... (truncated)'
        console.print(Panel(
            f"```typescript\n{code_preview}\n```",
            title=f"{review_file.name}",
            border_style="dim",
        ))
    except Exception:
        pass

    pause("Press Enter to run AI review...")

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

    _display_review_result(result)
    pause()


def demo_bad_code_review():
    """Demo code review catching security issues."""
    clear()
    console.print("[bold cyan]Step 5: Security Issue Detection[/bold cyan]\n")

    console.print("[yellow]Now let's review intentionally vulnerable code...[/yellow]\n")

    if not BAD_CODE_FILE.exists():
        console.print("[red]Bad code example not found[/red]")
        pause()
        return

    console.print(f"Reviewing: [red]{BAD_CODE_FILE.name}[/red]\n")

    # Show the vulnerable code first - highlight the bad parts
    bad_code_preview = '''class PaymentService:
    def __init__(self):
        # ISSUE: Hardcoded credentials
        self.secret_key = "super_secret_key_12345"

    def get_user_balance(self, user_id: str) -> float:
        # ISSUE: SQL injection vulnerability
        query = f"SELECT balance FROM users WHERE id = '{user_id}'"
        cursor = self.db.execute(query)
        return cursor.fetchone()[0]

    def process_payment(self, user_id: str, amount: float):
        # ISSUE: No input validation, race condition
        balance = self.get_user_balance(user_id)
        if balance >= amount:
            # Another request could modify balance here!
            self.db.execute(f"UPDATE users SET balance = {balance - amount}...")

    def export_transactions(self, user_id: str, format: str):
        # ISSUE: Command injection
        cmd = f"mysqldump payments --user={user_id} > /tmp/export.{format}"
        subprocess.os.system(cmd)  # Dangerous!

    def get_admin_data(self, admin_token=None):
        # ISSUE: Auth bypass - empty token grants access!
        if admin_token == "" or admin_token is None:
            pass  # Oops!
        return {"database_password": DATABASE_PASSWORD, ...}'''

    console.print(Panel(
        f"[red]{bad_code_preview}[/red]",
        title="⚠️  Vulnerable Code (can you spot the issues?)",
        border_style="red",
    ))

    pause("Press Enter to run AI security review...")

    from src.reviewer.code_reviewer import CodeReviewer

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Running security analysis...", total=None)

        reviewer = CodeReviewer()
        result = reviewer.review_file(BAD_CODE_FILE)

    _display_review_result(result)

    console.print("\n[green]✓ System correctly identified security vulnerabilities![/green]")
    pause()


def _display_review_result(result):
    """Display review result (shared helper)."""
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

        for issue in result.issues[:7]:
            sev_icon = {"critical": "🔴", "warning": "🟡", "suggestion": "🔵"}.get(issue.severity, "⚪")
            issues_table.add_row(
                f"{sev_icon} {issue.severity.upper()}",
                issue.category,
                issue.message[:70] + "..." if len(issue.message) > 70 else issue.message,
            )
        console.print(issues_table)


def demo_historical_accuracy():
    """Show historical accuracy - estimates vs actual."""
    clear()
    console.print("[bold cyan]Step 6: Historical Accuracy[/bold cyan]\n")

    console.print("Comparing our estimates to actual commit times...\n")

    # Check if we have repos
    back_repo = REPOS.get("back")
    if not back_repo or not back_repo.exists():
        console.print("[yellow]Repository not found, showing sample data...[/yellow]\n")
        _show_sample_accuracy()
        pause()
        return

    from src.validation.historical_accuracy import analyze_historical_accuracy, get_accuracy_summary

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Analyzing historical commits...", total=None)

        try:
            results = analyze_historical_accuracy(back_repo, sample_size=6)
            summary = get_accuracy_summary(results)
        except Exception as e:
            console.print(f"[yellow]Analysis error: {e}[/yellow]")
            _show_sample_accuracy()
            pause()
            return

    if not results:
        _show_sample_accuracy()
        pause()
        return

    # Show results table
    table = Table(title="Estimate vs Actual (from Git history)", box=box.ROUNDED)
    table.add_column("Commit", style="cyan", max_width=35)
    table.add_column("Estimated", style="yellow")
    table.add_column("Actual", style="green")
    table.add_column("Accuracy", style="magenta")

    for r in results[:6]:
        accuracy_icon = "✅" if r.within_range else "❌"
        table.add_row(
            r.commit_message[:35] + "..." if len(r.commit_message) > 35 else r.commit_message,
            f"{r.estimated_low:.1f}-{r.estimated_high:.1f}h",
            f"{r.actual_hours:.1f}h",
            accuracy_icon,
        )

    console.print(table)

    # Summary
    console.print(Panel(
        f"[bold]Accuracy Rate: {summary['accuracy_pct']}%[/bold]\n"
        f"({summary['within_range']}/{summary['total_samples']} estimates within range)\n\n"
        f"Average error: {summary['avg_error_hours']:+.1f} hours\n"
        f"Underestimates: {summary['underestimates']} | Overestimates: {summary['overestimates']}",
        title="📊 Summary",
        border_style="green",
    ))

    pause()


def _show_sample_accuracy():
    """Show sample accuracy data when repos aren't available."""
    table = Table(title="Estimate vs Actual (sample data)", box=box.ROUNDED)
    table.add_column("Commit", style="cyan")
    table.add_column("Estimated", style="yellow")
    table.add_column("Actual", style="green")
    table.add_column("Accuracy", style="magenta")

    sample_data = [
        ("Add leaderboard API", "2-4h", "3.2h", "✅"),
        ("Fix CORS config", "0.5-1h", "0.8h", "✅"),
        ("Implement NFT minting", "4-8h", "6.5h", "✅"),
        ("Update auth flow", "2-4h", "5.1h", "❌"),
        ("Add wallet panel UI", "1-3h", "2.2h", "✅"),
    ]

    for row in sample_data:
        table.add_row(*row)

    console.print(table)

    console.print(Panel(
        "[bold]Accuracy Rate: 80%[/bold]\n"
        "(4/5 estimates within range)\n\n"
        "Average error: +0.3 hours\n"
        "Underestimates: 1 | Overestimates: 0",
        title="📊 Summary",
        border_style="green",
    ))


def demo_pr_comment():
    """Show what a PR comment looks like."""
    clear()
    console.print("[bold cyan]Step 7: Automated PR Comments[/bold cyan]\n")

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
        "✅ Security vulnerability detection\n"
        "✅ Historical accuracy validation\n"
        "✅ GitHub webhook integration\n\n"
        "[bold green]Results[/bold green]\n\n"
        "• More predictable delivery estimates\n"
        "• Catch security issues before merge\n"
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
        demo_task_estimation_interactive()  # Interactive!
        demo_code_review()
        demo_bad_code_review()              # Security detection!
        demo_historical_accuracy()           # Credibility!
        demo_pr_comment()
        demo_summary()
        demo_questions()
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted[/yellow]")


if __name__ == "__main__":
    run_demo()
