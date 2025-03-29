FROM python:3.12-slim

# Install system dependencies including build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    python3-dev \
    portaudio19-dev \
    python3-pyaudio \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gevent

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Set environment variables for better memory management
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PYTHONASYNCIODEBUG=1
ENV PYTHONGC=1
ENV PYTHONMALLOC=malloc
ENV MALLOC_TRIM_THRESHOLD_=131072
ENV MALLOC_MMAP_THRESHOLD_=131072

# Command to run the application with optimized settings
CMD ["gunicorn", "--worker-class", "gevent", "--workers", "1", "--bind", "0.0.0.0:8080", "--timeout", "300", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "50", "--log-level", "debug", "--worker-tmp-dir", "/dev/shm", "--worker-connections", "1000", "11labs_v3:app"] 