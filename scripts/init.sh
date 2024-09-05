#!/bin/bash

# Path to the preparation script (generate_wg_server_config.py)
PREPARE_SCRIPT="/data/prepare.py"

# Path to the configuration file
CONFIG_FILE="/wgconf/prepare.conf"

# Load the configuration from /wgconf/prepare.conf
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file $CONFIG_FILE not found."
    exit 1
fi

# Source the configuration file to load SUBNET, LISTEN_PORT, WG_CONF, and optionally PRIVATE_KEY, IPV6_SUBNET
source "$CONFIG_FILE"

# Ensure SUBNET, LISTEN_PORT, and WG_CONF are set
if [ -z "$SUBNET" ] || [ -z "$LISTEN_PORT" ] || [ -z "$WG_CONF" ]; then
    echo "Error: SUBNET, LISTEN_PORT, and WG_CONF must be set in $CONFIG_FILE."
    exit 1
fi

# Prepare the command arguments
ARGS="--subnet \"$SUBNET\" --listen-port \"$LISTEN_PORT\" --output-file \"$WG_CONF\""

# If PRIVATE_KEY is set, add it to the arguments
if [ -n "$PRIVATE_KEY" ]; then
    ARGS="$ARGS --private-key \"$PRIVATE_KEY\""
fi

# If IPV6_SUBNET is set, add it to the arguments
if [ -n "$IPV6_SUBNET" ]; then
    ARGS="$ARGS --ipv6-subnet \"$IPV6_SUBNET\""
fi

# Check if the WireGuard configuration file exists
if [ ! -f "$WG_CONF" ]; then
    echo "WireGuard configuration file not found. Running preparation script..."
    eval "python3 \"$PREPARE_SCRIPT\" $ARGS"
    
    # Check again to ensure the preparation script succeeded in creating the config file
    if [ ! -f "$WG_CONF" ]; then
        echo "Error: Configuration file $WG_CONF was not created by the preparation script."
        exit 1
    fi
fi

# Check if PROHIBIT_SUBNETS is set
if [[ -n "$PROHIBIT_SUBNETS" ]]; then
    # Split the PROHIBIT_SUBNETS into an array using ',' as a delimiter
    IFS=',' read -r -a subnets <<< "$PROHIBIT_SUBNETS"

    # Loop through each subnet in the array
    for subnet in "${subnets[@]}"; do
        # Check if iptables rule for this subnet already exists
        if ! iptables -C FORWARD -i wg0 -d "$subnet" -j REJECT 2>/dev/null; then
            # If the rule does not exist, add it
            iptables -A FORWARD -i wg0 -d "$subnet" -j REJECT
            echo "Rule added for subnet: $subnet"
        else
            echo "Rule already exists for subnet: $subnet"
        fi
    done
else
    echo "PROHIBIT_SUBNETS is not set or is empty."
fi

# Start the WireGuard interface
echo "Starting WireGuard interface wg0..."
wg-quick up wg0 &&
bash /data/slp.sh
