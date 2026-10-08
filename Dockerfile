FROM python:3.11-slim

# Install ffmpeg, nodejs, curl, ca-certificates, unzip
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    curl \
    ca-certificates \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Ensure node symlink exists
RUN if [ -f /usr/bin/nodejs ] && [ ! -f /usr/bin/node ]; then ln -s /usr/bin/nodejs /usr/bin/node; fi

# Install Deno (official, ultra-fast JavaScript runtime for yt-dlp)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create downloads directory
RUN mkdir -p downloads

ENV PORT=8500
EXPOSE 8500

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8500}"]
