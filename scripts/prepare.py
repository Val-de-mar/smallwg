import os
import sys
import ipaddress
import argparse

# Global constants
DEFAULT_CONF_FILE_PATH = '/etc/wireguard/wg0.conf'

def panic(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)

def validate_inputs(subnet, listen_port, private_key):
    try:
        ipaddress.ip_network(subnet, strict=False)
    except ValueError:
        panic("Invalid subnet provided.")

    if not (0 < listen_port < 65536):
        panic("Invalid listen port provided. Must be between 1 and 65535.")

    if not private_key or len(private_key) != 44:  # WireGuard private keys are 44 characters long
        panic("Invalid private key provided.")

def check_existing_config(file_path):
    if os.path.exists(file_path):
        panic(f"Configuration file {file_path} already exists. Aborting to avoid overwrite.")

def generate_server_config(subnet, listen_port, private_key):
    # Generate the server's interface IP (first usable IP in the subnet)
    network = ipaddress.ip_network(subnet, strict=False)
    server_ip = str(next(network.hosts()))

    server_config = f"""
[Interface]
Address = {server_ip}/{network.prefixlen}
ListenPort = {listen_port}
PrivateKey = {private_key}
"""
    return server_config

def write_config_to_file(config, file_path):
    with open(file_path, 'w') as f:
        f.write(config)

def main():
    parser = argparse.ArgumentParser(description="Generate WireGuard server configuration.")
    parser.add_argument("--subnet", required=True, help="Subnet for the WireGuard server (e.g., 10.0.0.0/24)")
    parser.add_argument("--listen-port", type=int, required=True, help="Listen port for the WireGuard server (1-65535)")
    parser.add_argument("--private-key", required=True, help="Private key for the WireGuard server")
    parser.add_argument("--output-file", default=DEFAULT_CONF_FILE_PATH, help="Path to save the configuration file (default: /etc/wireguard/wg0.conf)")

    args = parser.parse_args()

    validate_inputs(args.subnet, args.listen_port, args.private_key)
    check_existing_config(args.output_file)

    server_config = generate_server_config(args.subnet, args.listen_port, args.private_key)

    write_config_to_file(server_config, args.output_file)

    print(f"Server configuration successfully written to {args.output_file}")

if __name__ == "__main__":
    main()
