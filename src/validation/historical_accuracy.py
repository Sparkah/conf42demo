"""
Historical accuracy validation - compare estimates to actual commit times.
"""

import json
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv
load_dotenv()

from src.analyzers.commit_analyzer import CommitAnalyzer, CommitData
from src.estimator.task_estimator import TaskEstimator


@dataclass
class AccuracyResult:
    """Result of comparing estimate to actual."""
    commit_message: str
    category: str

    # Actual metrics from git
    actual_hours: float  # Time since previous commit
    actual_files: int
    actual_churn: int

    # Our estimate
    estimated_low: float
    estimated_high: float
    confidence: float

    # Accuracy
    within_range: bool
    error_hours: float  # How far off (negative = underestimate)

    def to_dict(self) -> dict:
        return {
            "commit": self.commit_message,
            "category": self.category,
            "actual_hours": round(self.actual_hours, 1),
            "estimated_range": f"{self.estimated_low:.1f}-{self.estimated_high:.1f}h",
            "within_range": self.within_range,
            "error": f"{self.error_hours:+.1f}h",
        }


def analyze_historical_accuracy(
    repo_path: Path,
    sample_size: int = 10,
    min_hours: float = 0.2,  # Skip instant commits (< 12 min)
    max_hours: float = 6.0,  # Skip overnight gaps
) -> list[AccuracyResult]:
    """
    Analyze historical accuracy by comparing estimates to actual commit times.

    Uses time between commits as a proxy for actual work time.
    Filters out outliers (too quick or overnight gaps).

    Note: This is an approximation - works best for focused coding sessions.
    We cap at 6h to filter overnight gaps.
    """

    # Get commit history
    analyzer = CommitAnalyzer(repo_path)
    commits = analyzer.analyze_commits()

    # Filter commits with reasonable time gaps (within a work session)
    valid_commits = [
        c for c in commits
        if c.time_since_last_commit_hours is not None
        and min_hours <= c.time_since_last_commit_hours <= max_hours
        and c.total_churn > 3  # Skip trivial commits
    ]

    # Sample commits for analysis
    if len(valid_commits) > sample_size:
        # Take evenly spaced samples
        step = len(valid_commits) // sample_size
        valid_commits = valid_commits[::step][:sample_size]

    # Initialize estimator
    estimator = TaskEstimator(
        chroma_path=str(Path(__file__).parent.parent.parent / "data" / "chroma")
    )

    results = []

    for commit in valid_commits:
        # Get estimate for this commit's message (as if it were a task)
        try:
            estimate = estimator.estimate_task(commit.message)

            actual = commit.time_since_last_commit_hours
            est_low = estimate.estimated_hours_low
            est_high = estimate.estimated_hours_high

            # Check if actual is within estimated range
            within_range = est_low <= actual <= est_high

            # Calculate error (midpoint vs actual)
            est_mid = (est_low + est_high) / 2
            error = actual - est_mid

            results.append(AccuracyResult(
                commit_message=commit.message[:60],
                category=commit.category,
                actual_hours=actual,
                actual_files=commit.files_changed,
                actual_churn=commit.total_churn,
                estimated_low=est_low,
                estimated_high=est_high,
                confidence=estimate.confidence,
                within_range=within_range,
                error_hours=error,
            ))
        except Exception:
            continue

    return results


def get_accuracy_summary(results: list[AccuracyResult]) -> dict:
    """Get summary statistics for accuracy results."""
    if not results:
        return {"error": "No results"}

    within_range_count = sum(1 for r in results if r.within_range)
    total = len(results)

    errors = [r.error_hours for r in results]
    avg_error = sum(errors) / len(errors)

    return {
        "total_samples": total,
        "within_range": within_range_count,
        "accuracy_pct": round(within_range_count / total * 100, 1),
        "avg_error_hours": round(avg_error, 1),
        "underestimates": sum(1 for e in errors if e > 0),
        "overestimates": sum(1 for e in errors if e < 0),
    }
