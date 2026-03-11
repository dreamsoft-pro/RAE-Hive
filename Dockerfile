# Dockerfile for Base Agent
# Lightweight Python image with RAE SDK pre-installed

FROM python:3.10-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install basic tools
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    ca-certificates \
    gnupg \
    lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Install agent base dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy base agent code
COPY base_agent /app/base_agent
COPY config /app/config
COPY hive_engine.py /app/hive_engine.py
COPY planner.py /app/planner.py

# Create work directory
RUN mkdir -p /app/work_dir

# Create a non-root user
RUN useradd -m -u 1000 hiveuser && \
    chown -R hiveuser:hiveuser /app
USER hiveuser

# Default command (overridden by specific agents)
CMD ["python", "-m", "base_agent.main"]
