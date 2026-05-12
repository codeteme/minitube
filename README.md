# MiniTube

A full-stack video streaming platform built with a microservices architecture. Upload, discover, and watch videos with real-time chat, AI-powered summaries, automatic transcription, and an admin dashboard.

## Architecture

Six independent FastAPI services share a single PostgreSQL instance, orchestrated via Docker Compose:

| Service | Port | Responsibilities |
|---------|------|-----------------|
| **Video CRUD** | 8000 | Upload, streaming, metadata, thumbnail generation, ASR transcription, view counting, AI tagging |
| **Admin** | 8001 | System health metrics, application logs, user management (ban/delete), content moderation |
| **Communication** | 8002 | Real-time WebSocket chat, new-video and subscription notifications, notification inbox |
| **User Accounts & Prefs** | 8003 | Registration, login/logout, JWT auth, profile management, avatar upload, password reset |
| **Dashboard** | 8004 | Video search with history and suggestions, watch history, subscription feed, recommendations |
| **Intelligence** | 8005 | AI-generated video summaries (OpenAI or rules-based fallback), canonical tag taxonomy, auto-tagging |

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL
- **Auth:** JWT (PyJWT), bcrypt password hashing
- **Frontend:** Vue.js 3, TypeScript, Vite, Pinia
- **AI/ML:** OpenAI API (summarization & tagging), faster-whisper (ASR transcription)
- **Real-time:** WebSockets
- **Infrastructure:** Docker, Docker Compose
- **Testing:** pytest, Locust (load testing)

## Getting Started

### Prerequisites

- Docker and Docker Compose

### Run

```bash
git clone https://github.com/codeteme/minitube.git
cd minitube
docker-compose up -d
```

The frontend is available at `http://localhost:5173` once all services are healthy (roughly 30–60 seconds on first build).

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Video API | http://localhost:8000 |
| Admin API | http://localhost:8001 |
| Communication API | http://localhost:8002 |
| User Accounts API | http://localhost:8003 |
| Dashboard API | http://localhost:8004 |
| Intelligence API | http://localhost:8005 |

### Stop

```bash
docker-compose down          # keep data
docker-compose down -v       # wipe database
```

### View logs

```bash
docker-compose logs -f              # all services
docker-compose logs -f video        # specific service
```

## Configuration

Copy `.env.example` to `.env` in the project root and set any overrides:

```bash
cp .env.example .env
```

Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | _(empty)_ | Enables real AI summarization. Falls back to rules-based if unset. |
| `OPENAI_SUMMARY_MODEL` | `gpt-4o-mini` | OpenAI model for summaries and tagging |
| `SECRET_KEY` | `change-me-in-production` | JWT signing secret — override for any non-local deployment |
| `SEED_ADMIN_EMAIL` | `admin@example.com` | Email for the seeded admin account |
| `SEED_ADMIN_PASSWORD` | `admin123` | Password for the seeded admin account |

## Features

- **Auth:** JWT-based registration, login, role-based access (user / admin)
- **Video:** Upload, stream, thumbnail generation, view counting
- **ASR:** Automatic speech-to-text transcription via faster-whisper (runs on upload)
- **AI summaries:** OpenAI-powered video summaries with rules-based fallback
- **Auto-tagging:** Constrained canonical tag taxonomy with AI-driven assignment
- **Real-time chat:** WebSocket-based direct messaging between users
- **Notifications:** New-video and subscription event inbox
- **Search:** Keyword search with history and autocomplete suggestions
- **Subscriptions & feed:** Subscribe to channels, personalized video feed
- **Watch history:** Per-user viewing history
- **Admin dashboard:** System metrics, log viewer, user management, content deletion
- **Dark / light mode:** Persisted per user

## ASR (Automatic Transcription)

Transcription runs automatically after every upload using faster-whisper. Configured in `docker-compose.yml`:

```yaml
ASR_ENABLED: "true"
ASR_MODEL_SIZE: "tiny"   # tiny | base | small | medium | large
ASR_COMPUTE_TYPE: "int8"
```

The `tiny` model is fast but lower accuracy. Swap to `base` or `small` for better results at the cost of startup time.

## Load Testing

Uses [Locust](https://locust.io/). Run against a live stack:

```bash
pip install locust
locust -f locustfile.py VideoServiceUser
```

Available user classes: `AuthServiceUser`, `VideoServiceUser`, `AdminServiceUser`, `DashboardServiceUser`, `CommunicationServiceUser`, `IntelligenceServiceUser`

## Security

- JWT tokens verified on every protected endpoint; tokens carry user ID and role
- Passwords hashed with bcrypt — plaintext never stored or logged
- Admin-only endpoints return 403 for non-admin tokens
- Video ownership enforced server-side via JWT (not client-supplied fields)
- Pydantic validation at all API boundaries

## Known Limitations

- Video files are stored on a local bind-mounted volume — not suitable for horizontal scaling without object storage (S3 etc.)
- Single shared PostgreSQL instance across all services
- SMTP for password reset emails requires outbound port 587 to be open; the reset flow degrades gracefully if it is not (token is generated and logged, email silently skipped)
