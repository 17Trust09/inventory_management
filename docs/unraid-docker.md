# Unraid Docker Setup (mit externer PostgreSQL-DB)

Diese Anleitung ist für dein Setup gedacht, bei dem PostgreSQL bereits **als eigener Container auf Unraid** läuft.

> Passend zu deinem Screenshot: DB-Port ist bei dir auf dem Host als `15433` veröffentlicht, DB-Name/User/Passwort sind `inventorydb` / `inventory` / `inventory`.

## 1) Voraussetzungen

- Unraid mit laufendem PostgreSQL-Container (bei dir: `postgres:15`).
- Dieses Projekt als Ordner auf Unraid, z. B.:
  - `/mnt/user/appdata/inventory_management`
- Freier Port für die Django-App, z. B. `18000`.

## 2) `.env` für den App-Container anlegen

Lege im Projektordner eine Datei `.env` an (oder passe sie an):

```env
# Django
DJANGO_SECRET_KEY=change-me-long-random-secret
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=*
CSRF_TRUSTED_ORIGINS=http://DEINE_UNRAID_IP:18000

# Zeitzone/URL optional
TZ=Europe/Berlin
INVENTORY_BASE_URL=http://DEINE_UNRAID_IP:18000

# DB
DB_ENGINE=postgres
POSTGRES_DB=inventorydb
POSTGRES_USER=inventory
POSTGRES_PASSWORD=inventory
POSTGRES_HOST=DEINE_UNRAID_IP
POSTGRES_PORT=15433
```

### Wichtig zur DB-Verbindung

Da deine PostgreSQL laut Screenshot auf Unraid-Bridge läuft und den Host-Port `15433` nutzt, ist der stabilste Weg im App-Container:

- `POSTGRES_HOST=DEINE_UNRAID_IP`
- `POSTGRES_PORT=15433`

## 3) Dockerfile für die App

Lege im Projektordner eine `Dockerfile` an:

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["bash", "-lc", "python manage.py migrate && python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:8000"]
```

## 4) Docker-Compose-Stack für Unraid

Lege eine Datei `docker-compose.unraid.yml` an:

```yaml
services:
  inventory_app:
    build: .
    container_name: inventory_app
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "18000:8000"
    volumes:
      - ./media:/app/media
      - ./staticfiles:/app/staticfiles
```

Dann im Projektordner starten:

```bash
docker compose -f docker-compose.unraid.yml up -d --build
```

## 5) Initiale Einrichtung

### Logs prüfen

```bash
docker logs -f inventory_app
```

### Admin-User anlegen

```bash
docker exec -it inventory_app python manage.py createsuperuser
```

Danach öffnen:

- App: `http://DEINE_UNRAID_IP:18000`
- Admin: `http://DEINE_UNRAID_IP:18000/admin`

## 6) Optional: direkt per `docker run` statt Compose

```bash
docker build -t inventory_app:latest .

docker run -d \
  --name inventory_app \
  --restart unless-stopped \
  -p 18000:8000 \
  --env-file .env \
  -v /mnt/user/appdata/inventory_management/media:/app/media \
  -v /mnt/user/appdata/inventory_management/staticfiles:/app/staticfiles \
  inventory_app:latest
```

## 7) Typische Fehler & Fixes

- **`connection refused` zur DB**
  - Prüfe `POSTGRES_HOST` (Unraid-IP) und `POSTGRES_PORT=15433`.
  - Prüfe, ob der DB-Container wirklich auf `15433` published ist.
- **`DisallowedHost`**
  - `DJANGO_ALLOWED_HOSTS` in `.env` ergänzen (IP/Domain).
- **CSRF-Fehler beim Login**
  - `CSRF_TRUSTED_ORIGINS` inkl. Schema (`http://...`) setzen.
- **Statische Dateien fehlen**
  - `collectstatic` läuft beim Container-Start; Logs prüfen.

## 8) Sicherheits-Hinweis für Produktion

`runserver` ist für kleine Heimnetz-Setups ok, aber kein vollwertiger Produktions-Server.
Für dauerhaft/stabil: Gunicorn + Reverse Proxy (Nginx/Traefik) + HTTPS.
