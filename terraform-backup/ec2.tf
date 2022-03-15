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

locals {
    # get json output from earlier terraform run
    common_data = jsondecode(file("${path.module}/../tmp/terraform-output.json"))
}

locals {
    # get json output from earlier python db info gathering script
    db_data = jsondecode(file("${path.module}/../tmp/db.json"))
}

output "show_locals" {
  value = local.db_data.subnet_id
}

resource "random_integer" "ec2" {
  min = 10000
  max = 20000
}

module "ec2_instance" {
  source  = "terraform-aws-modules/ec2-instance/aws"
  version = ">= 3.4.0, < 4.0"

  name = "${local.name_prefix}-${random_integer.ec2.result}"

  ami                                   = var.ec2_ami
  instance_type                         = var.ec2_type
  key_name                              = var.ec2_key_name
  monitoring                            = true
  vpc_security_group_ids                = ["${local.common_data.ec2_security_group_id.value}"]
  subnet_id                             = "${local.db_data.subnet_id}"
  ebs_optimized                         = true
  instance_initiated_shutdown_behavior  = "terminate"
  iam_instance_profile                  = "${local.common_data.ec2_instance_profile.value}"
  
  #spot_instance_interruption_behavior   = "terminate"
  #create_spot_instance                  = true

  enable_volume_tags                    = false
  root_block_device = [
    {
      encrypted   = true
      volume_type = "gp3"
      throughput  = 800
      volume_size = 1024
      iops        = 6000
      tags = local.common_tags
    },
  ]

  tags = local.common_tags
}