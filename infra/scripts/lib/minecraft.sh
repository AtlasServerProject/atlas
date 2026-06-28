#!/bin/bash

copy_templates() {
    info "Copiando templates do Minecraft..."

    local TEMPLATE_DIR="$SCRIPT_DIR/../../templates"

    cp "$TEMPLATE_DIR/eula.txt" "$SERVER_PATH/fabric/eula.txt"
    cp "$TEMPLATE_DIR/server.properties" "$SERVER_PATH/fabric/server.properties"

    success "Templates copiados."
}

create_service() {
    info "Criando serviço systemd do Atlas..."

    local TEMPLATE_DIR="$SCRIPT_DIR/../../templates"

    sudo cp "$TEMPLATE_DIR/atlas.service" /etc/systemd/system/atlas.service
    sudo systemctl daemon-reload

    success "Serviço atlas criado."
}

enable_service() {
    info "Habilitando serviço atlas..."

    sudo systemctl enable atlas

    success "Serviço atlas habilitado."
}

start_server() {
    info "Iniciando servidor Atlas..."

    sudo systemctl restart atlas

    success "Servidor iniciado."
}