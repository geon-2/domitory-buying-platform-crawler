FROM python:3.11-slim

WORKDIR /app

# Chromium 및 필요한 system dependencies 설치
RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxrandr2 libgbm1 libasound2 \
    libxshmfence1 wget fonts-liberation libappindicator3-1 xdg-utils \
    && pip install --no-cache-dir flask gunicorn requests beautifulsoup4 playwright \
    && python -m playwright install chromium \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . .

CMD gunicorn app:app --workers 1 --bind 0.0.0.0:$PORT