# Backend Dockerfile for Flask API
# Multi-stage build for smaller production image

# ============================================
# Stage 1: Base image with dependencies
# ============================================
FROM python:3.12-slim as base

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: Development image
# ============================================
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-cov

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Run Flask development server
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]

# ============================================
# Stage 3: Production image
# ============================================
FROM base as production

# Create non-root user for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Run with Gunicorn (production WSGI server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "wsgi:app"]
