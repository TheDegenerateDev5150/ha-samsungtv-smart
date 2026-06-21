#!/usr/bin/env python3
# samsung_rpc_common.py
#
# Shared helpers for Samsung TV JSON-RPC over HTTPS.
#
# Key points:
# - Supports OpenSSL DH_KEY_TOO_SMALL workaround using DEFAULT:@SECLEVEL=1
# - Stores token files in the same directory as the scripts by default
# - No external Python dependency required

from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import ssl
from typing import Any, Dict, Optional


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def token_filename(host: str, port: int) -> str:
    return f"samsung_ipctl_token_{host}_{port}.json"


def default_token_path(host: str, port: int) -> Path:
    return script_dir() / token_filename(host, port)


def legacy_token_paths(host: str, port: int) -> list[Path]:
    # Compatibility with older script versions.
    return [
        script_dir() / f"samsung_ipctl_token_{host}.json",
        script_dir() / f"samsung_create_token_{host}_{port}.json",
        Path.home() / f".samsungtv_jsonrpc_{host}_{port}.token",
        Path("/tmp") / f"samsung_create_token_{host}_{port}.json",
    ]


def find_token(obj: Any) -> Optional[str]:
    """Find a token in common JSON shapes:
    - {"token": "..."}
    - {"AccessToken": "..."}
    - {"result": {"AccessToken": "..."}}
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in ("accesstoken", "access_token", "token") and isinstance(
                v, str
            ):
                return v.strip()
            found = find_token(v)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_token(item)
            if found:
                return found
    return None


def load_token_from_file(path: Path) -> Optional[str]:
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return None

    # JSON token file or JSON-RPC response
    try:
        obj = json.loads(text)
        token = find_token(obj)
        if token:
            return token
    except Exception:
        pass

    # Plain token file
    if "\n" not in text and len(text) >= 8:
        return text

    return None


def load_token(
    host: str, port: int, token: Optional[str] = None, token_file: Optional[str] = None
) -> Optional[str]:
    if token:
        return token.strip()

    if token_file:
        return load_token_from_file(Path(token_file).expanduser())

    paths = [default_token_path(host, port)] + legacy_token_paths(host, port)
    for path in paths:
        found = load_token_from_file(path)
        if found:
            return found

    return None


def save_token(host: str, port: int, token: str) -> Path:
    path = default_token_path(host, port)
    data = {
        "host": host,
        "port": port,
        "token": token,
    }
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    return path


def make_ssl_context(openssl_seclevel1: bool = False) -> ssl.SSLContext:
    # Similar to curl -k
    ctx = ssl._create_unverified_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    if openssl_seclevel1:
        # Python/OpenSSL equivalent of:
        #   curl --ciphers DEFAULT:@SECLEVEL=1
        # Needed by some Samsung TVs exposing weak DH params.
        try:
            ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        except ssl.SSLError:
            # Fallback for some OpenSSL builds.
            ctx.set_ciphers("ALL:@SECLEVEL=1")

    if hasattr(ctx, "minimum_version"):
        try:
            ctx.minimum_version = ssl.TLSVersion.TLSv1
        except Exception:
            pass

    return ctx


class SamsungJsonRpc:
    def __init__(
        self,
        host: str,
        port: int = 1516,
        token: Optional[str] = None,
        timeout: int = 10,
        openssl_seclevel1: bool = False,
    ):
        self.host = host
        self.port = port
        self.token = token
        self.timeout = timeout
        self._seclevel1 = openssl_seclevel1
        self.ssl_context = make_ssl_context(openssl_seclevel1)
        self._id = 0

    def next_id(self) -> int:
        self._id += 1
        return self._id

    def request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        include_token: bool = True,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self.next_id(),
            "method": method,
        }

        final_params: Dict[str, Any] = {}
        if include_token:
            if not self.token:
                raise ValueError("AccessToken is required for this request")
            final_params["AccessToken"] = self.token

        if params:
            final_params.update(params)

        if final_params:
            payload["params"] = final_params

        raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

        # Older Samsung TVs (e.g. 2020 / Tizen 5.5) expose weak DH params that
        # modern OpenSSL rejects with "dh key too small" unless the security
        # level is lowered (the Python equivalent of curl's
        # `--ciphers DEFAULT:@SECLEVEL=1`). Try normally first; on that specific
        # error, rebuild the context with SECLEVEL=1 and retry once — so the
        # tools work with OR without the --openssl-seclevel1 flag.
        for attempt in (0, 1):
            conn = http.client.HTTPSConnection(
                self.host,
                self.port,
                timeout=self.timeout,
                context=self.ssl_context,
            )
            try:
                conn.request(
                    "POST",
                    "/",
                    body=raw_body,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Content-Length": str(len(raw_body)),
                    },
                )
                resp = conn.getresponse()
                raw_response = resp.read().decode("utf-8", errors="replace")
                try:
                    parsed_response = json.loads(raw_response)
                except Exception:
                    parsed_response = raw_response

                return {
                    "http_status": resp.status,
                    "http_reason": resp.reason,
                    "request": payload,
                    "response": parsed_response,
                }
            except ssl.SSLError as ex:
                if (
                    attempt == 0
                    and not self._seclevel1
                    and "dh key too small" in str(ex).lower()
                ):
                    self._seclevel1 = True
                    self.ssl_context = make_ssl_context(True)
                    continue
                raise
            finally:
                conn.close()


def print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False))


def classify_response(res: Dict[str, Any]) -> tuple[str, Optional[int], str]:
    response = res.get("response")
    if isinstance(response, dict):
        if "result" in response:
            return "RESULT", None, ""
        if "error" in response:
            err = response.get("error") or {}
            if isinstance(err, dict):
                return "ERROR", err.get("code"), str(err.get("message", ""))
            return "ERROR", None, str(err)
    return "OTHER", None, repr(response)


def get_result(res: Dict[str, Any]) -> Optional[Any]:
    response = res.get("response")
    if isinstance(response, dict) and "result" in response:
        return response["result"]
    return None


def compact(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
