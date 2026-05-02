#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }
info() { echo -e "${CYAN}[→]${NC} $1"; }

cleanup() {
    echo ""
    info "Shutting down..."
    # Kill background processes
    if [[ -n "${BACKEND_PID:-}" ]]; then
        kill "$BACKEND_PID" 2>/dev/null && log "Backend stopped"
    fi
    if [[ -n "${FRONTEND_PID:-}" ]]; then
        kill "$FRONTEND_PID" 2>/dev/null && log "Frontend stopped"
    fi
    # Stop docker services
    docker compose -f "$ROOT_DIR/docker-compose.yml" stop db redis 2>/dev/null
    log "Infrastructure stopped"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        ClickSupply  —  Starting      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

# ─── 1. Check prerequisites ────────────────────────────────────────────────
info "Checking prerequisites..."

for cmd in docker node npm; do
    if ! command -v "$cmd" &>/dev/null; then
        err "$cmd is required but not found. Please install it."
        exit 1
    fi
done

# Find Python 3.11+
PYTHON=""
for py in python3.13 python3.12 python3.11; do
    if command -v "$py" &>/dev/null; then
        PYTHON="$(command -v "$py")"
        break
    fi
done
if [[ -z "$PYTHON" ]]; then
    err "Python 3.11+ is required. Install with: brew install python@3.12"
    exit 1
fi
log "All prerequisites found (Python: $($PYTHON --version))"

# ─── 2. Start infrastructure (Postgres + Redis) via Docker ──────────────────
info "Starting Postgres and Redis..."
docker compose -f "$ROOT_DIR/docker-compose.yml" up -d db redis
log "Postgres and Redis are up"

# Wait for Postgres to be truly ready
info "Waiting for Postgres..."
for i in $(seq 1 30); do
    if docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T db pg_isready -U clicksupply &>/dev/null; then
        break
    fi
    sleep 1
done
log "Postgres is ready"

# ─── 3. Backend setup ──────────────────────────────────────────────────────
info "Setting up backend..."
cd "$BACKEND_DIR"

# Create .env from example if missing
if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        cp .env.example .env
        warn ".env created from .env.example — review and update secrets"
    else
        err ".env.example not found. Create backend/.env manually."
        exit 1
    fi
fi

# Create virtualenv if missing or wrong Python version
if [[ ! -d .venv ]] || ! .venv/bin/python3 --version 2>/dev/null | grep -qE '3\.(1[1-9]|[2-9][0-9])'; then
    info "Creating Python virtual environment with $PYTHON..."
    rm -rf .venv
    "$PYTHON" -m venv .venv
fi

source .venv/bin/activate

# Upgrade pip first
.venv/bin/python3 -m pip install --upgrade pip -q

# Install dependencies
info "Installing backend dependencies..."
.venv/bin/python3 -m pip install -q -e ".[dev]" 2>&1 | tail -1

# Run migrations
info "Running database migrations..."
alembic upgrade head
log "Migrations complete"

# Start backend
info "Starting backend (uvicorn)..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
log "Backend running on http://localhost:8000  (PID $BACKEND_PID)"

# ─── 4. Frontend setup ─────────────────────────────────────────────────────
info "Setting up frontend..."
cd "$FRONTEND_DIR"

if [[ ! -d node_modules ]]; then
    info "Installing frontend dependencies..."
    npm install
fi

# Start frontend
info "Starting frontend (Next.js)..."
npm run dev &
FRONTEND_PID=$!
log "Frontend running on http://localhost:3000  (PID $FRONTEND_PID)"

# ─── 5. Ready ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        ClickSupply is running!       ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Frontend : http://localhost:3000    ║${NC}"
echo -e "${GREEN}║  Backend  : http://localhost:8000    ║${NC}"
echo -e "${GREEN}║  API Docs : http://localhost:8000/docs║${NC}"
echo -e "${GREEN}║  Health   : http://localhost:8000/health║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Press Ctrl+C to stop everything     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""

# Wait for background processes
wait
