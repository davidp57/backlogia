#!/bin/sh

# Start dbus and avahi in background (for Linux hosts)
mkdir -p /run/dbus
dbus-daemon --system 2>/dev/null || true
avahi-daemon --no-drop-root --daemonize 2>/dev/null || true

# Run caddy
exec "$@"
