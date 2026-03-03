# Basis-Image
FROM python:3.12-slim

# Umgebungsvariablen
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System-Abhängigkeiten (falls nötig)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
	pip install --no-cache-dir ebooklib beautifulsoup4 requests markdown markdownify openai flask && \
	pip freeze > dockerrequirements.txt
    #pip install --no-cache-dir -r requirements.txt
	

# Restlichen Code kopieren
COPY . .

# Neuen User erstellen
#RUN useradd -m appuser

# Berechtigungen für App-Ordner setzen
#RUN chown -R appuser:appuser /app

# Als appuser ausführen
#USER appuser

# Port deklarieren
EXPOSE 8080

CMD ["python", "gui3.py"]
