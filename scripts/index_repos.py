#!/usr/bin/env python3
"""
Script to index all repositories in the parent directory.
"""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.analyzers.commit_analyzer import CommitAnalyzer
from src.estimator.task_estimator import TaskEstimator

load_dotenv()

console = Console()


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error: Set ANTHROPIC_API_KEY in .env[/red]")
        sys.exit(1)

    # Find repos in parent directory
    parent_dir = Path(__file__).parent.parent.parent
    repos = [
        parent_dir / "back",
        parent_dir / "front",
        parent_dir / "sc",
    ]

    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Indexing repositories...", total=len(repos))

        estimator = TaskEstimator(api_key, chroma_path=str(data_dir / "chroma"))
        total_indexed = 0
        total_commits = []

        for repo_path in repos:
            if not repo_path.exists() or not (repo_path / ".git").exists():
                console.print(f"[yellow]Skipping {repo_path.name}[/yellow]")
                progress.advance(task)
                continue

            console.print(f"[blue]Analyzing {repo_path.name}...[/blue]")

            analyzer = CommitAnalyzer(repo_path)
            commits = analyzer.analyze_commits()

            # Save to JSON
            analyzer.save_to_json(commits, data_dir / f"{repo_path.name}_commits.json")

            # Index for RAG
            count = estimator.index_commits(commits, repo_path.name)
            total_indexed += count
            total_commits.extend(commits)

            console.print(f"  [green]✓ {count} commits indexed[/green]")
            progress.advance(task)

    console.print(f"\n[bold green]Done! Indexed {total_indexed} commits[/bold green]")

    # Print summary stats
    console.print("\n[bold]Summary:[/bold]")
    categories = {}
    for c in total_commits:
        categories[c.category] = categories.get(c.category, 0) + 1

    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        console.print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
