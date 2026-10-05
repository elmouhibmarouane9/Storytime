#!/usr/bin/env bash
# MIM · MEM Digital — one-command install on a fresh Debian/Ubuntu server.
#
#   curl -fsSL https://raw.githubusercontent.com/elmouhibmarouane9/Storytime/main/deploy/install.sh | bash
#
# Or clone first and run:  bash deploy/install.sh
#
# Installs Docker, clones the console into /opt/mim, generates an access code,
# and starts it. With a domain it also serves HTTPS via Caddy. Idempotent: safe
# to re-run, it pulls the latest code and restarts.

set -euo pipefail

REPO="${MIM_REPO:-https://github.com/elmouhibmarouane9/Storytime.git}"
BRANCH="${MIM_BRANCH:-main}"   # main is the shipping branch; override with MIM_BRANCH=...
DIR="${MIM_DIR:-/opt/mim}"

say() { printf '\n\033[1;33m▸ %s\033[0m\n' "$1"; }

say "Checking prerequisites"
if ! command -v docker >/dev/null 2>&1; then
  say "Installing Docker"
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl git openssl
  curl -fsSL https://get.docker.com | sh
else
  apt-get install -y -qq git openssl >/dev/null 2>&1 || true
fi

say "Fetching MIM into $DIR (branch: $BRANCH)"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" fetch --quiet origin "$BRANCH"
  git -C "$DIR" checkout --quiet "$BRANCH"
  git -C "$DIR" pull --quiet origin "$BRANCH"
else
  git clone --quiet --branch "$BRANCH" "$REPO" "$DIR"
fi
cd "$DIR"

say "Configuring"
if [ -f .env ]; then
  echo "  .env already exists — keeping it."
else
  CODE="$(openssl rand -hex 12)"
  read -r -p "  Domain for HTTPS (blank = localhost only, reachable via SSH tunnel): " DOMAIN || true
  cat > .env <<EOF
MIM_ACCESS_CODE=$CODE
MIM_DOMAIN=${DOMAIN:-localhost}
MIM_EMAIL=
TZ=Europe/Madrid
EOF
  echo
  echo "  ┌────────────────────────────────────────────────────────┐"
  echo "  │  ACCESS CODE — save it, this is how you log in          │"
  echo "  │  $CODE"
  echo "  └────────────────────────────────────────────────────────┘"
fi

mkdir -p backups

PROFILE=""
DOMAIN_VALUE="$(grep -E '^MIM_DOMAIN=' .env | cut -d= -f2- || true)"
if [ -n "$DOMAIN_VALUE" ] && [ "$DOMAIN_VALUE" != "localhost" ]; then
  PROFILE="--profile https"
  say "Opening the firewall for 80/443"
  if command -v ufw >/dev/null 2>&1; then ufw allow 80/tcp >/dev/null 2>&1 || true; ufw allow 443/tcp >/dev/null 2>&1 || true; fi
fi

say "Building and starting"
docker compose $PROFILE up -d --build --remove-orphans

say "Status"
docker compose ps
cat <<EOF

Done.

  • App URL     : ${DOMAIN_VALUE:-localhost}
  • Logs        : docker compose logs -f mim
  • Update      : git pull && docker compose up -d --build
  • Backups     : docker compose exec mim cat /app/data/clients.json
  • Your book   : volume 'mim-data' — survives rebuilds and restarts

No domain yet? Reach it over an SSH tunnel from your laptop:
  ssh -L 8501:127.0.0.1:8501 root@THIS_SERVER      then open http://localhost:8501

EOF
