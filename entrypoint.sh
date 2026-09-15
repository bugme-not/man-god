#!/bin/bash
set -e

# Increase file descriptor limits for high concurrency
ulimit -n 65535 || true

echo "[+] Preparing runtime directories for Cloud Run..."
mkdir -p /run/sshd /var/run/sshd /tmp/proxy_db /var/log/supervisor

echo "[+] Generating SSH Host Keys if missing..."
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    ssh-keygen -A
fi

echo "[+] Handing over execution to Supervisord..."
exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
