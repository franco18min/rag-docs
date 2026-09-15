FROM python:3.11-slim

WORKDIR /app

# System deps for PDF parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .
RUN chmod +x /app/scripts/start_space.sh

# Local compose keeps API on :8000. Hugging Face Spaces sets SPACE_ID → start script
# (API :8000 + ingest sample + Streamlit :7860).
EXPOSE 8000 7860

CMD ["sh", "-c", "if [ -n \"${SPACE_ID:-}\" ]; then exec /app/scripts/start_space.sh; else exec uvicorn app.main:app --host 0.0.0.0 --port 8000; fi"]
