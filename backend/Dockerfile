# Playwright's official image ships Chromium + all system libs preinstalled,
# matching the pinned playwright==1.44.0 in requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Install Python deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && python -m playwright install chromium

# Copy the application code.
COPY . .

ENV CHROMIUM_LOW_MEMORY=1 ANALYZE_CONCURRENCY=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
