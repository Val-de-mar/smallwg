import os
import sys
import ipaddress
import argparse
import subprocess

# Global constants
DEFAULT_CONF_FILE_PATH = '/etc/wireguard/wg0.conf'

def panic(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)

def validate_inputs(subnet, listen_port):
    try:
        ipaddress.ip_network(subnet, strict=False)
    except ValueError:
        panic("Invalid subnet provided.")

    if not (0 < listen_port < 65536):
        panic("Invalid listen port provided. Must be between 1 and 65535.")

def check_existing_config(file_path):
    if os.path.exists(file_path):
        panic(f"Configuration file {file_path} already exists. Aborting to avoid overwrite.")

def generate_private_key():
    try:
        private_key_result = subprocess.run(['wg', 'genkey'], stdout=subprocess.PIPE, check=True)
        private_key = private_key_result.stdout.decode('utf-8').strip()
        return private_key
    except subprocess.CalledProcessError:
        panic("Failed to generate private key.")

def generate_server_config(subnet, listen_port, private_key):
    # Generate the server's interface IP (first usable IP in the subnet)
    network = ipaddress.ip_network(subnet, strict=False)
    server_ip = str(next(network.hosts()))

    # Define PreUp, PostUp, PreDown, and PostDown commands
    pre_up = "echo 'Running PreUp tasks...'"
    post_up = "iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE"
    pre_down = "echo 'Running PreDown tasks...'"
    post_down = "iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE"

    server_config = f"""
[Interface]
Address = {server_ip}/{network.prefixlen}
ListenPort = {listen_port}
PrivateKey = {private_key}

# Commands to run before/after the interface is brought up/down
PreUp = {pre_up}
PostUp = {post_up}
PreDown = {pre_down}
PostDown = {post_down}
"""
    return server_config

def write_config_to_file(config, file_path):
    with open(file_path, 'w') as f:
        f.write(config)
    # Set file permissions to be readable and writable by the owner only
    os.chmod(file_path, 0o600)

def main():
    parser = argparse.ArgumentParser(description="Generate WireGuard server configuration.")
    parser.add_argument("--subnet", required=True, help="Subnet for the WireGuard server (e.g., 10.0.0.0/24)")
    parser.add_argument("--listen-port", type=int, required=True, help="Listen port for the WireGuard server (1-65535)")
    parser.add_argument("--private-key", help="Private key for the WireGuard server (if not provided, a new key will be generated)")
    parser.add_argument("--output-file", default=DEFAULT_CONF_FILE_PATH, help="Path to save the configuration file (default: /etc/wireguard/wg0.conf)")

    args = parser.parse_args()

    validate_inputs(args.subnet, args.listen_port)

    # Generate a private key if one is not provided
    if not args.private_key:
        print("No private key provided. Generating a new private key...", file=sys.stderr)
        private_key = generate_private_key()
    else:
        private_key = args.private_key

    check_existing_config(args.output_file)

    server_config = generate_server_config(args.subnet, args.listen_port, private_key)

    write_config_to_file(server_config, args.output_file)

    print(f"Server configuration successfully written to {args.output_file}")

if __name__ == "__main__":
    main()
