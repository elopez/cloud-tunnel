variable "base_image" {
  type    = string
  default = "ubuntu-24.04"
}
variable "output_name" {
  type    = string
  default = "cloud-tunnel"
}
variable "version" {
  type    = string
  default = "v1.0.0"
}
variable "user_data_path" {
  type    = string
  default = "cloud-init-default.yml"
}

source "hcloud" "base-arm64" {
  image         = var.base_image
  location      = "nbg1"
  server_type   = "cax11"
  ssh_keys      = []
  user_data     = file(var.user_data_path)
  ssh_username  = "root"
  snapshot_name = "${var.output_name}-${var.version}"
  snapshot_labels = {
    base    = var.base_image,
    version = var.version,
    name    = "${var.output_name}-${var.version}"
  }
}

source "hcloud" "base-amd64" {
  image         = var.base_image
  location      = "nbg1"
  server_type   = "cx22"
  ssh_keys      = []
  user_data     = file(var.user_data_path)
  ssh_username  = "root"
  snapshot_name = "${var.output_name}-${var.version}"
  snapshot_labels = {
    base    = var.base_image,
    version = var.version,
    name    = "${var.output_name}-${var.version}"
  }
}

build {
  sources = ["source.hcloud.base-arm64", "source.hcloud.base-amd64"]
  provisioner "shell" {
    scripts = [
      "os-setup.sh",
    ]
    env = {
      BUILDER = "packer"
    }
  }
  provisioner "shell" {
    inline = [
      "mkdir -p /var/lib/cloud/scripts/per-instance/",
    ]
  }
  provisioner "file" {
    source = "configure.py"
    destination = "/var/lib/cloud/scripts/per-instance/configure.py"
  }
}