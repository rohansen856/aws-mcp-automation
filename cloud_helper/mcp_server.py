import os
import json
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import asyncpg
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
from plotly.io import to_json
import pandas as pd
import subprocess
import tempfile
import shutil

# Load environment variables
load_dotenv()

# Database connection pool
db_pool = None

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Initialize resources for the AWS MCP server"""
    global db_pool
    print("AWS MCP Server starting...")
    
    # Initialize database connection pool
    db_pool = await asyncpg.create_pool(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'aws_mcp'),
        min_size=1,
        max_size=10
    )
    
    # Create tables if they don't exist
    await init_database()
    
    yield {"initialized_at": datetime.now().isoformat()}
    
    # Cleanup
    await db_pool.close()
    print("AWS MCP Server shutting down...")

# Create the MCP server
mcp = FastMCP("aws_automation", lifespan=lifespan)

async def init_database():
    """Initialize database tables"""
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS aws_operations (
                id SERIAL PRIMARY KEY,
                operation_type VARCHAR(100) NOT NULL,
                parameters JSONB,
                result JSONB,
                status VARCHAR(50),
                error_message TEXT,
                user_query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS terraform_states (
                id SERIAL PRIMARY KEY,
                resource_type VARCHAR(100),
                resource_name VARCHAR(255),
                state JSONB,
                terraform_config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS cost_data (
                id SERIAL PRIMARY KEY,
                service VARCHAR(100),
                cost DECIMAL(10, 2),
                usage_type VARCHAR(255),
                date DATE,
                raw_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

async def log_operation(operation_type: str, parameters: Dict, result: Any, 
                       status: str, error_message: str = None, user_query: str = None,
                       execution_time_ms: int = None):
    """Log AWS operations to database"""
    async with db_pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO aws_operations 
            (operation_type, parameters, result, status, error_message, user_query, execution_time_ms)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        ''', operation_type, json.dumps(parameters), json.dumps(result) if result else None, 
            status, error_message, user_query, execution_time_ms)

def get_aws_client(service: str):
    """Get AWS client with credentials from environment"""
    return boto3.client(
        service,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )

def get_aws_resource(service: str):
    """Get AWS resource with credentials from environment"""
    return boto3.resource(
        service,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )

@mcp.tool()
async def create_ec2_instance(
    instance_type: str = "t2.micro",
    ami_id: Optional[str] = None,
    key_name: Optional[str] = None,
    security_group_ids: Optional[List[str]] = None,
    subnet_id: Optional[str] = None,
    name: Optional[str] = None,
    use_terraform: bool = True
) -> str:
    """
    Create an EC2 instance with specified configuration.
    
    This tool creates an AWS EC2 instance either directly through AWS API or using Terraform.
    If no AMI ID is provided, it will use the latest Ubuntu Server AMI.
    
    Parameters:
    - instance_type: EC2 instance type (default: t2.micro)
    - ami_id: AMI ID to use (optional, defaults to latest Ubuntu)
    - key_name: Name of the SSH key pair (optional)
    - security_group_ids: List of security group IDs (optional)
    - subnet_id: Subnet ID for the instance (optional)
    - name: Name tag for the instance (optional)
    - use_terraform: Whether to use Terraform for creation (default: True)
    
    Returns:
    - Success message with instance details or error message
    """
    start_time = datetime.now()
    
    try:
        if use_terraform:
            # Create Terraform configuration
            tf_config = await generate_ec2_terraform_config(
                instance_type, ami_id, key_name, security_group_ids, 
                subnet_id, name
            )
            
            # Execute Terraform
            result = await apply_terraform(tf_config, f"ec2_{name or 'instance'}")
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await log_operation(
                "create_ec2_instance",
                {
                    "instance_type": instance_type,
                    "ami_id": ami_id,
                    "name": name,
                    "use_terraform": True
                },
                result,
                "success",
                execution_time_ms=execution_time
            )
            
            return f"✅ EC2 instance created successfully using Terraform!\n{result}"
            
        else:
            # Direct AWS API call
            ec2 = get_aws_client('ec2')
            
            # Get latest Ubuntu AMI if not specified
            if not ami_id:
                response = ec2.describe_images(
                    Owners=['099720109477'],  # Canonical
                    Filters=[
                        {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
                        {'Name': 'state', 'Values': ['available']}
                    ]
                )
                ami_id = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)[0]['ImageId']
            
            # Prepare instance parameters
            params = {
                'ImageId': ami_id,
                'InstanceType': instance_type,
                'MinCount': 1,
                'MaxCount': 1
            }
            
            if key_name:
                params['KeyName'] = key_name
            if security_group_ids:
                params['SecurityGroupIds'] = security_group_ids
            if subnet_id:
                params['SubnetId'] = subnet_id
            
            # Create instance
            response = ec2.run_instances(**params)
            instance_id = response['Instances'][0]['InstanceId']
            
            # Add name tag if provided
            if name:
                ec2.create_tags(
                    Resources=[instance_id],
                    Tags=[{'Key': 'Name', 'Value': name}]
                )
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await log_operation(
                "create_ec2_instance",
                params,
                {"instance_id": instance_id},
                "success",
                execution_time_ms=execution_time
            )
            
            return f"✅ EC2 instance created successfully!\nInstance ID: {instance_id}\nAMI: {ami_id}\nType: {instance_type}"
            
    except Exception as e:
        await log_operation(
            "create_ec2_instance",
            {"instance_type": instance_type, "ami_id": ami_id},
            None,
            "error",
            str(e)
        )
        return f"❌ Error creating EC2 instance: {str(e)}"

@mcp.tool()
async def list_ec2_instances(
    state_filter: Optional[str] = None,
    tag_filters: Optional[Dict[str, str]] = None
) -> str:
    """
    List EC2 instances with optional filters.
    
    Parameters:
    - state_filter: Filter by instance state (running, stopped, terminated, etc.)
    - tag_filters: Dictionary of tag key-value pairs to filter by
    
    Returns:
    - Formatted list of EC2 instances with their details
    """
    try:
        ec2 = get_aws_client('ec2')
        
        # Build filters
        filters = []
        if state_filter:
            filters.append({'Name': 'instance-state-name', 'Values': [state_filter]})
        if tag_filters:
            for key, value in tag_filters.items():
                filters.append({'Name': f'tag:{key}', 'Values': [value]})
        
        # Describe instances
        response = ec2.describe_instances(Filters=filters)
        
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                # Extract instance details
                instance_info = {
                    'InstanceId': instance['InstanceId'],
                    'InstanceType': instance['InstanceType'],
                    'State': instance['State']['Name'],
                    'LaunchTime': instance.get('LaunchTime', '').isoformat() if instance.get('LaunchTime') else 'N/A',
                    'PublicIP': instance.get('PublicIpAddress', 'N/A'),
                    'PrivateIP': instance.get('PrivateIpAddress', 'N/A'),
                    'Name': next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'N/A')
                }
                instances.append(instance_info)
        
        await log_operation(
            "list_ec2_instances",
            {"state_filter": state_filter, "tag_filters": tag_filters},
            {"count": len(instances)},
            "success"
        )
        
        if not instances:
            return "No EC2 instances found matching the criteria."
        
        # Format output
        result = f"Found {len(instances)} EC2 instance(s):\n\n"
        for inst in instances:
            result += f"📦 Instance: {inst['Name']} ({inst['InstanceId']})\n"
            result += f"   Type: {inst['InstanceType']}\n"
            result += f"   State: {inst['State']}\n"
            result += f"   Public IP: {inst['PublicIP']}\n"
            result += f"   Private IP: {inst['PrivateIP']}\n"
            result += f"   Launch Time: {inst['LaunchTime']}\n\n"
        
        return result
        
    except Exception as e:
        await log_operation(
            "list_ec2_instances",
            {"state_filter": state_filter},
            None,
            "error",
            str(e)
        )
        return f"❌ Error listing EC2 instances: {str(e)}"

@mcp.tool()
async def get_cost_analysis(
    start_date: str,
    end_date: str,
    granularity: str = "MONTHLY",
    service_filter: Optional[str] = None,
    generate_graph: bool = True
) -> str:
    """
    Get AWS cost analysis for a specified period with optional visualization.
    
    Parameters:
    - start_date: Start date in YYYY-MM-DD format
    - end_date: End date in YYYY-MM-DD format
    - granularity: DAILY, MONTHLY, or HOURLY (default: MONTHLY)
    - service_filter: Filter by specific AWS service (optional)
    - generate_graph: Whether to generate a visualization (default: True)
    
    Returns:
    - Cost analysis summary and optionally a graph
    """
    try:
        ce = get_aws_client('ce')  # Cost Explorer
        
        # Build filters
        filters = None
        if service_filter:
            filters = {
                "Dimensions": {
                    "Key": "SERVICE",
                    "Values": [service_filter]
                }
            }
        
        # Get cost and usage
        response = ce.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity=granularity,
            Metrics=['UnblendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ],
            Filter=filters
        )
        
        # Process results
        cost_data = []
        for result in response['ResultsByTime']:
            period = result['TimePeriod']['Start']
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                cost_data.append({
                    'period': period,
                    'service': service,
                    'cost': cost
                })
        
        # Store in database
        async with db_pool.acquire() as conn:
            for item in cost_data:
                await conn.execute('''
                    INSERT INTO cost_data (service, cost, date, raw_data)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT DO NOTHING
                ''', item['service'], item['cost'], datetime.strptime(item['period'], '%Y-%m-%d').date(), json.dumps(item))
        
        await log_operation(
            "get_cost_analysis",
            {
                "start_date": start_date,
                "end_date": end_date,
                "granularity": granularity
            },
            {"total_periods": len(response['ResultsByTime'])},
            "success"
        )
        
        # Generate summary
        df = pd.DataFrame(cost_data)
        total_cost = df['cost'].sum()
        
        result = f"💰 AWS Cost Analysis ({start_date} to {end_date}):\n\n"
        result += f"Total Cost: ${total_cost:.2f}\n\n"
        
        # Top services by cost
        top_services = df.groupby('service')['cost'].sum().sort_values(ascending=False).head(10)
        result += "Top 10 Services by Cost:\n"
        for service, cost in top_services.items():
            result += f"  - {service}: ${cost:.2f}\n"
        
        # Generate graph if requested
        if generate_graph and not df.empty:
            graph_json = await generate_cost_graph(df, granularity)
            result += f"\n\n📊 Cost visualization data generated (JSON format available)"
            
            # Save graph data for potential display
            async with db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO aws_operations (operation_type, parameters, result, status)
                    VALUES ('cost_graph', $1, $2, 'success')
                ''', json.dumps({"type": "cost_analysis"}), graph_json)
        
        return result
        
    except Exception as e:
        await log_operation(
            "get_cost_analysis",
            {"start_date": start_date, "end_date": end_date},
            None,
            "error",
            str(e)
        )
        return f"❌ Error getting cost analysis: {str(e)}"

@mcp.tool()
async def list_s3_buckets(
    include_size: bool = False,
    include_object_count: bool = False
) -> str:
    """
    List all S3 buckets with optional size and object count information.
    
    Parameters:
    - include_size: Include bucket size information (may take longer)
    - include_object_count: Include object count (may take longer)
    
    Returns:
    - List of S3 buckets with requested details
    """
    try:
        s3 = get_aws_client('s3')
        
        # List buckets
        response = s3.list_buckets()
        buckets = response['Buckets']
        
        result = f"📦 Found {len(buckets)} S3 bucket(s):\n\n"
        
        for bucket in buckets:
            bucket_name = bucket['Name']
            creation_date = bucket['CreationDate'].strftime('%Y-%m-%d %H:%M:%S')
            
            result += f"🪣 Bucket: {bucket_name}\n"
            result += f"   Created: {creation_date}\n"
            
            # Get region
            try:
                location = s3.get_bucket_location(Bucket=bucket_name)
                region = location.get('LocationConstraint', 'us-east-1') or 'us-east-1'
                result += f"   Region: {region}\n"
            except:
                result += f"   Region: Unable to determine\n"
            
            # Get size and object count if requested
            if include_size or include_object_count:
                try:
                    cloudwatch = get_aws_client('cloudwatch')
                    
                    if include_size:
                        # Get bucket size from CloudWatch
                        size_metric = cloudwatch.get_metric_statistics(
                            Namespace='AWS/S3',
                            MetricName='BucketSizeBytes',
                            Dimensions=[
                                {'Name': 'BucketName', 'Value': bucket_name},
                                {'Name': 'StorageType', 'Value': 'StandardStorage'}
                            ],
                            StartTime=datetime.now() - timedelta(days=2),
                            EndTime=datetime.now(),
                            Period=86400,
                            Statistics=['Average']
                        )
                        
                        if size_metric['Datapoints']:
                            size_bytes = size_metric['Datapoints'][-1]['Average']
                            size_gb = size_bytes / (1024**3)
                            result += f"   Size: {size_gb:.2f} GB\n"
                    
                    if include_object_count:
                        # Get object count from CloudWatch
                        count_metric = cloudwatch.get_metric_statistics(
                            Namespace='AWS/S3',
                            MetricName='NumberOfObjects',
                            Dimensions=[
                                {'Name': 'BucketName', 'Value': bucket_name},
                                {'Name': 'StorageType', 'Value': 'AllStorageTypes'}
                            ],
                            StartTime=datetime.now() - timedelta(days=2),
                            EndTime=datetime.now(),
                            Period=86400,
                            Statistics=['Average']
                        )
                        
                        if count_metric['Datapoints']:
                            object_count = int(count_metric['Datapoints'][-1]['Average'])
                            result += f"   Objects: {object_count:,}\n"
                            
                except Exception as e:
                    result += f"   Metrics: Unable to retrieve\n"
            
            result += "\n"
        
        await log_operation(
            "list_s3_buckets",
            {"include_size": include_size, "include_object_count": include_object_count},
            {"bucket_count": len(buckets)},
            "success"
        )
        
        return result
        
    except Exception as e:
        await log_operation(
            "list_s3_buckets",
            {},
            None,
            "error",
            str(e)
        )
        return f"❌ Error listing S3 buckets: {str(e)}"

@mcp.tool()
async def execute_aws_command(
    service: str,
    action: str,
    parameters: Dict[str, Any]
) -> str:
    """
    Execute a generic AWS command for any service.
    
    This is a flexible tool that can execute any AWS API call.
    
    Parameters:
    - service: AWS service name (e.g., 'ec2', 's3', 'lambda')
    - action: API action to perform (e.g., 'describe_instances', 'list_objects')
    - parameters: Dictionary of parameters for the API call
    
    Returns:
    - JSON response from the AWS API
    """
    try:
        client = get_aws_client(service)
        
        # Get the method
        if not hasattr(client, action):
            return f"❌ Action '{action}' not found for service '{service}'"
        
        method = getattr(client, action)
        
        # Execute the command
        response = method(**parameters)
        
        # Remove ResponseMetadata for cleaner output
        if 'ResponseMetadata' in response:
            del response['ResponseMetadata']
        
        await log_operation(
            "execute_aws_command",
            {
                "service": service,
                "action": action,
                "parameters": parameters
            },
            response,
            "success"
        )
        
        # Format response
        import json
        formatted_response = json.dumps(response, indent=2, default=str)
        
        return f"✅ AWS Command executed successfully:\n\n```json\n{formatted_response}\n```"
        
    except Exception as e:
        await log_operation(
            "execute_aws_command",
            {
                "service": service,
                "action": action,
                "parameters": parameters
            },
            None,
            "error",
            str(e)
        )
        return f"❌ Error executing AWS command: {str(e)}"

@mcp.tool()
async def get_operation_history(
    operation_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    Get history of AWS operations performed through this service.
    
    Parameters:
    - operation_type: Filter by operation type (optional)
    - status: Filter by status (success/error) (optional)
    - limit: Maximum number of records to return (default: 10)
    
    Returns:
    - Formatted operation history
    """
    try:
        async with db_pool.acquire() as conn:
            # Build query
            query = "SELECT * FROM aws_operations WHERE 1=1"
            params = []
            param_count = 0
            
            if operation_type:
                param_count += 1
                query += f" AND operation_type = ${param_count}"
                params.append(operation_type)
            
            if status:
                param_count += 1
                query += f" AND status = ${param_count}"
                params.append(status)
            
            query += f" ORDER BY created_at DESC LIMIT ${param_count + 1}"
            params.append(limit)
            
            # Execute query
            rows = await conn.fetch(query, *params)
            
            if not rows:
                return "No operations found matching the criteria."
            
            result = f"📜 Operation History (Last {len(rows)} operations):\n\n"
            
            for row in rows:
                result += f"🔹 Operation: {row['operation_type']}\n"
                result += f"   Status: {'✅' if row['status'] == 'success' else '❌'} {row['status']}\n"
                result += f"   Time: {row['created_at'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                
                if row['execution_time_ms']:
                    result += f"   Duration: {row['execution_time_ms']}ms\n"
                
                if row['user_query']:
                    result += f"   Query: {row['user_query']}\n"
                
                if row['error_message']:
                    result += f"   Error: {row['error_message']}\n"
                
                result += "\n"
            
            return result
            
    except Exception as e:
        return f"❌ Error retrieving operation history: {str(e)}"

# Terraform Helper Functions

async def generate_ec2_terraform_config(
    instance_type: str,
    ami_id: Optional[str],
    key_name: Optional[str],
    security_group_ids: Optional[List[str]],
    subnet_id: Optional[str],
    name: Optional[str]
) -> str:
    """Generate Terraform configuration for EC2 instance"""
    
    # Get latest Ubuntu AMI if not specified
    if not ami_id:
        ec2 = get_aws_client('ec2')
        response = ec2.describe_images(
            Owners=['099720109477'],
            Filters=[
                {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
                {'Name': 'state', 'Values': ['available']}
            ]
        )
        ami_id = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)[0]['ImageId']
    
    tf_config = f'''
terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = "{os.getenv('AWS_DEFAULT_REGION', 'us-east-1')}"
}}

resource "aws_instance" "{name or 'main'}" {{
  ami           = "{ami_id}"
  instance_type = "{instance_type}"
'''
    
    if key_name:
        tf_config += f'  key_name      = "{key_name}"\n'
    
    if security_group_ids:
        tf_config += f'  vpc_security_group_ids = {json.dumps(security_group_ids)}\n'
    
    if subnet_id:
        tf_config += f'  subnet_id     = "{subnet_id}"\n'
    
    if name:
        tf_config += f'''
  tags = {{
    Name = "{name}"
  }}
'''
    
    tf_config += '}\n'
    
    tf_config += f'''
output "instance_id" {{
  value = aws_instance.{name or 'main'}.id
}}

output "public_ip" {{
  value = aws_instance.{name or 'main'}.public_ip
}}
'''
    
    return tf_config

async def apply_terraform(tf_config: str, resource_name: str) -> str:
    """Apply Terraform configuration"""
    try:
        # Create temporary directory for Terraform files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write configuration
            tf_file = os.path.join(tmpdir, 'main.tf')
            with open(tf_file, 'w') as f:
                f.write(tf_config)
            
            # Initialize Terraform
            init_result = subprocess.run(
                ['terraform', 'init'],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )
            
            if init_result.returncode != 0:
                raise Exception(f"Terraform init failed: {init_result.stderr}")
            
            # Plan
            plan_result = subprocess.run(
                ['terraform', 'plan', '-out=tfplan'],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )
            
            if plan_result.returncode != 0:
                raise Exception(f"Terraform plan failed: {plan_result.stderr}")
            
            # Apply
            apply_result = subprocess.run(
                ['terraform', 'apply', '-auto-approve', 'tfplan'],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )
            
            if apply_result.returncode != 0:
                raise Exception(f"Terraform apply failed: {apply_result.stderr}")
            
            # Get outputs
            output_result = subprocess.run(
                ['terraform', 'output', '-json'],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )
            
            outputs = json.loads(output_result.stdout) if output_result.stdout else {}
            
            # Save state to database
            state_result = subprocess.run(
                ['terraform', 'show', '-json'],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )
            
            state = json.loads(state_result.stdout) if state_result.stdout else {}
            
            async with db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO terraform_states (resource_type, resource_name, state, terraform_config)
                    VALUES ($1, $2, $3, $4)
                ''', 'ec2_instance', resource_name, json.dumps(state), tf_config)
            
            # Format output
            result = "Terraform execution completed successfully!\n\n"
            for key, value in outputs.items():
                result += f"{key}: {value.get('value', 'N/A')}\n"
            
            return result
            
    except Exception as e:
        raise Exception(f"Terraform execution failed: {str(e)}")

async def generate_cost_graph(df: pd.DataFrame, granularity: str) -> str:
    """Generate cost visualization using Plotly"""
    
    # Create figure based on granularity
    if granularity == "DAILY":
        # Line chart for daily costs
        fig = px.line(df, x='period', y='cost', color='service',
                     title='Daily AWS Costs by Service',
                     labels={'cost': 'Cost ($)', 'period': 'Date'})
        fig.update_layout(height=600, width=1000)
    else:
        # Bar chart for monthly costs
        pivot_df = df.pivot_table(values='cost', index='period', columns='service', aggfunc='sum').fillna(0)
        fig = go.Figure()
        
        for service in pivot_df.columns:
            fig.add_trace(go.Bar(
                name=service,
                x=pivot_df.index,
                y=pivot_df[service]
            ))
        
        fig.update_layout(
            title='Monthly AWS Costs by Service',
            xaxis_title='Period',
            yaxis_title='Cost ($)',
            barmode='stack',
            height=600,
            width=1000
        )
    
    # Convert to JSON for storage
    return to_json(fig)

@mcp.tool()
async def describe_terraform_state(resource_name: Optional[str] = None) -> str:
    """
    Get current Terraform state for managed resources.
    
    Parameters:
    - resource_name: Specific resource name to query (optional)
    
    Returns:
    - Current state of Terraform-managed resources
    """
    try:
        async with db_pool.acquire() as conn:
            if resource_name:
                row = await conn.fetchrow('''
                    SELECT * FROM terraform_states 
                    WHERE resource_name = $1 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', resource_name)
                
                if not row:
                    return f"No Terraform state found for resource: {resource_name}"
                
                state = row['state']
                resources = state.get('values', {}).get('root_module', {}).get('resources', [])
                
                result = f"📋 Terraform State for {resource_name}:\n\n"
                for resource in resources:
                    result += f"Resource: {resource['type']}.{resource['name']}\n"
                    result += f"Provider: {resource['provider_name']}\n"
                    
                    values = resource.get('values', {})
                    result += f"  ID: {values.get('id', 'N/A')}\n"
                    result += f"  ARN: {values.get('arn', 'N/A')}\n"
                    
                    if 'instance_state' in values:
                        result += f"  State: {values['instance_state']}\n"
                    
                    result += "\n"
                
                return result
            else:
                rows = await conn.fetch('''
                    SELECT DISTINCT ON (resource_name) 
                        resource_name, resource_type, created_at
                    FROM terraform_states 
                    ORDER BY resource_name, created_at DESC
                ''')
                
                if not rows:
                    return "No Terraform-managed resources found."
                
                result = "📋 Terraform-managed resources:\n\n"
                for row in rows:
                    result += f"• {row['resource_name']} ({row['resource_type']})\n"
                    result += f"  Last updated: {row['created_at'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                
                return result
                
    except Exception as e:
        return f"❌ Error retrieving Terraform state: {str(e)}"

@mcp.tool()
async def stop_ec2_instance(instance_id: str) -> str:
    """
    Stop a running EC2 instance.
    
    Parameters:
    - instance_id: The ID of the EC2 instance to stop
    
    Returns:
    - Success or error message
    """
    try:
        ec2 = get_aws_client('ec2')
        
        # Stop the instance
        response = ec2.stop_instances(InstanceIds=[instance_id])
        
        current_state = response['StoppingInstances'][0]['CurrentState']['Name']
        previous_state = response['StoppingInstances'][0]['PreviousState']['Name']
        
        await log_operation(
            "stop_ec2_instance",
            {"instance_id": instance_id},
            {"current_state": current_state, "previous_state": previous_state},
            "success"
        )
        
        return f"✅ EC2 instance {instance_id} stop initiated.\nPrevious state: {previous_state}\nCurrent state: {current_state}"
        
    except Exception as e:
        await log_operation(
            "stop_ec2_instance",
            {"instance_id": instance_id},
            None,
            "error",
            str(e)
        )
        return f"❌ Error stopping EC2 instance: {str(e)}"

@mcp.tool()
async def start_ec2_instance(instance_id: str) -> str:
    """
    Start a stopped EC2 instance.
    
    Parameters:
    - instance_id: The ID of the EC2 instance to start
    
    Returns:
    - Success or error message
    """
    try:
        ec2 = get_aws_client('ec2')
        
        # Start the instance
        response = ec2.start_instances(InstanceIds=[instance_id])
        
        current_state = response['StartingInstances'][0]['CurrentState']['Name']
        previous_state = response['StartingInstances'][0]['PreviousState']['Name']
        
        await log_operation(
            "start_ec2_instance",
            {"instance_id": instance_id},
            {"current_state": current_state, "previous_state": previous_state},
            "success"
        )
        
        return f"✅ EC2 instance {instance_id} start initiated.\nPrevious state: {previous_state}\nCurrent state: {current_state}"
        
    except Exception as e:
        await log_operation(
            "start_ec2_instance",
            {"instance_id": instance_id},
            None,
            "error",
            str(e)
        )
        return f"❌ Error starting EC2 instance: {str(e)}"

@mcp.tool()
async def terminate_ec2_instance(instance_id: str, use_terraform: bool = False) -> str:
    """
    Terminate an EC2 instance permanently.
    
    Parameters:
    - instance_id: The ID of the EC2 instance to terminate
    - use_terraform: If True, destroy using Terraform (if managed by Terraform)
    
    Returns:
    - Success or error message
    """
    try:
        if use_terraform:
            # Check if resource is managed by Terraform
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT * FROM terraform_states 
                    WHERE state::text LIKE $1 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', f'%{instance_id}%')
                
                if row:
                    # Destroy using Terraform
                    with tempfile.TemporaryDirectory() as tmpdir:
                        tf_file = os.path.join(tmpdir, 'main.tf')
                        with open(tf_file, 'w') as f:
                            f.write(row['terraform_config'])
                        
                        # Init and destroy
                        subprocess.run(['terraform', 'init'], cwd=tmpdir, capture_output=True)
                        destroy_result = subprocess.run(
                            ['terraform', 'destroy', '-auto-approve'],
                            cwd=tmpdir,
                            capture_output=True,
                            text=True
                        )
                        
                        if destroy_result.returncode != 0:
                            raise Exception(f"Terraform destroy failed: {destroy_result.stderr}")
                        
                        # Remove from database
                        await conn.execute(
                            'DELETE FROM terraform_states WHERE id = $1',
                            row['id']
                        )
                        
                        return f"✅ EC2 instance {instance_id} destroyed using Terraform"
        
        # Direct termination
        ec2 = get_aws_client('ec2')
        response = ec2.terminate_instances(InstanceIds=[instance_id])
        
        current_state = response['TerminatingInstances'][0]['CurrentState']['Name']
        previous_state = response['TerminatingInstances'][0]['PreviousState']['Name']
        
        await log_operation(
            "terminate_ec2_instance",
            {"instance_id": instance_id},
            {"current_state": current_state, "previous_state": previous_state},
            "success"
        )
        
        return f"✅ EC2 instance {instance_id} termination initiated.\nPrevious state: {previous_state}\nCurrent state: {current_state}"
        
    except Exception as e:
        await log_operation(
            "terminate_ec2_instance",
            {"instance_id": instance_id},
            None,
            "error",
            str(e)
        )
        return f"❌ Error terminating EC2 instance: {str(e)}"

@mcp.tool()
async def create_s3_bucket(
    bucket_name: str,
    region: Optional[str] = None,
    versioning: bool = False,
    encryption: bool = True,
    public_access_block: bool = True
) -> str:
    """
    Create a new S3 bucket with specified configuration.
    
    Parameters:
    - bucket_name: Name of the bucket (must be globally unique)
    - region: AWS region for the bucket (optional, defaults to configured region)
    - versioning: Enable versioning on the bucket
    - encryption: Enable default encryption
    - public_access_block: Block public access (recommended)
    
    Returns:
    - Success message with bucket details or error
    """
    try:
        s3 = get_aws_client('s3')
        region = region or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        # Create bucket
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        
        # Configure versioning
        if versioning:
            s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
        
        # Configure encryption
        if encryption:
            s3.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [{
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    }]
                }
            )
        
        # Configure public access block
        if public_access_block:
            s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
        
        await log_operation(
            "create_s3_bucket",
            {
                "bucket_name": bucket_name,
                "region": region,
                "versioning": versioning,
                "encryption": encryption
            },
            {"bucket_name": bucket_name},
            "success"
        )
        
        return f"✅ S3 bucket '{bucket_name}' created successfully!\nRegion: {region}\nVersioning: {'Enabled' if versioning else 'Disabled'}\nEncryption: {'Enabled' if encryption else 'Disabled'}\nPublic Access: {'Blocked' if public_access_block else 'Allowed'}"
        
    except Exception as e:
        await log_operation(
            "create_s3_bucket",
            {"bucket_name": bucket_name},
            None,
            "error",
            str(e)
        )
        return f"❌ Error creating S3 bucket: {str(e)}"

@mcp.tool()
async def get_aws_service_status(services: Optional[List[str]] = None) -> str:
    """
    Get the current status and health of AWS services.
    
    Parameters:
    - services: List of service names to check (optional, defaults to common services)
    
    Returns:
    - Status information for requested AWS services
    """
    try:
        if not services:
            services = ['ec2', 's3', 'rds', 'lambda', 'dynamodb']
        
        health = get_aws_client('health')
        
        result = "🏥 AWS Service Health Status:\n\n"
        
        for service in services:
            try:
                # Get service health
                response = health.describe_events(
                    filter={
                        'services': [service],
                        'eventStatusCodes': ['open', 'upcoming']
                    }
                )
                
                events = response.get('events', [])
                
                if events:
                    result += f"⚠️  {service.upper()}: {len(events)} active event(s)\n"
                    for event in events[:3]:  # Show first 3 events
                        result += f"   - {event.get('eventTypeCode', 'Unknown')}: {event.get('region', 'Global')}\n"
                else:
                    result += f"✅ {service.upper()}: Operational\n"
                    
            except Exception as e:
                result += f"❓ {service.upper()}: Unable to check status\n"
        
        # Get account-level information
        try:
            sts = get_aws_client('sts')
            account_info = sts.get_caller_identity()
            result += f"\n📊 Account Information:\n"
            result += f"   Account ID: {account_info['Account']}\n"
            result += f"   User ARN: {account_info['Arn']}\n"
        except:
            pass
        
        return result
        
    except Exception as e:
        return f"❌ Error checking AWS service status: {str(e)}"

if __name__ == "__main__":
    print("🚀 AWS Automation MCP Server Starting...")
    print(f"Region: {os.getenv('AWS_DEFAULT_REGION', 'us-east-1')}")
    mcp.run()