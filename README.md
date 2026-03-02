# Retgrow Learn API

> Backend service powering the Retgrow Learn e-learning platform — built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Database & Migrations](#database--migrations)
- [Seeding Data](#seeding-data)
- [Running the Server](#running-the-server)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [License](#license)

---

## Overview

Retgrow Learn API is the RESTful backend for an educational platform designed to aid students' tech learning journey. It manages courses, lessons, quizzes, achievements, subscriptions, payments, certificates, real-time notifications, and more.

---

## Tech Stack

| Layer            | Technology                                  |
| ---------------- | ------------------------------------------- |
| Framework        | FastAPI 0.115                               |
| Language         | Python 3.13                                 |
| ORM              | SQLAlchemy 2.0 (async with `asyncpg`)       |
| Database         | PostgreSQL (via Neon / local)               |
| Migrations       | Alembic                                     |
| Authentication   | JWT (PyJWT) + Google OAuth                  |
| Payments         | Paystack · OPay · Stripe                    |
| Email            | aiosmtplib + Jinja2 templates               |
| PDF Generation   | ReportLab (certificates)                    |
| Real-time        | Server-Sent Events (SSE)                    |
| Rate Limiting    | SlowAPI                                     |
| Server           | Uvicorn (dev) / Gunicorn + Uvicorn (prod)   |
| Hosting          | Render                                      |

---

## Architecture

The API follows a **modular, layered architecture**:

```
src/
├── auth/               # Authentication & authorization (JWT, Google OAuth)
├── common/             # Shared config, database, rate limiting, utilities
├── events/             # Event dispatcher + SSE manager + listeners
├── models/             # SQLAlchemy ORM models
├── modules/            # Feature modules (controller → service → schema)
│   ├── achievements/
│   ├── certificates/
│   ├── contact/
│   ├── courses/
│   ├── cron/
│   ├── dashboard/
│   ├── deadlines/
│   ├── discussions/
│   ├── leaderboard/
│   ├── learning_path/
│   ├── lessons/
│   ├── modules/
│   ├── notifications/
│   ├── payments/
│   ├── quizzes/
│   ├── resources/
│   ├── search/
│   ├── subscriptions/
│   ├── tracks/
│   └── user/
├── router/             # Central router registry
├── seed/               # Database seeders
├── templates/          # Jinja2 email & HTML templates
└── main.py             # Application entry point
```

Each **feature module** follows a consistent pattern:
- `*_controller.py` — Route handlers (FastAPI router)
- `*_service.py` — Business logic
- `*_schema.py` — Pydantic request/response schemas

---

## Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL 15+ (local or cloud e.g. [Neon](https://neon.tech))
- pip / virtualenv

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd Retgrow-Learn-API

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file in the project root. Required variables:

```env
# App
APP_ENV=development
DEBUG=True
FRONTEND_URL=http://localhost:3000
SUPPORT_URL=http://localhost:3000/contact

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/retgrow_learn
ALEMBIC_DATABASE_URL=postgresql://user:password@localhost:5432/retgrow_learn

# JWT
JWT_SECRET=<your-secret>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440
JWT_REFRESH_SECRET=<your-refresh-secret>
JWT_REFRESH_EXPIRATION_DAYS=7

# CORS
ALLOWED_ORIGINS=http://localhost:3000

# Email (SMTP)
EMAIL_SENDER=noreply@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USE_TLS=True
SMTP_USER=<smtp-user>
SMTP_PASSWORD=<smtp-password>
CONTACT_RECIPIENT=admin@example.com

# Payments (optional in dev)
PAYSTACK_SECRET_KEY=
PAYSTACK_PUBLIC_KEY=
OPAY_PUBLIC_KEY=
OPAY_SECRET_KEY=
OPAY_MERCHANT_ID=
OPAY_ENVIRONMENT=sandbox
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Google OAuth (optional in dev)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Misc
CRON_SECRET=secret
LOG_LEVEL=info
```

> **Note:** In production, payment keys and email secrets are **required** and validated on startup.

---

## Database & Migrations

### Creating a Migration

```bash
alembic revision --autogenerate -m "describe your change"
```

### Running Migrations

```bash
alembic upgrade head
```

### Downgrading

```bash
alembic downgrade -1
```

---

## Seeding Data

Seed scripts populate the database with sample courses, lessons, achievements, and more:

```bash
# Main seeder (courses, modules, lessons, users, etc.)
python -m src.seed.seed

# Individual seeders
python -m src.seed.seed_lesson_content
python -m src.seed.seed_course_images
python -m src.seed.seed_achievement_icons
python -m src.seed.seed_resource_images
python -m src.seed.seed_notifications
```

---

## Running the Server

### Development

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`.

### Production

```bash
gunicorn src.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

---

## API Documentation

FastAPI automatically generates interactive API docs:

| Format  | URL                              |
| ------- | -------------------------------- |
| Swagger | `http://localhost:8000/docs`     |
| ReDoc   | `http://localhost:8000/redoc`    |

---

## Deployment

The project includes a `render.yaml` blueprint for one-click deployment to [Render](https://render.com):

1. Connect your GitHub repo to Render
2. Use the blueprint to auto-configure the service
3. Set environment variables in the Render dashboard
4. Deployments trigger automatically on push to `main`

---

## Project Structure

| Path                | Purpose                                       |
| ------------------- | --------------------------------------------- |
| `src/main.py`       | FastAPI app initialization & middleware        |
| `src/auth/`         | JWT authentication & Google OAuth flow         |
| `src/common/`       | Shared config, database, utils, rate limiter   |
| `src/events/`       | Event system (dispatcher, SSE, listeners)      |
| `src/models/`       | SQLAlchemy ORM model definitions               |
| `src/modules/`      | Feature modules (21 domains)                   |
| `src/router/`       | Centralized router registration                |
| `src/seed/`         | Database seeding scripts                       |
| `src/templates/`    | Jinja2 email & HTML templates                  |
| `alembic/`          | Migration configuration & versions             |
| `scripts/`          | Utility scripts (cron, testing, key gen)        |
| `docs/`             | Additional documentation                       |
| `render.yaml`       | Render deployment blueprint                    |

---

## License

This software is proprietary. See [LICENSE](./LICENSE) for details.
