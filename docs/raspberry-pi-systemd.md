# Raspberry Pi Setup (systemd Autostart)

Diese Anleitung zeigt, wie du das Django-Projekt auf einem Raspberry Pi als systemd-Dienst startest,
so dass die App nach dem Boot automatisch läuft und im Heimnetz erreichbar ist.

## 1) Projekt-Ordner prüfen

Beispielpfad (bitte anpassen, falls dein Repo woanders liegt):

```
/home/pi/inventory_management
```

## 2) Virtuelle Umgebung und Dependencies

Falls noch nicht geschehen:

```
cd /home/pi/inventory_management
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

> Hinweis: Für den Produktivbetrieb kannst du später auf gunicorn/nginx umsteigen. Für den Autostart reicht
> der Entwicklungsserver zunächst aus.

## 3) systemd-Service anlegen

Erstelle die Service-Datei:

```
sudo nano /etc/systemd/system/inventory.service
```

Inhalt (Pfad/Benutzer ggf. anpassen):

```
[Unit]
Description=Inventory Management Django App
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/inventory_management
Environment="PATH=/home/pi/inventory_management/venv/bin"
ExecStart=/home/pi/inventory_management/venv/bin/python manage.py runserver 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## 4) Service aktivieren und starten

```
sudo systemctl daemon-reload
sudo systemctl enable --now inventory.service
sudo systemctl status inventory.service
```

Logs ansehen:

```
journalctl -u inventory.service -f
```

## 5) Zugriff im Heimnetz

Im Browser auf deinem PC oder Handy:

```
http://<PI-IP>:8000
```

## 6) (Optional) Tailscale-Weiterleitung

Wenn Tailscale installiert ist, kannst du den lokalen Port durchreichen:

```
sudo tailscale serve http / http://127.0.0.1:8000
```

Dann ist die App unter deiner Tailscale-URL erreichbar.
