#!/usr/bin/env python3
# samsung_rpc_token.py
#
# Request/create a Samsung JSON-RPC AccessToken and save it next to this script.
#
# Examples:
#   python3 samsung_rpc_token.py --host 192.168.1.161
#   python3 samsung_rpc_token.py --host 192.168.4.123 --openssl-seclevel1
#   python3 samsung_rpc_token.py --host 192.168.4.123 --port 1516 --openssl-seclevel1

import argparse

from samsung_rpc_common import (
    SamsungJsonRpc,
    default_token_path,
    find_token,
    print_json,
    save_token,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Samsung TV JSON-RPC AccessToken")
    parser.add_argument("--host", required=True, help="TV IP address")
    parser.add_argument("--port", type=int, default=1516, help="Default: 1516")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--openssl-seclevel1", action="store_true", help="Equivalent to curl --ciphers DEFAULT:@SECLEVEL=1")
    args = parser.parse_args()

    client = SamsungJsonRpc(
        host=args.host,
        port=args.port,
        token=None,
        timeout=args.timeout,
        openssl_seclevel1=args.openssl_seclevel1,
    )

    print(f"Calling createAccessToken on https://{args.host}:{args.port}/")
    print("If the TV shows an authorization prompt, accept it.")
    print(f"Token will be saved next to the script as: {default_token_path(args.host, args.port).name}")
    print()

    res = client.request("createAccessToken", include_token=False)
    print_json(res)

    token = find_token(res.get("response"))
    if not token:
        print()
        print("No AccessToken found in the response.")
        print("If the TV displayed a prompt, accept it and rerun the command.")
        return 1

    path = save_token(args.host, args.port, token)
    print()
    print(f"AccessToken saved to: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
