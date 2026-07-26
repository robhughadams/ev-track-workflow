FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --prerelease=allow --no-dev --frozen

COPY . .

CMD ["uv", "run", "run_workflow.py"]
