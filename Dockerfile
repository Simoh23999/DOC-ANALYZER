FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5000 \
    DATABASE=/data/documents.db \
    UPLOAD_FOLDER=/data/uploads

# System deps: Tesseract OCR (+ French data) and runtime libs for PyMuPDF/Pillow.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-fra \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && tesseract --version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py analyzer.py ./
COPY templates/ ./templates/

# Writable data dir for sqlite db + uploads
RUN mkdir -p /data/uploads && useradd -m appuser && chown -R appuser:appuser /app /data
USER appuser

VOLUME ["/data"]
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT','5000')}/login\")" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
