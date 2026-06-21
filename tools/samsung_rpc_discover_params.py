#!/usr/bin/env python3
# samsung_rpc_discover_params.py
#
# Discover getter-like methods and setter parameter names.
#
# Token files are read from the same directory as this script:
#   samsung_ipctl_token_<host>_<port>.json
#
# Examples:
#   python3 samsung_rpc_discover_params.py --host 192.168.1.161
#   python3 samsung_rpc_discover_params.py --host 192.168.4.123 --openssl-seclevel1
#   python3 samsung_rpc_discover_params.py --host 192.168.4.123 --token "TOKEN" --openssl-seclevel1 --safe-setters --probe-param-names

import argparse
import json
import sys
import time
from typing import Any, Dict

from samsung_rpc_common import (
    SamsungJsonRpc,
    classify_response,
    compact,
    default_token_path,
    get_result,
    load_token,
)

DEFAULT_METHODS = [
    "artModeControl",
    "getTVStates",
    "getVideoStates",
    "powerControl",
    "remoteKeyControl",
    "directVolumeControl",
    "volumeUpDnControl",
    "muteControl",
    "channelUpDnControl",
    "directChannelControl",
    "inputSourceControl",
    "USBSourceControl",
    "externalSpeakerControl",
    "directAccessControl",
    "pictureModeControl",
    "pictureSizeControl",
    "soundModeControl",
    "speakerSelectControl",
    "contrastControl",
    "brightnessControl",
    "sharpnessControl",
    "colorControl",
    "tintControl",
    "RVUSourceControl",
    "ambientModeControl",
    "artmodeControl",
    "ArtModeControl",
]

SAFE_ECHO_SETTER_METHODS = {
    "artModeControl": ["artMode"],
    "directVolumeControl": ["volume"],
    "muteControl": ["mute"],
    "inputSourceControl": ["inputSource"],
    "pictureModeControl": ["pictureMode"],
    "pictureSizeControl": ["pictureSize"],
    "soundModeControl": ["soundMode"],
    "speakerSelectControl": ["speakerSelect"],
    "contrastControl": ["contrast"],
    "brightnessControl": ["brightness"],
    "sharpnessControl": ["sharpness"],
    "colorControl": ["color"],
    "tintControl": ["tint"],
    "powerControl": ["power"],
    "directAccessControl": ["applicationName"],
}

ALIAS_PARAM_NAMES = {
    "artModeControl": {"artMode": ["artMode", "mode", "status"]},
    "directVolumeControl": {"volume": ["volume", "Volume", "volumeLevel", "directVolume"]},
    "muteControl": {"mute": ["mute", "Mute", "status", "muteStatus"]},
    "inputSourceControl": {"inputSource": ["inputSource", "source", "input", "Source"]},
    "pictureModeControl": {"pictureMode": ["pictureMode", "mode", "PictureMode"]},
    "pictureSizeControl": {"pictureSize": ["pictureSize", "size", "PictureSize"]},
    "soundModeControl": {"soundMode": ["soundMode", "mode", "SoundMode"]},
    "speakerSelectControl": {"speakerSelect": ["speakerSelect", "speaker", "speakerType"]},
    "contrastControl": {"contrast": ["contrast", "value"]},
    "brightnessControl": {"brightness": ["brightness", "value"]},
    "sharpnessControl": {"sharpness": ["sharpness", "value"]},
    "colorControl": {"color": ["color", "value"]},
    "tintControl": {"tint": ["tint", "value"]},
    "powerControl": {"power": ["power", "status"]},
    "directAccessControl": {"applicationName": ["applicationName", "app", "appName"]},
}

PARAM_NAME_PROBES = {
    "remoteKeyControl": [
        ("remoteKey", "__invalid__"),
        ("key", "__invalid__"),
    ],
    "volumeUpDnControl": [
        ("control", "__invalid__"),
        ("volume", "__invalid__"),
    ],
    "channelUpDnControl": [
        ("control", "__invalid__"),
        ("channel", "__invalid__"),
    ],
    "directAccessControl": [
        ("applicationName", "__invalid__"),
        ("app", "__invalid__"),
        ("url", "about:blank"),
    ],
    "powerControl": [
        ("power", "__invalid__"),
        ("status", "__invalid__"),
    ],
}


def print_section(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def main() -> int:
    parser = argparse.ArgumentParser(description="Samsung TV JSON-RPC parameter discovery")
    parser.add_argument("--host", required=True, help="TV IP address")
    parser.add_argument("--port", type=int, default=1516)
    parser.add_argument("--token", help="AccessToken. If omitted, reads local token file next to script")
    parser.add_argument("--token-file", help="JSON or plain token file")
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--methods", help="Comma-separated method list")
    parser.add_argument("--safe-setters", action="store_true", help="Reapply current values to infer setter params")
    parser.add_argument("--probe-param-names", action="store_true", help="Probe selected param names with invalid values")
    parser.add_argument("--openssl-seclevel1", action="store_true", help="Equivalent to curl --ciphers DEFAULT:@SECLEVEL=1")
    parser.add_argument("--json-out", default="samsung_rpc_discovery_results.json")
    args = parser.parse_args()

    token = load_token(args.host, args.port, token=args.token, token_file=args.token_file)
    if not token:
        print("No token found.", file=sys.stderr)
        print(f"Expected local token file: {default_token_path(args.host, args.port)}", file=sys.stderr)
        print(f"Create one with: python3 samsung_rpc_token.py --host {args.host} --port {args.port}", file=sys.stderr)
        print("Or pass --token TOKEN", file=sys.stderr)
        return 2

    methods = [m.strip() for m in args.methods.split(",")] if args.methods else DEFAULT_METHODS
    methods = [m for m in methods if m]

    client = SamsungJsonRpc(
        host=args.host,
        port=args.port,
        token=token,
        timeout=args.timeout,
        openssl_seclevel1=args.openssl_seclevel1,
    )

    full_results: Dict[str, Any] = {
        "host": args.host,
        "port": args.port,
        "openssl_seclevel1": args.openssl_seclevel1,
        "methods": {},
        "summary": {},
    }

    print_section("1) Baseline calls: method with AccessToken only")
    baseline_results: Dict[str, Dict[str, Any]] = {}

    for method in methods:
        if args.delay:
            time.sleep(args.delay)

        try:
            res = client.request(method)
        except Exception as e:
            print(f"{method:30} EXCEPTION {e!r}")
            full_results["methods"].setdefault(method, {})["baseline_exception"] = repr(e)
            continue

        baseline_results[method] = res
        status, code, msg = classify_response(res)
        result = get_result(res)

        if status == "RESULT":
            print(f"{method:30} RESULT  {compact(result)}")
        elif status == "ERROR":
            print(f"{method:30} ERROR   code={code} msg={msg}")
        else:
            print(f"{method:30} OTHER   {compact(res.get('response'))}")

        full_results["methods"].setdefault(method, {})["baseline"] = res

    print_section("2) Inferred getter-like methods and fields")
    inferred_fields: Dict[str, Dict[str, Any]] = {}

    for method, res in baseline_results.items():
        result = get_result(res)
        if isinstance(result, dict) and result:
            inferred_fields[method] = dict(result)
            print(f"{method:30} fields={list(result.keys())} values={compact(result)}")

    if not inferred_fields:
        print("No getter-like result fields found.")

    full_results["summary"]["inferred_fields"] = inferred_fields

    if args.safe_setters:
        print_section("3) Safe setter echo tests: reapply current getter value")
        print("These calls may reapply current TV settings. They should be low-risk but are not purely read-only.")

        for method, fields in inferred_fields.items():
            allowed_fields = SAFE_ECHO_SETTER_METHODS.get(method, [])
            if not allowed_fields:
                continue

            for field in allowed_fields:
                if field not in fields:
                    continue

                current_value = fields[field]
                aliases = ALIAS_PARAM_NAMES.get(method, {}).get(field, [field])

                for param_name in aliases:
                    if args.delay:
                        time.sleep(args.delay)

                    params = {param_name: current_value}
                    try:
                        res = client.request(method, params)
                    except Exception as e:
                        print(f"{method:30} {compact(params):45} EXCEPTION {e!r}")
                        full_results["methods"].setdefault(method, {}).setdefault("safe_setter_tests", []).append(
                            {"params": params, "exception": repr(e)}
                        )
                        continue

                    status, code, msg = classify_response(res)
                    result = get_result(res)
                    if status == "RESULT":
                        print(f"{method:30} {compact(params):45} RESULT {compact(result)}")
                    elif status == "ERROR":
                        print(f"{method:30} {compact(params):45} ERROR code={code} msg={msg}")
                    else:
                        print(f"{method:30} {compact(params):45} OTHER {compact(res.get('response'))}")

                    full_results["methods"].setdefault(method, {}).setdefault("safe_setter_tests", []).append(res)

    if args.probe_param_names:
        print_section("4) Param name probes with invalid/null-ish values")
        print("Goal: detect -32602 Invalid params, which usually means method and param family exist.")
        print("Be careful: these are still real method calls.")

        for method, probes in PARAM_NAME_PROBES.items():
            if method not in methods and method not in baseline_results:
                continue

            for param_name, value in probes:
                if args.delay:
                    time.sleep(args.delay)

                params = {param_name: value}
                try:
                    res = client.request(method, params)
                except Exception as e:
                    print(f"{method:30} {compact(params):45} EXCEPTION {e!r}")
                    full_results["methods"].setdefault(method, {}).setdefault("param_name_probes", []).append(
                        {"params": params, "exception": repr(e)}
                    )
                    continue

                status, code, msg = classify_response(res)
                result = get_result(res)
                if status == "RESULT":
                    print(f"{method:30} {compact(params):45} RESULT {compact(result)}")
                elif status == "ERROR":
                    print(f"{method:30} {compact(params):45} ERROR code={code} msg={msg}")
                else:
                    print(f"{method:30} {compact(params):45} OTHER {compact(res.get('response'))}")

                full_results["methods"].setdefault(method, {}).setdefault("param_name_probes", []).append(res)

    print_section("5) Suggested mapping from observed results")
    for method, fields in inferred_fields.items():
        print(f"{method}:")
        print("  getter:")
        print("    params: AccessToken only")
        print(f"    returns: {list(fields.keys())}")
        if method in SAFE_ECHO_SETTER_METHODS:
            print("  possible_setter_params:")
            for field in SAFE_ECHO_SETTER_METHODS[method]:
                if field in fields:
                    aliases = ALIAS_PARAM_NAMES.get(method, {}).get(field, [field])
                    print(f"    {field}: aliases={aliases} current_value={fields[field]!r}")
        print()

    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(full_results, f, indent=2, ensure_ascii=False)

    print(f"Full results written to: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
