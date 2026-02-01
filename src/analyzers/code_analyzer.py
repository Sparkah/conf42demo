"""
Static code analysis for complexity metrics.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CodeMetrics:
    """Code complexity metrics for a file or codebase."""

    file_path: str
    language: str

    # Complexity metrics
    cyclomatic_complexity: float = 0.0
    lines_of_code: int = 0
    comment_ratio: float = 0.0

    # Risk indicators
    long_functions: int = 0
    deep_nesting: int = 0
    large_files: int = 0

    # Aggregated risk score (0-100)
    risk_score: float = 0.0


class CodeAnalyzer:
    """Analyzes code for complexity and risk metrics."""

    # Thresholds for risk assessment
    COMPLEXITY_THRESHOLD = 10  # Cyclomatic complexity
    LONG_FUNCTION_LINES = 50
    LARGE_FILE_LINES = 500
    DEEP_NESTING_LEVEL = 4

    SUPPORTED_EXTENSIONS = {
        ".py": "python",
        ".ts": "typescript",
        ".js": "javascript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".sol": "solidity",
    }

    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path)

    def _detect_language(self, file_path: Path) -> str:
        """Detect language from file extension."""
        return self.SUPPORTED_EXTENSIONS.get(file_path.suffix.lower(), "unknown")

    def _analyze_python_file(self, file_path: Path) -> CodeMetrics:
        """Analyze Python file using radon."""
        try:
            # Get cyclomatic complexity
            result = subprocess.run(
                ["radon", "cc", "-a", "-j", str(file_path)],
                capture_output=True,
                text=True,
            )

            # Get raw metrics
            raw_result = subprocess.run(
                ["radon", "raw", "-j", str(file_path)],
                capture_output=True,
                text=True,
            )

            # Parse results
            avg_complexity = 0.0
            loc = 0

            if result.returncode == 0:
                import json

                try:
                    data = json.loads(result.stdout)
                    if file_path.name in data:
                        blocks = data[file_path.name]
                        if blocks:
                            complexities = [b.get("complexity", 0) for b in blocks]
                            avg_complexity = sum(complexities) / len(complexities)
                except (json.JSONDecodeError, KeyError):
                    pass

            if raw_result.returncode == 0:
                import json

                try:
                    data = json.loads(raw_result.stdout)
                    if str(file_path) in data:
                        loc = data[str(file_path)].get("loc", 0)
                except (json.JSONDecodeError, KeyError):
                    pass

            return CodeMetrics(
                file_path=str(file_path),
                language="python",
                cyclomatic_complexity=avg_complexity,
                lines_of_code=loc,
            )

        except Exception:
            return CodeMetrics(file_path=str(file_path), language="python")

    def _analyze_typescript_file(self, file_path: Path) -> CodeMetrics:
        """Analyze TypeScript/JavaScript file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            loc = len([l for l in lines if l.strip() and not l.strip().startswith("//")])

            # Simple complexity heuristics
            complexity_indicators = [
                content.count(" if "),
                content.count(" if("),
                content.count(" else "),
                content.count(" for "),
                content.count(" for("),
                content.count(" while "),
                content.count(" while("),
                content.count(" switch "),
                content.count(" case "),
                content.count(" catch "),
                content.count(" ? "),  # ternary
                content.count(" && "),
                content.count(" || "),
            ]

            estimated_complexity = sum(complexity_indicators) / max(1, loc / 50)

            # Count long functions (heuristic: functions with many lines between braces)
            long_functions = 0
            comment_lines = len([l for l in lines if l.strip().startswith("//")])

            return CodeMetrics(
                file_path=str(file_path),
                language=self._detect_language(file_path),
                cyclomatic_complexity=estimated_complexity,
                lines_of_code=loc,
                comment_ratio=comment_lines / max(1, len(lines)),
                long_functions=long_functions,
            )

        except Exception:
            return CodeMetrics(
                file_path=str(file_path), language=self._detect_language(file_path)
            )

    def analyze_file(self, file_path: Path) -> CodeMetrics:
        """Analyze a single file for complexity metrics."""
        language = self._detect_language(file_path)

        if language == "python":
            metrics = self._analyze_python_file(file_path)
        elif language in ("typescript", "javascript"):
            metrics = self._analyze_typescript_file(file_path)
        else:
            # Basic analysis for other languages
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                loc = len([l for l in content.split("\n") if l.strip()])
                metrics = CodeMetrics(
                    file_path=str(file_path), language=language, lines_of_code=loc
                )
            except Exception:
                metrics = CodeMetrics(file_path=str(file_path), language=language)

        # Calculate risk score
        metrics.risk_score = self._calculate_risk_score(metrics)
        return metrics

    def _calculate_risk_score(self, metrics: CodeMetrics) -> float:
        """Calculate a 0-100 risk score based on metrics."""
        score = 0.0

        # Complexity factor (0-40 points)
        if metrics.cyclomatic_complexity > 0:
            complexity_factor = min(40, metrics.cyclomatic_complexity * 4)
            score += complexity_factor

        # Size factor (0-30 points)
        if metrics.lines_of_code > self.LARGE_FILE_LINES:
            score += 30
        elif metrics.lines_of_code > 200:
            score += 15

        # Long functions factor (0-20 points)
        score += min(20, metrics.long_functions * 5)

        # Low comment ratio penalty (0-10 points)
        if metrics.comment_ratio < 0.05 and metrics.lines_of_code > 100:
            score += 10

        return min(100, score)

    def analyze_directory(self, dir_path: Path = None) -> list[CodeMetrics]:
        """Analyze all supported files in a directory."""
        if dir_path is None:
            dir_path = self.repo_path

        metrics = []
        for ext in self.SUPPORTED_EXTENSIONS:
            for file_path in dir_path.rglob(f"*{ext}"):
                # Skip node_modules, dist, etc.
                if any(
                    skip in str(file_path)
                    for skip in ["node_modules", "dist", ".git", "__pycache__", "venv"]
                ):
                    continue
                metrics.append(self.analyze_file(file_path))

        return metrics

    def get_repo_summary(self) -> dict:
        """Get a summary of the entire repository's code quality."""
        all_metrics = self.analyze_directory()

        if not all_metrics:
            return {"total_files": 0, "avg_risk_score": 0}

        return {
            "total_files": len(all_metrics),
            "total_loc": sum(m.lines_of_code for m in all_metrics),
            "avg_complexity": sum(m.cyclomatic_complexity for m in all_metrics)
            / len(all_metrics),
            "avg_risk_score": sum(m.risk_score for m in all_metrics) / len(all_metrics),
            "high_risk_files": [m.file_path for m in all_metrics if m.risk_score > 50],
            "languages": list(set(m.language for m in all_metrics)),
        }
