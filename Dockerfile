# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

# No bytecode files, unbuffered logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install the package first (its own layer) so source edits do not re-resolve deps.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Run as a non-root user.
RUN useradd --system --uid 10001 --no-create-home clausewise
USER 10001

ENTRYPOINT ["clausewise"]
CMD ["bench", "--no-write"]
