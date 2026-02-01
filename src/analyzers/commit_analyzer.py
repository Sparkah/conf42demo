"""
Analyzes git commit history to extract features for ML/estimation.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from git import Repo
from git.objects.commit import Commit


@dataclass
class CommitData:
    """Extracted features from a single commit."""

    sha: str
    message: str
    author: str
    timestamp: datetime

    # File metrics
    files_changed: int
    insertions: int
    deletions: int
    file_list: list[str] = field(default_factory=list)

    # Derived metrics
    total_churn: int = 0
    time_since_last_commit_hours: Optional[float] = None

    # Categories (derived from message/files)
    category: str = "unknown"

    # Complexity score (filled by code analyzer)
    complexity_score: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "CommitData":
        d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**d)


class CommitAnalyzer:
    """Extracts commit data from a git repository."""

    CATEGORY_KEYWORDS = {
        "auth": ["auth", "login", "jwt", "farcaster", "session", "token"],
        "nft": ["nft", "mint", "token", "contract", "blockchain", "eth", "wallet"],
        "api": ["api", "endpoint", "route", "controller", "service"],
        "ui": ["ui", "frontend", "visual", "color", "style", "css", "panel"],
        "infra": ["infra", "deploy", "docker", "ci", "cd", "cors", "config", "env"],
        "fix": ["fix", "bug", "patch", "hotfix", "issue"],
        "refactor": ["refactor", "cleanup", "reorganize", "restructure"],
        "test": ["test", "spec", "jest", "pytest", "coverage"],
        "docs": ["doc", "readme", "comment", "license"],
        "feature": ["add", "implement", "create", "new", "feature"],
    }

    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path)
        self.repo = Repo(repo_path)

    def _categorize_commit(self, message: str, files: list[str]) -> str:
        """Categorize commit based on message and files."""
        msg_lower = message.lower()

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in msg_lower for kw in keywords):
                return category

        # Check file paths
        file_str = " ".join(files).lower()
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in file_str for kw in keywords):
                return category

        return "other"

    def _extract_commit_stats(self, commit: Commit) -> tuple[int, int, int, list[str]]:
        """Extract file change statistics from a commit."""
        try:
            if commit.parents:
                diff = commit.parents[0].diff(commit)
            else:
                # Initial commit
                diff = commit.diff(None)

            files = []
            insertions = 0
            deletions = 0

            for d in diff:
                if d.a_path:
                    files.append(d.a_path)
                elif d.b_path:
                    files.append(d.b_path)

            # Get stats from commit
            stats = commit.stats.total
            insertions = stats.get("insertions", 0)
            deletions = stats.get("deletions", 0)

            return len(files), insertions, deletions, files

        except Exception:
            return 0, 0, 0, []

    def analyze_commits(self, max_commits: int = 500) -> list[CommitData]:
        """Analyze all commits in the repository."""
        commits_data = []
        prev_timestamp = None

        for commit in list(self.repo.iter_commits("HEAD", max_count=max_commits)):
            files_changed, insertions, deletions, file_list = self._extract_commit_stats(commit)

            timestamp = datetime.fromtimestamp(commit.committed_date)

            # Calculate time since last commit
            time_since_last = None
            if prev_timestamp:
                delta = prev_timestamp - timestamp  # prev is more recent
                time_since_last = delta.total_seconds() / 3600  # hours

            data = CommitData(
                sha=commit.hexsha[:7],
                message=commit.message.strip().split("\n")[0],  # First line only
                author=commit.author.name,
                timestamp=timestamp,
                files_changed=files_changed,
                insertions=insertions,
                deletions=deletions,
                file_list=file_list,
                total_churn=insertions + deletions,
                time_since_last_commit_hours=time_since_last,
                category=self._categorize_commit(commit.message, file_list),
            )

            commits_data.append(data)
            prev_timestamp = timestamp

        # Reverse to chronological order
        return list(reversed(commits_data))

    def save_to_json(self, commits: list[CommitData], output_path: Path) -> None:
        """Save commit data to JSON file."""
        data = [c.to_dict() for c in commits]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_from_json(self, input_path: Path) -> list[CommitData]:
        """Load commit data from JSON file."""
        with open(input_path) as f:
            data = json.load(f)
        return [CommitData.from_dict(d) for d in data]


def analyze_multiple_repos(repo_paths: list[Path], output_dir: Path) -> dict[str, list[CommitData]]:
    """Analyze multiple repositories and save results."""
    all_commits = {}

    for repo_path in repo_paths:
        if not (repo_path / ".git").exists():
            continue

        analyzer = CommitAnalyzer(repo_path)
        commits = analyzer.analyze_commits()

        repo_name = repo_path.name
        all_commits[repo_name] = commits

        # Save individual repo data
        analyzer.save_to_json(commits, output_dir / f"{repo_name}_commits.json")

    return all_commits
