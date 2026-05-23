FROM python:3.13-slim

WORKDIR /app

# System deps + Node.js 24 LTS (required by Reflex to build the frontend)
RUN apt-get update && apt-get install -y gcc curl unzip && \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY rxconfig.py .
COPY job_finder/ job_finder/
COPY services/ services/
COPY database/ database/
COPY core/ core/
COPY templates/ templates/
COPY mcp_server.py .

# Pre-install Next.js dependencies so the first startup doesn't need to fetch them
RUN reflex init --loglevel warning

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 3000
