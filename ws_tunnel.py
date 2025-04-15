import socket

def replace_placeholders(payload, target_host, target_port):
    """
    Replace [host] with 'target_host:target_port'
    and [crlf] with '\r\n' in the payload template.
    Return as bytes.
    """
    host_value = f"{target_host}:{target_port}"
    payload = payload.replace("[host]", host_value)
    payload = payload.replace("[crlf]", "\r\n")
    return payload.encode()

def read_headers(sock):
    """
    Read from 'sock' until we reach a blank line (\r\n\r\n).
    Return the full headers as bytes, including the final \r\n\r\n.
    """
    response = b""
    while b"\r\n\r\n" not in response:
        chunk = sock.recv(1)
        if not chunk:
            break
        response += chunk
    return response

def establish_ws_tunnel(proxy_host, proxy_port, target_host, target_port, payload_template):
    """
    Connect to the proxy, perform the WebSocket (or HTTP) handshake to
    get a raw TCP tunnel, then return the connected socket.
    Raise an exception on failure.
    """
    # 1. Create a TCP socket to the proxy
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((proxy_host, proxy_port))

    # 2. Construct the handshake payload
    payload = replace_placeholders(payload_template, target_host, target_port)
    # Possibly there are multiple "blocks" separated by double-CRLF
    payload_parts = payload.split(b"\r\n\r\n")

    # 3. Send the first block
    sock.sendall(payload_parts[0] + b"\r\n\r\n")

    # 4. Read first response (should hopefully see "100 Continue" if the server uses it)
    first_resp = read_headers(sock)
    # Debug info
    print(">> First response:\n", first_resp.decode("latin1", errors="replace"), flush=True)

    if b"100 Continue" in first_resp:
        # 5. If "100 Continue," send the remaining blocks
        for part in payload_parts[1:]:
            if part.strip():
                sock.sendall(part + b"\r\n\r\n")

        # 6. Read second response (should be "101 Switching Protocols" or the final handshake)
        second_resp = read_headers(sock)
        print(">> Second response:\n", second_resp.decode("latin1", errors="replace"), flush=True)

    else:
        # If no 100 Continue, maybe we just send all at once
        # or maybe the handshake is complete. This depends on your server's behavior.
        if len(payload_parts) > 1:
            for part in payload_parts[1:]:
                if part.strip():
                    sock.sendall(part + b"\r\n\r\n")

        # Optionally read next response
        second_resp = read_headers(sock)
        print(">> Second response (no 100 Continue path):\n",
              second_resp.decode("latin1", errors="replace"), flush=True)

    # If we got here, we assume the tunnel is "upgraded" to raw.
    # Some servers give "101 Switching Protocols," others do different things.
    # We won't parse it strictly. We'll just proceed.
    print("[*] WebSocket handshake done. Returning raw socket.")
    return sock
