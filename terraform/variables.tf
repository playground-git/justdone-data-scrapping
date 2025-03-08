variable "credentials" {
  description = "Credentials"
  default     = "<Path to your Service Account json file>"
}

variable "project" {
  description = "Project"
  default     = "<Project ID>"
}

variable "region" {
  description = "Region"
  default     = "europe-west1"
}

variable "location" {
  description = "Project Location"
  default     = "EU"
}

variable "gcs_bucket_name" {
  description = "Storage Bucket Name"
  default     = "<Project Bucket ID>"
}

variable "gcs_storage_class" {
  description = "Bucket Storage Class"
  default     = "STANDARD"
}
