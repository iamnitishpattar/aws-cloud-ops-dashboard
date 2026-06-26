import boto3
from config import Config

def get_ec2_resource():
    return boto3.resource('ec2', region_name=Config.AWS_REGION)

def get_ec2_client():
    return boto3.client('ec2', region_name=Config.AWS_REGION)

def terminate_instance(instance_id):
    """Terminates a specific EC2 instance."""
    ec2_resource = get_ec2_resource()
    print(f"Terminating instance {instance_id}...")
    instance = ec2_resource.Instance(instance_id)
    instance.terminate()
    instance.wait_until_terminated()
    print(f"Instance {instance_id} terminated successfully.")

def terminate_all_project_instances():
    """Finds all instances with our project tag and terminates them."""
    ec2_client = get_ec2_client()
    print("Finding all instances created by this project...")
    response = ec2_client.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': ['Automated-Cloud-Instance']},
            {'Name': 'instance-state-name', 'Values': ['running', 'pending', 'stopped']}
        ]
    )
    
    instance_ids = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
            
    if not instance_ids:
        print("No project instances found to terminate.")
        return
        
    print(f"Found {len(instance_ids)} instance(s) to terminate: {', '.join(instance_ids)}")
    ec2_resource = get_ec2_resource()
    instances = ec2_resource.instances.filter(InstanceIds=instance_ids)
    instances.terminate()
    print("Termination signal sent. Waiting for instances to terminate...")
    
    for instance_id in instance_ids:
        ec2_resource.Instance(instance_id).wait_until_terminated()
        
    print("All project instances terminated.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "all":
            terminate_all_project_instances()
        else:
            terminate_instance(sys.argv[1])
    else:
        print("Usage: python terminate.py <instance_id> | all")
