FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Install system dependencies (including build tools for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools
    gcc \
    python3-dev \
    libpq-dev \
    # For uv
    curl \
    gnupg \
    # PostgreSQL client runtime library (for asyncpg)
    libpq5 \
    # System utilities for Playwright
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

# Install uv, Python dependencies, and Playwright browsers
COPY pyproject.toml uv.lock* ./
RUN curl -Ls https://astral.sh/uv/install.sh | bash && \
    export PATH="/root/.local/bin:${PATH}" && \
    uv pip install --system . && \
    playwright install chromium && \
    echo "Installed pip packages:" && \
    uv pip list
    # Note: The Playwright browser cache will now be in /root/.cache/ms-playwright
    # within this single layer.

COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
