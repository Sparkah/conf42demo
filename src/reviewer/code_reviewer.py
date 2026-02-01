"""
AI-powered code review with risk scoring.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from src.utils.llm_client import get_llm_client
from src.analyzers.code_analyzer import CodeAnalyzer, CodeMetrics


@dataclass
class ReviewIssue:
    """A single issue found during code review."""

    severity: str  # "critical", "warning", "suggestion"
    category: str  # "security", "performance", "maintainability", "bug", "style"
    file: str
    line: int | None
    message: str
    suggestion: str | None = None


@dataclass
class ReviewResult:
    """Complete review result for code changes."""

    # Overall scores
    risk_score: float  # 0-100
    quality_score: float  # 0-100

    # Issues found
    issues: list[ReviewIssue]

    # Summary
    summary: str
    merge_recommendation: str  # "approve", "request_changes", "needs_discussion"

    # Metrics from static analysis
    static_metrics: dict

    def to_dict(self) -> dict:
        return {
            "risk_score": self.risk_score,
            "quality_score": self.quality_score,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "file": i.file,
                    "line": i.line,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
            "summary": self.summary,
            "merge_recommendation": self.merge_recommendation,
            "static_metrics": self.static_metrics,
        }


class CodeReviewer:
    """Reviews code changes using static analysis + LLM."""

    def __init__(self):
        self.llm = None  # Lazy load

    def _get_llm(self):
        """Lazy load LLM client."""
        if self.llm is None:
            self.llm = get_llm_client()
        return self.llm

    def _read_file_content(self, file_path: Path, max_lines: int = 500) -> str:
        """Read file content with line limit."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            if len(lines) > max_lines:
                lines = lines[:max_lines]
                lines.append(f"\n... truncated ({len(lines)} more lines)")
            return "\n".join(lines)
        except Exception as e:
            return f"Error reading file: {e}"

    def _get_git_diff(self, repo_path: Path) -> str:
        """Get the current git diff."""
        import subprocess

        try:
            # Get staged diff
            result = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            diff = result.stdout

            # If no staged changes, get unstaged diff
            if not diff.strip():
                result = subprocess.run(
                    ["git", "diff"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )
                diff = result.stdout

            # If still no diff, get diff from last commit
            if not diff.strip():
                result = subprocess.run(
                    ["git", "diff", "HEAD~1"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )
                diff = result.stdout

            return diff[:10000]  # Limit diff size

        except Exception as e:
            return f"Error getting diff: {e}"

    def _review_with_llm(
        self,
        code_content: str,
        file_path: str,
        static_metrics: CodeMetrics | None,
    ) -> dict:
        """Use LLM to review code."""

        metrics_context = ""
        if static_metrics:
            metrics_context = f"""
## Static Analysis Results
- Cyclomatic Complexity: {static_metrics.cyclomatic_complexity:.1f}
- Lines of Code: {static_metrics.lines_of_code}
- Risk Score: {static_metrics.risk_score:.0f}/100
"""

        prompt = f"""You are an expert code reviewer. Review this code and identify issues.

## File: {file_path}
{metrics_context}

## Code
```
{code_content}
```

## Review Instructions
1. Check for security vulnerabilities (injection, auth issues, secrets)
2. Check for bugs and logic errors
3. Check for performance issues
4. Check for maintainability problems
5. Check for missing error handling

Provide your review in this JSON format:
{{
    "risk_score": <0-100>,
    "quality_score": <0-100>,
    "issues": [
        {{
            "severity": "<critical|warning|suggestion>",
            "category": "<security|performance|maintainability|bug|style>",
            "line": <line_number or null>,
            "message": "<description of issue>",
            "suggestion": "<how to fix>"
        }}
    ],
    "summary": "<1-2 sentence summary>",
    "merge_recommendation": "<approve|request_changes|needs_discussion>"
}}

Focus on meaningful issues, not style nitpicks. Return ONLY valid JSON."""

        llm = self._get_llm()
        content = llm.complete(prompt, max_tokens=2048, temperature=0.2)

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            return {
                "risk_score": 50,
                "quality_score": 50,
                "issues": [],
                "summary": "Unable to parse review",
                "merge_recommendation": "needs_discussion",
            }

    def review_file(self, file_path: Path) -> ReviewResult:
        """Review a single file."""
        content = self._read_file_content(file_path)

        # Get static analysis metrics
        analyzer = CodeAnalyzer(file_path.parent)
        static_metrics = analyzer.analyze_file(file_path)

        # Get LLM review
        llm_result = self._review_with_llm(content, str(file_path), static_metrics)

        issues = [
            ReviewIssue(
                severity=i.get("severity", "suggestion"),
                category=i.get("category", "maintainability"),
                file=str(file_path),
                line=i.get("line"),
                message=i.get("message", ""),
                suggestion=i.get("suggestion"),
            )
            for i in llm_result.get("issues", [])
        ]

        return ReviewResult(
            risk_score=llm_result.get("risk_score", 50),
            quality_score=llm_result.get("quality_score", 50),
            issues=issues,
            summary=llm_result.get("summary", ""),
            merge_recommendation=llm_result.get("merge_recommendation", "needs_discussion"),
            static_metrics={
                "complexity": static_metrics.cyclomatic_complexity,
                "loc": static_metrics.lines_of_code,
                "static_risk": static_metrics.risk_score,
            },
        )

    def review_diff(self, repo_path: Path) -> ReviewResult:
        """Review current git diff in a repository."""
        diff = self._get_git_diff(repo_path)

        if not diff.strip() or "Error" in diff:
            return ReviewResult(
                risk_score=0,
                quality_score=100,
                issues=[],
                summary="No changes to review",
                merge_recommendation="approve",
                static_metrics={},
            )

        # Review the diff content
        prompt = f"""You are an expert code reviewer. Review this git diff and identify issues.

## Git Diff
```diff
{diff}
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
            "line": <line_number or null>,
            "message": "<description of issue>",
            "suggestion": "<how to fix>"
        }}
    ],
    "summary": "<1-2 sentence summary of the changes and their quality>",
    "merge_recommendation": "<approve|request_changes|needs_discussion>"
}}

Return ONLY valid JSON."""

        llm = self._get_llm()
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
                "summary": "Unable to parse review",
                "merge_recommendation": "needs_discussion",
            }

        issues = [
            ReviewIssue(
                severity=i.get("severity", "suggestion"),
                category=i.get("category", "maintainability"),
                file=i.get("file", "unknown"),
                line=i.get("line"),
                message=i.get("message", ""),
                suggestion=i.get("suggestion"),
            )
            for i in llm_result.get("issues", [])
        ]

        return ReviewResult(
            risk_score=llm_result.get("risk_score", 50),
            quality_score=llm_result.get("quality_score", 50),
            issues=issues,
            summary=llm_result.get("summary", ""),
            merge_recommendation=llm_result.get("merge_recommendation", "needs_discussion"),
            static_metrics={"diff_lines": len(diff.split("\n"))},
        )
