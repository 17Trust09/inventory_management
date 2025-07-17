
# Django Inventory Management Setup

### 1. Install Python3 and Dependencies
```bash
sudo apt update
sudo apt install python3 python3-pip python3-dev libpq-dev postgresql postgresql-contrib
```

### 2. Install Virtual Environment
Create a virtual environment for the project:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Required Python Packages
Navigate to your project directory and install the necessary Python dependencies:
```bash
pip install -r requirements.txt
```

### 4. Setup PostgreSQL
1. Create a new PostgreSQL user and database:
    ```bash
    sudo -u postgres createuser --interactive
    sudo -u postgres createdb inventory_db
    ```
2. Set up the PostgreSQL database connection in the Django settings.

### 5. Create Django Superuser
Run the following commands to apply migrations and create a superuser for the Django admin panel:
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Configure Systemd Service

To ensure the Django project runs automatically after reboot, create a systemd service.

#### Create the Django service file

Create the service file in `/etc/systemd/system/django_inventory.service`:
```bash
sudo nano /etc/systemd/system/django_inventory.service
```

Insert the following content:

```ini
[Unit]
Description=Django Inventory Service
After=network.target

[Service]
User=pi
Group=pi
WorkingDirectory=/home/pi/inventory_management
ExecStart=/home/pi/inventory_management/venv/bin/python /home/pi/inventory_management/manage.py runserver 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Reload systemd and start the service

Reload systemd and enable the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable django_inventory.service
sudo systemctl start django_inventory.service
```

Check the status of the service:
```bash
sudo systemctl status django_inventory.service
```

### 7. Create the `start_django.sh` Script

Create the `start_django.sh` script in your project directory:
```bash
nano /home/pi/inventory_management/start_django.sh
```

Insert the following content:

```bash
#!/bin/bash

# Activate the virtual environment
source /home/pi/inventory_management/venv/bin/activate

# Run the Django development server
python /home/pi/inventory_management/manage.py runserver 0.0.0.0:8000
```

Make the script executable:
```bash
chmod +x /home/pi/inventory_management/start_django.sh
```

### 8. Access the Django Inventory Management System
Once the service is running, you can access your Django inventory management system from any device in your network by visiting:
```bash
http://<your-raspberry-pi-ip>:8000
```

You can log in using the superuser credentials created earlier.

## Useful Commands

- To stop the service:
  ```bash
  sudo systemctl stop django_inventory.service
  ```

- To restart the service:
  ```bash
  sudo systemctl restart django_inventory.service
  ```

- To check the status of the service:
  ```bash
  sudo systemctl status django_inventory.service
  ```

## Troubleshooting
- If the server is not accessible, ensure that your firewall allows incoming traffic on port 8000.
- If you encounter issues, check the logs for any errors:
  ```bash
  journalctl -u django_inventory.service
  ```
