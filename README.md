# DevFlow Backend

DevFlow is a FastAPI backend for the DevFlow application. It provides a versioned authentication API with sign-up, email verification, login (access + refresh JWTs), password reset, change password, PostgreSQL persistence, Argon2 password hashing, SMTP email delivery, Alembic migrations, and automated tests.

## Technology

- Python 3.11+
- FastAPI and Pydantic
- PostgreSQL, SQLAlchemy async, SQLModel, and `asyncpg`
- Alembic for schema migrations
- Argon2 for password hashing
- PyJWT for access and refresh tokens
- SlowAPI for auth endpoint rate limiting
- `uv` for dependency and environment management
- Pytest for unit, integration, and e2e tests

## Project structure

```text
api/             HTTP routers and shared dependencies
api/v1/          Versioned API v1 feature routers
core/            Application settings, database session, and security helpers
middleware/      Auth JWT middleware for protected routes
models/          SQLModel database models
repositories/    Database access layer
schemas/         Request and response models
services/        Business logic and email integration
alembic/         Database migration scripts
tests/           Unit, integration, and e2e tests
main.py          FastAPI application entry point
```

## Prerequisites

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/)
- A reachable PostgreSQL instance
- SMTP credentials for sending verification and reset emails

Docker is optional. The included application container does not start PostgreSQL itself; point its environment variables at an existing database. A separate `docker-compose.test.yml` file starts a local PostgreSQL database for testing.

## Getting started

1. Clone the repository and enter it.

   ```bash
   git clone <repository-url>
   cd devflow-backend
   ```

2. Create a `.env` file in the project root:

   ```dotenv
   POSTGRES_DB=devflow
   POSTGRES_USER=devflow
   POSTGRES_PASSWORD=change-me
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   SQL_ECHO=false
   DATABASE_NULL_POOL=false

   SMTP_HOST=smtp.example.com
   SMTP_PORT=587
   SMTP_USERNAME=your-smtp-username
   SMTP_PASSWORD=your-smtp-password
   SMTP_FROM=no-reply@example.com
   SMTP_USE_TLS=true

   SECRET_KEY=change-me-to-a-long-random-string
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   REFRESH_TOKEN_EXPIRE_DAYS=7
   EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS=24
   PASSWORD_RESET_TOKEN_EXPIRE_HOURS=1
   FRONTEND_URL=http://localhost:3000
   ```

   The application reads `.env` by default. To use a different file, set `ENV_FILE` to its path before running a command.

3. Install the locked project dependencies:

   ```bash
   uv sync --all-groups
   ```

4. Apply the database schema:

   ```bash
   uv run alembic upgrade head
   ```

5. Run the development server:

   ```bash
   uv run uvicorn main:app --reload
   ```

The API is available at `http://127.0.0.1:8000`. Interactive documentation is available at `/docs`; the OpenAPI document is at `/openapi.json`.

## Docker

Build and run the API container with:

```bash
docker compose up --build
```

The service loads environment variables from `.env` via `env_file` and listens on port `8000`. Ensure `POSTGRES_HOST` resolves from inside the container. Run migrations separately before or after start:

```bash
uv run alembic upgrade head
```

## API

All application routes are prefixed with `/api/v1`.

### `POST /api/v1/auth/signup`

Creates an inactive user account, stores an Argon2-hashed password, and emails a verification link. Limited to **5 requests per minute per client IP**.

Request body:

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "password": "Password123!",
  "confirm_password": "Password123!"
}
```

Successful response (`201 Created`):

```json
{
  "message": "Sign up successful. Please check your email."
}
```

### `POST /api/v1/auth/verify-email`

Activates the account using the opaque token from the verification email. Limited to **10/minute**.

```json
{ "token": "<verification-token>" }
```

### `POST /api/v1/auth/login`

Returns access and refresh JWTs for an active (verified) user. Limited to **5/minute**.

```json
{
  "email": "john@example.com",
  "password": "Password123!"
}
```

Successful response (`200 OK`):

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer"
}
```

Inactive accounts receive `403`. Invalid credentials receive `401`.

### `POST /api/v1/auth/refresh`

Exchanges a valid refresh token for a new access + refresh pair (rotation). Limited to **10/minute**.

```json
{ "refresh_token": "<jwt>" }
```

### `POST /api/v1/auth/forget-password`

Always returns a generic success message. If the email exists, a reset link is emailed. Limited to **3/minute**.

```json
{ "email": "john@example.com" }
```

### `POST /api/v1/auth/reset-password`

Sets a new password using the reset token. Invalidates existing refresh sessions. Limited to **5/minute**.

```json
{
  "token": "<reset-token>",
  "password": "NewPassword123!",
  "confirm_password": "NewPassword123!"
}
```

### `POST /api/v1/auth/change-password`

Requires `Authorization: Bearer <access_token>` (enforced by auth middleware). Invalidates refresh sessions. Limited to **5/minute**.

```json
{
  "current_password": "Password123!",
  "new_password": "NewPassword123!",
  "confirm_password": "NewPassword123!"
}
```

Password rules (signup / reset / change): 8–128 characters, at least one lowercase, uppercase, number, and special character; confirm field must match. Change-password also requires the new password to differ from the current one.

## Database migrations

```bash
uv run alembic upgrade head
```

Create a new autogenerated migration after changing a SQLModel model:

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

Review autogenerated migration files before applying them.

## Testing

Start the test PostgreSQL service if you need the integration database:

```bash
docker compose -f docker-compose.test.yml up -d
```

Configure the application to use that database (see `.env.test` for JWT and SMTP placeholders).

```powershell
# PowerShell
$env:ENV_FILE = ".env.test"
uv run alembic upgrade head
uv run pytest
```

```bash
# macOS/Linux
ENV_FILE=.env.test uv run alembic upgrade head
ENV_FILE=.env.test uv run pytest
```

The test database container exposes PostgreSQL on `localhost:55432` with database, username, and password all set to `devflow_test`.

## Current status

Authentication includes signup, email verification, login (access + refresh), refresh rotation, forget-password, reset-password, and change-password. Protected routes are gated by `AuthJWTMiddleware`.

## Security notes

- Never commit `.env` files or real database/SMTP/`SECRET_KEY` credentials.
- Use a strong PostgreSQL password and `SECRET_KEY` outside local development.
- Configure trusted SMTP credentials before deployment.
- Auth endpoints are rate-limited per IP as documented above.
- Refresh tokens are stored hashed; password change/reset invalidates refresh sessions.
