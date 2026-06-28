#!/bin/bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/lib/bootstrap.sh"

header

info "Iniciando instalação do Atlas..."

check_os
check_internet
check_java
check_postgres
check_permissions

create_directories

install_fabric

install_stack

copy_templates

create_service

enable_service

start_server

success "========================================"
success " Atlas instalado com sucesso!"
success "========================================"

info "Servidor: $SERVER_NAME"
info "Minecraft: $MC_VERSION"
info "Cobblemon: $COBBLEMON_VERSION"
info "Porta: $SERVER_PORT"

echo
info "Execute:"
echo "atlas-cli status"