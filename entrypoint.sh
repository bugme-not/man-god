#!/bin/bash
set -e

# Increase file descriptor limits for high concurrency
ulimit -n 65535 || true

echo "[+] Tuning Kernel & TCP Socket Parameters for Low Latency..."
# Enable Google BBR Congestion Control
sysctl -w net.core.default_qdisc=fq 2>/dev/null || true
sysctl -w net.ipv4.tcp_congestion_control=bbr 2>/dev/null || true

# Maximize socket memory buffers (16MB max) for fast streaming
sysctl -w net.core.rmem_max=16777216 2>/dev/null || true
sysctl -w net.core.wmem_max=16777216 2>/dev/null || true
sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216" 2>/dev/null || true
sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216" 2>/dev/null || true

# Fast socket recycling, low FIN timeouts, and TCP Fast Open
sysctl -w net.ipv4.tcp_fin_timeout=15 2>/dev/null || true
sysctl -w net.ipv4.tcp_tw_reuse=1 2>/dev/null || true
sysctl -w net.ipv4.tcp_fastopen=3 2>/dev/null || true

echo "[+] Preparing runtime directories for Cloud Run..."
mkdir -p /run/sshd /var/run/sshd /tmp/proxy_db /var/log/supervisor

echo "[+] Generating SSH Host Keys if missing..."
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    ssh-keygen -A
fi

echo "[+] Handing over execution to Supervisord..."
exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
