"""
Task estimation using RAG over historical commits + LLM analysis.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from src.utils.llm_client import get_llm_client
from src.analyzers.commit_analyzer import CommitData


@dataclass
class TaskEstimate:
    """Estimation result for a task."""

    task_description: str

    # Time estimates
    estimated_hours_low: float
    estimated_hours_high: float
    confidence: float  # 0-1

    # Complexity assessment
    complexity_score: float  # 1-10
    complexity_reasoning: str

    # Risk assessment
    risk_score: float  # 0-100
    risk_factors: list[str]

    # Similar past work
    similar_commits: list[dict]

    # Recommendations
    recommendations: list[str]

    def to_dict(self) -> dict:
        return {
            "task_description": self.task_description,
            "estimated_hours": {
                "low": self.estimated_hours_low,
                "high": self.estimated_hours_high,
                "confidence": self.confidence,
            },
            "complexity": {
                "score": self.complexity_score,
                "reasoning": self.complexity_reasoning,
            },
            "risk": {
                "score": self.risk_score,
                "factors": self.risk_factors,
            },
            "similar_commits": self.similar_commits,
            "recommendations": self.recommendations,
        }


class TaskEstimator:
    """Estimates task difficulty using RAG + LLM."""

    def __init__(self, chroma_path: str = "./data/chroma"):
        self.chroma_path = Path(chroma_path)
        self.llm = None  # Lazy load

        # Initialize ChromaDB with default embedding function
        self.chroma_client = chromadb.PersistentClient(path=str(self.chroma_path))

        # Use default embedding function (all-MiniLM-L6-v2)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        self.collection = self.chroma_client.get_or_create_collection(
            name="commits",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def _get_llm(self):
        """Lazy load LLM client."""
        if self.llm is None:
            self.llm = get_llm_client()
        return self.llm

    def index_commits(self, commits: list[CommitData], repo_name: str) -> int:
        """Index commits for RAG retrieval."""
        documents = []
        metadatas = []
        ids = []

        for commit in commits:
            # Create rich document for embedding
            doc = f"""
            Commit: {commit.message}
            Category: {commit.category}
            Files changed: {commit.files_changed}
            Lines added: {commit.insertions}
            Lines deleted: {commit.deletions}
            Files: {', '.join(commit.file_list[:10])}
            """

            documents.append(doc.strip())
            metadatas.append(
                {
                    "sha": commit.sha,
                    "message": commit.message,
                    "repo": repo_name,
                    "category": commit.category,
                    "files_changed": commit.files_changed,
                    "insertions": commit.insertions,
                    "deletions": commit.deletions,
                    "total_churn": commit.total_churn,
                    "time_since_last": commit.time_since_last_commit_hours or 0,
                    "timestamp": commit.timestamp.isoformat(),
                }
            )
            ids.append(f"{repo_name}_{commit.sha}")

        if documents:
            self.collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

        return len(documents)

    def find_similar_commits(self, task_description: str, n_results: int = 5) -> list[dict]:
        """Find similar past commits using semantic search."""
        results = self.collection.query(
            query_texts=[task_description],
            n_results=n_results,
        )

        similar = []
        if results["metadatas"] and results["metadatas"][0]:
            for i, meta in enumerate(results["metadatas"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                similar.append(
                    {
                        "sha": meta["sha"],
                        "message": meta["message"],
                        "repo": meta["repo"],
                        "category": meta["category"],
                        "files_changed": meta["files_changed"],
                        "total_churn": meta["total_churn"],
                        "time_hours": meta["time_since_last"],
                        "similarity": 1 - distance,  # Convert distance to similarity
                    }
                )

        return similar

    def _estimate_with_llm(
        self, task_description: str, similar_commits: list[dict], codebase_context: str = ""
    ) -> dict:
        """Use LLM to estimate task complexity and time."""

        similar_context = "\n".join(
            [
                f"- {c['message']} ({c['files_changed']} files, {c['total_churn']} lines, ~{c['time_hours']:.1f}h)"
                for c in similar_commits
            ]
        )

        prompt = f"""You are an expert software engineering estimator. Analyze this task and provide estimates.

## Task Description
{task_description}

## Similar Past Work (from this codebase)
{similar_context if similar_context else "No similar past work found."}

## Codebase Context
{codebase_context if codebase_context else "Full-stack TypeScript application (NestJS backend, Cocos Creator frontend, Solidity smart contracts)"}

## Your Analysis

Provide your analysis in the following JSON format:
{{
    "estimated_hours_low": <number>,
    "estimated_hours_high": <number>,
    "confidence": <0.0-1.0>,
    "complexity_score": <1-10>,
    "complexity_reasoning": "<brief explanation>",
    "risk_score": <0-100>,
    "risk_factors": ["<factor1>", "<factor2>", ...],
    "recommendations": ["<recommendation1>", "<recommendation2>", ...]
}}

Consider:
- Time includes coding, testing, and review
- Complexity considers cognitive load, not just lines of code
- Risk factors include: touching critical paths, lack of tests, new patterns, external dependencies
- Be realistic based on the similar past work shown

Return ONLY the JSON, no other text."""

        llm = self._get_llm()
        content = llm.complete(prompt, max_tokens=1024, temperature=0.3)

        try:
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            # Fallback estimates
            return {
                "estimated_hours_low": 2,
                "estimated_hours_high": 8,
                "confidence": 0.3,
                "complexity_score": 5,
                "complexity_reasoning": "Unable to parse LLM response",
                "risk_score": 50,
                "risk_factors": ["Estimation uncertainty"],
                "recommendations": ["Break down task into smaller pieces"],
            }

    def estimate_task(
        self, task_description: str, codebase_context: str = ""
    ) -> TaskEstimate:
        """Estimate a task's difficulty, time, and risk."""

        # Find similar past work
        similar_commits = self.find_similar_commits(task_description, n_results=5)

        # Get LLM estimate
        llm_result = self._estimate_with_llm(
            task_description, similar_commits, codebase_context
        )

        return TaskEstimate(
            task_description=task_description,
            estimated_hours_low=llm_result["estimated_hours_low"],
            estimated_hours_high=llm_result["estimated_hours_high"],
            confidence=llm_result["confidence"],
            complexity_score=llm_result["complexity_score"],
            complexity_reasoning=llm_result["complexity_reasoning"],
            risk_score=llm_result["risk_score"],
            risk_factors=llm_result["risk_factors"],
            similar_commits=similar_commits,
            recommendations=llm_result["recommendations"],
        )
