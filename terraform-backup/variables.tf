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

### ec2
variable "ec2_ami" {
  description = "AMI image ID"
  type        = string
}
variable "ec2_key_name" {
  description = "Access key name"
  type        = string
}
variable "ec2_type" {
  description = "Instance type"
  type        = string
}

