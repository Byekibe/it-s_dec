# Docker Setup Notes

## Overview

The application is containerized using Docker with the following services:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `db` | postgres:16-alpine | 5432 | PostgreSQL database |
| `redis` | redis:7-alpine | 6379 | Celery broker & cache |
| `api` | Custom (Dockerfile) | 5000 | Flask API |
| `worker` | Custom (Dockerfile) | - | Celery background worker |

## File Structure

```
dog/
├── docker-compose.yml    # All services orchestration
├── backend/
│   ├── Dockerfile        # Multi-stage build for API
│   └── ...
└── client/
    └── Dockerfile        # (Future) Frontend build
```

## Quick Start

```bash
# From project root (dog/)
cd /path/to/dog

# Start all services
docker-compose up -d

# Start with rebuild
docker-compose up -d --build

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f worker

# Stop all services
docker-compose down

# Stop and remove volumes (DELETES DATA)
docker-compose down -v
```

## Dockerfile Explained

The backend Dockerfile uses **multi-stage builds**:

### Stage 1: `base`
- Python 3.12 slim image
- Installs system deps (gcc, libpq for PostgreSQL)
- Installs Python dependencies from requirements.txt

### Stage 2: `development`
- Extends base
- Adds pytest for testing
- Runs Flask dev server with hot reload
- Used by docker-compose by default

### Stage 3: `production`
- Extends base
- Creates non-root user (security)
- Runs Gunicorn with 4 workers
- Used for deployment

## docker-compose.yml Explained

### Services

#### `db` (PostgreSQL)
```yaml
db:
  image: postgres:16-alpine
  environment:
    POSTGRES_USER: dog
    POSTGRES_PASSWORD: dog_secret
    POSTGRES_DB: dog_db
  volumes:
    - postgres_data:/var/lib/postgresql/data  # Persist data
  healthcheck:
    test: pg_isready  # Wait until DB is ready
```

#### `redis`
```yaml
redis:
  image: redis:7-alpine
  volumes:
    - redis_data:/data  # Persist data
  healthcheck:
    test: redis-cli ping
```

#### `api` (Flask)
```yaml
api:
  build:
    context: ./backend
    target: development  # Use dev stage
  volumes:
    - ./backend:/app    # Hot reload - changes reflect immediately
    - /app/env          # Exclude virtualenv
  depends_on:
    db: { condition: service_healthy }  # Wait for DB
```

#### `worker` (Celery)
```yaml
worker:
  command: celery -A app.core.celery worker --loglevel=info
  # Same env vars as api
  # No port exposed (internal only)
```

## Environment Variables

Create a `.env` file in the backend folder (`backend/.env`):

```bash
# Database
POSTGRES_USER=dog
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=dog_db

# Security (CHANGE THESE!)
SECRET_KEY=your-super-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# JWT
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Email (when implemented)
# MAIL_SERVER=smtp.mailtrap.io
# MAIL_PORT=587
# MAIL_USERNAME=your_username
# MAIL_PASSWORD=your_password
# MAIL_DEFAULT_SENDER=noreply@yourapp.com
```

## Common Commands

### Database Operations

```bash
# Run migrations
docker-compose exec api flask db upgrade

# Create new migration
docker-compose exec api flask db migrate -m "Description"

# Access PostgreSQL directly
docker-compose exec db psql -U dog -d dog_db
```

### Testing

```bash
# Run all tests
docker-compose exec api pytest

# Run specific test file
docker-compose exec api pytest tests/test_auth.py -v

# Run with coverage
docker-compose exec api pytest --cov=app
```

### Debugging

```bash
# Shell into API container
docker-compose exec api bash

# Shell into worker container
docker-compose exec worker bash

# View Redis data
docker-compose exec redis redis-cli

# Check container status
docker-compose ps

# Check resource usage
docker stats
```

### Celery Operations

```bash
# View active tasks
docker-compose exec worker celery -A app.core.celery inspect active

# View registered tasks
docker-compose exec worker celery -A app.core.celery inspect registered

# Purge all pending tasks
docker-compose exec worker celery -A app.core.celery purge
```

## Development Workflow

1. **Start services**: `docker-compose up -d`
2. **Edit code** in `backend/` - changes auto-reload
3. **Run tests**: `docker-compose exec api pytest`
4. **View logs**: `docker-compose logs -f api`
5. **Stop when done**: `docker-compose down`

## Production Deployment

For production, modify docker-compose or create `docker-compose.prod.yml`:

```yaml
api:
  build:
    target: production  # Use production stage
  volumes: []           # No code mounting
  environment:
    - FLASK_ENV=production
    - FLASK_DEBUG=0
```

Build and run:
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

## Troubleshooting

### Port already in use
```bash
# Find what's using the port
lsof -i :5000
# Or change port in docker-compose.yml
```

### Database connection refused
```bash
# Check if DB is healthy
docker-compose ps
# Check DB logs
docker-compose logs db
```

### Permission denied on volumes
```bash
# Fix ownership (Linux)
sudo chown -R $USER:$USER ./backend
```

### Rebuild from scratch
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

## Connecting Existing PostgreSQL

If you want to use an existing PostgreSQL instead of the containerized one:

1. Comment out `db` service in docker-compose.yml
2. Update `DATABASE_URL` to point to your existing DB:
   ```yaml
   api:
     environment:
       - DATABASE_URL=postgresql://user:pass@host.docker.internal:5432/dbname
   ```
   Note: `host.docker.internal` refers to your host machine from inside Docker.

3. Remove `depends_on: db` from api and worker services
