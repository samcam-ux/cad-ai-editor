# CAD AI Editor - Production Docker image
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# System deps: Python, Qt (for ODA), xvfb (headless display)
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    xvfb \
    libopengl0 libgl1 \
    libxcb-cursor0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY backend/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt \
    && pip3 install --no-cache-dir gunicorn

# App code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# ODA File Converter - see setup-oda.sh
# 1. Download .deb from https://www.opendesign.com/guestfiles/oda_file_converter
# 2. Save as oda-converter.deb in project root
# 3. Uncomment the lines below:
# COPY oda-converter.deb /tmp/oda.deb
# RUN dpkg -i /tmp/oda.deb || apt-get install -f -y && rm /tmp/oda.deb
# ENV PATH="/usr/bin:$PATH"

# Create dirs
RUN mkdir -p uploads outputs && chmod 777 uploads outputs

# Env defaults
ENV APP_URL=""
ENV STRIPE_SECRET_KEY=""
ENV STRIPE_WEBHOOK_SECRET=""

EXPOSE 8099

# Run with gunicorn (production) 
CMD ["gunicorn", "backend.main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8099", \
     "--timeout", "300"]
