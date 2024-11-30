# cloud-tunnel

This repository provides a [HashiCorp
Packer](https://developer.hashicorp.com/packer) template to build IPv6 tunnel
VMs on [Hetzner Cloud](https://www.hetzner.com/cloud/). An accompanying blog
post will be published shortly.

## Requirements
To build the images you will need an account and project set up on Hetzner
Cloud, and an [API token](https://docs.hetzner.cloud/#getting-started)
configured on said project. You can get a referral link from a current Hetzner
customer to receive some initial credits you can use to get started on the
platform.

## Usage
Start by installing [Packer](https://developer.hashicorp.com/packer/install) on
your computer. Then you can have Packer install the Hetzner plugin by running
`packer init`, and build the image for both x86 and ARM servers using the
`packer build` command.

```shell
$ git clone https://github.com/elopez/cloud-tunnel.git
$ cd cloud-tunnel # this repository
$ export HCLOUD_TOKEN=YOUR_TOKEN_HERE
$ packer init .
Installed plugin github.com/hetznercloud/hcloud v1.6.0 in "/$HOME/.config/packer/plugins/github.com/hetznercloud/hcloud/packer-plugin-hcloud_v1.6.0_x5.0_linux_amd64"
$ packer build .
hcloud.base-arm64: output will be in this color.
hcloud.base-amd64: output will be in this color.
...
==> hcloud.base-amd64: This can take some time
==> hcloud.base-arm64: Destroying server...
==> hcloud.base-arm64: Deleting temporary SSH key...
Build 'hcloud.base-arm64' finished after 2 minutes 57 seconds.
==> hcloud.base-amd64: Destroying server...
==> hcloud.base-amd64: Deleting temporary SSH key...
Build 'hcloud.base-amd64' finished after 3 minutes 12 seconds.
```

### Deploying a server

Once the images have been built, you may create a virtual server on Hetzner
using these images. Browse to the "Create a server" page, and choose the
location you want to deploy to. Ideally, pick the one with the lowest latency
from your current location. You can get latency measurements to each location by
visiting the [Hetzner Latency Test](https://hetzner-latency.sliplane.io/) page.

Once you have selected a region, skip the image selection and select the VM type
you want to deploy instead (Dedicated or Shared vCPU, x86 or Arm64, and the VM
size). Then, go back to the "Image" step, and pick the "cloud-tunnel" image from
the "Snapshots" tab. Ensure both IPv4 and IPv6 are enabled from the networking
section. Select or add an SSH key, to be able to connect to the server later on
and configure your local peer on the tunnel. Give it an appropriate name on the
last step, and finally press "Create & Buy now" to conclude the deployment
process.

### Configuring the local endpoint

Start by creating some WireGuard keys for your local endpoint. Refer to the
accompanying blog post for an example tutorial on a MikroTik router. You will
need some more details to be able to configure the local WireGuard client fully,
so we will connect to the server to obtain them. Get the IPv4 address of your
server from the Hetzner panel and use `ssh` to connect. Once you are logged in,
run `wg show` and note the server's public key for later use.

Then, edit `/etc/wireguard/v6tun.conf` with your favorite editor. At the end of
the file, you will see a commented-out section that looks like this:

```toml
#[Peer]
## home router
#PublicKey = HOME_WG_PUB
#PresharedKey = AAAAA....A=
#AllowedIPs = 2001:0DB8::/64, fd82:6bf9:f085::2
```

Uncomment it by removing the initial `#` characters, and edit the `PublicKey`
field with your local endpoints' WireGuard public key. Make a note of the
`PresharedKey` and both the public IPv6 network as well as the ULA address that
accompanies it. Save the changes and restart the WireGuard tunnel or reboot the
server. At this point, you should have all the information you need to finish
configuring your local endpoint.