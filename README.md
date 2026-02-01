# AI-Driven Engineering Quality

> Predict delivery time and improve code reliability using ML + LLM

**Conf42 Demo** - How we use machine learning to estimate task difficulty and review code automatically.

## Features

- **Task Estimation**: Describe a task → get time estimate + complexity score
- **Code Review**: Analyze files for risk, quality issues, and security concerns
- **RAG over Git History**: Find similar past work to inform estimates
- **GitHub Integration**: Auto-review PRs via webhooks

## Quick Start

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Set API key (OpenRouter or Anthropic)
export OPENROUTER_API_KEY=your-key

# Index your repos
python -m src.cli index /path/to/repo1 /path/to/repo2

# Estimate a task
python -m src.cli estimate "Add user authentication with OAuth"

# Review code
python -m src.cli review /path/to/file.ts
```

## Commands

| Command | Description |
|---------|-------------|
| `analyze <repo>` | Analyze commit history |
| `index <repos>` | Index repos for RAG |
| `estimate <task>` | Estimate task difficulty |
| `review <file>` | Review code quality |
| `review -d <repo>` | Review git diff |
| `metrics <repo>` | Show code metrics |
| `serve` | Start webhook server |
| `present` | Run presentation demo |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  1. FEATURE EXTRACTION                                      │
│     ├── Git history: commits, churn, file ownership         │
│     ├── Static analysis: complexity, LOC, dependencies      │
│     └── Embeddings: commit messages → vectors               │
│                                                             │
│  2. RAG RETRIEVAL                                           │
│     └── Find similar past work via semantic search          │
│                                                             │
│  3. LLM ANALYSIS                                            │
│     ├── Task complexity reasoning                           │
│     ├── Risk factor identification                          │
│     └── Code smell detection                                │
│                                                             │
│  4. OUTPUT                                                  │
│     ├── Time estimate with confidence                       │
│     ├── Risk score (0-100)                                  │
│     └── Actionable recommendations                          │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Python 3.11+**
- **FastAPI** - Webhook server
- **ChromaDB** - Vector store for RAG
- **Claude API** (via OpenRouter) - LLM analysis
- **Rich** - Terminal UI

## Presentation

Run the interactive demo:
```bash
python scripts/presentation_demo.py
```

## License

MIT
