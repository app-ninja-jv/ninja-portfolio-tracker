# syntax=docker/dockerfile:1
#
# Pins the interpreter, which is the whole point — the package needs 3.10+
# (zip(strict=True), PEP 604 unions) and system Pythons are often older.
#
#   docker compose build
#   docker compose run --rm tracker doctor
#
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependency layer first, by name, so editing source doesn't re-download wheels.
# Kept in sync with the optional-dependencies in pyproject.toml.
# pandas/numpy ship manylinux wheels for 3.12 — no build toolchain needed.
RUN python -m pip install --upgrade pip && \
    pip install \
      "yfinance>=0.2.40" \
      "pandas>=2.0" \
      "pytest>=7.4" \
      "ruff>=0.4"

# Source, installed editable so a bind mount picks up edits without a rebuild.
# --no-deps because everything is already present in the layer above.
COPY . .
RUN pip install -e . --no-deps

# Non-root. UID 1000 matches the typical host user so bind-mounted files
# stay writable from both sides.
RUN useradd -m -u 1000 tracker && \
    mkdir -p /app/data /app/build && \
    chown -R tracker:tracker /app
USER tracker

# Sanity check at build time — fails the image rather than the first command
RUN python -c "import tracker, sys; \
print(f'ninja-portfolio-tracker {tracker.__version__} on Python {sys.version.split()[0]}')"

ENTRYPOINT ["tracker"]
CMD ["--help"]
