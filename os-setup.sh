#!/bin/bash
set -e -o pipefail

echo "Waiting for cloud-init to finish..."
cloud-init status --wait

echo "Configuring and enabling UFW..."
sudo ufw allow 51820/udp comment Wireguard
sudo ufw allow 22/tcp comment OpenSSH
sudo ufw route allow out on v6tun to ::/0
sudo ufw route allow in on v6tun from ::/0
sudo ufw --force enable

echo "Cleanup..."
cloud-init clean --machine-id --seed --logs --configs all
rm -vrf /root/.ssh/authorized_keys

echo "Disk sync..."
sync

echo "Finished"
