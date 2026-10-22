#!/usr/bin/env bash
set -eu
cd -- "$(dirname -- "$0")"
protocol=/usr/share/wayland-protocols/staging/ext-background-effect/ext-background-effect-v1.xml
wayland-scanner client-header "$protocol" background-effect-client.h
wayland-scanner private-code "$protocol" background-effect-protocol.c
cc -c background-effect-protocol.c $(pkg-config --cflags wayland-client) -o background-effect-protocol.o
qt_version="$(pkg-config --modversion Qt6Gui)"
qt_headers="$(pkg-config --variable=includedir Qt6Gui)"
g++ -std=c++17 -O2 -fPIC -pie main.cpp background-effect-protocol.o \
    -I"$qt_headers/QtGui/$qt_version" -I"$qt_headers/QtGui/$qt_version/QtGui" \
    -I"$qt_headers/QtCore/$qt_version" -I"$qt_headers/QtCore/$qt_version/QtCore" \
    $(pkg-config --cflags --libs Qt6Quick Qt6Qml Qt6Gui wayland-client) \
    -o dashboard-native
