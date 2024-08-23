#!/bin/bash

# Path to the WireGuard configuration file
WG_CONF="/etc/wireguard/wg0.conf"

# Path to the preparation script (generate_wg_server_config.py)
PREPARE_SCRIPT="/data/prepare.py"

# Arguments for the preparation script
SUBNET="10.73.34.0/24"
LISTEN_PORT="12001"

# Check if the WireGuard configuration file exists
if [ ! -f "$WG_CONF" ]; then
    echo "WireGuard configuration file not found. Running preparation script..."
    python3 "$PREPARE_SCRIPT" --subnet "$SUBNET" --listen-port "$LISTEN_PORT"  --output-file "$WG_CONF"
    
    # Check again to ensure the preparation script succeeded in creating the config file
    if [ ! -f "$WG_CONF" ]; then
        echo "Error: Configuration file $WG_CONF was not created by the preparation script."
        exit 1
    fi
fi

# Start the WireGuard interface
echo "Starting WireGuard interface wg0..."
wg-quick up wg0 &&
bash /data/slp.sh