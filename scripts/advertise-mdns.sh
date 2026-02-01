#!/bin/bash
# Advertise backlogia.local on macOS using Bonjour
# This is needed because Docker on macOS runs in a VM and can't broadcast mDNS directly
#
# Usage: ./scripts/advertise-mdns.sh
# Stop with Ctrl+C

echo "Advertising backlogia.local on port 443..."
echo "Access from any device on your network at: https://backlogia.local"
echo "Press Ctrl+C to stop"
echo ""

# Register the service - this keeps running until killed
dns-sd -P backlogia _https._tcp local 443 backlogia.local $(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
