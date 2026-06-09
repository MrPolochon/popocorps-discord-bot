# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml uv.lock ./

# Install UV package manager for faster dependency installation
RUN pip install uv

# Install Python dependencies
RUN uv sync --frozen

# Make the uv-created virtual environment the default Python (so `python` sees the deps)
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p raid_data guild_settings temp_images

# Expose port for web dashboard
EXPOSE 5000

# Start the application
CMD ["python", "run.py"]