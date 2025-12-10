# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend with PJSIP
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install runtime dependencies and build dependencies separately
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build dependencies (will be removed later)
    build-essential \
    pkg-config \
    python3-dev \
    # Runtime dependencies (will be kept)
    libssl3 \
    libasound2 \
    libopus0 \
    libspeex1 \
    libspeexdsp1 \
    libsndfile1 \
    libportaudio2 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    # Remove build dependencies after pip install to reduce image size
    && apt-get purge -y --auto-remove \
    build-essential \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create data directory for persistent storage
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=backend.app.main

# Expose ports
EXPOSE 3002 5001 5060/udp 5060/tcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5001/api/health || exit 1

# Run the application
CMD ["python", "-m", "backend.app.main"]

