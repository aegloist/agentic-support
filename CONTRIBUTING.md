# Contributing Guide

## Dependency management

`pyproject.toml` is the single source of truth for dependencies: runtime dependencies go in `[project.dependencies]` and optional groups go in `[project.optional-dependencies]` (`dev`, `rerank`, `docs`). The repo no longer maintains a separate `requirements.txt`, so the two version manifests can't drift apart.

`uv.lock` is the locked version manifest committed to the repo, used to reproduce the full dependency tree. CI runs `uv lock --check`, which fails as soon as it gets out of sync with `pyproject.toml`.

```bash
uv sync --extra dev          # Reproduce the dev environment exactly per uv.lock (recommended)
uv lock --check              # After editing pyproject, verify the lockfile is in sync

pip install -e ".[dev]"      # Development (includes pytest, ruff, mypy)
pip install -e ".[rerank]"   # Local bge recall + Cross-Encoder reranking
pip install -e ".[docs]"     # Unstructured parses PDF/Office/HTML/images
```

## Code style

The project uses Python 3.11+. Formatting, import sorting, and static checks all go through Ruff, with mypy for type checking. New modules should include a module-level docstring; public classes, functions, and async interfaces should use Google-style docstrings covering purpose, arguments, return values, and exceptions.

```bash
ruff format .
ruff check .
mypy
python -m compileall -q app eval
pytest -q
```

CI runs Ruff, mypy, and pytest on Python 3.11 and 3.12 in turn, and requires coverage of `app` / `eval` to be no lower than 70%.

Before committing, make sure you're not committing `.env` files, secrets, database files, or evaluation artifacts. Business logic should live in layered directories, pass data through schemas, and avoid touching infrastructure directly from the routing layer.
