#!/usr/bin/env bash
# Allow Cloudflare IPs through UFW for HTTPS traffic. Requires sudo privileges.

# Exit on error, undefined variable, or pipe failure
set -euo pipefail

# Check for root privileges
[[ $EUID -ne 0 ]] && { echo "Error: This script must be run as root." >&2; exit 1; }

# Fetch Cloudflare IP ranges
echo "Fetching Cloudflare IP ranges..."
cf_ips="$(curl -fsSw '\n' https://www.cloudflare.com/ips-v{4,6})" || {
    echo "Error: Failed to fetch Cloudflare IP ranges." >&2
    exit 1
}

# Add UFW rules for each Cloudflare IP range
echo "Allowing Cloudflare IPs through UFW for port 443..."
for cfip in $cf_ips; do
    # Skip empty lines
    [ -n "$cfip" ] || continue
    # Basic validation: allow only characters valid in IP/CIDR (digits, hex, '.', ':', '/')
    case "$cfip" in
        (*[!0-9A-Fa-f.:/]*)
            # Unexpected characters, skip this line
            continue
            ;;
    esac
    # Add UFW rule to allow traffic from this Cloudflare IP to port 443
    ufw allow from "$cfip" proto tcp to any port 443 comment 'Cloudflare'
done

echo "Cloudflare IPs have been allowed through UFW for HTTPS traffic."