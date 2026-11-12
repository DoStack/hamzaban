# Hamzaban

Hamzaban is a Django and PostgreSQL project with Django-rendered pages and locally bundled React components. The initial profile shell reuses Service45's RTL layout patterns, teal palette, Unfold admin setup, and locally served Peyda (پیدا) font. No Service45 car-service models or database content are included.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
npm ci
npm run build
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Set the PostgreSQL connection values in `.env` before running migrations. The customer profile is at `/profile/`; the Unfold admin is at `/admin/`.

Vercel Hobby deployment is planned but not configured yet. When deployment access is available, verify the Python runtime, PostgreSQL connection, static and media handling, and any background-job needs before deploying.

## Checks

```bash
coverage run --source=clients.views manage.py test --settings=config.test_settings
coverage report --fail-under=80
npm test
python manage.py check
npm run build
```

The tests use a temporary SQLite database under `/tmp`, so they do not need a running PostgreSQL server. Local application development uses PostgreSQL from `.env`.
