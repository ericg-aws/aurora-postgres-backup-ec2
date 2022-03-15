output "ec2_security_group_id" {
  value       = "${module.sgr_ec2.security_group_id}"
  description = "ec2 security group id"
}

output "ec2_instance_profile" {
  value       = "${aws_iam_instance_profile.ec2.id}"
  description = "ec2 instance profile"
}