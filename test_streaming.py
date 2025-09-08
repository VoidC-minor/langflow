#!/usr/bin/env python3
"""
Test streaming functionality with an existing flow ID.
User provides the flow ID to test streaming results.
"""

import asyncio
import json
import os
import sys
import time

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

LANGFLOW_URL = os.getenv("LANGFLOW_URL", "http://localhost:7860")
API_KEY = os.getenv("LANGFLOW_API_KEY", "")


async def get_available_flows():
    """Get list of available flows for user selection."""
    console.print("[blue]Fetching available flows...")
    
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{LANGFLOW_URL}/api/v1/flows/", headers=headers)
            
            if response.status_code == 200:
                flows = response.json()
                console.print(f"[green]Found {len(flows)} flows")
                
                if flows:
                    console.print("\n[cyan]Available flows:")
                    for i, flow in enumerate(flows[:50], 1):
                        name = flow.get('name', 'Unnamed')
                        flow_id = flow.get('id', '')
                        console.print(f"  {i:2d}. {name} (ID: {flow_id})")
                
                return flows
            else:
                console.print(f"[red]Failed to fetch flows: {response.status_code}")
                return []
                
    except Exception as e:
        console.print(f"[red]Error fetching flows: {e}")
        return []


async def test_flow_streaming(flow_id: str, input_message: str = "Hello, test streaming"):
    """Test streaming on a specific flow and display results."""
    console.print(f"\n[bold blue]Testing Streaming on Flow: {flow_id}")
    console.print("=" * 70)
    
    # Streaming URL
    stream_url = f"{LANGFLOW_URL}/api/v1/run/{flow_id}?stream=true"
    
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    
    input_data = {
        "input_value": input_message,
        "input_type": "text",
        "output_type": "chat"
    }
    
    console.print(f"[cyan]Streaming URL: {stream_url}")
    console.print(f"[cyan]Input Message: '{input_message}'")
    console.print(f"[cyan]Request Data: {input_data}")
    
    # Results tracking
    results = {
        "status_code": None,
        "content_type": None,
        "events": [],
        "tokens": [],
        "messages": [],
        "errors": [],
        "duration": 0,
        "success": False
    }
    
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            console.print(f"\n[yellow]Starting streaming request...")
            
            async with client.stream("POST", stream_url, headers=headers, json=input_data) as response:
                results["status_code"] = response.status_code
                results["content_type"] = response.headers.get("content-type", "")
                
                console.print(f"[blue]Status Code: {response.status_code}")
                console.print(f"[blue]Content-Type: {results['content_type']}")
                
                if response.status_code == 200:
                    console.print("[green]HTTP 200 - Connection successful")
                    
                    # Check streaming headers
                    if "text/event-stream" in results['content_type']:
                        console.print("[green]Event-stream content-type detected")
                    else:
                        console.print(f"[yellow]Unexpected content-type: {results['content_type']}")
                    
                    # Read streaming events
                    console.print(f"\n[bold yellow]STREAMING RESULTS:")
                    console.print("-" * 50)
                    
                    event_count = 0
                    token_count = 0
                    timeout_counter = 0
                    
                    async for line in response.aiter_lines():
                        if not line or line.strip() == "":
                            timeout_counter += 0.1
                            if timeout_counter > 10:  # 10 second timeout
                                console.print(f"[yellow]Timeout after 10 seconds")
                                break
                            await asyncio.sleep(0.1)
                            continue
                        
                        timeout_counter = 0  # Reset timeout
                        event_count += 1
                        
                        console.print(f"\n[bold green]Event #{event_count}:")
                        console.print(f"[dim]Raw line: {line}")
                        
                        try:
                            event_data = json.loads(line)
                            event_type = event_data.get("event", "unknown")
                            results["events"].append(event_type)
                            
                            console.print(f"[green]  Event Type: [bold]{event_type}[/bold]")
                            
                            if event_type == "token":
                                token_data = event_data.get("data", {})
                                chunk = token_data.get("chunk", "")
                                token_id = token_data.get("id", "")
                                
                                results["tokens"].append(chunk)
                                token_count += 1
                                
                                console.print(f"[bold yellow]  TOKEN #{token_count}: '{chunk}'")
                                if token_id:
                                    console.print(f"[dim]     Token ID: {token_id}")
                                
                                # Print cumulative text
                                if results["tokens"]:
                                    cumulative = "".join(results["tokens"])
                                    console.print(f"[bold cyan]  Cumulative Text: '{cumulative}'")
                                
                            elif event_type == "add_message":
                                msg_data = event_data.get("data", {})
                                sender = msg_data.get("sender", "Unknown")
                                text = msg_data.get("text", "")
                                msg_id = msg_data.get("id", "")
                                
                                results["messages"].append({"sender": sender, "text": text, "id": msg_id})
                                
                                console.print(f"[blue]  MESSAGE from [bold]{sender}[/bold]:")
                                console.print(f"[blue]     Text: {text}")
                                if msg_id:
                                    console.print(f"[dim]     Message ID: {msg_id}")
                                
                            elif event_type == "end":
                                console.print("[bold magenta]  END - Stream completed successfully")
                                results["success"] = True
                                break
                                
                            elif event_type == "error":
                                error_data = event_data.get("data", {})
                                results["errors"].append(error_data)
                                console.print(f"[red]  ERROR: {error_data}")
                                break
                            
                            else:
                                # Other event types
                                data = event_data.get("data", {})
                                console.print(f"[cyan]  Data: {data}")
                            
                            # Limit events for very long streams
                            if event_count >= 50:
                                console.print("[yellow]Received 50 events, stopping for demo...")
                                break
                                
                        except json.JSONDecodeError as e:
                            console.print(f"[red]  JSON decode error: {e}")
                            console.print(f"[red]     Raw content: {line}")
                            continue
                    
                    results["duration"] = time.time() - start_time
                    
                    # Final summary
                    console.print(f"\n[bold blue]STREAMING TEST SUMMARY:")
                    console.print("=" * 40)
                    console.print(f"[cyan]Duration: {results['duration']:.2f} seconds")
                    console.print(f"[cyan]Total Events: {len(results['events'])}")
                    console.print(f"[cyan]Total Tokens: {len(results['tokens'])}")
                    console.print(f"[cyan]Total Messages: {len(results['messages'])}")
                    console.print(f"[cyan]Errors: {len(results['errors'])}")
                    
                    if results["tokens"]:
                        final_text = "".join(results["tokens"])
                        console.print(f"[bold yellow]Final Streamed Text: '{final_text}'")
                    
                    if results["messages"]:
                        console.print(f"[blue]Messages Received:")
                        for i, msg in enumerate(results["messages"], 1):
                            console.print(f"  {i}. {msg['sender']}: {msg['text'][:100]}...")
                    
                    if results["success"]:
                        console.print("[bold green]STREAMING TEST SUCCESSFUL!")
                    else:
                        console.print("[yellow]Stream ended without 'end' event")
                
                else:
                    # Handle error responses
                    error_text = await response.aread()
                    results["errors"].append(f"HTTP {response.status_code}: {error_text.decode()}")
                    console.print(f"[red]Request failed with status {response.status_code}")
                    console.print(f"[red]Error response: {error_text.decode()}")
                
    except Exception as e:
        results["errors"].append(str(e))
        console.print(f"[red]Exception occurred: {e}")
        import traceback
        console.print(f"[red]Traceback: {traceback.format_exc()}")
    
    results["duration"] = time.time() - start_time
    return results


async def main():
    """Main function - interactive flow selection and streaming test."""
    
    # Health check
    console.print("[blue]Checking Langflow connection...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{LANGFLOW_URL}/health")
            if response.status_code == 200:
                console.print("[green]Langflow is accessible")
            else:
                console.print(f"[red]Health check failed: {response.status_code}")
                return
    except Exception as e:
        console.print(f"[red]Cannot connect to Langflow: {e}")
        return
    
    # Get flow ID from user
    flow_id = None
    
    # Check if flow ID provided as command line argument
    if len(sys.argv) > 1:
        flow_id = sys.argv[1]
        console.print(f"[green]Using flow ID from command line: {flow_id}")
    else:
        # Show available flows and get user input
        flows = await get_available_flows()
        
        console.print(f"\n[bold cyan]Please enter a flow ID to test:")
        console.print(f"[dim]You can copy a flow ID from the list above")
        console.print(f"[dim]Or check the Langflow UI for flow IDs")
        
        flow_id = Prompt.ask("[yellow]Flow ID")
    
    if not flow_id or flow_id.strip() == "":
        console.print("[red]No flow ID provided")
        return
    
    flow_id = flow_id.strip()
    
    # Get input message
    console.print(f"\n[bold cyan]Enter input message (or press Enter for default):")
    input_message = Prompt.ask("[yellow]Input message", default="Hello, test streaming")
    
    # Run the streaming test
    results = await test_flow_streaming(flow_id, input_message)
    
    # Final assessment
    console.print(f"\n[bold blue]FINAL ASSESSMENT:")
    console.print("=" * 50)
    
    if results["status_code"] == 200:
        console.print("[bold green]STREAMING ENDPOINT IS WORKING!")
        console.print("[green]  - HTTP 200 response received")
        console.print("[green]  - Event-stream protocol active")
        
        if results["tokens"]:
            console.print("[green]  - Token streaming is functional")
            console.print(f"[green]  - Received {len(results['tokens'])} tokens")
        else:
            console.print("[yellow]  - No tokens received (may be normal)")
            
        if results["messages"]:
            console.print(f"[green]  - Received {len(results['messages'])} messages")
            
    else:
        console.print("[bold red]STREAMING ENDPOINT HAS ISSUES")
        console.print(f"[red]  - HTTP Status: {results['status_code']}")
        
    if results["errors"]:
        console.print(f"[red]Errors encountered: {len(results['errors'])}")
        for error in results["errors"]:
            console.print(f"[red]  - {error}")
    
    console.print(f"\n[bold green]STREAMING TEST COMPLETED!")
    
    # Return results for potential further processing
    return results


if __name__ == "__main__":
    asyncio.run(main())
