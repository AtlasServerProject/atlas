#!/bin/bash

GREEN="\033[0;32m"
RED="\033[0;31m"
BLUE="\033[0;34m"
YELLOW="\033[1;33m"
NC="\033[0m"

header() {
    clear
    echo "==============================================="
    echo "                ATLAS INSTALLER"
    echo "==============================================="
    echo
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERRO]${NC} $1"
}

abort() {
    error "$1"
    exit 1
}

check_os() {
    info "Verificando sistema operacional..."

    if [ ! -f /etc/os-release ]; then
        abort "Não foi possível identificar o sistema operacional."
    fi

    source /etc/os-release

    if [[ "$ID" != "ubuntu" ]]; then
        abort "Sistema não suportado. Use Ubuntu Server."
    fi

    success "Ubuntu detectado: $PRETTY_NAME"
}

check_internet() {
    info "Verificando conexão com a internet..."

    if ping -c 1 1.1.1.1 >/dev/null 2>&1; then
        success "Conexão com a internet OK."
    else
        abort "Sem conexão com a internet."
    fi
}

check_java() {
    info "Verificando Java..."

    if ! command -v java >/dev/null 2>&1; then
        abort "Java não encontrado."
    fi

    JAVA_CURRENT_VERSION=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}' | cut -d. -f1)

    if [ "$JAVA_CURRENT_VERSION" -lt "$JAVA_VERSION" ]; then
        abort "Java $JAVA_VERSION ou superior é necessário."
    fi

    success "Java $JAVA_CURRENT_VERSION encontrado."
}

check_permissions() {
    info "Verificando permissões..."

    if [ ! -w "/opt/atlas" ]; then
        warning "Usuário atual não possui escrita direta em /opt/atlas. Usaremos sudo quando necessário."
    else
        success "Permissões OK."
    fi
}

create_directories() {
    info "Criando diretórios do Atlas..."

    sudo mkdir -p "$SERVER_PATH"
    sudo mkdir -p "$MODS_PATH"
    sudo mkdir -p "$BACKUP_PATH"
    sudo mkdir -p "$LOG_PATH"
    sudo mkdir -p "$WORLD_PATH"

    sudo chown -R "$USER:$USER" "$SERVER_PATH"
    sudo chown -R "$USER:$USER" "$BACKUP_PATH"
    sudo chown -R "$USER:$USER" "$LOG_PATH"

    success "Diretórios criados."
}