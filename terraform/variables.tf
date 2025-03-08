variable "credentials" {
  description = "Credentials"
  default     = "~/.config/gcloud/application_default_credentials.json"
}

variable "project" {
  description = "Project"
  default     = "de-tasks-453115"
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
  default     = "de-task-1-bucket"
}

variable "gcs_storage_class" {
  description = "Bucket Storage Class"
  default     = "STANDARD"
}
