import os
import re
import subprocess
import sys
import ipaddress
import configparser

# Global constant for configuration file paths
CONFIG_FILE_PATH = '/wgconf/adduser.conf'
WG_CONFIG_PATH = '/etc/wireguard/wg0.conf'


def load_config(config_file_path):
    config = configparser.ConfigParser()
    config.read(config_file_path)
    return config


def get_existing_ips(wg_config_path):
    with open(wg_config_path, 'r') as f:
        data = f.read()
    # Find all existing IP addresses in the [Peer] sections
    existing_ips = re.findall(r'AllowedIPs\s*=\s*([\d\.:\./]+)', data)
    # Also include the IP in the [Interface] Address field
    interface_ips = re.findall(r'Address\s*=\s*([\d\.:\./]+)', data)
    existing_ips.extend(interface_ips)
    return [ip.split('/')[0] for ip in existing_ips]

def get_interface_subnets(wg_config_path):
    with open(wg_config_path, 'r') as f:
        data = f.read()
    # Find the subnets in the [Interface] section
    matches = re.findall(r'Address\s*=\s*([\d\.:\./]+)', data)
    ipv4_subnet = None
    ipv6_subnet = None

    for match in matches:
        network = ipaddress.ip_network(match, strict=False)
        if network.version == 4:
            ipv4_subnet = match
        elif network.version == 6:
            ipv6_subnet = match

    if not ipv4_subnet:
        raise ValueError("IPv4 subnet not found in the configuration file.")

    return ipv4_subnet, ipv6_subnet


def generate_random_ip(subnet, existing_ips):
    subnet = ipaddress.ip_network(subnet, strict=False)
    for ip in subnet.hosts():
        if str(ip) not in existing_ips:
            return str(ip)
    raise RuntimeError("No available IP addresses in the subnet.")

def append_peer_to_config(wg_config_path, username, public_key, ip_address, ipv6_address=None):
    peer_config = f"""
[Peer]
# {username}
PublicKey = {public_key}
AllowedIPs = {ip_address}/32
"""
    if ipv6_address:
        peer_config += f", {ipv6_address}/128"

    with open(wg_config_path, 'a') as f:
        f.write(peer_config)

def get_server_public_key(interface_name):
    try:
        result = subprocess.run(['wg', 'show', interface_name, 'public-key'], stdout=subprocess.PIPE, check=True)
        return result.stdout.decode('utf-8').strip()
    except subprocess.CalledProcessError:
        print("Failed to retrieve the server's public key.", file=sys.stderr)
        sys.exit(1)

def generate_client_config(ip_address, private_key, server_public_key, endpoint, dns_server, allowed_ips, persistent_keepalive, ipv6_address=None):
    client_config = f"""
[Interface]
PrivateKey = {private_key}
Address = {ip_address}/32
"""
    if ipv6_address:
        client_config += f", {ipv6_address}/128"

    client_config += f"""
# DNS = {dns_server}

[Peer]
PublicKey = {server_public_key}
Endpoint = {endpoint}
AllowedIPs = {allowed_ips}
PersistentKeepalive = {persistent_keepalive}
"""
    return client_config

def generate_key_pair():
    try:
        private_key_result = subprocess.run(['wg', 'genkey'], stdout=subprocess.PIPE, check=True)
        private_key = private_key_result.stdout.decode('utf-8').strip()

        public_key_result = subprocess.run(['wg', 'pubkey'], input=private_key.encode('utf-8'), stdout=subprocess.PIPE, check=True)
        public_key = public_key_result.stdout.decode('utf-8').strip()

        return private_key, public_key
    except subprocess.CalledProcessError:
        print("Failed to generate key pair.", file=sys.stderr)
        sys.exit(1)

def apply_changes_to_server(interface_name):
    try:
        # Use process substitution to pass the output of wg-quick strip to wg syncconf
        command = f"wg syncconf {interface_name} <(wg-quick strip {interface_name})"
        subprocess.run(command, shell=True, check=True, executable='/bin/bash')
        print(f"Configuration successfully applied to {interface_name}.", file=sys.stderr)
    except subprocess.CalledProcessError:
        print(f"Failed to apply configuration to {interface_name}.", file=sys.stderr)
        sys.exit(1)

def main():
    # Load the configuration from /wgconf/adduser.conf
    config = load_config(CONFIG_FILE_PATH)
    
    WG_INTERFACE_NAME = config['DEFAULT'].get('WG_INTERFACE_NAME', 'wg0')
    DNS_SERVER = config['DEFAULT'].get('DNS_SERVER', '8.8.8.8')
    ENDPOINT = config['DEFAULT']['ENDPOINT']
    ALLOWED_IPS = config['DEFAULT'].get('ALLOWED_IPS', '0.0.0.0/0')
    PERSISTENT_KEEPALIVE = config['DEFAULT'].getint('PERSISTENT_KEEPALIVE', 21)

    print("Do you want to generate a new key pair for the client? (yes/no): ", file=sys.stderr, end="")
    generate_keys = input().strip().lower()

    if generate_keys in {'yes', 'y', 'Y'}:
        print("Enter the username: ", file=sys.stderr, end="")
        username = input()
        private_key, public_key = generate_key_pair()
    else:
        print("Enter the username: ", file=sys.stderr, end="")
        username = input()
        print("Enter the public key: ", file=sys.stderr, end="")
        public_key = input()
        private_key = "[your private key]"

    existing_ips = get_existing_ips(WG_CONFIG_PATH)
    ipv4_subnet, ipv6_subnet = get_interface_subnets(WG_CONFIG_PATH)
    

    ip_address = generate_random_ip(ipv4_subnet, existing_ips)
    ipv6_address = generate_random_ip(ipv6_subnet, existing_ips) if ipv6_subnet else None
    
    # Append the new peer to the configuration file
    append_peer_to_config(WG_CONFIG_PATH, username, public_key, ip_address, ipv6_address)
    
    # Get the server's public key from the wg0 interface
    server_public_key = get_server_public_key(WG_INTERFACE_NAME)

    # Generate the client configuration
    client_config = generate_client_config(ip_address, private_key, server_public_key, ENDPOINT, DNS_SERVER, ALLOWED_IPS, PERSISTENT_KEEPALIVE, ipv6_address)

    # Print a message to stderr and then the configuration to stdout
    print(f"\nGenerated client configuration:", file=sys.stderr)
    print(client_config)

    # Apply the changes to the running WireGuard interface
    apply_changes_to_server(WG_INTERFACE_NAME)

if __name__ == "__main__":
    main()
