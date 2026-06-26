provider "aws" {
  region = var.aws_region
}

# 1. Provide an Existing Key Pair or create one
# Assuming 'cloud_computing_key' is already created by Python, we just reference it or create a new one.
# For demo purposes, we will just use the name of the existing key.

# 2. Security Group
resource "aws_security_group" "project_sg" {
  name        = "cloud_computing_sg_terraform"
  description = "Security group for Cloud Computing Project (Terraform)"

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP (Nginx)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Jenkins
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Gitea
  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Grafana
  ingress {
    from_port   = 3001
    to_port     = 3001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Prometheus
  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # WireGuard UDP
  ingress {
    from_port   = 51820
    to_port     = 51820
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # WireGuard Web UI
  ingress {
    from_port   = 51821
    to_port     = 51821
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 3. EC2 Instance
resource "aws_instance" "full_stack" {
  ami           = var.ami_id
  instance_type = var.instance_type
  key_name      = var.key_name
  vpc_security_group_ids = [aws_security_group.project_sg.id]

  tags = {
    Name = "Automated-full_stack-Instance-Terraform"
  }

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y --allowerasing docker jq git

    # Create a 2GB swapfile to prevent OOM crashes on t2.micro
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab

    systemctl start docker
    systemctl enable docker
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose

    PUBLIC_IP=$(curl -s ifconfig.me)

    mkdir -p /opt/fullstack/nginx
    mkdir -p /opt/fullstack/prometheus
    cd /opt/fullstack

    cat << 'YML' > docker-compose.yml
    version: '3.8'
    services:
      gitea:
        image: gitea/gitea:latest
        restart: always
        environment:
          - USER_UID=1000
          - USER_GID=1000
          - GITEA__database__DB_TYPE=sqlite3
        ports:
          - "3000:3000"
          - "2222:22"
        volumes:
          - ./gitea:/data
          
      jenkins:
        image: jenkins/jenkins:lts
        restart: always
        user: root
        ports:
          - "8080:8080"
          - "50000:50000"
        volumes:
          - ./jenkins:/var/jenkins_home
          
      prometheus:
        image: prom/prometheus:latest
        restart: always
        volumes:
          - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
        ports:
          - "9090:9090"
          
      grafana:
        image: grafana/grafana:latest
        restart: always
        ports:
          - "3001:3000"
        environment:
          - GF_SECURITY_ADMIN_PASSWORD=admin
          
      node-exporter:
        image: prom/node-exporter:latest
        restart: always
        ports:
          - "9100:9100"
          
      nginx:
        image: nginx:alpine
        restart: always
        ports:
          - "80:80"
        volumes:
          - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    YML

    cat << NGINX > nginx/nginx.conf
    events {}
    http {
        server {
            listen 80;
            server_name gitea.$${PUBLIC_IP}.nip.io;
            location / {
                proxy_pass http://gitea:3000;
                proxy_set_header Host \$host;
                proxy_set_header X-Real-IP \$remote_addr;
            }
        }
        server {
            listen 80;
            server_name jenkins.$${PUBLIC_IP}.nip.io;
            location / {
                proxy_pass http://jenkins:8080;
                proxy_set_header Host \$host;
                proxy_set_header X-Real-IP \$remote_addr;
            }
        }
        server {
            listen 80;
            server_name grafana.$${PUBLIC_IP}.nip.io;
            location / {
                proxy_pass http://grafana:3000;
                proxy_set_header Host \$host;
            }
        }
        server {
            listen 80;
            server_name prometheus.$${PUBLIC_IP}.nip.io;
            location / {
                proxy_pass http://prometheus:9090;
                proxy_set_header Host \$host;
            }
        }
    }
    NGINX

    cat << 'PROM' > prometheus/prometheus.yml
    global:
      scrape_interval: 15s
    scrape_configs:
      - job_name: 'node'
        static_configs:
          - targets: ['node-exporter:9100']
    PROM

    docker-compose up -d
  EOF
}
