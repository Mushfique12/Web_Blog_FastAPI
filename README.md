# Web Blog FastAPI

A full-stack blog application built with FastAPI, SQLAlchemy, and Jinja2. It includes a public blog frontend, authenticated user flows, post management APIs, password reset support, and profile image uploads.

## Overview

This project is a personal blog platform that supports:

- Public home and post pages rendered with Jinja2 templates
- User registration and login
- JWT-based authentication for protected API routes
- Blog post CRUD endpoints with author checks
- Password reset flow with email delivery using SMTP
- User profile images with local media storage
- SQLite persistence via SQLAlchemy async engine
- API documentation via OpenAPI/Swagger

## Tech Stack

- Python 3.13
- FastAPI
- SQLAlchemy 2.0 with async SQLite (`aiosqlite`)
- Pydantic + pydantic-settings
- JWT authentication via `PyJWT`
- Argon2 password hashing via `pwdlib`
- Jinja2 templates for HTML pages
- Pillow for profile image processing
- SMTP email support for password reset emails

## Project Structure

```text
.
├── main.py                  # FastAPI app entry point and HTML routes
├── models.py                # SQLAlchemy ORM models
├── database.py              # Async database setup and session dependency
├── auth.py                  # JWT/auth helpers and current-user dependency
├── schemas.py               # Pydantic request/response models
├── config.py                # Environment settings and configuration
├── email_utils.py           # Password reset email logic
├── image_utils.py           # Profile image validation and processing
├── populate_db.py           # Script to seed sample users/posts
├── blog.db                  # SQLite database file
├── .env                     # Local environment variables
├── requirements.txt         # Python dependencies
├── static/                  # CSS, JS, icons, and generated static assets
├── media/                   # Uploaded profile images and media files
├── templates/               # Jinja2 HTML templates
├── routers/
│   ├── __init__.py
│   ├── posts.py             # Post-related API routes
│   └── users.py             # Auth/user/account API routes
└── populate_images/         # Sample images used for seeding demo data
```

## Features

### User authentication and accounts

- Register a user account
- Log in using email + password through `/api/users/token`
- Access the authenticated user via `/api/users/me`
- Change password for logged-in users
- Request password reset emails
- Reset password with a secure token flow

### Blog functionality

- List latest posts on the home page
- View individual posts by ID
- Browse posts for a specific user
- Create, update, and delete posts from authorized API routes
- Author-only permissions enforced for post updates and deletion

### Frontend

The app serves a server-rendered blog UI with pages such as:

- `/`
- `/posts`
- `/posts/{post_id}`
- `/users/{user_id}/posts`
- `/login`
- `/register`
- `/account`
- `/forgot-password`
- `/reset-password`

### API docs

FastAPI automatically exposes interactive docs at:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Configuration

Environment variables are loaded from `.env` using `pydantic-settings`.

Required values include:

- `SECRET_KEY`
- `MAIL_SERVER`
- `MAIL_PORT`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_FROM`
- `MAIL_USE_TLS`
- `FRONTEND_URL`

The project includes a `.env` file for local development, but you should replace secrets before using it in any real deployment.

## Local Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
fastapi run main.py
```

4. Open the app in a browser:

```text
http://localhost:8000
```

## Database

This project uses SQLite by default and creates the database tables automatically on startup.

- Database URL: `sqlite+aiosqlite:///./blog.db`
- Tables are created from SQLAlchemy models in `models.py`
- The app creates tables at startup via the lifespan hook in `main.py`

## Seeding Demo Data

A helper script is included to populate the database with sample users and posts:

```bash
python populate_db.py
```

This script also prepares local sample profile images used in the blog.

## Notes

- This project is a feature-complete personal blog demo, but it is still a work-in-progress project.
- The app is designed for local development and learning, not a production-grade deployment setup by default.
- Password reset emails are integrated with SMTP and can be configured through the environment settings.

## Common API Routes

```text
POST   /api/users                Create a user
POST   /api/users/token          Login and receive JWT token
GET    /api/users/me             Current authenticated user
PATCH  /api/users/me/password   Change password
POST   /api/users/forgot-password
POST   /api/users/reset-password

GET    /api/posts                List posts with pagination
POST   /api/posts                Create a new post
GET    /api/posts/{post_id}     Fetch a single post
PUT    /api/posts/{post_id}     Update a post (full replace)
PATCH  /api/posts/{post_id}     Update a post (partial)
DELETE /api/posts/{post_id}      Delete a post
```

## License

This project does not currently include a license file. Review the repository owner’s usage policy before reusing or distributing the code.
