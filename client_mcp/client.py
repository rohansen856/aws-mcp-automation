import asyncio
import os
from typing import Optional, Dict, List, Any
from contextlib import AsyncExitStack
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.request import urlopen

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import ollama
import chromadb
from chromadb.config import Settings
import requests
from bs4 import BeautifulSoup
import re

load_dotenv()

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
        # This would ideally scrape AWS docs, but for demo purposes, we'll add some common knowledge
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

class EnhancedAWSMCPClient:
    def __init__(self):
        self.sessions = []
        self.exit_stack = AsyncExitStack()
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'granite3.3')
        self.knowledge_base = AWSKnowledgeBase()
        self.conversation_context = []
        
    async def connect_to_server(self, server_script_path: str):
        """Connect to the AWS MCP server"""
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
            env=None
        )

        print(f'🚀 Connecting to AWS MCP Server...')
        print(f'🤖 Using {self.ollama_model} model for natural language processing')

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        
        await session.initialize()
        
        self.sessions.append({
            "path": server_script_path,
            "session": session
        })
        
        response = await session.list_tools()
        tools = response.tools
        print(f"\n✅ Connected to AWS automation server with {len(tools)} tools available")
        print("Available operations:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process user query with RAG enhancement"""
        # Search knowledge base for relevant information
        kb_results = self.knowledge_base.search(query)
        
        # Get available tools
        available_tools = []
        session_map = {}
        
        for session_info in self.sessions:
            session = session_info["session"]
            response = await session.list_tools()
            for tool in response.tools:
                tool_info = { 
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                available_tools.append(tool_info)
                session_map[tool.name] = session

        # Format knowledge base context
        kb_context = "\n".join([f"- {r['text']}" for r in kb_results]) if kb_results else "No specific AWS knowledge found for this query."

        # Enhanced system prompt with conversation context
        recent_context = "\n".join(self.conversation_context[-3:]) if self.conversation_context else "No previous context."
        
        system_prompt = f"""You are an AWS expert assistant with access to AWS automation tools. 

Current Context:
{recent_context}

Relevant AWS Knowledge:
{kb_context}

Available Tools:
{self._format_tools(available_tools)}

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

Current time: {get_current_time()}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        response = ollama.chat(
            model=self.ollama_model,
            messages=messages
        )
        response_content = response['message']['content']

        # Store conversation context
        self.conversation_context.append(f"User: {query}")
        self.conversation_context.append(f"Assistant: {response_content[:200]}...")

        # Process tool calls if needed
        final_output = [response_content]
        
        if "---TOOL_START---" in response_content and "---TOOL_END---" in response_content:
            try:
                tool_section = response_content.split("---TOOL_START---")[1].split("---TOOL_END---")[0].strip()
                tool_lines = [line.strip() for line in tool_section.split('\n') if line.strip()]
                
                tool_name = tool_lines[0][5:].strip()
                input_json = tool_lines[1][6:].strip()
                tool_input = json.loads(input_json)
                
                if tool_name in session_map:
                    result = await session_map[tool_name].call_tool(tool_name, tool_input)
                    final_output.append(f"\n[Tool {tool_name} executed]")

                    # Get follow-up response
                    follow_up_messages = messages + [
                        {"role": "assistant", "content": response_content},
                        {"role": "user", "content": f"Tool {tool_name} returned: {result.content}\n\nPlease provide a helpful response incorporating this information."}
                    ]
                    
                    follow_up_response = ollama.chat(
                        model=self.ollama_model,
                        messages=follow_up_messages
                    )
                    final_output.append(follow_up_response['message']['content'])

            except Exception as e:
                final_output.append(f"\n❌ Error executing tool: {str(e)}")

        return "\n".join(final_output)

    def _format_tools(self, tools: List[Dict]) -> str:
        """Format tools information clearly"""
        formatted = []
        for i, tool in enumerate(tools):
            formatted.append(f"Tool {i+1}: {tool['name']}")
            formatted.append(f"Description: {tool['description']}")
            formatted.append(f"Input Schema: {json.dumps(tool['input_schema'], indent=2)}")
            formatted.append("")
        return "\n".join(formatted)

    async def interactive_session(self):
        """Run an interactive AWS management session"""
        print("\n🎮 AWS Interactive Session Started!")
        print("I can help you manage AWS resources, answer questions, and provide cost analysis.")
        print("Type 'help' for examples or 'quit' to exit.\n")
        
        while True:
            try:
                query = input("\n🔧 AWS Console> ").strip()
                
                if query.lower() == 'quit':
                    break
                
                if query.lower() == 'help':
                    print("""
Example queries you can try:
- "Create a t2.micro EC2 instance with Ubuntu"
- "Show me all running EC2 instances"
- "What's my AWS cost for the last 3 months?"
- "List all S3 buckets with their sizes"
- "Stop instance i-1234567890abcdef0"
- "What are the best practices for EC2?"
- "How can I optimize my AWS costs?"
- "Show me my operation history"
- "Create an S3 bucket named my-data-bucket"
                    """)
                    continue
                
                print("\n⏳ Processing...")
                response = await self.process_query(query)
                print("\n" + response)
                    
            except KeyboardInterrupt:
                print("\n\n👋 Session interrupted. Type 'quit' to exit.")
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python aws_client_enhanced.py <path_to_aws_mcp_server.py>")
        sys.exit(1)
        
    client = EnhancedAWSMCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.interactive_session()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())