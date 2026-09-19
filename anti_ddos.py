import asyncio
import collections
import socket
import struct
import time
import os
import sys

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

MAX_CONN_PER_IP = 150       
RATE_LIMIT_WINDOW = 5       
MAX_REQ_PER_WINDOW = 200    
BAN_TIME = 600              
IPSET_NAME = "antiddos_blacklist"
LOOP_INTERVAL = 0.5         

banned_ips = {}  
ip_history = collections.defaultdict(lambda: collections.deque(maxlen=MAX_REQ_PER_WINDOW + 10))

IPV4_PACK = struct.Struct("<I")
IPV6_PACK = struct.Struct("<4I")

ipset_proc = None

def log(msg: str) -> None:
    print(f"[Anti-DDoS Engine] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}", flush=True)

def parse_hex_ip_fast(hex_str: str) -> str:
    try:
        length = len(hex_str)
        if length == 8:
            addr_int = int(hex_str, 16)
            return socket.inet_ntop(socket.AF_INET, IPV4_PACK.pack(addr_int))
        elif length == 32:
            words = (
                int(hex_str[0:8], 16),
                int(hex_str[8:16], 16),
                int(hex_str[16:24], 16),
                int(hex_str[24:32], 16)
            )
            return socket.inet_ntop(socket.AF_INET6, IPV6_PACK.pack(*words))
    except (ValueError, OSError):
        pass
    return ""

def read_proc_sockets_fast():
    remote_ips = []
    
    for path in ("/proc/net/tcp", "/proc/net/tcp6"):
        if not os.path.exists(path):
            continue
            
        with open(path, "rb") as f:
            f.readline()
            for line in f:
                parts = line.split()
                if len(parts) < 4:
                    continue
                
                state = parts[3]
                if state != b"01" and state != b"02":
                    continue
                
                rem_addr = parts[2]
                colon_pos = rem_addr.find(b":")
                if colon_pos == -1:
                    continue
                
                hex_ip = rem_addr[:colon_pos].decode("ascii")
                ip = parse_hex_ip_fast(hex_ip)
                
                if ip and not (ip.startswith("127.") or ip == "::1" or ip == "0.0.0.0"):
                    remote_ips.append(ip)
                    
    return remote_ips

async def exec_cmd(*args) -> bool:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    await proc.wait()
    return proc.returncode == 0

async def setup_firewall():
    global ipset_proc
    log("Initializing kernel ipset rules...")
    await exec_cmd("ipset", "create", IPSET_NAME, "hash:ip", "timeout", str(BAN_TIME), "-exist")
    await exec_cmd("iptables", "-I", "INPUT", "-m", "set", "--match-set", IPSET_NAME, "src", "-j", "DROP")
    
    ipset_proc = await asyncio.create_subprocess_exec(
        "ipset", "restore",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )

async def ban_ips_batch(ips: list):
    if not ips or not ipset_proc or ipset_proc.stdin.is_closing():
        return

    now = time.time()
    commands = []
    
    for ip in ips:
        if ip in banned_ips:
            continue
        banned_ips[ip] = now + BAN_TIME
        commands.append(f"add {IPSET_NAME} {ip} timeout {BAN_TIME} -exist\n")
        log(f"ALERT: Ban applied to {ip} (Kernel ipset)")
        
    if commands:
        payload = "".encode("utf-8").join(c.encode("utf-8") for c in commands)
        ipset_proc.stdin.write(payload)
        await ipset_proc.stdin.drain()

async def prune_expired_bans():
    now = time.time()
    expired = [ip for ip, exp_time in banned_ips.items() if now >= exp_time]
    for ip in expired:
        del banned_ips[ip]
        ip_history.pop(ip, None)

async def inspect_connections():
    now = time.time()
    remote_ips = await asyncio.to_thread(read_proc_sockets_fast)
    
    active_counts = collections.defaultdict(int)
    ips_to_ban = set()

    for ip in remote_ips:
        if ip in banned_ips:
            continue

        active_counts[ip] += 1
        history = ip_history[ip]
        history.append(now)

        if active_counts[ip] > MAX_CONN_PER_IP:
            log(f"EXCEEDED CONCURRENCY: {ip} ({active_counts[ip]} active sockets)")
            ips_to_ban.add(ip)
            continue

        while history and now - history[0] > RATE_LIMIT_WINDOW:
            history.popleft()

        if len(history) > MAX_REQ_PER_WINDOW:
            log(f"RATE LIMIT EXCEEDED: {ip} ({len(history)} reqs/{RATE_LIMIT_WINDOW}s)")
            ips_to_ban.add(ip)

    if ips_to_ban:
        await ban_ips_batch(list(ips_to_ban))

async def main():
    await setup_firewall()
    log("Engine started. Real-time C-level kernel socket inspection active...")

    while True:
        try:
            await inspect_connections()
            await prune_expired_bans()
        except Exception as e:
            log(f"Error inside engine loop: {e}")
            
        await asyncio.sleep(LOOP_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        if ipset_proc:
            ipset_proc.terminate()
        log("Shutting down engine...")
