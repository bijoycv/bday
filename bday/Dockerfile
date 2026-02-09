FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    gcc \
    libpq-dev \
    pkg-config \
    python3-dev \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Install dependencies via uv
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy project
COPY . .

# Copy entrypoint
COPY ./entrypoint.sh /
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
