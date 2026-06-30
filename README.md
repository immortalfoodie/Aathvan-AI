# The Last-Minute Life Saver

An AI-powered productivity companion that reads tasks and assignments, breaks them into realistic daily steps with time estimates, schedules them with your approval, and adapts the plan in real time as you report progress.

> **Current status**: Step 1 — Foundation architecture (auth, CRUD, skeleton UI). AI-powered task decomposition, scheduling, and Google integrations are coming in later steps.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| Node.js | 18+ |
| PostgreSQL | 14+ |
| npm | 9+ |

---

## Quick Start

### 1. Clone and set up the database

```bash
# Create a PostgreSQL database
psql -U postgres -c "CREATE DATABASE lifesaver;"
```

### 2. Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL, JWT_SECRET, etc.

# Run database migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at `http://localhost:5173`. API calls are proxied to the backend automatically.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry point
│   │   ├── config.py        # Environment configuration
│   │   ├── dependencies.py  # Auth dependency (JWT extraction)
│   │   ├── db/              # Database session & base
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic layer
│   │   └── routers/         # API route handlers
│   ├── alembic/             # Database migrations
│   ├── tests/               # pytest test suite
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── api/             # HTTP client (Axios)
│       ├── components/      # Reusable UI components
│       ├── contexts/        # React contexts (auth state)
│       ├── hooks/           # Custom hooks
│       └── pages/           # Page components
└── README.md
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/lifesaver` |
| `JWT_SECRET` | Secret key for signing JWTs | *(required, no default)* |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_EXPIRATION_MINUTES` | Token expiry in minutes | `1440` (24 hours) |

---

## API Endpoints

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/signup` | Create account, returns JWT |
| POST | `/auth/login` | Log in, returns JWT |
| GET | `/auth/me` | Get current user info |

### Tasks
| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks` | List your tasks |
| POST | `/tasks` | Create a task |
| GET | `/tasks/{id}` | Get task details |
| PATCH | `/tasks/{id}` | Update a task |
| DELETE | `/tasks/{id}` | Delete a task |

### Task Steps
| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks/{id}/steps` | List steps for a task |
| POST | `/tasks/{id}/steps` | Add a step |
| PATCH | `/steps/{id}` | Update a step |

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

Tests use an in-memory SQLite database — no PostgreSQL required.

---

## Roadmap

- [x] **Step 1**: Foundation architecture (auth, CRUD, skeleton UI)
- [ ] **Step 2**: AI-powered task decomposition (LLM integration)
- [ ] **Step 3**: Scheduling & prioritization algorithm
- [ ] **Step 4**: Google Classroom & Calendar integration
- [ ] **Step 5**: Notifications & real-time updates
