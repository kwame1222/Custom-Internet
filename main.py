import time
from config import CONFIG
from tunnel_strategies import get_strategy
from ssh_connector import connect_via_ws_and_start_socks
def main():
    """
    1) Use ws_tunnel to do the WebSocket handshake with the remote proxy.
    2) Wrap that socket in Paramiko's SSH transport.
    3) Provide a local SOCKS proxy on CONFIG['LOCAL_SOCKS_PORT'].
    4) Sleep or wait forever so it doesn't exit.
    """
    try:
        strategy_cls = get_strategy(CONFIG['MODE'])
        ws_sock      = strategy_cls(CONFIG).establish()

        ssh_connection = connect_via_ws_and_start_socks(
            ws_socket       = ws_sock,
            ssh_user        = CONFIG['SSH_USERNAME'],
            ssh_password    = CONFIG['SSH_PASSWORD'],
            ssh_port        = CONFIG['SSH_PORT'],
            local_socks_port= CONFIG['LOCAL_SOCKS_PORT'],
        )

        print(f"[+] SOCKS proxy up on 127.0.0.1:{CONFIG['LOCAL_SOCKS_PORT']}")
        print("[+] All traffic through that proxy is forwarded over SSH via WS tunnel.")

        # Keep running until user kills it (CTRL+C)
        while True:
            time.sleep(999999)

    except KeyboardInterrupt:
        print("[*] Shutting down (KeyboardInterrupt).")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    main()
