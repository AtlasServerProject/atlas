#!/bin/bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$EUID" -ne 0 ]]; then
    echo 'Execute com sudo. São instalados arquivos em /etc/atlas, /opt/atlas/scripts e unidades systemd.' >&2
    exit 1
fi
if [[ "$#" -gt 1 || ( "$#" -eq 1 && "$1" != '--reconfigure' ) ]]; then
    echo 'Uso: sudo infra/scripts/install-offsite.sh [--reconfigure]' >&2
    exit 1
fi
command -v restic >/dev/null || { echo 'restic ausente: sudo apt install restic' >&2; exit 1; }
install -d -m 700 /etc/atlas
install -d -m 755 /opt/atlas/scripts
umask 077

# Credenciais lidas somente neste terminal; nunca passam por argumentos de processo.
if [[ ! -f /etc/atlas/offsite.env || "${1:-}" == '--reconfigure' ]]; then
    read -rp 'Cloudflare Account ID (32 caracteres hexadecimais): ' account
    read -rp 'Nome do bucket R2: ' bucket
    read -rp 'R2 Access Key ID: ' key_id
    read -rsp 'R2 Secret Access Key (não aparece): ' secret; echo
    # Colar pelo navegador costuma trazer espaços nas pontas.
    account="${account//[[:space:]]/}"; bucket="${bucket//[[:space:]]/}"
    key_id="${key_id//[[:space:]]/}"; secret="${secret//[[:space:]]/}"
    [[ "$account" =~ ^[0-9a-f]{32}$ ]] || { echo 'Account ID inválido.' >&2; exit 1; }
    [[ "$bucket" =~ ^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$ ]] || { echo 'Nome de bucket inválido.' >&2; exit 1; }
    [[ "$key_id" =~ ^[A-Za-z0-9]{16,128}$ && "$secret" =~ ^[A-Za-z0-9]{16,128}$ ]] || { echo 'Chave de acesso inválida.' >&2; exit 1; }
    printf 'RESTIC_REPOSITORY=s3:https://%s.r2.cloudflarestorage.com/%s/atlas\nAWS_ACCESS_KEY_ID=%s\nAWS_SECRET_ACCESS_KEY=%s\nAWS_DEFAULT_REGION=auto\n' \
        "$account" "$bucket" "$key_id" "$secret" > /etc/atlas/offsite.env.new
    mv /etc/atlas/offsite.env.new /etc/atlas/offsite.env
    unset secret
fi
chmod 600 /etc/atlas/offsite.env
if [[ ! -f /etc/atlas/offsite.restic-password ]]; then
    openssl rand -base64 48 > /etc/atlas/offsite.restic-password
    new_password=1
fi
chmod 600 /etc/atlas/offsite.restic-password
if [[ ! -f /etc/atlas/offsite.json ]]; then
    install -m 600 "$SCRIPT_DIR/../config/offsite.example.json" /etc/atlas/offsite.json
fi

(
    set -a; . /etc/atlas/offsite.env; set +a
    export RESTIC_PASSWORD_FILE=/etc/atlas/offsite.restic-password RESTIC_CACHE_DIR=/var/cache/atlas-offsite
    if ! restic cat config >/dev/null 2>&1; then
        restic init
    fi
    restic cat config >/dev/null
)

install -m 755 "$SCRIPT_DIR/offsite-backup.py" /opt/atlas/scripts/offsite-backup.py
install -m 644 "$SCRIPT_DIR/../templates/atlas-offsite.service" /etc/systemd/system/atlas-offsite.service
install -d -m 755 /etc/systemd/system/atlas-backup.service.d
install -m 644 "$SCRIPT_DIR/../templates/atlas-backup.service.d/offsite.conf" /etc/systemd/system/atlas-backup.service.d/offsite.conf
systemctl daemon-reload
# Primeiro envio em segundo plano; o Minecraft não é parado.
systemctl start --no-block atlas-offsite.service
echo 'Envio iniciado. Acompanhe: sudo journalctl -fu atlas-offsite'
if [[ "${new_password:-}" == 1 ]]; then
    echo
    echo 'IMPORTANTE: sem a senha abaixo a cópia externa não pode ser lida. Guarde-a fora deste servidor'
    echo '(gerenciador de senhas) e não a publique. Para vê-la: sudo cat /etc/atlas/offsite.restic-password'
fi
