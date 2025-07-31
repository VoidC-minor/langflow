#!/usr/bin/env python3
"""
Create a simple test flow for benchmarking.
"""

import httpx
import json
import asyncio
from rich.console import Console

console = Console()

async def create_test_flow():
    """Create a simple test flow."""
    url = "http://localhost:7860"
    
    # Create a simple flow with a basic component
    flow_data = {
        "name": "test-flow",
        "description": "Test flow for benchmarking",
        "data": {
            "nodes": [
                {
                    "id": "1",
                    "type": "ChatInput",
                    "position": {"x": 100, "y": 100},
                    "data": {"node": {"template": {"input_value": {"value": "Hello"}}}}
                },
                {
                    "id": "2", 
                    "type": "ChatOutput",
                    "position": {"x": 300, "y": 100},
                    "data": {"node": {"template": {}}}
                }
            ],
            "edges": [
                {
                    "id": "edge-1",
                    "source": "1",
                    "target": "2",
                    "sourceHandle": "output",
                    "targetHandle": "input"
                }
            ]
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create the flow
            response = await client.post(
                f"{url}/api/v1/flows",
                json=flow_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                flow = response.json()
                console.print(f"✅ Test flow created: {flow.get('id', 'unknown')}", style="green")
                return flow.get('id')
            else:
                console.print(f"❌ Failed to create flow: {response.status_code}", style="red")
                console.print(response.text)
                return None
                
    except Exception as e:
        console.print(f"❌ Error creating test flow: {e}", style="red")
        return None

async def main():
    """Main function."""
    console.print("🔧 Creating test flow for benchmarking...", style="bold blue")
    flow_id = await create_test_flow()
    
    if flow_id:
        console.print(f"✅ Test flow ready with ID: {flow_id}", style="green")
        console.print("You can now run the benchmark with this flow ID.", style="blue")
    else:
        console.print("❌ Failed to create test flow", style="red")

if __name__ == "__main__":
    asyncio.run(main()) 