# syntax=docker/dockerfile:1
#
# There was no image before. This is a command-line tool: the entrypoint is the
# CLI, the default command prints its help, and reports land in /app/reports
# (mount a volume). git is installed because GitPython shells out to it to
# clone the repository under review.

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app . .
RUN mkdir -p /app/reports && chown app:app /app/reports
VOLUME ["/app/reports"]

USER app

# GOOGLE_API_KEY is read at the first model call, not at start: --help and the
# static-analysis stages run without it.
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
