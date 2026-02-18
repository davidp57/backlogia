#!/bin/bash
# Trust Caddy's internal root CA on the host machine.
# This makes browsers accept the HTTPS certificate for backlogia.local
# without warnings, and enables PWA install support.
#
# Usage: ./scripts/trust-caddy-cert.sh
# (requires sudo for adding to the system trust store)

CERT_PATH="$(cd "$(dirname "$0")/.." && pwd)/data/caddy_data/caddy/pki/authorities/local/root.crt"

if [ ! -f "$CERT_PATH" ]; then
    echo "Root CA certificate not found at:"
    echo "  $CERT_PATH"
    echo ""
    echo "Start the containers first with: docker compose --profile https up -d"
    echo "Then re-run this script."
    exit 1
fi

OS="$(uname -s)"
case "$OS" in
    Darwin)
        echo "Adding Caddy root CA to macOS Keychain..."
        sudo security add-trusted-cert -d -r trustRoot \
            -k /Library/Keychains/System.keychain "$CERT_PATH"
        echo ""
        echo "Done! Restart your browser for the change to take effect."
        echo "https://backlogia.local should now show a valid certificate."
        ;;
    Linux)
        if [ -d /usr/local/share/ca-certificates ]; then
            echo "Adding Caddy root CA to system trust store..."
            sudo cp "$CERT_PATH" /usr/local/share/ca-certificates/backlogia-caddy.crt
            sudo update-ca-certificates
            echo ""
            echo "Done! Restart your browser for the change to take effect."
        else
            echo "Could not detect certificate trust directory."
            echo "Manually import this certificate into your browser:"
            echo "  $CERT_PATH"
        fi
        ;;
    MINGW*|MSYS*|CYGWIN*)
        # Convert to Windows path for certutil
        WIN_CERT_PATH="$(cygpath -w "$CERT_PATH" 2>/dev/null || echo "$CERT_PATH")"
        echo "Adding Caddy root CA to Windows certificate store..."
        echo "This requires an elevated (Administrator) terminal."
        certutil.exe -addstore -f Root "$WIN_CERT_PATH"
        echo ""
        echo "Done! Restart your browser for the change to take effect."
        echo "https://backlogia.local should now show a valid certificate."
        ;;
    *)
        echo "Unsupported OS: $OS"
        echo "Manually import this certificate into your browser:"
        echo "  $CERT_PATH"
        exit 1
        ;;
esac
