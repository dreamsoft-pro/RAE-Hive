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
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy SDK code
COPY sdk/python/rae_memory_sdk /sdk/rae_memory_sdk
RUN pip install --no-cache-dir -e /sdk/rae_memory_sdk

# Install agent base dependencies
COPY agent_hive/base_agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy base agent code
COPY agent_hive/base_agent /app/base_agent
COPY agent_hive/config /app/config

# Create a non-root user
RUN useradd -m -u 1000 hiveuser && \
    chown -R hiveuser:hiveuser /app
USER hiveuser

# Default command (overridden by specific agents)
CMD ["python", "-m", "base_agent.main"]
