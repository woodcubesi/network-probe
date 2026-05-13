#!/usr/bin/env bash
set -euo pipefail

APP_NAME="networkprobe"
SERVICE_NAME="networkprobe"
INSTALL_DIR="/opt/networkprobe"
SERVICE_USER="networkprobe"
LISTEN_HOST="127.0.0.1"
PORT="8081"
WITH_NGINX="0"
SERVER_NAME="_"
OPEN_FIREWALL="0"
START_NOW="1"

usage() {
  cat <<'USAGE'
Network Probe Linux installer

Usage:
  sudo bash ./install.sh [options]

Options:
  --install-dir PATH      Install directory (default: /opt/networkprobe)
  --user USER             System user for the service (default: networkprobe)
  --listen-host HOST      App bind host (default: 127.0.0.1)
  --port PORT             App port (default: 8081)
  --with-nginx            Install/configure Nginx reverse proxy on port 80
  --server-name NAME      Nginx server_name (default: _)
  --open-firewall         Open UFW firewall for HTTP or app port if UFW is active
  --no-start              Install but do not start the service
  -h, --help              Show this help

Examples:
  sudo bash ./install.sh
  sudo bash ./install.sh --listen-host 0.0.0.0 --open-firewall
  sudo bash ./install.sh --with-nginx --server-name probe.example.local --open-firewall
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir)
      INSTALL_DIR="${2:?missing value for --install-dir}"
      shift 2
      ;;
    --user)
      SERVICE_USER="${2:?missing value for --user}"
      shift 2
      ;;
    --listen-host)
      LISTEN_HOST="${2:?missing value for --listen-host}"
      shift 2
      ;;
    --port)
      PORT="${2:?missing value for --port}"
      shift 2
      ;;
    --with-nginx)
      WITH_NGINX="1"
      shift
      ;;
    --server-name)
      SERVER_NAME="${2:?missing value for --server-name}"
      shift 2
      ;;
    --open-firewall)
      OPEN_FIREWALL="1"
      shift
      ;;
    --no-start)
      START_NOW="0"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root, for example: sudo bash ./install.sh" >&2
  exit 1
fi

case "${PORT}" in
  ''|*[!0-9]*)
    echo "--port must be numeric" >&2
    exit 1
    ;;
esac

if (( PORT < 1 || PORT > 65535 )); then
  echo "--port must be between 1 and 65535" >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_APP="${SCRIPT_DIR}/app.py"
SOURCE_README="${SCRIPT_DIR}/README.md"

if [[ ! -f "${SOURCE_APP}" ]]; then
  SOURCE_APP="$(cd -- "${SCRIPT_DIR}/.." && pwd)/app.py"
  SOURCE_README="$(cd -- "${SCRIPT_DIR}/.." && pwd)/README.md"
fi

if [[ ! -f "${SOURCE_APP}" ]]; then
  echo "app.py not found. Keep install.sh beside app.py or inside the linux package." >&2
  exit 1
fi

PYTHON_BIN="$(command -v python3 || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "python3 not found. Installing python3 with apt..."
  apt-get update
  apt-get install -y python3
  PYTHON_BIN="$(command -v python3)"
fi

if ! "${PYTHON_BIN}" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  echo "Python 3.10 or newer is required." >&2
  exit 1
fi

if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --home-dir "${INSTALL_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0755 "${INSTALL_DIR}"
install -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0644 "${SOURCE_APP}" "${INSTALL_DIR}/app.py"
if [[ -f "${SOURCE_README}" ]]; then
  install -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0644 "${SOURCE_README}" "${INSTALL_DIR}/README.md"
fi

cat >/etc/systemd/system/${SERVICE_NAME}.service <<UNIT
[Unit]
Description=Network Probe web application
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${PYTHON_BIN} ${INSTALL_DIR}/app.py --host ${LISTEN_HOST} --port ${PORT} --quiet
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"

if [[ "${WITH_NGINX}" == "1" ]]; then
  PROXY_HOST="${LISTEN_HOST}"
  if [[ "${PROXY_HOST}" == "0.0.0.0" ]]; then
    PROXY_HOST="127.0.0.1"
  fi

  if ! command -v nginx >/dev/null 2>&1; then
    apt-get update
    apt-get install -y nginx
  fi

  cat >/etc/nginx/sites-available/networkprobe <<NGINX
server {
    listen 80;
    server_name ${SERVER_NAME};

    location / {
        proxy_pass http://${PROXY_HOST}:${PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
NGINX

  ln -sfn /etc/nginx/sites-available/networkprobe /etc/nginx/sites-enabled/networkprobe
  nginx -t
  systemctl enable nginx
fi

if [[ "${OPEN_FIREWALL}" == "1" ]] && command -v ufw >/dev/null 2>&1 && ufw status | grep -qi "Status: active"; then
  if [[ "${WITH_NGINX}" == "1" ]]; then
    ufw allow 80/tcp
  else
    ufw allow "${PORT}/tcp"
  fi
fi

if [[ "${START_NOW}" == "1" ]]; then
  systemctl restart "${SERVICE_NAME}.service"
  if [[ "${WITH_NGINX}" == "1" ]]; then
    systemctl restart nginx
  fi
fi

echo "Network Probe installed."
echo "Service: ${SERVICE_NAME}"
echo "Service URL: http://${LISTEN_HOST}:${PORT}"
if [[ "${WITH_NGINX}" == "1" ]]; then
  echo "Nginx URL: http://${SERVER_NAME}"
fi
echo "Check status: systemctl status ${SERVICE_NAME}"
