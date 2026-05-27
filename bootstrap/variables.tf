// Variables required by bootstrap/main.tf
variable "kubeconfig" {
  description = "Path to a kubeconfig file used by Terraform providers"
  type        = string
}

variable "bootstrap_revision" {
  description = "Revision/branch/tag for bootstrap resources"
  type        = string
  default     = "main"
}

variable "cluster_name" {
  description = "Cluster name used in runtime_info and file paths"
  type        = string
}

variable "sops_age_key" {
  description = "SOPS age private key contents (the content of the age key file)"
  type        = string
  sensitive   = true
  validation {
    condition     = length(trimspace(var.sops_age_key)) > 0
    error_message = "sops_age_key must be provided and non-empty."
  }
}
