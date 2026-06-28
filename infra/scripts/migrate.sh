#!/bin/bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

source "$SCRIPT_DIR/lib/bootstrap.sh"

MIGRATIONS_DIR="$PROJECT_ROOT/database/migrations"

header

info "Executando migrations do Atlas..."

sudo -u postgres psql -d "$POSTGRES_DATABASE" <<SQL
CREATE TABLE IF NOT EXISTS schema_migrations (
    id BIGSERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    executed_at TIMESTAMP NOT NULL DEFAULT NOW()
);
SQL

for migration in "$MIGRATIONS_DIR"/*.sql; do
    filename="$(basename "$migration")"

    already_run=$(sudo -u postgres psql -d "$POSTGRES_DATABASE" -tAc "SELECT COUNT(*) FROM schema_migrations WHERE filename = '$filename';")

    if [ "$already_run" = "1" ]; then
        warning "Ignorando migration já aplicada: $filename"
        continue
    fi

    info "Aplicando migration: $filename"

    if sudo -u postgres psql -d "$POSTGRES_DATABASE" < "$migration"; then
        sudo -u postgres psql -d "$POSTGRES_DATABASE" -c "INSERT INTO schema_migrations (filename) VALUES ('$filename');"
        success "Migration aplicada: $filename"
    else
        abort "Falha ao aplicar migration: $filename"
    fi
done

success "Todas as migrations foram processadas."