# Backend Developer Guide

> A comprehensive guide for developers working on the Retgrow Learn API codebase.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Architecture Overview](#architecture-overview)
- [Adding a New Module](#adding-a-new-module)
- [Authentication & Authorization](#authentication--authorization)
- [Database Patterns](#database-patterns)
- [Event System](#event-system)
- [Payment Integration](#payment-integration)
- [Email Templates](#email-templates)
- [Testing](#testing)
- [Code Conventions](#code-conventions)

---

## Development Setup

1. Fork or clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `venv\Scripts\activate` (Windows) or `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` values into a `.env` file
6. Run migrations: `alembic upgrade head`
7. Seed the database: `python -m src.seed.seed`
8. Start the server: `uvicorn src.main:app --reload`

---

## Architecture Overview

The backend follows a **modular, three-layer architecture** inside each feature module:

```
src/modules/<feature>/
├── <feature>_controller.py   # Route handlers — defines HTTP endpoints
├── <feature>_service.py      # Business logic — processes data & interacts with DB
└── <feature>_schema.py       # Pydantic schemas — validates request/response data
```

### Request Flow

```
Client Request
  → FastAPI Router (controller)
    → Service Layer (business logic)
      → SQLAlchemy ORM (database)
    ← Response Schema (serialization)
  ← JSON Response
```

### Key Singletons

| Component              | Location                         | Purpose                          |
| ---------------------- | -------------------------------- | -------------------------------- |
| `settings`             | `src/common/config.py`           | Environment config via Pydantic  |
| `async_session_maker`  | `src/common/database/database.py`| Async database session factory   |
| `limiter`              | `src/common/rate_limit.py`       | Shared SlowAPI rate limiter      |
| `event_dispatcher`     | `src/events/dispatcher.py`       | Publish/subscribe event bus      |
| `sse_manager`          | `src/events/sse_manager.py`      | SSE connection manager           |

---

## Adding a New Module

1. **Create the module folder:**
   ```
   src/modules/your_feature/
   ├── __init__.py
   ├── your_feature_controller.py
   ├── your_feature_service.py
   └── your_feature_schema.py
   ```

2. **Define your Pydantic schemas** in `your_feature_schema.py`:
   ```python
   from pydantic import BaseModel

   class YourFeatureCreate(BaseModel):
       name: str
       description: str | None = None

   class YourFeatureResponse(BaseModel):
       id: int
       name: str
       # ...

       class Config:
           from_attributes = True
   ```

3. **Write the service layer** in `your_feature_service.py`:
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession

   async def create_feature(db: AsyncSession, data: YourFeatureCreate):
       # Business logic here
       pass
   ```

4. **Create the router** in `your_feature_controller.py`:
   ```python
   from fastapi import APIRouter, Depends
   from src.auth.dependencies import get_current_user

   router = APIRouter(prefix="/your-feature", tags=["Your Feature"])

   @router.post("/")
   async def create(data: YourFeatureCreate, user=Depends(get_current_user)):
       # Call service
       pass
   ```

5. **Register the router** in `src/router/routers.py`:
   ```python
   from src.modules.your_feature.your_feature_controller import router as your_feature_router

   def include_routers(app):
       # ... existing routers
       app.include_router(your_feature_router)
   ```

6. **Add any new ORM models** in `src/models/` and create a migration:
   ```bash
   alembic revision --autogenerate -m "add your_feature table"
   alembic upgrade head
   ```

---

## Authentication & Authorization

### JWT Flow

1. User logs in via `/auth/login` or `/auth/google/callback`
2. Server issues an **access token** (short-lived) and a **refresh token** (7 days)
3. Frontend stores the access token in an HTTP-only cookie
4. Middleware on the frontend injects the `Authorization: Bearer <token>` header into API requests
5. Backend validates the token using `get_current_user` dependency

### Key Auth Dependencies

```python
from src.auth.dependencies import get_current_user, get_current_admin

# Require authenticated user
@router.get("/protected")
async def protected_route(user=Depends(get_current_user)):
    pass

# Require admin role (if applicable)
@router.get("/admin-only")
async def admin_route(user=Depends(get_current_admin)):
    pass
```

### Google OAuth

- Initiated at `GET /auth/google`
- Callback handled at `GET /auth/google/callback`
- On success, user is created (if new) and JWT tokens are issued

---

## Database Patterns

### Async Sessions

Always use async sessions from the dependency:

```python
from src.common.database.database import get_db

@router.get("/items")
async def list_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item))
    return result.scalars().all()
```

### Eager Loading

To avoid `MissingGreenlet` errors with lazy relationships:

```python
from sqlalchemy.orm import selectinload

result = await db.execute(
    select(Certificate).options(selectinload(Certificate.course))
)
```

### Migrations Workflow

```bash
# After modifying models:
alembic revision --autogenerate -m "description"
alembic upgrade head

# Rollback:
alembic downgrade -1
```

---

## Event System

The platform uses a **publish/subscribe event system** for cross-module communication (e.g., triggering achievements and notifications after a lesson is completed).

### Publishing an Event

```python
from src.events.dispatcher import event_dispatcher

await event_dispatcher.dispatch("lesson_completed", {
    "user_id": user.id,
    "lesson_id": lesson.id,
    "course_id": course.id,
})
```

### Listening for Events

Listeners are registered in `src/events/listeners/`:

- `auth_listener.py` — Login streak tracking
- `achievement_listener.py` — Badge & achievement awarding
- `notification_listener.py` — Real-time notification dispatch

### SSE (Server-Sent Events)

Real-time notifications are pushed to the frontend via SSE:

- **Manager:** `src/events/sse_manager.py` handles per-user connections
- **Endpoint:** `/notifications/stream` (GET, authenticated)
- **Frontend:** Uses `@microsoft/fetch-event-source` to consume the stream

---

## Payment Integration

The platform supports **three payment providers**:

| Provider  | Status     | Key Files                              |
| --------- | ---------- | -------------------------------------- |
| Paystack  | Active     | `src/modules/payments/paystack_*.py`   |
| OPay      | Sandbox    | `src/modules/payments/opay_*.py`       |
| Stripe    | Integrated | `src/modules/payments/stripe_*.py`     |

### Payment Flow

1. User selects a plan on the frontend
2. Frontend calls `POST /payments/initialize` with the plan and provider
3. Backend creates a payment session with the provider and returns a checkout URL
4. User completes payment on the provider's page
5. Provider sends a webhook to `POST /payments/webhook/<provider>`
6. Backend verifies the payment and activates the subscription

---

## Email Templates

Email templates are stored in `src/templates/` as Jinja2 `.html` files. They are rendered and sent via `aiosmtplib`:

| Template              | Trigger                              |
| --------------------- | ------------------------------------ |
| Welcome email         | User registration                    |
| Password reset        | Forgot password request              |
| Contact form receipt  | Contact form submission              |
| Subscription confirm  | Successful payment                   |

---

## Testing

```bash
# Run all tests
python -m pytest

# Run a specific test
python -m pytest test_gamification.py -v

# Utility scripts
python scripts/seed_test_data.py    # Populate test data
python scripts/test_cert_gen.py     # Test certificate generation
python scripts/test_new_emails.py   # Test email sending
```

---

## Code Conventions

| Convention             | Standard                                  |
| ---------------------- | ----------------------------------------- |
| Naming                 | `snake_case` for files, functions, vars   |
| Type Hints             | Required on all function signatures       |
| Async                  | All DB operations must be `async`         |
| Schemas                | Pydantic v2 with `from_attributes = True` |
| Imports                | Absolute imports from `src.*`             |
| Error Handling         | Use `HTTPException` with clear messages   |
| Logging                | Use `logging.getLogger(__name__)`         |
