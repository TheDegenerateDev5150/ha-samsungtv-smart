# Samsung JSON-RPC tools — DH fix + local token files

This pack replaces the previous scripts.

Changes:
- Adds `--openssl-seclevel1`, equivalent to curl `--ciphers DEFAULT:@SECLEVEL=1`.
- Token files are stored/read from the same directory as the scripts.
- Fixes token-file discovery.
- Keeps port `1516` as default. Use `1515` only if your TV actually responds there.

## Files

```text
samsung_rpc_common.py
samsung_rpc_token.py
samsung_rpc.py
samsung_rpc_discover_params.py
samsung_rpc_token.sh
```

## 1. Install

```sh
unzip samsung_jsonrpc_tools_dhfix_localtoken.zip
cd samsung_jsonrpc_tools_dhfix_localtoken
chmod +x samsung_rpc_token.py samsung_rpc.py samsung_rpc_discover_params.py samsung_rpc_token.sh
```

## 2. Create token — Python

For a normal TV:

```sh
python3 samsung_rpc_token.py --host 192.168.1.161
```

For a TV that raises `DH_KEY_TOO_SMALL`:

```sh
python3 samsung_rpc_token.py --host 192.168.4.yyy --openssl-seclevel1
```

The token is saved next to the scripts:

```text
samsung_ipctl_token_<host>_<port>.json
```

Example:

```text
samsung_ipctl_token_192.168.4.yyy_1516.json
```

## 3. Create token — curl shell helper

Normal:

```sh
./samsung_rpc_token.sh 192.168.1.161
```

With OpenSSL security level 1:

```sh
./samsung_rpc_token.sh 192.168.4.yyy 1516 seclevel1
```

## 4. Test calls

```sh
python3 samsung_rpc.py --host 192.168.1.161 state
python3 samsung_rpc.py --host 192.168.1.161 call artModeControl
python3 samsung_rpc.py --host 192.168.1.161 call artModeControl '{"artMode":"artModeOn"}'
python3 samsung_rpc.py --host 192.168.1.161 call artModeControl '{"artMode":"artModeOff"}'
```

With DH fix:

```sh
python3 samsung_rpc.py --host 192.168.4.yyy --openssl-seclevel1 state
python3 samsung_rpc.py --host 192.168.4.yyy --openssl-seclevel1 call artModeControl
```

## 5. Discovery

Read-only baseline:

```sh
python3 samsung_rpc_discover_params.py --host 192.168.1.161
```

With DH fix:

```sh
python3 samsung_rpc_discover_params.py --host 192.168.4.yyy --openssl-seclevel1
```

Full discovery:

```sh
python3 samsung_rpc_discover_params.py \
  --host 192.168.4.yyy \
  --openssl-seclevel1 \
  --safe-setters \
  --probe-param-names
```

## 6. Use an explicit token

```sh
python3 samsung_rpc_discover_params.py \
  --host 192.168.4.yyy \
  --token "U5...5N" \
  --openssl-seclevel1
```

## 7. Correct curl examples

Create token:

```sh
curl -k -m 5 "https://192.168.4.yyy:1516/" \
  --json '{"jsonrpc":"2.0","id":1,"method":"createAccessToken"}' \
  --ciphers 'DEFAULT:@SECLEVEL=1'
```

Power off — note the required `AccessToken` key:

```sh
curl -k -m 5 "https://192.168.4.yyy:1516/" \
  --json '{"jsonrpc":"2.0","id":1,"method":"powerControl","params":{"AccessToken":"U5...5N","power":"powerOff"}}' \
  --ciphers 'DEFAULT:@SECLEVEL=1'
```

Incorrect:

```json
"params":{"U5...5N","power":"powerOff"}
```

Correct:

```json
"params":{"AccessToken":"U5...5N","power":"powerOff"}
```
