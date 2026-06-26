import boto3
import os
from botocore.exceptions import ClientError
from config import Config

def get_ec2_client():
    return boto3.client('ec2', region_name=Config.AWS_REGION)

def get_ec2_resource():
    return boto3.resource('ec2', region_name=Config.AWS_REGION)

def setup_key_pair(ec2_client):
    """Creates a new key pair or uses an existing one."""
    print(f"Setting up Key Pair: {Config.KEY_NAME}...")
    try:
        key_pair = ec2_client.create_key_pair(KeyName=Config.KEY_NAME)
        private_key = key_pair['KeyMaterial']
        
        # Save private key to a file
        key_file = f"{Config.KEY_NAME}.pem"
        with open(key_file, 'w') as f:
            f.write(private_key)
        
        # Set permissions for the key file (Unix only, but won't hurt on Windows if ignored)
        try:
            os.chmod(key_file, 0o400)
        except Exception:
            pass
            
        print(f"Key Pair created and saved as {key_file}")
    except ClientError as e:
        if 'InvalidKeyPair.Duplicate' in str(e):
            print("Key Pair already exists. Using existing key.")
        else:
            raise

def setup_security_group(ec2_client):
    """Creates a security group allowing SSH and HTTP."""
    print(f"Setting up Security Group: {Config.SECURITY_GROUP_NAME}...")
    try:
        response = ec2_client.create_security_group(
            GroupName=Config.SECURITY_GROUP_NAME,
            Description='Allow SSH, HTTP, and Minecraft access'
        )
        sg_id = response['GroupId']
        print(f"Security Group created with ID: {sg_id}")
    except ClientError as e:
        if 'InvalidGroup.Duplicate' in str(e):
            print("Security Group already exists. Retrieving its ID...")
            response = ec2_client.describe_security_groups(GroupNames=[Config.SECURITY_GROUP_NAME])
            sg_id = response['SecurityGroups'][0]['GroupId']
        else:
            raise

    # Always try to add inbound rules (ignores errors if rules already exist)
    try:
        ec2_client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 8080, 'ToPort': 8080, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 3000, 'ToPort': 3000, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 3001, 'ToPort': 3001, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 9090, 'ToPort': 9090, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 51821, 'ToPort': 51821, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'udp', 'FromPort': 51820, 'ToPort': 51820, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 25565, 'ToPort': 25565, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 9093, 'ToPort': 9093, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        )
        print("Inbound rules added successfully.")
    except ClientError:
        pass # Rules likely already exist
        
    return sg_id

def deploy_instance(template='jenkins'):
    ec2 = get_ec2_resource()
    ec2_client = get_ec2_client()
    
    key_name = Config.KEY_NAME
    setup_key_pair(ec2_client)
    sg_id = setup_security_group(ec2_client)
    
    # Define User Data scripts for different templates
    user_data_scripts = {
        'jenkins': """#!/bin/bash
yum update -y
wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key
yum install java-21-amazon-corretto -y
yum install jenkins -y
yum install iptables -y
systemctl start jenkins
systemctl enable jenkins
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
""",
        'wordpress': """#!/bin/bash
yum update -y
yum install -y httpd mariadb105-server php8.2 php8.2-mysqlnd
systemctl start httpd
systemctl enable httpd
systemctl start mariadb
systemctl enable mariadb
mysql -e "CREATE DATABASE wordpress; CREATE USER 'wordpress'@'localhost' IDENTIFIED BY 'password'; GRANT ALL PRIVILEGES ON wordpress.* TO 'wordpress'@'localhost'; FLUSH PRIVILEGES;"
usermod -a -G apache ec2-user
chown -R ec2-user:apache /var/www
chmod 2775 /var/www
wget https://wordpress.org/latest.tar.gz
tar -xzf latest.tar.gz
cp -r wordpress/* /var/www/html/
cd /var/www/html/
cp wp-config-sample.php wp-config.php
sed -i "s/database_name_here/wordpress/" wp-config.php
sed -i "s/username_here/wordpress/" wp-config.php
sed -i "s/password_here/password/" wp-config.php
chown -R apache:apache /var/www/html/
systemctl restart httpd
""",
        'minecraft': """#!/bin/bash
yum update -y
yum install java-17-amazon-corretto -y
adduser minecraft
su - minecraft -c "wget https://piston-data.mojang.com/v1/objects/8f3112a1049751cc472ec13e397eade5336ca7ae/server.jar"
su - minecraft -c "echo 'eula=true' > eula.txt"
su - minecraft -c "nohup java -Xmx1024M -Xms1024M -jar server.jar nogui &"
""",
        'gitea': """#!/bin/bash
yum update -y
yum install docker iptables -y
systemctl start docker
systemctl enable docker
docker run -d --name gitea -p 3000:3000 -p 2222:22 --restart always -v /var/lib/gitea:/data gitea/gitea:latest
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 3000
""",
        'wireguard': """#!/bin/bash
yum update -y
yum install docker iptables -y
systemctl start docker
systemctl enable docker
PUBLIC_IP=$(curl -s ifconfig.me)
docker run -d --name=wg-easy -e WG_HOST="$PUBLIC_IP" -e PASSWORD_HASH='$2a$12$qlJdAgcMTCxRuetY83cvI.rGfDu2eqeqCMjk3TnthYcbBxRsqvhNm' -v /etc/wireguard:/etc/wireguard -p 51820:51820/udp -p 51821:51821/tcp --cap-add=NET_ADMIN --cap-add=SYS_MODULE --sysctl="net.ipv4.conf.all.src_valid_mark=1" --sysctl="net.ipv4.ip_forward=1" --restart always ghcr.io/wg-easy/wg-easy
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 51821
""",
        'full_stack': """#!/bin/bash
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
mkdir -p /opt/fullstack/alertmanager
cd /opt/fullstack

cat << 'EOF' > docker-compose.yml
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
      - ./prometheus/alert_rules.yml:/etc/prometheus/alert_rules.yml
    ports:
      - "9090:9090"
    depends_on:
      - alertmanager
      
  alertmanager:
    image: prom/alertmanager:latest
    restart: always
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    ports:
      - "9093:9093"
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      
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
EOF

cat << EOF > nginx/nginx.conf
events {}
http {
    server {
        listen 80;
        server_name gitea.${PUBLIC_IP}.nip.io;
        location / {
            proxy_pass http://gitea:3000;
            proxy_set_header Host \\$host;
            proxy_set_header X-Real-IP \\$remote_addr;
        }
    }
    server {
        listen 80;
        server_name jenkins.${PUBLIC_IP}.nip.io;
        location / {
            proxy_pass http://jenkins:8080;
            proxy_set_header Host \\$host;
            proxy_set_header X-Real-IP \\$remote_addr;
        }
    }
    server {
        listen 80;
        server_name grafana.${PUBLIC_IP}.nip.io;
        location / {
            proxy_pass http://grafana:3000;
            proxy_set_header Host \\$host;
        }
    }
    server {
        listen 80;
        server_name prometheus.${PUBLIC_IP}.nip.io;
        location / {
            proxy_pass http://prometheus:9090;
            proxy_set_header Host \\$host;
        }
    }
}
EOF

cat << 'EOF' > prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - 'alert_rules.yml'

scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF

cat << 'EOF' > prometheus/alert_rules.yml
groups:
  - name: instance_alerts
    rules:
      - alert: InstanceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Instance {{ $labels.instance }} is DOWN"
          description: "{{ $labels.instance }} of job {{ $labels.job }} has been down for more than 1 minute."

      - alert: HighCpuUsage
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is above 80% for more than 2 minutes (current value: {{ $value }}%)."

      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage is above 80% for more than 2 minutes (current value: {{ $value }}%)."

      - alert: HighDiskUsage
        expr: (1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High disk usage on {{ $labels.instance }}"
          description: "Disk usage is above 85% for more than 5 minutes (current value: {{ $value }}%)."
EOF

cat << 'EOF' > alertmanager/alertmanager.yml
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'nitishpattar7@gmail.com'
  smtp_auth_username: 'nitishpattar7@gmail.com'
  smtp_auth_password: 'ueni hatn faga nuwd'
  smtp_require_tls: true

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'all-notifications'

receivers:
  - name: 'all-notifications'
    email_configs:
      - to: 'nitishpattar7@gmail.com'
        send_resolved: true
        headers:
          Subject: '{{ .Status | toUpper }} | Cloud Alert: {{ .CommonLabels.alertname }}'
    webhook_configs:
      - url: 'http://telegram-bot:8000/alert'
        send_resolved: true
EOF

# Create a simple Telegram alert forwarder
mkdir -p /opt/fullstack/telegram-bot
cat << 'PYEOF' > /opt/fullstack/telegram-bot/bot.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse

BOT_TOKEN = "8610923558:AAEe6pz1C59YReqRRQ5wNFVQaW0fJNxCzu0"
CHAT_ID = "8566134275"

class AlertHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
            for alert in data.get('alerts', []):
                status = alert.get('status', 'unknown').upper()
                labels = alert.get('labels', {})
                annotations = alert.get('annotations', {})
                emoji = '\U0001F6A8' if status == 'FIRING' else '\u2705'
                msg = f"{emoji} *{status}*\n"
                msg += f"*Alert:* {labels.get('alertname', 'N/A')}\n"
                msg += f"*Severity:* {labels.get('severity', 'N/A')}\n"
                msg += f"*Summary:* {annotations.get('summary', 'N/A')}\n"
                msg += f"*Description:* {annotations.get('description', 'N/A')}"
                send_telegram(msg)
        except Exception as e:
            print(f"Error: {e}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'ok')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = urllib.parse.urlencode({
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }).encode()
    try:
        req = urllib.request.Request(url, data=payload)
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Telegram send error: {e}")

if __name__ == '__main__':
    print("Telegram Alert Bot listening on port 8000...")
    HTTPServer(('0.0.0.0', 8000), AlertHandler).serve_forever()
PYEOF

# Add telegram-bot service to docker-compose using volume mount (no build needed)
cat << 'EOF' >> /opt/fullstack/docker-compose.yml

  telegram-bot:
    image: python:3.11-alpine
    restart: always
    working_dir: /app
    command: python bot.py
    volumes:
      - ./telegram-bot/bot.py:/app/bot.py
    ports:
      - "8000:8000"
EOF

docker-compose up -d
"""
    }
    
    selected_script = user_data_scripts.get(template, user_data_scripts['jenkins'])

    print(f"Deploying {template} instance...")
    
    instances = ec2.create_instances(
        ImageId=Config.AMI_ID,
        InstanceType=Config.INSTANCE_TYPE,
        MinCount=1,
        MaxCount=1,
        KeyName=key_name,
        SecurityGroupIds=[sg_id],
        UserData=selected_script,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [{'Key': 'Name', 'Value': f'Automated-{template}-Instance'}]
            }
        ]
    )
    
    instance = instances[0]
    print(f"Instance {instance.id} created. Waiting for it to enter 'running' state...")
    instance.wait_until_running()
    instance.reload()
    
    print(f"Instance is running! Public IP: {instance.public_ip_address}")
    print(f"You can access the web server at: http://{instance.public_ip_address} (It might take a minute or two to start)")
    return instance.id

if __name__ == "__main__":
    deploy_instance()
