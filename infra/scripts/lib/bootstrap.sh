#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/../../config"

source "$CONFIG_DIR/atlas.conf"
source "$CONFIG_DIR/stack.conf"

source "$SCRIPT_DIR/common.sh"
source "$SCRIPT_DIR/download.sh"
source "$SCRIPT_DIR/fabric.sh"
source "$SCRIPT_DIR/minecraft.sh"
source "$SCRIPT_DIR/postgres.sh"
source "$SCRIPT_DIR/stack.sh"