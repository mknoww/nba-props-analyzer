# Dockerfile
# Container image for the NBA props analyzer API

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system-level dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and assets into the image
COPY src/ ./src
COPY assets/ ./assets
COPY README.md ./README.md

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV ASSETS_DIR=/app/assets
ENV PROPS_FILE=sample_props.csv
ENV PORT=8080

# If you later connect to vLLM, set these via docker run or .env:
# ENV VLLM_BASE_URL=http://llm:8000
# ENV VLLM_MODEL=mistral-7b-instruct

# Expose the Flask port
EXPOSE 8080

# Run the Flask app
CMD ["python", "src/app.py"]

