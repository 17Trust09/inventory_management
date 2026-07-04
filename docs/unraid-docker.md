# Unraid Docker Setup (mit PostgreSQL als separatem Container)

> **Branch:** `fix/runtime-fehler-und-deps` – getestet auf Unraid 7.x

Diese Anleitung beschreibt das Setup des inventory_management auf Unraid mit:
- **PostgreSQL 15** als separatem Docker-Container (Unraid Docker-UI)
- **inventory_app** als Compose-Stack (Unraid Compose Manager)
- Dem Branch `fix/runtime-fehler-und-deps`

---

## 1) Voraussetzungen

- Unraid mit laufendem Docker-Service
- Pfadbasis: `/mnt/data/appdata/`
- Freier Port für die Django-App: `18000`
- Freier Port für PostgreSQL: `15433` (Host) → `5432` (Container)

---

## 2) Projekt auf Unraid klonen

**Einmalig** im Unraid-Terminal:

```bash
mkdir -p /mnt/data/appdata/inventory_management
git clone --depth 1 --branch fix/runtime-fehler-und-deps \
    https://github.com/17Trust09/inventory_management.git \
    /mnt/data/appdata/inventory_management
```

Bei Updates später:

```bash
cd /mnt/data/appdata/inventory_management
git pull
```

---

## 3) `.env` anlegen

Datei: `/mnt/data/appdata/inventory_management/.env`

```env
# Django
DJANGO_SECRET_KEY=change-me-long-random-secret
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=*
CSRF_TRUSTED_ORIGINS=http://DEINE_UNRAID_IP:18000

# Zeitzone/URL
TZ=Europe/Berlin
INVENTORY_BASE_URL=http://DEINE_UNRAID_IP:18000

# PostgreSQL
DB_ENGINE=postgres
POSTGRES_DB=inventorydb
POSTGRES_USER=inventory
POSTGRES_PASSWORD=inventory
POSTGRES_HOST=DEINE_UNRAID_IP
POSTGRES_PORT=15433
POSTGRES_CONN_MAX_AGE=60
```

> **⚠️ Wichtig:** `POSTGRES_HOST` muss die **Unraid-IP** sein (z. B. `192.168.178.69`), **nicht** `127.0.0.1` oder `db`.  
> Der PostgreSQL-Container läuft als separater Docker-Container und exponiert Port `15433` auf dem Host.

---

## 4) Dockerfile im Projektordner anlegen

Datei: `/mnt/data/appdata/inventory_management/Dockerfile`

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# build-essential + python3-dev werden für hnswlib benötigt
# default-libmysqlclient-dev + pkg-config für mysqlclient
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        pkg-config \
        default-libmysqlclient-dev \
        build-essential \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["bash", "-lc", "python manage.py migrate && python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:8000"]
```

> **Hinweis:** `build-essential` und `python3-dev` werden benötigt, weil `hnswlib` natives Kompilieren erfordert.  
> `pkg-config` + `default-libmysqlclient-dev` für `mysqlclient` (auch wenn PostgreSQL genutzt wird).

---

## 5) PostgreSQL-Container im Unraid Docker-UI anlegen

Öffne **Docker** in der Unraid-WebUI und klicke **"Add Container"**.

| Feld | Wert |
|------|------|
| Name | `inventory-db` |
| Repository | `postgres:15` |

### Umgebungsvariablen

| Variable | Wert |
|----------|------|
| `POSTGRES_PASSWORD` | `inventory` |
| `POSTGRES_USER` | `inventory` |
| `POSTGRES_DB` | `inventorydb` |

### Pfad-Mapping

| Host-Pfad | Container-Pfad |
|-----------|----------------|
| `/mnt/cache/appdata/postgresql15` | `/var/lib/postgresql/data` |

### Port-Mapping

| Host-Port | Container-Port |
|-----------|----------------|
| `15433` | `5432` |

> **Netzwerk:** Auf **Bridge** lassen (default).  
> **Wichtig:** Der Host-Port `15433` verhindert Konflikte mit anderen PostgreSQL-Instanzen auf dem Unraid-Host.

Danach den Container starten. Nach einigen Sekunden prüfen:

```bash
docker logs inventory-db
```

Sollte `database system is ready to accept connections` zeigen.

---

## 6) Compose-Stack in Unraid anlegen

### 6.1 Stack erstellen

1. In Unraid auf **Compose** gehen
2. **Add New Compose Stack**
3. `stack_name`: `inventory-management`
4. `Stack Directory`: `default` (wie im Screenshot)
5. Mit **OK** bestätigen

### 6.2 Compose-Inhalt eintragen

In den Editor folgenden Inhalt einfügen:

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

> **Hinweis:** Der PostgreSQL-Container (`inventory-db`) wird **nicht** im Compose-File definiert, da er bereits über das Docker-UI läuft.  
> Verbindung erfolgt über `POSTGRES_HOST=DEINE_UNRAID_IP` und `POSTGRES_PORT=15433`.

### 6.3 SAVE CHANGES und starten

- **Save Changes** klicken
- Beim Stack auf **Compose Up** klicken
- Der Build-Vorgang dauert beim ersten Mal ca. 5 Minuten
- Nach erfolgreichem Build startet der Container automatisch

### 6.4 Build beschleunigen (optional)

Das Image kann manuell vorgebaut werden, damit Compose Up schneller geht:

```bash
docker build -t inventory_app /mnt/data/appdata/inventory_management
```

Danach startet **Compose Up** sofort (überspringt den Build).

---

## 7) Admin-User anlegen

Auf Unraid funktioniert `docker exec -it` **nicht** (runc-Problem mit User-Namespaces).  
Stattdessen mit `nsenter` in den Container gehen:

### 7.1 PID des Containers ermitteln

```bash
docker inspect inventory_app --format '{{.State.Pid}}'
```

### 7.2 In den Container wechseln

```bash
sudo nsenter -t <PID> -m -u -i -n -p /bin/bash
```

Danach:

```bash
cd /app
python manage.py createsuperuser
```

Username, Email (Enter) und Passwort eingeben, dann `exit`.

### 7.3 Alternative: Ohne Interaktion per Python

```bash
docker exec inventory_app python -c "
import django; import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory_management.settings')
import django; django.setup()
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Admin created: admin / admin123')
else:
    print('Superuser already exists')
"
```

---

## 8) Zugriff

| Dienst | URL |
|--------|-----|
| App | `http://DEINE_UNRAID_IP:18000` |
| Admin | `http://DEINE_UNRAID_IP:18000/admin` |

---

## 9) Updates

```bash
cd /mnt/data/appdata/inventory_management
git pull
```

Dann im Compose Manager den Stack **Compose Down** und **Compose Up** (oder Recreate).

---

## 10) Typische Fehler & Fixes

### Build-Fehler `hnswlib` / `mysqlclient`

**Fehler:** `Failed to build hnswlib` / `Can not find valid pkg-config name`

**Lösung:** `build-essential`, `python3-dev`, `pkg-config` und `default-libmysqlclient-dev` im Dockerfile installieren (siehe Schritt 4).

### `connection refused` zur DB

**Fehler:** `could not connect to server: Connection refused`

**Lösung prüfen:**
1. PostgreSQL-Container läuft? → `docker logs inventory-db`
2. `POSTGRES_HOST` auf die Unraid-IP gesetzt? (nicht `127.0.0.1` oder `db`)
3. `POSTGRES_PORT=15433`?
4. Port `15433` ist im PostgreSQL-Container auf Host gemappt?

### `DisallowedHost`

**Lösung:** `DJANGO_ALLOWED_HOSTS=*` oder die konkrete IP in `.env` setzen.

### CSRF-Fehler beim Login

**Lösung:** `CSRF_TRUSTED_ORIGINS=http://DEINE_UNRAID_IP:18000` in `.env` setzen.

### `docker exec -it` funktioniert nicht

**Fehler:** `OCI runtime exec failed: open /run/user/0/runc-process...`

**Lösung:** `nsenter` verwenden (siehe Schritt 7) oder den Python-Einzeiler ohne Interaktion.

### Statische Dateien fehlen (CSS ohne Formatierung)

**Lösung:** Ordner existieren? Prüfen:

```bash
mkdir -p /mnt/data/appdata/inventory_management/media
mkdir -p /mnt/data/appdata/inventory_management/staticfiles
```

Dann Container neustarten (Compose Down / Up).

---

## 11) Sicherheits-Hinweis

`runserver` ist für kleine Heimnetz-Setups ok, aber kein vollwertiger Produktions-Server.  
Für dauerhaften Betrieb: Gunicorn + Reverse Proxy (Nginx/Traefik) + HTTPS.
