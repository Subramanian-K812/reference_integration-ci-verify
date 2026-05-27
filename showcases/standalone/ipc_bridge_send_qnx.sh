#! /bin/sh
# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

LOLA_DISCOVERY_ROOT=/var/data/tmp_discovery/mw_com_lola
LOLA_SERVICE_DISCOVERY_DIR="$LOLA_DISCOVERY_ROOT/service_discovery"
LOLA_SERVICE_ID_DIR="$LOLA_SERVICE_DISCOVERY_DIR/6432"
LOLA_INSTANCE_DIR="$LOLA_SERVICE_ID_DIR/1"

running_on_qnx() {
    [ -x "$(command -v slay)" ]
}

prepare_qnx_lola_tree() {
    rm -rf "$LOLA_DISCOVERY_ROOT"
    mkdir -p "$LOLA_INSTANCE_DIR"
    chmod 755 "$LOLA_DISCOVERY_ROOT"
    chmod 755 "$LOLA_SERVICE_DISCOVERY_DIR"
    chmod 777 "$LOLA_SERVICE_ID_DIR"
    chmod 777 "$LOLA_INSTANCE_DIR"
}

if running_on_qnx
then
    prepare_qnx_lola_tree
fi

exec /mnt/showcases/bin/ipc_bridge_cpp "$@"
