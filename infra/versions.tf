terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.4"
    }
  }
}

# Auth: demo.sh / infra/tf.sh export GOOGLE_OAUTH_ACCESS_TOKEN from `gcloud auth print-access-token`,
# so no application-default login is needed.
provider "google" {
  project = var.project
  region  = var.region
}
