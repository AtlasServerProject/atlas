#!/bin/bash

ensure_stack_tools() {
    info "Verificando ferramentas da Atlas Stack..."

    if ! command -v curl >/dev/null 2>&1; then
        sudo apt install curl -y
    fi

    if ! command -v jq >/dev/null 2>&1; then
        sudo apt install jq -y
    fi

    success "Ferramentas OK."
}

install_modrinth_mod() {
    local SLUG="$1"
    local REQUIRED_VERSION="${2:-}"

    info "Buscando mod: $SLUG"

    local JSON
    JSON=$(curl -fsSL --get \
        --data-urlencode "game_versions=[\"$MC_VERSION\"]" \
        --data-urlencode 'loaders=["fabric"]' \
        "https://api.modrinth.com/v2/project/$SLUG/version")

    local VERSION_JSON

    if [ -n "$REQUIRED_VERSION" ]; then
        VERSION_JSON=$(echo "$JSON" | jq --arg version "$REQUIRED_VERSION" '[.[] | select(.version_number == $version)][0]')
    else
        VERSION_JSON=$(echo "$JSON" | jq '.[0]')
    fi

    if [ "$VERSION_JSON" = "null" ] || [ -z "$VERSION_JSON" ]; then
        abort "Nenhuma versão compatível encontrada para $SLUG."
    fi

    local MOD_NAME
    local MOD_VERSION
    local FILE_URL
    local FILE_NAME

    MOD_NAME=$(echo "$VERSION_JSON" | jq -r '.name')
    MOD_VERSION=$(echo "$VERSION_JSON" | jq -r '.version_number')
    FILE_URL=$(echo "$VERSION_JSON" | jq -r '((.files[] | select(.primary == true) | .url) // .files[0].url)')
    FILE_NAME=$(echo "$VERSION_JSON" | jq -r '((.files[] | select(.primary == true) | .filename) // .files[0].filename)')

    info "Instalando $MOD_NAME ($MOD_VERSION)"

    download_file "$FILE_URL" "$MODS_PATH/$FILE_NAME"
}

install_stack() {
    info "Instalando Atlas Stack..."

    ensure_stack_tools

    mkdir -p "$MODS_PATH"

    install_modrinth_mod "$FABRIC_API_SLUG"
    install_modrinth_mod "$COBBLEMON_SLUG" "$COBBLEMON_VERSION"
    install_modrinth_mod "$LITHIUM_SLUG"
    install_modrinth_mod "$FERRITECORE_SLUG"
    install_modrinth_mod "$MODERNFIX_SLUG"

    success "Atlas Stack instalada."
}