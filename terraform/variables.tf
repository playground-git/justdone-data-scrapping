variable "credentials" {
  description = "My Credentials"
  default     = "<Path to your Service Account json file>"
}

variable "project" {
  description = "Project"
  default     = "<Your Project ID>"
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
  description = "My Storage Bucket Name"
  default     = "<Your Project Bucket ID>"
}
