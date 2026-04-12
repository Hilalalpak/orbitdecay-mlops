#!/bin/bash
# Production API initialization script
# Author: Hilal Alpak
# Version: 1.0.0

set -e

USER_NAME="prod_user"
SSH_PORT="2224"

echo "Starting OrbitDecay Production API..."

if [ ! -f "/etc/ssh/ssh_host_rsa_key" ]; then
    echo "Generating SSH keys..."
    sudo ssh-keygen -A
fi

sudo mkdir -p /run/sshd
sudo chmod 755 /run/sshd

if [ -f "/home/${USER_NAME}/.ssh/authorized_keys" ] && [ -s "/home/${USER_NAME}/.ssh/authorized_keys" ]; then
    echo "Key-based auth enabled"
    sudo sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
else
    echo "Password auth enabled"
fi

echo "Starting SSH daemon..."
sudo /usr/sbin/sshd -D &
SSH_PID=$!

sleep 2
if kill -0 $SSH_PID 2>/dev/null; then
    echo "✅ SSH ready: ssh ${USER_NAME}@localhost -p ${SSH_PORT}"
else
    echo "❌ SSH failed"
    exit 1
fi

echo "Starting production API server..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4