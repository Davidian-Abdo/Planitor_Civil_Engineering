# --------------------------
# Stage 1: Builder
# --------------------------
FROM python:3.9-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies to local user path
RUN pip install --no-cache-dir --user -r requirements.txt


# --------------------------
# Stage 2: Production
# Multi-stage build

# ---- Build stage ----
FROM python:3.9-slim as builder
WORKDIR /app

# System dependencies for building packages
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Production stage ----
FROM python:3.9-slim as production
WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app

# Copy dependencies from builder
COPY --from=builder /root/.local /home/app/.local

# Copy application code
COPY --chown=app:app . .

# Create necessary directories
RUN mkdir -p logs outputs backups templates && chown -R app:app logs outputs backups templates

# Switch to non-root user
USER app

# Set environment for Python packages
ENV PATH=/home/app/.local/bin:$PATH
ENV PYTHONPATH=/app

# Expose Streamlit port
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/healthz || exit 1

# Start Streamlit
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]