"""
Example client for AWS Flask APIs
Demonstrates how to interact with both streaming and non-streaming endpoints
"""

import json
import requests
from typing import Generator
import sys

# API Configuration
CLIENT_API_URL = "http://localhost:5001"
AWS_API_URL = "http://localhost:5000"

def stream_chat(message: str, session_id: str = "demo") -> Generator[dict, None, None]:
    """Send a chat message and stream the response"""
    url = f"{CLIENT_API_URL}/chat"
    data = {
        "message": message,
        "session_id": session_id
    }
    
    response = requests.post(url, json=data, stream=True)
    response.raise_for_status()
    
    for line in response.iter_lines():
        if line:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                print(f"Failed to parse: {line}")

def simple_query(query: str) -> dict:
    """Send a simple query (non-streaming)"""
    url = f"{CLIENT_API_URL}/query"
    data = {"query": query}
    
    response = requests.post(url, json=data)
    response.raise_for_status()
    return response.json()

def list_ec2_instances_direct() -> Generator[dict, None, None]:
    """Directly call AWS API to list EC2 instances (streaming)"""
    url = f"{AWS_API_URL}/ec2/instances"
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    for line in response.iter_lines():
        if line:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                print(f"Failed to parse: {line}")

def create_s3_bucket_direct(bucket_name: str) -> dict:
    """Directly create an S3 bucket"""
    url = f"{AWS_API_URL}/s3/buckets"
    data = {
        "bucket_name": bucket_name,
        "encryption": True,
        "versioning": False
    }
    
    response = requests.post(url, json=data)
    response.raise_for_status()
    return response.json()

def print_streaming_response(response_generator: Generator[dict, None, None]):
    """Pretty print streaming responses"""
    for response in response_generator:
        status = response.get('status', 'info')
        message = response.get('message', '')
        
        # Color coding based on status
        if status == 'error':
            print(f"❌ {message}")
        elif status == 'success':
            print(f"✅ {message}")
        elif status == 'warning':
            print(f"⚠️  {message}")
        elif status == 'assistant':
            print(f"\n🤖 Assistant:\n{message}\n")
        else:
            print(f"ℹ️  {message}")

def main():
    """Main example flow"""
    print("🚀 AWS Flask API Client Example\n")
    
    # Example 1: Simple query
    print("1️⃣ Simple Query Example:")
    print("-" * 50)
    result = simple_query("What are the best practices for EC2?")
    print(f"Response: {result['response'][:200]}...\n")
    
    # Example 2: Chat with streaming (asking to list instances)
    print("2️⃣ Chat Example - List EC2 Instances:")
    print("-" * 50)
    responses = stream_chat("Show me all my EC2 instances")
    print_streaming_response(responses)
    
    # Example 3: Direct API call
    print("\n3️⃣ Direct API Call - List EC2 Instances:")
    print("-" * 50)
    instances = list_ec2_instances_direct()
    print_streaming_response(instances)
    
    # Example 4: Cost analysis via chat
    print("\n4️⃣ Chat Example - Cost Analysis:")
    print("-" * 50)
    responses = stream_chat("What's my AWS cost for the last month?")
    print_streaming_response(responses)
    
    # Example 5: Create resource via chat
    print("\n5️⃣ Chat Example - Create S3 Bucket:")
    print("-" * 50)
    responses = stream_chat("Create an S3 bucket named my-demo-bucket-12345")
    print_streaming_response(responses)
    
    # Example 6: Get help
    print("\n6️⃣ Get Help:")
    print("-" * 50)
    response = requests.get(f"{CLIENT_API_URL}/help")
    help_data = response.json()
    print("Available example queries:")
    for category in help_data['examples']:
        print(f"\n{category['category']}:")
        for query in category['queries'][:2]:  # Show first 2 examples
            print(f"  - {query}")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the API servers.")
        print("Make sure both Flask servers are running:")
        print("  - AWS API Server on port 5000")
        print("  - Client API Server on port 5001")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)