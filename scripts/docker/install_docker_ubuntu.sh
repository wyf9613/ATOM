#!/usr/bin/env bash
set -euo pipefail

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "Docker Engine and Compose are already installed."
  exit 0
fi

while pgrep -f '^/usr/bin/python3 /usr/bin/unattended-upgrade$' >/dev/null; do
  echo "Ubuntu unattended upgrades are using APT; waiting 30 seconds..."
  sleep 30
done

sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker "${USER}"
sudo docker run --rm hello-world

cat <<'EOF'

Docker is installed and its daemon passed hello-world.
Log out and back in before using Docker without sudo, then run:

  docker version
  docker compose version
  ./scripts/docker/humble_build.sh
EOF
