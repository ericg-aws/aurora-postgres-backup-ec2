output "ec2_instance_id" {
  value       = "${module.ec2_instance.id}"
  description = "ec2 instance ID"
}