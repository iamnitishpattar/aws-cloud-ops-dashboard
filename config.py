import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # AWS Settings
    AWS_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    
    # We use a standard Amazon Linux 2 AMI for us-east-1. 
    # NOTE: If you change the region, you must update this AMI ID.
    AMI_ID = 'ami-0c101f26f147fa7fd' # Amazon Linux 2023 AMI in us-east-1
    INSTANCE_TYPE = 't2.micro'       # Free tier eligible
    
    KEY_NAME = 'cloud_computing_key'
    SECURITY_GROUP_NAME = 'cloud_computing_sg'
    
    # User Data script to run on boot: Updates system, installs Nginx, and starts it.
    USER_DATA_SCRIPT = '''#!/bin/bash
    yum update -y
    yum install -y nginx
    systemctl start nginx
    systemctl enable nginx
    echo "<h1>Welcome to your Automated Cloud Instance!</h1>" > /usr/share/nginx/html/index.html
    '''
