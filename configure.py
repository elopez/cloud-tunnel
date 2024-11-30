#!/usr/bin/env python3

# ULA-generation code
# Original credit: Andrew Ho
# https://github.com/andrewlkho/ulagen

import hashlib
import time
import uuid
import argparse


def get_eui64():
    """
    Retrieve the MAC address of the node running this code.
    Returns the MAC address in canonical format (XX-XX-XX-XX-XX-XX).
    """
    mac = uuid.getnode()
    eui64 = mac >> 24 << 48 | 0xFFFE000000 | mac & 0xFFFFFF
    eui64_canon = "-".join([format(eui64, "02X")[i : i + 2] for i in range(0, 18, 2)])
    return eui64_canon


def time_ntpformat():
    """
    Return the current NTP-format time.
    """
    # Seconds relative to 1900-01-01 00:00
    return time.time() - time.mktime((1900, 1, 1, 0, 0, 0, 0, 1, -1))


def gen_prefix():
    """
    Generate a prefix in the fd00::/8 address space.
    """
    h = hashlib.sha1()
    h.update((get_eui64() + str(time_ntpformat())).encode("us-ascii"))
    globalid = h.hexdigest()[0:10]

    return ":".join(("fd" + globalid[0:2], globalid[2:6], globalid[6:10]))


# Network suffix masking
mask_suffix = lambda suffix, length: (suffix & ((2**length) - 1)) << (64 - length)


def gen_subnet(prefix, suffix, length=64, showlength=True):
    """
    Create a subnet from the given prefix.
    """

    # We only support networks in this size range.
    assert length >= 48, "Subnet too big"
    assert length <= 64, "Subnet too small"

    if (suffix == 0) or (length == 48):
        # This is the prefix itself.
        if showlength:
            return "%s::/%s" % (prefix, length)
        else:
            return prefix
    else:
        return "%s:%x::%s" % (
            prefix,
            mask_suffix(suffix, length),
            ("/%d" % length) if showlength else "",
        )


# Configuration code
import subprocess
import re
import yaml
import ipaddress
from jinja2 import Template

WAN_IF = "eth0"


# Function to run a shell command and return its output
def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout.strip()


# Function to get the current IPv6 address and subnet of eth0
def get_wan_ipv6_address():
    with open("/etc/netplan/50-cloud-init.yaml") as stream:
        conf = yaml.safe_load(stream)

    return conf["network"]["ethernets"][WAN_IF]["addresses"][0]


# Function to generate WireGuard keys
def generate_wg_key():
    private_key = run_command("wg genkey")
    psk = run_command("wg genpsk")
    return private_key, psk


# Main function to generate the config file
def generate_wireguard_config():
    # Get current IPv6 address and subnet on eth0
    ipv6_address = get_wan_ipv6_address()
    ipv6_network = ipaddress.IPv6Network(ipv6_address, strict=False).with_prefixlen
    ula_network = gen_subnet(gen_prefix(), 0, showlength=False)

    # Generate WireGuard keys
    private_key, psk = generate_wg_key()

    # Jinja2 template for the WireGuard config
    wg_config_template = """\
[Interface]
# VPS endpoint
Address = {{ ula_network }}::1
PrivateKey = {{ wg_private_key }}
ListenPort = 51820
# Adjust your MTU as needed (typically, your WAN MTU - 60)
MTU = 1360

# enable IPv6 forwarding
PreUp = echo 1 > /proc/sys/net/ipv6/conf/all/forwarding
# stop routing the whole prefix to the host interface (will clash with the rule below otherwise)
PreUp = ip route del {{ ipv6_network }} dev {{ wan_if }}
PreUp = ip addr del {{ ipv6_address }} dev {{ wan_if }}
# route allowed IPs (see below) to the WireGuard interface (will be added automatically)
#PreUp = ip route add {{ ipv6_network }} dev %i

# restore routing for host interface
PostDown = ip route add {{ ipv6_network }} dev {{ wan_if }}
PostDown = ip addr add {{ ipv6_address }} dev {{ wan_if }}

#[Peer]
## home router
#PublicKey = HOME_WG_PUB
#PresharedKey = {{ wg_psk }}
#AllowedIPs = {{ ipv6_network }}, {{ ula_network }}::2
"""

    # Create the Jinja2 template and render it with the variables
    template = Template(wg_config_template)
    config = template.render(
        ula_network=ula_network,
        ipv6_address=ipv6_address,
        ipv6_network=ipv6_network,
        wg_private_key=private_key,
        wg_psk=psk,
        wan_if=WAN_IF,
    )

    with open("/etc/wireguard/v6tun.conf", "w") as f:
        f.write(config)

    run_command("systemctl enable wg-quick@v6tun")
    run_command("systemctl start wg-quick@v6tun")


# Main function to generate the config file
def generate_ndppd_config():
    # Get current IPv6 address and subnet on eth0
    ipv6_address = get_wan_ipv6_address()
    ipv6_network = ipaddress.IPv6Network(ipv6_address, strict=False).with_prefixlen

    # Jinja2 template for the WireGuard config
    ndppd_config_template = """\
proxy {{ wan_if }} {
  router yes
  ttl 120000
  timeout 10000

  rule {{ ipv6_network }} {
      iface v6tun
  }
}
"""

    # Create the Jinja2 template and render it with the variables
    template = Template(ndppd_config_template)
    config = template.render(
        ipv6_network=ipv6_network,
        wan_if=WAN_IF,
    )

    with open("/etc/ndppd.conf", "w") as f:
        f.write(config)

    run_command("systemctl enable ndppd")
    run_command("systemctl start ndppd")
    run_command("systemctl restart ndppd")


if __name__ == "__main__":
    generate_wireguard_config()
    generate_ndppd_config()
