terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = ">= 3.74.2, < 4.0"
    }
    local      = ">= 2.1.0, < 3.0"
    random     = ">= 3.1.0, < 4.0"
  }
  required_version = ">= 1.1.5, < 2.0"
}