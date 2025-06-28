import os
import json
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.request import urlopen
import traceback

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import ollama
import chromadb
from chromadb.config import Settings
from bs4 import BeautifulSoup
from marshmallow import Schema, fields, validate, ValidationError
import logging
import re

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Configuration
AWS_API_BASE_URL = os.getenv('AWS_API_BASE_URL', 'http://localhost:5000')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'granite3.1')

# Validation Schemas
class QuerySchema(Schema):
    query = fields.String(required=True, validate=validate.Length(min=1, max=1000))
    context = fields.List(fields.String(), required=False)
    stream = fields.Boolean(required=False)

class ChatMessageSchema(Schema):
    message = fields.String(required=True, validate=validate.Length(min=1, max=1000))
    session_id = fields.String(required=False)

# Error handlers
@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify({"error": "Validation error", "messages": e.messages}), 400

@app.errorhandler(404)
def handle_not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def handle_internal_error(e):
    logger.error(f"Internal error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500

# Knowledge Base Class
class AWSKnowledgeBase:
    """RAG system for AWS documentation"""
    
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path="./aws_knowledge_base")
        
        # Create or get collection
        try:
            self.collection = self.chroma_client.create_collection(
                name="aws_docs",
                metadata={"hnsw:space": "cosine"}
            )
            self._populate_knowledge_base()
        except:
            self.collection = self.chroma_client.get_collection("aws_docs")
    
    def _populate_knowledge_base(self):
        """Populate with common AWS knowledge"""
        aws_knowledge = [
            {
                "id": "ec2_basics",
                "text": "Amazon EC2 (Elastic Compute Cloud) provides scalable computing capacity. Common instance types include: t2.micro (1 vCPU, 1 GB RAM, free tier eligible), t3.medium (2 vCPUs, 4 GB RAM), m5.large (2 vCPUs, 8 GB RAM). Best practices: use Auto Scaling Groups for high availability, enable detailed monitoring, use appropriate instance types for workload.",
                "metadata": {"service": "ec2", "topic": "basics"}
            },
            {
                "id": "s3_basics",
                "text": "Amazon S3 (Simple Storage Service) provides object storage. Storage classes: Standard (frequent access), Standard-IA (infrequent access), Glacier (archival). Best practices: enable versioning for critical data, use lifecycle policies to optimize costs, enable server-side encryption, implement least-privilege bucket policies.",
                "metadata": {"service": "s3", "topic": "basics"}
            },
            {
                "id": "cost_optimization",
                "text": "AWS Cost Optimization strategies: 1) Use Reserved Instances for predictable workloads (up to 75% savings), 2) Enable AWS Cost Explorer for visibility, 3) Set up billing alerts, 4) Use Spot Instances for fault-tolerant workloads, 5) Right-size instances regularly, 6) Delete unattached EBS volumes, 7) Use S3 lifecycle policies.",
                "metadata": {"service": "general", "topic": "cost"}
            },
            {
                "id": "security_best_practices",
                "text": "AWS Security Best Practices: 1) Enable MFA on root account, 2) Use IAM roles instead of access keys, 3) Enable CloudTrail for audit logging, 4) Use VPC for network isolation, 5) Encrypt data at rest and in transit, 6) Regular security assessments with AWS Inspector, 7) Implement least privilege access.",
                "metadata": {"service": "general", "topic": "security"}
            },
            {
                "id": "vpc_networking",
                "text": "Amazon VPC (Virtual Private Cloud) allows you to launch AWS resources in a logically isolated virtual network. Key concepts: Subnets (public/private), Route Tables, Internet Gateway, NAT Gateway, Security Groups (instance-level firewall), NACLs (subnet-level firewall). Best practice: use multiple Availability Zones for high availability.",
                "metadata": {"service": "vpc", "topic": "networking"}
            },
            {
                "id": "lambda_basics",
                "text": "AWS Lambda lets you run code without provisioning servers. Key features: automatic scaling, pay per request, supports multiple languages. Best practices: keep functions small and focused, use environment variables for configuration, implement proper error handling, monitor with CloudWatch.",
                "metadata": {"service": "lambda", "topic": "basics"}
            },
            {
                "id": "rds_basics",
                "text": "Amazon RDS (Relational Database Service) provides managed database instances. Supports MySQL, PostgreSQL, Oracle, SQL Server, MariaDB, and Aurora. Features: automated backups, Multi-AZ deployments for high availability, read replicas for scalability, automated patching.",
                "metadata": {"service": "rds", "topic": "basics"}
            }
        ]
        
        for doc in aws_knowledge:
            self.collection.add(
                documents=[doc["text"]],
                metadatas=[doc["metadata"]],
                ids=[doc["id"]]
            )
    
    def search(self, query: str, n_results: int = 3) -> List[Dict]:
        """Search the knowledge base"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted_results

# Initialize knowledge base
knowledge_base = AWSKnowledgeBase()

# Session management
conversation_sessions = {}

def get_current_time() -> str:
    """Get current time with timezone info"""
    try:
        with urlopen('https://ipapi.co/json/') as response:
            ip_data = json.loads(response.read().decode())
        timezone = ip_data.get('timezone', 'UTC')
        
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        tz_abbrev = now.strftime('%Z')
        
        return (f"Current local time: {now.strftime('%A, %B %d, %Y at %I:%M:%S %p')} {tz_abbrev}\n"
                f"ISO format: {now.isoformat()}")
                
    except Exception:
        now = datetime.now(ZoneInfo('UTC'))
        return (f"Current UTC time:\n"
                f"{now.strftime('%A, %B %d, %Y at %I:%M:%S %p')} UTC\n"
                f"ISO format: {now.isoformat()}")

def parse_tool_call(response_content: str) -> Optional[Dict]:
    """Parse tool call from LLM response"""
    if "---TOOL_START---" in response_content and "---TOOL_END---" in response_content:
        try:
            tool_section = response_content.split("---TOOL_START---")[1].split("---TOOL_END---")[0].strip()
            tool_lines = [line.strip() for line in tool_section.split('\n') if line.strip()]
            
            tool_name = tool_lines[0][5:].strip()
            input_json = tool_lines[1][6:].strip()
            tool_input = json.loads(input_json)
            
            return {
                "tool_name": tool_name,
                "input": tool_input
            }
        except Exception as e:
            logger.error(f"Error parsing tool call: {str(e)}")
            return None
    return None

def map_tool_to_api_endpoint(tool_name: str, tool_input: Dict) -> Optional[Dict]:
    """Map tool calls to AWS API endpoints"""
    mapping = {
        "create_ec2_instance": {
            "method": "POST",
            "endpoint": "/ec2/instances",
            "data": tool_input
        },
        "list_ec2_instances": {
            "method": "GET",
            "endpoint": "/ec2/instances",
            "params": tool_input
        },
        "stop_ec2_instance": {
            "method": "POST",
            "endpoint": f"/ec2/instances/{tool_input.get('instance_id')}/stop",
            "data": {}
        },
        "start_ec2_instance": {
            "method": "POST",
            "endpoint": f"/ec2/instances/{tool_input.get('instance_id')}/start",
            "data": {}
        },
        "terminate_ec2_instance": {
            "method": "DELETE",
            "endpoint": f"/ec2/instances/{tool_input.get('instance_id')}/terminate",
            "params": {"use_terraform": tool_input.get('use_terraform', False)}
        },
        "list_s3_buckets": {
            "method": "GET",
            "endpoint": "/s3/buckets",
            "params": tool_input
        },
        "create_s3_bucket": {
            "method": "POST",
            "endpoint": "/s3/buckets",
            "data": tool_input
        },
        "get_cost_analysis": {
            "method": "POST",
            "endpoint": "/cost-analysis",
            "data": tool_input
        },
        "execute_aws_command": {
            "method": "POST",
            "endpoint": "/aws/command",
            "data": tool_input
        },
        "get_operation_history": {
            "method": "GET",
            "endpoint": "/operations/history",
            "params": tool_input
        },
        "describe_terraform_state": {
            "method": "GET",
            "endpoint": "/terraform/state",
            "params": tool_input
        },
        "get_aws_service_status": {
            "method": "GET",
            "endpoint": "/service-status",
            "params": {"services": ",".join(tool_input.get('services', []))} if tool_input.get('services') else {}
        }
    }
    
    return mapping.get(tool_name)

def stream_response(message: str, status: str = "info", tool_result: Any = None):
    """Helper to format streaming responses"""
    response = {
        "message": message,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    if tool_result is not None:
        response["tool_result"] = tool_result
    return json.dumps(response) + "\n"

# API Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ollama_model": OLLAMA_MODEL,
        "aws_api_url": AWS_API_BASE_URL
    })

@app.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint with streaming support"""
    try:
        data = request.get_json()
        schema = ChatMessageSchema()
        validated_data = schema.load(data)
        
        message = validated_data['message']
        session_id = validated_data.get('session_id', 'default')
        
        def generate():
            try:
                # Get or create session context
                if session_id not in conversation_sessions:
                    conversation_sessions[session_id] = []
                
                session_context = conversation_sessions[session_id]
                
                # Search knowledge base
                yield stream_response("Searching AWS knowledge base...", "info")
                kb_results = knowledge_base.search(message)
                
                # Format knowledge base context
                kb_context = "\n".join([f"- {r['text']}" for r in kb_results]) if kb_results else "No specific AWS knowledge found for this query."
                
                # Get available tools description
                tools_description = get_tools_description()
                
                # Build context
                recent_context = "\n".join(session_context[-3:]) if session_context else "No previous context."
                
                system_prompt = f"""You are an AWS expert assistant with access to AWS automation tools. 

Current Context:
{recent_context}

Relevant AWS Knowledge:
{kb_context}

Available Tools:
{tools_description}

Instructions:
1. Analyze the user's query carefully
2. Use the AWS knowledge provided to give accurate information
3. If the user wants to perform an AWS action, use the appropriate tool
4. For questions about AWS, provide detailed answers using the knowledge base
5. To call a tool, respond EXACTLY in this format:
---TOOL_START---
TOOL: tool_name
INPUT: {{"key": "value"}}
---TOOL_END---
6. For multi-step operations, guide the user through each step
7. Always consider security best practices and cost implications
8. Format your responses in clear Markdown

Current time: {get_current_time()}
"""

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
                
                # Get initial response from LLM
                yield stream_response("Processing your request...", "info")
                
                response = ollama.chat(
                    model=OLLAMA_MODEL,
                    messages=messages
                )
                response_content = response['message']['content']
                
                # Store in session context
                session_context.append(f"User: {message}")
                session_context.append(f"Assistant: {response_content[:200]}...")
                
                # Keep only last 10 exchanges
                if len(session_context) > 20:
                    session_context = session_context[-20:]
                conversation_sessions[session_id] = session_context
                
                # Check for tool calls
                tool_call = parse_tool_call(response_content)
                
                if tool_call:
                    yield stream_response(f"Executing {tool_call['tool_name']}...", "info")
                    
                    # Map to API endpoint
                    api_call = map_tool_to_api_endpoint(tool_call['tool_name'], tool_call['input'])
                    
                    if api_call:
                        # Make API call to AWS backend
                        try:
                            url = f"{AWS_API_BASE_URL}{api_call['endpoint']}"
                            
                            if api_call['method'] == 'GET':
                                api_response = requests.get(url, params=api_call.get('params', {}), stream=True)
                            elif api_call['method'] == 'POST':
                                api_response = requests.post(url, json=api_call.get('data', {}), stream=True)
                            elif api_call['method'] == 'DELETE':
                                api_response = requests.delete(url, params=api_call.get('params', {}))
                            
                            # Handle streaming responses
                            if api_response.headers.get('content-type') == 'application/x-ndjson':
                                for line in api_response.iter_lines():
                                    if line:
                                        try:
                                            line_data = json.loads(line)
                                            yield stream_response(line_data.get('message', ''), line_data.get('status', 'info'))
                                        except:
                                            yield stream_response(line.decode('utf-8'), "info")
                            else:
                                # Non-streaming response
                                result = api_response.json()
                                yield stream_response("Tool execution completed", "success", result)
                            
                            # Get follow-up response from LLM
                            follow_up_messages = messages + [
                                {"role": "assistant", "content": response_content},
                                {"role": "user", "content": f"The tool execution completed. Please provide a helpful summary of what was done and any relevant information for the user."}
                            ]
                            
                            follow_up_response = ollama.chat(
                                model=OLLAMA_MODEL,
                                messages=follow_up_messages
                            )
                            
                            yield stream_response(follow_up_response['message']['content'], "assistant")
                            
                        except requests.exceptions.RequestException as e:
                            yield stream_response(f"Error calling AWS API: {str(e)}", "error")
                    else:
                        yield stream_response(f"Unknown tool: {tool_call['tool_name']}", "error")
                else:
                    # No tool call, just return the response
                    yield stream_response(response_content, "assistant")
                    
            except Exception as e:
                logger.error(f"Error in chat generation: {str(e)}\n{traceback.format_exc()}")
                yield stream_response(f"Error: {str(e)}", "error")
        
        return Response(stream_with_context(generate()), content_type='application/x-ndjson')
        
    except ValidationError as e:
        return jsonify({"error": "Validation error", "messages": e.messages}), 400
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/query', methods=['POST'])
def process_query():
    """Process a single query (non-streaming)"""
    try:
        schema = QuerySchema()
        data = schema.load(request.get_json() or {})
        
        query = data['query']
        context = data.get('context', [])
        
        # Search knowledge base
        kb_results = knowledge_base.search(query)
        
        # Process with LLM
        kb_context = "\n".join([f"- {r['text']}" for r in kb_results]) if kb_results else ""
        
        system_prompt = f"""You are an AWS expert assistant. 

Relevant AWS Knowledge:
{kb_context}

Instructions:
1. Provide accurate, helpful information about AWS
2. Use the knowledge base information when relevant
3. Format responses in clear Markdown
4. Be concise but thorough
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages
        )
        
        return jsonify({
            "success": True,
            "response": response['message']['content'],
            "knowledge_base_results": kb_results
        })
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/sessions/<session_id>', methods=['DELETE'])
def clear_session(session_id):
    """Clear a conversation session"""
    if session_id in conversation_sessions:
        del conversation_sessions[session_id]
        return jsonify({"success": True, "message": f"Session {session_id} cleared"})
    return jsonify({"error": "Session not found"}), 404

@app.route('/knowledge/search', methods=['POST'])
def search_knowledge():
    """Search the knowledge base directly"""
    try:
        data = request.get_json() or {}
        query = data.get('query', '')
        n_results = data.get('n_results', 3)
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        results = knowledge_base.search(query, n_results)
        
        return jsonify({
            "success": True,
            "results": results,
            "count": len(results)
        })
        
    except Exception as e:
        logger.error(f"Error searching knowledge base: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_tools_description():
    """Get formatted description of available tools"""
    tools = [
        {
            "name": "create_ec2_instance",
            "description": "Create an EC2 instance",
            "parameters": ["instance_type", "ami_id", "key_name", "security_group_ids", "subnet_id", "name", "use_terraform"]
        },
        {
            "name": "list_ec2_instances",
            "description": "List EC2 instances with optional filters",
            "parameters": ["state_filter", "tag_filters"]
        },
        {
            "name": "stop_ec2_instance",
            "description": "Stop a running EC2 instance",
            "parameters": ["instance_id"]
        },
        {
            "name": "start_ec2_instance",
            "description": "Start a stopped EC2 instance",
            "parameters": ["instance_id"]
        },
        {
            "name": "terminate_ec2_instance",
            "description": "Terminate an EC2 instance permanently",
            "parameters": ["instance_id", "use_terraform"]
        },
        {
            "name": "list_s3_buckets",
            "description": "List all S3 buckets",
            "parameters": ["include_size", "include_object_count"]
        },
        {
            "name": "create_s3_bucket",
            "description": "Create a new S3 bucket",
            "parameters": ["bucket_name", "region", "versioning", "encryption", "public_access_block"]
        },
        {
            "name": "get_cost_analysis",
            "description": "Get AWS cost analysis for a period",
            "parameters": ["start_date", "end_date", "granularity", "service_filter", "generate_graph"]
        },
        {
            "name": "execute_aws_command",
            "description": "Execute any AWS API command",
            "parameters": ["service", "action", "parameters"]
        },
        {
            "name": "get_operation_history",
            "description": "Get history of operations",
            "parameters": ["operation_type", "status", "limit"]
        },
        {
            "name": "describe_terraform_state",
            "description": "Get Terraform state information",
            "parameters": ["resource_name"]
        },
        {
            "name": "get_aws_service_status",
            "description": "Check AWS service health status",
            "parameters": ["services"]
        }
    ]
    
    formatted = []
    for tool in tools:
        params_str = ", ".join(tool["parameters"])
        formatted.append(f"- {tool['name']}: {tool['description']} (Parameters: {params_str})")
    
    return "\n".join(formatted)

@app.route('/help', methods=['GET'])
def get_help():
    """Get help information and example queries"""
    examples = [
        {
            "category": "EC2 Management",
            "queries": [
                "Create a t2.micro EC2 instance with Ubuntu",
                "Show me all running EC2 instances",
                "Stop instance i-1234567890abcdef0",
                "Start instance i-1234567890abcdef0",
                "Terminate instance i-1234567890abcdef0"
            ]
        },
        {
            "category": "S3 Management",
            "queries": [
                "List all S3 buckets with their sizes",
                "Create an S3 bucket named my-data-bucket",
                "Show me S3 buckets in us-west-2 region"
            ]
        },
        {
            "category": "Cost Analysis",
            "queries": [
                "What's my AWS cost for the last 3 months?",
                "Show me daily costs for the past week",
                "Analyze EC2 costs for this month"
            ]
        },
        {
            "category": "AWS Best Practices",
            "queries": [
                "What are the best practices for EC2?",
                "How can I optimize my AWS costs?",
                "What are AWS security best practices?",
                "Explain VPC networking basics"
            ]
        },
        {
            "category": "Operations",
            "queries": [
                "Show me my operation history",
                "Check AWS service status",
                "Show terraform state for my resources"
            ]
        }
    ]
    
    return jsonify({
        "success": True,
        "examples": examples,
        "available_tools": get_tools_description().split('\n'),
        "tips": [
            "You can ask questions about AWS services and best practices",
            "I can help you create, manage, and monitor AWS resources",
            "Use natural language - I'll understand what you want to do",
            "I provide real-time cost analysis and optimization suggestions"
        ]
    })

@app.route('/api/docs', methods=['GET'])
def api_documentation():
    """Get API documentation"""
    endpoints = [
        {
            "endpoint": "/chat",
            "method": "POST",
            "description": "Main chat endpoint with streaming support",
            "parameters": {
                "message": "Your message or query (required)",
                "session_id": "Session ID for conversation context (optional)"
            },
            "response": "Streaming JSON responses with message, status, and optional tool_result"
        },
        {
            "endpoint": "/query",
            "method": "POST",
            "description": "Process a single query without streaming",
            "parameters": {
                "query": "Your query (required)",
                "context": "Additional context (optional)"
            },
            "response": "JSON with response and knowledge base results"
        },
        {
            "endpoint": "/knowledge/search",
            "method": "POST",
            "description": "Search the knowledge base directly",
            "parameters": {
                "query": "Search query (required)",
                "n_results": "Number of results (optional, default: 3)"
            },
            "response": "JSON with search results"
        },
        {
            "endpoint": "/sessions/{session_id}",
            "method": "DELETE",
            "description": "Clear a conversation session",
            "parameters": {},
            "response": "Success message"
        },
        {
            "endpoint": "/help",
            "method": "GET",
            "description": "Get help information and examples",
            "parameters": {},
            "response": "JSON with examples and tips"
        },
        {
            "endpoint": "/health",
            "method": "GET",
            "description": "Health check endpoint",
            "parameters": {},
            "response": "JSON with status and configuration"
        }
    ]
    
    return jsonify({
        "success": True,
        "api_version": "1.0",
        "base_url": request.url_root,
        "endpoints": endpoints,
        "streaming_format": "application/x-ndjson",
        "authentication": "Not required for demo"
    })

# Error handler for all unhandled exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}\n{traceback.format_exc()}")
    return jsonify({"error": "Internal server error", "message": str(e)}), 500

if __name__ == '__main__':
    # Check for required environment variables
    if not os.getenv('AWS_API_BASE_URL'):
        logger.warning("AWS_API_BASE_URL not set, using default: http://localhost:5000")
    
    # Run the Flask app
    app.run(
        host=os.getenv('CLIENT_FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('CLIENT_FLASK_PORT', 5001)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )