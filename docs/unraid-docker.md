# Unraid Docker Setup (mit externer PostgreSQL-DB)

Diese Anleitung ist für dein Setup gedacht, bei dem PostgreSQL bereits **als eigener Container auf Unraid** läuft und du den **Unraid Compose Manager** nutzt.

> Passend zu deinem Screenshot: DB-Port ist bei dir auf dem Host als `15433` veröffentlicht, DB-Name/User/Passwort sind `inventorydb` / `inventory` / `inventory`.

## 1) Voraussetzungen

- Unraid mit laufendem PostgreSQL-Container (bei dir: `postgres:15`).
- Pfadbasis auf deinem System: `/mnt/data/appdata/`
- Git ist auf Unraid verfügbar (oder du kopierst das Projekt per SMB/File-Manager).
- Freier Port für die Django-App, z. B. `18000`.

## 2) Projekt **einmalig** auf Unraid ablegen (clone)

### Variante A: per Terminal (empfohlen)

```bash
mkdir -p /mnt/data/appdata/inventory_management
git clone https://github.com/17Trust09/inventory_management.git /mnt/data/appdata/inventory_management
```

Bei Updates später:

```bash
cd /mnt/data/appdata/inventory_management
git pull
```

### Variante B: ohne Git

- Projekt lokal laden und als Ordner nach `/mnt/data/appdata/inventory_management` kopieren.

## 3) `.env` im Projektordner anlegen

Datei: `/mnt/data/appdata/inventory_management/.env`

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

## 4) Dockerfile im Projektordner anlegen

Datei: `/mnt/data/appdata/inventory_management/Dockerfile`

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Wichtig: git wird benötigt, weil requirements.txt mindestens ein Git-Dependency enthält
# (z. B. mediapy @ git+https://...)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["bash", "-lc", "python manage.py migrate && python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:8000"]
```

## 5) Compose Manager in Unraid (dein Workflow)

### 5.1 Stack erstellen

1. In Unraid auf **Compose** gehen.
2. **Add New Compose Stack** klicken.
3. `stack_name` setzen, z. B. `inventory-management`.
4. `Stack Directory` kannst du auf `default` lassen (wie in deinem Screenshot).
5. Mit **OK** bestätigen.

### 5.2 Compose-Inhalt eintragen

In den Editor (wie im Screenshot) folgenden Inhalt einfügen:

```yaml
services:
  inventory_app:
    build:
      context: /mnt/data/appdata/inventory_management
      dockerfile: Dockerfile
    container_name: inventory_app
    restart: unless-stopped
    env_file:
      - /mnt/data/appdata/inventory_management/.env
    ports:
      - "18000:8000"
    volumes:
      - /mnt/data/appdata/inventory_management/media:/app/media
      - /mnt/data/appdata/inventory_management/staticfiles:/app/staticfiles
```

Dann **Save Changes** und anschließend Stack starten.

## 6) Initiale Einrichtung

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

## 7) Updates mit Compose Manager

1. Code aktualisieren:

```bash
cd /mnt/data/appdata/inventory_management
git pull
```

2. In Unraid Compose Manager den Stack **neu bauen/redeployen** (je nach Button/Version: Recreate / Up / Compose Up).

So wird das neue Image gebaut und mit dem aktuellen Projektstand gestartet.

## 8) Optional: direkt per `docker run` statt Compose

```bash
docker build -t inventory_app:latest /mnt/data/appdata/inventory_management

docker run -d \
  --name inventory_app \
  --restart unless-stopped \
  -p 18000:8000 \
  --env-file /mnt/data/appdata/inventory_management/.env \
  -v /mnt/data/appdata/inventory_management/media:/app/media \
  -v /mnt/data/appdata/inventory_management/staticfiles:/app/staticfiles \
  inventory_app:latest
```

## 9) Typische Fehler & Fixes

- **Build-Fehler `Cannot find command 'git'`**
  - Entsteht, wenn eine Git-Dependency in `requirements.txt` steckt.
  - Mit obigem Dockerfile wird `git` im Image installiert (Fix).

- **`connection refused` zur DB**
  - Prüfe `POSTGRES_HOST` (Unraid-IP) und `POSTGRES_PORT=15433`.
  - Prüfe, ob der DB-Container wirklich auf `15433` published ist.
- **`DisallowedHost`**
  - `DJANGO_ALLOWED_HOSTS` in `.env` ergänzen (IP/Domain).
- **CSRF-Fehler beim Login**
  - `CSRF_TRUSTED_ORIGINS` inkl. Schema (`http://...`) setzen.
- **Statische Dateien fehlen**
  - `collectstatic` läuft beim Container-Start; Logs prüfen.

## 10) Sicherheits-Hinweis für Produktion

`runserver` ist für kleine Heimnetz-Setups ok, aber kein vollwertiger Produktions-Server.
Für dauerhaft/stabil: Gunicorn + Reverse Proxy (Nginx/Traefik) + HTTPS.
