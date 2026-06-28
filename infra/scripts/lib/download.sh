#!/bin/bash

download_file() {
    local URL="$1"
    local OUTPUT_FILE="$2"

    if [ -z "$URL" ]; then
        abort "URL não informada para download."
    fi

    if [ -z "$OUTPUT_FILE" ]; then
        abort "Nome do arquivo de saída não informado."
    fi

    if [ -f "$OUTPUT_FILE" ]; then
        success "Arquivo já existe: $OUTPUT_FILE"
        return
    fi

    info "Baixando: $OUTPUT_FILE"

    if wget -q --show-progress "$URL" -O "$OUTPUT_FILE"; then
        success "Download concluído: $OUTPUT_FILE"
    else
        rm -f "$OUTPUT_FILE"
        abort "Falha ao baixar: $URL"
    fi
}