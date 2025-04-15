# SSH-over-WebSocket with SOCKS Proxy (Supports payloads)

This project demonstrates tunneling SSH through a WebSocket “proxy” endpoint, then exposing a local SOCKS4/5 proxy. Applications can connect to `127.0.0.1:1080` (by default), and all traffic is forwarded over SSH via a remote WebSocket gateway.

## Features

- **WebSocket Handshake**: Performs a custom HTTP/WebSocket handshake with a proxy (`ws_tunnel.py`).
- **SSH-over-WebSocket**: Uses Paramiko to authenticate to a remote SSH server once the tunnel is established.
- **Local SOCKS Proxy**: Exposes a SOCKS4/5 listener on your local machine. All incoming connections route through SSH.

## How It Works

1. **WebSocket Connection**  
   - `ws_tunnel.py` connects to `PROXY_HOST:PROXY_PORT` and sends the specified WebSocket handshake headers (as defined in `CONFIG['PAYLOAD_TEMPLATE']`).
   - The server (or proxy) responds with `101 Switching Protocols` or a similar success status, upgrading the socket to a raw TCP connection.

2. **SSH Transport**  
   - Once the WebSocket is “upgraded,” we hand the raw socket to `paramiko.Transport`, which starts the SSH client. 
   - We authenticate using `SSH_USERNAME` and `SSH_PASSWORD`.

3. **SOCKS Proxy**  
   - `ssh_connector.py` opens a SOCKS proxy on `LOCAL_SOCKS_PORT` (1080 by default).
   - Each SOCKS connection is translated to a Paramiko “direct-tcpip” channel, which routes through the SSH connection.

## Project Structure

```
.
├── config.py         # Contains the CONFIG dict with your connection settings
├── .gitignore
├── main.py           # Entry point: sets up WS tunnel, starts SSH, starts SOCKS
├── project_dump.txt  # Example data or logs
├── README.md         # (This file)
├── ssh_connector.py  # Contains the SSHOverWebSocket class & the SOCKS server logic
└── ws_tunnel.py      # WebSocket handshake and raw socket creation
```

## Configuration

All user-configurable values are in **`config.py`**:
```python
CONFIG = {
    'LOCAL_SOCKS_PORT': 1080,
    'PROXY_HOST': '',
    'PROXY_PORT': 80,
    'TARGET_HOST': '',
    'TARGET_PORT': 80,
    'SSH_USERNAME': '',
    'SSH_PASSWORD': '',
    'SSH_PORT': 22,
    'PAYLOAD_TEMPLATE': ( #example payload
        "GET / HTTP/1.1[crlf]Host: example.webiste[crlf]"
        "Expect: 100-continue[crlf][crlf]"
        "GET- / HTTP/1.1[crlf]Host: [host][crlf]Upgrade: Websocket[crlf][crlf]"
    ),
}
```

| Key                 | Description                                                                                                              |
|---------------------|--------------------------------------------------------------------------------------------------------------------------|
| `LOCAL_SOCKS_PORT` | Port on which the local SOCKS proxy will listen (default 1080).                                                           |
| `PROXY_HOST`        | Hostname or IP for the **WebSocket/HTTP proxy** that performs the actual upgrade.                                        |
| `PROXY_PORT`        | Port for the proxy (e.g., 80 or 443).                                                                                    |
| `TARGET_HOST`       | The real SSH-over-WebSocket gateway address (behind the proxy).                                                          |
| `TARGET_PORT`       | The port on the gateway for WebSocket upgrade (not the SSH port; e.g., 80).                                              |
| `SSH_USERNAME`      | SSH username for Paramiko authentication.                                                                                |
| `SSH_PASSWORD`      | SSH password for Paramiko authentication.                                                                                |
| `SSH_PORT`          | The “internal” SSH port used by Paramiko once the tunnel is established (often 22, but can differ depending on the setup).|
| `PAYLOAD_TEMPLATE`  | The HTTP/WebSocket upgrade string. `[host]` is replaced by `TARGET_HOST:TARGET_PORT`; `[crlf]` is replaced by `\r\n`.     |

## Installation & Dependencies

- **Python 3.7+** recommended
- [**Paramiko**](https://pypi.org/project/paramiko/) for SSH
- Standard library modules (`socket`, `threading`, etc.)

Install Paramiko:
```bash
pip install paramiko
```

## Usage

1. **Configure**: Edit `config.py` with the correct hosts, ports, and credentials for your environment.
2. **Run**: 
   ```bash
   python main.py
   ```
3. **Use the SOCKS Proxy**: Once running, you’ll see something like:
   ```
   [*] WebSocket handshake done. Returning raw socket.
   [*] SSH transport established and authenticated.
   [*] SOCKS proxy listening on 127.0.0.1:1080
   [+] SOCKS proxy up on 127.0.0.1:1080
   [+] All traffic through that proxy is forwarded over SSH via WS tunnel.
   ```
   - Configure your application or browser to use **SOCKS5** (or **SOCKS4**) at `127.0.0.1:1080`.
   - All connections will then be relayed through the SSH-over-WebSocket tunnel.

## Tor/Browser Configuration

If you want to route Tor through this SOCKS proxy:
1. Start this program first.
2. In your Tor settings (e.g., Tor Browser → Preferences → Network), set a custom proxy:
   - SOCKS 5
   - Address: `127.0.0.1`
   - Port: `1080`
3. Tor will attempt to do DNS resolution or domain lookups through the tunnel. The updated, more complete SOCKS4/5 logic in `ssh_connector.py` handles this properly.

## Troubleshooting

- **Authentication Failure**: Check `SSH_USERNAME` and `SSH_PASSWORD` or see if the remote server has additional auth requirements.
- **WebSocket Handshake Fails**: Verify your `PAYLOAD_TEMPLATE` matches what the proxy requires. Watch the console output for the exact HTTP response.
- **Connection Refused**: Ensure the remote host/port is accessible. Some proxies require TLS (port 443) or other special headers.
- **Timeout or No Data**: Firewall or NAT might be blocking the tunnel. Double-check networking and any advanced handshake details.

## Contributing

1. Fork the repo
2. Make changes / add features
3. Open a Pull Request

