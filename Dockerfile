# ---------- build layer ----------
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && \
    apt-get install -y curl gnupg libpq-dev && \
    rm -rf /var/lib/apt/lists/*

RUN curl -Ls https://astral.sh/uv/install.sh | bash
ENV PATH="/root/.local/bin:${PATH}"
COPY pyproject.toml uv.lock* ./
RUN uv pip install --system .
RUN playwright install chromium

# ---------- runtime layer ----------
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Install runtime system dependencies for Playwright (Chromium)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL client library (for asyncpg) \
    libpq5 \
    # System utilities
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    wget \
    xdg-utils \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Copy Python libraries and executables from builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the Playwright browser cache from builder
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
