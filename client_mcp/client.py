import asyncio
import os
from typing import Optional
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import ollama

from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.request import urlopen
import json

load_dotenv()

def get_current_time() -> str:
    """
    Retrieves the current date, time, and timezone information.
    Returns a formatted string with local time in both 12-hour and ISO formats,
    along with timezone abbreviation.
    
    """
    try:
        # Get timezone information
        with urlopen('https://ipapi.co/json/') as response:
            ip_data = json.loads(response.read().decode())
        timezone = ip_data.get('timezone', 'UTC')
        
        # Get current time in the detected timezone
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        
        # Get timezone abbreviation (like EST, EDT, IST)
        tz_abbrev = now.strftime('%Z')
        
        # Format the response
        return (f"Current local time: {now.strftime('%A, %B %d, %Y at %I:%M:%S %p')} {tz_abbrev}\n"
                f"ISO format: {now.isoformat()}")
                
    except Exception as e:
        # Fallback to UTC if there's any error
        now = datetime.now(ZoneInfo('UTC'))
        return (f"Could not detect local timezone. Current UTC time:\n"
                f"{now.strftime('%A, %B %d, %Y at %I:%M:%S %p')} UTC\n"
                f"ISO format: {now.isoformat()}")


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.sessions = []  # Store multiple sessions
        self.exit_stack = AsyncExitStack()
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'granite3.3')
        
    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server and add to sessions list
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        print(f'Using the {os.getenv("OLLAMA_MODEL", "granite3.3")} model for Ollama API')

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        
        await session.initialize()
        
        # Add to sessions list
        self.sessions.append({
            "path": server_script_path,
            "session": session
        })
        
        # List available tools for this server
        response = await session.list_tools()
        tools = response.tools
        print(f"\nConnected to server {server_script_path} with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Ollama and available tools"""
        # Get available tools from all sessions
        available_tools = []
        session_map = {}  # Map tool names to their sessions
        
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

        # Format tools information more clearly
        tools_prompt = "\n".join(
            f"Tool {i+1}: {tool['name']}\n"
            f"Description: {tool['description']}\n"
            f"Input Schema: {tool['input_schema']}\n"
            for i, tool in enumerate(available_tools))
        
        # System prompt with clear instructions
        system_prompt = f"""You are an AI assistant with access to tools. 

    Available Tools:
    {tools_prompt}

    Instructions:
    1. Carefully analyze the user's query to determine if a tool is needed.
    2. To call a tool, respond EXACTLY in this format:
    ---TOOL_START---
    TOOL: tool_name
    INPUT: {{"key": "value"}}
    ---TOOL_END---
    3. The INPUT must be valid JSON matching the tool's input schema.
    4. If no tool is needed, respond normally to the user's query.
    5. Never make up tool names or parameters - only use what's provided.

    current details : {get_current_time()}
    """

        # Initial Ollama API call
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        response = ollama.chat(
            model=self.ollama_model,
            messages=messages
        )
        response_content = response['message']['content']

        # Process response and handle tool calls
        final_output = [response_content]
        tool_results = []

        # More robust tool call detection
        tool_call_start = "---TOOL_START---"
        tool_call_end = "---TOOL_END---"
        
        if tool_call_start in response_content and tool_call_end in response_content:
            try:
                # Extract tool call section
                tool_section = response_content.split(tool_call_start)[1].split(tool_call_end)[0].strip()
                
                # Parse tool name and input
                tool_lines = [line.strip() for line in tool_section.split('\n') if line.strip()]
                
                tool_name = tool_lines[0][5:].strip()
                input_json = tool_lines[1][6:].strip()
                
                # Parse the input as JSON
                tool_input = json.loads(input_json)
                
                # Verify tool exists
                tool_exists = any(tool['name'] == tool_name for tool in available_tools)
                if not tool_exists:
                    raise ValueError(f"Tool '{tool_name}' not found in available tools")
                
                # Use the appropriate session for this tool
                if tool_name in session_map:
                    result = await session_map[tool_name].call_tool(tool_name, tool_input)
                    tool_results.append({"call": tool_name, "result": result})
                    final_output.append(f"\n[Tool {tool_name} executed successfully]")

                    # Continue conversation with tool results
                    follow_up_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query},
                        {"role": "assistant", "content": response_content},
                        {"role": "user", "content": f"Tool {tool_name} returned: {result.content}\n\nNow provide a helpful response to my original query incorporating this information."}
                    ]
                    
                    follow_up_response = ollama.chat(
                        model=self.ollama_model,
                        messages=follow_up_messages
                    )
                    final_output.append(follow_up_response['message']['content'])

            except json.JSONDecodeError:
                final_output.append("\nError: Invalid JSON format in tool input.")
            except ValueError as e:
                final_output.append(f"\nError: {str(e)}")
            except Exception as e:
                final_output.append(f"\nError executing tool: {str(e)}")

        return "\n".join(final_output)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        for server_script in sys.argv[1:]:
            await client.connect_to_server(server_script)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())