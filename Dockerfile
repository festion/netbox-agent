FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y gcc python3-dev && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 netboxagent
WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ src/
COPY config/ config/
COPY scripts/ scripts/

# Set permissions
RUN mkdir -p logs cache && chown -R netboxagent:netboxagent /app
USER netboxagent

# Set Python path
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python scripts/health_check.py || exit 1

CMD ["python", "src/netbox_agent.py"]