FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies, MySQL, Node.js & Python
RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    mysql-server \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements & install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip3 install --no-cache-dir -r /app/backend/requirements.txt

# Copy frontend dependencies & install
COPY frontend/package*.json /app/frontend/
RUN cd /app/frontend && npm install

# Copy application files
COPY . /app

# Build Next.js application
RUN cd /app/frontend && npm run build

# Make start script executable
RUN chmod +x /app/start.sh

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://127.0.0.1:8000/api/v1/health || exit 1

CMD ["/app/start.sh"]
