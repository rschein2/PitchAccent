FROM python:3.11-slim

# Install system deps for fugashi/MeCab
RUN apt-get update && apt-get install -y \
    build-essential \
    swig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Download UniDic dictionary
RUN python -m unidic download

# Copy app code
COPY pitch_accent/ pitch_accent/
COPY api.py .

# Railway provides PORT env var
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}
