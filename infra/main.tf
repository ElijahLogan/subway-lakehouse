# subway-pulse ingestion on AWS, sized to stay inside the Lambda / EventBridge
# Scheduler / SSM free allowances. Deliberately NOT used (they cost money from
# hour one): NAT gateways, VPCs, MSK/Kafka, Kinesis shards, Secrets Manager.

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.60"
    }
  }
}



provider "aws" {
  region = var.region
  default_tags {
    tags = {
      project = "subway-pulse"
      env     = var.env
    }
  }
}

provider "databricks" {}

module databricks {
  source = "./modules/databricks"
}