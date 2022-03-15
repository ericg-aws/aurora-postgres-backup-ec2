### shared 

variable "project" {
  description = "associated project or app"
  type        = string
}

variable "environment" {
  description = "associated environment"
  type        = string
}

variable "region" {
  description = "associated region"
  type        = string
}

variable "az" {
  description = "associated az for the ec2"
  type        = string
}

variable "vpc_id" {
  description = "ID of existing VPC"
  type        = string
}

variable "private_subnets_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "public_subnets_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

### s3
variable "s3_days_until_glacier" {
  description = "days until moving to glacier tier"
  type        = number
}
variable "s3_days_until_expiry" {
  description = "days until deletion"
  type        = number
}
variable "s3_kms_key" {
  description = "kms encryption key"
  type        = string
}

### security group
variable "sgr_ingress_cidr_blocks" {
  description = "Source networks for incoming traffic"
  type        = list(string)
}
variable "sgr_cidr_blocks" {
  description = "Source networks for incoming traffic"
  type        = string
}


