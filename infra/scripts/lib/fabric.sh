#!/bin/bash

install_fabric() {
    info "Verificando instalação do Fabric..."

    if [ -f "$SERVER_PATH/fabric/fabric-server-launch.jar" ]; then
        success "Fabric já está instalado."
        return
    fi

    info "Criando diretório do servidor Fabric..."

    mkdir -p "$SERVER_PATH/fabric"

    cd "$SERVER_PATH/fabric"

    local INSTALLER="fabric-installer-${FABRIC_INSTALLER_VERSION}.jar"
    local URL="https://maven.fabricmc.net/net/fabricmc/fabric-installer/${FABRIC_INSTALLER_VERSION}/${INSTALLER}"

    download_file "$URL" "$INSTALLER"

    info "Instalando Fabric..."

    java -jar "$INSTALLER" server \
        -mcversion "$MC_VERSION" \
        -loader "$FABRIC_LOADER_VERSION" \
        -downloadMinecraft

    success "Fabric instalado."
}