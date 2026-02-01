# Docker/Unraid (Compose Manager) – PostgreSQL

Diese Anleitung richtet sich an Unraid-Setups mit Compose Manager und PostgreSQL.
Empfohlen wird die offizielle **Postgres 15**-Variante (stabil und weit verbreitet).
Wenn du lieber eine neuere Version nutzt, kannst du das Image in der `docker-compose.yml`
auf `postgres:16` oder `postgres:17` ändern.

## 1) Dateien

Im Repository liegen:

- `Dockerfile` (baut die Django-App)
- `docker/entrypoint.sh` (führt Migrationen + Collectstatic aus)
- `docker-compose.yml` (App + Postgres)

## 2) Beispiel `.env`

```bash
DJANGO_SECRET_KEY=super-secret-key
DJANGO_DEBUG=false

# local:
# PostgreSQL
# DB_ENGINE=postgres
# POSTGRES_DB=inventorydb
# POSTGRES_USER=inventory
# POSTGRES_PASSWORD=inventory
# POSTGRES_HOST=127.0.0.1
# POSTGRES_PORT=5432
# POSTGRES_CONN_MAX_AGE=60

# docker:
POSTGRES_USER=inventory
POSTGRES_PASSWORD=inventory
POSTGRES_DB=inventorydb
POSTGRES_HOST=192.168.178.69
POSTGRES_PORT=5433
DJANGO_SETTINGS_MODULE=inventory_management.settings_postgres
```

## 3) Start in Unraid (Compose Manager)

1. Repository in deinen Appdata-Pfad klonen (z. B. `/mnt/user/appdata/inventory_management`).
2. In Compose Manager `docker-compose.yml` auswählen.
3. `Compose Up`.

> Hinweis: Wenn Compose Manager noch eine alte `docker-compose.yml` mit `version:` im
> Appdata-Verzeichnis hat, bitte die Datei aus dem Repo erneut übernehmen (oder das
> `version:`-Feld entfernen), damit die Warnung nicht mehr erscheint.

Die App ist danach unter `http://<unraid-ip>:8111` erreichbar.

Wenn beim Start ein Fehler wie `bind: address already in use` erscheint, ist der
gewählte `POSTGRES_PORT` bereits belegt. In dem Fall entweder einen freien Port in
`.env` setzen (z. B. `POSTGRES_PORT=5434`) **oder** die Portfreigabe im
`docker-compose.postgres.yml` komplett deaktivieren (empfohlen, wenn du nur intern
auf Postgres zugreifst).

Wenn du **bereits eine eigene Postgres-Instanz** (z. B. einen anderen Docker-Container)
auf dem Host laufen hast, nutze diese statt der integrierten DB:

- Verwende `docker-compose.yml` (App + interne DB ohne Portfreigabe), **oder**
- entferne den `db`-Service aus deiner Compose-Datei und setze in `.env`:
  - `POSTGRES_HOST=<IP des vorhandenen Postgres-Containers>`
  - `POSTGRES_PORT=<dessen Port>`

So vermeidest du Portkollisionen mit dem vorhandenen Postgres-Container.

## 4) Update-Mechanik (1‑Klick Update in Unraid)

Die Docker-Variante nutzt **Container-Updates** statt Git-Pull:

1. **Compose Manager** → `Update` (neues Image ziehen).
2. Container startet neu.
3. Beim Start werden automatisch:
   - `python manage.py migrate --noinput`
   - `python manage.py collectstatic --noinput`

Das passiert durch `docker/entrypoint.sh`. Damit brauchst du **keinen** systemd/reboot
wie beim Raspberry Pi.

## 5) PostgreSQL-Version in Unraid

Nutze nach Möglichkeit die offizielle Version:

- **Postgres 15** (empfohlen, Standard)
- **Postgres 16/17** (funktioniert ebenfalls, wenn du aktuell bleiben willst)

Die **Lemmy-Postgres**-Variante ist speziell für Lemmy gedacht und für dieses Projekt
nicht nötig.
