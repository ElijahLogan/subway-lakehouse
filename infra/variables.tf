variable "region" {
  type    = string
  default = "us-east-1"
}

variable "env" {
  type    = string
  default = "dev"
}


variable "databricks_host" {
  type    = string
}

variable "volume_path" {
  type    = string
}