output "instance_id" {
  description = "The ID of the EC2 instance"
  value       = aws_instance.full_stack.id
}

output "public_ip" {
  description = "The public IP of the EC2 instance"
  value       = aws_instance.full_stack.public_ip
}

output "gitea_url" {
  description = "URL to access Gitea"
  value       = "http://${aws_instance.full_stack.public_ip}:3000"
}

output "jenkins_url" {
  description = "URL to access Jenkins"
  value       = "http://${aws_instance.full_stack.public_ip}:8080"
}

output "grafana_url" {
  description = "URL to access Grafana"
  value       = "http://${aws_instance.full_stack.public_ip}:3001"
}

output "alertmanager_url" {
  description = "URL to access Alertmanager"
  value       = "http://${aws_instance.full_stack.public_ip}:9093"
}
