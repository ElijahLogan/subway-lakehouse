variable "env" {
  type    = string
}

variable "lambda_zip" {
  description = "Path to the zip built by `make lambda`"
  type        = string
  default     = "../../../build/layer.zip"
}   

variable "databricks_host" {
  type    = string
}

variable "volume_path" {
  type    = string
}

variable "dd_site" {
  type    = string
  default = "dev"
}


