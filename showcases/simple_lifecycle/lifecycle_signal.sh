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
# This script sends a signal to a process by name. It uses `slay` on QNX and `pkill` on other systems.
# Usage: lifecycle_signal.sh <process_name> <signal>
# Example: lifecycle_signal.sh my_process SIGTERM

running_on_qnx() {
    [ -x "$(command -v slay)" ]
}

process_name=$1
signal=$2

if running_on_qnx
then
    slay -s $signal -f $process_name
else
    # `pkill -f` matches against the whole command line, which also matches
    # this helper script itself (its own argv contains "$process_name"). That
    # made the script kill itself with the very signal it was sending, exiting
    # non-zero. Iterate the matches and skip our own PID so only the real
    # target process(es) get signalled. `-f` is still required because the
    # supervised binary names exceed the 15-char /proc/<pid>/comm limit.
    # `kill -s` in POSIX sh (dash) expects the signal name without the "SIG"
    # prefix (e.g. TERM, USR1), so strip it if present.
    for pid in $(pgrep -f "$process_name"); do
        [ "$pid" -eq "$$" ] && continue
        kill -s "${signal#SIG}" "$pid"
    done
fi
