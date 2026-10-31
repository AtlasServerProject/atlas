#!/bin/bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$EUID" -ne 0 ]]; then
    echo 'Execute com sudo. São instalados arquivos em /etc/atlas, /opt/atlas/scripts e unidades systemd.' >&2
    exit 1
fi
if [[ "$#" -ne 1 || ! -f "$1" ]]; then
    echo 'Uso: sudo infra/scripts/install-backup.sh /caminho/privado/backup.pgpass' >&2
    exit 1
fi
for command in python3 pg_dump pg_restore psql systemctl; do
    command -v "$command" >/dev/null
done
install -d -m 700 /etc/atlas
install -d -m 755 /opt/atlas/scripts
install -m 600 "$1" /etc/atlas/backup.pgpass
if [[ ! -f /etc/atlas/backup.json ]]; then
    install -m 600 "$SCRIPT_DIR/../config/backup.example.json" /etc/atlas/backup.json
fi
install -m 755 "$SCRIPT_DIR/backup-manager.py" /opt/atlas/scripts/backup-manager.py
install -m 644 "$SCRIPT_DIR/../templates/atlas-backup.service" /etc/systemd/system/atlas-backup.service
install -m 644 "$SCRIPT_DIR/../templates/atlas-backup.timer" /etc/systemd/system/atlas-backup.timer
systemctl daemon-reload
# Primeiro backup valida a instalação antes de ativar o agendamento.
systemctl start atlas-backup.service
systemctl enable --now atlas-backup.timer
systemctl list-timers atlas-backup.timer --no-pager
