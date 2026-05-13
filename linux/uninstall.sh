#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="networkprobe"
INSTALL_DIR="/opt/networkprobe"
SERVICE_USER="networkprobe"
REMOVE_NGINX="1"
REMOVE_USER="1"

usage() {
  cat <<'USAGE'
Network Probe Linux uninstaller

Usage:
  sudo bash ./uninstall.sh [options]

Options:
  --install-dir PATH       Install directory (default: /opt/networkprobe)
  --user USER              System user to remove (default: networkprobe)
  --keep-nginx-config      Keep /etc/nginx/sites-available/networkprobe
  --keep-user              Keep the service user
  -h, --help               Show this help
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
    --keep-nginx-config)
      REMOVE_NGINX="0"
      shift
      ;;
    --keep-user)
      REMOVE_USER="0"
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
  echo "Run as root, for example: sudo bash ./uninstall.sh" >&2
  exit 1
fi

if systemctl list-unit-files | awk '{print $1}' | grep -qx "${SERVICE_NAME}.service"; then
  systemctl stop "${SERVICE_NAME}.service" || true
  systemctl disable "${SERVICE_NAME}.service" || true
fi

rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload

if [[ "${REMOVE_NGINX}" == "1" ]]; then
  rm -f /etc/nginx/sites-enabled/networkprobe
  rm -f /etc/nginx/sites-available/networkprobe
  if command -v nginx >/dev/null 2>&1; then
    nginx -t && systemctl reload nginx || true
  fi
fi

if [[ -d "${INSTALL_DIR}" ]]; then
  rm -rf -- "${INSTALL_DIR}"
fi

if [[ "${REMOVE_USER}" == "1" ]] && id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  userdel "${SERVICE_USER}" || true
fi

echo "Network Probe removed."
