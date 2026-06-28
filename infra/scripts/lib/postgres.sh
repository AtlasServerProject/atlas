#!/bin/bash

check_postgres() {
    info "Verificando PostgreSQL..."

    if ! command -v psql >/dev/null 2>&1; then
        abort "PostgreSQL não encontrado. Instale com: sudo apt install postgresql postgresql-contrib -y"
    fi

    if systemctl is-active --quiet postgresql; then
        success "PostgreSQL está ativo."
    else
        abort "PostgreSQL não está rodando. Execute: sudo systemctl start postgresql"
    fi
}