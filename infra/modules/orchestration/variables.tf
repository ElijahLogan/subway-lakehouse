variable "env" {
  type    = string
}

variable "lambda_arn" {
  type    = string
}
variable "polling_enabled" {
  description = "Flip to false to pause ingestion without destroying anything"
  type        = bool
  default     = true
}