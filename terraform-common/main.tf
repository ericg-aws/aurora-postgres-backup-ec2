provider "aws" {
    region = var.region
}

locals {
  name_prefix = "${var.project}-${var.environment}"
}

locals {
  common_tags = {
    terraform           = "true"
    terraform_workspace = terraform.workspace
    project             = var.project
    environment         = var.environment
    auto-delete         = "no"
  }
}

module "sgr_ec2" {
  source = "terraform-aws-modules/security-group/aws"
  version = ">= 4.8.0 , < 5.0"

  name                = "${local.name_prefix}-ec2"
  description         = "temp ec2 backup instance"
  vpc_id              = var.vpc_id
  ingress_cidr_blocks = var.sgr_ingress_cidr_blocks

  ingress_with_cidr_blocks = []

  egress_with_cidr_blocks = [
    {
      from_port   = 0
      to_port     = 0
      protocol    = -1
      description = "all ports"
      cidr_blocks = "0.0.0.0/0"
      self        = true
    }
  ]

  tags = local.common_tags
}


resource "aws_vpc_endpoint" "s3" {
  vpc_id       = var.vpc_id
  service_name = "com.amazonaws.${var.region}.s3"

  tags = local.common_tags
}

resource "aws_vpc_endpoint_route_table_association" "associate1" {
  route_table_id = "rtb-0285ca1f790ca8734"
  vpc_endpoint_id = aws_vpc_endpoint.s3.id
}

resource "aws_vpc_endpoint_route_table_association" "associate2" {
  route_table_id = "rtb-039fa1beb348ef210"
  vpc_endpoint_id = aws_vpc_endpoint.s3.id
}