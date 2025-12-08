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

# Install system dependencies for PJSIP and audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libasound2-dev \
    libopus-dev \
    libspeex-dev \
    libspeexdsp-dev \
    libsndfile1-dev \
    portaudio19-dev \
    ffmpeg \
    curl \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements and install
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

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

