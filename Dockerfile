# run:
# docker builder prune
# docker build --no-cache -t epubarena3:latest .
# save: 
# docker save epubarena3:latest > epubarena3.tar
# copy: Datei mit z.B. filezilla auf den VPS bringen
# load/import image:
# docker load -i epubarena3.tar
# data Ordner erstellen und Rechte vergeben
# docker chmod 664 data
# Container erstellen und starten:
# - in Ordner mit yaml-Datei wechseln, evtl. imagenamen anpassen
# docker compose up -d


# --- Builder stage ---
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Build dependencies for wheels (kept only in builder)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY dockerrequirements.txt .

# Install into an isolated prefix to copy only what we need
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r dockerrequirements.txt
    #pip install --no-cache-dir --prefix=/install ebooklib beautifulsoup4 requests keyboard markdown markdownify openai uvicorn fastapi Jinja2 python-multipart


# --- Runtime stage ---
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy runtime deps from builder
COPY --from=builder /install /usr/local

# Copy app code
COPY . .

# Port deklarieren
EXPOSE 8080

CMD ["python", "gui3.py"]
