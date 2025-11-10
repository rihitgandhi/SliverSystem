FROM python:3.11-slim

# Use a non-root user in production if desired (left as root for simplicity)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps (if needed) and pip packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy app sources
COPY . /app

# Expose the port the app will run on
EXPOSE 8000

# Use Gunicorn for production
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8000", "app:app"]
