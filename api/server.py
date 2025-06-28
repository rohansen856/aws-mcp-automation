import os
import json
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from decimal import Decimal
from functools import wraps
import traceback

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import asyncpg
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
from plotly.io import to_json
import pandas as pd
import subprocess
import tempfile
import shutil
from  marshmallow import Schema, fields, validate, ValidationError
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Database connection pool
db_pool = None

# Validation Schemas
class EC2InstanceSchema(Schema):
    instance_type = fields.String(required=False, 
                                 validate=validate.OneOf([
                                     "t2.micro", "t2.small", "t2.medium", "t2.large",
                                     "t3.micro", "t3.small", "t3.medium", "t3.large",
                                     "m5.large", "m5.xlarge", "c5.large", "c5.xlarge"
                                 ]))
    ami_id = fields.String(required=False, allow_none=True)
    key_name = fields.String(required=False, allow_none=True)
    security_group_ids = fields.List(fields.String(), required=False, allow_none=True)
    subnet_id = fields.String(required=False, allow_none=True)
    name = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))
    use_terraform = fields.Boolean(required=False)

class CostAnalysisSchema(Schema):
    start_date = fields.Date(required=True, format="%Y-%m-%d")
    end_date = fields.Date(required=True, format="%Y-%m-%d")
    granularity = fields.String(required=False,
                               validate=validate.OneOf(["DAILY", "MONTHLY", "HOURLY"]))
    service_filter = fields.String(required=False, allow_none=True)
    generate_graph = fields.Boolean(required=False)

class S3BucketSchema(Schema):
    bucket_name = fields.String(required=True, validate=[
        validate.Length(min=3, max=63),
        validate.Regexp(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$')
    ])
    region = fields.String(required=False, allow_none=True)
    versioning = fields.Boolean(required=False)
    encryption = fields.Boolean(required=False)
    public_access_block = fields.Boolean(required=False)

class AWSCommandSchema(Schema):
    service = fields.String(required=True, validate=validate.Length(min=2, max=50))
    action = fields.String(required=True, validate=validate.Length(min=2, max=100))
    parameters = fields.Dict(required=False,)

# Error handlers
@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify({"error": "Validation error", "messages": e.messages}), 400

@app.errorhandler(404)
def handle_not_found(_):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def handle_internal_error(e):
    logger.error(f"Internal error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500

# Helper decorators
def validate_json(schema_class):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            schema = schema_class()
            try:
                data = schema.load(request.get_json() or {})
                return f(data, *args, **kwargs)
            except ValidationError as err:
                return jsonify({"error": "Validation error", "messages": err.messages}), 400
        return decorated_function
    return decorator

def async_route(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return decorated_function

# Database initialization
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
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO aws_operations 
                (operation_type, parameters, result, status, error_message, user_query, execution_time_ms)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''', operation_type, json.dumps(parameters), json.dumps(result) if result else None, 
                status, error_message, user_query, execution_time_ms)
    except Exception as e:
        logger.error(f"Failed to log operation: {str(e)}")

# AWS client helpers
def get_aws_client(service: str):
    """Get AWS client with credentials from environment"""
    try:
        return boto3.client(
            service,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        )
    except NoCredentialsError:
        raise Exception("AWS credentials not configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")

def get_aws_resource(service: str):
    """Get AWS resource with credentials from environment"""
    try:
        return boto3.resource(
            service,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        )
    except NoCredentialsError:
        raise Exception("AWS credentials not configured.")

# Streaming helper
def stream_response(message: str, status: str = "info"):
    """Helper to format streaming responses"""
    return json.dumps({"message": message, "status": status}) + "\n"

# API Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "aws_region": os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    })

@app.route('/ec2/instances', methods=['POST'])
@async_route
@validate_json(EC2InstanceSchema)
async def create_ec2_instance(data):
    """Create EC2 instance endpoint"""
    def generate():
        yield stream_response("Starting EC2 instance creation...", "info")
        
        start_time = datetime.now()
        
        try:
            instance_type = data.get('instance_type', 't2.micro')
            ami_id = data.get('ami_id')
            key_name = data.get('key_name')
            security_group_ids = data.get('security_group_ids')
            subnet_id = data.get('subnet_id')
            name = data.get('name')
            use_terraform = data.get('use_terraform', True)
            
            if use_terraform:
                yield stream_response("Generating Terraform configuration...", "info")
                # Terraform implementation would go here
                yield stream_response("Terraform execution not implemented in this demo", "warning")
            else:
                yield stream_response("Creating EC2 instance via AWS API...", "info")
                
                ec2 = get_aws_client('ec2')
                
                # Get latest Ubuntu AMI if not specified
                if not ami_id:
                    yield stream_response("Finding latest Ubuntu AMI...", "info")
                    response = ec2.describe_images(
                        Owners=['099720109477'],
                        Filters=[
                            {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
                            {'Name': 'state', 'Values': ['available']}
                        ]
                    )
                    ami_id = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)[0]['ImageId']
                    yield stream_response(f"Selected AMI: {ami_id}", "info")
                
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
                yield stream_response("Launching instance...", "info")
                response = ec2.run_instances(**params)
                instance_id = response['Instances'][0]['InstanceId']
                
                # Add name tag if provided
                if name:
                    yield stream_response(f"Adding name tag: {name}", "info")
                    ec2.create_tags(
                        Resources=[instance_id],
                        Tags=[{'Key': 'Name', 'Value': name}]
                    )
                
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                # Log operation asynchronously
                asyncio.create_task(log_operation(
                    "create_ec2_instance",
                    params,
                    {"instance_id": instance_id},
                    "success",
                    execution_time_ms=execution_time
                ))
                
                yield stream_response(f"✅ EC2 instance created successfully!", "success")
                yield stream_response(f"Instance ID: {instance_id}", "success")
                yield stream_response(f"AMI: {ami_id}", "info")
                yield stream_response(f"Type: {instance_type}", "info")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error creating EC2 instance: {error_msg}")
            yield stream_response(f"❌ Error: {error_msg}", "error")
            
            # Log error asynchronously
            asyncio.create_task(log_operation(
                "create_ec2_instance",
                data,
                None,
                "error",
                error_msg
            ))
    
    return Response(stream_with_context(generate()), content_type='application/x-ndjson')

@app.route('/ec2/instances', methods=['GET'])
@async_route
async def list_ec2_instances():
    """List EC2 instances endpoint"""
    async def generate():
        yield stream_response("Fetching EC2 instances...", "info")
        
        try:
            state_filter = request.args.get('state')
            tag_filters = {}
            
            # Parse tag filters from query params
            for key, value in request.args.items():
                if key.startswith('tag_'):
                    tag_name = key[4:]  # Remove 'tag_' prefix
                    tag_filters[tag_name] = value
            
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
            
            yield stream_response(f"Found {len(instances)} EC2 instance(s)", "info")
            
            for inst in instances:
                yield stream_response(f"📦 Instance: {inst['Name']} ({inst['InstanceId']})", "info")
                yield stream_response(f"   Type: {inst['InstanceType']}", "info")
                yield stream_response(f"   State: {inst['State']}", "info")
                yield stream_response(f"   Public IP: {inst['PublicIP']}", "info")
                yield stream_response(f"   Private IP: {inst['PrivateIP']}", "info")
                yield stream_response(f"   Launch Time: {inst['LaunchTime']}", "info")
                yield stream_response("", "info")  # Empty line for readability
            
            # Log operation
            await log_operation(
                "list_ec2_instances",
                {"state_filter": state_filter, "tag_filters": tag_filters},
                {"count": len(instances)},
                "success"
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error listing EC2 instances: {error_msg}")
            yield stream_response(f"❌ Error: {error_msg}", "error")
    
    return Response(stream_with_context(generate()), content_type='application/x-ndjson')

@app.route('/ec2/instances/<instance_id>/stop', methods=['POST'])
@async_route
async def stop_ec2_instance(instance_id):
    """Stop EC2 instance endpoint"""
    try:
        ec2 = get_aws_client('ec2')
        response = ec2.stop_instances(InstanceIds=[instance_id])
        
        current_state = response['StoppingInstances'][0]['CurrentState']['Name']
        previous_state = response['StoppingInstances'][0]['PreviousState']['Name']
        
        await log_operation(
            "stop_ec2_instance",
            {"instance_id": instance_id},
            {"current_state": current_state, "previous_state": previous_state},
            "success"
        )
        
        return jsonify({
            "success": True,
            "message": f"EC2 instance {instance_id} stop initiated",
            "previous_state": previous_state,
            "current_state": current_state
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error stopping EC2 instance: {error_msg}")
        await log_operation(
            "stop_ec2_instance",
            {"instance_id": instance_id},
            None,
            "error",
            error_msg
        )
        return jsonify({"error": error_msg}), 500

@app.route('/ec2/instances/<instance_id>/start', methods=['POST'])
@async_route
async def start_ec2_instance(instance_id):
    """Start EC2 instance endpoint"""
    try:
        ec2 = get_aws_client('ec2')
        response = ec2.start_instances(InstanceIds=[instance_id])
        
        current_state = response['StartingInstances'][0]['CurrentState']['Name']
        previous_state = response['StartingInstances'][0]['PreviousState']['Name']
        
        await log_operation(
            "start_ec2_instance",
            {"instance_id": instance_id},
            {"current_state": current_state, "previous_state": previous_state},
            "success"
        )
        
        return jsonify({
            "success": True,
            "message": f"EC2 instance {instance_id} start initiated",
            "previous_state": previous_state,
            "current_state": current_state
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error starting EC2 instance: {error_msg}")
        await log_operation(
            "start_ec2_instance",
            {"instance_id": instance_id},
            None,
            "error",
            error_msg
        )
        return jsonify({"error": error_msg}), 500

@app.route('/ec2/instances/<instance_id>/terminate', methods=['DELETE'])
@async_route
async def terminate_ec2_instance(instance_id):
    """Terminate EC2 instance endpoint"""
    try:
        use_terraform = request.args.get('use_terraform', 'false').lower() == 'true'
        
        if use_terraform:
            # Terraform termination logic would go here
            return jsonify({"error": "Terraform termination not implemented"}), 501
        
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
        
        return jsonify({
            "success": True,
            "message": f"EC2 instance {instance_id} termination initiated",
            "previous_state": previous_state,
            "current_state": current_state
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error terminating EC2 instance: {error_msg}")
        await log_operation(
            "terminate_ec2_instance",
            {"instance_id": instance_id},
            None,
            "error",
            error_msg
        )
        return jsonify({"error": error_msg}), 500

@app.route('/s3/buckets', methods=['GET'])
@async_route
async def list_s3_buckets():
    """List S3 buckets endpoint"""
    async def generate():
        yield stream_response("Fetching S3 buckets...", "info")
        
        try:
            include_size = request.args.get('include_size', 'false').lower() == 'true'
            include_object_count = request.args.get('include_object_count', 'false').lower() == 'true'
            
            s3 = get_aws_client('s3')
            
            # List buckets
            response = s3.list_buckets()
            buckets = response['Buckets']
            
            yield stream_response(f"📦 Found {len(buckets)} S3 bucket(s):", "info")
            
            for bucket in buckets:
                bucket_name = bucket['Name']
                creation_date = bucket['CreationDate'].strftime('%Y-%m-%d %H:%M:%S')
                
                yield stream_response(f"🪣 Bucket: {bucket_name}", "info")
                yield stream_response(f"   Created: {creation_date}", "info")
                
                # Get region
                try:
                    location = s3.get_bucket_location(Bucket=bucket_name)
                    region = location.get('LocationConstraint', 'us-east-1') or 'us-east-1'
                    yield stream_response(f"   Region: {region}", "info")
                except:
                    yield stream_response(f"   Region: Unable to determine", "warning")
                
                # Get size and object count if requested
                if include_size or include_object_count:
                    try:
                        _ = get_aws_client('cloudwatch')
                        
                        if include_size:
                            yield stream_response("   Fetching bucket size...", "info")
                            # CloudWatch metrics logic here
                            yield stream_response("   Size: Metric retrieval not implemented", "warning")
                        
                        if include_object_count:
                            yield stream_response("   Fetching object count...", "info")
                            # CloudWatch metrics logic here
                            yield stream_response("   Objects: Metric retrieval not implemented", "warning")
                            
                    except Exception as e:
                        yield stream_response(f"   Metrics: Unable to retrieve - {str(e)}", "warning")
                
                yield stream_response("", "info")  # Empty line for readability
            
            await log_operation(
                "list_s3_buckets",
                {"include_size": include_size, "include_object_count": include_object_count},
                {"bucket_count": len(buckets)},
                "success"
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error listing S3 buckets: {error_msg}")
            yield stream_response(f"❌ Error: {error_msg}", "error")
    
    return Response(stream_with_context(generate()), content_type='application/x-ndjson')

@app.route('/s3/buckets', methods=['POST'])
@async_route
@validate_json(S3BucketSchema)
async def create_s3_bucket(data):
    """Create S3 bucket endpoint"""
    try:
        bucket_name = data['bucket_name']
        region = data.get('region') or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        versioning = data.get('versioning', False)
        encryption = data.get('encryption', True)
        public_access_block = data.get('public_access_block', True)
        
        s3 = get_aws_client('s3')
        
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
            data,
            {"bucket_name": bucket_name},
            "success"
        )
        
        return jsonify({
            "success": True,
            "message": f"S3 bucket '{bucket_name}' created successfully",
            "bucket_name": bucket_name,
            "region": region,
            "versioning": "Enabled" if versioning else "Disabled",
            "encryption": "Enabled" if encryption else "Disabled",
            "public_access": "Blocked" if public_access_block else "Allowed"
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error creating S3 bucket: {error_msg}")
        await log_operation(
            "create_s3_bucket",
            data,
            None,
            "error",
            error_msg
        )
        return jsonify({"error": error_msg}), 500

@app.route('/cost-analysis', methods=['POST'])
@async_route
@validate_json(CostAnalysisSchema)
async def get_cost_analysis(data):
    """Get AWS cost analysis endpoint"""
    async def generate():
        yield stream_response("Starting cost analysis...", "info")
        
        try:
            start_date = data['start_date'].strftime('%Y-%m-%d')
            end_date = data['end_date'].strftime('%Y-%m-%d')
            granularity = data.get('granularity', 'MONTHLY')
            service_filter = data.get('service_filter')
            generate_graph = data.get('generate_graph', True)
            
            yield stream_response(f"Analyzing costs from {start_date} to {end_date}...", "info")
            
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
            yield stream_response("Fetching cost data from AWS...", "info")
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
            yield stream_response("Storing cost data...", "info")
            async with db_pool.acquire() as conn:
                for item in cost_data:
                    await conn.execute('''
                        INSERT INTO cost_data (service, cost, date, raw_data)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT DO NOTHING
                    ''', item['service'], item['cost'], datetime.strptime(item['period'], '%Y-%m-%d').date(), json.dumps(item))
            
            # Generate summary
            df = pd.DataFrame(cost_data)
            total_cost = df['cost'].sum()
            
            yield stream_response(f"💰 AWS Cost Analysis ({start_date} to {end_date}):", "success")
            yield stream_response(f"Total Cost: ${total_cost:.2f}", "success")
            yield stream_response("", "info")
            
            # Top services by cost
            top_services = df.groupby('service')['cost'].sum().sort_values(ascending=False).head(10)
            yield stream_response("Top 10 Services by Cost:", "info")
            for service, cost in top_services.items():
                yield stream_response(f"  - {service}: ${cost:.2f}", "info")
            
            await log_operation(
                "get_cost_analysis",
                data,
                {"total_periods": len(response['ResultsByTime'])},
                "success"
            )
            
            if generate_graph and not df.empty:
                yield stream_response("📊 Cost visualization data generated", "info")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in cost analysis: {error_msg}")
            yield stream_response(f"❌ Error: {error_msg}", "error")
    
    return Response(stream_with_context(generate()), content_type='application/x-ndjson')

@app.route('/aws/command', methods=['POST'])
@async_route
@validate_json(AWSCommandSchema)
async def execute_aws_command(data):
    """Execute generic AWS command endpoint"""
    try:
        service = data['service']
        action = data['action']
        parameters = data.get('parameters', {})
        
        client = get_aws_client(service)
        
        # Get the method
        if not hasattr(client, action):
            return jsonify({"error": f"Action '{action}' not found for service '{service}'"}), 400
        
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
        
        return jsonify({
            "success": True,
            "service": service,
            "action": action,
            "response": response
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error executing AWS command: {error_msg}")
        await log_operation(
            "execute_aws_command",
            data,
            None,
            "error",
            error_msg
        )
        return jsonify({"error": error_msg}), 500

@app.route('/operations/history', methods=['GET'])
@async_route
async def get_operation_history():
    """Get operation history endpoint"""
    try:
        operation_type = request.args.get('operation_type')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 10))
        
        # Validate limit
        if limit < 1 or limit > 100:
            return jsonify({"error": "Limit must be between 1 and 100"}), 400
        
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
            
            operations = []
            for row in rows:
                operations.append({
                    'id': row['id'],
                    'operation_type': row['operation_type'],
                    'status': row['status'],
                    'created_at': row['created_at'].isoformat(),
                    'execution_time_ms': row['execution_time_ms'],
                    'user_query': row['user_query'],
                    'error_message': row['error_message'],
                    'parameters': row['parameters'],
                    'result': row['result']
                })
            
            return jsonify({
                "success": True,
                "count": len(operations),
                "operations": operations
            })
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error retrieving operation history: {error_msg}")
        return jsonify({"error": error_msg}), 500

@app.route('/terraform/state', methods=['GET'])
@async_route
async def describe_terraform_state():
    """Get Terraform state endpoint"""
    try:
        resource_name = request.args.get('resource_name')
        
        async with db_pool.acquire() as conn:
            if resource_name:
                row = await conn.fetchrow('''
                    SELECT * FROM terraform_states 
                    WHERE resource_name = $1 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', resource_name)
                
                if not row:
                    return jsonify({"error": f"No Terraform state found for resource: {resource_name}"}), 404
                
                return jsonify({
                    "success": True,
                    "resource_name": row['resource_name'],
                    "resource_type": row['resource_type'],
                    "state": row['state'],
                    "created_at": row['created_at'].isoformat(),
                    "updated_at": row['updated_at'].isoformat()
                })
            else:
                rows = await conn.fetch('''
                    SELECT DISTINCT ON (resource_name) 
                        resource_name, resource_type, created_at
                    FROM terraform_states 
                    ORDER BY resource_name, created_at DESC
                ''')
                
                resources = []
                for row in rows:
                    resources.append({
                        'resource_name': row['resource_name'],
                        'resource_type': row['resource_type'],
                        'last_updated': row['created_at'].isoformat()
                    })
                
                return jsonify({
                    "success": True,
                    "count": len(resources),
                    "resources": resources
                })
                
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error retrieving Terraform state: {error_msg}")
        return jsonify({"error": error_msg}), 500

@app.route('/service-status', methods=['GET'])
@async_route
async def get_aws_service_status():
    """Get AWS service status endpoint"""
    def generate():
        yield stream_response("Checking AWS service status...", "info")
        
        try:
            services_param = request.args.get('services')
            if services_param:
                services = services_param.split(',')
            else:
                services = ['ec2', 's3', 'rds', 'lambda', 'dynamodb']
            
            health = get_aws_client('health')
            
            yield stream_response("🏥 AWS Service Health Status:", "info")
            
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
                        yield stream_response(f"⚠️  {service.upper()}: {len(events)} active event(s)", "warning")
                        for event in events[:3]:  # Show first 3 events
                            yield stream_response(f"   - {event.get('eventTypeCode', 'Unknown')}: {event.get('region', 'Global')}", "warning")
                    else:
                        yield stream_response(f"✅ {service.upper()}: Operational", "success")
                        
                except Exception as e:
                    yield stream_response(f"❓ {service.upper()}: Unable to check status - {str(e)}", "error")
            
            # Get account-level information
            try:
                yield stream_response("", "info")
                yield stream_response("📊 Account Information:", "info")
                
                sts = get_aws_client('sts')
                account_info = sts.get_caller_identity()
                yield stream_response(f"   Account ID: {account_info['Account']}", "info")
                yield stream_response(f"   User ARN: {account_info['Arn']}", "info")
            except Exception as e:
                yield stream_response(f"   Unable to retrieve account info: {str(e)}", "warning")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error checking AWS service status: {error_msg}")
            yield stream_response(f"❌ Error: {error_msg}", "error")
    
    return Response(stream_with_context(generate()), content_type='application/x-ndjson')

# Initialize database on startup
@app.before_request
@async_route
async def startup():
    """Initialize database connection pool and tables"""
    global db_pool
    if not hasattr(app, '_has_run_startup'):
        app._has_run_startup = True
    
    try:
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
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

# Cleanup on shutdown
@app.teardown_appcontext
@async_route
async def shutdown(error=None):
    """Clean up resources"""
    global db_pool
    if db_pool:
        try:
            if not db_pool._loop.is_closed():
                await db_pool.close()
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")

# Error handler for all unhandled exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}\n{traceback.format_exc()}")
    return jsonify({"error": "Internal server error", "message": str(e)}), 500

if __name__ == '__main__':
    # Check for required environment variables
    required_env_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'DB_PASSWORD']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your .env file")
        exit(1)
    
    # Run the Flask app
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )