data "google_project" "this" {}

locals {
  ssh_metadata = "${var.ssh_user}:${trimspace(file(pathexpand(var.ssh_public_key_file)))}"
  labels       = { purpose = "doris-poc", managed-by = "terraform" }
}

# ---------- APIs (left enabled on destroy) ----------
resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# ---------- Doris nodes: one VM per zone, FE + BE on each ----------
resource "google_compute_instance" "doris" {
  count        = length(var.zones)
  name         = "${var.name_prefix}-${count.index + 1}"
  zone         = "${var.region}-${var.zones[count.index]}"
  machine_type = lookup(var.machine_type_override, "${var.name_prefix}-${count.index + 1}", var.machine_type)
  tags         = ["doris"]
  labels       = local.labels

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = var.disk_gb
      type  = "pd-balanced"
    }
  }

  network_interface {
    network = "default"
    access_config {} # ephemeral external IP (operator SSH + firewall-limited 9030)
  }

  metadata = { ssh-keys = local.ssh_metadata }

  service_account {
    email  = "${data.google_project.this.number}-compute@developer.gserviceaccount.com"
    scopes = ["https://www.googleapis.com/auth/devstorage.read_only", "https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/monitoring.write", "https://www.googleapis.com/auth/pubsub", "https://www.googleapis.com/auth/service.management.readonly", "https://www.googleapis.com/auth/servicecontrol", "https://www.googleapis.com/auth/trace.append"]
  }

  desired_status            = var.vm_status
  allow_stopping_for_update = true

  lifecycle {
    # imported VMs carry a pinned image version; never replace a node just because the family moved on
    ignore_changes = [boot_disk[0].initialize_params[0].image]
  }

  depends_on = [google_project_service.apis]
}

# ---------- Client VM: runs the mysql / jdbc / arrow-flight probes inside the VPC ----------
resource "google_compute_instance" "client" {
  name         = "${var.name_prefix}-client"
  zone         = "${var.region}-${var.zones[0]}"
  machine_type = var.client_machine_type
  labels       = local.labels

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = var.client_disk_gb
      type  = "pd-balanced"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata = { ssh-keys = local.ssh_metadata }

  service_account {
    email  = "${data.google_project.this.number}-compute@developer.gserviceaccount.com"
    scopes = ["https://www.googleapis.com/auth/devstorage.read_only", "https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/monitoring.write", "https://www.googleapis.com/auth/pubsub", "https://www.googleapis.com/auth/service.management.readonly", "https://www.googleapis.com/auth/servicecontrol", "https://www.googleapis.com/auth/trace.append"]
  }

  desired_status            = var.vm_status
  allow_stopping_for_update = true

  lifecycle {
    ignore_changes = [boot_disk[0].initialize_params[0].image]
  }

  depends_on = [google_project_service.apis]
}

# ---------- Firewall: FE/BE ports only from the operator IP (VPC-internal traffic uses default-allow-internal) ----------
resource "google_compute_firewall" "operator" {
  name          = "doris-client-from-me"
  network       = "default"
  direction     = "INGRESS"
  priority      = 1000
  description   = "Doris FE/BE ports from operator IP"
  source_ranges = ["${var.allow_ip}/32"]
  target_tags   = ["doris"]

  allow {
    protocol = "tcp"
    ports    = ["9030", "8030", "8040"]
  }
}

# ---------- Demo site on Cloud Run (optional: set site_image) ----------
resource "google_cloud_run_v2_service" "site" {
  count               = var.site_image == "" ? 0 : 1
  name                = var.site_service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    containers {
      image = var.site_image
      ports { container_port = 8080 }
      resources {
        limits = { memory = "256Mi", cpu = "1" }
      }
    }
    scaling { max_instance_count = 2 }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  count    = var.site_image == "" ? 0 : 1
  name     = google_cloud_run_v2_service.site[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ---------- Ansible inventory, regenerated on every apply ----------
resource "local_file" "inventory" {
  filename        = "${path.module}/${var.inventory_path}"
  file_permission = "0644"
  content = templatefile("${path.module}/inventory.tftpl", {
    ssh_user = var.ssh_user
    nodes = [for i, vm in google_compute_instance.doris : {
      name        = vm.name
      zone        = vm.zone
      internal_ip = vm.network_interface[0].network_ip
      external_ip = try(vm.network_interface[0].access_config[0].nat_ip, "")
      seed        = i == 0
    }]
    client = {
      name        = google_compute_instance.client.name
      zone        = google_compute_instance.client.zone
      internal_ip = google_compute_instance.client.network_interface[0].network_ip
      external_ip = try(google_compute_instance.client.network_interface[0].access_config[0].nat_ip, "")
    }
  })
}
