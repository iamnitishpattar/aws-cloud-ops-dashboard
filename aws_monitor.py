import boto3
from datetime import datetime, timedelta
from config import Config

def get_cloudwatch_client():
    return boto3.client('cloudwatch', region_name=Config.AWS_REGION)

def get_instance_metric(cw_client, instance_id, metric_name, namespace='AWS/EC2'):
    """Fetches a specific metric for an instance from the last 15 minutes."""
    start_time = datetime.utcnow() - timedelta(minutes=15)
    end_time = datetime.utcnow()

    response = cw_client.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=300, # 5 minutes
        Statistics=['Average']
    )
    
    datapoints = response.get('Datapoints', [])
    if not datapoints:
        return "No data available yet"
    
    # Sort and return the most recent data point
    latest = sorted(datapoints, key=lambda x: x['Timestamp'], reverse=True)[0]
    return f"{latest['Average']:.2f}"

def monitor_instance(instance_id):
    """Monitors CPU and Network for a given instance ID and returns a dict."""
    cw_client = get_cloudwatch_client()
    
    cpu = get_instance_metric(cw_client, instance_id, 'CPUUtilization')
    net_in = get_instance_metric(cw_client, instance_id, 'NetworkIn')
    net_out = get_instance_metric(cw_client, instance_id, 'NetworkOut')
    
    return {
        "instance_id": instance_id,
        "cpu": cpu,
        "net_in": net_in,
        "net_out": net_out
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        metrics = monitor_instance(sys.argv[1])
        print("="*40)
        print(f"Instance ID : {metrics['instance_id']}")
        print(f"CPU Util    : {metrics['cpu']} %")
        print(f"Net In      : {metrics['net_in']} bytes")
        print(f"Net Out     : {metrics['net_out']} bytes")
        print("="*40)
    else:
        print("Usage: python aws_monitor.py <instance_id>")
