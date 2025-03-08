terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.24.0"
    }
  }
}

provider "google" {
  credentials = file(var.credentials)
  project     = var.project
  region      = var.region
}


resource "google_storage_bucket" "de-task-1-bucket" {
  name          = var.gcs_bucket_name
  location      = var.location
  force_destroy = true
}
