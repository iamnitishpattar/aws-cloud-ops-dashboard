import argparse
import sys
from aws_deploy import deploy_instance
from aws_monitor import monitor_instance
from terminate import terminate_instance, terminate_all_project_instances
import boto3
from config import Config

def get_instances():
    """Returns a list of dictionaries containing project instances."""
    ec2_client = boto3.client('ec2', region_name=Config.AWS_REGION)
    response = ec2_client.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': ['Automated-*-Instance']}
        ]
    )
    
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            state = instance['State']['Name']
            ip = instance.get('PublicIpAddress', 'N/A')
            iid = instance['InstanceId']
            
            # Extract the Name tag
            instance_name = 'Automated-Cloud-Instance'
            if 'Tags' in instance:
                for tag in instance['Tags']:
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
            
            instances.append({
                'id': iid,
                'name': instance_name,
                'state': state,
                'ip': ip
            })
    return instances

def list_instances():
    """Lists all instances related to this project (CLI version)."""
    print("Fetching active project instances...")
    instances = get_instances()
    
    print("-" * 85)
    print(f"{'Instance ID':<20} | {'Name':<25} | {'State':<10} | {'Public IP':<15}")
    print("-" * 85)
    
    if not instances:
        print("No instances found.")
    else:
        for inst in instances:
            print(f"{inst['id']:<20} | {inst['state']:<10} | {inst['ip']:<15}")
            
    print("-" * 65)

def main():
    parser = argparse.ArgumentParser(description="Automated Cloud Deployment & Monitoring Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Deploy command
    subparsers.add_parser("deploy", help="Deploy a new EC2 instance with Nginx")

    # List command
    subparsers.add_parser("list", help="List all deployed project instances")

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor a specific instance")
    monitor_parser.add_argument("instance_id", help="The ID of the instance to monitor")

    # Terminate command
    terminate_parser = subparsers.add_parser("terminate", help="Terminate instance(s)")
    terminate_parser.add_argument("target", help="Instance ID, or 'all' to terminate all project instances")

    args = parser.parse_args()

    if args.command == "deploy":
        deploy_instance()
    elif args.command == "list":
        list_instances()
    elif args.command == "monitor":
        monitor_instance(args.instance_id)
    elif args.command == "terminate":
        if args.target == "all":
            terminate_all_project_instances()
        else:
            terminate_instance(args.target)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
