import socket
import threading
import time
import re

BUF_SIZE = 131072         # 128KB buffer
MAX_CONN_PER_IP = 150     # Max connections per real client IP
RATE_LIMIT_WINDOW = 120   # 2-minute sliding window

ip_connections = {}
ip_lock = threading.Lock()


def check_rate_limit(ip):
    now = time.time()
    with ip_lock:
        if ip not in ip_connections:
            ip_connections[ip] = []
        
        # Purge timestamps outside window
        ip_connections[ip] = [t for t in ip_connections[ip] if now - t < RATE_LIMIT_WINDOW]
        
        if len(ip_connections[ip]) >= MAX_CONN_PER_IP:
            return False
        ip_connections[ip].append(now)
        return True


def cleanup_stale_ips():
    """Background garbage collector to purge idle IP memory every 5 minutes."""
    while True:
        time.sleep(300)
        now = time.time()
        with ip_lock:
            empty_ips = [
                ip for ip, timestamps in ip_connections.items()
                if not [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
            ]
            for ip in empty_ips:
                del ip_connections[ip]


def extract_real_ip(header_bytes, fallback_ip):
    """Extract real client IP from X-Forwarded-For or X-Real-IP headers."""
    try:
        header_text = header_bytes.decode('utf-8', errors='ignore')
        match = re.search(r'X-Forwarded-For:\s*([^\r\n,]+)', header_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r'X-Real-IP:\s*([^\r\n]+)', header_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return fallback_ip


def tune_socket(sock):
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    # Enable TCP Keepalive
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1 << 20)
    except OSError:
        pass


def bridge(src, dst):
    try:
        while True:
            data = src.recv(BUF_SIZE)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            src.close()
        except Exception:
            pass
        try:
            dst.close()
        except Exception:
            pass


def handle(client, addr):
    try:
        tune_socket(client)
        
        # Read initial HTTP upgrade request from Nginx to extract real IP
        initial_payload = client.recv(4096)
        if not initial_payload:
            client.close()
            return

        real_ip = extract_real_ip(initial_payload, addr[0])

        if not check_rate_limit(real_ip):
            client.sendall(b"HTTP/1.1 429 Too Many Requests\r\nConnection: close\r\n\r\n")
            client.close()
            return

        # Connect to local SSH server on port 22
        ssh = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tune_socket(ssh)
        ssh.connect(('127.0.0.1', 22))

        # Start bidirectional pipe (Nginx handles WS framing)
        t1 = threading.Thread(target=bridge, args=(client, ssh), daemon=True)
        t2 = threading.Thread(target=bridge, args=(ssh, client), daemon=True)
        t1.start()
        t2.start()
    except Exception:
        client.close()


def main():
    threading.Thread(target=cleanup_stale_ips, daemon=True).start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 2222))
    server.listen(2048)
    
    print("Anti-DDoS SSH-WS Guard listening on 127.0.0.1:2222")
    
    while True:
        client, addr = server.accept()
        threading.Thread(target=handle, args=(client, addr), daemon=True).start()


if __name__ == "__main__":
    main()
