import socket
import threading
import paramiko
import struct

class SSHOverWebSocket:
    """
    Wraps a Paramiko Transport (SSH) that runs on top of a raw
    WebSocket-upgraded socket, plus a local SOCKS server.
    """

    def __init__(self, ws_socket, ssh_username, ssh_password, ssh_port=22):
        """
        ws_socket: the raw connected socket from the WS tunnel
        ssh_username / ssh_password: credentials
        ssh_port: the 'real' SSH port the server is listening on (often 22).
                  Some SSH-over-WebSocket providers might ignore it,
                  but we pass it anyway to Paramiko connect().
        """
        self.ws_socket = ws_socket
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.ssh_port = ssh_port
        self.transport = None

    def start_ssh_transport(self):
        """
        Initialize Paramiko Transport over the raw ws_socket,
        authenticate with the given credentials.
        """
        self.transport = paramiko.Transport(self.ws_socket)
        self.transport.start_client()

        # You might want to do hostkey checks here, e.g.:
        # server_key = self.transport.get_remote_server_key()
        # if not verify_host_key(server_key):
        #     raise Exception("Unknown Host Key!")

        # Password-based auth
        self.transport.auth_password(self.ssh_username, self.ssh_password)
        if not self.transport.is_authenticated():
            raise Exception("SSH Authentication failed")

        print("[*] SSH transport established and authenticated.")

    def close(self):
        """ Clean up. """
        if self.transport is not None:
            self.transport.close()

    def open_socks_proxy(self, local_port):
        """
        Start a small SOCKS4/5 server on local_port that forwards
        connections through the SSH transport.

        The user can configure their browser or app to use
        127.0.0.1:local_port as a SOCKS proxy.
        """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', local_port))
        server.listen(100)
        print(f"[*] SOCKS proxy listening on 127.0.0.1:{local_port}")

        def handle_socks_client(client_sock):
            try:
                # Minimal parse for SOCKS4/5. Let's do a naive approach.
                # For real usage, you'd fully parse the protocol.
                # We'll do a quick check for SOCKS4 or 5 handshake.

                data = client_sock.recv(1024)
                if not data:
                    client_sock.close()
                    return

                # This is extremely bare-bones. In real code, parse carefully.
                # We'll assume the client is doing SOCKS4 or 5 with a CONNECT command.
                # The "destination" might be at some offset.

                # For demonstration, let's assume we read a domain or IP from the data.
                # Then we do open_channel('direct-tcpip', (host, port), (client_ip, client_port))
                # We'll pretend the request is for, say, data[4:8] IP and data[8:10] port if it's SOCKS4.

                version = data[0]
                if version == 4:
                    # SOCKS4
                    port = struct.unpack('>H', data[2:4])[0]
                    ip_bytes = data[4:8]
                    host = socket.inet_ntoa(ip_bytes)
                    # skip userID
                    # respond with "granted"
                    resp = b"\x00\x5A" + data[2:4] + data[4:8]
                    client_sock.sendall(resp)
                elif version == 5:
                    # Possibly handle the method negotiation
                    # We'll cheat and respond "no auth needed"
                    client_sock.sendall(b"\x05\x00")
                    # Next read the actual connect request
                    connect_req = client_sock.recv(1024)
                    # second byte is CMD, typically 0x01 for CONNECT
                    # parse host + port
                    addr_type = connect_req[3]
                    idx = 4
                    if addr_type == 1:
                        # IPv4
                        ip_bytes = connect_req[idx:idx+4]
                        idx += 4
                        host = socket.inet_ntoa(ip_bytes)
                    elif addr_type == 3:
                        # domain
                        domain_len = connect_req[idx]
                        idx += 1
                        domain = connect_req[idx: idx+domain_len].decode()
                        idx += domain_len
                        host = domain
                    else:
                        # ignoring IPv6
                        client_sock.close()
                        return
                    port = struct.unpack('>H', connect_req[idx:idx+2])[0]

                    # reply: 05 00 00 01 ...
                    reply = b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                    client_sock.sendall(reply)
                else:
                    # Not a recognized SOCKS version
                    client_sock.close()
                    return

                print(f"[*] Opening SSH channel to {host}:{port}")

                # Make a direct-tcpip channel via Paramiko
                chan = self.transport.open_channel(
                    "direct-tcpip",
                    (host, port),
                    client_sock.getsockname()
                )

                # Now forward data in both directions
                def forward(src, dst):
                    try:
                        while True:
                            chunk = src.recv(4096)
                            if not chunk:
                                break
                            dst.sendall(chunk)
                    except:
                        pass
                    finally:
                        dst.close()
                        src.close()

                threading.Thread(target=forward, args=(client_sock, chan), daemon=True).start()
                threading.Thread(target=forward, args=(chan, client_sock), daemon=True).start()

            except Exception as e:
                print(f"[!] SOCKS client error: {e}")
                client_sock.close()

        def accept_loop():
            while True:
                try:
                    client_sock, _ = server.accept()
                    threading.Thread(target=handle_socks_client, args=(client_sock,), daemon=True).start()
                except:
                    break

        threading.Thread(target=accept_loop, daemon=True).start()
        print("[*] SOCKS proxy started.")

        # We won’t return; it’s up to you to keep the main thread alive, etc.


def connect_via_ws_and_start_socks(ws_socket, ssh_user, ssh_password, ssh_port, local_socks_port):
    """
    A convenience function:
      1) Start SSH transport over the ws_socket
      2) Start a local SOCKS proxy
    """
    connector = SSHOverWebSocket(ws_socket, ssh_user, ssh_password, ssh_port)
    connector.start_ssh_transport()
    connector.open_socks_proxy(local_socks_port)
    # Keep the object in scope so it’s not garbage-collected
    return connector
