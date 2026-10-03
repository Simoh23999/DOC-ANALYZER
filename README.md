# DOC-ANALYZER - Analyse de documents universitaires (Flask + OCR + IA)

Application Flask de dépôt, extraction OCR et question-réponse sur documents PDF/DOC/DOCX.

## 1. Prérequis

- Docker (ou Podman) pour la méthode recommandée, **ou** Python 3.11 + Tesseract en local.
- Une clé API Groq : https://console.groq.com/

## 2. Configuration (`.env`)

```powershell
copy .env.example .env
```

```
SECRET_KEY=...        # obligatoire en prod : python -c "import secrets; print(secrets.token_hex(32))"
GROQ_API_KEY=...     
PORT=5000
FLASK_DEBUG=0         # 1 en dev local, 0 en prod/Docker
DATABASE=documents.db # /data/documents.db sous Docker
UPLOAD_FOLDER=uploads # /data/uploads sous Docker
```

## 3. Lancement avec Docker (recommandé)

L'image contient déjà Python, les dépendances, Tesseract + données français (`tesseract-ocr`, `tesseract-ocr-fra`) et Gunicorn. Aucune installation locale de Tesseract n'est nécessaire.

### 3.1 Depuis l'image publiée (GHCR)

```powershell
$ docker pull ghcr.io/simoh23999/doc-analyzer:latest
$ docker run -p 5000:5000 -e SECRET_KEY=votre-secret -e GROQ_API_KEY=votre-cle -v doc-data:/data ghcr.io/simoh23999/doc-analyzer:latest
```

### 3.2 Avec docker compose

```powershell
docker compose up --build
```

Le service `web` utilise `.env`, expose `5000:5000` et persiste la base SQLite + les uploads dans le volume `doc-data:/data`. Puis ouvrir http://localhost:5000/login.



