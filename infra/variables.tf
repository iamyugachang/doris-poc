variable "project" {
  type    = string
  default = "doris-poc"
}

variable "region" {
  type    = string
  default = "asia-east1"
}

variable "zones" {
  description = "One Doris VM per zone suffix (FE + BE on each)."
  type        = list(string)
  default     = ["a", "b", "c"]
}

variable "name_prefix" {
  type    = string
  default = "doris"
}

variable "machine_type" {
  type    = string
  default = "e2-standard-4"
}

variable "machine_type_override" {
  # per-node override, e.g. { "doris-3" = "n2-standard-4" } when a zone is out of the default type
  type    = map(string)
  default = {}
}

variable "disk_gb" {
  type    = number
  default = 50
}

variable "client_machine_type" {
  type    = string
  default = "e2-small"
}

variable "client_disk_gb" {
  type    = number
  default = 20
}

variable "vm_status" {
  description = "Power state of every VM: RUNNING or TERMINATED (demo.sh stop/start flips this)."
  type        = string
  default     = "RUNNING"
  validation {
    condition     = contains(["RUNNING", "TERMINATED"], var.vm_status)
    error_message = "vm_status must be RUNNING or TERMINATED."
  }
}

variable "allow_ip" {
  description = "Operator IPv4 (no mask) allowed to reach FE/BE ports 9030/8030/8040 from the internet."
  type        = string
}

variable "ssh_user" {
  type = string
}

variable "ssh_public_key_file" {
  description = "Public key installed on every VM for ssh_user (the gcloud-managed key works)."
  type        = string
  default     = "~/.ssh/google_compute_engine.pub"
}

variable "site_image" {
  description = "Container image for the demo site on Cloud Run. Empty string = do not manage the Cloud Run service."
  type        = string
  default     = ""
}

variable "site_service_name" {
  type    = string
  default = "doris-ha-demo"
}

variable "inventory_path" {
  description = "Where to write the generated Ansible inventory."
  type        = string
  default     = "../ansible/inventory.ini"
}
