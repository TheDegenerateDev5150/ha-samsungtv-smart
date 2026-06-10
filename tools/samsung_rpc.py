#!/usr/bin/env python3
# samsung_rpc.py
#
# Generic Samsung JSON-RPC CLI.
#
# Token files are read from the same directory as this script:
#   samsung_ipctl_token_<host>_<port>.json
#
# Examples:
#   python3 samsung_rpc.py --host 192.168.1.161 state
#   python3 samsung_rpc.py --host 192.168.1.161 call artModeControl
#   python3 samsung_rpc.py --host 192.168.1.161 call artModeControl '{"artMode":"artModeOn"}'
#   python3 samsung_rpc.py --host 192.168.4.123 --openssl-seclevel1 call getTVStates
#   python3 samsung_rpc.py --host 192.168.4.123 --token "TOKEN" --openssl-seclevel1 call powerControl '{"power":"powerOff"}'

import argparse
import json
import sys

from samsung_rpc_common import SamsungJsonRpc, load_token, print_json, default_token_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Samsung TV JSON-RPC CLI")
    parser.add_argument("--host", required=True, help="TV IP address")
    parser.add_argument("--port", type=int, default=1516)
    parser.add_argument("--token", help="AccessToken. If omitted, reads local token file next to script")
    parser.add_argument("--token-file", help="JSON or plain token file")
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--openssl-seclevel1", action="store_true", help="Equivalent to curl --ciphers DEFAULT:@SECLEVEL=1")

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("state", help="Call getTVStates")
    sub.add_parser("video", help="Call getVideoStates")

    key_p = sub.add_parser("key", help="Send remoteKeyControl")
    key_p.add_argument("remote_key")

    call_p = sub.add_parser("call", help="Call any method with optional JSON params")
    call_p.add_argument("method")
    call_p.add_argument("params_json", nargs="?")

    args = parser.parse_args()

    token = load_token(args.host, args.port, token=args.token, token_file=args.token_file)
    if not token:
        print("No token found.", file=sys.stderr)
        print(f"Expected local token file: {default_token_path(args.host, args.port)}", file=sys.stderr)
        print("Create one with:", file=sys.stderr)
        print(f"  python3 samsung_rpc_token.py --host {args.host} --port {args.port}", file=sys.stderr)
        print("Or pass --token TOKEN", file=sys.stderr)
        return 2

    client = SamsungJsonRpc(
        host=args.host,
        port=args.port,
        token=token,
        timeout=args.timeout,
        openssl_seclevel1=args.openssl_seclevel1,
    )

    if args.cmd == "state":
        print_json(client.request("getTVStates"))
        return 0

    if args.cmd == "video":
        print_json(client.request("getVideoStates"))
        return 0

    if args.cmd == "key":
        print_json(client.request("remoteKeyControl", {"remoteKey": args.remote_key}))
        return 0

    if args.cmd == "call":
        params = None
        if args.params_json:
            try:
                params = json.loads(args.params_json)
                if not isinstance(params, dict):
                    raise ValueError("params_json must be a JSON object")
            except Exception as e:
                print(f"Invalid params_json: {e}", file=sys.stderr)
                return 3

        print_json(client.request(args.method, params))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
