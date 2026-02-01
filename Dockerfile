FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=inventory_management.settings_postgres

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
ARG MEDIAPY_VERSION=1.1.6
RUN if pip install -r requirements.txt; then \
        echo "Installed requirements (git mediapy available)."; \
    else \
        echo "Failed to install git-based mediapy. Falling back to mediapy==${MEDIAPY_VERSION}."; \
        pip install "mediapy==${MEDIAPY_VERSION}"; \
        grep -v "mediapy @ git+https://github.com/PWhiddy/mediapy.git@" requirements.txt > /tmp/requirements-no-git.txt; \
        pip install -r /tmp/requirements-no-git.txt; \
    fi

COPY . .

RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
