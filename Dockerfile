FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# Install system dependencies needed for Pillow and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files from public directory
COPY public/ .

# Collect static files into staticfiles directory
RUN python manage.py collectstatic --noinput

# Expose default Cloud Run port
EXPOSE 8080

# Ensure entrypoint has execute permissions
RUN chmod +x entrypoint.sh || true

CMD ["/bin/sh", "entrypoint.sh"]
