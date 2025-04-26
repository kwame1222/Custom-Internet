# SSH-over-WebSocket with SOCKS Proxy (Supports payloads & SNI fronting)

This project demonstrates tunneling SSH through a WebSocket “proxy” endpoint, then exposing a local SOCKS4/5 proxy. Applications can connect to `127.0.0.1:1080` (by default), and all traffic is forwarded over SSH via a remote WebSocket gateway. It now supports three tunnel modes (direct, HTTP payload, and SNI domain fronting) for maximum flexibility.

## Features

- **WebSocket Handshake**: Performs a custom HTTP/WebSocket handshake with a proxy (`ws_tunnel.py`).
- **SSH-over-WebSocket**: Uses Paramiko to authenticate to a remote SSH server once the tunnel is established.
- **Local SOCKS Proxy**: Exposes a SOCKS4/5 listener on your local machine. All incoming connections route through SSH.
- **Flexible Tunnel Modes**: Choose between:
  - **direct**: Plain TCP straight to target
  - **http_payload**: Plain TCP to proxy+custom upgrade payload
  - **sni_fronted**: TLS to proxy with SNI domain fronting, then upgrade payload

## How It Works

1. **Strategy Selection**  
   - Based on `CONFIG['MODE']`, `main.py` picks one of three strategies (in `tunnel_strategies.py`) to establish the underlying socket.

2. **WebSocket Connection**  
   - `ws_tunnel.py` (called by the strategy) connects to the proxy and sends the WebSocket / HTTP upgrade handshake defined in `CONFIG['PAYLOAD_TEMPLATE']`.  
   - On success (`101 Switching Protocols` or equivalent), the socket is left in raw mode.

3. **SSH Transport**  
   - The raw socket is handed to `paramiko.Transport`, which starts the SSH client.  
   - Authentication uses `SSH_USERNAME` and `SSH_PASSWORD`.

4. **SOCKS Proxy**  
   - `ssh_connector.py` opens a SOCKS4/5 proxy on `CONFIG['LOCAL_SOCKS_PORT']`.  
   - Each incoming SOCKS connection is mapped to a Paramiko "direct-tcpip" channel, forwarding traffic through SSH.

## Project Structure

```
.
├── config.py            # Configuration (hosts, ports, credentials, mode, front domain)
├── .gitignore
├── main.py              # Entry point: selects strategy, sets up tunnel, starts SSH & SOCKS
├── project_dump.txt     # Example data or logs
├── README.md            # (This file)
├── ssh_connector.py     # SSHTransport + SOCKS server implementation
├── ws_tunnel.py         # HTTP/WebSocket handshake & raw socket creation
└── tunnel_strategies.py # Strategy pattern for direct/http_payload/sni_fronted
```

## Configuration

All user-configurable values are in **`config.py`**:
```python
CONFIG = {
    'LOCAL_SOCKS_PORT': 1080,        # SOCKS listener port

    'PROXY_HOST': '',                # WebSocket/HTTP proxy endpoint
    'PROXY_PORT': 80,

    'TARGET_HOST': '',               # SSH-over-WS gateway behind the proxy
    'TARGET_PORT': 80,

    'SSH_USERNAME': '',              # SSH auth credentials
    'SSH_PASSWORD': '',
    'SSH_PORT': 22,                  # Internal SSH port (usually 22)

    'PAYLOAD_TEMPLATE': (            # HTTP/WS upgrade string with placeholders
        "GET / HTTP/1.1[crlf]Host: example.website[crlf]"
        "Expect: 100-continue[crlf][crlf]"
        "GET / HTTP/1.1[crlf]Host: [host][crlf]Upgrade: websocket[crlf][crlf]"
    ),

    'MODE': 'http_payload',          # tunnel mode: direct | http_payload | sni_fronted
    'FRONT_DOMAIN': '',              # used only when MODE='sni_fronted'
}
```

| Key                 | Description                                                                                                              |
|---------------------|--------------------------------------------------------------------------------------------------------------------------|
| `LOCAL_SOCKS_PORT`  | Port on which the local SOCKS proxy will listen (default 1080).                                                         |
| `PROXY_HOST`        | Hostname or IP for the WebSocket/HTTP proxy.                                                                            |
| `PROXY_PORT`        | Port for the proxy (e.g., 80 or 443).                                                                                   |
| `TARGET_HOST`       | The SSH-over-WebSocket gateway address (behind the proxy).                                                              |
| `TARGET_PORT`       | The port on the gateway for WebSocket upgrade (not the SSH port).                                                       |
| `SSH_USERNAME`      | SSH username for Paramiko authentication.                                                                               |
| `SSH_PASSWORD`      | SSH password for Paramiko authentication.                                                                               |
| `SSH_PORT`          | The "internal" SSH port used by Paramiko once the tunnel is established.                                               |
| `PAYLOAD_TEMPLATE`  | The HTTP/WebSocket upgrade string. `[host]` → `TARGET_HOST:TARGET_PORT`; `[crlf]` → `\r\n`.                           |
| `MODE`              | Selects the tunnel strategy:                                                                                             |
|                     | • `direct`      — TCP straight to `TARGET_HOST:TARGET_PORT`                                                               |
|                     | • `http_payload`— Plain TCP to `PROXY_HOST` + custom HTTP/WS payload                                                     |
|                     | • `sni_fronted` — TLS to `PROXY_HOST` with SNI=`FRONT_DOMAIN`, then HTTP/WS payload                                     |
| `FRONT_DOMAIN`      | Domain to use for SNI when `MODE='sni_fronted'` (falls back to `PROXY_HOST` if empty).                                  |

## Installation & Dependencies

- **Python 3.7+** recommended  
- [**Paramiko**](https://pypi.org/project/paramiko/) for SSH  
- Standard library (`socket`, `threading`, `ssl`, etc.)

Install Paramiko:
```bash
pip install paramiko
```

## Usage

1. **Configure**: Edit `config.py` with the correct hosts, ports, credentials, `MODE`, and—if using SNI fronting—`FRONT_DOMAIN`.
2. **Run**:
   ```bash
   python main.py
   ```
3. **Use the SOCKS Proxy**: Once running, you’ll see:
   ```
   [*] WebSocket handshake done. Returning raw socket.
   [*] SSH transport established and authenticated.
   [*] SOCKS proxy listening on 127.0.0.1:1080
   [+] SOCKS proxy up on 127.0.0.1:1080
   [+] All traffic through that proxy is forwarded over SSH via WS tunnel.
   ```
   - Configure your application or browser to use **SOCKS5** (or **SOCKS4**) at `127.0.0.1:1080`.

## Tor/Browser Configuration

If you want to route Tor through this SOCKS proxy:

1. Start this program first.
2. In Tor Browser settings → Network, set a custom proxy:
   - **SOCKS5**
   - Address: `127.0.0.1`
   - Port: `1080`

The enhanced SOCKS4/5 logic in `ssh_connector.py` handles DNS and domain lookups properly.

## Troubleshooting

- **Authentication Failure**: Verify your SSH credentials or server settings.
- **Handshake Fails**: Ensure your `PAYLOAD_TEMPLATE` matches the proxy’s requirements, and check console output for HTTP response details.
- **Connection Refused**: Confirm access to the proxy and gateway (e.g., port 443/TLS vs. port 80).
- **Timeout or No Data**: Check firewall/NAT rules and any advanced handshake needs.

## Contributing

1. Fork the repo  
2. Make changes / add features (e.g. new `TunnelStrategy`)  
3. Open a Pull Request

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).