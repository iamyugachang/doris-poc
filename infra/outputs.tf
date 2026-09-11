output "nodes" {
  description = "Doris VMs: name, zone, internal and external IP"
  value = [for vm in google_compute_instance.doris : {
    name        = vm.name
    zone        = vm.zone
    internal_ip = vm.network_interface[0].network_ip
    external_ip = try(vm.network_interface[0].access_config[0].nat_ip, "")
  }]
}

output "client" {
  value = {
    name        = google_compute_instance.client.name
    zone        = google_compute_instance.client.zone
    internal_ip = google_compute_instance.client.network_interface[0].network_ip
    external_ip = try(google_compute_instance.client.network_interface[0].access_config[0].nat_ip, "")
  }
}

output "site_url" {
  value = try(google_cloud_run_v2_service.site[0].uri, null)
}

output "inventory" {
  value = local_file.inventory.filename
}
