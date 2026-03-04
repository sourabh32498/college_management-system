FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY student/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY student /app

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && gunicorn student.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
