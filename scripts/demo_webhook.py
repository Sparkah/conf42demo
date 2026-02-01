#!/usr/bin/env python3
"""
Demo script to simulate a GitHub webhook locally.
This lets you test the PR review flow without setting up a real webhook.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

load_dotenv()

console = Console()


async def demo_review_diff(repo_path: Path):
    """Demo: Review the latest commit as if it were a PR."""
    import subprocess

    # Get the diff from last commit
    result = subprocess.run(
        ["git", "diff", "HEAD~1"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    diff = result.stdout

    if not diff.strip():
        console.print("[yellow]No changes in last commit[/yellow]")
        return

    # Get commit message as "PR title"
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    pr_title = result.stdout.strip()

    # Count files
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    files = [f for f in result.stdout.strip().split("\n") if f]

    console.print(Panel(
        f"[bold]Simulating PR Review[/bold]\n\n"
        f"Title: {pr_title}\n"
        f"Files: {len(files)}\n"
        f"Diff size: {len(diff)} chars",
        title="Demo Webhook",
        border_style="blue",
    ))

    # Run the review
    from src.utils.llm_client import get_llm_client
    from src.api.github_webhook import format_review_comment
    from src.reviewer.code_reviewer import ReviewResult, ReviewIssue
    import json

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Running AI review...", total=None)

        llm = get_llm_client()

        prompt = f"""You are an expert code reviewer. Review this GitHub PR diff and identify issues.

## PR Title: {pr_title}
## Files Changed: {len(files)}

## Diff
```diff
{diff[:10000]}
```

## Review Instructions
1. Check for security vulnerabilities
2. Check for bugs and logic errors
3. Check for breaking changes
4. Check for missing error handling
5. Consider the impact of these changes

Provide your review in this JSON format:
{{
    "risk_score": <0-100>,
    "quality_score": <0-100>,
    "issues": [
        {{
            "severity": "<critical|warning|suggestion>",
            "category": "<security|performance|maintainability|bug|style>",
            "file": "<filename>",
            "message": "<description of issue>",
            "suggestion": "<how to fix>"
        }}
    ],
    "summary": "<1-2 sentence summary of the changes and their quality>",
    "merge_recommendation": "<approve|request_changes|needs_discussion>"
}}

Return ONLY valid JSON."""

        content = llm.complete(prompt, max_tokens=2048, temperature=0.2)

    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        llm_result = json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        llm_result = {
            "risk_score": 50,
            "quality_score": 50,
            "issues": [],
            "summary": "Unable to analyze PR",
            "merge_recommendation": "needs_discussion",
        }

    # Create result object
    issues = [
        ReviewIssue(
            severity=i.get("severity", "suggestion"),
            category=i.get("category", "maintainability"),
            file=i.get("file", "unknown"),
            line=None,
            message=i.get("message", ""),
            suggestion=i.get("suggestion"),
        )
        for i in llm_result.get("issues", [])
    ]

    result = ReviewResult(
        risk_score=llm_result.get("risk_score", 50),
        quality_score=llm_result.get("quality_score", 50),
        issues=issues,
        summary=llm_result.get("summary", ""),
        merge_recommendation=llm_result.get("merge_recommendation", "needs_discussion"),
        static_metrics={},
    )

    # Format as GitHub comment
    comment = format_review_comment(result, pr_title, len(files))

    console.print("\n[bold green]Generated PR Comment:[/bold green]\n")
    console.print(Panel(comment, title="GitHub PR Comment Preview", border_style="green"))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Demo webhook PR review")
    parser.add_argument("repo", nargs="?", default="../back", help="Path to repo")
    args = parser.parse_args()

    repo_path = Path(args.repo).resolve()
    if not (repo_path / ".git").exists():
        console.print(f"[red]Not a git repo: {repo_path}[/red]")
        sys.exit(1)

    asyncio.run(demo_review_diff(repo_path))


if __name__ == "__main__":
    main()
