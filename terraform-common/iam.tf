
resource "aws_iam_policy" "ec2-secrets" {
  name        = "${local.name_prefix}-ec2-secrets"
  path        = "/"
  description = "allow ec2 to read secrets starting with aurora"
  policy = file("${path.module}/input-files/iam-ec2-secrets.json")
}

resource "aws_iam_policy" "ec2-cloudwatch" {
  name        = "${local.name_prefix}-ec2-cloudwatch"
  path        = "/"
  description = "allow ec2 to write to cloudwatch"
  policy = file("${path.module}/input-files/iam-ec2-cloudwatch.json")
}

resource "aws_iam_policy" "ec2-s3" {
  name        = "${local.name_prefix}-ec2-s3"
  path        = "/"
  description = "allow ec2 pod to read backup s3 buckets"
  policy = templatefile("${path.module}/input-files/iam-ec2-s3.json", {
    s3_bucket = aws_s3_bucket.backup_bucket.arn
  })
}

resource "aws_iam_policy" "ec2-s3-kms" {
  name        = "${local.name_prefix}-ec2-s3-kms"
  path        = "/"
  description = "allow ec2 pod to read backup s3 buckets"
  policy = templatefile("${path.module}/input-files/iam-ec2-s3-kms.json", {
    s3_kms_key = var.s3_kms_key
  })
}

resource "aws_iam_role" "ec2" {
  name = "${local.name_prefix}-ec2"
  path = "/"

  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }
    ]
}
EOF
}

# task role for ec2 permissions
resource "aws_iam_role_policy_attachment" "ec2-s3" {
  role        = aws_iam_role.ec2.name
  policy_arn  = aws_iam_policy.ec2-s3.arn
}

# task role for ec2 permissions
resource "aws_iam_role_policy_attachment" "ec2-secrets" {
  role        = aws_iam_role.ec2.name
  policy_arn  = aws_iam_policy.ec2-secrets.arn
}

# task role for cw permissions
resource "aws_iam_role_policy_attachment" "ec2-cloudwatch" {
  role        = aws_iam_role.ec2.name
  policy_arn  = aws_iam_policy.ec2-cloudwatch.arn
}

# task role for s3 kms permissions
resource "aws_iam_role_policy_attachment" "ec2-s3-kms" {
  role        = aws_iam_role.ec2.name
  policy_arn  = aws_iam_policy.ec2-s3-kms.arn
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${local.name_prefix}"
  role = aws_iam_role.ec2.name
}