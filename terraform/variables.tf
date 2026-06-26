variable "aws_region" {
  description = "The AWS region to deploy to"
  default     = "us-east-1"
}

variable "instance_type" {
  description = "The EC2 instance type"
  default     = "t2.micro"
}

variable "ami_id" {
  description = "The AMI ID for the EC2 instance (Amazon Linux 2023)"
  default     = "ami-05b10e08d247fb927"
}

variable "key_name" {
  description = "The name of the SSH key pair"
  default     = "cloud_computing_key"
}
