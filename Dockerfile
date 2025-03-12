ARG PYTHON_VERSION=3.13.2
FROM python:${PYTHON_VERSION}-slim

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for psycopg and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Copy the requirements first to leverage Docker cache
COPY pyproject.toml version.txt README.md ./
COPY yt_navigator ./yt_navigator
COPY app ./app

# Install dependencies with cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --cache-dir=/root/.cache/pip --no-cache-dir -e .

# Copy the rest of the code
COPY . .

# Set up all directories and permissions before switching to appuser
RUN mkdir -p /app/logs && \
    touch /app/logs/$(date +%Y-%m-%d).jsonl && \
    mkdir -p /app/.cache/huggingface/transformers && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod 777 /app/logs && \
    chmod 666 /app/logs/$(date +%Y-%m-%d).jsonl && \
    chmod +x /app/docker-entrypoint.sh

# Set environment variable for Hugging Face cache
ENV HF_HOME=/app/.cache/huggingface

# Switch to the non-privileged user to run the application.
USER appuser

# Expose the port that the application listens on.
EXPOSE 8000

# Set the entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Run the application.
CMD ["gunicorn", "yt_navigator.wsgi", "--bind=0.0.0.0:8000", "--workers=4", "--threads=4", "--timeout=120"]
