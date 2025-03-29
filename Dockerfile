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

# Command to run the application with gevent worker and proper timeouts
CMD ["gunicorn", "--worker-class", "gevent", "--workers", "1", "--bind", "0.0.0.0:8080", "--timeout", "120", "--keep-alive", "5", "11labs_v3:app"] 